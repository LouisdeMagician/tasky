# Import necessary modules for the foreground script
import sys
import json
import hashlib
import asyncio
import schedule
import configparser
from pyfiglet import Figlet
from rich.table import Table
from datetime import datetime
from rich.console import Console
from pushbullet import Pushbullet

# Initialize Rich Console for styling output
console = Console()

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

# Read configuration from the file
config = read_config()

# Get paths from the configuration
tasks_file = config.get('paths', 'tasks_file', fallback='default_tasks_file')
completed_tasks_file = config.get('paths', 'completed_tasks_file', fallback='default_due_tasks.json')


# Custom JSON Encoder for handling datetime objects
class TaskEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return super().default(obj)


def sort_tasks(tasks):
    """
    Sort the list of tasks based on time and priority.

    Args:
        tasks (list): List of tasks.

    Returns:
        list: Sorted list of tasks.
    """
    if isinstance(tasks, list):
        # If tasks is a list, sort it by values
        sorted_tasks = sorted(
            tasks,
            key=lambda x: (
                x['time'],
                int(x['priority'])
            )
        )
    else:
        # Handle other cases as needed
        sorted_tasks = []

    return sorted_tasks


def load_tasks():
    """
    Load tasks from the tasks file or create an empty list.

    Returns:
        list: Loaded or newly created list of tasks.
    """
    try:
        with open(tasks_file, "r") as file:
            tasks = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        tasks = []
    return sort_tasks(tasks)


def load_due_tasks():
    """
    Load completed tasks from the completed tasks file or create an empty list.

    Returns:
        list: Loaded or newly created list of completed tasks.
    """
    try:
        with open(completed_tasks_file, "r") as file:
            completed_tasks = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        completed_tasks = []
    return completed_tasks

# Load tasks and completed tasks at the start of the program
tasks = load_tasks()
completed_tasks = load_due_tasks()


def send_notification(title, body):
    """
    Send a notification using Pushbullet.

    Args:
        title (str): Notification title.
        body (str): Notification body.
    """
    config = read_config()
    access_token = config.get('Pushbullet', 'access_token', fallback=None)

    try:
        if access_token:
            pb = Pushbullet(access_token)
            pb.push_note(title, body)
        else:
            console.print("Pushbullet access token not found in the config file.", style="bold red")
            pass
    except Exception:
        console.print("Error sending notification. Check internet connection, API key push limit and pushbullet.com to troubleshoot", style="bold red")


def save_tasks():
    """
    Save tasks to the tasks file.

    Note:
        Sends an error notification if saving fails.
    """
    try:
        with open(tasks_file, "w") as file:
            if tasks:
                sorted_tasks = sort_tasks(tasks)
                json.dump(sorted_tasks, file, cls=TaskEncoder)
            else:
                console.print("No tasks to save.", style="bold yellow")
    except (PermissionError, FileNotFoundError):
        send_notification("Tasky:", "Error:\nUnable to save tasks. Check file permissions and try again.")
        console.print("Error: Unable to save tasks. Check file permissions and try again.", style="bold red")


# Function to hash the passkey using SHA-256
def hash_passkey(passkey):
    """
    Hash the user's passkey using SHA-256.

    Args:
        passkey (str): User's passkey.

    Returns:
        str: Hashed passkey.
    """
    hashed_passkey = hashlib.sha256(passkey.encode()).hexdigest()
    return hashed_passkey


# Function to authenticate the user
def authenticate_user():
    """
    Authenticate the user using a hashed passkey.

    Note:
        Exits the program after three unsuccessful attempts.

    Raises:
        SystemExit: If authentication fails after three attempts.
    """
    stored_hashed_passkey = load_hashed_passkey()

    for _ in range(3):
        entered_passkey = console.input("[bold white]\nEnter Passkey[bold white]: ").strip()
        hashed_entered_passkey = hash_passkey(entered_passkey)

        if hashed_entered_passkey == stored_hashed_passkey:
            return
        send_notification("Tasky:", "Passkey Authentication Failed!")
        console.print("Incorrect Passkey", style="bold red")

    send_notification("Tasky:", "Passkey; Access Denied!")
    console.print("Access Denied", style="bold red")
    sys.exit()


def get_option():
    """
    Get the user-selected option.

    Returns:
        int: User-selected option.

    Raises:
        SystemExit: If an invalid option is entered after seven attempts.
    """
    for _ in range(7):
        option = console.input("[bold white]\nSelect Option[bold white]: ")
        if option.isdigit():
            return int(option)
        console.print("Invalid Option, Try again", style="bold red")
        if _ == 6:
            sys.exit()


