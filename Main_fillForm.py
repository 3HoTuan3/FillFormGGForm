import subprocess
import time
import sys
import threading
from datetime import datetime, timedelta

# ===========================
# CẤU HÌNH CHÍNH
# ===========================

# Chọn mode: "fast" hoặc "slow"
MODE = "fast"  # Thay đổi thành "slow" để chạy chậm

# Số phút muốn chạy chương trình (ví dụ: 2, 5, 10...)
DURATION_MINUTES = 10

# Số form cần mở song song trong mỗi lần chạy (ví dụ: 1, 2, 3, 4...)
FORMS_PER_BATCH = 2

# Thời gian chờ giữa các batch (phút) (ví dụ: 2, 5, 10...)
WAIT_MINUTES_BETWEEN_BATCH = 2

# ===========================
# BIẾN TOÀN CỤC
# ===========================

stop_flag = False  # Cờ để dừng chương trình

# ===========================
# LOGIC CHÍNH
# ===========================

def get_script_path(mode):
    """Trả về đường dẫn file script theo mode được chọn"""
    if mode.lower() == "fast":
        return "fill_Form_Fast.py"
    elif mode.lower() == "slow":
        return "fill_Form_slow.py"
    else:
        print(f"❌ Mode '{mode}' không hợp lệ! Chỉ dùng 'fast' hoặc 'slow'")
        sys.exit(1)

def listen_for_quit():
    """Lắng nghe nhập từ bàn phím để thoát"""
    global stop_flag
    while not stop_flag:
        try:
            user_input = input()
            if user_input.lower() == 'q':
                print("\n\n⚠️  Người dùng yêu cầu dừng chương trình!")
                stop_flag = True
                break
        except EOFError:
            break
        except Exception as e:
            pass

def run_form_script(script_path, form_number, batch_number):
    """Chạy script điền form"""
    global stop_flag
    
    if stop_flag:
        return False
    
    print(f"\n{'='*60}")
    print(f"🔄 Batch #{batch_number} - Form #{form_number}")
    print(f"   Script: {script_path}")
    print(f"   Thời gian bắt đầu: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=False
        )
        print(f"✅ Batch #{batch_number} - Form #{form_number} hoàn thành!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Batch #{batch_number} - Form #{form_number} gặp lỗi: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Không tìm thấy file: {script_path}")
        return False

def run_batch_parallel(script_path, batch_number, forms_count):
    """Chạy nhiều form song song trong một batch"""
    global stop_flag
    
    threads = []
    completed = [0]  # Dùng list để có thể modify trong nested function
    
    print(f"\n{'#'*60}")
    print(f"📦 BATCH #{batch_number} - Bắt đầu {forms_count} form song song")
    print(f"   Thời gian bắt đầu: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'#'*60}\n")
    
    # Tạo thread cho mỗi form
    for form_num in range(1, forms_count + 1):
        if stop_flag:
            break
        
        thread = threading.Thread(
            target=lambda fn=form_num: (
                run_form_script(script_path, fn, batch_number),
                completed.append(1) if run_form_script(script_path, fn, batch_number) else None
            ),
            daemon=False
        )
        threads.append(thread)
        thread.start()
        
        # Chờ 1 giây giữa việc tạo các thread
        time.sleep(1)
    
    # Chờ tất cả các thread hoàn thành
    for thread in threads:
        thread.join()
    
    forms_completed = len([x for x in completed if x == 1])
    print(f"\n✅ Batch #{batch_number} hoàn thành: {forms_completed}/{forms_count} form")
    
    return forms_completed

def main():
    """Hàm chính"""
    global stop_flag
    
    print("\n" + "="*60)
    print("🚀 CHƯƠNG TRÌNH ĐIỀN GOOGLE FORM TỰ ĐỘNG")
    print("="*60)
    print(f"⚙️  Cấu HÌNH:")
    print(f"   - Mode: {MODE}")
    print(f"   - Tổng thời gian chạy: {DURATION_MINUTES} phút")
    print(f"   - Số form mỗi lần: {FORMS_PER_BATCH} form (song song)")
    print(f"   - Thời gian chờ giữa batch: {WAIT_MINUTES_BETWEEN_BATCH} phút")
    print(f"   - Thời gian bắt đầu: {datetime.now().strftime('%H:%M:%S')}")
    print("="*60)
    print(f"\n💡 Để dừng chương trình, nhập 'q' và nhấn Enter")
    print("="*60 + "\n")
    
    # Bắt đầu thread lắng nghe input từ người dùng
    input_thread = threading.Thread(target=listen_for_quit, daemon=True)
    input_thread.start()
    
    # Tính thời gian kết thúc
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=DURATION_MINUTES)
    
    script_path = get_script_path(MODE)
    total_forms_completed = 0
    batch_number = 1
    
    while datetime.now() < end_time and not stop_flag:
        # Chạy batch với nhiều form song song
        forms_completed = run_batch_parallel(script_path, batch_number, FORMS_PER_BATCH)
        total_forms_completed += forms_completed
        
        # Tính thời gian còn lại
        time_left = end_time - datetime.now()
        
        if time_left.total_seconds() > 0 and not stop_flag:
            minutes_left = int(time_left.total_seconds() / 60)
            seconds_left = int(time_left.total_seconds() % 60)
            print(f"\n⏱️  Thời gian còn lại: {minutes_left}m {seconds_left}s")
            print(f"📊 Tổng form hoàn thành: {total_forms_completed} form")
            
            # Chờ giữa các batch
            wait_seconds = WAIT_MINUTES_BETWEEN_BATCH * 60
            batch_number += 1
            
            print(f"\n⏸️  Chờ {WAIT_MINUTES_BETWEEN_BATCH} phút trước batch tiếp theo...")
            
            # Chờ với khả năng kiểm tra stop_flag
            start_wait = datetime.now()
            while (datetime.now() - start_wait).total_seconds() < wait_seconds and not stop_flag:
                time.sleep(1)
                remaining_wait = wait_seconds - (datetime.now() - start_wait).total_seconds()
                if int(remaining_wait) % 10 == 0 and int(remaining_wait) > 0:
                    print(f"   Chờ {int(remaining_wait)}s nữa...")
        else:
            if stop_flag:
                print(f"\n⏰ Nhận được yêu cầu dừng!")
            else:
                print(f"\n⏰ Hết thời gian!")
            break
    
    # Kết thúc
    end_actual = datetime.now()
    duration = (end_actual - start_time).total_seconds() / 60
    
    print(f"\n\n{'='*60}")
    if stop_flag:
        print(f"🛑 CHƯƠNG TRÌNH ĐÃ ĐƯỢC DỪNG BỞI NGƯỜI DÙNG")
    else:
        print(f"🏁 CHƯƠNG TRÌNH KẾT THÚC")
    print(f"{'='*60}")
    print(f"📊 THỐNG KÊ CUỐI CÙNG:")
    print(f"   - Tổng form hoàn thành: {total_forms_completed} form")
    print(f"   - Tổng batch: {batch_number - 1}")
    print(f"   - Thời gian thực tế: {duration:.1f} phút")
    print(f"   - Thời gian kết thúc: {end_actual.strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()