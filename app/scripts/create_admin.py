"""Promote a user to admin by email.

Usage (from Backend/ with venv active):
  python -m app.scripts.create_admin you@example.com
"""

import sys

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.user import User, UserRole


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.scripts.create_admin <email>")
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"No user found with email: {email}")
            print("Register the account first, then run this command again.")
            sys.exit(1)
        user.role = UserRole.ADMIN
        user.is_active = True
        db.commit()
        print(f"Updated {email} to role=admin")
    finally:
        db.close()


if __name__ == "__main__":
    main()
