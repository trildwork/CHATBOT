from fastapi import APIRouter
from schemas.common import ChatRequest
from services.rag_service import process_query_stream
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(process_query_stream(request.query, request.history), media_type="text/event-stream")
