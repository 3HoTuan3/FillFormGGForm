import random
import time
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def main():
    # --- CẤU HÌNH ---
    FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSd9oCNYshlqMm752gqTxOxi7iedg74q2iCx6CCEH5LbHKgutg/viewform"

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.maximize_window()
    wait = WebDriverWait(driver, 20)

    # --- BIẾN TOÀN CỤC ---
    current_age_group = 2  # Mặc định 18-22

    # --- HÀM HỖ TRỢ ---
    def scroll_to(element):
        try:
            actions = ActionChains(driver)
            actions.move_to_element(element).perform()
            time.sleep(0.3)
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element,
            )
            time.sleep(0.5)
        except:
            pass

    def click(el):
        try:
            scroll_to(el)
            driver.execute_script("arguments[0].click();", el)
        except:
            pass

    def get_opts(el, type_role="radio"):
        return el.find_elements(By.XPATH, f".//div[@role='{type_role}']")

    def click_checkboxes_by_indices(question_element, target_indices, min_selection=1):
        scroll_to(question_element)
        opts = get_opts(question_element, "checkbox")
        if not opts:
            return

        selected_count = 0
        for opt in opts:
            if opt.get_attribute("aria-checked") == "true":
                click(opt)

        valid_targets = [i for i in target_indices if i < len(opts)]
        random.shuffle(valid_targets)

        max_limit = min(len(valid_targets), 3)
        if max_limit < min_selection:
            max_limit = min_selection

        if len(valid_targets) >= min_selection:
            k = random.randint(min_selection, max_limit)
            picks = valid_targets[:k]
        else:
            picks = valid_targets

        for i in picks:
            click(opts[i])
            selected_count += 1
            time.sleep(0.1)

        if selected_count == 0 and len(opts) > 0:
            click(opts[0])

    def nav():
        """Hàm điều hướng: Chỉ bấm Tiếp/Next, tuyệt đối TRÁNH nút Xóa/Clear"""
        time.sleep(1)
        buttons = driver.find_elements(By.XPATH, "//div[@role='button']")
        for btn in buttons:
            txt = btn.text.lower()

            if "xóa" in txt or "clear" in txt:
                continue

            # Chỉ bấm các nút điều hướng trang (Tiếp/Next)
            if any(x in txt for x in ["tiếp", "next"]):
                if btn.is_displayed():
                    click(btn)
                    return True
        return False

    def find_question_block(keywords):
        all_questions = driver.find_elements(
            By.CSS_SELECTOR, "div.Qr7Oae[role='listitem']"
        )
        for q in all_questions:
            text = q.text.lower()
            if isinstance(keywords, list):
                if any(k in text for k in keywords):
                    return q
            elif keywords in text:
                return q
        return None

    # --- LOGIC PAGE 3 ---
    def process_page_3_logic():
        nonlocal current_age_group
        print("   -> Đang áp dụng Logic Page 3...")

        def answer_question(keywords, allowed_indices, get_idx_callback=None):
            q_block = find_question_block(keywords)
            if q_block:
                scroll_to(q_block)
                opts = get_opts(q_block)
                if not opts:
                    return -1
                final_idx = 0
                if get_idx_callback:
                    final_idx = get_idx_callback()
                else:
                    valid = [i for i in allowed_indices if i < len(opts)]
                    if valid:
                        final_idx = random.choice(valid)
                if final_idx < len(opts):
                    click(opts[final_idx])
                    return final_idx
            return -1

        # Câu 1: Giới tính - Chọn 1 trong 2 (Nam hoặc Nữ, tránh "Khác")
        answer_question("giới tính", [0, 1])

        # Câu 2: Tuổi - Random với weight khác nhau
        def pick_age_idx():
            return random.choices(
                [0, 1, 2, 3, 4], 
                weights=[0.10, 0.25, 0.25, 0.20, 0.20]
            )[0]

        age_idx = answer_question("tuổi", [], get_idx_callback=pick_age_idx)
        current_age_group = age_idx + 1

        # ===== LOGIC THEO ĐỘ TUỔI =====
        
        if age_idx == 0:  # Dưới 18 tuổi
            print("      -> Xử lý: Dưới 18 tuổi")
            # Trình độ học vấn: Trung học phổ thông hoặc Trường nghề
            answer_question("học vấn", [0, 1])
            # Nghề nghiệp: Học sinh/Sinh viên
            answer_question("nghề nghiệp", [0])
            # Cấp bậc: Không tham gia thị trường lao động
            answer_question("cấp bậc", [0])
            # Thu nhập: Dưới 5 triệu
            answer_question("thu nhập", [0])

        elif age_idx == 1:  # 18-22 tuổi
            print("      -> Xử lý: 18-22 tuổi")
            # Trình độ học vấn: Random Cao đẳng hoặc Cử nhân đại học
            answer_question("học vấn", [2, 3])
            # Nghề nghiệp: Random 3 phương án
            job_choice = answer_question("nghề nghiệp", [0, 1, 3])
            # Cấp bậc: Tùy theo chọn nghề
            if job_choice == 3:  # Làm việc tự do
                answer_question("cấp bậc", [1])  # Làm việc tự do
            elif job_choice == 1:  # Chưa có việc làm
                answer_question("cấp bậc", [0])  # Không tham gia thị trường
            else:  # Học sinh/Sinh viên
                answer_question("cấp bậc", [0, 2])  # Không tham gia hoặc Thực tập sinh
            # Thu nhập: Dưới 5 triệu hoặc 5-15 triệu
            answer_question("thu nhập", [0, 1])

        elif age_idx == 2:  # 23-25 tuổi
            print("      -> Xử lý: 23-25 tuổi")
            # Trình độ học vấn: Random Cao đẳng, Cử nhân, hoặc Thạc sĩ
            answer_question("học vấn", [2, 3, 4])
            # Nghề nghiệp: Random tất cả các phương án
            job_choice = answer_question("nghề nghiệp", [0, 1, 2, 3])
            # Cấp bậc: Random tất cả các phương án (trừ Other)
            if job_choice == 3:  # Làm việc tự do
                answer_question("cấp bậc", [1, 4])  # Freelancer hoặc Team Leader
            elif job_choice == 2:  # Toàn thời gian
                answer_question("cấp bậc", [3, 4, 5])  # Associate, Team Leader, Middle Manager
            elif job_choice == 1:  # Chưa có việc làm
                answer_question("cấp bậc", [0])  # Không tham gia
            else:  # Học sinh/Sinh viên
                answer_question("cấp bậc", [0, 2])  # Không tham gia hoặc Thực tập sinh
            # Thu nhập: 3 phương án đầu (dưới 5, 5-15, 16-30 triệu)
            answer_question("thu nhập", [0, 1, 2])

        elif age_idx == 3:  # 26-28 tuổi
            print("      -> Xử lý: 26-28 tuổi")
            # Trình độ học vấn: Thạc sĩ hoặc Cử nhân (tránh dưới Cao đẳng)
            answer_question("học vấn", [3, 4])
            # Nghề nghiệp: Toàn thời gian hoặc Làm việc tự do (TUYỆT ĐỐI TRÁNH học sinh/chưa có việc)
            job_choice = answer_question("nghề nghiệp", [2, 3])
            # Cấp bậc: Các phương án cao hơn
            answer_question("cấp bậc", [1, 3, 4, 5, 6])
            # Thu nhập: Từ 16 triệu trở lên (phương án 2, 3, 4)
            answer_question("thu nhập", [2, 3, 4])

        else:  # Trên 28 tuổi (age_idx == 4)
            print("      -> Xử lý: Trên 28 tuổi")
            # Trình độ học vấn: TRÁNH Trung học, Trường nghề, Cao đẳng (chọn từ Cử nhân trở lên)
            answer_question("học vấn", [3, 4, 5])
            # Nghề nghiệp: Toàn thời gian hoặc Làm việc tự do (TUYỆT ĐỐI TRÁNH học sinh/chưa có việc)
            job_choice = answer_question("nghề nghiệp", [2, 3])
            # Cấp bậc: Các phương án cao hơn
            answer_question("cấp bậc", [1, 3, 4, 5, 6, 7])
            # Thu nhập: Từ 16 triệu trở lên
            answer_question("thu nhập", [2, 3, 4])

        # Câu 8: Thành phố - Ưu tiên Đà Nẵng (80%), ít khi chọn thành phố khác
        print("   -> Đang tìm câu 8 (Thành phố)...")
        def pick_city_idx():
            if random.random() < 0.80:
                return 2  # Đà Nẵng (ưu tiên cao)
            return random.choice([0, 1])  # Hồ Chí Minh hoặc Hà Nội (hiếm)

        answer_question(["thành phố", "địa phương"], [], get_idx_callback=pick_city_idx)

    # --- LOGIC PAGE 4 (Random) ---
    def process_page_4_logic():
        print("   -> Đang xử lý Page 4 (Multiple Choice)...")
        qs = driver.find_elements(By.CSS_SELECTOR, "div.Qr7Oae[role='listitem']")
        
        for idx, q in enumerate(qs):
            opts_cb = get_opts(q, "checkbox")
            opts_rd = get_opts(q, "radio")
            
            # Câu 13: Tần suất sử dụng - Chỉ chọn 1 đáp án (Radio)
            if opts_rd and not opts_cb:
                # Tìm xem đây có phải câu tần suất không
                q_text = q.text.lower()
                if "tần suất" in q_text:
                    print("      -> Câu 13 (Tần suất): Random 1 phương án")
                    click(random.choice(opts_rd))
                    continue
            
            # ===== MULTIPLE CHOICE (Checkbox) =====
            if opts_cb:
                q_text = q.text.lower()
                
                # Câu 9: Biết đến BNPL từ đâu
                if "biết đến" in q_text and "nguồn" in q_text:
                    print("      -> Câu 9 (Nguồn biết đến BNPL)")
                    if current_age_group <= 3:  # Dưới 25 tuổi (age_idx: 0,1,2)
                        # Chọn: Mạng xã hội (1), Gợi ý bạn bè (2), Trang web/app (3)
                        selected = [1, 2, 3]
                        random.shuffle(selected)
                        picks = selected[:random.randint(2, 3)]
                        for i in picks:
                            if i < len(opts_cb):
                                click(opts_cb[i])
                    else:  # Từ 26 tuổi trở lên
                        # Chọn: Email quảng cáo (4), Công cụ tìm kiếm (0) + 1-2 cái khác
                        picks = [0, 4]
                        remaining = [1, 2, 3]
                        random.shuffle(remaining)
                        picks.extend(remaining[:random.randint(1, 2)])
                        for i in picks:
                            if i < len(opts_cb):
                                click(opts_cb[i])
                
                # Câu 10: Loại sản phẩm/dịch vụ sử dụng BNPL
                elif "loại sản phẩm" in q_text or "thanh toán cho những loại" in q_text:
                    print("      -> Câu 10 (Loại sản phẩm/dịch vụ)")
                    if current_age_group <= 3:  # Dưới 25 tuổi
                        # Chọn: Công nghệ (0), Thời trang (1), Các sản phẩm giá nhỏ (4)
                        selected = [0, 1, 4]
                        random.shuffle(selected)
                        picks = selected[:random.randint(2, 3)]
                        for i in picks:
                            if i < len(opts_cb):
                                click(opts_cb[i])
                    else:  # Từ 26 tuổi trở lên
                        # Ưu tiên dịch vụ du lịch (3), công nghệ (0), các sản phẩm khác
                        picks = [0, 3]
                        remaining = [1, 2, 4]
                        random.shuffle(remaining)
                        picks.append(remaining[0])
                        picks = picks[:random.randint(2, 4)]
                        for i in picks:
                            if i < len(opts_cb):
                                click(opts_cb[i])
                
                # Câu 11: Mục đích sử dụng BNPL
                elif "mục đích" in q_text:
                    print("      -> Câu 11 (Mục đích sử dụng)")
                    if current_age_group <= 3:  # Dưới 25 tuổi
                        # Chọn: Tận dụng ưu đãi (2), Tiện lợi nhanh chóng (3), Mua ngay (1)
                        selected = [1, 2, 3]
                        random.shuffle(selected)
                        picks = selected[:random.randint(2, 3)]
                        for i in picks:
                            if i < len(opts_cb):
                                click(opts_cb[i])
                    else:  # Từ 26 tuổi trở lên
                        # Random tất cả các phương án (trừ Other)
                        total = len(opts_cb)
                        safe_indices = list(range(total - 1)) if total > 1 else [0]
                        picks = random.sample(safe_indices, random.randint(2, min(4, len(safe_indices))))
                        for i in picks:
                            click(opts_cb[i])
                
                # Câu 12: Thông tin ưu tiên xem xét
                elif "thông tin" in q_text and "ưu tiên" in q_text:
                    print("      -> Câu 12 (Thông tin ưu tiên)")
                    if current_age_group <= 3:  # Dưới 25 tuổi
                        # Chọn: Kỳ hạn thanh toán (2), Số lượng cửa hàng (4), 
                        # Điều kiện đăng ký (3), Thông tin đơn vị (1)
                        selected = [1, 2, 3, 4]
                        picks = random.sample(selected, random.randint(2, 4))
                        for i in picks:
                            if i < len(opts_cb):
                                click(opts_cb[i])
                    else:  # Từ 26 tuổi trở lên
                        # Ưu tiên lãi suất, thông tin đơn vị, kỳ hạn
                        selected = [0, 1, 2]
                        picks = random.sample(selected, random.randint(2, 3))
                        # Có thể thêm 1-2 cái khác
                        if random.random() < 0.5:
                            remaining = [3, 4]
                            picks.extend(random.sample(remaining, random.randint(1, 2)))
                        picks = picks[:5]
                        for i in picks:
                            if i < len(opts_cb):
                                click(opts_cb[i])
                
                # Câu 14: Nhà cung cấp BNPL đã biết
                elif "nhà cung cấp" in q_text or "biết hoặc nghe đến" in q_text:
                    print("      -> Câu 14 (Nhà cung cấp BNPL)")
                    # Luôn chọn 2 trong 3 cái (SPayLater, Ví Trả Sau, ZaloPay)
                    main_providers = [0, 1, 2]  # SPayLater, Ví Trả Sau, ZaloPay
                    picks = random.sample(main_providers, 2)
                    
                    # Có thể thêm các cái khác (Fundiin, Kredivo, Home Credit, Atome, Ree-Pay)
                    if random.random() < 0.5:
                        other_providers = [3, 4, 5, 6, 7]
                        picks.extend(random.sample(other_providers, random.randint(1, 2)))
                    
                    picks.sort()
                    for i in picks:
                        if i < len(opts_cb):
                            click(opts_cb[i])
                
                # Câu hỏi multiple choice khác (fallback)
                else:
                    print(f"      -> Câu hỏi khác: {q_text[:50]}...")
                    total = len(opts_cb)
                    safe_indices = list(range(total - 1)) if total > 1 else [0]
                    if safe_indices:
                        picks = random.sample(safe_indices, random.randint(2, min(4, len(safe_indices))))
                        for i in picks:
                            click(opts_cb[i])

    # ==========================
    # MAIN EXECUTION
    # ==========================
    try:
        driver.get(FORM_URL)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        print("PAGE 1...")
        nav()

        print("PAGE 2...")
        time.sleep(1)
        rs = driver.find_elements(By.XPATH, "//div[@role='radio']")
        if rs:
            click(rs[random.choice([0, 1])])
        nav()

        print("PAGE 3...")
        wait.until(
            EC.visibility_of_all_elements_located(
                (By.CSS_SELECTOR, "div.Qr7Oae[role='listitem']")
            )
        )
        process_page_3_logic()
        nav()

        print("PAGE 4...")
        wait.until(
            EC.visibility_of_all_elements_located(
                (By.CSS_SELECTOR, "div.Qr7Oae[role='listitem']")
            )
        )
        process_page_4_logic()
        nav()

        print("PAGE 5 (Matrix)...")
        time.sleep(2)
        rows = driver.find_elements(
            By.XPATH, "//div[@role='radiogroup'] | //tr[@role='radiogroup']"
        )
        for r in rows:
            scroll_to(r)
            ops = get_opts(r)
            if ops:
                click(random.choice(ops))

        # --- BƯỚC QUAN TRỌNG: BẤM NEXT Ở TRANG 5 ĐỂ QUA TRANG CUỐI ---
        print("Đang bấm 'Tiếp' (Next) ở trang 5 để sang trang Gửi...")
        nav_result = nav()  # Bấm Next
        if nav_result:
            print("   -> Đã bấm Tiếp thành công.")
        else:
            print("   -> Không thấy nút Tiếp, có thể đang ở trang cuối rồi?")

        time.sleep(3)  # Chờ trang cuối load

        # --- TRANG CUỐI CÙNG: TÌM VÀ BẤM GỬI (SUBMIT) ---
        print("🏁 Đang tìm nút Gửi/Submit ở trang cuối...")
        time.sleep(1)

        submit_clicked = False

        # CÁCH 1: Tìm theo thẻ Span cụ thể
        try:
            potential_submits = driver.find_elements(
                By.XPATH,
                "//span[contains(text(), 'Submit') or contains(text(), 'Gửi')]",
            )
            for sp in potential_submits:
                try:
                    parent_btn = sp.find_element(
                        By.XPATH, "./ancestor::div[@role='button']"
                    )
                    if (
                        "clear" in parent_btn.text.lower()
                        or "xóa" in parent_btn.text.lower()
                    ):
                        continue

                    print(f"   -> Đã tìm thấy nút Gửi chính xác: {sp.text}")
                    click(parent_btn)
                    submit_clicked = True
                    break
                except:
                    click(sp)
                    submit_clicked = True
                    break
        except:
            pass

        # CÁCH 2: Nếu Cách 1 thất bại, tìm nút button cuối cùng
        if not submit_clicked:
            print("   -> Đang thử tìm nút cuối cùng trong trang (Fallback)...")
            all_btns = driver.find_elements(By.XPATH, "//div[@role='button']")
            valid_btns = [
                b
                for b in all_btns
                if b.is_displayed()
                and "xóa" not in b.text.lower()
                and "clear" not in b.text.lower()
                and "quay lại" not in b.text.lower()
                and "back" not in b.text.lower()
            ]

            if valid_btns:
                last_btn = valid_btns[-1]
                print(f"   -> Click nút cuối cùng hợp lệ: '{last_btn.text}'")
                click(last_btn)
            else:
                print("⚠️ Không tìm thấy nút Gửi nào khả thi!")

        # --- CHỜ MÀN HÌNH CẢM ƠN ---
        print("⏳ Đang đợi màn hình cảm ơn để xác nhận...")
        try:
            another_response_link = wait.until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//a[contains(text(), 'Submit another response') or contains(text(), 'Gửi phản hồi khác') or contains(text(), 'gửi câu trả lời khác')]",
                    )
                )
            )
            print("✅ THÀNH CÔNG! Đã thấy màn hình cảm ơn.")
            time.sleep(2)
        except Exception:
            print(
                "⚠️ Hết thời gian chờ (20s) mà chưa thấy màn hình cảm ơn. Kiểm tra lại xem đã bấm Gửi chưa."
            )

    except Exception:
        traceback.print_exc()
    finally:
        print("✅ Kết thúc chương trình.")
        driver.quit()


if __name__ == "__main__":
    main()
