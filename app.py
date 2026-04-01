import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_cropper import st_cropper
import fitz  
import io
import pandas as pd
from datetime import datetime

# Tắt giới hạn pixel an toàn
Image.MAX_IMAGE_PIXELS = None

st.set_page_config(page_title="Gemi Check Layout", layout="wide")

# ==========================================
# THUẬT TOÁN AI: TỰ ĐỘNG CĂN CHỈNH ẢNH (GIẢI QUYẾT LỖI SỐ 3)
# ==========================================
def can_chinh_anh_tu_dong(img_chuan, img_thucte):
    # Chuyển sang ảnh xám để tìm đặc trưng
    gray1 = cv2.cvtColor(img_chuan, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img_thucte, cv2.COLOR_BGR2GRAY)
    
    # Sử dụng thuật toán ORB để tìm các điểm giống nhau (Logo, chữ, đường viền...)
    orb = cv2.ORB_create(5000)
    kp1, des1 = orb.detectAndCompute(gray1, None)
    kp2, des2 = orb.detectAndCompute(gray2, None)
    
    if des1 is None or des2 is None:
        return cv2.resize(img_thucte, (img_chuan.shape[1], img_chuan.shape[0]))

    # Ghép nối các điểm đặc trưng
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)
    
    # Lấy 15% các điểm khớp hoàn hảo nhất
    good_matches = int(len(matches) * 0.15)
    matches = matches[:good_matches]
    
    if len(matches) < 10:
        # Nếu không đủ điểm khớp (2 ảnh hoàn toàn khác nhau), chỉ chỉnh lại kích thước
        return cv2.resize(img_thucte, (img_chuan.shape[1], img_chuan.shape[0]))
        
    src_pts = np.float32([ kp1[m.queryIdx].pt for m in matches ]).reshape(-1,1,2)
    dst_pts = np.float32([ kp2[m.trainIdx].pt for m in matches ]).reshape(-1,1,2)
    
    # Tính toán ma trận biến đổi (Xoay, lật, kéo dãn cho khớp)
    M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
    
    if M is not None:
        h, w, _ = img_chuan.shape
        # Bẻ cong và nắn ảnh thực tế cho khớp 100% với ảnh chuẩn
        aligned_img = cv2.warpPerspective(img_thucte, M, (w, h))
        return aligned_img
    else:
        return cv2.resize(img_thucte, (img_chuan.shape[1], img_chuan.shape[0]))


# ==========================================
# HÀM XỬ LÝ PDF (GIẢI QUYẾT LỖI SỐ 1 & SỐ 2)
# ==========================================
def lay_so_trang_pdf(file_bytes):
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
    return len(pdf_document)

@st.cache_data
def xu_ly_file_tai_len(file_bytes, file_name, trang_so=0, dpi=150):
    if file_name.lower().endswith('.pdf'):
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        page = pdf_document.load_page(trang_so) 
        # DPI có thể thay đổi để "Zoom" nét hơn
        pix = page.get_pixmap(dpi=dpi) 
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return Image.open(buf)
    else:
        return Image.open(io.BytesIO(file_bytes)).convert("RGB")


# ==========================================
# THANH CÔNG CỤ BÊN TRÁI
# ==========================================
st.sidebar.header("⚙️ Cài đặt & Dữ liệu")

# Thanh trượt Zoom (Đổi DPI để phóng to chi tiết)
st.sidebar.markdown("---")
st.sidebar.write("**Độ nét PDF (Tính năng Zoom):**")
muc_zoom = st.sidebar.slider("Kéo lên cao để phóng to chi tiết (Máy yếu nên để mức 100-150)", min_value=100, max_value=300, value=150, step=50)
st.sidebar.info("💡 Mẹo: Ở bất kỳ bức ảnh nào hiện ra, bạn có thể đưa chuột vào góc phải ảnh -> bấm nút [ ⤢ ] để phóng to toàn màn hình.")

