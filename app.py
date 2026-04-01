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

# Cấu hình giao diện rộng hơn để hiển thị bảng báo cáo đẹp mắt
st.set_page_config(page_title="Gemi Check Layout", layout="wide")

# ==========================================
# CỘT BÊN TRÁI: QUẢN LÝ DỮ LIỆU ĐƠN HÀNG
# ==========================================
st.sidebar.header("📋 Cơ sở dữ liệu (Tùy chọn)")
st.sidebar.write("Tải file Excel danh sách đơn hàng để chọn nhanh mã hàng không cần gõ tay.")

file_excel_db = st.sidebar.file_uploader("Tải file Excel (Kế hoạch SX)", type=['xlsx', 'xls'])
danh_sach_ma_don = []

if file_excel_db:
    try:
        # Đọc file Excel, lấy dữ liệu ở cột đầu tiên làm Mã đơn hàng
        df_db = pd.read_excel(file_excel_db)
        cot_dau_tien = df_db.columns[0]
        # Lọc bỏ ô trống và chuyển thành danh sách
        danh_sach_ma_don = df_db[cot_dau_tien].dropna().astype(str).unique().tolist()
        st.sidebar.success(f"✅ Đã tải thành công {len(danh_sach_ma_don)} mã đơn hàng!")
    except Exception as e:
        st.sidebar.error("Lỗi đọc file. Đảm bảo file Excel có cột đầu tiên là Mã đơn hàng.")

st.title("Gemi Spot The Difference 🕵️‍♂️")

# --- Hàm hỗ trợ ---
def lay_so_trang_pdf(file_bytes):
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
    return len(pdf_document)

@st.cache_data
def xu_ly_file_tai_len(file_bytes, file_name, trang_so=0):
    if file_name.lower().endswith('.pdf'):
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        page = pdf_document.load_page(trang_so) 
        pix = page.get_pixmap(dpi=100) 
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return Image.open(buf)
    else:
        return Image.open(io.BytesIO(file_bytes)).convert("RGB")

# Khởi tạo bộ nhớ tạm
if 'anh_chuan_da_cat' not in st.session_state:
    st.session_state.anh_chuan_da_cat = None
if 'lich_su_kiem_tra' not in st.session_state:
    st.session_state.lich_su_kiem_tra = []

# ==========================================
# KHU VỰC LÀM VIỆC CHÍNH
# ==========================================
col_trai, col_phai = st.columns(2)

# --- BƯỚC 1: BẢN CHUẨN ---
with col_trai:
    st.subheader("1️⃣ Bản Chuẩn (Mẫu/PDF)")
    if st.session_state.anh_chuan_da_cat is None:
        loai_anh_1 = st.radio("Nguồn ảnh Chuẩn:", ("Tải file (PDF/Ảnh)", "Chụp Camera"), key="radio_1", horizontal=True)
        img_chuan_goc = None
        
        if loai_anh_1 == "Tải file (PDF/Ảnh)":
            file_1 = st.file_uploader("Chọn file layout gốc", type=['pdf', 'jpg', 'jpeg', 'png'], key="file_1")
            if file_1 is not None:
                file_bytes_1 = file_1.getvalue()
                if file_1.name.lower().endswith('.pdf'):
                    tong_so_trang = lay_so_trang_pdf(file_bytes_1)
                    if tong_so_trang > 1:
                        trang_chon = st.selectbox(f"Chọn trang:", range(1, tong_so_trang + 1), key="page_1")
                        img_chuan_goc = xu_ly_file_tai_len(file_bytes_1, file_1.name, trang_chon - 1)
                    else:
                        img_chuan_goc = xu_ly_file_tai_len(file_bytes_1, file_1.name, 0)
                else:
                    img_chuan_goc = xu_ly_file_tai_len(file_bytes_1, file_1.name)
        else:
            pic_1 = st.camera_input("Chụp bản chuẩn", key="cam_1")
            if pic_1 is not None:
                img_chuan_goc = Image.open(pic_1)
                
        if img_chuan_goc is not None:
            st.info("Kéo khung xanh để lấy vùng layout:")
            cropped_img_chuan = st_cropper(img_chuan_goc, realtime_update=True, box_color='#00FF00', aspect_ratio=None, key="crop_1")
            if st.button("✂️ XÁC NHẬN BẢN CHUẨN", use_container_width=True):
                st.session_state.anh_chuan_da_cat = cropped_img_chuan
                st.rerun()
    else:
        st.success("✅ Đã ghi nhớ Bản Chuẩn!")
        st.image(st.session_state.anh_chuan_da_cat, width=200)
        if st.button("🔄 Thay đổi Bản Chuẩn", use_container_width=True):
            st.session_state.anh_chuan_da_cat = None
            st.rerun()

