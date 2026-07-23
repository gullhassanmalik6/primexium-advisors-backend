from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, content, leads, student

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(leads.router)
api_router.include_router(student.router)
api_router.include_router(admin.router)
api_router.include_router(content.public_router)
api_router.include_router(content.admin_router)
