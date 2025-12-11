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
WAIT_AFTER_PAGE_LOAD = 3.5  # seconds to wait after navigating to next page

# ================= HÀM HỖ TRỢ =================
def scroll_to_element(driver, element):
    """No-op fast scroll: do minimal work (no smooth lướt)."""
    try:
        # keep tiny pause to allow element reference stability, but do not scroll visibly
        time.sleep(0.05)
    except:
        pass

def force_click(driver, element):
    """Fast click using JS, minimal waiting."""
    try:
        driver.execute_script("arguments[0].click();", element)
    except:
        try:
            element.click()
        except:
            pass
    # minimal post-click pause
    time.sleep(0.06)

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
    """Quick click + concise debug (no scrolling)."""
    try:
        opt_text = (el.text or "").strip().splitlines()[0]
    except:
        opt_text = "<no-text>"
    if qidx is None:
        print(f"   >> CHỌN: '{opt_text}'  | CÂU: {qname}")
    else:
        print(f"   >> Câu {qidx+1} CHỌN: '{opt_text}'  | CÂU: {qname}")
    # direct fast click
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
    """Click Next and wait a fixed time for the next page to render."""
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, "div[role='button']")
        next_btn = None
        for btn in buttons:
            txt = (btn.text or "").lower()
            if ("tiếp" in txt or "next" in txt) and btn.is_displayed():
                next_btn = btn
                break

        if next_btn:
            print(">> Bấm NEXT...")
            try:
                driver.execute_script("arguments[0].click();", next_btn)
            except:
                try:
                    next_btn.click()
                except:
                    pass

            # fixed wait after navigation
            time.sleep(WAIT_AFTER_PAGE_LOAD)
            return True
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
                n = len(opts)
                if n == 1:
                    pick_idx = 0
                elif n == 2:
                    # fallback: bias to second option
                    try:
                        pick_idx = random.choices([0,1], weights=[0.05, 0.95], k=1)[0]
                    except:
                        pick_idx = random.randrange(2)
                else:
                    # extremes (index 0 and last) = 5% each; remaining share 90% equally
                    extreme = 0.05
                    remaining = 1.0 - 2 * extreme
                    middle_count = n - 2
                    middle_w = remaining / middle_count if middle_count > 0 else 0
                    weights = [extreme] + [middle_w] * middle_count + [extreme]
                    try:
                        pick_idx = random.choices(list(range(n)), weights=weights, k=1)[0]
                    except:
                        pick_idx = random.randrange(n)
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

def _find_option_index_by_keywords(opts, keywords):
    if isinstance(keywords, str):
        keywords = [keywords]
    for i, o in enumerate(opts):
        text = (o.text or "").lower()
        for k in keywords:
            if k in text:
                return i
    return None

def _is_electric_text(txt):
    txt = (txt or "").lower()
    return "xe máy điện" in txt or "xe đạp điện" in txt or "xe điện" in txt

