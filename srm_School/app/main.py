# app/main.py
from fastapi import FastAPI
from app.api.routes import auth, students, attendance, score, teacher, schedule, auth_student, device, schools, face_terminal, mobile_api

from fastapi.middleware.cors import CORSMiddleware

# Admin Panel
app = FastAPI(
    title="Admin Panel",
    docs_url="/docs",             
    openapi_url="/openapi.json",  
    redoc_url="/redoc"            
)


# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin routerlar
app.include_router(auth.router)
app.include_router(students.router)
app.include_router(schedule.router)
app.include_router(attendance.router)
app.include_router(score.router)
app.include_router(teacher.router)
app.include_router(face_terminal.router)
app.include_router(device.router)
app.include_router(schools.router)

# Mobile uchun faqat kerakli routerlar
app.include_router(auth_student.router)
app.include_router(mobile_api.router)