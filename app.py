import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_cropper import st_cropper
import fitz  
import io

# Tắt giới hạn pixel nhưng vẫn an toàn nhờ tối ưu RAM bên dưới
Image.MAX_IMAGE_PIXELS = None

st.set_page_config(page_title="Gemi Check Layout", layout="centered")
st.title("Gemi Spot The Difference 🕵️‍♂️")

def lay_so_trang_pdf(file_bytes):
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
    return len(pdf_document)

# TỐI ƯU HÓA: Chỉ xử lý 1 lần, hạ DPI và dùng JPEG đệm để cứu RAM
@st.cache_data
def xu_ly_file_tai_len(file_bytes, file_name, trang_so=0):
    if file_name.lower().endswith('.pdf'):
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        page = pdf_document.load_page(trang_so) 
        
        # Hạ dpi xuống 100 để máy chủ miễn phí không bị sập (trước là 200)
        pix = page.get_pixmap(dpi=100) 
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        buf = io.BytesIO()
        # Dùng JPEG chất lượng cao thay vì PNG để siêu tiết kiệm bộ nhớ
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return Image.open(buf)
    else:
        # Nếu là ảnh thường, đảm bảo chuyển về hệ màu chuẩn
        return Image.open(io.BytesIO(file_bytes)).convert("RGB")

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
            file_bytes_1 = file_1.getvalue()
            if file_1.name.lower().endswith('.pdf'):
                tong_so_trang = lay_so_trang_pdf(file_bytes_1)
                if tong_so_trang > 1:
                    trang_chon = st.selectbox(f"File có {tong_so_trang} trang. Chọn trang cần xem:", range(1, tong_so_trang + 1), key="page_1")
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
            file_bytes_2 = file_2.getvalue()
            if file_2.name.lower().endswith('.pdf'):
                tong_so_trang_2 = lay_so_trang_pdf(file_bytes_2)
                if tong_so_trang_2 > 1:
                    trang_chon_2 = st.selectbox(f"File có {tong_so_trang_2} trang. Chọn trang cần xem:", range(1, tong_so_trang_2 + 1), key="page_2")
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
            
            # --- XỬ LÝ SO SÁNH ---
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
