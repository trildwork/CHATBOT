# FILE: services/rag_service.py

import json
import logging
import sys
from datetime import datetime, timezone
from operator import itemgetter
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain.chains.router.llm_router import RouterOutputParser
from langchain.chains.router.multi_prompt_prompt import MULTI_PROMPT_ROUTER_TEMPLATE
from langchain.prompts import PromptTemplate
from langchain.schema import AIMessage, HumanMessage
from langchain.schema.runnable import Runnable
from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForRetrieverRun,
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnablePassthrough
from langchain_mongodb import MongoDBAtlasVectorSearch
from pydantic import BaseModel, Field

from core.db import db
from core.llm import embedding_model, llm
from schemas.common import ChatMessage

# Setup logging for RAG service
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


# 1. ĐỊNH NGHĨA PYDANTIC MODEL CHO FILTERS (Không đổi)
class JobFilters(BaseModel):
    """Cấu trúc chỉ chứa bộ lọc keywords"""
    keywords: Optional[List[str]] = Field(
        None, description="Các từ khóa chung hoặc thuật ngữ nghiệp vụ chữ thường, ví dụ: ['backend', 'api', 'python']."
    )


AVAILABLE_LEVELS = ["Intern", "Junior", "Senior", "Lead", "Manager"]


# CẬP NHẬT: Gắn thẻ nguồn vào metadata của document để biết nó đến từ đâu
class MultiSourceRetriever(BaseRetriever):
    """
    Retriever sử dụng router để chọn retriever phù hợp.
    CẬP NHẬT: Gắn thẻ nguồn (tên retriever) vào metadata của mỗi document.
    """
    retrievers: Dict[str, BaseRetriever]
    router: Runnable

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        result = self.router.invoke({"input": query}, config={
                                    "callbacks": run_manager.get_child()})
        destination = result.get('destination')

        if destination and destination in self.retrievers:
            logger.info(f"Router chose (sync): {destination}")
            chosen_retriever = self.retrievers[destination]
            docs = chosen_retriever.get_relevant_documents(
                query, callbacks=run_manager.get_child())
            for doc in docs:
                doc.metadata["source_retriever"] = destination
            return docs

        logger.warning(
            "Router could not choose a destination (sync). Querying all retrievers.")
        all_docs = []
        for name, retriever in self.retrievers.items():
            docs = retriever.get_relevant_documents(
                query, callbacks=run_manager.get_child())
            for doc in docs:
                doc.metadata["source_retriever"] = name
            all_docs.extend(docs)
        return all_docs

    async def _aget_relevant_documents(self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun) -> List[Document]:
        result = await self.router.ainvoke({"input": query}, config={"callbacks": run_manager.get_child()})
        destination = result.get('destination')

        if destination and destination in self.retrievers:
            logger.info(f"Router chose (async): {destination}")
            chosen_retriever = self.retrievers[destination]
            docs = await chosen_retriever.ainvoke(query, config={"callbacks": run_manager.get_child()})
            for doc in docs:
                doc.metadata["source_retriever"] = destination
            return docs

        logger.warning(
            "Router could not choose a destination (async). Querying all retrievers.")
        all_docs = []
        for name, retriever in self.retrievers.items():
            docs = await retriever.ainvoke(query, config={"callbacks": run_manager.get_child()})
            for doc in docs:
                doc.metadata["source_retriever"] = name
            all_docs.extend(docs)
        return all_docs


# 2. XÂY DỰNG GET_RETRIEVER (Không đổi)
def get_retriever(job_filters: Optional[JobFilters] = None):
    logger.info(f"get_retriever() called with filters: {job_filters}")

    # Lấy thời gian hiện tại để lọc các job hết hạn
    current_time_iso = datetime.now(timezone.utc).isoformat()

    # Xây dựng pre_filter cho MongoDB
    # Điều kiện mặc định: job phải còn hạn
    mongo_filter = {"deadline": {"$gte": current_time_iso}}

    vs_jobs = MongoDBAtlasVectorSearch(
        collection=db["jobs_vector"],
        embedding=embedding_model,
        index_name="jobs_vector_index"  # Sửa lại index name cho đúng
    )

    # Chỉ định pre_filter khi tạo retriever
    # Retriever sẽ chỉ tìm kiếm trên các document thỏa mãn điều kiện này
    jobs_retriever = vs_jobs.as_retriever(
        search_kwargs={
            'k': 10,
            'pre_filter': mongo_filter
        }
    )

    logger.info(f"Applying real-time filter for active jobs: {mongo_filter}")
    logger.info(f"Current time used for filtering: {current_time_iso}")

    # Force flush để đảm bảo log hiển thị ngay
    sys.stdout.flush()

    # Phần còn lại của hàm giữ nguyên...
    vs_policies = MongoDBAtlasVectorSearch(
        # Sửa index name
        collection=db["policies_vector"], embedding=embedding_model, index_name="policies_vector_index"
    )
    policies_retriever = vs_policies.as_retriever(search_kwargs={'k': 3})

    retriever_infos = [
        {"name": "recruitment", "description": "Hữu ích cho các câu hỏi về tuyển dụng, tìm kiếm công việc, ứng viên và hồ sơ.",
         "retriever": jobs_retriever},
        {"name": "company_policies", "description": "Hữu ích cho các câu hỏi về quy định, điều khoản dịch vụ, chính sách bảo mật của công ty.",
         "retriever": policies_retriever}
    ]
    router_template = MULTI_PROMPT_ROUTER_TEMPLATE.format(destinations="\n".join(
        [f'{r["name"]}: {r["description"]}' for r in retriever_infos]))
    router_prompt = PromptTemplate.from_template(router_template)
    lcel_router = router_prompt | llm | RouterOutputParser()

    return MultiSourceRetriever(retrievers={info["name"]: info["retriever"] for info in retriever_infos}, router=lcel_router)


