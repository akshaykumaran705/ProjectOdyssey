from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
import app.schemas.schemas as schema
import app.models.models as model
import app.core.security as security
from app.api.deps import db_dependency, get_current_user_from_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register_user(user: schema.UserCreate, db: db_dependency) -> dict:
    if not user.email or not user.password:
        return {"error": "Email and passwords are required"}
    elif "@" not in user.email:
        return {"error": "Invalid email format"}
    existing_user = db.query(model.Users).filter(model.Users.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email id already exists")
    hashed_password = security.get_password_hash(user.password)
    new_user = model.Users(email=user.email, password=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"Message": "User Registered Successfully", "user_id": new_user.id}

@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: db_dependency = None):
    user = db.query(model.Users).filter(model.Users.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid Credentials")
    access_token = security.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_current_user(current_user: model.Users = Depends(get_current_user_from_token)):
    return current_user
