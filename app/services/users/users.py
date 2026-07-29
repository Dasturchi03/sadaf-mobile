from app.repositories.users import users as rp


async def get_user(user_id: int = None, username: str = None):
    return await rp._get_user(user_id=user_id, username=username)


async def get_users():
    return await rp._get_users()
