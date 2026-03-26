import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_cropper import st_cropper
import fitz  # Thư viện PyMuPDF

# Cấu hình giao diện
st.set_page_config(page_title="Gemi Check Layout", layout="centered")
st.title("Gemi Spot The Difference 🕵️‍♂️")

# --- HÀM HỖ TRỢ XỬ LÝ FILE PDF/ẢNH ---
def lay_so_trang_pdf(uploaded_file):
    """Đếm tổng số trang của file PDF"""
    pdf_document = fitz.open(stream=uploaded_file.getvalue(), filetype="pdf")
    return len(pdf_document)

def xu_ly_file_tai_len(uploaded_file, trang_so=0):
    """Xử lý file tải lên (đọc đúng trang PDF hoặc đọc Ảnh)"""
    if uploaded_file.name.lower().endswith('.pdf'):
        pdf_document = fitz.open(stream=uploaded_file.getvalue(), filetype="pdf")
        page = pdf_document.load_page(trang_so) # Đọc trang được chỉ định
        pix = page.get_pixmap(dpi=200) # Xuất ảnh độ phân giải cao
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img
    else:
        return Image.open(uploaded_file)

# Khởi tạo bộ nhớ tạm cho Bản Chuẩn
if 'anh_chuan_da_cat' not in st.session_state:
    st.session_state.anh_chuan_da_cat = None

# ==========================================
# BƯỚC 1: BẢN CHUẨN (MẪU GỐC)
# ==========================================
if st.session_state.anh_chuan_da_cat is None:
    st.subheader("Bước 1: Bản Chuẩn (Mẫu/PDF)")
    loai_anh_1 = st.radio("Chọn cách nhập Bản Chuẩn:", ("Tải file (PDF/Ảnh)", "Chụp Camera"), key="radio_1")
    img_chuan_goc = None
    
    if loai_anh_1 == "Tải file (PDF/Ảnh)":
        file_1 = st.file_uploader("Chọn file layout gốc", type=['pdf', 'jpg', 'jpeg', 'png'], key="file_1")
        if file_1 is not None:
            # Nếu là PDF, kiểm tra số trang
            if file_1.name.lower().endswith('.pdf'):
                tong_so_trang = lay_so_trang_pdf(file_1)
                if tong_so_trang > 1:
                    trang_chon = st.selectbox(f"File có {tong_so_trang} trang. Chọn trang cần xem:", range(1, tong_so_trang + 1), key="page_1")
                    img_chuan_goc = xu_ly_file_tai_len(file_1, trang_chon - 1)
                else:
                    img_chuan_goc = xu_ly_file_tai_len(file_1, 0)
            else:
                img_chuan_goc = xu_ly_file_tai_len(file_1)
    else:
        pic_1 = st.camera_input("Chụp bản chuẩn", key="cam_1")
        if pic_1 is not None:
            img_chuan_goc = Image.open(pic_1)
            
    # Hiển thị công cụ cắt cho Bản Chuẩn
    if img_chuan_goc is not None:
        st.write("👉 **Kéo khung xanh để lấy vùng layout:**")
        # SỬA LỖI: aspect_ratio=None cho phép kéo khung tự do
        cropped_img_chuan = st_cropper(img_chuan_goc, realtime_update=True, box_color='#00FF00', aspect_ratio=None, key="crop_1")
        if st.button("✂️ XÁC NHẬN BẢN CHUẨN"):
            st.session_state.anh_chuan_da_cat = cropped_img_chuan
            st.rerun()

# ==========================================
# BƯỚC 2: BẢN THỰC TẾ & SO SÁNH
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
            if file_2.name.lower().endswith('.pdf'):
                tong_so_trang_2 = lay_so_trang_pdf(file_2)
                if tong_so_trang_2 > 1:
                    trang_chon_2 = st.selectbox(f"File có {tong_so_trang_2} trang. Chọn trang cần xem:", range(1, tong_so_trang_2 + 1), key="page_2")
                    img_thucte_goc = xu_ly_file_tai_len(file_2, trang_chon_2 - 1)
                else:
                    img_thucte_goc = xu_ly_file_tai_len(file_2, 0)
            else:
                img_thucte_goc = xu_ly_file_tai_len(file_2)
    else:
        pic_2 = st.camera_input("Chụp bản thực tế tại xưởng", key="cam_2")
        if pic_2 is not None:
            img_thucte_goc = Image.open(pic_2)

    # Hiển thị công cụ cắt cho Bản Thực Tế và Tiến hành So sánh
    if img_thucte_goc is not None:
        st.write("👉 **Kéo khung đỏ sao cho vừa khít với Bản Chuẩn nhất:**")
        # SỬA LỖI: aspect_ratio=None cho phép kéo khung tự do, key="crop_2" phải khác crop_1
        cropped_img_thucte = st_cropper(img_thucte_goc, realtime_update=True, box_color='#FF0000', aspect_ratio=None, key="crop_2")
        
        if st.button("🔍 XÁC NHẬN & PHÂN TÍCH LỖI"):
            st.write("Gemi đang soi lỗi, đợi một chút nhé...")
            
            # --- XỬ LÝ SO SÁNH ---
            # Chuyển đổi màu sắc để OpenCV đọc hiểu
            img1 = cv2.cvtColor(np.array(st.session_state.anh_chuan_da_cat), cv2.COLOR_RGB2BGR)
            img2 = cv2.cvtColor(np.array(cropped_img_thucte), cv2.COLOR_RGB2BGR)
            
            # Cân chỉnh kích thước ảnh 2 bằng ảnh 1
            height, width, _ = img1.shape
            img2_res = cv2.resize(img2, (width, height))
            
            # Thuật toán bắt lỗi
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
                cv2.rectangle(img1, (x, y), (x + w, y + h), (0, 0, 255), 4) # Khoanh đỏ
                count += 1

            img_result = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
            st.image(img_result, caption="Ảnh phân tích từ Gemi", use_container_width=True)
            
            if count == 0:
                st.success("🎉 TUYỆT VỜI! Mọi thứ khớp hoàn hảo.")
            else:
                st.error(f"⚠️ CẢNH BÁO: Phát hiện {count} điểm khác biệt (Đã khoanh đỏ)!")
