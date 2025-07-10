# scripts/cleanup_expired_jobs.py
import os
import sys
from datetime import datetime, timezone
from pymongo.results import DeleteResult

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.db import db
from config import settings # Để load env vars nếu cần

def run_cleanup():
    """
    Tìm và xóa tất cả các chunk của các job đã hết hạn khỏi collection vector.
    """
    jobs_collection = db["jobs_vector"]
    current_time_iso = datetime.now(timezone.utc).isoformat()

    # Query để tìm tất cả các document có 'deadline' đã qua
    # metadata.deadline được lưu dưới dạng ISO string
    query = {
        "metadata.deadline": {
            "$lt": current_time_iso
        }
    }

    print(f"Bắt đầu dọn dẹp các job hết hạn (trước ngày {current_time_iso})...")
    
    # In ra số lượng job sẽ bị xóa để kiểm tra (tùy chọn)
    count_to_delete = jobs_collection.count_documents(query)
    if count_to_delete == 0:
        print("Không có job hết hạn nào để dọn dẹp.")
        return

    print(f"Tìm thấy {count_to_delete} chunk của các job đã hết hạn. Bắt đầu xóa...")

    # Thực hiện xóa
    try:
        result: DeleteResult = jobs_collection.delete_many(query)
        print(f"Hoàn thành! Đã xóa thành công {result.deleted_count} chunk.")
    except Exception as e:
        print(f"Đã xảy ra lỗi trong quá trình dọn dẹp: {e}")

if __name__ == "__main__":
    run_cleanup()
