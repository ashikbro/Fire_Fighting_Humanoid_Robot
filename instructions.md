# Instructions for Fire Fighting Humanoid Robot

This document provides instructions on how to set up and run the various components of the Fire Fighting Humanoid Robot project.

## 1. Backend Application

The backend application is built with FastAPI and serves as the central communication hub.

### Prerequisites

*   Python 3.8+
*   pip

### Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Environment**:
    *   Create a `.env` file by copying the `.env.example` file:
        ```bash
        copy .env.example .env
        ```
    *   Update the `.env` file with your specific configuration settings.

3.  **Run the Application**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

## 2. Web Dashboard

The web dashboard provides a user interface for monitoring and controlling the robot.

### Prerequisites

*   A modern web browser

### Running the Dashboard

1.  Open the `dashboard/firebot_updated_enhanced.html` file in your web browser.
2.  Ensure that the backend application is running, as the dashboard communicates with it to fetch data and send commands.

## 3. Mobile Application

The mobile application is built with Flutter and allows for remote control of the robot.

### Prerequisites

*   Flutter SDK
*   Android Studio or Xcode for building and running the app

### Setup

1.  **Navigate to the `mobile_app` directory**:
    ```bash
    cd mobile_app
    ```

2.  **Install Dependencies**:
    ```bash
    flutter pub get
    ```

3.  **Run the Application**:
    *   Connect a device or start an emulator.
    *   Run the following command:
        ```bash
        flutter run
        ```

## 4. Vision System

The vision system is a key component of the robot's autonomous operation.

### Running the Vision System

The vision system is integrated into the main application and does not need to be run separately. The `vision` module is used by the `automation` module to process images and detect fires.

## 5. Running Tests

To ensure the reliability of the system, it is important to run the tests regularly.

### Prerequisites

*   `pytest`

### Running the Tests

1.  **Install `pytest`**:
    ```bash
    pip install pytest
    ```

2.  **Run the tests**:
    ```bash
    pytest