def get_task():
    """
    Get task details from the user.

    Returns:
        tuple: Tuple containing task name, task time, and priority level.
    """
    console.print("Schedule Task", style="bold white underline")
    console.print("*Datetime inputs should be in (YYYY-MM-DD HH:MM) format, time defaults to 00:00 if only date is given.", style="italic bold yellow")

    while True:
        task = console.input("[bold white]Input Task[bold white]: ").strip()
        task_time = console.input("[bold white]Task Time[bold white]: ").strip()
        priority = console.input("[bold white]Task Priority (1 for High, 2 for Medium, 3 for Low)[bold white]: ").strip()

        if not task or not priority:
            console.print("Task and Priority fields cannot be empty", style="bold red")
            continue

        if not priority.isdigit() or int(priority) not in {1, 2, 3}:
            console.print("Invalid priority level. Choose 1 for High, 2 for Medium, or 3 for Low.", style="bold red")
            continue

        return task, task_time, int(priority)


def convert_to_consistent_format(user_task_time, time_format):
    """
    Convert user-provided task time to a consistent datetime format.

    Args:
        user_task_time (str): User-provided task time.
        time_format (str): Format of the desired datetime.

    Returns:
        datetime: Consistent datetime object.
    """
    # Define a list of possible time formats to try
    time_formats = ['%Y-%m-%d %H:%M', '%H:%M', '%Y-%m-%d', '%I:%M %p', '%I %p']

    for time_format in time_formats:
        try:
            # Try parsing the user input with the specified time format
            task_datetime = datetime.strptime(user_task_time, time_format)

            # Check if user time is already in full datetime format and return a date object version of user time
            if time_format == '%Y-%m-%d %H:%M':
                return task_datetime

            # If the format includes only time, add the current date
            elif '%H:%M' in time_format or '%I:%M %p' in time_format or '%I %p' in time_format:
                # Get the current date components
                current_date = datetime.now().date()

                # Set the date components to the current date
                task_datetime = task_datetime.replace(
                    year=current_date.year,
                    month=current_date.month,
                    day=current_date.day
                )

            return task_datetime

        except ValueError:
            # If parsing fails with the current format, try the next one
            continue

    # If none of the formats work, return None or raise an exception
    return None


def time_is_valid(user_task_time):
    """
    Check if the user-provided task time is valid (in the future and in the correct format).

    Args:
        user_task_time (str): User-provided task time.

    Returns:
        bool: True if the time is valid, False otherwise.
    """
    # Specify the time format to use for validation
    time_format =  '%Y-%m-%d %H:%M'

    task_datetime = convert_to_consistent_format(user_task_time, time_format)

    if task_datetime is None:
        return False

    # Get the current datetime
    current_datetime = datetime.now()

    # Compare the user's task time with the current time
    return task_datetime > current_datetime


def add_task():
    """
    Add a new task to the task list.

    Notes:
        Exits the function call after three unsuccessful attempts to add a valid task.
    """
    for _ in range(3):
        new_task, task_time, priority = get_task()
        if time_is_valid(task_time):
            console.print("Valid....", style="dim bold green")
            pass
        # Verify task before adding to task list
        console.print(f'[bold white]\nYour Task[bold white]: [dim bold white italic underline]{new_task}[dim bold white italic underline]')
        console.print(f'[bold white]Your Task Time[bold white]: [dim bold white italic underline]{task_time}[dim bold white italic underline]')
        console.print(f'[bold white]Priority Level[bold white]: [dim bold white italic underline]{priority}[dim bold white italic underline]')
        confirm_task = console.input("[bold white]Confirm to add task? (Default is Yes)[bold white] [bold italic yellow]Y/N[bold italic yellow]: ").strip().lower()

        if confirm_task == "n":
            continue

        if not time_is_valid(task_time):
            console.print(f"[bold red]Invalid time[bold red]. ([bold italic white]{task_time}[bold italic white]) [bold red]Please make sure time is in the future and in correct format.[bold red]")
            continue
        elif not confirm_task or confirm_task == "y":
            add_task_to_list(new_task, task_time, priority)
            console.print(f"[bold green]Task:[bold green] [bold italic white]{new_task}[bold italic white] [bold green]added successfully![bold green]")
            send_notification("Tasky:", f"New Task Added!\nTask: {new_task}\nTime: {task_time}\nPriority Level: {priority}")
            break

    save_tasks()