# --- BƯỚC 2: BẢN THỰC TẾ ---
with col_phai:
    st.subheader("2️⃣ Bản Thực Tế")
    if st.session_state.anh_chuan_da_cat is not None:
        loai_anh_2 = st.radio("Nguồn ảnh Thực Tế:", ("Chụp Camera", "Tải file (PDF/Ảnh)"), key="radio_2", horizontal=True)
        img_thucte_goc = None
        
        if loai_anh_2 == "Tải file (PDF/Ảnh)":
            file_2 = st.file_uploader("Chọn file thực tế", type=['pdf', 'jpg', 'jpeg', 'png'], key="file_2")
            if file_2 is not None:
                file_bytes_2 = file_2.getvalue()
                if file_2.name.lower().endswith('.pdf'):
                    tong_so_trang_2 = lay_so_trang_pdf(file_bytes_2)
                    if tong_so_trang_2 > 1:
                        trang_chon_2 = st.selectbox(f"Chọn trang:", range(1, tong_so_trang_2 + 1), key="page_2")
                        img_thucte_goc = xu_ly_file_tai_len(file_bytes_2, file_2.name, trang_chon_2 - 1)
                    else:
                        img_thucte_goc = xu_ly_file_tai_len(file_bytes_2, file_2.name, 0)
                else:
                    img_thucte_goc = xu_ly_file_tai_len(file_bytes_2, file_2.name)
        else:
            pic_2 = st.camera_input("Chụp thực tế tại xưởng", key="cam_2")
            if pic_2 is not None:
                img_thucte_goc = Image.open(pic_2).convert("RGB")

        if img_thucte_goc is not None:
            st.info("Kéo khung đỏ vừa khít với Bản Chuẩn:")
            cropped_img_thucte = st_cropper(img_thucte_goc, realtime_update=True, box_color='#FF0000', aspect_ratio=None, key="crop_2")
            
            if st.button("🔍 PHÂN TÍCH LỖI", type="primary", use_container_width=True):
                img1 = cv2.cvtColor(np.array(st.session_state.anh_chuan_da_cat), cv2.COLOR_RGB2BGR)
                img2 = cv2.cvtColor(np.array(cropped_img_thucte), cv2.COLOR_RGB2BGR)
                
                height, width, _ = img1.shape
                img2_res = cv2.resize(img2, (width, height))
                
                g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
                g2 = cv2.cvtColor(img2_res, cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(g1, g2)
                
                _, thresh = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
                cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                count = 0
                for c in cnts:
                    if cv2.contourArea(c) < 800:
                        continue
                    x, y, w, h = cv2.boundingRect(c)
                    cv2.rectangle(img1, (x, y), (x + w, y + h), (0, 0, 255), 4)
                    count += 1

                img_result = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
                st.image(img_result, caption="Ảnh phân tích", use_container_width=True)
                
                if count == 0:
                    st.success("🎉 KHỚP HOÀN HẢO!")
                else:
                    st.error(f"⚠️ PHÁT HIỆN {count} LỖI KHÁC BIỆT!")
                    
                st.session_state.so_loi_hien_tai = count

# ==========================================
# KHU VỰC LƯU BÁO CÁO (NẰM DƯỚI CÙNG)
# ==========================================
if 'so_loi_hien_tai' in st.session_state:
    st.markdown("---")
    st.subheader("📝 Ghi nhận kết quả vào Sổ tay KCS")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        # Tự động hiển thị Dropdown nếu có file Excel, ngược lại cho nhập tay
        if danh_sach_ma_don:
            ma_don = st.selectbox("Chọn Mã đơn hàng:", [""] + danh_sach_ma_don)
        else:
            ma_don = st.text_input("Nhập Mã đơn hàng:")
            
    with col_b:
        nguoi_kiem = st.text_input("Người kiểm tra:", value="Gemi KCS")
        
    with col_c:
        st.write("")
        st.write("") # Căn chỉnh nút bấm cho ngang hàng
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
