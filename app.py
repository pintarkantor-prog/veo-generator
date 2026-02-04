import streamlit as st

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. CUSTOM CSS (TAMPILAN SIDEBAR & TOMBOL HIJAU) ---
st.markdown("""
    <style>
    /* Sidebar Gelap Profesional */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    
    /* Teks Sidebar Putih */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: white !important;
    }

    /* Tombol Copy Hijau Terang */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 1px solid #ffffff !important;
        transform: scale(1.1); 
    }
    
    button[title="Copy to clipboard"]:active {
        background-color: #1e7e34 !important;
    }
    
    .stTextArea textarea {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("semangat buat alur cerita nya guys ❤️")

# --- 3. SIDEBAR: KONFIGURASI TOKOH & SKALA TINGGI ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Skala Postur")
    
    characters = []

    # Karakter 1 (Referensi Utama)
    st.markdown("**Karakter 1 (Patokan Tinggi)**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="Contoh: UDIN")
    c1_desc = st.text_area("Deskripsi Fisik 1", key="char_desc_0", placeholder="Pria dewasa, tinggi 180cm, tegap...", height=68)
    characters.append({"name": c1_name, "desc": c1_desc, "height_rel": "sebagai referensi tinggi utama"})
    
    st.divider()

    # Karakter 2 (Relatif terhadap Karakter 1)
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="Contoh: TUNG")
    c2_h_rel = st.selectbox("Tinggi Karakter 2", 
                            ["Lebih tinggi dari Karakter 1", 
                             "Sama tinggi dengan Karakter 1", 
                             "Lebih pendek dari Karakter 1",
                             "Sangat kecil (setinggi lutut Karakter 1)"], key="h_rel_1")
    c2_desc = st.text_area("Deskripsi Fisik 2", key="char_desc_1", placeholder="Log kayu hidup, kaki pendek...", height=68)
    characters.append({"name": c2_name, "desc": c2_desc, "height_rel": c2_h_rel})

    st.divider()
    num_chars = st.number_input("Tambah Karakter Lainnya", min_value=2, max_value=5, value=2)

# --- 4. PARAMETER KUALITAS & KONSISTENSI SKALA ---
img_quality = (
    "resolution 1080x1920 pixels, vertical 9:16 aspect ratio, edge-to-edge portrait, "
    "maintain strict height scale between characters, accurate body proportions, "
    "consistent character height in every frame, no black bars, no letterbox, "
    "auto-enhance facial features, restore skin texture, extreme sharpness, "
    "vivid color saturation, hyper-detailed 8k, natural lighting, 35mm lens, f/11, --ar 9:16"
)

vid_quality = (
    "1080x1920 pixels, 9:16 vertical video, accurate height difference between characters, "
    "smooth motion, high-fidelity restoration, vivid colors, 60fps, sharp focus, NO CGI"
)

# --- 5. FORM INPUT ADEGAN ---
st.subheader("📝 Detail Adegan")
scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        col_setup = [2, 1] + [1] * len(characters)
        cols = st.columns(col_setup)
        
        with cols[0]:
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"desc_{i}", height=100)
        with cols[1]:
            scene_time = st.selectbox(f"Waktu {i}", ["Pagi hari", "Siang hari", "Sore hari", "Malam hari"], key=f"time_{i}")
        
        scene_dialogs = []
        for idx, char in enumerate(characters):
            with cols[idx + 2]:
                char_label = char['name'] if char['name'] else f"Karakter {idx+1}"
                d_input = st.text_input(f"Dialog {char_label}", key=f"diag_{idx}_{i}")
                scene_dialogs.append({"name": char_label, "text": d_input})
        
        scene_data.append({"num": i, "desc": user_desc, "time": scene_time, "dialogs": scene_dialogs})

st.divider()

# --- 6. TOMBOL GENERATE ---
if st.button("🚀 BUAT PROMPT", type="primary"):
    filled_scenes = [s for s in scene_data if s["desc"].strip() != ""]
    
    if not filled_scenes:
        st.warning("Silakan isi kolom 'Visual Adegan'.")
    else:
        st.header("📋 Hasil Prompt")
        
        # Ringkasan Skala Tinggi untuk Prompt
        height_summary = f"Height Consistency Rules: {characters[0]['name']} is the primary height anchor. "
        if len(characters) > 1:
            height_summary += f"{characters[1]['name']} is strictly {characters[1]['height_rel']}. "

        for scene in filled_scenes:
            i = scene["num"]
            v_input = scene["desc"]
            
            detected_physique = []
            for char in characters:
                if char['name'] and char['name'].lower() in v_input.lower():
                    detected_physique.append(f"{char['name']} ({char['desc']})")
            
            char_ref = "Characters Appearance: " + ", ".join(detected_physique) + ". " if detected_physique else ""
            
            time_map = {
                "Pagi hari": "vibrant morning sun, crystal clear golden light",
                "Siang hari": "intense bright midday sun, vivid sky, punchy shadows",
                "Sore hari": "deep orange sunset glow, high contrast lighting",
                "Malam hari": "neon vivid night lighting, deep rich blacks, sharp light sources"
            }
            eng_time = time_map.get(scene["time"], "clear natural lighting")
            
            # PROMPT GAMBAR
            final_img = (
                f"buatkan saya sebuah gambar adegan ke {i}. {height_summary} "
                f"pertajam kualitas visual dari referensi, perbaiki detail wajah dan tekstur. "
                f"Visual: {char_ref}{v_input}. Waktu: {scene['time']}. "
                f"Environment: {eng_time}. {img_quality}"
            )

            # PROMPT VIDEO
            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            dialog_part = f"\n\nDialog:\n" + "\n".join(dialog_lines) if dialog_lines else ""

            final_vid = (
                f"Generate a vertical 1080x1920 video for Scene {i}. {height_summary} "
                f"Ensure accurate height scale between {characters[0]['name']} and other characters. "
                f"Visual: {char_ref}{v_input}. Lighting: {eng_time}. {vid_quality}.{dialog_part}"
            )

            st.subheader(f"Adegan {i}")
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.caption(f"📸 PROMPT GAMBAR")
                st.code(final_img, language="text")
            with res_col2:
                st.caption(f"🎥 PROMPT VIDEO")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v3.8 - Height & Scale Optimized")
