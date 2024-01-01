# **Tasky: Efficient Task Management**

## DESCRIPTION

Tasky is an easy-to-use command-line task management tool designed to help users efficiently organize and keep track of their tasks. Whether you're a developer managing project timelines or an individual organizing personal tasks, Tasky provides a simple yet powerful solution.

### FEATURES:

  ***Foreground and Background Operation:*** Tasky operates in both foreground and background, allowing you to manage tasks seamlessly in your terminal while also receiving notifications for due tasks.

  ***Command Execution:*** Execute commands automatically when tasks containing commands are due. Integrate Tasky with your workflow by automating tasks and processes.

  ***Task Scheduling:*** Schedule tasks with specific due dates and priority levels. Tasky ensures you stay on top of your commitments by notifying you in advance.

  ***Precise Notifications and Reminders:*** Recieve notifications on as many connected devices as possible when; scheduled tasks are due, tasks are added or deleted, Passkey access is denied and when tasks are due soon (defaults to 60 seconds). Recieve command line outputs and errors as notifications for tasks containing commands. Notification channel for Tasky is Pushbullet.

  ***Customizable Options:*** Customize file destinations and paths, Customize notification settings to suit your preferences; Adjust due soon notification thresholds to desired time values in seconds. Adjust frequency of checking due tasks in the background for more precise timing.

  ***Intuitive User Interface:*** The command-line interface is designed to be user-friendly and interactive, making it easy to add, view, and manage tasks with minimal effort.

  ***Task History:*** Ability to view all completed tasks and their details.

  ***Security:*** Tasky comes with a password feature 'Passkey', to prevent unauthorized access and enhance privacy. Tasky Passkey passkey feature contains advanced functionalities such as password hashing and password resets. Tasky also notifies you when a wrong Passkey is entered and access is denied.

### Video Demo: [Tasky CLI tool](https://youtu.be/Cuu1tivU1q4?feature=shared)



## Getting Started

### INSTALLATION:

Clone the repository to a new folder `Tasky` in the home directory:

    git clone https://github.com/LouisdeMagician/tasky ~/Tasky

Navigate to the Tasky directory:

    cd Tasky

Install dependencies:

    pip install -r requirements.txt

Edit the config file to *set your Pushbullet API Access Token*:

    nano tasky.config

  Add your API key in the Pushbullet field as below:

  > *#Set your PushBullet API key*
>
  > *[Pushbullet]*
>
  > *access_token = your_pushbullet_api_key*

  Save and exit the text editor.

### CONFIGURATION:

  *Background Script.*

  (This part of the program should run as a background service to ensure uninterrupted functioning after ending terminal sessions or reboots. Manages; checking due tasks, sending notifications for due tasks, deleting and storing completed tasks in tasks history. All Asynchronously.)

  The Tasky background script configuration comes with two configuration options:

  ***OPTION 1:*** *System service setup*. Choose this option if you want Tasky background script to run locally on the host machine, having the ability to execute commands on the host terminal.

  ***OPTION 2:*** *Docker setup*. Choose this option if you want Tasky background script to run in a docker container, isolated from the host machine. It has the ability to execute limited commands on the docker environment terminal.

  **SETUPS:**

   #### OPTION 1.
   *Direct Execution on Host (System Service Setup):*

   In this setting, Users create a service file that runs the script in the background.
   The script can directly execute commands on the host machine.

   ***Step 1***. Open a terminal and navigate to the sytemd service manager directory:

        cd /etc/systemd/systems

  Create a privileged service file named 'tasky. service':

        sudo nano tasky.service

  ***Step 2***. Copy and paste the sample service file below, edit the paths and values to fit your personal user details as per instructions below:

            [Unit]
            Description=Tasky Background Service

            [Service]
            ExecStart=/usr/bin/python3 /full/path/to/your/Tasky/btasky.py
            Restart=always
            User=your_username
            Group=your_group
            WorkingDirectory=/full/path/to/your/Tasky

            [Install]
            WantedBy=multi-user.target

***Replace `full/path/to/your/Tasky/btasky.py` with the actual absolute path to the 'btasky' script in your system.***

***Replace `/full/path/to/your/Tasky` with the actual absolute path to the 'Tasky' directory on your system.***

***Replace `your_username` and `your_group` with the actual values of your username and group on your system.***

(You can use the `id` command to find out your current user and group information. Open a terminal and run:

      id

  Here's an example output:

  > uid=1000(example) gid=1000(example) groups=1000(your_group),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),116(lpadmin),126(sambashare)

  In this example, your username value (uid=1000) is 'example' and your group (gid=1000) is 'example'. Use these username and group information in your systemd service file.)

  Save and close the 'tasky.service' file.

  ***Step 3***. Reload the system manager daemon. Run the command:

      sudo systemctl daemon-reload

  ***Step 4***. Enable the newly created service and start it. Run the commands:

      sudo systemctl enable tasky.service

      sudo systemctl start tasky.service

  Now the newly created 'tasky.service' service should be running. You can check the status by running:

    sudo systemctl status tasky.service

  And view the service logs for troubleshooting any errors by running:

    journalctl -xeu tasky.service

