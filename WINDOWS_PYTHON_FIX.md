# How to Fix "python is not recognized" on Windows

This guide provides the steps to fix the "python is not recognized" error in your terminal. This happens when the Windows operating system cannot find your Python installation.

## Step 1: Find Your Python Installation Path

First, you need to find where Python is installed on your computer.

1.  Open the Start Menu and type `Python`.
2.  Right-click on the Python application that appears (e.g., "Python 3.1x") and select **"Open file location"**.
3.  This will open a File Explorer window with a shortcut to Python. Right-click on the shortcut and select **"Open file location"** again.
4.  A new File Explorer window will open. This is your Python installation directory. **Copy this path** from the address bar (e.g., `C:\Users\YourUser\AppData\Local\Programs\Python\Python311`).
5.  In the same directory, you will see a `Scripts` folder. Open it and **copy the path to the `Scripts` folder** as well (e.g., `C:\Users\YourUser\AppData\Local\Programs\Python\Python311\Scripts`).

## Step 2: Add Python to Your System's PATH

Now you need to tell Windows where to find Python.

1.  In the Start Menu, search for and open **"Edit the system environment variables"**.
2.  In the window that appears, click the **"Environment Variables..."** button.
3.  In the "System variables" section (the bottom box), find the variable named **`Path`**, select it, and click **"Edit..."**.
4.  Click **"New"** and paste the first path you copied (the main Python installation directory).
5.  Click **"New"** again and paste the second path you copied (the `Scripts` folder path).
6.  Click **"OK"** on all the windows to save the changes.

## Step 3: Relaunch and Run the Project

**This is a critical step.** You must close your current terminal and open a new one for the changes to take effect.

1.  **Close your current terminal window.**
2.  **Open a new terminal** in your project directory (`C:\project\Fire_Fighting_Humanoid_Robot`).
3.  Now, run the final commands to launch your project:

    ```bash
    # First, install the required packages
    python -m pip install -r requirements.txt

    # Then, run the production server
    python -m waitress --host=0.0.0.0 --port=8000 app.api.main:app
    ```

After following these steps, your environment will be correctly configured, and your project will launch successfully.