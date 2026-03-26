import streamlit as st
import cv2
import numpy as np
from PIL import Image
from streamlit_cropper import st_cropper

# Cấu hình giao diện
st.set_page_config(page_title="Gemi Check Layout", layout="centered")
st.title("Gemi Spot The Difference 🕵️‍♂️")

# Khởi tạo bộ nhớ tạm để lưu ảnh ĐÃ CẮT
if 'anh_chuan_da_cat' not in st.session_state:
    st.session_state.anh_chuan_da_cat = None

# --- BƯỚC 1: CHỤP VÀ CẮT ẢNH CHUẨN ---
if st.session_state.anh_chuan_da_cat is None:
    st.subheader("Bước 1: Bản Chuẩn (Mẫu/PDF)")
    
    # Cho phép tải ảnh lên hoặc chụp từ Camera
    loai_anh = st.radio("Chọn nguồn ảnh Bản Chuẩn:", ("Chụp Camera", "Tải file lên"))
    pic_chuan = None
    
    if loai_anh == "Chụp Camera":
        pic_chuan = st.camera_input("Chụp bản chuẩn", key="cam_1")
    else:
        pic_chuan = st.file_uploader("Chọn file ảnh chuẩn", type=['jpg', 'jpeg', 'png'])
    
    # Nếu đã có ảnh (chụp hoặc tải lên), hiển thị công cụ cắt
    if pic_chuan is not None:
        img_chuan_goc = Image.open(pic_chuan)
        st.write("👉 **Hãy kéo các góc khung xanh để khoanh vùng cần kiểm tra:**")
        
        # Công cụ cắt ảnh (trên điện thoại vuốt rất mượt)
        cropped_img_chuan = st_cropper(img_chuan_goc, realtime_update=True, box_color='#00FF00', aspect_ratio=None)
        
        if st.button("✂️ XÁC NHẬN BẢN CHUẨN"):
            st.session_state.anh_chuan_da_cat = cropped_img_chuan
            st.rerun()

# --- BƯỚC 2: CHỤP, CẮT ẢNH THỰC TẾ & SO SÁNH ---
else:
    st.success("✅ Đã ghi nhớ Bản Chuẩn!")
    if st.button("🔄 Làm lại Bước 1"):
        st.session_state.anh_chuan_da_cat = None
        st.rerun()
        
    st.subheader("Bước 2: Bản Thực Tế (Thùng carton)")
    pic_thucte = st.camera_input("Chụp bản thực tế tại xưởng", key="cam_2")

    if pic_thucte is not None:
        img_thucte_goc = Image.open(pic_thucte)
        st.write("👉 **Hãy khoanh vùng sao cho kích thước tương đồng với Bản Chuẩn nhất:**")
        
        cropped_img_thucte = st_cropper(img_thucte_goc, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
        
        if st.button("🔍 XÁC NHẬN & PHÂN TÍCH LỖI"):
            st.write("Gemi đang soi lỗi, đợi một chút nhé...")
            
            # --- XỬ LÝ SO SÁNH TRÊN 2 ẢNH ĐÃ CẮT ---
            # Chuyển đổi ảnh chuẩn
            img1 = cv2.cvtColor(np.array(st.session_state.anh_chuan_da_cat), cv2.COLOR_RGB2BGR)
            # Chuyển đổi ảnh thực tế
            img2 = cv2.cvtColor(np.array(cropped_img_thucte), cv2.COLOR_RGB2BGR)
            
            # Cân chỉnh kích thước ảnh 2 theo ảnh 1
            height, width, _ = img1.shape
            img2_res = cv2.resize(img2, (width, height))
            
            # Thuật toán tìm điểm khác biệt
            g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            g2 = cv2.cvtColor(img2_res, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(g1, g2)
            _, thresh = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
            
            cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            count = 0
            for c in cnts:
                if cv2.contourArea(c) < 800: # Lọc các hạt bụi siêu nhỏ
                    continue
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(img1, (x, y), (x + w, y + h), (0, 0, 255), 5) # Vẽ khung đỏ
                count += 1

            # Hiển thị kết quả
            img_result = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
            st.image(img_result, caption="Ảnh phân tích từ Gemi (Vùng đã cắt)", use_container_width=True)
            
            if count == 0:
                st.success("🎉 TUYỆT VỜI! Không phát hiện lỗi bavia hay sai lệch layout.")
            else:
                st.error(f"⚠️ CẢNH BÁO: Phát hiện {count} điểm khác biệt (Đã khoanh đỏ)!")
