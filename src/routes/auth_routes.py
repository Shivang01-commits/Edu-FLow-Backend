from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db.main import get_db
from src.models.user_schema import UserCreate, UserLogin
from src.services.auth_service import AuthService
from src.core.jwt_handler import create_access_token

auth_router = APIRouter(prefix="/auth", tags=["auth"])
service = AuthService()


@auth_router.post("/signup", status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):

    # check if user already exists
    existing_user = service.get_user_by_email(db, user.email)

    if existing_user:
        raise HTTPException(
            status_code=409, detail="User with this email already exists"
        )

    new_user = service.create_user(db, user.email, user.password)

    return {
        "message": "User created successfully",
        "user_id": new_user.id,
        "email": new_user.email,
    }


@auth_router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):

    db_user = service.authenticate_user(db, user.email, user.password)

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"user_id": str(db_user.id)})

    return {"access_token": token, "token_type": "bearer"}
