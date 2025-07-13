# scripts/cleanup_scheduler.py
from .cleanup_expired_jobs import run_cleanup
import os
import sys
import time
from datetime import datetime


import schedule

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def scheduled_cleanup():
    """
    Wrapper function cho scheduled cleanup với logging
    """
    print(f"\n{'='*50}")
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Bắt đầu cleanup định kỳ...")
    print(f"{'='*50}")

    try:
        run_cleanup()
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cleanup hoàn thành thành công!")
    except Exception as e:
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Lỗi khi chạy cleanup: {e}")

    print(f"{'='*50}\n")


def main():
    """
    Thiết lập và chạy scheduler
    """
    print("🕐 Khởi động Cleanup Scheduler...")
    print("📅 Lịch trình: Chạy hàng ngày lúc 2:00 AM")
    print("🔄 Để dừng scheduler, nhấn Ctrl+C")

    # Lên lịch chạy cleanup hàng ngày lúc 2:00 AM
    schedule.every().day.at("02:00").do(scheduled_cleanup)

    # Hoặc có thể dùng các lịch trình khác:
    # schedule.every(6).hours.do(scheduled_cleanup)  # Mỗi 6 tiếng
    # schedule.every().monday.at("01:00").do(scheduled_cleanup)  # Thứ 2 hàng tuần
    # schedule.every(30).minutes.do(scheduled_cleanup)  # Mỗi 30 phút (cho test)

    print(
        f"✅ Scheduler đã được thiết lập. Lần chạy tiếp theo: {schedule.next_run()}")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Kiểm tra mỗi phút
    except KeyboardInterrupt:
        print("\n🛑 Dừng cleanup scheduler...")
        print("👋 Goodbye!")


if __name__ == "__main__":
    main()
