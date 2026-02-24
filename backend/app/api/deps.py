from typing import Annotated, Optional
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
import app.models.models as model
import app.core.security as security

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

def get_current_user_from_token(token: str = Depends(oauth2_scheme), db: db_dependency = None) -> model.Users:
    credential_exception = HTTPException(status_code=401, detail="Invalid auth credentials")
    payload = security.verify_token(token)
    if payload is None:
        raise credential_exception
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credential_exception
    user = db.query(model.Users).filter(model.Users.id == user_id).first()
    if user is None:
        raise credential_exception
    return user
