
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from pydantic import BaseModel, Field

from pymongo.errors import DuplicateKeyError

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    TOKEN_EXPIRE_MINUTES
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# Registration request
class RegisterRequest(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_.-]+$"
    )

    password: str = Field(
        min_length=8,
        max_length=128
    )


# Login request
class LoginRequest(BaseModel):

    username: str

    password: str


# Bearer token authentication
bearer_scheme = HTTPBearer(auto_error=False)


# Register a new user
@router.post("/register", status_code=201)
def register_user(
    payload: RegisterRequest,
    request: Request
):

    users = request.app.state.db.users

    # Enforce unique usernames
    users.create_index("username", unique=True)

    user_document = {

        "username": payload.username,

        "hashed_password": hash_password(
            payload.password
        ),

        "created_at": datetime.now(timezone.utc)

    }

    try:

        users.insert_one(user_document)

    except DuplicateKeyError:

        raise HTTPException(
            status_code=409,
            detail="Username already exists"
        )

    return {
        "message": "User registered successfully",
        "username": payload.username
    }


# Login an existing user
@router.post("/login")
def login_user(
    payload: LoginRequest,
    request: Request
):

    users = request.app.state.db.users

    user = users.find_one({
        "username": payload.username
    })

    if (
        not user
        or not verify_password(
            payload.password,
            user["hashed_password"]
        )
    ):

        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )

    token = create_access_token(
        payload.username
    )

    return {

        "access_token": token,

        "token_type": "bearer",

        "expires_in": TOKEN_EXPIRE_MINUTES * 60

    }


# Verify incoming access token
def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    )
):

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    if credentials is None:
        raise unauthorized

    try:

        payload = decode_access_token(
            credentials.credentials
        )

        username = payload.get("sub")

        if not username:
            raise unauthorized

    except Exception:
        raise unauthorized

    user = request.app.state.db.users.find_one({
        "username": username
    })

    if not user:
        raise unauthorized

    return {
        "username": user["username"],
        "user_id": str(user["_id"])
    }


# Current authenticated user
@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user)
):

    return current_user
