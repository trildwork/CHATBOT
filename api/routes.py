from fastapi import APIRouter
from schemas.common import ChatRequest
from services.rag_service import process_query

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    answer = process_query(request.query, request.history)
    return {"answer": answer}
