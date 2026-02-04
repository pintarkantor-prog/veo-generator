import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. KONFIGURASI API OTOMATIS ---
# Menggunakan API Key yang telah Anda berikan secara otomatis
MY_API_KEY = "AIzaSyBJdViWnCZ7cnQE3Wx-c_WJQpWH_zsEHpI"
genai.configure(api_key=MY_API_KEY)

# --- 3. CUSTOM CSS (PERBAIKAN SIDEBAR & TEXT) ---
st.markdown("""
    <style>
    /* Memaksa Sidebar berwarna gelap dan teks putih agar terbaca jelas */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
        color: white !important;
    }
    
    /* Memastikan semua teks di sidebar (label, span, p) berwarna putih */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: white !important;
    }

    /* Tombol Copy Hijau Terang agar kontras dan mudah terlihat */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important;
        border-radius: 6px !important;
        border: 1px solid #ffffff !important;
        transform: scale(1.1);
    }
    
    /* Styling Hasil Gambar dari API */
    .stImage > img {
        border-radius: 12px;
        border: 3px solid #28a745;
    }

    /* Merapikan tampilan input area agar nyaman di mata */
    .stTextArea textarea {
        background-color: #262730 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("semangat buat alur cerita nya guys ❤️❤️❤️")

# --- 4. SIDEBAR: KONFIGURASI & UPLOAD REFERENSI ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Referensi Tokoh")
    st.write("Upload foto karakter agar AI mengikuti visual yang sama.")
    
    characters = []

    # --- INPUT KARAKTER 1 ---
    st.markdown("### **Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="Contoh: UDIN")
    c1_desc = st.text_area("Deskripsi Fisik 1", key="char_desc_0", placeholder="Detail baju, rambut, dll...", height=70)
    c1_img = st.file_uploader("Upload Foto Karakter 1", type=['png', 'jpg', 'jpeg'], key="img_ref_0")
    if c1_img:
        st.image(c1_img, caption="Preview Karakter 1", width=120)
    
    st.divider()

    # --- INPUT KARAKTER 2 ---
    st.markdown("### **Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="Contoh: TUNG")
    c2_desc = st.text_area("Deskripsi Fisik 2", key="char_desc_1", placeholder="Detail fisik...", height=70)
    c2_img = st.file_uploader("Upload Foto Karakter 2", type=['png', 'jpg', 'jpeg'], key="img_ref_1")
    if c2_img:
        st.image(c2_img, caption="Preview Karakter 2", width=120)

    st.divider()
    num_chars = st.number_input("Tambah Karakter Lainnya", min_value=2, max_value=5, value=2)

# --- 5. PARAMETER KUALITAS VISUAL ---
img_quality = (
    "natural photography style, raw photo, captured on 35mm lens, f/8, "
    "authentic skin texture, natural lighting, sharp details, "
    "consistent character appearance, high resolution, NO 3D, NO render, NO cartoon"
)

# --- 6. FORM INPUT DATA ADEGAN ---
st.subheader("📝 Detail Adegan")
scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        # Layout: Visual (2) + Waktu (1) + Dialog Tokoh (1 per karakter)
        col_setup = [2, 1] + [1] * int(num_chars)
        cols = st.columns(col_setup)
        
        with cols[0]:
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"desc_{i}", height=100)
        with cols[1]:
            scene_time = st.selectbox(f"Waktu {i}", ["Pagi hari", "Siang hari", "Sore hari", "Malam hari"], key=f"time_{i}")
        
        scene_dialogs = []
        for idx in range(int(num_chars)):
            with cols[idx + 2]:
                char_label = f"Karakter {idx+1}"
                d_input = st.text_input(f"Dialog {char_label}", key=f"diag_{idx}_{i}")
                scene_dialogs.append({"name": char_label, "text": d_input})
        
        # Simpan data adegan jika deskripsi diisi
        scene_data.append({"num": i, "desc": user_desc, "time": scene_time, "dialogs": scene_dialogs})

st.divider()

# --- 7. TOMBOL GENERATE (LOGIKA MULTIMODAL) ---
if st.button("🚀 BUAT PROMPT & GENERATE VISUAL", type="primary"):
    # Filter hanya adegan yang sudah diinput deskripsinya
    filled_scenes = [s for s in scene_data if s["desc"].strip() != ""]
    
    if not filled_scenes:
        st.warning("Silakan isi kolom 'Visual Adegan' pada form yang tersedia.")
    else:
        st.header("📋 Hasil Output PINTAR MEDIA")
        
        for scene in filled_scenes:
            i = scene["num"]
            v_input = scene["desc"]
            
            # Logika Deteksi Karakter & Penggunaan Referensi Gambar
            active_images = []
            char_context = ""
            
            if c1_name and c1_name.lower() in v_input.lower():
                char_context += f"{c1_name} ({c1_desc}). "
                if c1_img:
                    active_images.append(Image.open(c1_img))
            
            if c2_name and c2_name.lower() in v_input.lower():
                char_context += f"{c2_name} ({c2_desc}). "
                if c2_img:
                    active_images.append(Image.open(c2_img))
            
            # Gabungkan Prompt untuk AI
            final_img_prompt = (
                f"Consistent character scene {i}. Visual: {v_input}. "
                f"Characters appearing: {char_context}. Time: {scene['time']}. {img_quality}"
            )

            st.subheader(f"Adegan {i}")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.caption("📸 PROMPT & VISUAL GAMBAR")
                st.code(final_img_prompt, language="text")
                
                # Tombol Generate untuk memicu API Imagen-3
                if st.button(f"Generate Visual Adegan {i}", key=f"btn_gen_{i}"):
                    with st.spinner(f"AI sedang menganalisis foto referensi & teks adegan {i}..."):
                        try:
                            # Memanggil model Imagen 3 (Banana)
                            model = genai.GenerativeModel('imagen-3.0-generate-001')
                            api_input = [final_img_prompt]
                            if active_images:
                                api_input.extend(active_images)
                                
                            response = model.generate_content(api_input)
                            st.image(response.images[0], use_container_width=True, caption=f"Visual Adegan {i}")
                        except Exception as e:
                            st.error(f"Gagal generate: {e}. Pastikan model tersedia di akun Anda.")

            with col_b:
                st.caption("🎥 PROMPT VIDEO (Copy Manual)")
                st.code(f"Natural motion, scene {i}. Visual: {v_input}. Characters: {char_context}", language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v3.4")
