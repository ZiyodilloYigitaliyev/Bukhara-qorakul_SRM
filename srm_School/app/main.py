from fastapi import FastAPI
from app.api.routes import auth, students  
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import attendance
from app.api.routes import score
from app.api.routes import teacher 
from app.api.routes import schedule
from app.api.routes import auth_student

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(schedule.router)
app.include_router(attendance.router) 
app.include_router(score.router)  
app.include_router(teacher.router)
app.include_router(auth_student.router)