def format_docs(docs: List[Document]) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def _format_chat_history(chat_history: List[ChatMessage]):
    buffer = []
    for msg in chat_history:
        if msg.role == "user":
            buffer.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            buffer.append(AIMessage(content=msg.content))
    return buffer


# CẬP NHẬT: Luồng xử lý chính được cấu trúc lại để trả về jobId
async def process_query_stream(query: str, history: List[ChatMessage]) -> AsyncGenerator[str, None]:
    """
    Xử lý câu hỏi, bao gồm trích xuất filter, RAG, và trả về cả câu trả lời lẫn danh sách job ID.
    """
    logger.info(f"process_query_stream() called with query: '{query}'")
    logger.info(f"History length: {len(history)}")

    # Force flush logs
    sys.stdout.flush()

    # # 1. Trích xuất filter từ câu hỏi (không đổi)
    # filter_extraction_prompt = PromptTemplate.from_template(
    #     """Dựa vào câu hỏi của người dùng, hãy trích xuất các tiêu chí lọc cho việc làm.
    #     Nếu không có thông tin, hãy để trống. Câu hỏi người dùng: {query}"""
    # )
    # filter_extraction_chain = (
    #     filter_extraction_prompt | llm.with_structured_output(JobFilters)
    # )
    # extracted_filters = await filter_extraction_chain.ainvoke({"query": query})
    # print(f"Extracted job filters: {extracted_filters}")

    # retriever = get_retriever(job_filters=extracted_filters)
    logger.info("Creating retriever...")
    retriever = get_retriever()
    logger.info("Retriever created successfully")

    # Force flush logs
    sys.stdout.flush()

    # 2. Xác định câu hỏi độc lập nếu có lịch sử trò chuyện
    _template = """Với lịch sử trò chuyện sau đây và một câu hỏi theo sau, hãy diễn đạt lại câu hỏi đó thành một câu hỏi độc lập.
    Lịch sử trò chuyện: {chat_history}
    Câu hỏi theo sau: {question}
    Câu hỏi độc lập:"""
    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_template)

    input_query = query
    if history:
        logger.info("History found, creating standalone question.")
        standalone_question_chain = (
            {"question": itemgetter(
                "question"), "chat_history": lambda x: _format_chat_history(x["chat_history"])}
            | CONDENSE_QUESTION_PROMPT
            | llm
            | StrOutputParser()
        )
        input_query = await standalone_question_chain.ainvoke({"question": query, "chat_history": history})
        logger.info(f"Standalone question: {input_query}")

    # 3. Lấy tài liệu (jobs, policies, etc.) MỘT LẦN DUY NHẤT
    logger.info("Retrieving documents...")
    retrieved_docs = await retriever.ainvoke(input_query)
    logger.info(f"Retrieved {len(retrieved_docs)} documents")
    context_str = format_docs(retrieved_docs)

    # 4. Tạo và stream câu trả lời từ LLM
    qa_template = """Bạn là "CareerZone AI", một trợ lý tuyển dụng ảo thông minh.
    Sử dụng ngữ cảnh sau để trả lời câu hỏi. Nếu không biết, hãy nói bạn không biết.
    NGỮ CẢNH: --- {context} ---
    CÂU HỎI: {question}
    TRẢ LỜI:"""
    QA_PROMPT = PromptTemplate.from_template(qa_template)
    qa_chain = QA_PROMPT | llm | StrOutputParser()

    async for chunk in qa_chain.astream({"context": context_str, "question": input_query}):
        response_packet = {"type": "answer_chunk", "data": chunk}
        yield f"data: {json.dumps(response_packet, ensure_ascii=False)}\n\n"

    # # 5. Lọc và gửi danh sách các jobId đã tìm được
    # job_ids = []
    # job_docs = [doc for doc in retrieved_docs if doc.metadata.get("source_retriever") == "recruitment"]

    # for doc in job_docs:
    #     # Lấy jobId từ metadata
    #     job_id = doc.metadata.get("jobId")
    #     if job_id:
    #         # Chuyển đổi sang str để đảm bảo tương thích JSON (phòng trường hợp nó là ObjectId)
    #         job_ids.append(str(job_id))

    # if job_ids:
    #     print(f"Found {len(job_ids)} job IDs to return.")
    #     response_packet = {"type": "source_job_ids", "data": job_ids}
    #     yield f"data: {json.dumps(response_packet, ensure_ascii=False)}\n\n"

    # # Gửi tín hiệu kết thúc stream
    # end_packet = {"type": "stream_end"}
    # yield f"data: {json.dumps(end_packet, ensure_ascii=False)}\n\n"
