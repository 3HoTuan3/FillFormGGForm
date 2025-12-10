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

def get_option_elements(question_element):
    """Trả về list các element option (radio/checkbox/label) đã hiển thị"""
    opts = question_element.find_elements(By.CSS_SELECTOR, "div[role='radio']")
    if not opts:
        opts = question_element.find_elements(By.CSS_SELECTOR, "div[role='checkbox']")
    if not opts:
        opts = question_element.find_elements(By.TAG_NAME, "label")
    visible = [o for o in opts if o.is_displayed()]
    return visible

def find_question_by_keywords(questions, keywords):
    """Tìm question element bằng danh sách keyword (hoặc chuỗi) trong text"""
    if isinstance(keywords, str):
        keywords = [keywords]
    for q in questions:
        text = (q.text or "").lower()
        if all(any(k in text for k in keywords) if isinstance(keywords, list) else (keywords in text) for keywords in [keywords]):
            # match any provided keyword
            for k in keywords:
                if k in text:
                    return q
    # fallback: try checking any of the keywords
    for q in questions:
        text = (q.text or "").lower()
        for k in keywords:
            if k in text:
                return q
    return None

def debug_click(driver, el, qname="", qidx=None):
    """Click with debug print"""
    try:
        opt_text = (el.text or "").strip().splitlines()[0]
    except:
        opt_text = "<no-text>"
    if qidx is None:
        print(f"   >> CHỌN: '{opt_text}'  | CÂU: {qname}")
    else:
        print(f"   >> Câu {qidx+1} CHỌN: '{opt_text}'  | CÂU: {qname}")
    scroll_to_element(driver, el)
    force_click(driver, el)

