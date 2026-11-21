
import os
from datetime import datetime, timedelta, timezone

import jwt

from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is missing")

ALGORITHM = "HS256"

TOKEN_EXPIRE_MINUTES = 60

# Password hashing
password_hash = PasswordHash.recommended()


# Hash password
def hash_password(password: str) -> str:

    return password_hash.hash(password)


# Verify password
def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return password_hash.verify(
        plain_password,
        hashed_password
    )


# Generate JWT token
def create_access_token(username: str) -> str:

    expiration = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": username,
        "exp": expiration
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# Verify JWT token
def decode_access_token(token: str):

    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )
