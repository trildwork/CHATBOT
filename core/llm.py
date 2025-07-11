# core/llm.py
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI

from config.settings import GOOGLE_API_KEY, OPENROUTER_API_KEY, OPENROUTER_LLM_MODEL

# Khởi tạo một lần và tái sử dụng
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GOOGLE_API_KEY
)

# Mô hình để sinh câu trả lời (không streaming)
llm = ChatOpenAI(
    model=OPENROUTER_LLM_MODEL,
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0.1
)

# Mô hình để trích xuất metadata (không streaming)
structured_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest",
    temperature=0,
    google_api_key=GOOGLE_API_KEY
)
