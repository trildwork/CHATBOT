# start.py
"""
Script đơn giản để khởi động nhanh tất cả services
Dành cho development - không có monitoring phức tạp
"""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))


def run_api():
    """Chạy FastAPI server"""
    print("🌐 Starting API server...")
    os.system(
        f"cd {project_root} && python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")


def run_kafka():
    """Chạy Kafka consumer"""
    print("📨 Starting Kafka consumer...")
    try:
        from workers.kafka_consumer import start_consumer
        start_consumer()
    except Exception as e:
        print(f"❌ Kafka error: {e}")


def run_scheduler():
    """Chạy cleanup scheduler"""
    print("⏰ Starting cleanup scheduler...")
    try:
        import schedule

        from scripts.cleanup_expired_jobs import run_cleanup

        # Schedule cleanup - có thể thay đổi thời gian ở đây
        schedule.every().day.at("02:00").do(run_cleanup)  # 2:00 AM hàng ngày
        # schedule.every(30).minutes.do(run_cleanup)  # Uncomment để test mỗi 30 phút

        print(f"📅 Next cleanup: {schedule.next_run()}")

        while True:
            schedule.run_pending()
            time.sleep(60)
    except Exception as e:
        print(f"❌ Scheduler error: {e}")


def main():
    print("🚀 CareerZone - Starting All Services")
    print("=====================================")
    print("Services: API + Kafka + Cleanup")
    print("Press Ctrl+C to stop all services")
    print()

    try:
        # Start all services in separate threads
        threads = []

        # API Server thread
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        threads.append(api_thread)

        # Wait a bit for API to start
        time.sleep(3)

        # Kafka Consumer thread
        kafka_thread = threading.Thread(target=run_kafka, daemon=True)
        kafka_thread.start()
        threads.append(kafka_thread)

        # Cleanup Scheduler thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        threads.append(scheduler_thread)

        print("✅ All services started!")
        print("🌐 API: http://localhost:8000")
        print("📨 Kafka: Listening for events")
        print("⏰ Scheduler: Cleanup jobs scheduled")
        print("\n🛑 Press Ctrl+C to stop...")

        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping all services...")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
