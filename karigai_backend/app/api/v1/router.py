from fastapi import APIRouter

from .endpoints import voice, vision, documents, learning, users, workflows

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(vision.router, prefix="/vision", tags=["vision"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(learning.router, prefix="/learning", tags=["learning"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])