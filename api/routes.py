from fastapi import APIRouter
from schemas.common import ChatRequest
from services.rag_service import process_query
import uuid

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    answer = process_query(request.query, session_id)
    return {"answer": answer, "session_id": session_id}
