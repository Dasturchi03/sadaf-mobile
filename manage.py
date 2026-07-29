import asyncio
from argparse import ArgumentParser
from app.models.users.users import Users
from app.core.db import session_manager
from app.db.init_db import create_db
from app.utils.deps.auth import auth_handler


def add_user(username: str, password: str):
    while not username:
        username = input("Enter username: ")
    with session_manager() as db:
        user = Users()
        user.username = username
        user.password = auth_handler.get_password_hash(password)

        db.add(user)
        try:
            db.commit()
            print("✅ User added successfully!")
        except Exception as err:
            db.rollback()
            print(f"❌ Error adding user: {err}")


def main():
    parser = ArgumentParser(description="Create new user")
    parser.add_argument('-u', '--username', type=str, help="Username for new user")
    parser.add_argument('-p', '--password', type=str, default="12345", help="Password (default: 12345)")
    parser.add_argument('-db', '--createdb', action='store_true', help="Create database tables")
    args = parser.parse_args()

    if args.createdb:
        asyncio.run(create_db())
    else:
        add_user(username=args.username, password=args.password)


if __name__ == "__main__":
    main()
