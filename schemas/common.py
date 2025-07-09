from pydantic import BaseModel
from typing import Optional
import uuid

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
