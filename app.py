import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. KONFIGURASI API ---
MY_API_KEY = "AIzaSyBJdViWnCZ7cnQE3Wx-c_WJQpWH_zsEHpI"
genai.configure(api_key=MY_API_KEY)

# --- 3. CUSTOM CSS (SIDEBAR TETAP GELAP) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; color: white !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: white !important; }
    button[title="Copy to clipboard"] { background-color: #28a745 !important; color: white !important; }
    .stImage > img { border-radius: 12px; border: 3px solid #28a745; }
    .stTextArea textarea { background-color: #262730 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("semangat buat alur cerita nya guys ❤️")

# --- 4. SIDEBAR: KONFIGURASI & REFERENSI ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    st.divider()
    st.subheader("👥 Identitas & Referensi Tokoh")
    
    characters = []
    # Input Karakter 1
    st.markdown("### **Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="UDIN")
    c1_desc = st.text_area("Deskripsi Fisik 1", key="char_desc_0", height=70)
    c1_img = st.file_uploader("Upload Foto 1", type=['png', 'jpg', 'jpeg'], key="img_ref_0", label_visibility="collapsed")
    if c1_img: st.image(c1_img, width=120)
    
    st.divider()
    # Input Karakter 2
    st.markdown("### **Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="TUNG")
    c2_desc = st.text_area("Deskripsi Fisik 2", key="char_desc_1", height=70)
    c2_img = st.file_uploader("Upload Foto 2", type=['png', 'jpg', 'jpeg'], key="img_ref_1", label_visibility="collapsed")
    if c2_img: st.image(c2_img, width=120)

# --- 5. INPUT DATA ADEGAN ---
st.subheader("📝 Detail Adegan")
scene_inputs = []
for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        cols = st.columns([2, 1])
        with cols[0]:
            u_desc = st.text_area(f"Visual Adegan {i}", key=f"desc_{i}", height=100)
        with cols[1]:
            s_time = st.selectbox(f"Waktu {i}", ["Pagi hari", "Siang hari", "Sore hari", "Malam hari"], key=f"time_{i}")
        scene_inputs.append({"num": i, "desc": u_desc, "time": s_time})

# --- 6. FUNGSI GENERATE (DENGAN DETEKSI MODEL) ---
def generate_visual_api(prompt, images, scene_num):
    try:
        # Mencoba mendeteksi model Imagen yang diizinkan di akun Anda
        all_models = [m.name for m in genai.list_models() if 'imagen' in m.name.lower()]
        
        if not all_models:
            st.error("❌ Model Imagen TIDAK DITEMUKAN di akun Anda.")
            st.warning("Solusi: Buka Google AI Studio, klik 'Settings' (ikon gerigi) -> 'Billing', dan klik 'Set up billing'.")
            return None
        
        # Mencoba model yang ditemukan satu per satu
        for model_name in all_models:
            try:
                model = genai.GenerativeModel(model_name)
                content = [prompt]
                if images:
                    for img in images: content.append(Image.open(img))
                
                response = model.generate_content(content)
                if response.images: return response.images[0]
            except:
                continue
        return None
    except Exception as e:
        st.error(f"Sistem Gagal: {e}")
        return None

# --- 7. TAMPILAN OUTPUT ---
st.divider()
if st.button("🚀 PROSES SEMUA ADEGAN", type="primary"):
    st.session_state.submitted = True

if st.session_state.get("submitted"):
    st.header("📋 Hasil Output PINTAR MEDIA")
    for scene in scene_inputs:
        if not scene["desc"].strip(): continue
        
        i = scene["num"]
        active_imgs = []
        char_ctx = ""
        # Deteksi Tokoh di Teks
        if c1_name and c1_name.lower() in scene["desc"].lower():
            char_ctx += f"{c1_name} ({c1_desc}). "
            if c1_img: active_imgs.append(c1_img)
        if c2_name and c2_name.lower() in scene["desc"].lower():
            char_ctx += f"{c2_name} ({c2_desc}). "
            if c2_img: active_imgs.append(c2_img)

        prompt = f"Consistent character scene {i}: {scene['desc']}. Characters: {char_ctx}. Time: {scene['time']}. natural photography style."

        st.subheader(f"Adegan {i}")
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("📸 PROMPT GAMBAR")
            st.code(prompt, language="text")
            if st.button(f"GENERATE VISUAL {i}", key=f"btn_gen_{i}"):
                res = generate_visual_api(prompt, active_imgs, i)
                if res: st.image(res, use_container_width=True)
        with col_b:
            st.caption("🎥 PROMPT VIDEO")
            st.code(f"Video motion, scene {i}: {scene['desc']}", language="text")
        st.divider()