# Tải danh sách đơn hàng
st.sidebar.markdown("---")
file_excel_db = st.sidebar.file_uploader("📋 Tải file Excel Mã Đơn Hàng", type=['xlsx', 'xls'])
danh_sach_ma_don = []
if file_excel_db:
    try:
        df_db = pd.read_excel(file_excel_db)
        cot_dau_tien = df_db.columns[0]
        danh_sach_ma_don = df_db[cot_dau_tien].dropna().astype(str).unique().tolist()
        st.sidebar.success(f"Đã tải {len(danh_sach_ma_don)} mã đơn.")
    except Exception as e:
        st.sidebar.error("Lỗi đọc file Excel.")

st.title("Gemi Spot The Difference 🕵️‍♂️ (Bản Pro AI)")

# Bộ nhớ tạm
if 'anh_chuan_da_cat' not in st.session_state: st.session_state.anh_chuan_da_cat = None
if 'lich_su_kiem_tra' not in st.session_state: st.session_state.lich_su_kiem_tra = []

# ==========================================
# KHU VỰC LÀM VIỆC CHÍNH
# ==========================================
col_trai, col_phai = st.columns(2)

# --- BƯỚC 1: BẢN CHUẨN ---
with col_trai:
    st.subheader("1️⃣ Bản Chuẩn (Mẫu/PDF)")
    if st.session_state.anh_chuan_da_cat is None:
        file_1 = st.file_uploader("Tải file layout gốc (PDF/Ảnh)", type=['pdf', 'jpg', 'jpeg', 'png'], key="file_1")
        img_chuan_goc = None
        
        if file_1 is not None:
            file_bytes_1 = file_1.getvalue()
            # GIẢI QUYẾT LỖI SỐ 1: Hộp chọn trang hiển thị rõ ràng
            if file_1.name.lower().endswith('.pdf'):
                tong_so_trang = lay_so_trang_pdf(file_bytes_1)
                trang_chon = 1
                if tong_so_trang > 1:
                    trang_chon = st.number_input(f"File có {tong_so_trang} trang. Nhập trang cần kiểm tra:", min_value=1, max_value=tong_so_trang, value=1, key="num_1")
                img_chuan_goc = xu_ly_file_tai_len(file_bytes_1, file_1.name, trang_chon - 1, dpi=muc_zoom)
            else:
                img_chuan_goc = xu_ly_file_tai_len(file_bytes_1, file_1.name, dpi=muc_zoom)
                
        if img_chuan_goc is not None:
            st.info("Kéo khung xanh để lấy vùng layout. Bấm vào ảnh để vuốt zoom nếu cần:")
            cropped_img_chuan = st_cropper(img_chuan_goc, realtime_update=True, box_color='#00FF00', aspect_ratio=None, key="crop_1")
            if st.button("✂️ XÁC NHẬN BẢN CHUẨN", use_container_width=True):
                st.session_state.anh_chuan_da_cat = cropped_img_chuan
                st.rerun()
    else:
        st.success("✅ Đã ghi nhớ Bản Chuẩn!")
        st.image(st.session_state.anh_chuan_da_cat, use_container_width=True)
        if st.button("🔄 Thay đổi Bản Chuẩn", use_container_width=True):
            st.session_state.anh_chuan_da_cat = None
            st.rerun()

