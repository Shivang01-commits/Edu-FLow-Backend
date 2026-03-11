from sqlalchemy.orm import Session
from src.db.models import User
from src.core.config import hash_password, verify_password


class AuthService:
    def create_user(self, db: Session, email: str, password: str):
        hashed = hash_password(password)
        user = User(email=email, password_hash=hashed)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate_user(self, db: Session, email: str, password: str):
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None
        return user