def add_task_to_list(task, task_time, priority):
    """
    Add a new task to the tasks list.

    Args:
        task (str): Task name.
        task_time (str): Task time.
        priority (int): Task priority level.
    """
    task = task.strip()
    task_time = task_time.strip()

    # Specify the time format to be used
    time_format = "%Y-%m-%d %H:%M"  # You can adjust this format based on your needs

    # Convert the task time to a consistent format
    converted_datetime = convert_to_consistent_format(task_time, time_format)

    # Convert the task datetime back to string before adding to dictionary
    datetime_str = converted_datetime.strftime("%Y-%m-%d %H:%M:%S")

    # Create a dictionary for the new task
    new_task = {"name": task, "time": datetime_str, "priority": priority}

    tasks.append(new_task)


def display_tasks():
    """
    Display the current tasks in a formatted table.
    """
    table = Table(title="Current Tasks\n", title_style="bold magenta underline", show_lines=True, show_edge=False)
    table.add_column("Index", style="bold white")
    table.add_column("Task", style="bold white")
    table.add_column("Time", style="bold white")
    table.add_column("Priority Level", style="bold white")

    if not tasks:
        console.print("No tasks available.", style="bold white")
    else:
        sorted_tasks = sort_tasks(tasks)

        for idx, task_data in enumerate(sorted_tasks, start=1):
            task = task_data['name']
            task_time = task_data['time']
            priority = task_data['priority']

            table.add_row(
                str(idx),
                task,
                task_time,
                str(priority)
            )

        console.print(table)


def delete_task():
    """
    Delete a task based on user input (index or task name).
    """
    display_tasks()

    # Get user input for task deletion
    user_input = console.input("[bold white]\nEnter the index or name of the task to delete[bold white]: ").strip()

    sorted_tasks = sort_tasks(tasks)
    # Validate user input
    if user_input.isdigit():
        index = int(user_input)
        if 1 <= index <= len(tasks):
            task_to_delete = sorted_tasks[index - 1]["name"]
            confirm_deletion = console.input(f"[bold yellow]Confirm to delete task[bold yellow] '[italic white]{task_to_delete}[italic white]' [italic bold yellow]? (Y/N)[italic bold yellow]: ").strip().lower()
            if confirm_deletion == 'y':
                del tasks[index - 1]
                send_notification("Tasky:", f"Task: '{task_to_delete}' deleted!")
                console.print(f"[bold green]Task '[italic white]{task_to_delete}[italic white]' [bold green]deleted[bold green].")
            else:
                console.print("Deletion canceled.", style="bold green")
        else:
            console.print("Invalid index. Please enter a valid index.", style="bold red")
    elif any(task['name'] == user_input for task in tasks):
        confirm_deletion = console.input(f"[bold yellow]Confirm to delete task[bold yellow] '[italic white]{user_input}[italic white]' [italic bold yellow]? (Y/N)[italic bold yellow]: ").strip().lower()
        if confirm_deletion == 'y':
            tasks[:] = [task for task in tasks if task['name'] != user_input]
            console.print(f"[bold green]Task[bold green] '[italic white]{user_input}[italic white]' [bold green]deleted.[bold green]")
        else:
            console.print("Deletion canceled.", style="bold green")
    else:
        console.print("Invalid input. Please enter a valid index or task name.", style="bold red")
    save_tasks()


def preview_tasks():
    """
    Display a preview of the tasks in a formatted table.
    """
    table = Table(title="Task Preview\n", title_style="bold magenta underline", show_lines=True, show_edge=False)
    table.add_column("Index", style="bold white")
    table.add_column("Task", style="bold white")
    table.add_column("Time", style="bold white")
    table.add_column("Priority Level", style="bold white")

    if not tasks:
        console.print("No tasks available.", style="bold white")
    else:
        sorted_tasks = sort_tasks(tasks)

        for idx, task_data in enumerate(sorted_tasks, start=1):
            task = task_data['name']
            task_time = task_data['time']
            priority = task_data['priority']

            table.add_row(
                str(idx),
                task,
                task_time,
                str(priority)
            )

        console.print(table)


