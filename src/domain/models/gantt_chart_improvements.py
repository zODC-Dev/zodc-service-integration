"""
Cải tiến đề xuất cho Gantt Chart Calculation

File này chứa các gợi ý để cải thiện và đơn giản hóa tính toán Gantt Chart
trong hệ thống zodc-integration.
"""

from datetime import datetime, time, timedelta
from typing import List, Dict, Tuple

# Các vấn đề chính được phát hiện:
# 1. Phức tạp không cần thiết trong tính toán thời gian làm việc
# 2. Lỗi về timezone khi so sánh các mốc thời gian
# 3. Vòng lặp không cần thiết trong việc xử lý quan hệ cha-con
# 4. Quá nhiều xử lý đặc biệt cho các trường hợp biên

# Phương pháp cải tiến được đề xuất:


class GanttChartCalculationImprovements:
    """Các đề xuất cải tiến cho tính toán Gantt Chart"""

    @staticmethod
    def verify_timezone_consistency(all_dates: List[datetime]) -> bool:
        """Kiểm tra xem tất cả các ngày có cùng múi giờ không"""
        if not all_dates:
            return True

        first_tz = all_dates[0].tzinfo
        return all(d.tzinfo == first_tz for d in all_dates)

    @staticmethod
    def calculate_effective_working_hours(
        hours_per_day: int,
        lunch_break_minutes: int
    ) -> float:
        """Tính toán số giờ làm việc hiệu quả trong một ngày"""
        return hours_per_day - (lunch_break_minutes / 60)

    @staticmethod
    def simplify_workday_handling(
        current_time: datetime,
        work_start: time,
        work_end: time,
        include_weekends: bool
    ) -> datetime:
        """Đơn giản hóa việc xử lý ngày làm việc"""
        # Xử lý cuối tuần
        if not include_weekends and current_time.weekday() >= 5:
            # Tính số ngày để đến thứ Hai tiếp theo
            days_to_add = (7 - current_time.weekday() + 1) % 7
            if days_to_add == 0:
                days_to_add = 1
            current_time = current_time + timedelta(days=days_to_add)
            # Đặt về thời gian bắt đầu làm việc
            return current_time.replace(
                hour=work_start.hour,
                minute=work_start.minute,
                second=0,
                microsecond=0
            )

        # Xử lý ngoài giờ làm việc
        current_time_time = current_time.time()

        # Trước giờ làm việc
        if current_time_time < work_start:
            return current_time.replace(
                hour=work_start.hour,
                minute=work_start.minute,
                second=0,
                microsecond=0
            )

        # Sau giờ làm việc
        if current_time_time >= work_end:
            next_day = current_time + timedelta(days=1)
            # Nếu ngày tiếp theo là cuối tuần và không tính cuối tuần
            if not include_weekends and next_day.weekday() >= 5:
                days_to_add = (8 - next_day.weekday()) % 7
                next_day = next_day + timedelta(days=days_to_add)

            return next_day.replace(
                hour=work_start.hour,
                minute=work_start.minute,
                second=0,
                microsecond=0
            )

        # Hiện tại nằm trong giờ làm việc
        return current_time

    @staticmethod
    def simplified_parent_child_handling(
        tasks: Dict[str, Tuple[datetime, datetime]],
        parent_child_relationships: Dict[str, List[str]]
    ) -> Dict[str, Tuple[datetime, datetime]]:
        """Đơn giản hóa xử lý quan hệ cha-con trong Gantt Chart"""
        # Đối với mỗi mối quan hệ cha-con, đảm bảo cha kết thúc sau con
        updated_tasks = tasks.copy()

        for parent_id, child_ids in parent_child_relationships.items():
            if parent_id not in updated_tasks:
                continue

            parent_start, parent_end = updated_tasks[parent_id]
            latest_child_end = parent_end

            # Tìm thời gian kết thúc trễ nhất trong các con
            for child_id in child_ids:
                if child_id in updated_tasks:
                    _, child_end = updated_tasks[child_id]
                    if child_end > latest_child_end:
                        latest_child_end = child_end

            # Cập nhật thời gian kết thúc của cha nếu cần
            if latest_child_end > parent_end:
                updated_tasks[parent_id] = (parent_start, latest_child_end)

        return updated_tasks


# Đề xuất cải tiến chung:
"""
1. Đơn giản hóa tính toán thời gian:
   - Giảm số lượng phương thức và hàm tiện ích
   - Đơn giản hóa cách tính toán giờ làm việc và thời gian hoàn thành
   - Xử lý nhất quán trong việc bỏ qua cuối tuần và giờ nghỉ

2. Sửa lỗi so sánh múi giờ:
   - Đảm bảo tất cả các datetime đều có cùng thông tin múi giờ
   - Thêm kiểm tra và chuẩn hóa đầu vào

3. Tối ưu hóa xử lý quan hệ cha-con:
   - Thay thế vòng lặp lặp lại bằng một lần quét đơn giản
   - Sửa lại logic để xử lý các trường hợp đặc biệt tốt hơn

4. Đơn giản hóa xử lý ước tính thời gian:
   - Sử dụng các giá trị mặc định đơn giản hơn cho các issue có ước tính bằng 0
   - Giảm sự phức tạp trong việc tính toán thời gian cho các loại issue khác nhau

5. Cải thiện khả năng đọc và bảo trì:
   - Thêm ghi log chi tiết để dễ dàng gỡ lỗi
   - Đơn giản hóa logic phức tạp
   - Tách logic thành các phương thức riêng biệt với trách nhiệm rõ ràng
"""
