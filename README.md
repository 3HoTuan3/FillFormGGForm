# Auto Fill Google Form — Hướng dẫn nhanh

Tổng quan  
Repository này chứa các script tự động điền Google Form bằng Selenium. Có 2 mode: `fill_Form_fast.py` (nhanh) và `fill_Form_slow.py` (chậm). File chạy chính để điều phối là `CodeFillForm\Main_fillForm.py`.

Yêu cầu hệ thống
- Windows, Python 3.8+ (khuyến nghị 3.10+)
- Google Chrome cài sẵn (webdriver_manager sẽ tự cài driver tương thích)

Cài đặt và kích hoạt virtual environment (Windows)
1. Mở PowerShell hoặc Command Prompt tại thư mục project:
   - cd "d:\Document(D)\Python\Linh_Tinh_Che_Code"
2. Tạo venv và bật:
   - python -m venv .venv
   - .venv\Scripts\activate

Cài thư viện
1. Cập nhật pip rồi cài:
   - python -m pip install --upgrade pip
   - pip install -r requirements.txt

File requirements (xem ví dụ trong repository)
- selenium
- webdriver-manager

Cấu hình nhanh
- Mở `CodeFillForm\Main_fillForm.py` và chỉnh:
  - MODE = "fast" hoặc "slow"
  - DURATION_MINUTES = tổng phút muốn chạy
  - FORMS_PER_BATCH = số form mở song song trong 1 batch
  - WAIT_MINUTES_BETWEEN_BATCH = phút chờ giữa 2 batch

Chạy chương trình (recommended)
- Trong venv, chạy:
  - python CodeFillForm\Main_fillForm.py
- Trong lúc chạy muốn dừng nhanh: gõ `q` rồi Enter -> chương trình dừng và in thống kê.

Chạy 1 file form trực tiếp (dành cho người không rành code)
- Mở venv rồi chạy 1 trong 2 file:
  - python CodeFillForm\fill_Form_fast.py
  - python CodeFillForm\fill_Form_slow.py
- Lưu ý: mỗi file sẽ mở Chrome, tự thực hiện điền và submit.

Ghi chú vận hành
- webdriver_manager sẽ tự tải ChromeDriver tương thích; cần Chrome đã cài trên máy.
- Nếu cần thay link form, chỉnh biến `FORM_URL` trong 2 file `fill_Form_*.py`.
- Kiểm tra popup/permission của Chrome nếu script không tương tác được.

Vấn đề thường gặp
- Lỗi không tìm thấy ChromeDriver: kiểm tra Chrome đã cài và phiên bản Python venv đang active.
- Script không thấy câu hỏi: form layout thay đổi → cần điều chỉnh selectors trong code.

Liên hệ
- Thay đổi nhanh: chỉnh biến cấu hình trong `Main_fillForm.py` và `FORM_URL` trong file điền form.