import time
import random
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException

# ================= CẤU HÌNH =================
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScBFNB5Y_cGG2ZXe3ekmHwnq3tPSHqHckhMi9CnGPwanzBDGw/viewform"

# ================= HÀM HỖ TRỢ =================
def scroll_to_element(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
        time.sleep(0.3)
    except: pass

def force_click(driver, element):
    """Click bằng JS để chắc chắn ăn"""
    try:
        driver.execute_script("arguments[0].click();", element)
    except:
        try:
            element.click()
        except: pass
    time.sleep(0.2)

def get_visible_questions(driver):
    """Lấy danh sách các câu hỏi đang hiển thị trên màn hình"""
    # Chờ một chút để DOM ổn định
    time.sleep(1)
    try:
        # Google Form dùng role='listitem' cho khung câu hỏi
        items = driver.find_elements(By.CSS_SELECTOR, "div[role='listitem']")
        # Chỉ lấy các câu hỏi đang hiển thị (để tránh lấy nhầm câu hỏi của trang trước/sau ẩn đi)
        visible_items = [item for item in items if item.is_displayed()]
        return visible_items
    except:
        return []

def fill_question(driver, question_element, q_index):
    """Xử lý điền 1 câu hỏi bất kỳ (Radio hoặc Checkbox)"""
    try:
        # Tìm các tùy chọn (Radio hoặc Checkbox)
        opts = question_element.find_elements(By.CSS_SELECTOR, "div[role='radio']")
        q_type = "RADIO"
        
        if not opts:
            opts = question_element.find_elements(By.CSS_SELECTOR, "div[role='checkbox']")
            q_type = "CHECKBOX"
        
        # Nếu không tìm thấy role chuẩn, thử tìm label (cho các dạng form cũ hoặc đặc biệt)
        if not opts:
            opts = question_element.find_elements(By.TAG_NAME, "label")
            q_type = "LABEL"

        if not opts:
            print(f"   [!] Câu {q_index+1}: Không tìm thấy đáp án để chọn (Có thể là câu Text input).")
            return

        # Lọc các option bị ẩn (nếu có)
        valid_opts = [o for o in opts if o.is_displayed()]
        if not valid_opts:
            return

        # LOGIC CHỌN
        if q_type == "CHECKBOX":
            # Checkbox: Chọn ngẫu nhiên từ 1 đến 3 ô
            num_to_pick = random.randint(1, min(3, len(valid_opts)))
            picks = random.sample(valid_opts, num_to_pick)
            for p in picks:
                scroll_to_element(driver, p)
                force_click(driver, p)
        else:
            # Radio: Chọn 1
            # Logic: Né option cuối cùng nếu nó là mục "Khác" (thường có input text đi kèm)
            # Google Form mục "Khác" thường có class khác biệt hoặc input text bên trong
            # Ở đây ta đơn giản chọn random, nếu trúng mục Khác thì chấp nhận (hoặc giới hạn index)
            
            # Ưu tiên chọn các mục đầu, giảm tỉ lệ chọn mục cuối (thường là mục Khác)
            if len(valid_opts) > 2:
                 pick = random.choice(valid_opts[:-1]) # Bỏ mục cuối
            else:
                 pick = random.choice(valid_opts)
            
            scroll_to_element(driver, pick)
            force_click(driver, pick)
            
        # print(f"   -> Đã điền câu {q_index+1} ({q_type})")

    except Exception as e:
        print(f"   [!] Lỗi điền câu {q_index+1}: {str(e)[:50]}")

def go_next_page(driver):
    """Tìm nút Next và bấm, sau đó CHỜ trang chuyển hẳn"""
    try:
        # Lấy danh sách câu hỏi hiện tại để làm mốc so sánh
        old_questions = driver.find_elements(By.CSS_SELECTOR, "div[role='listitem']")
        
        buttons = driver.find_elements(By.CSS_SELECTOR, "div[role='button']")
        next_btn = None
        for btn in buttons:
            txt = btn.text.lower()
            if ("tiếp" in txt or "next" in txt) and btn.is_displayed():
                next_btn = btn
                break
        
        if next_btn:
            print(">> Bấm NEXT...")
            scroll_to_element(driver, next_btn)
            force_click(driver, next_btn)
            
            # LOGIC CHỜ QUAN TRỌNG: Chờ cho câu hỏi đầu tiên của trang cũ biến mất
            if old_questions:
                try:
                    WebDriverWait(driver, 5).until(EC.staleness_of(old_questions[0]))
                except TimeoutException:
                    pass # Hết giờ thì cứ chạy tiếp
            
            time.sleep(2) # Chờ thêm cho trang mới render
            return True
        else:
            return False
    except Exception as e:
        print(f"Lỗi Next: {e}")
        return False

# ================= LOGIC CHÍNH =================
def main():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless") 
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    
    try:
        print("--- START ---")
        driver.get(FORM_URL)
        time.sleep(3)

        # ---------------- TRANG 1: Giới thiệu ----------------
        print("\n[Trang 1]")
        # Trang này thường chỉ có nút Next, không có câu hỏi listitem
        go_next_page(driver)

        # ---------------- TRANG 2: 5 Câu hỏi thông tin ----------------
        print("\n[Trang 2] Đang xử lý 5 câu hỏi...")
        qs_p2 = get_visible_questions(driver)
        print(f"   Tìm thấy {len(qs_p2)} câu hỏi.")
        
        for idx, q in enumerate(qs_p2):
            fill_question(driver, q, idx)
        
        go_next_page(driver)

        # ---------------- TRANG 3: Các câu hỏi tiếp theo ----------------
        print("\n[Trang 3] Đang xử lý...")
        qs_p3 = get_visible_questions(driver)
        print(f"   Tìm thấy {len(qs_p3)} câu hỏi.")
        
        for idx, q in enumerate(qs_p3):
            fill_question(driver, q, idx)
            
        go_next_page(driver)

        # ---------------- TRANG 4: Ma trận / Linear Scale ----------------
        print("\n[Trang 4] Đang xử lý...")
        qs_p4 = get_visible_questions(driver)
        print(f"   Tìm thấy {len(qs_p4)} câu hỏi.")
        
        for idx, q in enumerate(qs_p4):
            fill_question(driver, q, idx)
            
        go_next_page(driver)

        # ---------------- TRANG 5: NỘP ----------------
        print("\n[Trang 5] Tìm nút Gửi...")
        time.sleep(2)
        
        # Tìm nút Gửi/Submit
        buttons = driver.find_elements(By.CSS_SELECTOR, "div[role='button']")
        found_submit = False
        
        # Cách 1: Tìm theo text
        for btn in buttons:
            txt = btn.text.lower()
            if ("gửi" in txt or "submit" in txt or "nộp" in txt) and "xóa" not in txt and btn.is_displayed():
                print(">> Đã tìm thấy nút Gửi (theo Text). CLICK!")
                scroll_to_element(driver, btn)
                force_click(driver, btn)
                found_submit = True
                break
        
        # Cách 2: Nếu không thấy, bấm nút áp chót (tránh nút Xóa)
        if not found_submit:
            visible_btns = [b for b in buttons if b.is_displayed()]
            if len(visible_btns) >= 2:
                target = visible_btns[-2] # Nút trước nút cuối cùng
                if "xóa" not in target.text.lower():
                    print(f">> Fallback: Bấm nút '{target.text}' (Vị trí áp chót)")
                    scroll_to_element(driver, target)
                    force_click(driver, target)
                    found_submit = True

        if found_submit:
            print(">> ĐÃ NỘP FORM THÀNH CÔNG!")
        else:
            print("!! Không tìm thấy nút nộp.")

        time.sleep(5)

    except Exception as e:
        print(f"Lỗi Fatal: {e}")
        # import traceback
        # traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    main()