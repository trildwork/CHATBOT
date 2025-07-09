from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.documents import Document
from core.db import db
from core.llm import embedding_model


def load_policies():
    """Tải, chia nhỏ và nạp dữ liệu chính sách."""
    print("--- Bắt đầu xử lý file chính sách ---")
    # 1. Load
    loader = TextLoader("data/policies.txt", encoding="utf-8")
    docs = loader.load()

    # 2. Split
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(docs)
    print(f"Đã chia file chính sách thành {len(chunks)} chunks.")

    # 3. Store
    policies_collection = db["policies_vector"]
    # Xóa dữ liệu cũ để tránh trùng lặp
    policies_collection.delete_many({})

    MongoDBAtlasVectorSearch.from_documents(
        documents=chunks,
        embedding=embedding_model,
        collection=policies_collection,
        index_name="policies_vector_index"
    )
    print("--- Hoàn thành nạp dữ liệu chính sách ---")


def load_jobs_and_guides():
    """Hàm giả lập để nạp dữ liệu jobs và guides."""
    print("--- Bắt đầu nạp dữ liệu giả lập cho Jobs và Guides ---")

    # Dữ liệu Jobs
    jobs_collection = db["jobs_vector"]
    jobs_collection.delete_many({})
    job_docs = [
        Document(page_content="Senior Python Developer. Yêu cầu 5 năm kinh nghiệm với Django, Flask. Ưu tiên có kinh nghiệm với DevOps.", metadata={"source": "jobs", "title": "Senior Python Developer"}),
        Document(page_content="Junior Frontend Developer (ReactJS). Yêu cầu kiến thức về HTML, CSS, JavaScript và React. Lương cạnh tranh.", metadata={"source": "jobs", "title": "Junior Frontend Developer"}),
        Document(page_content="Data Scientist. Cần có kinh nghiệm làm việc với các mô hình Machine Learning, Deep Learning. Sử dụng thành thạo Python và các thư viện như aiohttp, aio-pika.", metadata={"source": "jobs", "title": "Data Scientist"}),
        Document(page_content="Product Manager. Quản lý vòng đời sản phẩm, từ lên ý tưởng đến ra mắt. Yêu cầu kỹ năng giao tiếp tốt.", metadata={"source": "jobs", "title": "Product Manager"}),
        Document(page_content="UI/UX Designer. Thiết kế giao diện cho các ứng dụng web và di động. Sử dụng thành thạo Figma, Sketch.", metadata={"source": "jobs", "title": "UI/UX Designer"}),
        Document(page_content="DevOps Engineer. Xây dựng và duy trì hệ thống CI/CD. Kinh nghiệm với Docker, Kubernetes là một lợi thế.", metadata={"source": "jobs", "title": "DevOps Engineer"}),
        Document(page_content="Business Analyst. Phân tích yêu cầu nghiệp vụ và chuyển thành các yêu cầu kỹ thuật. Cần có kiến thức về SQL.", metadata={"source": "jobs", "title": "Business Analyst"}),
        Document(page_content="Quality Assurance Engineer. Kiểm thử phần mềm, viết test case và báo cáo lỗi. Có kinh nghiệm với kiểm thử tự động.", metadata={"source": "jobs", "title": "Quality Assurance Engineer"}),
        Document(page_content="Technical Writer. Viết tài liệu kỹ thuật, hướng dẫn sử dụng cho các sản phẩm phần mềm.", metadata={"source": "jobs", "title": "Technical Writer"}),
        Document(page_content="Marketing Manager. Lập kế hoạch và triển khai các chiến dịch marketing online. Có kinh nghiệm về SEO, SEM.", metadata={"source": "jobs", "title": "Marketing Manager"}),
    ]
    MongoDBAtlasVectorSearch.from_documents(job_docs, embedding_model, collection=jobs_collection, index_name="jobs_vector_index")
    print(f"Đã nạp {len(job_docs)} jobs mẫu.")

    # Dữ liệu Guides
    guides_collection = db["guides_vector"]
    guides_collection.delete_many({})
    guide_docs = [
        Document(page_content="Hướng dẫn tạo tài khoản: Truy cập trang đăng ký, điền đầy đủ thông tin và nhấn nút 'Đăng ký'.", metadata={"source": "guides", "title": "Hướng dẫn tạo tài khoản"}),
        Document(page_content="Cách đặt lại mật khẩu: Vào trang đăng nhập, nhấn 'Quên mật khẩu', nhập email và làm theo hướng dẫn.", metadata={"source": "guides", "title": "Cách đặt lại mật khẩu"}),
        Document(page_content="Làm thế nào để tạo CV: Đăng nhập vào tài khoản, vào mục 'Quản lý CV' và chọn 'Tạo CV mới'.", metadata={"source": "guides", "title": "Làm thế nào để tạo CV"}),
    ]
    MongoDBAtlasVectorSearch.from_documents(guide_docs, embedding_model, collection=guides_collection, index_name="guides_vector_index")
    print(f"Đã nạp {len(guide_docs)} guides mẫu.")
    
    print("--- Hoàn thành nạp dữ liệu giả lập ---")


if __name__ == "__main__":
    load_policies()
    load_jobs_and_guides()
