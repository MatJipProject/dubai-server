# crud.py
from app.users.schema import auth_schema as schemas

# 인메모리 DB 대용
fake_users_db = {}

def get_user_by_username(username: str):
    if username in fake_users_db:
        return fake_users_db[username]
    return None

def create_user(user: schemas.UserCreate, hashed_password: str):
    db_user = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password
    }
    fake_users_db[user.username] = db_user
    return db_user