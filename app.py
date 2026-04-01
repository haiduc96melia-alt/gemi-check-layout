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
# MÃ CSS TẠO THANH CUỘN (SCROLLBAR) NHƯ EXCEL
# ==========================================
st.markdown("""
    <style>
    /* Ép 2 cột chính hiển thị thanh cuộn trái/phải, lên/xuống nếu ảnh quá to */
    [data-testid="column"] {
        overflow: auto;
        height: 75vh; /* Chiều cao cửa sổ bằng 75% màn hình */
        border: 1px solid #ddd; /* Tạo khung viền mờ cho dễ nhìn */
        padding: 10px;
        border-radius: 5px;
    }
    /* Chỉnh thanh cuộn cho đẹp mắt hơn */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #f1f1f1; 
    }
    ::-webkit-scrollbar-thumb {
        background: #888; 
        border-radius: 5px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555; 
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# THUẬT TOÁN AI: TỰ ĐỘNG CĂN CHỈNH ẢNH
# ==========================================
def can_chinh_anh_tu_dong(img_chuan, img_thucte):
    gray1 = cv2.cvtColor(img_chuan, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img_thucte, cv2.COLOR_BGR2GRAY)
    
    orb = cv2.ORB_create(5000)
    kp1, des1 = orb.detectAndCompute(gray1, None)
    kp2, des2 = orb.detectAndCompute(gray2, None)
    
    if des1 is None or des2 is None:
        return cv2.resize(img_thucte, (img_chuan.shape[1], img_chuan.shape[0]))

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)
    
    good_matches = int(len(matches) * 0.15)
    matches = matches[:good_matches]
    
    if len(matches) < 10:
        return cv2.resize(img_thucte, (img_chuan.shape[1], img_chuan.shape[0]))
        
    src_pts = np.float32([ kp1[m.queryIdx].pt for m in matches ]).reshape(-1,1,2)
    dst_pts = np.float32([ kp2[m.trainIdx].pt for m in matches ]).reshape(-1,1,2)
    
    M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
    
    if M is not None:
        h, w, _ = img_chuan.shape
        aligned_img = cv2.warpPerspective(img_thucte, M, (w, h))
        return aligned_img
    else:
        return cv2.resize(img_thucte, (img_chuan.shape[1], img_chuan.shape[0]))

# ==========================================
# HÀM XỬ LÝ PDF VÀ ẢNH (Cố định độ nét DPI=150)
# ==========================================
def lay_so_trang_pdf(file_bytes):
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
    return len(pdf_document)

@st.cache_data
def xu_ly_file_tai_len(file_bytes, file_name, trang_so=0):
    if file_name.lower().endswith('.pdf'):
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        page = pdf_document.load_page(trang_so) 
        # Cố định DPI 150 để ảnh nét to mà không sập RAM
        pix = page.get_pixmap(dpi=150) 
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return Image.open(buf)
    else:
        return Image.open(io.BytesIO(file_bytes)).convert("RGB")

# ==========================================
# THANH CÔNG CỤ BÊN TRÁI (QUẢN LÝ DỮ LIỆU EXCEL)
# ==========================================
st.sidebar.header("📋 Cơ sở dữ liệu")
file_excel_db = st.sidebar.file_uploader("Tải file Excel Mã Đơn Hàng", type=['xlsx', 'xls'])
danh_sach_ma_don = []
if file_excel_db:
    try:
        df_db = pd.read_excel(file_excel_db)
        cot_dau_tien = df_db.columns[0]
        danh_sach_ma_don = df_db[cot_dau_tien].dropna().astype(str).unique().tolist()
        st.sidebar.success(f"Đã tải {len(danh_sach_ma_don)} mã đơn.")
    except Exception as e:
        st.sidebar.error("Lỗi đọc file Excel.")

st.title("Gemi Spot The Difference 🕵️‍♂️")

if 'anh_chuan_da_cat' not in st.session_state: st.session_state.anh_chuan_da_cat = None
if 'lich_su_kiem_tra' not in st.session_state: st.session_state.lich_su_kiem_tra = []

# ==========================================
# KHU VỰC LÀM VIỆC CHÍNH (ĐÃ CÓ THANH CUỘN)
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
            
            # --- CHỌN TRANG PDF ---
            trang_chon_1 = 1
            if file_1.name.lower().endswith('.pdf'):
                tong_so_trang = lay_so_trang_pdf(file_bytes_1)
                if tong_so_trang > 1:
                    trang_chon_1 = st.number_input(f"File có {tong_so_trang} trang. Chọn trang:", min_value=1, max_value=tong_so_trang, value=1, key="num_1")
            
            # Xử lý ảnh luôn ở mức 150 DPI
            if file_1.name.lower().endswith('.pdf'):
                img_chuan_goc = xu_ly_file_tai_len(file_bytes_1, file_1.name, trang_chon_1 - 1)
            else:
                img_chuan_goc = xu_ly_file_tai_len(file_bytes_1, file_1.name)
                
        if img_chuan_goc is not None:
            st.info("Dùng thanh cuộn bên cạnh/bên dưới để xem toàn bộ ảnh:")
            # Khung cắt cố định Key
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
    st.subheader("2️⃣ Bản Thực Tế")
    if st.session_state.anh_chuan_da_cat is not None:
        file_2 = st.file_uploader("Tải file thực tế hoặc chụp ảnh", type=['pdf', 'jpg', 'jpeg', 'png'], key="file_2")
        img_thucte_goc = None
        
        if file_2 is not None:
            file_bytes_2 = file_2.getvalue()
            
            # --- CHỌN TRANG PDF ---
            trang_chon_2 = 1
            if file_2.name.lower().endswith('.pdf'):
                tong_so_trang_2 = lay_so_trang_pdf(file_bytes_2)
                if tong_so_trang_2 > 1:
                    trang_chon_2 = st.number_input(f"File có {tong_so_trang_2} trang. Chọn trang:", min_value=1, max_value=tong_so_trang_2, value=1, key="num_2")
            
            # Xử lý ảnh luôn ở mức 150 DPI
            if file_2.name.lower().endswith('.pdf'):
                img_thucte_goc = xu_ly_file_tai_len(file_bytes_2, file_2.name, trang_chon_2 - 1)
            else:
                img_thucte_goc = xu_ly_file_tai_len(file_bytes_2, file_2.name)

        if img_thucte_goc is not None:
            st.info("Dùng thanh cuộn bên cạnh/bên dưới để xem toàn bộ ảnh:")
            cropped_img_thucte = st_cropper(img_thucte_goc, realtime_update=True, box_color='#FF0000', aspect_ratio=None, key="crop_2")
            
            if st.button("🔍 CĂN CHỈNH AI & PHÂN TÍCH LỖI", type="primary", use_container_width=True):
                with st.spinner('AI đang tự động nắn ảnh và soi lỗi...'):
                    img1 = cv2.cvtColor(np.array(st.session_state.anh_chuan_da_cat), cv2.COLOR_RGB2BGR)
                    img2_raw = cv2.cvtColor(np.array(cropped_img_thucte), cv2.COLOR_RGB2BGR)
                    
                    img2_aligned = can_chinh_anh_tu_dong(img1, img2_raw)
                    
                    g1 = cv2.GaussianBlur(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY), (5,5), 0)
                    g2 = cv2.GaussianBlur(cv2.cvtColor(img2_aligned, cv2.COLOR_BGR2GRAY), (5,5), 0)
                    
                    diff = cv2.absdiff(g1, g2)
                    
                    _, thresh = cv2.threshold(diff, 50, 255, cv2.THRESH_BINARY)
                    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    count = 0
                    for c in cnts:
                        if cv2.contourArea(c) < 800: 
                            continue
                        x, y, w, h = cv2.boundingRect(c)
                        cv2.rectangle(img1, (x, y), (x + w, y + h), (0, 0, 255), 4)
                        count += 1

                    img_result = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
                    st.image(img_result, caption="Kết quả phân tích", use_container_width=True)
                    
                    if count == 0:
                        st.success("🎉 KHỚP HOÀN HẢO!")
                    else:
                        st.error(f"⚠️ PHÁT HIỆN {count} LỖI KHÁC BIỆT!")
                        
                    st.session_state.so_loi_hien_tai = count

# ==========================================
# KHU VỰC LƯU BÁO CÁO NẰM NGOÀI KHUNG CUỘN
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
