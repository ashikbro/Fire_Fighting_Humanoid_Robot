# Raspberry Pi Deployment Guide

This guide provides specific instructions and considerations for deploying the Fire Fighting Humanoid Robot project onto a Raspberry Pi.

## 1. Hardware and System Setup

-   **[ ] Recommended Model**: Use a **Raspberry Pi 4 (4GB or 8GB model) or a Raspberry Pi 5**. The vision processing and backend server require significant memory and processing power.
-   **[ ] Power Supply**: Ensure you have a high-quality, official power supply that can provide stable power (at least 3A for Pi 4, 5A for Pi 5), especially when connecting hardware like cameras and motors.
-   **[ ] Cooling**: The Raspberry Pi will be under a heavy, continuous load. A cooling solution (e.g., a heatsink with a fan) is **essential** to prevent thermal throttling, which would severely degrade performance.
-   **[ ] Operating System**: Install **Raspberry Pi OS (64-bit)**. The 64-bit version is crucial for performance and compatibility with modern machine learning libraries.

## 2. Software and Dependencies

The most critical part of the setup is installing the correct software dependencies for the ARM architecture of the Raspberry Pi.

-   **[ ] Install Python**:
    ```bash
    sudo apt update
    sudo apt install python3-pip python3-venv -y
    ```
-   **[ ] Create a Virtual Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
-   **[ ] Install Dependencies**:
    *   **PyTorch**: The object detection model (`.pt`) requires PyTorch. You must install a version compiled for ARM64. Do **not** install it from the standard `requirements.txt`. Find the correct wheel for your Raspberry Pi OS version from the official PyTorch website or trusted sources.
    *   **OpenCV**: Installing `opencv-python` can be slow. It's often faster to install it via `apt` and then link it to your virtual environment.
        ```bash
        sudo apt install python3-opencv
        ```
    *   **Other Dependencies**: Install the remaining dependencies using the `requirements.txt` file. You may need to install some system-level libraries first.
        ```bash
        sudo apt install libatlas-base-dev
        pip install -r requirements.txt
        ```

## 3. Hardware Interfacing

-   **[ ] Camera Setup**:
    *   Connect your camera (CSI or USB).
    *   Use the `libcamera-hello` command to test that the camera is working at the OS level.
    *   You may need to adjust the `CAMERA_INDEX` in your `.env` file. It is often `0` for a single USB camera or may require a specific GStreamer pipeline string for the Pi Camera Module.
-   **[ ] Actuator and Sensor Control (Crucial)**:
    *   The current project code is high-level. You will need to write the low-level Python code to control the robot's motors and actuators via the Raspberry Pi's **GPIO pins**.
    *   Libraries like `RPi.GPIO`, `gpiozero`, or specific motor controller libraries (e.g., for an I2C motor driver) will be required.
    *   This low-level logic should be integrated into the `automation/actuator_manager.py` and `automation/fire_suppression.py` modules.

## 4. Network Configuration

-   **[ ] Set a Static IP Address**: For the mobile app to reliably connect to the robot, the Raspberry Pi must have a predictable IP address. Configure your router to assign a static IP address to the Raspberry Pi's MAC address.

## 5. Automated Startup on Boot

To have your robot's main application start automatically when the Raspberry Pi powers on, you should create a `systemd` service.

-   **[ ] Create a Service File**:
    1.  Create a file named `firebot.service` in `/etc/systemd/system/`:
        ```ini
        [Unit]
        Description=FireBot Main Application
        After=network.target

        [Service]
        User=your_username
        WorkingDirectory=/home/your_username/Fire_Fighting_Humanoid_Robot
        ExecStart=/home/your_username/Fire_Fighting_Humanoid_Robot/.venv/bin/python main.py
        Restart=always

        [Install]
        WantedBy=multi-user.target
        ```
    2.  Replace `your_username` with your actual username.
-   **[ ] Enable and Start the Service**:
    ```bash
    sudo systemctl enable firebot.service
    sudo systemctl start firebot.service
    ```

By following this guide, you will be well-prepared to configure your project on the Raspberry Pi.