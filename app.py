import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_cropper import st_cropper
import fitz  
import io
import pandas as pd
from datetime import datetime

# Tắt giới hạn pixel
Image.MAX_IMAGE_PIXELS = None

st.set_page_config(page_title="Gemi Check Layout", layout="centered")
st.title("Gemi Spot The Difference 🕵️‍♂️")

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
# BƯỚC 1: BẢN CHUẨN
# ==========================================
if st.session_state.anh_chuan_da_cat is None:
    st.subheader("Bước 1: Bản Chuẩn (Mẫu/PDF)")
    loai_anh_1 = st.radio("Chọn cách nhập Bản Chuẩn:", ("Tải file (PDF/Ảnh)", "Chụp Camera"), key="radio_1")
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
        st.write("👉 **Kéo khung xanh để lấy vùng layout:**")
        cropped_img_chuan = st_cropper(img_chuan_goc, realtime_update=True, box_color='#00FF00', aspect_ratio=None, key="crop_1")
        if st.button("✂️ XÁC NHẬN BẢN CHUẨN"):
            st.session_state.anh_chuan_da_cat = cropped_img_chuan
            st.rerun()

# ==========================================
# BƯỚC 2: BẢN THỰC TẾ & BÁO CÁO EXCEL
# ==========================================
else:
    st.success("✅ Đã ghi nhớ Bản Chuẩn!")
    if st.button("🔄 Thay đổi Bản Chuẩn"):
        st.session_state.anh_chuan_da_cat = None
        st.rerun()
        
    st.subheader("Bước 2: Bản Thực Tế (Thùng carton/PDF Bình bản)")
    loai_anh_2 = st.radio("Chọn cách nhập Bản Thực Tế:", ("Chụp Camera", "Tải file (PDF/Ảnh)"), key="radio_2")
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
        pic_2 = st.camera_input("Chụp bản thực tế tại xưởng", key="cam_2")
        if pic_2 is not None:
            img_thucte_goc = Image.open(pic_2).convert("RGB")

    if img_thucte_goc is not None:
        st.write("👉 **Kéo khung đỏ sao cho vừa khít với Bản Chuẩn nhất:**")
        cropped_img_thucte = st_cropper(img_thucte_goc, realtime_update=True, box_color='#FF0000', aspect_ratio=None, key="crop_2")
        
        if st.button("🔍 XÁC NHẬN & PHÂN TÍCH LỖI"):
            st.write("Gemi đang soi lỗi, đợi một chút nhé...")
            
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
            st.image(img_result, caption="Ảnh phân tích từ Gemi", use_container_width=True)
            
            if count == 0:
                st.success("🎉 TUYỆT VỜI! Mọi thứ khớp hoàn hảo.")
            else:
                st.error(f"⚠️ CẢNH BÁO: Phát hiện {count} điểm khác biệt (Đã khoanh đỏ)!")
                
            # Lưu biến count vào session_state để dùng ở phần nhập liệu bên dưới
            st.session_state.so_loi_hien_tai = count

        # ==========================================
        # KHU VỰC NHẬP LIỆU & XUẤT EXCEL
        # ==========================================
        if 'so_loi_hien_tai' in st.session_state:
            st.markdown("---")
            st.subheader("📝 Lưu báo cáo kiểm tra")
            
            col1, col2 = st.columns(2)
            with col1:
                ma_don = st.text_input("Mã đơn hàng / Lô SX:")
            with col2:
                nguoi_kiem = st.text_input("Người kiểm tra (KCS):")
                
            if st.button("💾 Ghi vào sổ tay"):
                if ma_don:
                    ket_qua_danh_gia = "ĐẠT (OK)" if st.session_state.so_loi_hien_tai == 0 else "LỖI (NG)"
                    st.session_state.lich_su_kiem_tra.append({
                        "Ngày giờ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Mã đơn hàng": ma_don,
                        "Người kiểm tra": nguoi_kiem,
                        "Số lỗi phát hiện": st.session_state.so_loi_hien_tai,
                        "Đánh giá": ket_qua_danh_gia
                    })
                    st.success("Đã ghi nhận kết quả!")
                else:
                    st.warning("Vui lòng nhập Mã đơn hàng để lưu!")

            # Hiển thị bảng dữ liệu và nút tải file Excel
            if st.session_state.lich_su_kiem_tra:
                st.write("**Sổ tay kiểm tra trong ngày:**")
                df = pd.DataFrame(st.session_state.lich_su_kiem_tra)
                st.dataframe(df)

                # Tạo file Excel trong bộ nhớ đệm
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Lich_Su_Kiem_Tra')
                
                # Nút tải file
                ten_file = f"Bao_Cao_Ojitex_{datetime.now().strftime('%d%m%Y')}.xlsx"
                st.download_button(
                    label="📥 Tải file báo cáo Excel (.xlsx)",
                    data=buffer.getvalue(),
                    file_name=ten_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