# ---------------- PAGE 2 LOGIC --------------------------------
def process_page_2(driver):
    """
    Thực hiện logic cho Trang 2 theo yêu cầu người dùng:
    - Câu 1: Giới tính -> chỉ chọn Nam(0) hoặc Nữ(1)
    - Câu 2: Độ tuổi -> prefer 0 hoặc 1
    - Câu 3: Phường -> random
    - Câu 4: Nghề nghiệp -> phụ thuộc độ tuổi (+ giới tính ảnh hưởng Nội trợ)
    - Câu 5: Thu nhập -> phụ thuộc độ tuổi & nghề
    """
    print("\n[Trang 2] Áp dụng logic chi tiết...")
    questions = get_visible_questions(driver)
    print(f"   Tìm thấy listitem hiển thị: {len(questions)}")
    # map detection keywords
    q_gender = find_question_by_keywords(questions, ["giới tính", "giới tính", "giới"])
    q_age = find_question_by_keywords(questions, ["độ tuổi", "tuổi", "độ tuổi", "tuoi"])
    q_city = find_question_by_keywords(questions, ["phường", "đà nẵng", "đà nẵng", "đànẵng", "phuong"])
    q_job = find_question_by_keywords(questions, ["nghề", "nghề nghiệp", "nghe", "nghề nghiệp"])
    q_income = find_question_by_keywords(questions, ["thu nhập", "thu nhập", "thu nhập hiện", "mức thu nhập"])

    # fallback by position if detection failed
    # many forms place the 5 questions sequentially; try to map by index order
    visible_opts_map = {}
    for idx, q in enumerate(questions):
        visible_opts_map[idx] = get_option_elements(q)

    # Determine Q1 element
    if not q_gender:
        # assume first interactive question
        for q in questions:
            if get_option_elements(q):
                q_gender = q
                break
    if not q_age:
        # after gender likely next interactive
        found = False
        started = False
        for q in questions:
            if q == q_gender:
                started = True
                continue
            if started and get_option_elements(q):
                q_age = q
                found = True
                break
        if not found:
            # fallback to second interactive overall
            ints = [q for q in questions if get_option_elements(q)]
            if len(ints) >= 2:
                q_age = ints[1]

    # Q3
    if not q_city:
        ints = [q for q in questions if get_option_elements(q)]
        # try third interactive
        if len(ints) >= 3:
            q_city = ints[2]

    # Q4
    if not q_job:
        ints = [q for q in questions if get_option_elements(q)]
        if len(ints) >= 4:
            q_job = ints[3]

    # Q5
    if not q_income:
        ints = [q for q in questions if get_option_elements(q)]
        if len(ints) >= 5:
            q_income = ints[4]

    # --- Q1: Gender ---
    gender_idx = None
    gender_text = ""
    if q_gender:
        opts = get_option_elements(q_gender)
        if opts:
            # choose 0 or 1 only
            candidates = [i for i in [0,1] if i < len(opts)]
            gender_idx = random.choice(candidates)
            gender_text = (opts[gender_idx].text or "").strip()
            debug_click(driver, opts[gender_idx], qname="Giới tính", qidx=0)
        else:
            print("   [!] Q1: Không tìm thấy option")
    else:
        print("   [!] Q1: Không tìm thấy block câu hỏi")

    time.sleep(0.15)

    # --- Q2: Age ---
    age_idx = None
    age_text = ""
    if q_age:
        opts = get_option_elements(q_age)
        if opts:
            # weights: prefer index 0 and 1 (18-24 and 25-34)
            population = list(range(len(opts)))
            # default weights: favor first two, small chance for others
            weights = []
            for i in population:
                if i == 0 or i == 1:
                    weights.append(0.4)
                else:
                    weights.append(0.1)
            # normalize not required for random.choices
            try:
                age_idx = random.choices(population, weights=weights, k=1)[0]
            except:
                age_idx = random.randrange(len(opts))
            age_text = (opts[age_idx].text or "").strip()
            debug_click(driver, opts[age_idx], qname="Độ tuổi", qidx=1)
        else:
            print("   [!] Q2: Không tìm thấy option")
    else:
        print("   [!] Q2: Không tìm thấy block câu hỏi")

    time.sleep(0.15)

    # --- Q3: City (random any) ---
    city_idx = None
    city_text = ""
    if q_city:
        opts = get_option_elements(q_city)
        if opts:
            city_idx = random.randrange(len(opts))
            city_text = (opts[city_idx].text or "").strip()
            debug_click(driver, opts[city_idx], qname="Phường/Địa phương", qidx=2)
        else:
            print("   [!] Q3: Không tìm thấy option")
    else:
        print("   [!] Q3: Không tìm thấy block câu hỏi")

    time.sleep(0.15)

    # --- Q4: Job, phụ thuộc age & gender ---
    job_idx = None
    job_text = ""
    if q_job:
        opts = get_option_elements(q_job)
        if opts:
            # build candidate indices based on age_idx and gender
            candidates = list(range(len(opts)))  # default all
            # mapping based on prompt (0-based indices)
            # 0 Học sinh/Sinh viên
            # 1 Cán bộ/Giáo viên/Nhân viên nhà nước
            # 2 Nhân viên văn phòng
            # 3 Nhân viên dịch vụ/bán hàng
            # 4 Tài xế công nghệ/Giao hàng
            # 5 Lao động phổ thông/Công nhân
            # 6 Kinh doanh tự do
            # 7 Chủ doanh nghiệp/Quản lý cấp cao-trung
            # 8 Nội trợ/Không đi làm
            if age_idx == 0:  # 18-24
                allowed = [0, 3, 4, 6]
            elif age_idx == 1:  # 25-34
                allowed = [1, 2, 4, 5, 6, 7]
                # if female, allow Nội trợ as well
                if gender_idx == 1:  # female chosen index 1
                    allowed.append(8)
            else:  # 35-45 or >45
                # exclude student(0) and service(3)
                allowed = [i for i in range(len(opts)) if i not in (0, 3)]
            # clamp allowed to available options
            candidates = [i for i in allowed if i < len(opts)]
            if not candidates:
                candidates = list(range(len(opts)))
            job_idx = random.choice(candidates)
            job_text = (opts[job_idx].text or "").strip()
            debug_click(driver, opts[job_idx], qname="Nghề nghiệp", qidx=3)
        else:
            print("   [!] Q4: Không tìm thấy option")
    else:
        print("   [!] Q4: Không tìm thấy block câu hỏi")

    time.sleep(0.15)

    # --- Q5: Income, phụ thuộc age & job ---
    income_idx = None
    income_text = ""
    if q_income:
        opts = get_option_elements(q_income)
        if opts:
            # indices for income based on prompt:
            # 0 Dưới 5M
            # 1 5-10M
            # 2 11-20M
            # 3 Trên 20M
            candidates = list(range(len(opts)))
            if age_idx == 0:  # 18-24
                if job_idx in (0, 3, 4):  # student/service/driver
                    candidates = [i for i in [0] if i < len(opts)]
                elif job_idx == 6:  # kinh doanh tự do
                    candidates = [i for i in [1, 2] if i < len(opts)]
                else:
                    # fallback small income
                    candidates = [i for i in [0,1] if i < len(opts)]
            elif age_idx == 1:  # 25-34
                candidates = [i for i in [1,2,3] if i < len(opts)]
            else:  # 35-45 and >45
                candidates = [i for i in [1,2,3] if i < len(opts)]
            if not candidates:
                candidates = list(range(len(opts)))
            income_idx = random.choice(candidates)
            income_text = (opts[income_idx].text or "").strip()
            debug_click(driver, opts[income_idx], qname="Thu nhập", qidx=4)
        else:
            print("   [!] Q5: Không tìm thấy option")
    else:
        print("   [!] Q5: Không tìm thấy block câu hỏi")

    print(f"\n   => KẾT LUẬN TRANG 2: Giới tính='{gender_text}' (idx={gender_idx}), Tuổi='{age_text}' (idx={age_idx}), Phường='{city_text}', Nghề='{job_text}' (idx={job_idx}), Thu nhập='{income_text}' (idx={income_idx})")
    time.sleep(0.5)
    return {
        "gender_idx": gender_idx,
        "age_idx": age_idx,
        "city_idx": city_idx,
        "job_idx": job_idx,
        "income_idx": income_idx
    }

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
        go_next_page(driver)

        # ---------------- TRANG 2: 5 Câu hỏi thông tin ----------------
        # Thay vì loop generic, gọi hàm process_page_2 với logic phụ thuộc
        print("\n[Trang 2] Bắt đầu logic chi tiết...")
        page2_result = process_page_2(driver)
        go_next_page(driver)

        # ---------------- TRANG 3: Các câu hỏi tiếp theo ----------------
        print("\n[Trang 3] Đang xử lý...")
        qs_p3 = get_visible_questions(driver)
        print(f"   Tìm thấy {len(qs_p3)} câu hỏi.")
        
        for idx, q in enumerate(qs_p3):
            # dùng generic fill cho các câu không quan trọng
            opts = get_option_elements(q)
            if opts:
                choice = random.randrange(len(opts))
                debug_click(driver, opts[choice], qname=f"Trang3_Câu{idx+1}", qidx=idx)
        go_next_page(driver)

        # ---------------- TRANG 4: Ma trận / Linear Scale ----------------
        print("\n[Trang 4] Đang xử lý...")
        qs_p4 = get_visible_questions(driver)
        print(f"   Tìm thấy {len(qs_p4)} câu hỏi.")
        
        for idx, q in enumerate(qs_p4):
            opts = get_option_elements(q)
            if opts:
                # prefer not to pick last if it's "other"
                pick_idx = random.randrange(len(opts)-1) if len(opts) > 2 else random.randrange(len(opts))
                debug_click(driver, opts[pick_idx], qname=f"Trang4_Câu{idx+1}", qidx=idx)
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
    finally:
        driver.quit()

if __name__ == "__main__":
    main()