import streamlit as st
import cv2
import numpy as np
from PIL import Image

# Cấu hình giao diện
st.set_page_config(page_title="Gemi Check Layout", layout="centered")
st.title("Gemi Spot The Difference 🕵️‍♂️")
st.write("Chụp ảnh mẫu và ảnh thực tế trên dây chuyền để tìm lỗi bavia/sai lệch layout.")

# --- CỘT 1: CHỤP ẢNH CHUẨN ---
st.subheader("1. Bản Chuẩn (Mẫu/PDF)")
pic_chuan = st.camera_input("Chụp bản chuẩn", key="cam_1")

# --- CỘT 2: CHỤP ẢNH THỰC TẾ ---
st.subheader("2. Bản Thực Tế (Thùng carton)")
pic_thucte = st.camera_input("Chụp bản thực tế", key="cam_2")

# --- XỬ LÝ SO SÁNH ---
if pic_chuan is not None and pic_thucte is not None:
    st.write("Gemi đang phân tích...")
    
    # Chuyển đổi ảnh từ Camera sang định dạng OpenCV đọc được
    img1_pil = Image.open(pic_chuan)
    img1 = cv2.cvtColor(np.array(img1_pil), cv2.COLOR_RGB2BGR)
    
    img2_pil = Image.open(pic_thucte)
    img2 = cv2.cvtColor(np.array(img2_pil), cv2.COLOR_RGB2BGR)
    
    # Cân chỉnh kích thước ảnh thực tế bằng với ảnh chuẩn
    height, width, _ = img1.shape
    img2_res = cv2.resize(img2, (width, height))
    
    # Tìm điểm khác biệt
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2_res, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(g1, g2)
    _, thresh = cv2.threshold(diff, 35, 255, cv2.THRESH_BINARY)
    
    # Tìm vùng lỗi
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    count = 0
    for c in cnts:
        if cv2.contourArea(c) < 800: # Bỏ qua các hạt bụi nhỏ
            continue
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(img1, (x, y), (x + w, y + h), (0, 0, 255), 5) # Vẽ khung đỏ
        count += 1

    # Chuyển đổi lại hệ màu để hiển thị trên web
    img_result = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
    
    # --- HIỂN THỊ KẾT QUẢ ---
    st.image(img_result, caption="Ảnh phân tích từ Gemi", use_container_width=True)
    
    if count == 0:
        st.success("🎉 TUYỆT VỜI! Không phát hiện điểm khác biệt.")
    else:
        st.error(f"⚠️ CẢNH BÁO: Phát hiện {count} điểm khác biệt (Đã khoanh đỏ)!")