# --- BƯỚC 2: BẢN THỰC TẾ ---
with col_phai:
    st.subheader("2️⃣ Bản Thực Tế (Bản Test/Bình Bản)")
    if st.session_state.anh_chuan_da_cat is not None:
        file_2 = st.file_uploader("Tải file thực tế (PDF/Ảnh) hoặc chụp ảnh", type=['pdf', 'jpg', 'jpeg', 'png'], key="file_2")
        img_thucte_goc = None
        
        if file_2 is not None:
            file_bytes_2 = file_2.getvalue()
            if file_2.name.lower().endswith('.pdf'):
                tong_so_trang_2 = lay_so_trang_pdf(file_bytes_2)
                trang_chon_2 = 1
                if tong_so_trang_2 > 1:
                    trang_chon_2 = st.number_input(f"File có {tong_so_trang_2} trang. Nhập trang cần kiểm tra:", min_value=1, max_value=tong_so_trang_2, value=1, key="num_2")
                img_thucte_goc = xu_ly_file_tai_len(file_bytes_2, file_2.name, trang_chon_2 - 1, dpi=muc_zoom)
            else:
                img_thucte_goc = xu_ly_file_tai_len(file_bytes_2, file_2.name, dpi=muc_zoom)

        if img_thucte_goc is not None:
            st.info("Kéo khung đỏ. Không lo bị lệch vì AI sẽ tự nắn lại ảnh cho bạn!")
            cropped_img_thucte = st_cropper(img_thucte_goc, realtime_update=True, box_color='#FF0000', aspect_ratio=None, key="crop_2")
            
            if st.button("🔍 CĂN CHỈNH AI & PHÂN TÍCH LỖI", type="primary", use_container_width=True):
                with st.spinner('AI đang tự động nắn ảnh và soi lỗi...'):
                    img1 = cv2.cvtColor(np.array(st.session_state.anh_chuan_da_cat), cv2.COLOR_RGB2BGR)
                    img2_raw = cv2.cvtColor(np.array(cropped_img_thucte), cv2.COLOR_RGB2BGR)
                    
                    # Gọi hàm AI nắn ảnh tự động
                    img2_aligned = can_chinh_anh_tu_dong(img1, img2_raw)
                    
                    # Làm mờ nhẹ để khử nhiễu bụi li ti trước khi trừ
                    g1 = cv2.GaussianBlur(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY), (5,5), 0)
                    g2 = cv2.GaussianBlur(cv2.cvtColor(img2_aligned, cv2.COLOR_BGR2GRAY), (5,5), 0)
                    
                    diff = cv2.absdiff(g1, g2)
                    
                    # Tăng ngưỡng (Threshold) lên 50 để tránh báo lỗi các pixel mờ do nét mực in
                    _, thresh = cv2.threshold(diff, 50, 255, cv2.THRESH_BINARY)
                    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    count = 0
                    for c in cnts:
                        if cv2.contourArea(c) < 800: # Pixel nhỏ hơn 800 bị coi là bụi, bỏ qua
                            continue
                        x, y, w, h = cv2.boundingRect(c)
                        cv2.rectangle(img1, (x, y), (x + w, y + h), (0, 0, 255), 4)
                        count += 1

                    img_result = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
                    st.image(img_result, caption="Kết quả (Bấm vào góc phải ảnh để phóng to toàn màn hình)", use_container_width=True)
                    
                    if count == 0:
                        st.success("🎉 KHỚP HOÀN HẢO!")
                    else:
                        st.error(f"⚠️ PHÁT HIỆN {count} LỖI KHÁC BIỆT!")
                        
                    st.session_state.so_loi_hien_tai = count

# ==========================================
# KHU VỰC LƯU BÁO CÁO 
# ==========================================
if 'so_loi_hien_tai' in st.session_state:
    st.markdown("---")
    st.subheader("📝 Ghi nhận kết quả vào Sổ tay KCS")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if danh_sach_ma_don:
            ma_don = st.selectbox("Chọn Mã đơn hàng:", [""] + danh_sach_ma_don)
        else:
            ma_don = st.text_input("Nhập Mã đơn hàng:")
    with col_b:
        nguoi_kiem = st.text_input("Người kiểm tra:", value="Gemi KCS")
    with col_c:
        st.write("")
        st.write("") 
        if st.button("💾 Ghi dữ liệu & Xuất Báo Cáo", type="primary", use_container_width=True):
            if ma_don and ma_don != "":
                ket_qua_danh_gia = "ĐẠT" if st.session_state.so_loi_hien_tai == 0 else "LỖI"
                st.session_state.lich_su_kiem_tra.append({
                    "Thời gian": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Mã đơn hàng": ma_don,
                    "KCS": nguoi_kiem,
                    "Số lỗi": st.session_state.so_loi_hien_tai,
                    "Kết quả": ket_qua_danh_gia
                })
                st.success("Đã ghi vào sổ!")
            else:
                st.warning("Vui lòng điền/chọn Mã đơn hàng!")

    if st.session_state.lich_su_kiem_tra:
        df = pd.DataFrame(st.session_state.lich_su_kiem_tra)
        st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='BaoCao')
        st.download_button(
            label="📥 Tải file Báo Cáo (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"BaoCao_Layout_{datetime.now().strftime('%d%m')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
