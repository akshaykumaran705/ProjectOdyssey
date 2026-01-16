from fastapi import FastAPI
from schema import Users,Cases,CaseFiles,AuditLogs
from db import SessionLocal, engine
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Annotated
from fastapi import Depends
import schema
import model 
app = FastAPI(title="ProjectOdyssey")
token = OAuth2PasswordBearer(tokenUrl="token")
model.Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
db_dependency = Annotated[Session, Depends(get_db)]
@app.get("/health")
async def health_check():
    return {"status":"ok"}
@app.post("/auth/register")
async def register_user(user:schema.UserCreate,db:db_dependency) -> dict:
    if not user.email or not user.password:
        return {"error":"Email and passwords are required"}
    elif "@" not in user.email:
        return {"error":"Invalid email format"}
    existing_user = db.query(model.Users).filter(model.Users.email==user.email).first()
    if existing_user:
        return {"Error":"Email Id already exists"}
    new_user = model.Users(email = user.email,password = user.password,role = user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"Message":"User Registered Successfully","user_id":new_user.id}
@app.post("/auth/login")
async def login_user(user:schema.UserLogin,db:db_dependency):
    if not user.email or not user.password:
        return {"error":"Email and passwords are required"}
    db_user = db.query(model.Users).filter(model.Users.email == user.email).first()
    if not db_user or db_user.password != user.password:
        return {"error":"Invalid email or password"}
    return {"message":"User logged in successfully","user_id":db_user.id}
@app.get("/auth/me")
async def get_current_user(db:db_dependency):
    user = db.query(model.Users).first()
    if not user:
        return {"error":"User not found"}
    return {"user":{"id":user.id,"email":user.email,"role":user.role}}
@app.post("/cases")
async def create_case(case:schema.CaseCreate,db:db_dependency):
    if not case.title or not case.chief_complaint:
        return {"error":"Title and chief complaint are required"}
    # TODO: Get actual user_id from authentication token/session
    first_user = db.query(model.Users).first()
    if not first_user:
        return {"error":"No users found. Please register first."}
    new_case = model.Cases(
        created_by_user_id=first_user.id,
        title=case.title,
        chief_complaint=case.chief_complaint,
        history_present_illness=case.history_present_illness,
        age=case.age,
        sex=case.sex
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return {"message":"Case created successfully","case_id":new_case.id}
@app.get("/cases")
async def get_cases(db:db_dependency):
    cases = db.query(model.Cases).all()
    return {"cases":[{"id":c.id,"title":c.title,"chief_complaint":c.chief_complaint,"created_by_user_id":c.created_by_user_id} for c in cases]}
@app.get("/cases/{case_id}")
async def get_case(case_id:int,db:db_dependency):
    case = db.query(model.Cases).filter(model.Cases.id == case_id).first()
    if not case:
        return {"error":"Case not found"}
    return {"case":{"id":case.id,"title":case.title,"chief_complaint":case.chief_complaint,"created_by_user_id":case.created_by_user_id}}
    