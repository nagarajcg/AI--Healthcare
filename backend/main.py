"""
AI Healthcare Imaging Data Regulator & Multi-Agent System
FastAPI Backend Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api import doctor_routes, patients, staff, agents, auth, reports, translation_routes, scans, tts_routes, prescription_routes, appointment_routes

app = FastAPI(
    title="AI Healthcare Imaging Data Regulator",
    description="Multi-Agent System connecting Doctors, Patients, and Hospital Staff",
    version="1.0.0",
)

# CORS — allow the frontend served on any local port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(doctor_routes.router)
app.include_router(patients.router)
app.include_router(staff.router)
app.include_router(agents.router)
app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(translation_routes.router)
app.include_router(scans.router)
app.include_router(tts_routes.router)
app.include_router(prescription_routes.router)
app.include_router(appointment_routes.router)

# Serve static frontend files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
