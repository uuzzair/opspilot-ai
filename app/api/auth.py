"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import TokenRead, UserLogin, UserRegister
from app.schemas.user import CurrentUserRead, UserRead
from app.services import audit_log_service
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserRegister,
    db: Session = Depends(get_db),
) -> User:
    """Register a user."""
    existing_user = auth_service.get_user_by_email(db, user_in.email)
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = auth_service.create_user(db, user_in)
    audit_log_service.safe_create_audit_log(
        db,
        entity_type="user",
        entity_id=user.id,
        action="registered",
        actor_id=user.id,
        details={"email": user.email, "role": user.role},
    )
    return user


@router.post("/login", response_model=TokenRead)
def login_user(
    user_in: UserLogin,
    db: Session = Depends(get_db),
) -> TokenRead:
    """Login and return a bearer token."""
    user = auth_service.authenticate_user(db, user_in.email, user_in.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenRead(access_token=auth_service.create_user_access_token(user))


@router.get("/me", response_model=CurrentUserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the current user."""
    return current_user
