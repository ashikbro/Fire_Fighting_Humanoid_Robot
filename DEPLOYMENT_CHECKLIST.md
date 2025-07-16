# Deployment Checklist

This document provides the final checklist of critical steps required to take the Fire Fighting Humanoid Robot project from its current advanced state to a fully deployment-ready production environment.

## 1. Final Configuration and Secrets Management

-   **[ ] Create a `.env` file**: Copy the `.env.example` file to a new `.env` file.
-   **[ ] Generate a Secure API Key**: Replace the placeholder `"your_secret_api_key"` in your new `.env` file with a strong, randomly generated secret key.
-   **[ ] Set Production Environment Variables**: Ensure all other variables in the `.env` file (like `DEBUG=False`) are correctly set for a production environment.

## 2. Security Hardening

-   **[ ] Restrict CORS Origins**: In `app/api/main.py`, change `allow_origins=["*"]` to the specific domain of your web dashboard (e.g., `allow_origins=["http://your-dashboard-domain.com"]`). This is critical to prevent unauthorized websites from accessing your API.
-   **[ ] Implement Real User Authentication**: In `app/api/main.py`, replace the placeholder `admin`/`admin` credentials in the `/token` endpoint with a secure user authentication system that hashes and stores user passwords in a database.
-   **[ ] Configure Release Signing for Android**: Before publishing the mobile app, you must generate a private signing key and configure the `mobile_app/android/app/build.gradle.kts` file to use it for release builds. This is essential for app store submission and security.

## 3. Production-Grade Application Serving

-   **[ ] Use a Production WSGI Server**: The instructions currently use `uvicorn` with `--reload`, which is for development only. For production, run the backend application using a robust WSGI server like `gunicorn`.
    *   Example command: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.api.main:app`
-   **[ ] Consider a Database Migration**: The current SQLite database is suitable for small-scale use. If you anticipate a high volume of data or concurrent users, plan to migrate to a more robust database like PostgreSQL.

## 4. Final Cleanup and Testing

-   **[ ] Remove Redundant Directories**: If you haven't already, run the commands provided in the `instructions.md` file to remove the legacy `src` and `mobile_app/app` directories.
-   **[ ] Run a Full Test Suite**: Execute all tests one last time using `pytest` to ensure that all recent changes are stable and have not introduced regressions.
-   **[ ] Real-World Hardware Testing**: The most critical step is to test the entire system with the actual robot hardware in a controlled but realistic environment. Verify that all sensors, navigation, and fire-suppression systems function as expected.

Once you have completed all the items on this checklist, your project will be fully hardened and ready for a production deployment.