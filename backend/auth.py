from datetime import datetime,timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from schema import UserCreate
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_password_hash(password:str)->str:
    pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")
    return pwd_context.hash(password)

def verify_password(plain_password:str,hased_password:str)->bool:
    pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")
    return pwd_context.verify(plain_password,hased_password)

def create_access_token(data:dict,expires_delta:Optional[timedelta] = None)->str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token:str)->Optional[dict]:
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms = [ALGORITHM])
        return payload
    except jwt.JWTError:
        return None