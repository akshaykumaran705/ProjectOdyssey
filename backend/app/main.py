from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
import app.models.models as model
import app.utils.object_store as object_store

from app.api.routers import auth, cases, health

app = FastAPI(title="ProjectOdyssey")

origins = [
    "http://localhost:5173",
    "http://localhost:5173/*",
    "http://localhost:3000",
    "http://localhost:3000/*",
]
app.add_middleware(CORSMiddleware,
                   allow_origins=origins,
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"]
                   )

model.Base.metadata.create_all(bind=engine)

@app.on_event("startup")
async def startup_event():
    object_store.object_store.ensure_bucket_exists()

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(cases.router)
