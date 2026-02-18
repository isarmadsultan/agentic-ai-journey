import sqlite3
import re
from getpass import getpass

from db import bootstrap, connect
from common import hash_password

def validate_email(email):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Password must be at least 8 characters"""
    return len(password) >= 8

def create_user_account():
    """Create a new user account"""
    print("=== User Account Creator ===\n")

    bootstrap()
    
    # Get user information
    name = input("Enter your name: ").strip()
    if not name:
        print("Error: Name cannot be empty!")
        return False
    
    # Get and validate email
    while True:
        email = input("Enter your email: ").strip()
        if not validate_email(email):
            print("Error: Invalid email format. Please try again.")
            continue
        break
    
    # Get and validate password
    while True:
        password = getpass("Enter password (min 8 characters): ")
        if not validate_password(password):
            print("Error: Password must be at least 8 characters!")
            continue
        
        password_confirm = getpass("Confirm password: ")
        if password != password_confirm:
            print("Error: Passwords don't match!")
            continue
        break
    
    # Hash the password
    password_hash = hash_password(password)
    
    # Connect to database
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Insert user into database
        cursor.execute('''
            INSERT INTO USER (name, email, password_hash)
            VALUES (?, ?, ?)
        ''', (name, email, password_hash))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        print(f"\n✓ Account created successfully!")
        print(f"User ID: {user_id}")
        print(f"Name: {name}")
        print(f"Email: {email}")
        
        conn.close()
        return True
        
    except sqlite3.IntegrityError:
        print("\nError: This email is already registered!")
        return False
    except sqlite3.OperationalError as e:
        print(f"\nError: Database not found. Please run the database creation script first.")
        print(f"Details: {e}")
        return False
    except Exception as e:
        print(f"\nError creating account: {e}")
        return False

if __name__ == "__main__":
    create_user_account()
