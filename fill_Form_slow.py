import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================= CẤU HÌNH =================
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScBFNB5Y_cGG2ZXe3ekmHwnq3tPSHqHckhMi9CnGPwanzBDGw/viewform"

# ================= HÀM HỖ TRỢ =================
def scroll_to_element(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
        time.sleep(0.5)
    except: pass

def scroll_to_bottom(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

def force_click(driver, element):
    """Click bằng JS để xuyên qua các lớp phủ"""
    driver.execute_script("arguments[0].click();", element)
    time.sleep(0.3)

def get_valid_questions(driver, min_expected=0):
    """Lọc bỏ tiêu đề/hình ảnh, chỉ lấy câu hỏi có thể tương tác"""
    attempts = 0
    while attempts < 3:
        all_items = driver.find_elements(By.CSS_SELECTOR, 'div[role="listitem"]')
        valid_qs = []
        for item in all_items:
            if item.find_elements(By.CSS_SELECTOR, 'div[role="radio"]') or \
               item.find_elements(By.CSS_SELECTOR, 'div[role="checkbox"]'):
                valid_qs.append(item)
        
        if len(valid_qs) >= min_expected:
            return valid_qs
        scroll_to_bottom(driver)
        time.sleep(1)
        attempts += 1
    return valid_qs

def click_next_and_wait(driver, current_elements):
    """Bấm Next và đợi trang chuyển hoàn toàn"""
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, 'div[role="button"]')
        next_btn = None
        for btn in buttons:
            if "tiếp" in btn.text.lower() or "next" in btn.text.lower():
                next_btn = btn
                break
        
        if next_btn:
            scroll_to_element(driver, next_btn)
            force_click(driver, next_btn)
            print(">> Đã bấm Next...")
        else:
            return False

        # Đợi trang cũ biến mất (Staleness)
        if len(current_elements) > 0:
            try:
                WebDriverWait(driver, 5).until(EC.staleness_of(current_elements[0]))
                time.sleep(1.5)
                return True
            except: return False
        else:
            time.sleep(3)
            return True
    except: return False

def random_choice(driver, question_element, limit_indices=[]):
    """Chọn random đáp án, hỗ trợ giới hạn index"""
    try:
        options = question_element.find_elements(By.CSS_SELECTOR, 'div[role="radio"]')
        if not options: options = question_element.find_elements(By.CSS_SELECTOR, 'label')
        
        valid_indices = [i for i in range(len(options))]
        if limit_indices:
            valid_indices = [i for i in valid_indices if i in limit_indices]
        
        if valid_indices:
            idx = random.choice(valid_indices)
            scroll_to_element(driver, options[idx])
            force_click(driver, options[idx])
    except: pass

# ================= LOGIC CHÍNH =================
def main():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless") # Bỏ comment nếu muốn chạy ngầm
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    
    try:
        print("--- BẮT ĐẦU AUTOMATION ---")
        driver.get(FORM_URL)
        time.sleep(3)

        # --- TRANG 1: Mở đầu ---
        print("1. Đang xử lý Trang 1...")
        p1_check = driver.find_elements(By.CSS_SELECTOR, 'div[role="heading"]') 
        click_next_and_wait(driver, p1_check)
        
        # --- TRANG 2: 5 Câu hỏi ---
        print("2. Đang xử lý Trang 2...")
        scroll_to_bottom(driver)
        qs_p2 = get_valid_questions(driver, min_expected=5)
        if len(qs_p2) >= 5:
            random_choice(driver, qs_p2[0], limit_indices=[0, 1]) # Câu 1: Chỉ chọn 1,2
            for i in range(1, 5): # Câu 2-5: Random
                random_choice(driver, qs_p2[i])
        click_next_and_wait(driver, qs_p2)

        # --- TRANG 3: 6 Câu hỏi ---
        print("3. Đang xử lý Trang 3...")
        scroll_to_bottom(driver)
        qs_p3 = get_valid_questions(driver, min_expected=6)
        if len(qs_p3) >= 6:
            for i in range(6): random_choice(driver, qs_p3[i])
        click_next_and_wait(driver, qs_p3)

        # --- TRANG 4: Linear Scale (24 câu) ---
        print("4. Đang xử lý Trang 4 (Linear Scale)...")
        scroll_to_bottom(driver)
        qs_p4 = get_valid_questions(driver, min_expected=10)
        
        # Trọng số: Ít chọn 1 và 6
        population = [0, 1, 2, 3, 4, 5]
        weights = [0.1, 0.2, 0.2, 0.2, 0.2, 0.1]
        
        for q in qs_p4:
            try:
                options = q.find_elements(By.CSS_SELECTOR, 'div[role="radio"]')
                if not options: options = q.find_elements(By.CSS_SELECTOR, 'label')
                
                if len(options) >= 2:
                    idx = random.choices(population, weights=weights, k=1)[0]
                    if idx >= len(options): idx = len(options) - 1 # Safety check
                    scroll_to_element(driver, options[idx])
                    force_click(driver, options[idx])
            except: pass
        click_next_and_wait(driver, qs_p4)

        # --- TRANG 5: NỘP ---
        print("5. Đang xử lý Trang 5 (Nộp)...")
        time.sleep(2)
        
        all_buttons = driver.find_elements(By.CSS_SELECTOR, 'div[role="button"]')
        found_submit = False

        # Ưu tiên 1: Tìm theo Text
        for btn in all_buttons:
            txt = btn.text.lower()
            if ("gửi" in txt or "submit" in txt) and "xóa" not in txt:
                scroll_to_element(driver, btn)
                force_click(driver, btn)
                found_submit = True
                print(">> Đã bấm nút Gửi (theo Text).")
                break
        
        # Ưu tiên 2: Fallback nút ÁP CHÓT (Fix cho trường hợp nút ẩn text)
        if not found_submit and len(all_buttons) >= 2:
            target_btn = all_buttons[-2] # Nút nằm trước nút "Xóa hết"
            scroll_to_element(driver, target_btn)
            force_click(driver, target_btn)
            found_submit = True
            print(">> Đã bấm nút Gửi (theo vị trí Áp Chót).")

        if found_submit:
            print("\n=== HOÀN THÀNH KHẢO SÁT THÀNH CÔNG! ===")
        else:
            print("\n!! Không bấm được nút nộp.")

        time.sleep(5) # Đợi một chút rồi tắt

    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    main()