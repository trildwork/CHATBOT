# scripts/cleanup_expired_jobs.py
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pymongo.results import DeleteResult

from config import settings  # Để load env vars nếu cần
from core.db import db

# Setup logging


def setup_logging():
    """Thiết lập logging cho cleanup script"""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "cleanup.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


def run_cleanup():
    """
    Tìm và xóa tất cả các chunk của các job đã hết hạn khỏi collection vector.
    """
    try:
        jobs_collection = db["jobs_vector"]
        current_time_iso = datetime.now(timezone.utc).isoformat()

        # Query để tìm tất cả các document có 'deadline' đã qua
        # metadata.deadline được lưu dưới dạng ISO string
        query = {
            "deadline": {
                "$lt": current_time_iso
            }
        }

        logger.info(
            f"Bắt đầu dọn dẹp các job hết hạn (trước ngày {current_time_iso})...")

        # In ra số lượng job sẽ bị xóa để kiểm tra (tùy chọn)
        count_to_delete = jobs_collection.count_documents(query)
        if count_to_delete == 0:
            logger.info("Không có job hết hạn nào để dọn dẹp.")
            return

        logger.info(
            f"Tìm thấy {count_to_delete} chunk của các job đã hết hạn. Bắt đầu xóa...")

        # Thực hiện xóa
        result: DeleteResult = jobs_collection.delete_many(query)
        logger.info(
            f"Hoàn thành! Đã xóa thành công {result.deleted_count} chunk.")

        # Ghi log thống kê
        remaining_count = jobs_collection.count_documents({})
        logger.info(f"Tổng số chunk còn lại trong database: {remaining_count}")

    except Exception as e:
        logger.error(
            f"Đã xảy ra lỗi trong quá trình dọn dẹp: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Khởi động cleanup script...")
    logger.info("="*60)

    try:
        run_cleanup()
        logger.info("Script cleanup hoàn thành thành công!")
    except Exception as e:
        logger.error(f"Script cleanup thất bại: {e}")
        sys.exit(1)

    logger.info("="*60)
