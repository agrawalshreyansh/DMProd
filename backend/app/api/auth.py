from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.models.user import User
from app.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    user_id: str
    email: str


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest) -> TokenResponse:
    existing = await User.find_one(User.email == body.email)
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(email=body.email, password_hash=hash_password(body.password))
    await user.insert()

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user_id=str(user.id), email=user.email)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    user = await User.find_one(User.email == body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user_id=str(user.id), email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> None:
    # ponytail: JWTs are stateless, nothing to invalidate server-side.
    # The frontend drops the cookie holding the token; this endpoint exists
    # for API symmetry / a place to add a denylist later if ever needed.
    return None