def process_page_3(driver, page2_result):
    """
    Trang 3 logic theo yêu cầu (robust, không crash nếu thiếu option).
    Chọn Q7 trước, sau đó Q6/Q8/Q10 dựa trên Q7 và age rules.
    """
    print("\n[Trang 3] Áp dụng logic chi tiết (Xe máy / Xe điện)...")
    age_idx = page2_result.get("age_idx") if page2_result else None

    questions = get_visible_questions(driver)
    print(f"   Tìm thấy listitem hiển thị: {len(questions)}")

    q6 = find_question_by_keywords(questions, ["loại phương tiện", "phương tiện", "sử dụng thường xuyên", "loại phương tiện nào"])
    q7 = find_question_by_keywords(questions, ["đã từng sử dụng", "sử dụng xe máy điện", "đã từng"])
    q8 = find_question_by_keywords(questions, ["thời gian", "đã sử dụng bao lâu", "thời gian đã sử dụng"])
    q9 = find_question_by_keywords(questions, ["mục đích", "mục đích chính"])
    q10 = find_question_by_keywords(questions, ["tần suất", "thường sử dụng", "tần suất như thế nào"])
    q11 = find_question_by_keywords(questions, ["chỗ sạc", "sạc xe", "có chỗ sạc"])

    ints = [q for q in questions if get_option_elements(q)]
    if not q6 and len(ints) >= 1: q6 = ints[0]
    if not q7 and len(ints) >= 2: q7 = ints[1]
    if not q8 and len(ints) >= 3: q8 = ints[2]
    if not q9 and len(ints) >= 4: q9 = ints[3]
    if not q10 and len(ints) >= 5: q10 = ints[4]
    if not q11 and len(ints) >= 6: q11 = ints[5]

    def text_of(opts, i):
        try:
            return (opts[i].text or "").strip()
        except:
            return ""

    def find_idx(opts, keywords):
        if not opts: return None
        return _find_option_index_by_keywords(opts, keywords)

    # Q7: chọn trước (nếu có)
    opts7 = get_option_elements(q7) if q7 else []
    print("   >> Q7 options count:", len(opts7), "texts:", [(o.text or "").strip().splitlines()[0] for o in opts7] if opts7 else [])
    q7_idx = None
    q7_text = ""
    if opts7:
        q7_idx = random.randrange(len(opts7))
        q7_text = text_of(opts7, q7_idx)
        debug_click(driver, opts7[q7_idx], qname="Q7 Đã từng sử dụng xe máy điện", qidx=6)
    else:
        print("   [!] Q7 không có option, bỏ qua Q7")

    time.sleep(0.06)

    # Q6: Tuân theo age rules và liên kết với Q7
    opts6 = get_option_elements(q6) if q6 else []
    print("   >> Q6 options count:", len(opts6), "texts:", [(o.text or "").strip().splitlines()[0] for o in opts6] if opts6 else [])
    q6_idx = None
    q6_text = ""

    def is_electric_label(s):
        return _is_electric_text(s)

    def excluded_by_age_label(s):
        s = (s or "").lower()
        if age_idx == 0:  # 18-24
            # exclude xe ô tô xăng, xe đạp, đi bộ
            return any(x in s for x in ["xe ô tô", "xe ô tô xăng", "xe đạp", "đi bộ"])
        else:
            # 25-34, 35-45, >45: exclude đi bộ, xe đạp điện, xe đạp, xe buýt/phương tiện công cộng
            return any(x in s for x in ["đi bộ", "xe đạp điện", "xe đạp", "xe buýt", "phương tiện công cộng", "bus"])

    if opts6:
        if q7_text and "có" in q7_text.lower() and "đang" in q7_text.lower():
            # force electric if present
            idx_e = None
            for i, o in enumerate(opts6):
                if is_electric_label(o.text):
                    idx_e = i
                    break
            if idx_e is not None:
                q6_idx = idx_e
            else:
                # fallback to age-respecting choice
                cand = [i for i,o in enumerate(opts6) if not excluded_by_age_label(o.text) and "đi bộ" not in (o.text or "").lower()]
                q6_idx = random.choice(cand) if cand else random.randrange(len(opts6))
        else:
            # choose non-electric respecting age exclusions
            candidates = []
            for i, o in enumerate(opts6):
                t = (o.text or "").lower()
                if is_electric_label(t):
                    continue
                if excluded_by_age_label(t):
                    continue
                if "đi bộ" in t:
                    continue
                candidates.append(i)
            if not candidates:
                # fallback to any non-electric
                candidates = [i for i,o in enumerate(opts6) if not is_electric_label((o.text or "").lower())]
            if not candidates:
                candidates = list(range(len(opts6)))
            q6_idx = random.choice(candidates)
        q6_text = text_of(opts6, q6_idx)
        debug_click(driver, opts6[q6_idx], qname="Q6 Loại phương tiện", qidx=5)
    else:
        print("   [!] Q6 không có option")

    time.sleep(0.06)

    # Nếu Q6 là electric nhưng Q7 chọn non-active -> try set Q7 active (nếu tồn tại)
    if opts7 and q6_text and is_electric_label(q6_text):
        idx_active = find_idx(opts7, ["có, đang sử dụng", "có đang sử dụng", "có, đang", "đang sử dụng"])
        if idx_active is not None:
            # click only if different
            if q7_idx != idx_active:
                q7_idx = idx_active
                q7_text = text_of(opts7, q7_idx)
                debug_click(driver, opts7[q7_idx], qname="Q7 (sync vì Q6 là điện)", qidx=6)

    time.sleep(0.06)

    # Q8: theo Q7
    opts8 = get_option_elements(q8) if q8 else []
    print("   >> Q8 options count:", len(opts8), "texts:", [(o.text or "").strip().splitlines()[0] for o in opts8] if opts8 else [])
    q8_idx = None
    q8_text = ""
    if opts8:
        if q7_text and "chưa" in q7_text.lower():
            # default 'Dưới 6 tháng'
            idx = find_idx(opts8, ["dưới 6", "duoi 6", "dưới 6 tháng"])
            q8_idx = idx if idx is not None else 0
        elif q7_text and "có" in q7_text.lower() and "đang" in q7_text.lower():
            # choose among "1 năm - 3 năm" or "Trên 3 năm"
            choices = []
            for k in ["1 năm - 3", "1 năm - 3 năm", "trên 3", "trên 3 năm"]:
                idx = find_idx(opts8, [k])
                if idx is not None:
                    choices.append(idx)
            choices = list(dict.fromkeys(choices))
            q8_idx = random.choice(choices) if choices else random.randrange(len(opts8))
        elif q7_text and ("ngừng" in q7_text.lower() or "đã ngừng" in q7_text.lower() or "ngung" in q7_text.lower()):
            # random among first three: dưới 6, 6 tháng - 1 năm, 1 năm - 3 năm
            candidates = []
            for k in ["dưới 6", "duoi 6", "6 tháng", "6 thang", "1 năm - 3", "1 năm - 3 năm"]:
                idx = find_idx(opts8, [k])
                if idx is not None:
                    candidates.append(idx)
            candidates = list(dict.fromkeys(candidates))
            q8_idx = random.choice(candidates) if candidates else random.randrange(len(opts8))
        else:
            q8_idx = random.randrange(len(opts8))
        q8_text = text_of(opts8, q8_idx)
        debug_click(driver, opts8[q8_idx], qname="Q8 Thời gian sử dụng xe máy điện", qidx=7)
    else:
        print("   [!] Q8 không có option")

    time.sleep(0.06)

    # Q9: exclude 'tận dụng...' and weight for age 18-24
    opts9 = get_option_elements(q9) if q9 else []
    print("   >> Q9 options count:", len(opts9), "texts:", [(o.text or "").strip().splitlines()[0] for o in opts9] if opts9 else [])
    q9_idx = None
    q9_text = ""
    if opts9:
        allowed = []
        for i,o in enumerate(opts9):
            t = (o.text or "").lower()
            if any(x in t for x in ["tận dụng", "ưu đãi", "chính sách", "uu dai", "uutai"]):
                continue
            allowed.append(i)
        if not allowed:
            allowed = list(range(len(opts9)))

        if age_idx == 0:
            weights = []
            for i in allowed:
                t = (opts9[i].text or "").lower()
                if any(x in t for x in ["đi học", "đi làm", "đi học/đi làm", "đi làm/đi học"]):
                    w = 6.0
                elif any(x in t for x in ["giao hàng", "bán thời gian", "giao hàng hoặc"]):
                    w = 6.0
                elif "tiết kiệm" in t or "tiết kiệm chi phí" in t:
                    w = 2.0
                else:
                    w = 1.0
                weights.append(w)
            try:
                q9_idx = random.choices(allowed, weights=weights, k=1)[0]
            except:
                q9_idx = random.choice(allowed)
        else:
            q9_idx = random.choice(allowed)
        q9_text = text_of(opts9, q9_idx)
        debug_click(driver, opts9[q9_idx], qname="Q9 Mục đích chính", qidx=8)
    else:
        print("   [!] Q9 không có option")

    time.sleep(0.06)

    # Q10: tần suất, liên hệ Q7
    opts10 = get_option_elements(q10) if q10 else []
    print("   >> Q10 options count:", len(opts10), "texts:", [(o.text or "").strip().splitlines()[0] for o in opts10] if opts10 else [])
    q10_idx = None
    q10_text = ""
    if opts10:
        if q7_text and "có" in q7_text.lower() and "đang" in q7_text.lower():
            candidates = []
            for k in ["mỗi ngày", "moi ngay", "3-5", "3 - 5", "3–5", "3 đến 5", "3 đến 5 lần"]:
                idx = find_idx(opts10, [k])
                if idx is not None:
                    candidates.append(idx)
            candidates = list(dict.fromkeys(candidates))
            if not candidates:
                candidates = list(range(min(2, len(opts10))))
            q10_idx = random.choice(candidates)
        else:
            idx_month = find_idx(opts10, ["1-3 lần", "1 - 3", "1–3"])
            idx_rare = find_idx(opts10, ["hiếm", "dưới 1 lần", "duoi 1"])
            idx_notuse = find_idx(opts10, ["tôi không còn sử dụng", "không còn sử dụng", "tôi không còn", "khong con su dung"])
            candidates = []; weights = []
            if idx_month is not None:
                candidates.append(idx_month); weights.append(10)
            if idx_rare is not None:
                candidates.append(idx_rare); weights.append(10)
            if idx_notuse is not None:
                candidates.append(idx_notuse); weights.append(80)
            # dedupe
            final = []
            final_w = []
            seen = set()
            for c,w in zip(candidates, weights):
                if c not in seen:
                    final.append(c); final_w.append(w); seen.add(c)
            if not final:
                q10_idx = random.randrange(len(opts10))
            else:
                try:
                    q10_idx = random.choices(final, weights=final_w, k=1)[0]
                except:
                    q10_idx = random.choice(final)
        q10_text = text_of(opts10, q10_idx)
        debug_click(driver, opts10[q10_idx], qname="Q10 Tần suất sử dụng", qidx=9)
    else:
        print("   [!] Q10 không có option")

    time.sleep(0.06)

    # Q11 random
    opts11 = get_option_elements(q11) if q11 else []
    q11_idx = None
    q11_text = ""
    if opts11:
        q11_idx = random.randrange(len(opts11))
        q11_text = text_of(opts11, q11_idx)
        debug_click(driver, opts11[q11_idx], qname="Q11 Có chỗ sạc không", qidx=10)
    else:
        print("   [!] Q11 không có option")

    print(f"\n   => KẾT LUẬN TRANG 3: Q6='{q6_text}' (idx={q6_idx}), Q7='{q7_text}' (idx={q7_idx}), Q8='{q8_text}', Q9='{q9_text}', Q10='{q10_text}', Q11='{q11_text}')")
    time.sleep(0.06)

    return {
        "q6_idx": q6_idx, "q6_text": q6_text,
        "q7_idx": q7_idx, "q7_text": q7_text,
        "q8_idx": q8_idx, "q8_text": q8_text,
        "q9_idx": q9_idx, "q9_text": q9_text,
        "q10_idx": q10_idx, "q10_text": q10_text,
        "q11_idx": q11_idx, "q11_text": q11_text
    }

if __name__ == "__main__":
    main()