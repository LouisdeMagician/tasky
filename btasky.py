# Import necessary modules for the background script
import re
import sys
import json
import signal
import asyncio
import logging
import aiofiles
import configparser
from pushbullet import Pushbullet
from datetime import datetime, timedelta

# Configuration file path
config_file = "tasky.config"

def read_config():
    """
    Read and parse the configuration file.

    Returns:
        configparser.ConfigParser: The parsed configuration object.
    """
    config = configparser.ConfigParser()
    with open(config_file, mode='r') as file:
        config.read_file(file)
    return config

async def aio_read_config():
    """
    Asynchronously read the configuration from the specified file.

    Returns:
        configparser.ConfigParser: Configuration object.
    """
    config = configparser.ConfigParser()
    async with aiofiles.open(config_file, mode='r') as file:
        contents = await file.read()
        config.read_string(contents)
    return config

# Load configuration
config = read_config()

# Log file path
log_file = config.get('Logs', 'log_file', fallback='tasky_log_file.log')

# Configure logging to write logs to the specified file
logging.basicConfig(filename=log_file, level=logging.INFO)

# Tasks file path
tasks_file = config.get('paths', 'tasks_file', fallback='tasks.json')

# Completed tasks file path
completed_tasks_file = config.get('paths', 'completed_tasks_file', fallback='completed_tasks.json')

# Frequency to check for notifications in seconds
check_frequency = int(config.get('notification', 'check_frequency_seconds', fallback=20))

class TaskEncoder(json.JSONEncoder):
    """
    JSON Encoder for tasks containing datetime objects.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return super().default(obj)


async def aio_read_tasks():
    """
    Asynchronously read tasks from the tasks file.

    Returns:
        list: List of tasks.
    """
    async with aiofiles.open(tasks_file, mode='r') as file:
        content = await file.read()
        return json.loads(content) if content else []


async def aio_write_tasks(tasks):
    """
    Asynchronously write tasks to the tasks file.

    Args:
        tasks (list): List of tasks.
    """
    async with aiofiles.open(tasks_file, mode='w') as file:
        await file.write(json.dumps(tasks, cls=TaskEncoder))


async def aio_read_completed_tasks():
    """
    Asynchronously read completed tasks from the completed tasks file.

    Returns:
        list: List of completed tasks.
    """
    try:
        async with aiofiles.open(completed_tasks_file, mode='r') as file:
            content = await file.read()
            return json.loads(content) if content else []
    except FileNotFoundError:
        # If the file doesn't exist, create an empty file and return an empty list
        async with aiofiles.open(completed_tasks_file, mode='w'):
            pass
        return []


async def aio_append_completed_tasks(completed_tasks):
    """
    Asynchronously append completed tasks to the completed tasks file.

    Args:
        completed_tasks (list): List of completed tasks.
    """
    try:
        # Read existing completed tasks from file
        existing_completed_tasks = await aio_read_completed_tasks()

        # Combine existing and new completed tasks
        all_completed_tasks = existing_completed_tasks + completed_tasks

        # Write the entire list to the file
        await aio_write_completed_tasks(all_completed_tasks)
    except (PermissionError, FileNotFoundError):
        logging.warning("Error: Unable to append completed tasks. Check file permissions and try again.")


async def aio_write_completed_tasks(completed_tasks):
    """
    Asynchronously write completed tasks to the completed tasks file.

    Args:
        completed_tasks (list): List of completed tasks.
    """
    try:
        async with aiofiles.open(completed_tasks_file, mode='w') as file:
            await file.write(json.dumps(completed_tasks, cls=TaskEncoder))
    except (PermissionError, FileNotFoundError):
        logging.warning("Error: Unable to write completed tasks. Check file permissions and try again.")


async def aio_send_notification(title, body):
    """
    Asynchronously send a notification using Pushbullet.

    Args:
        title (str): Notification title.
        body (str): Notification body.
    """
    config = await aio_read_config()
    access_token = config.get("Pushbullet", "access_token", fallback=None)

    try:
        if access_token:
            pb = Pushbullet(access_token)
            pb.push_note(title, body)
        else:
            logging.warning("Pushbullet access token not found in the config file.")
    except Exception:
        logging.info("Error sending notification. Check internet connection, API key push limit and pushbullet.com to troubleshoot")

def extract_command(task_name):
    """
    Extract the command from a task name.

    Args:
        task_name (str): Task name.

    Returns:
        str: Extracted command, or None if no command is found.
    """
    pattern = re.compile(r'^(-e|--execute)\s+(.*)$')
    match = pattern.match(task_name)

    if match:
        return match.group(2)

    return None


async def aio_execute_command(command):
    """
    Asynchronously execute a shell command using Docker.

    Args:
        command (str): Shell command.

    Returns:
        tuple: A tuple containing stdout and stderr as strings.
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return stdout.decode(), stderr.decode()
    except Exception as e:
        logging.exception("Error occurred while executing command: %s", str(e))
        return None, str(e)

async def aio_check_due_tasks():
    """
    Asynchronously check for due tasks and send notifications.

    This function checks the time difference between the current time and the scheduled time
    of each task. If a task is due soon or overdue, it sends notifications accordingly.
    """
    config = await aio_read_config()
    due_soon_secs = int(config.get('notification', 'due_soon_threshold', fallback=60))
    tasks = await aio_read_tasks()
    current_time = datetime.now()

    tasks_to_remove = []
    completed_tasks = []

    for task in tasks:
        task_name, task_time, priority = task['name'], task['time'], task['priority']
        command = extract_command(task_name)

        task_time = datetime.strptime(task_time, "%Y-%m-%d %H:%M:%S")
        time_difference = task_time - current_time

        average = int(due_soon_secs - check_frequency)
        if average < time_difference.total_seconds() <= due_soon_secs:
            await aio_send_notification("Tasky:", f"Task Due Soon\nTask: {task_name} due in {due_soon_secs} seconds")

        if time_difference <= timedelta(minutes=0):
            await aio_send_notification("Tasky:", f"Task Due\nTask: {task_name}\nTime: {task_time}\nPriority: {priority}")
            completed_tasks.append(task)
            tasks_to_remove.append(task)

            if command:
                output, error = await aio_execute_command(command)
                await aio_send_notification("Tasky:", f"Command Execution Result\nCommand: {command}\nOutput: {output}\nError: {error}")

    await aio_append_completed_tasks(completed_tasks)

    for task in tasks_to_remove:
        tasks.remove(task)

    await aio_write_tasks(tasks)


def handle_exit(signum, frame):
    """
    Signal handler for termination signals (SIGINT and SIGTERM).

    Args:
        signum (int): Signal number.
        frame (object): Frame object.
    """
    logging.info("Received termination signal. Exiting gracefully.")
    sys.exit(0)

# Set up signal handlers for graceful exit
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


async def main():
    """
    Asynchronously run the main background loop to check for due tasks periodically.
    """
    config = await aio_read_config()

    # Uncomment the line below if you want to use a different check frequency from the config
    check_frequency = int(config.get('notification', 'check_frequency_seconds', fallback=20))

    while True:
        asyncio.create_task(aio_check_due_tasks())
        await asyncio.sleep(check_frequency)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
