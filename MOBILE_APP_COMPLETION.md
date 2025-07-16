# Mobile App Completion Guide

This guide provides the final steps to build and prepare the FireBot mobile app for real-world use.

## 1. Configure the Server IP Address

Before building the final version, you must ensure the app knows how to connect to the robot's backend server.

-   **[ ] Launch the app on a test device or emulator.**
-   **[ ] Navigate to the Settings screen.**
-   **[ ] Enter the static IP address of your Raspberry Pi** (or wherever the backend server is running) and save it. The app will store this address for all future connections.

## 2. Build the Release Version for Android (APK)

An APK is the file format used by Android for distributing and installing mobile apps.

-   **[ ] Open a terminal in the `mobile_app` directory.**
-   **[ ] Run the following command:**
    ```bash
    flutter build apk --release
    ```
-   **[ ] Locate the APK file.** Once the build is complete, you will find the release APK file in the following directory:
    `mobile_app/build/app/outputs/flutter-apk/app-release.apk`
-   **[ ] Install on an Android device.** You can now copy this `app-release.apk` file to any Android device to install and run the app.

## 3. Build the Release Version for iOS (IPA) - Optional

If you plan to run the app on an iPhone or iPad, you will need to build an IPA file. This process requires a Mac with Xcode installed.

-   **[ ] Open the `mobile_app/ios` directory in Xcode.**
-   **[ ] Configure code signing.** In Xcode, you must select a development team and configure the code signing settings for the "Runner" target. This is required by Apple to run apps on physical devices.
-   **[ ] Run the build command.** In a terminal on your Mac, navigate to the `mobile_app` directory and run:
    ```bash
    flutter build ipa --release
    ```
-   **[ ] Distribute the app.** The generated IPA file can be found in the `build/ios/ipa/` directory and can be distributed through methods like Apple's TestFlight or Ad Hoc deployment.

## 4. Final Testing

-   **[ ] Install the release build on a physical device.**
-   **[ ] Test all features thoroughly**, including the live video stream, manual controls, and notifications, to ensure everything works as expected when connected to the actual robot.

Once you have completed these steps, your mobile application will be fully configured and ready for use in the field.