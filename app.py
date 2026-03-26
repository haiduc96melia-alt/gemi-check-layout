import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_cropper import st_cropper
import fitz  # Thư viện PyMuPDF để đọc file PDF

# Cấu hình giao diện
st.set_page_config(page_title="Gemi Check Layout", layout="centered")
st.title("Gemi Spot The Difference 🕵️‍♂️")

# --- HÀM HỖ TRỢ ĐỌC FILE PDF ---
def xu_ly_file_tai_len(uploaded_file):
    """Hàm này tự động nhận diện file là Ảnh hay PDF để xử lý"""
    if uploaded_file.name.lower().endswith('.pdf'):
        # Đọc file PDF từ bộ nhớ tạm
        pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        page = pdf_document.load_page(0) # Lấy trang đầu tiên của PDF
        # Chuyển trang PDF thành ảnh với độ phân giải cao (DPI 200)
        pix = page.get_pixmap(dpi=200) 
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img
    else:
        # Nếu là file ảnh bình thường
        return Image.open(uploaded_file)

# Khởi tạo bộ nhớ tạm
if 'anh_chuan_da_cat' not in st.session_state:
    st.session_state.anh_chuan_da_cat = None

# --- BƯỚC 1: TẢI BẢN CHUẨN (HỖ TRỢ PDF) VÀ CẮT ---
if st.session_state.anh_chuan_da_cat is None:
    st.subheader("Bước 1: Bản Chuẩn (Mẫu/PDF)")
    
    loai_anh = st.radio("Chọn cách nhập Bản Chuẩn:", ("Tải file (PDF/Ảnh)", "Chụp Camera"))
    
    img_chuan_goc = None
    
    if loai_anh == "Tải file (PDF/Ảnh)":
        # Cho phép chọn cả file PDF
        file_tai_len = st.file_uploader("Chọn file layout gốc", type=['pdf', 'jpg', 'jpeg', 'png'])
        if file_tai_len is not None:
            img_chuan_goc = xu_ly_file_tai_len(file_tai_len)
    else:
        pic_chuan = st.camera_input("Chụp bản chuẩn", key="cam_1")
        if pic_chuan is not None:
            img_chuan_goc = Image.open(pic_chuan)
            
    # Hiển thị công cụ cắt nếu đã có ảnh/pdf
    if img_chuan_goc is not None:
        st.write("👉 **Hãy kéo các góc khung xanh để khoanh vùng layout cần kiểm tra:**")
        cropped_img_chuan = st_cropper(img_chuan_goc, realtime_update=True, box_color='#00FF00', aspect_ratio=None)
        
        if st.button("✂️ XÁC NHẬN BẢN CHUẨN"):
            st.session_state.anh_chuan_da_cat = cropped_img_chuan
            st.rerun()

# --- BƯỚC 2: CHỤP BẢN THỰC TẾ & SO SÁNH ---
else:
    st.success("✅ Đã ghi nhớ Bản Chuẩn từ PDF/Ảnh!")
    if st.button("🔄 Thay đổi Bản Chuẩn"):
        st.session_state.anh_chuan_da_cat = None
        st.rerun()
        
    st.subheader("Bước 2: Bản Thực Tế (Thùng carton)")
    pic_thucte = st.camera_input("Chụp bản thực tế tại xưởng", key="cam_2")

    if pic_thucte is not None:
        img_thucte_goc = Image.open(pic_thucte)
        st.write("👉 **Hãy khoanh vùng sao cho vừa khít với Bản Chuẩn nhất:**")
        
        cropped_img_thucte = st_cropper(img_thucte_goc, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
        
        if st.button("🔍 XÁC NHẬN & PHÂN TÍCH LỖI"):
            st.write("Gemi đang soi lỗi, đợi một chút nhé...")
            
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
                if cv2.contourArea(c) < 800: # Lọc nhiễu nhỏ
                    continue
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(img1, (x, y), (x + w, y + h), (0, 0, 255), 4) # Khoanh đỏ
                count += 1

            img_result = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
            st.image(img_result, caption="Ảnh phân tích từ Gemi", use_container_width=True)
            
            if count == 0:
                st.success("🎉 TUYỆT VỜI! Mọi thứ khớp hoàn hảo với layout PDF.")
            else:
                st.error(f"⚠️ CẢNH BÁO: Phát hiện {count} điểm khác biệt (Đã khoanh đỏ)!")
