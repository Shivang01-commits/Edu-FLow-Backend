from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.main import get_db
from src.models.user_schema import UserCreate, UserLogin
from src.services.auth_service import AuthService
from src.core.jwt_handler import create_access_token

auth_router = APIRouter(prefix="/auth", tags=["auth"])
service = AuthService()


@auth_router.post("/signup")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    new_user = service.create_user(db, user.email, user.password)
    return {
        "message": "User created successfully!",
        "user_id": new_user.id,
        "email": new_user.email,
    }


@auth_router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = service.authenticate_user(db, user.email, user.password)
    if not db_user:
        return {"error": "Invalid credentials"}
    token = create_access_token({"user_id": str(db_user.id)})
    return {"access_token": token}
