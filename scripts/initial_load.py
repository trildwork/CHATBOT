# FILE: scripts/initial_load.py
import os
import sys
from typing import List, Optional

from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_mongodb import MongoDBAtlasVectorSearch
from pydantic import BaseModel, Field

from core.db import db
from core.llm import embedding_model, structured_llm

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# --- Pydantic Models for Data Enrichment ---
class JobMetadata(BaseModel):
    """
    Mô hình Pydantic để chứa metadata được LLM trích xuất cho một công việc.
    """
    category: str = Field(
        description="Phân loại ngành nghề của công việc, ví dụ: 'Software Development', 'Marketing', 'Data Science'.")
    level: str = Field(
        description="Cấp bậc của công việc, ví dụ: 'Intern', 'Junior', 'Senior', 'Manager'.")
    skills: List[str] = Field(
        description="Danh sách các kỹ năng công nghệ, phần mềm, hoặc chuyên môn cụ thể được yêu cầu.")
    keywords: List[str] = Field(
        description="Các từ khóa chung hoặc thuật ngữ nghiệp vụ khác liên quan đến công việc.")


class Job(BaseModel):
    """Mô hình Pydantic đại diện cho một công việc thô."""
    title: str
    page_content: str  # Description of the job


def load_policies():
    """Tải, chia nhỏ và nạp dữ liệu chính sách."""
    print("--- Bắt đầu xử lý file chính sách ---")
    loader = TextLoader("data/policies.txt", encoding="utf-8")
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(docs)
    print(f"Đã chia file chính sách thành {len(chunks)} chunks.")
    policies_collection = db["policies_vector"]
    policies_collection.delete_many({})
    MongoDBAtlasVectorSearch.from_documents(
        documents=chunks,
        embedding=embedding_model,
        collection=policies_collection,
        index_name="policies_vector_index"
    )
    print("--- Hoàn thành nạp dữ liệu chính sách ---")


def load_jobs():
    """
    Nạp dữ liệu jobs.
    Tự động trích xuất và làm giàu metadata cho jobs bằng LLM.
    """
    jobs_collection = db["jobs_vector"]
    jobs_collection.delete_many({})

    raw_job_data = [
        {"title": "Senior Python Developer", "page_content": "Senior Python Developer. Yêu cầu 5 năm kinh nghiệm với Django, Flask. Ưu tiên có kinh nghiệm với DevOps. Xây dựng các hệ thống backend và API.", "jobId": "job_001"},
        {"title": "Junior Frontend Developer",
            "page_content": "Junior Frontend Developer (ReactJS). Yêu cầu kiến thức về HTML, CSS, JavaScript và React. Xây dựng giao diện người dùng cho ứng dụng web.", "jobId": "job_002"},
        {"title": "Marketing Manager", "page_content": "Marketing Manager. Lập kế hoạch và triển khai các chiến dịch marketing online. Có kinh nghiệm về SEO, SEM, và Google Analytics. Quản lý đội ngũ marketing.", "jobId": "job_003"},
        {"title": "Data Scientist", "page_content": "Data Scientist. Cần có kinh nghiệm làm việc với các mô hình Machine Learning, Deep Learning. Sử dụng thành thạo Python và các thư viện như Scikit-learn, TensorFlow.", "jobId": "job_004"},
        {"title": "Nhân viên Kế toán Tổng hợp",
            "page_content": "Cần tuyển Kế toán tổng hợp có kinh nghiệm 2 năm. Thành thạo phần mềm MISA, Excel. Chịu trách nhiệm báo cáo thuế, báo cáo tài chính. Cẩn thận, trung thực.", "jobId": "job_005"}
    ]

    enriched_job_docs = []
    for job_data in raw_job_data:
        # Kết hợp metadata đã trích xuất với dữ liệu gốc
        full_metadata = {
            "source": "jobs",
            "title": job_data["title"],
            "jobId": job_data["jobId"]
        }

        # Tạo Document hoàn chỉnh
        doc = Document(
            page_content=job_data["page_content"], metadata=full_metadata)
        enriched_job_docs.append(doc)

    # 4. Nạp các documents đã được làm giàu vào Vector Store
    MongoDBAtlasVectorSearch.from_documents(
        documents=enriched_job_docs,
        embedding=embedding_model,
        collection=jobs_collection,
        index_name="default"
    )
    print(f"Đã nạp {len(enriched_job_docs)} jobs đã được làm giàu metadata.")

    print("--- Hoàn thành nạp dữ liệu ---")


if __name__ == "__main__":
    load_policies()
    load_jobs()
