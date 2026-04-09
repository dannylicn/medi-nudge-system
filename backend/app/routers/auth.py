"""Auth router — login and token refresh."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, hash_password
from app.models.models import User
from app.schemas.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email, User.is_active == True).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse, include_in_schema=False)
def register(payload: LoginRequest, full_name: str = "Coordinator", db: Session = Depends(get_db)):
    """Dev-only: create a user for testing."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=payload.email, full_name=full_name, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token)
