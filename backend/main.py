from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, Depends

from database import engine, Base
import models
from routers import users, pieces, history, settings, robot, pieces_import

from auth import get_current_user, require_role
from models import UserRole

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tunibot Glue Robot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(pieces.router)
app.include_router(history.router)
app.include_router(settings.router)
app.include_router(robot.router)
app.include_router(pieces_import.router)

@app.get("/")
def read_root():
    return {"status": "Tunibot backend is running"}

@app.get("/me")
def read_me(current_user = Depends(get_current_user)):
    return {"email": current_user.email, "role": current_user.role}