def update_task():
    """
    Update a task based on user input (index or task name).
    """
    display_tasks()

    for _ in range(3):
        # Get user input for task update
        user_input = console.input("[bold white]\nEnter the index or name of the task to update[bold white]: ").strip()

        sorted_tasks = sort_tasks(tasks)
        # Validate user input
        if user_input.isdigit():
            index = int(user_input)
            if 1 <= index <= len(tasks):
                task_to_update = sorted_tasks[index - 1]['name']
                console.print(f"[bold green]Updating[bold green] [italic white]{index}. {task_to_update}[italic white][green]...[green]")
                update_task_details(task_to_update)
                break
            else:
                console.print("Invalid index. Please enter a valid index.", style="bold red")
                continue
        elif user_input in [task['name'] for task in tasks]:
            console.print(f"[bold green]Updating[bold green] [italic white]{user_input}[italic white][bold green]...[bold green]")
            update_task_details(user_input)
            save_tasks()
            break
        else:
            console.print("Invalid input. Please enter a valid index or task name.", style="bold red")
            continue


def update_task_details(task_name):
    """
    Update details of a specific task.

    Args:
        task_name (str): Name of the task to be updated.
    """
    # Get updated details from the user
    updated_task_name = console.input("[bold white]Enter updated task name [italic](press Enter to keep the same)[italic][bold white]: ").strip()
    for _ in range(5):
        updated_task_time = console.input("[bold white]Enter updated task time[bold white] [italic](press Enter to keep the same)[italic]: ").strip()
        time_format = "%Y-%m-%d %H:%M"
        if updated_task_time and time_is_valid(updated_task_time):
            updated_task_time = convert_to_consistent_format(updated_task_time, time_format)
            # Convert the task datetime back to string before adding to dictionary
            updated_task_time = updated_task_time.strftime("%Y-%m-%d %H:%M:%S")
            break
        elif updated_task_time == "":
            break
        else:
            updated_task_time = tasks[tasks.index(next(task for task in tasks if task['name'] == task_name))]['time']
            console.print(f"Invalid time. Please make sure time is in the future and in correct format.", style="bold red")
            continue
    updated_priority = console.input("[bold white]Enter updated priority ([italic]press Enter to keep the same[italic])[bold white]: ").strip()

    confirm_update = console.input(f"[bold yellow]Confirm to update task?[bold yellow] [italic bold white]'{task_name}'[italic bold white]: [bold yellow](Default is Y)[bold yellow] [italic bold yellow]Y/N[italic bold yellow]: ").strip().lower()
    if not confirm_update or confirm_update == "y":

        # If user entered only an updated time or priority, keep the existing values for other details
        updated_task_time = updated_task_time or next(task for task in tasks if task['name'] == task_name)['time']
        updated_priority = updated_priority or next(task for task in tasks if task['name'] == task_name)['priority']

        # Update the task with the provided details
        tasks[tasks.index(next(task for task in tasks if task['name'] == task_name))] = {
            'name': updated_task_name or task_name,
            'time': updated_task_time,
            'priority': updated_priority,
        }

        send_notification("Tasky:", f"Task: {task_name} updated!")
        console.print(f"[bold green]Task[bold green] [italic bold white]'{task_name}'[italic bold white] [bold green]updated![bold green]")
    else:

        console.print("Task update cancelled.", style="bold green")


