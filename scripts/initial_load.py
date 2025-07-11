# FILE: scripts/initial_load.py
import json
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
    # kiểm tra đã nnapj dữ liệu jobs hay chưa
    if db["policies_vector"].count_documents({}) > 0:
        print("Dữ liệu chính sách đã được nạp trước đó. Bỏ qua quá trình nạp lại.")
        return
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


def _get_value(data, key, sub_key=None):
    """
    Helper function to safely extract a value from a potentially nested dictionary.
    """
    value = data.get(key)
    if isinstance(value, dict) and sub_key:
        return value.get(sub_key)
    return value


def load_jobs():
    """
    Nạp dữ liệu jobs từ file JSON, xử lý các định dạng dữ liệu không nhất quán.
    """

    # kiểm tra đã nnapj dữ liệu jobs hay chưa
    if db["jobs_vector"].count_documents({}) > 0:
        print("Dữ liệu jobs đã được nạp trước đó. Bỏ qua quá trình nạp lại.")
        return
    print("--- Bắt đầu xử lý file jobs ---")
    jobs_collection = db["jobs_vector"]
    jobs_collection.delete_many({})

    # 1. Đọc dữ liệu từ file JSON
    try:
        with open("data/jobs.json", "r", encoding="utf-8") as f:
            raw_job_data = json.load(f)
        print(f"Đã đọc được {len(raw_job_data)} jobs từ file JSON.")
    except FileNotFoundError:
        print("Lỗi: Không tìm thấy file data/jobs.json")
        return
    except json.JSONDecodeError:
        print("Lỗi: File data/jobs.json không có định dạng hợp lệ.")
        return

    enriched_job_docs = []
    for job_data in raw_job_data:
        # 2. Tạo nội dung trang (page_content)
        page_content = f"Tiêu đề: {job_data.get('title', '')}\n"
        page_content += f"Mô tả: {job_data.get('description', '')}\n"
        page_content += f"Yêu cầu: {job_data.get('requirements', '')}\n"
        page_content += f"Phúc lợi: {job_data.get('benefits', '')}"

        # 3. Tạo metadata, xử lý các định dạng không nhất quán
        job_id = _get_value(job_data, "_id", "$oid")
        deadline = _get_value(job_data, "deadline", "$date")
        created_at = _get_value(job_data, "createdAt", "$date")
        updated_at = _get_value(job_data, "updatedAt", "$date")
        recruiter_id = _get_value(job_data, "recruiterProfileId", "$oid")
        min_salary = _get_value(job_data, "minSalary", "$numberDecimal")
        max_salary = _get_value(job_data, "maxSalary", "$numberDecimal")

        full_metadata = {
            "source": "jobs",
            "jobId": str(job_id) if job_id else "",
            "title": job_data.get("title", ""),
            "category": job_data.get("category", ""),
            "experience": job_data.get("experience", ""),
            "type": job_data.get("type", ""),
            "workType": job_data.get("workType", ""),
            "status": job_data.get("status", ""),
            "approved": job_data.get("approved", False),
            "location_city": _get_value(job_data, "location", "city"),
            "location_district": _get_value(job_data, "location", "district"),
            "minSalary": float(min_salary) if min_salary is not None else None,
            "maxSalary": float(max_salary) if max_salary is not None else None,
            "deadline": deadline,
            "createdAt": created_at,
            "updatedAt": updated_at,
            "recruiterProfileId": str(recruiter_id) if recruiter_id else ""
        }
        # Loại bỏ các khóa có giá trị None
        full_metadata = {k: v for k,
                         v in full_metadata.items() if v is not None}

        # 4. Tạo Document hoàn chỉnh
        doc = Document(page_content=page_content, metadata=full_metadata)
        enriched_job_docs.append(doc)

    # 5. Nạp các documents đã được làm giàu vào Vector Store
    if enriched_job_docs:
        MongoDBAtlasVectorSearch.from_documents(
            documents=enriched_job_docs,
            embedding=embedding_model,
            collection=jobs_collection,
            index_name="jobs_vector_index"
        )
        print(
            f"Đã nạp {len(enriched_job_docs)} jobs đã được làm giàu metadata.")
    else:
        print("Không có job nào để nạp.")

    print("--- Hoàn thành nạp dữ liệu jobs ---")


if __name__ == "__main__":
    load_policies()
    load_jobs()
