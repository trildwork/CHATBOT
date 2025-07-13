# run_all.py
"""
Script master để chạy tất cả các service cùng lúc:
- FastAPI server
- Kafka consumer 
- Cleanup scheduler
"""
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


class ServiceManager:
    def __init__(self):
        self.processes = {}
        self.threads = {}
        self.running = True

    def log(self, service, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{service}] {message}")

    def start_api_server(self):
        """Khởi động FastAPI server"""
        try:
            self.log("API", "Khởi động FastAPI server...")
            cmd = [sys.executable, "-m", "uvicorn", "api.main:app",
                   "--reload", "--host", "0.0.0.0", "--port", "8000"]

            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            self.processes["api"] = process
            self.log("API", f"Server started with PID: {process.pid}")

            # Monitor process output in separate thread
            def monitor_api():
                while self.running and process.poll() is None:
                    try:
                        line = process.stdout.readline()
                        if line:
                            # Lọc bỏ các dòng không cần thiết và hiển thị logs quan trọng
                            line = line.strip()
                            if any(keyword in line.lower() for keyword in ["error", "warning", "rag service", "applying", "filter", "router chose"]):
                                self.log("API", line)
                            elif "INFO:" in line and any(keyword in line for keyword in ["started", "running", "reload"]):
                                self.log("API", line)
                    except:
                        break

            threading.Thread(target=monitor_api, daemon=True).start()

        except Exception as e:
            self.log("API", f"Lỗi khởi động API server: {e}")

    def start_kafka_consumer(self):
        """Khởi động Kafka consumer"""
        def run_kafka():
            try:
                self.log("KAFKA", "Khởi động Kafka consumer...")

                # Import và chạy kafka consumer
                from workers.kafka_consumer import start_consumer
                start_consumer()

            except Exception as e:
                self.log("KAFKA", f"Lỗi Kafka consumer: {e}")
                if self.running:
                    self.log("KAFKA", "Thử khởi động lại sau 30 giây...")
                    time.sleep(30)
                    if self.running:
                        self.start_kafka_consumer()

        thread = threading.Thread(target=run_kafka, daemon=True)
        thread.start()
        self.threads["kafka"] = thread
        self.log("KAFKA", "Kafka consumer thread started")

    def start_cleanup_scheduler(self):
        """Khởi động cleanup scheduler"""
        def run_scheduler():
            try:
                self.log("CLEANUP", "Khởi động cleanup scheduler...")

                # Import schedule và cleanup function
                import schedule

                from scripts.cleanup_expired_jobs import run_cleanup

                def scheduled_cleanup():
                    self.log("CLEANUP", "Bắt đầu cleanup job...")
                    try:
                        run_cleanup()
                        self.log("CLEANUP", "Cleanup hoàn thành thành công!")
                    except Exception as e:
                        self.log("CLEANUP", f"Lỗi cleanup: {e}")

                # Schedule cleanup hàng ngày lúc 2:00 AM
                schedule.every().day.at("02:00").do(scheduled_cleanup)

                # Có thể uncomment dòng dưới để test (chạy mỗi 5 phút)
                # schedule.every(5).minutes.do(scheduled_cleanup)

                self.log(
                    "CLEANUP", f"Scheduler thiết lập xong. Lần chạy tiếp theo: {schedule.next_run()}")

                while self.running:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute

            except Exception as e:
                self.log("CLEANUP", f"Lỗi scheduler: {e}")

        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()
        self.threads["cleanup"] = thread
        self.log("CLEANUP", "Cleanup scheduler thread started")

    def start_all(self):
        """Khởi động tất cả services"""
        self.log("MASTER", "🚀 Khởi động tất cả services...")
        self.log("MASTER", "="*60)

        # Start API server
        self.start_api_server()
        time.sleep(2)  # Wait a bit for API to start

        # Start Kafka consumer
        self.start_kafka_consumer()
        time.sleep(1)

        # Start cleanup scheduler
        self.start_cleanup_scheduler()
        time.sleep(1)

        self.log("MASTER", "✅ Tất cả services đã được khởi động!")
        self.log("MASTER", "📊 Services đang chạy:")
        self.log("MASTER", "   - API Server: http://localhost:8000")
        self.log("MASTER", "   - Kafka Consumer: Listening for job events")
        self.log("MASTER", "   - Cleanup Scheduler: Daily at 2:00 AM")
        self.log("MASTER", "")
        self.log("MASTER", "🛑 Nhấn Ctrl+C để dừng tất cả services")
        self.log("MASTER", "="*60)

    def stop_all(self):
        """Dừng tất cả services"""
        self.log("MASTER", "🛑 Đang dừng tất cả services...")
        self.running = False

        # Stop processes
        for name, process in self.processes.items():
            try:
                self.log("MASTER", f"Dừng {name} process...")
                process.terminate()
                process.wait(timeout=10)
                self.log("MASTER", f"✅ {name} đã dừng")
            except Exception as e:
                self.log("MASTER", f"❌ Lỗi khi dừng {name}: {e}")
                try:
                    process.kill()
                except:
                    pass

        # Wait for threads to finish
        for name, thread in self.threads.items():
            if thread.is_alive():
                self.log("MASTER", f"Chờ {name} thread kết thúc...")
                thread.join(timeout=5)

        self.log("MASTER", "👋 Tất cả services đã dừng!")

    def run(self):
        """Chạy service manager"""
        def signal_handler(signum, frame):
            self.stop_all()
            sys.exit(0)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self.start_all()

            # Keep main thread alive
            while self.running:
                time.sleep(1)

                # Check if API process is still running
                if "api" in self.processes:
                    if self.processes["api"].poll() is not None:
                        self.log("API", "❌ API server đã dừng bất ngờ!")
                        break

        except KeyboardInterrupt:
            pass
        finally:
            self.stop_all()


def main():
    """Main function"""
    print("🎯 CareerZone Service Manager")
    print("============================")
    print("Khởi động tất cả services: API + Kafka + Cleanup Scheduler")
    print()

    # Kiểm tra dependencies
    try:
        import schedule
        import uvicorn
        print("✅ Dependencies OK")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Chạy: pip install -r requirements.txt")
        return

    # Kiểm tra file .env
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️  Cảnh báo: Không tìm thấy file .env")
        print("Tạo file .env với các biến môi trường cần thiết")

    manager = ServiceManager()
    manager.run()


if __name__ == "__main__":
    main()
