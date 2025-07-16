# Use official Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies including OpenCV requirements
RUN apt-get update && apt-get install -y \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/models /app/runs/detect/train/weights

# Download YOLOv8 model
RUN curl -L https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -o /app/runs/detect/train/weights/best.pt

# Upgrade pip and install Python dependencies from requirements.txt
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy project files to container
COPY . /app

# Expose port 8000 for the application
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]
