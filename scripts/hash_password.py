import sys
import os
from getpass import getpass

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.auth import get_password_hash

def main():
    """
    A simple script to hash a password and append it to the users.txt file.
    """
    users_file_path = os.path.join(os.path.dirname(__file__), '..', 'users.txt')

    # Get user input
    username = input("Enter username: ")
    password = getpass("Enter password: ")
    role = input("Enter role (e.g., admin, operator): ")

    # Hash the password
    hashed_password = get_password_hash(password)

    # Append the new user to the users.txt file
    with open(users_file_path, "a") as f:
        f.write(f"{username}:{hashed_password}:{role}\n")

    print(f"User '{username}' added successfully to {users_file_path}")

if __name__ == "__main__":
    main()