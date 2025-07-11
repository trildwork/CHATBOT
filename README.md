# CareerZone AI CHATBOT

Một dự án chatbot AI được thiết kế để hỗ trợ các vấn đề liên quan đến định hướng nghề nghiệp và các chính sách của công ty. Chatbot này tận dụng sức mạnh của các mô hình ngôn ngữ lớn (Large Language Models – LLM) cùng kỹ thuật Retrieval‑Augmented Generation (RAG) để cung cấp những câu trả lời chính xác, phù hợp ngữ cảnh từ cơ sở tri thức đã định sẵn.

## 🏛️ Sơ đồ kiến trúc hệ thống

<div align="center">
  <img src="https://github.com/user-attachments/assets/ef1ffa9c-1528-4fa1-9e35-17b479cd821b" width="466" alt="Architecture" />
</div>

## 🛠️ Cài đặt

1. **Clone repository**

   ```bash
   git clone https://github.com/tuoitho/CareerZone-AI-CHATBOT.git
   cd CareerZone-AI-CHATBOT
   ```

2. **Tạo và kích hoạt môi trường ảo**

   ```bash
   python -m venv venv
   # Trên Windows, dùng:
   # venv\Scripts\activate
   source venv/bin/activate
   ```

3. **Cài đặt các thư viện cần thiết**

   ```bash
   pip install -r requirements.txt
   ```

4. **Cấu hình biến môi trường**

   Tạo file `.env` ở thư mục gốc và khai báo:

   ```env
   # MongoDB
   MONGODB_URI="your_mongodb_atlas_uri"
   DB_NAME="your_database_name"

   # Google AI
   GOOGLE_API_KEY="your_google_api_key"

   # OpenRouter (OpenAI models)
   OPENROUTER_API_KEY="your_openrouter_key"
   OPENROUTER_LLM_MODEL="openai/gpt-3.5-turbo"

   # Kafka
   KAFKA_BOOTSTRAP_SERVERS="your_kafka_bootstrap_server"
   KAFKA_JOB_EVENTS_TOPIC="job_events_topic_name"
   ```

## 🚀 Sử dụng

1. **Nạp dữ liệu ban đầu** (chỉ thực hiện một lần)

   ```bash
   python scripts/initial_load.py
   ```

2. **Chạy Kafka Consumer**

   ```bash
   python workers/kafka_consumer.py
   ```

3. **Khởi động API server**

   ```bash
   uvicorn api.main:app --reload
   ```

   API sẽ sẵn sàng tại `http://localhost:8000`.

4. **Gửi yêu cầu đến API**

   Ví dụ với `curl`:

   ```bash
   curl -X POST http://localhost:8000/api/v1/chat \
        -H "Content-Type: application/json" \
        -d '{
          "query": "Công ty có chính sách gì về việc đăng tin tuyển dụng?",
          "history": []
        }'
   ```

## 🤝 Đóng góp

Chúng tôi luôn chào đón đóng góp từ cộng đồng để cải thiện dự án. Nếu bạn muốn đóng góp, vui lòng tạo Pull Request hoặc mở Issue để thảo luận trước về thay đổi.
