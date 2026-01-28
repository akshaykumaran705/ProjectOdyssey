from fastapi import FastAPI,File,UploadFile
from db import SessionLocal, engine
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from fastapi import Depends
import schema
import model 
import pdf_extractor
import narrative_builder
import auth
from fastapi import HTTPException 
import io
import object_store
import uuid
import case_analysis
from builder import generate_case_analysis
from runner import LLMRunner
from source_hashing import compute_source_hash
import structured_case
app = FastAPI(title="ProjectOdyssey")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
model.Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
db_dependency = Annotated[Session, Depends(get_db)]
def get_current_user_from_token(token:str = Depends(oauth2_scheme),db:db_dependency = None) -> model.Users:
    credential_exception = HTTPException(status_code = 401,detail = "Invalid auth credentials")
    payload = auth.verify_token(token)
    if payload is None:
        raise credential_exception
    user_id:Optional[str] = payload.get("sub")
    if user_id is None:
        raise credential_exception
    user = db.query(model.Users).filter(model.Users.id == user_id).first()
    if user is None:
        raise credential_exception
    return user
@app.get("/health")
async def health_check():
    return {"status":"ok"}
@app.on_event("startup")
async def startup_event():
    object_store.object_store.ensure_bucket_exists()

@app.post("/auth/register")
async def register_user(user:schema.UserCreate,db:db_dependency) -> dict:
    if not user.email or not user.password:
        return {"error":"Email and passwords are required"}
    elif "@" not in user.email:
        return {"error":"Invalid email format"}
    existing_user = db.query(model.Users).filter(model.Users.email==user.email).first()
    if existing_user:
        return {"Error":"Email Id already exists"}
    hashed_password = auth.get_password_hash(user.password)
    new_user = model.Users(email = user.email,password = hashed_password ,role = user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"Message":"User Registered Successfully","user_id":new_user.id}

@app.post("/auth/login")
async def login_user(form_data:OAuth2PasswordRequestForm = Depends(),db:db_dependency=None):
    user = db.query(model.Users).filter(model.Users.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password,user.password):
        raise HTTPException(status_code = 400, detail = "Invalid Credentials")
    access_token = auth.create_access_token(data={"sub":str(user.id)})
    return {"access_token":access_token,"token_type":"bearer"}

@app.get("/auth/me")
async def get_current_user(current_user: model.Users = Depends(get_current_user_from_token)):
   return current_user
