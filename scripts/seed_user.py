import os
import random
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash

from database.db import get_db


FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Reyansh", "Krishna", "Ishaan",
    "Rahul", "Rohan", "Karan", "Siddharth", "Aryan", "Yash", "Vikram",
    "Aman", "Nikhil", "Pranav", "Harsh", "Manish", "Ravi", "Suresh",
    "Anand", "Deepak", "Sanjay", "Rajesh", "Amit", "Sourav", "Kabir",
    "Aanya", "Diya", "Saanvi", "Anika", "Myra", "Pari", "Aadhya",
    "Priya", "Pooja", "Neha", "Riya", "Sneha", "Kavya", "Ananya",
    "Meera", "Lakshmi", "Sita", "Divya", "Shruti", "Kriti", "Isha",
    "Rohini", "Nisha", "Anjali", "Swati", "Tanvi", "Ishita", "Aishwarya",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Agarwal", "Mishra", "Tiwari", "Pandey",
    "Singh", "Yadav", "Kumar", "Chauhan", "Rathore", "Shekhawat",
    "Patel", "Shah", "Desai", "Mehta", "Joshi", "Trivedi",
    "Reddy", "Naidu", "Rao", "Chowdary", "Nair", "Menon", "Pillai",
    "Iyer", "Iyengar", "Krishnan", "Subramanian",
    "Banerjee", "Chatterjee", "Mukherjee", "Bose", "Sen", "Ghosh", "Das",
    "Khan", "Ahmed", "Ali", "Hussain", "Sayyad",
    "Deshmukh", "Patil", "Kulkarni", "Bhosale", "Jadhav",
    "Bhat", "Shetty", "Hegde", "Kamath",
]

EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]


def generate_user():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    suffix = random.randint(10, 999)
    domain = random.choice(EMAIL_DOMAINS)
    email = f"{first.lower()}.{last.lower()}{suffix}@{domain}"
    return name, email


def email_exists(conn, email):
    row = conn.execute(
        "SELECT 1 FROM users WHERE email = ?", (email,)
    ).fetchone()
    return row is not None


def main():
    conn = get_db()
    try:
        while True:
            name, email = generate_user()
            if not email_exists(conn, email):
                break

        password_hash = generate_password_hash("password123")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash, created_at) "
                "VALUES (?, ?, ?, ?)",
                (name, email, password_hash, created_at),
            )
            user_id = cursor.lastrowid

        print(f"id:    {user_id}")
        print(f"name:  {name}")
        print(f"email: {email}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
