# Use official Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies from requirements.txt
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --resume-retries 5 -r /app/requirements.txt

# Copy project files to container
COPY . /app

# Expose port 5000 for Flask app
EXPOSE 8080

# Command to run the application
CMD ["python", "main.py"]
