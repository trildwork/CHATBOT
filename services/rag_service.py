from typing import List

from langchain.chains import ConversationalRetrievalChain
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser
from langchain.chains.router.multi_prompt_prompt import MULTI_PROMPT_ROUTER_TEMPLATE
from langchain.memory import ConversationBufferMemory
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_mongodb import MongoDBAtlasVectorSearch

from core.db import db
from core.llm import embedding_model, llm

# Dictionary để lưu memory cho mỗi session
chat_histories = {}


class MultiSourceRetriever(BaseRetriever):
    """Retriever tùy chỉnh chứa logic router."""
    retrievers: dict
    llm_chain: LLMRouterChain

    def _get_relevant_documents(self, query: str, *, run_manager) -> List[Document]:
        """Use router chain to determine which retriever to use."""
        result = self.llm_chain.invoke({"input": query})
        destination = result['destination']
        if destination in self.retrievers:
            print(f"Router chose: {destination}")
            return self.retrievers[destination]._get_relevant_documents(query, run_manager=run_manager)
        else:
            print("Router could not choose a destination.")
            return []


def get_conversational_rag_chain(session_id: str):
    vs_jobs = MongoDBAtlasVectorSearch(
        collection=db["jobs_vector"],
        embedding=embedding_model,
        index_name="default"
    )
    vs_policies = MongoDBAtlasVectorSearch(
        collection=db["policies_vector"],
        embedding=embedding_model,
        index_name="default"
    )
    vs_guides = MongoDBAtlasVectorSearch(
        collection=db["guides_vector"],
        embedding=embedding_model,
        index_name="default"
    )

    retriever_infos = [
        {
            "name": "recruitment",
            "description": "Hữu ích cho các câu hỏi về tuyển dụng, tìm kiếm công việc, ứng viên và hồ sơ.",
        },
        {
            "name": "company_policies",
            "description": "Hữu ích cho các câu hỏi về quy định, điều khoản dịch vụ, chính sách bảo mật của công ty.",
        },
        {
            "name": "usage_guides",
            "description": "Hữu ích cho các câu hỏi về cách sử dụng các tính năng trên website, ví dụ: cách đăng ký, đặt lại mật khẩu, tạo CV.",
        }
    ]

    from langchain.prompts import PromptTemplate
    router_template = MULTI_PROMPT_ROUTER_TEMPLATE.format(
        destinations="\n".join(
            [f'{r["name"]}: {r["description"]}' for r in retriever_infos])
    )
    router_prompt = PromptTemplate(
        template=router_template,
        input_variables=["input"],
        output_parser=RouterOutputParser(),
    )
    router_chain = LLMRouterChain.from_llm(llm, router_prompt)

    multi_retriever = MultiSourceRetriever(
        retrievers={
            "recruitment": vs_jobs.as_retriever(),
            "company_policies": vs_policies.as_retriever(),
            "usage_guides": vs_guides.as_retriever()
        },
        llm_chain=router_chain
    )

    if session_id not in chat_histories:
        chat_histories[session_id] = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True, output_key='answer'
        )
    memory = chat_histories[session_id]

    qa_template = """Bạn là "CareerConnect AI", một trợ lý tuyển dụng ảo thông minh và chuyên nghiệp.
    Nhiệm vụ của bạn là hỗ trợ người dùng về các vấn đề liên quan đến tuyển dụng, chính sách công ty và hướng dẫn sử dụng website.
    Sử dụng những đoạn ngữ cảnh được cung cấp dưới đây để trả lời câu hỏi của người dùng một cách chính xác và chi tiết.
    Nếu ngữ cảnh không chứa thông tin cần thiết để trả lời, hãy lịch sự nói rằng: "Tôi chưa có thông tin về vấn đề này. Bạn có thể hỏi câu khác được không?".
    Tuyệt đối không được bịa đặt thông tin. Luôn trả lời bằng tiếng Việt.

    NGỮ CẢNH:
    ---
    {context}
    ---

    CÂU HỎI: {question}

    TRẢ LỜI:"""
    QA_PROMPT = PromptTemplate(template=qa_template, input_variables=["context", "question"])
    
    from langchain.chains.llm import LLMChain
    from langchain.chains.combine_documents.stuff import StuffDocumentsChain

    llm_chain = LLMChain(llm=llm, prompt=QA_PROMPT)
    combine_docs_chain = StuffDocumentsChain(
        llm_chain=llm_chain, document_variable_name="context"
    )
    from langchain.prompts import PromptTemplate
    _template = """
    Bạn là một trợ lý AI tuyển dụng chuyên nghiệp và thân thiện của CareerConnect. Hãy luôn trả lời bằng tiếng Việt.

Với lịch sử trò chuyện sau đây và một câu hỏi theo sau, hãy diễn đạt lại câu hỏi đó thành một câu hỏi độc lập.

Lịch sử trò chuyện:
{chat_history}

Câu hỏi theo sau: {question}
Câu hỏi độc lập:"""
    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_template)

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=multi_retriever,
        memory=memory,
        # condense_question_prompt=CONDENSE_QUESTION_PROMPT,
        verbose=True,
        question_generator=LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT), # Cung cấp question_generator
        combine_docs_chain=combine_docs_chain, # Cung cấp combine_docs_chain

        return_source_documents=True
    )
    return chain


def process_query(query: str, session_id: str) -> str:
    chain = get_conversational_rag_chain(session_id)
    result = chain.invoke({"question": query})
    return result.get("answer", "Lỗi xử lý.")
