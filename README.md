# CareerZone AI CHATBOT

[cite\_start]Một dự án chatbot AI được thiết kế để hỗ trợ các vấn đề liên quan đến định hướng nghề nghiệp và các chính sách của công ty. [cite: 3] [cite\_start]Chatbot này tận dụng sức mạnh của các mô hình ngôn ngữ lớn (LLM) và kỹ thuật Sinh tăng cường truy xuất (Retrieval-Augmented Generation - RAG) để cung cấp những câu trả lời chính xác, phù hợp và theo ngữ cảnh từ một cơ sở tri thức đã được định sẵn. [cite: 4]

## ✨ Tính năng chính

  * [cite\_start]**API dựa trên FastAPI**: Cung cấp các endpoint hiệu suất cao và dễ sử dụng để tương tác với chatbot. [cite: 5]
  * [cite\_start]**Tích hợp đa mô hình LLM**: Sử dụng các mô hình ngôn ngữ lớn tiên tiến (Google Gemini, OpenAI qua OpenRouter) để hiểu và tạo ra các câu trả lời tự nhiên, linh hoạt. [cite: 6, 18]
  * [cite\_start]**Dịch vụ RAG thông minh**: Tăng cường năng lực của LLM bằng cách truy xuất thông tin liên quan từ cơ sở dữ liệu vector. [cite: 7] [cite\_start]Hệ thống có khả năng định tuyến (router) câu hỏi đến đúng nguồn dữ liệu (chính sách công ty hoặc tin tuyển dụng) để có câu trả lời chính xác nhất. [cite: 338, 348]
  * [cite\_start]**Xử lý bất đồng bộ với Kafka**: Sử dụng Apache Kafka để quản lý các sự kiện liên quan đến tin tuyển dụng (tạo, cập nhật, xóa) một cách hiệu quả và tách biệt, đảm bảo hệ thống luôn được cập nhật với dữ liệu mới nhất. [cite: 8]
  * [cite\_start]**Cập nhật Vector Store theo thời gian thực**: Một worker chuyên dụng lắng nghe các sự kiện từ Kafka và tự động cập nhật cơ sở dữ liệu vector (MongoDB Atlas) khi có tin tuyển dụng mới, thay đổi hoặc bị xóa. [cite: 374, 375, 376]
  * [cite\_start]**Lọc và tìm kiếm động**: Hỗ trợ lọc các tin tuyển dụng đã hết hạn trong thời gian thực ngay tại khâu truy xuất. [cite: 316, 346]
  * [cite\_start]**Cấu hình linh hoạt**: Dễ dàng tùy chỉnh các thiết lập của ứng dụng thông qua biến môi trường. [cite: 9, 11]

## 🏛️ Sơ đồ kiến trúc hệ thống


## 🛠️ Cài đặt

1.  **Clone repository:**

    ```bash
    git clone https://github.com/tuoitho/CareerZone-AI-CHATBOT.git
    cd CareerZone-AI-CHATBOT
    ```

2.  **Tạo và kích hoạt môi trường ảo:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # Trên Windows, dùng `venv\Scripts\activate`
    ```

3.  **Cài đặt các thư viện cần thiết:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Cấu hình các biến môi trường:**
    [cite\_start]Tạo một file `.env` ở thư mục gốc và điền các thông tin cần thiết. [cite: 11]

    ```env
    # MongoDB
    MONGODB_URI="your_mongodb_atlas_uri"
    DB_NAME="your_database_name"

    # Google AI
    GOOGLE_API_KEY="your_google_api_key"

    # OpenRouter AI (for OpenAI models)
    OPENROUTER_API_KEY="your_openrouter_key"
    OPENROUTER_LLM_MODEL="openai/gpt-3.5-turbo"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS="your_kafka_bootstrap_server"
    KAFKA_JOB_EVENTS_TOPIC="job_events_topic_name"
    ```

## 🚀 Sử dụng

1.  **Nạp dữ liệu ban đầu:**
    Chạy script này một lần để khởi tạo cơ sở dữ liệu vector với các chính sách và tin tuyển dụng mẫu.

    ```bash
    python scripts/initial_load.py
    ```

2.  **Chạy Kafka Consumer:**
    Mở một terminal và chạy worker để lắng nghe các sự kiện cập nhật tin tuyển dụng.

    ```bash
    python workers/kafka_consumer.py
    ```

3.  **Chạy API server:**
    Mở một terminal khác và khởi động server FastAPI.

    ```bash
    uvicorn api.main:app --reload
    ```

    API sẽ có sẵn tại `http://localhost:8000`.

4.  **Gửi yêu cầu đến API:**
    [cite\_start]Sử dụng một công cụ như `curl`, Postman hoặc file `test.http` đi kèm để gửi yêu cầu đến endpoint `/api/v1/chat`. [cite: 13]

    **Ví dụ `curl`:**

    ```bash
    curl -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -d '{
      "query": "Công ty có chính sách gì về việc đăng tin tuyển dụng?",
      "history": []
    }'
    ```

## 🤝 Đóng góp

[cite\_start]Chúng tôi luôn chào đón các đóng góp từ cộng đồng để cải thiện dự án. [cite: 13] [cite\_start]Nếu bạn muốn đóng góp, vui lòng tạo một Pull Request hoặc mở một Issue để thảo luận về các thay đổi được đề xuất. [cite: 14]