# Use the Kali Linux base image
FROM kalilinux/kali-rolling

# Update package manager repositories and install Tini
RUN apt-get update --fix-missing && apt-get install -y \
 python3 \
 python3-pip \
 tini \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /Tasky

# Copy the current directory contents into the container at /Tasky
COPY btasky.py .
COPY tasky.config .
COPY tasks.json .
COPY completed_tasks.json .
COPY tasky_log_file.log .
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run the background script
CMD ["python3", "btasky.py"]
