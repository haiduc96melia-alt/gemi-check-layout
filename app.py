import streamlit as st
import cv2
import numpy as np
from PIL import Image

# Cấu hình giao diện
st.set_page_config(page_title="Gemi Check Layout", layout="centered")
st.title("Gemi Spot The Difference 🕵️‍♂️")

# Sử dụng bộ nhớ tạm của Streamlit để lưu ảnh Bản Chuẩn
if 'anh_chuan' not in st.session_state:
    st.session_state.anh_chuan = None

# --- BƯỚC 1: CHỤP ẢNH CHUẨN ---
if st.session_state.anh_chuan is None:
    st.subheader("Bước 1: Chụp Bản Chuẩn (Mẫu/PDF)")
    st.info("Hãy đưa bản vẽ hoặc mẫu chuẩn vào khung hình và chụp trước nhé.")
    
    pic_chuan = st.camera_input("Chụp bản chuẩn", key="cam_1")
    
    # Nếu chụp xong, lưu ảnh và tải lại trang để sang Bước 2
    if pic_chuan is not None:
        st.session_state.anh_chuan = pic_chuan
        st.rerun()

# --- BƯỚC 2: CHỤP ẢNH THỰC TẾ & SO SÁNH ---
else:
    st.success("✅ Đã ghi nhớ Bản Chuẩn!")
    
    # Nút để chụp lại nếu ảnh bước 1 bị mờ
    if st.button("📸 Chụp lại Bản Chuẩn"):
        st.session_state.anh_chuan = None
        st.rerun()
        
    st.subheader("Bước 2: Chụp Bản Thực Tế (Thùng carton)")
    pic_thucte = st.camera_input("Chụp bản thực tế", key="cam_2")

    # --- XỬ LÝ SO SÁNH ---
    if pic_thucte is not None:
        st.write("Gemi đang phân tích, chờ chút nhé...")
        
        # Đọc ảnh từ bộ nhớ
        img1_pil = Image.open(st.session_state.anh_chuan)
        img1 = cv2.cvtColor(np.array(img1_pil), cv2.COLOR_RGB2BGR)
        
        img2_pil = Image.open(pic_thucte)
        img2 = cv2.cvtColor(np.array(img2_pil), cv2.COLOR_RGB2BGR)
        
        # Cân chỉnh kích thước
        height, width, _ = img1.shape
        img2_res = cv2.resize(img2, (width, height))
        
        # Tìm điểm khác biệt
        g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        g2 = cv2.cvtColor(img2_res, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(g1, g2)
        _, thresh = cv2.threshold(diff, 35, 255, cv2.THRESH_BINARY)
        
        cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        count = 0
        for c in cnts:
            if cv2.contourArea(c) < 800: # Lọc nhiễu
                continue
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(img1, (x, y), (x + w, y + h), (0, 0, 255), 5) # Vẽ khung đỏ
            count += 1

        # Hiển thị kết quả
        img_result = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
        st.image(img_result, caption="Ảnh phân tích từ Gemi", use_container_width=True)
        
        if count == 0:
            st.success("🎉 TUYỆT VỜI! Không phát hiện lỗi bavia hay sai lệch.")
        else:
            st.error(f"⚠️ CẢNH BÁO: Phát hiện {count} điểm khác biệt (Đã khoanh đỏ)!")