You can start and stop the Tasky background service from running manually by running `sudo systemctl stop tasky.service` and `sudo systemctl start tasky.service`, but the service should restart automatically after every reboot.


  **How to enable sudo commands for Tasky background service (System Service setup)**:

  Open the sudoers file using the visudo command:

      sudo visudo

  Add the following line at the end of the sudoers file, replacing `your_username` and `/full/path/to/your/Tasky/btasky.py` with the appropriate values:

      your_username ALL=(ALL:ALL) NOPASSWD: /usr/bin/python3 /full/path/to/your/Tasky/btasky.py

  This line grants your user (`your_username`) the permission to run the Tasky background Python script without a password prompt.


#### OPTION 2:
*Containerized Execution (Docker Setup):*

In this setting, Users build a Docker container with a custom Tasky Kali image.

The script runs inside the container, isolated from the host machine, and commands execute within the container environment.

Install Docker If you haven't installed Docker yet, you can download and install the desktop from the official [Docker website](https://www.docker.com/) or install the docker package on your terminal: `sudo apt install docker.io` and `sudo apt install docker-compose`.

***Step 1***. Navigate to your `/Tasky` directory and pull the docker image used for the *Tasky background script* container:

    cd ~/Tasky
```
docker pull louisdemagician/tasky:1.0
```
***Step 2***. Verify that the Docker Compose yml file is present in your `Tasky` directory:

    cat docker-compose.yml

  The following content should be in the yml file, update accordingly if not accurate:
```
version: '3'
services:
 background_script:
  build:
   context: .
   dockerfile: Dockerfile
  command: ["python3", "btasky.py"]
  stdin_open: true
  tty: true
  volumes:
   - .:/Tasky
   - /etc/localtime:/etc/localtime:ro
  image: tasky_image:1.0
  privileged: true
  restart: unless-stopped
```
***Step 3***. Run the Docker container with the *tasky* image and yml configs in detached mode:

    sudo docker-compose up -d

***Step 4***. Verify *Tasky* container is running:

    sudo docker ps

You should see a container named `background_script` or `tasky_image` in the list.
Interact with *Tasky* by scheduling tasks and commands.

You can view the container logs for troubleshooting any errors by running:

    sudo docker-compose logs

And view the *Tasky* program logs for details like info, warning and errors by navigating to the `~/Tasky` directory and running:

    cat tasky_log_file.log


***Ensure that the background script is running continuously to receive notifications.***



## Usage:
***Make sure Pushbullet _API access token_ is added by editing `tasky.config` file. Do this before using *Tasky*.***

*Foreground Script*.

(This part of the program runs when called in the terminal and ends when exited, interrupted or terminal session is closed. Manages; The interactive and colorful displays on the termial, Tasky options (adding tasks, deleting tasks, viewing tasks history etc).

Run Tasky in terminal:

    python3 tasky.py

  Default Passkey is `tasky`

  Follow the prompts to add, view, and manage your tasks.

Example:

**Reset Tasky Passkey**
```
python tasky.py
```
Enter Passkey

Enter option 5, follow prompts, make sure new Passkey is at least 5 characters long.

**Schedule a task**
```
python tasky.py
```
Enter Passkey

Enter option 1, follow prompts.

***To schedule terminal commands as tasks, prefix the task with the tag `-e` or `--execute` followed by a space and the command you want to run when task time is due, verbatim.***

**View scheduled tasks**
```
python tasky.py
```
Enter Passkey

Enter option 3, follow prompts.

**Edit/Update a task**
```
python tasky.py
```
Enter Passkey

Enter option 4, follow prompts.

**Delete a task**
```
python tasky.py
```
Enter Passkey

Enter option 2, follow prompts.

**View Task History**
```
python tasky.py
```
Enter Passkey

Enter option 7, follow prompts.

**Exit Tasky**

Enter option 6 or press CTRL+C twice

### NOTES

+ ***Ensure that the devices have an internet connection to send and recieve notifications, as Pushbullet is not an offline service.***

- ***Ensure that your API Access Token still has valid notification pushes left.***

Pushbullet offers 500 pushes per month for free accounts. See [PushBullet](https://www.pushbullet.com) for more info.

- ***Tasky background script creates a log file `tasky_log.log` by default.***

This file contains logs from the *Tasky* background script process. You can change file name or path in the config file.

+ ***Tasky foreground script creates file `tasks.json` by default***

This file contains scheduled tasks in JSON format. You can customize the name and path in the config file.

- ***Tasky foreground script creates file `passkey.txt` by default***

This file contains a hash of the current user *Passkey*. You can also customize the name and path in the config file.

+ ***Tasky foreground script creates file `completed_tasks.json` by default***

This file contains the *Tasky* tasks history in JSON format. You can also customize the name and path in the config file.

- **Customize *Tasky* settings by editing the `tasky.config` file:**

   + *Set/Reset your Pushbullet API Access Token in the Pushbullet field at the bottom of `tasky.config` file.*
   + *Specify file paths if desired.*
   + *Change the value of due tasks checking frequency, (Note that while this will enhance time precision by running the loop more frequently, it leads to higher CPU usage)*
   + *Set 'Task Due Soon' notification preferences to any desired value in seconds, to suit your needs.*

+ *You can view and copy the Dockerfile used in building the tasky image [here](./Dockerfile)*


### Testing:

The project includes a comprehensive test suite to verify the functionality of key components. Run tests using the pytest command.

Run the test suite to ensure the integrity of Tasky:

    pytest test_tasky.py


## Contributing:

Feel free to contribute to Tasky by opening issues, submitting feature requests, or creating pull requests. Your feedback and contributions are highly appreciated.

## License:

This project is licensed under the MIT License - see the LICENSE file for details.
