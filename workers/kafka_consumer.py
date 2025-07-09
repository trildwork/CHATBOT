import json
from kafka import KafkaConsumer
from config import settings
from core.db import db
from core.llm import embedding_model
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class JobPayload(BaseModel):
    id: str
    title: str
    description: str
    requirements: str
    benefits: Optional[str] = ""
    location: dict
    minSalary: Optional[int] = 0
    maxSalary: Optional[int] = 0
    deadline: datetime

class JobEvent(BaseModel):
    action: str  # "CREATE", "UPDATE", "DELETE"
    payload: JobPayload

text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

def _prepare_documents(job: JobPayload) -> list[Document]:
    """Chuẩn bị văn bản và metadata từ một job để embedding."""
    content = (
        f"Tiêu đề công việc: {job.title}\n"
        f"Mô tả: {job.description}\n"
        f"Yêu cầu: {job.requirements}\n"
        f"Phúc lợi: {job.benefits}\n"
        f"Địa điểm: {job.location.get('city')}, {job.location.get('district')}"
    )
    metadata = {
        "source": "job_posting",
        "job_id": job.id,
        "title": job.title,
        "city": job.location.get('city'),
        "deadline": job.deadline.isoformat()
    }
    doc = Document(page_content=content, metadata=metadata)
    split_docs = text_splitter.split_documents([doc])
    return split_docs

def upsert_job(job: JobPayload):
    """Thêm mới hoặc cập nhật một job vào vector store."""
    job_id = job.id
    print(f"Bắt đầu UPSERT cho job_id: {job_id}")
    jobs_collection = db["jobs_vector"]
    vs_jobs = MongoDBAtlasVectorSearch(
        collection=jobs_collection,
        embedding=embedding_model,
        index_name="jobs_vector_index"
    )
    vs_jobs.delete(ids=[job_id])
    documents = _prepare_documents(job)
    vs_jobs.add_documents(documents, ids=[job_id for _ in documents])
    print(f"  - Đã thêm {len(documents)} chunks mới cho job_id: {job_id}")

def delete_job(job_id: str):
    """Xóa tất cả các chunks liên quan đến một job_id."""
    print(f"Bắt đầu DELETE cho job_id: {job_id}")
    jobs_collection = db["jobs_vector"]
    vs_jobs = MongoDBAtlasVectorSearch(
        collection=jobs_collection,
        embedding=embedding_model,
        index_name="jobs_vector_index"
    )
    vs_jobs.delete(ids=[job_id])
    print(f"  - Đã xóa thành công các chunks của job_id: {job_id}")

def start_consumer():
    consumer = KafkaConsumer(
        settings.KAFKA_JOB_EVENTS_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest'
    )
    print("Kafka consumer started. Waiting for job events...")

    for message in consumer:
        try:
            event_data = message.value
            job_event = JobEvent(**event_data)

            action = job_event.action.upper()
            payload = job_event.payload

            print(f"Received event: {action} for job_id: {payload.id}")

            if action in ["CREATE", "UPDATE"]:
                upsert_job(payload)
            elif action == "DELETE":
                delete_job(payload.id)
            else:
                print(f"Unknown action: {action}")

        except Exception as e:
            print(f"Error processing message: {message.value}. Error: {e}")

if __name__ == "__main__":
    start_consumer()
