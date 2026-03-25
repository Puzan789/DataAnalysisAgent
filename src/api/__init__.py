from fastapi import APIRouter
from src.api.v1.chat import router as agent_router
from src.api.v1.databaseinfo import router as db_router
from src.api.v1.vectordb import vector_router
from src.api.v1.message import router as message_router
from src.api.v1.auth import auth_router
from src.api.v1.chart import router as chart_router

router = APIRouter()
router.include_router(agent_router)
router.include_router(db_router)
router.include_router(vector_router)
router.include_router(message_router)
router.include_router(auth_router)
router.include_router(chart_router)
