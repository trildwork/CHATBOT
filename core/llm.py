# core/llm.py
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from config.settings import GOOGLE_API_KEY

# Khởi tạo một lần và tái sử dụng
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GOOGLE_API_KEY
)

# Mô hình để sinh câu trả lời (không streaming)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite-preview-06-17",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.1
)

# Mô hình để trích xuất metadata (không streaming)
structured_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite-preview-06-17",
    temperature=0,
    google_api_key=GOOGLE_API_KEY
)
