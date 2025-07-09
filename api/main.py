from fastapi import FastAPI
from api.routes import router as chat_router

app = FastAPI(title="Smart RAG Chatbot Service")
app.include_router(chat_router, prefix="/api/v1")
