import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password, normalize_email
from app.db.session import SessionLocal
from app.models.user import User


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local platform user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    email = normalize_email(args.email)
    password = getpass("Password: ")
    password_confirmation = getpass("Confirm password: ")

    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    if password != password_confirmation:
        raise SystemExit("Passwords do not match.")

    with SessionLocal() as db:
        existing_user = db.scalar(select(User).where(User.email == email))
        if existing_user is not None:
            raise SystemExit("A user with this email already exists.")

        user = User(
            email=email,
            display_name=args.name.strip(),
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        print(f"Created user {email}.")


if __name__ == "__main__":
    main()
