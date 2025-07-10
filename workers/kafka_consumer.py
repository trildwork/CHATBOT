import json
from datetime import datetime
from typing import List, Optional

from kafka import KafkaConsumer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_mongodb import MongoDBAtlasVectorSearch
from pydantic import BaseModel, Field

from config import settings
from core.db import db
from core.llm import embedding_model


class JobPayload(BaseModel):
    jobId: str
    description: str
    title: str
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    skills: Optional[List[str]] = Field(default_factory=list)
    category: Optional[str] = None
    area: Optional[str] = None
    minSalary: Optional[int] = None
    maxSalary: Optional[int] = None
    companyName: Optional[str] = None
    location: Optional[dict] = Field(
        default_factory=dict)  # {city, district, address}
    type: Optional[str] = None  # e.g., FULL_TIME, PART_TIME
    workType: Optional[str] = None  # e.g., ON_SITE, REMOTE
    experience: Optional[str] = None  # e.g., '1-2 Năm'
    # Dùng datetime để dễ dàng so sánh và query
    deadline: Optional[datetime] = None


class JobEvent(BaseModel):
    eventType: str
    timestamp: str
    payload: JobPayload

# --- Logic xử lý ---


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=200)
jobs_collection = db["jobs_vector"]  # Tái sử dụng collection object


def _prepare_documents(job: JobPayload) -> list[Document]:
    """
    Chuẩn bị văn bản và metadata từ một job để embedding.
    Làm giàu nội dung và metadata để RAG tìm kiếm tốt hơn.
    """
    # Ghép các trường văn bản quan trọng để tạo ngữ cảnh đầy đủ
    content_parts = [
        f"Công ty: {job.companyName if job.companyName else 'Chưa cập nhật'}",
        f"Tiêu đề công việc: {job.title}",
        f"Mô tả: {job.description}"
    ]
    if job.requirements:
        content_parts.append(f"Yêu cầu: {job.requirements}")
    if job.benefits:
        content_parts.append(f"Phúc lợi: {job.benefits}")
    if job.type or job.workType:
        content_parts.append(
            f"Loại công việc: {job.type if job.type else 'N/A'}, Hình thức làm việc: {job.workType if job.workType else 'N/A'}")
    if job.experience:
        content_parts.append(f"Yêu cầu kinh nghiệm: {job.experience}")
    if job.location:
        content_parts.append(
            f"Địa điểm: {job.location.get('city', 'N/A')}, {job.location.get('district', 'N/A')}")
    if job.skills:
        content_parts.append(f"Kỹ năng: {', '.join(job.skills)}")
    if job.minSalary is not None and job.maxSalary is not None:
        content_parts.append(f"Mức lương: {job.minSalary} - {job.maxSalary}")

    content = "\n".join(content_parts)

    # Metadata chứa tất cả các trường có thể lọc được
    # page content là cái dùng để embedding
    # TODO: metadata là để filter nếu cần thêm filter in the future
    metadata = {
        "source": "job_posting",
        "job_id": job.jobId,
        "title": job.title,
        "companyName": job.companyName,
        "city": job.location.get('city') if job.location else None,
        "category": job.category,
        "experience": job.experience,
        "workType": job.workType,
        "type": job.type,
        "area": job.area,
        "deadline": job.deadline.isoformat() if job.deadline else None
    }

    # Một job có thể được chia thành nhiều document (chunk)
    # Mỗi chunk sẽ có cùng metadata
    doc = Document(page_content=content, metadata=metadata)
    split_docs = text_splitter.split_documents([doc])
    return split_docs


def upsert_job(job: JobPayload):
    """
    Thêm mới hoặc cập nhật một job vào vector store.
    Logic: Xóa tất cả các chunk cũ của job, sau đó thêm các chunk mới.
    """
    job_id = job.jobId
    print(f"Bắt đầu UPSERT cho job_id: {job_id}")

    # 1. Xóa tất cả các chunk cũ thuộc về job_id này
    # Đây là cách làm đúng: xóa dựa trên metadata
    delete_result = jobs_collection.delete_many({"job_id": job_id})
    print(f"  - Đã xóa {delete_result.deleted_count} chunk cũ.")

    # 2. Chuẩn bị và thêm các chunk mới
    documents = _prepare_documents(job)
    if not documents:
        print(
            f"  - Không có document nào được tạo cho job_id: {job_id}. Bỏ qua.")
        return

    vs_jobs = MongoDBAtlasVectorSearch.from_documents(
        documents=documents,
        embedding=embedding_model,
        collection=jobs_collection,
        index_name="default"  # Đảm bảo index name là đúng
    )
    print(f"  - Đã thêm {len(documents)} chunk mới cho job_id: {job_id}")


def delete_job(job_id: str):
    """Xóa tất cả các chunk liên quan đến một job_id."""
    print(f"Bắt đầu DELETE cho job_id: {job_id}")
    delete_result = jobs_collection.delete_many({"job_id": job_id})
    if delete_result.deleted_count > 0:
        print(
            f"  - Đã xóa thành công {delete_result.deleted_count} chunk của job_id: {job_id}")
    else:
        print(f"  - Không tìm thấy chunk nào để xóa cho job_id: {job_id}")


def start_consumer():
    consumer = KafkaConsumer(
        settings.KAFKA_JOB_EVENTS_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        group_id='careerzone_rag_consumer_group'  # Thêm group_id là best practice
    )
    print("Kafka consumer đã sẵn sàng. Đang chờ sự kiện job...")

    for message in consumer:
        try:
            event_data = message.value
            print(f"Nhận được message: {message.value}")
            # Validate bằng model JobEvent mới
            job_event = JobEvent(**event_data)

            event_type = job_event.eventType.upper()
            payload = job_event.payload

            print(
                f"Nhận được sự kiện: {event_type} cho job_id: {payload.jobId}")

            if event_type in ["JOB_CREATED", "JOB_UPDATED"]:
                upsert_job(payload)
            elif event_type == "JOB_DELETED":
                delete_job(payload.jobId)
            else:
                print(f"Hành động không xác định: {event_type}")

        except Exception as e:
            print(f"Lỗi xử lý message: {message.value}. Lỗi: {e}")


if __name__ == "__main__":
    start_consumer()
