"""Seed (or update) the default admin user from .env.

Reads:
  ADMIN_EMAIL=admin@primexium.com
  ADMIN_PASSWORD=Admin@12345

Usage (from Backend/ with venv active):
  python -m app.scripts.seed_admin
  # or:
  python scripts/seed_admin.py
"""

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.user import User, UserRole


def seed_admin() -> None:
    email = (settings.admin_email or "").strip().lower()
    password = settings.admin_password or ""

    if not email or not password:
        raise SystemExit(
            "Set ADMIN_EMAIL and ADMIN_PASSWORD in Backend/.env before seeding."
        )

    if len(password) < 8:
        raise SystemExit("ADMIN_PASSWORD must be at least 8 characters.")

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                first_name="Primexium",
                last_name="Admin",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created admin user: {email} (role=admin)")
        else:
            user.role = UserRole.ADMIN
            user.is_active = True
            user.hashed_password = hash_password(password)
            db.add(user)
            db.commit()
            print(f"Updated existing user to admin: {email} (password reset from .env)")
    finally:
        db.close()


def main() -> None:
    seed_admin()


if __name__ == "__main__":
    main()