@app.post("/cases")
async def create_case(case:schema.CaseCreate,db:db_dependency,current_user:model.Users = Depends(get_current_user_from_token)):
    if not case.title or not case.chief_complaint:
        return {"error":"Title and chief complaint are required"}
    first_user = db.query(model.Users).first()
    if not first_user:
        return {"error":"No users found. Please register first."}
    new_case = model.Cases(
        created_by_user_id=current_user.id,
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
async def get_cases(current_user:model.Users = Depends(get_current_user_from_token),db:db_dependency=None):
    cases = db.query(model.Cases).filter(model.Cases.created_by_user_id == current_user.id).all()
    return {"cases":[{"id":c.id,"title":c.title,"chief_complaint":c.chief_complaint,"created_by_user_id":c.created_by_user_id} for c in cases]}
@app.get("/cases/{case_id}")
async def get_case(case_id:int,db:db_dependency = None,current_user:model.Users = Depends(get_current_user_from_token)):
    case = db.query(model.Cases).filter(model.Cases.id == case_id,model.Cases.created_by_user_id == current_user.id).first()
    if not case:
        return {"error":"Case not found"}
    return {"case":{"id":case.id,"title":case.title,"chief_complaint":case.chief_complaint,"created_by_user_id":case.created_by_user_id}}
@app.post("/cases/{case_id}/files")
async def upload_case_file(case_id:int,file:UploadFile = File(...),db:db_dependency=None,current_user:model.Users = Depends(get_current_user_from_token)):
    if file.content_type not in ["application/pdf","image/png","image/jpeg"]:
        return {"error":"Unsupported file type"}
    data = await file.read()
    size = len(data)
    if size > 5 * 1024 * 1024:
        return {"error":"File size exceeds limit"}
    key = f"case_{case_id}/{uuid.uuid4()}-{file.filename}"
    case = db.query(model.Cases).filter(model.Cases.id == case_id,model.Cases.created_by_user_id == current_user.id).first()
    if not case:
        return {"Error":"Case not found"}
    new_file = model.CaseFiles(case_id = case_id,file_name=file.filename,content_type = file.content_type,object_key = key,size_bytes = size)
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    object_store.object_store.upload_fileobj(fileobj = io.BytesIO(data),key = key,content_type=file.content_type)
    return {"File Uploaded Successfully":key,"size":size}

@app.post("/cases/{case_id}/normalize")
async def normalize_case_data(case_id:int,db:db_dependency = None, current_user:model.Users = Depends(get_current_user_from_token)):
    case = db.query(model.Cases).filter(model.Cases.id == case_id,model.Cases.created_by_user_id == current_user.id).first()
    if not case:
        return {"error":"Case not found"}
    pdf_extractor.process_pdf_extraction(db,case_id)
    case_fields = {
        "age":case.age,
        "sex":case.sex,
        "chief_complaint":case.chief_complaint,
        "history_present_illness":case.history_present_illness
    }
    docs = db.query(model.CaseDocumentsText).filter(model.CaseDocumentsText.case_id==case.id).all()
    extracted_docs = [{
        "file_id":d.file_id,
        "extracted_text": d.extracted_text,
    } for d in docs]
    source_hash = compute_source_hash(case_fields,extracted_docs)
    existing = db.query(model.CaseStructured).filter(model.CaseStructured.case_id == case_id).first()
    if existing and existing.source_hash == source_hash:
        return{
            "case_id": case_id,
            "status":"already_normalized",
            "source_hash":source_hash
        }
    
    narrative = narrative_builder.build_case_narrative(case,docs)
    structured = structured_case.narrative_to_structured_case(narrative)
    structured_json = structured.model_dump()
    new_case = model.CaseStructured(case_id=case.id,source_hash=source_hash,normalized_data=structured_json) 
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return {
        "message": "Case Normalized",
        "case_id": case_id,
        "status":"Normalized",
        "structured_case":structured_json,
        "source_hase":source_hash,
        "documents_extracted": len(docs),
        "narrative":narrative[:1500]
    }

@app.post("/cases/{case_id}/analyze")
def analyze_case(case_id:int,body:schema.AnalyzeRequest,db:db_dependency=None,current_user = Depends(get_current_user_from_token)):
    case = db.query(model.Cases).filter(model.Cases.id==case_id,model.Cases.created_by_user_id==current_user.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    structured = db.query(model.CaseStructured).filter(model.CaseStructured.case_id==case_id).first()
    if not structured:
        raise HTTPException(status_code=400,detail="Case not normalized yet")
    narrative_text = case.narrative_text if hasattr(case,"narrative_text") else ""
    if not narrative_text:
        narrative_text= ""
    runner = LLMRunner(base_url = "http://localhost:8080/",model="mlx-community/medgemma-4b-it-4bit")
    analysis_row, cache_hit = generate_case_analysis(db,case_id=case_id,structured_source_hash= structured.source_hash,structured_case=structured.normalized_data,narrative = narrative_text,analysis_version=body.analysis_version,force=body.force,runner=runner)

    return {
        "case_id":analysis_row.case_id,
        "source_hash":analysis_row.source_hash,
        "analysis_version":analysis_row.analysis_version,
        "analysis_data":analysis_row.analysis_data,
        "created_at": analysis_row.created_at,
    }

@app.get("/cases/{case_id}/analysis")
def get_analysis(case_id:int,analyis_version:str="v1",db:db_dependency=None,current_user=Depends(get_current_user_from_token)):
    case = db.query(model.Cases).filter(model.Cases.id==case_id,model.Cases.created_by_user_id==current_user.id).first()
    if not case:
        raise HTTPException(status_code=404,detail="Case not found")
    row = case_analysis.get_latest_case_analysis(db,case_id=case_id,analysis_version=analyis_version)
    if not row:
        raise HTTPException(status_code=404,detail="No Analysis found")
    
    return {
        "case_id":row.case_id,
        "source_hash":row.source_hash,
        "analysis_version":row.analysis_version,
        "analysis_data":row.analysis_data,
        "created_at":row.created_at
    }