# Function to load hashed passkey from a file
def load_hashed_passkey():
    """
    Load the hashed passkey from the passkey.txt file.

    Returns:
        str: Hashed passkey.
    """
    try:
        with open("passkey.txt", "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        # If file not found, use a default passkey and hash it
        return hash_passkey("tasky")


# Function to save hashed passkey to a file
def save_hashed_passkey(passkey):
    """
    Save the hashed passkey to the passkey.txt file.

    Args:
        passkey (str): Passkey to be hashed and saved.
    """
    with open("passkey.txt", "w") as file:
        file.write(passkey)


# Update passkey function
def update_passkey():
    """
    Update the passkey based on user input.
    """
    for trials in range(4):
        if trials == 3:
            # Exit if maximum trials reached
            send_notification("Tasky:", "Passkey update failed! Try again later.")
            console.print("Passkey update failed! Try again later.", style="bold red")
            console.print("\nExiting Program...", style="bold blue")
            sys.exit()

        current_passkey = console.input("[bold white]Enter the current passkey[bold white]: ").strip()
        stored_hashed_passkey = load_hashed_passkey()

        if hash_passkey(current_passkey) == stored_hashed_passkey:
            for tries in range(4):
                if tries == 3:
                    # Exit if maximum trials reached
                    send_notification("Tasky:", "Invalid new passkey. Passkey Update failed!")
                    console.print("Passkey update failed! Try again later.", style="bold red")
                    console.print("\nExiting Program...", style="bold blue")
                    sys.exit()

                new_passkey = console.input("[bold white]Enter a new passkey[bold white]: ").strip()

                if not new_passkey or len(new_passkey) < 5:
                    console.print("Invalid passkey. Passkey must be at least 5 characters long.", style="bold red")
                    new_passkey = current_passkey
                    continue
                elif len(new_passkey) >= 5:
                    # Save the new hashed passkey
                    save_hashed_passkey(hash_passkey(new_passkey))
                    console.print("Passkey updated successfully!", style="bold green")
                    send_notification("Tasky:", "Passkey Updated successfully!")
                    break

        elif hash_passkey(current_passkey) != stored_hashed_passkey:
            # Notify if current passkey is incorrect
            #send_notification("Tasky:", "Incorrect passkey. Passkey Update failed!")
            console.print("Incorrect passkey! Try again.", style="bold red")
            continue


# Define a function to handle program exit
def exit_program():
    """
    Exit the program.
    """
    console.print("Exiting program....\n", style="bold blue")
    sys.exit()


def view_past_tasks():
    """
    Display a table of completed tasks.
    """
    table = Table(title="Completed Tasks\n", title_style="bold magenta underline", show_lines=True, show_edge=False)
    table.add_column("Index", style="bold white")
    table.add_column("Task", style="bold white")
    table.add_column("Date", style="bold white")
    table.add_column("Priority Level", style="bold white")

    if not completed_tasks:
        console.print("Tasks History is empty.", style="bold white")
    else:
        sorted_tasks = sort_tasks(completed_tasks)

        for idx, task_data in enumerate(sorted_tasks, start=1):
            task = task_data['name']
            task_time = task_data['time']
            priority = task_data['priority']

            table.add_row(
                str(idx),
                task,
                task_time,
                str(priority)
            )

        console.print(table)


async def main():
    # Run scheduled jobs
    schedule.run_pending()

    try:
        # Display Tasky ASCII art and introduction
        f = Figlet(font='graffiti')
        intro_f = (f.renderText("      TASKY"))
        console.print(intro_f, style="bold blue")
        console.print("_._AN EFFICIENT INTERACTIVE C.L.I TOOL FOR TASK MANAGEMENT_._", style="dim bold black")
        console.print("-Schedule reminders as tasks[bold black]...[bold black]", style="italic bold black")
        console.print("-Schedule terminal commands as tasks[bold black]...[bold black]", style="italic bold black")
        console.print("-Receive precise notifications when task time is due[bold black]...[bold black]", style="italic bold black")
        console.print("-Receive terminal command outputs and errors as notifications[bold black]...[bold black]", style="italic bold black")
        console.print("-Set Task Due Soon notifications to desired values in seconds[bold black]...[bold black]", style="italic bold black")
        console.print("\n**Setup Pushbullet API Access Token in .config_file before use", style="bold yellow")
        console.print("**Default Passkey is 'tasky'. Select Option 5 to update passkey.", style="bold yellow")

        # Authenticate user using passkey
        authenticate_user()

        while True:
            # Display available options
            f = Figlet(font='term')
            options_f = f.renderText("\nOPTIONS")
            console.print(options_f, style="bold white underline")
            console.print("1: Add Task", style="bold magenta")
            console.print("2: Delete Task", style="bold magenta")
            console.print("3: Preview Tasks", style="bold magenta")
            console.print("4: Update Task", style="bold magenta")
            console.print("5: Change Passkey", style="bold magenta")
            console.print("6: Exit Program", style="magenta")
            console.print("7: View Task History", style="bold magenta")

            # Mapping user options to corresponding functions
            option_functions = {
                1: add_task,
                2: delete_task,
                3: preview_tasks,
                4: update_task,
                5: update_passkey,
                6: exit_program,
                7: view_past_tasks,
            }

            for _ in range(3):
                user_option = get_option()
                if user_option in option_functions:
                    option_name = {
                        1: "Add Task",
                        2: "Delete Task",
                        3: "Preview Tasks",
                        4: "Update Task",
                        5: "Change Passkey",
                        6: "Exit",
                        7: "View Task History"
                    }[user_option]

                    console.print(f"[bold blue]Executing[bold blue]: [bold magenta]{option_name}....[bold magenta]\n")
                    option_functions[user_option]()
                    break
                elif user_option == 6:
                    console.print("Exiting program....\n", style="blue")
                    break  # Break out of the loop to exit the program

                else:
                    console.print("Invalid option. Please choose a valid option.", style="bold red")
                    continue

            # Run scheduled jobs after the loop
            schedule.run_pending()

    except KeyboardInterrupt:
        console.print("\nProgram interrupted. Exiting...\n", style="bold blue")
        sys.exit()


if __name__ == "__main__":
    asyncio.run(main())
