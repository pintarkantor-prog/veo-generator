import streamlit as st

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. CUSTOM CSS (SIDEBAR & TOMBOL COPY HIJAU) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: white !important; }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 1px solid #ffffff !important;
        transform: scale(1.1); 
    }
    button[title="Copy to clipboard"]:active { background-color: #1e7e34 !important; }
    .stTextArea textarea { font-size: 14px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("semangat buat alur cerita nya guys ❤️")

# --- 3. SIDEBAR: KONFIGURASI TOKOH ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas Tokoh")
    
    characters = []
    # Karakter 1
    st.markdown("**Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="UDIN")
    c1_desc = st.text_area("Fisik 1", key="char_desc_0", placeholder="Contoh: Pria kepala jeruk, jaket denim...", height=68)
    characters.append({"name": c1_name, "desc": c1_desc})
    
    st.divider()
    # Karakter 2
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="TUNG")
    c2_desc = st.text_area("Fisik 2", key="char_desc_1", placeholder="Contoh: Manusia kayu, mata biru...", height=68)
    characters.append({"name": c2_name, "desc": c2_desc})

    st.divider()
    num_chars = st.number_input("Tambah Karakter Lainnya", min_value=2, max_value=5, value=2)

# --- 4. PARAMETER KUALITAS (Optimasi Bananan untuk Gambar, Veo 3 untuk Video) ---

# --- Untuk Bananan (Gambar) ---
img_quality = (
    "full body vertical portrait, 1080x1920 pixels, 9:16 aspect ratio, edge-to-edge frame, "
    "no black bars, no padding, no borders, ultra-vivid color saturation, "
    "deep color depth, extreme sharpness, hyper-detailed textures, crystal clear 8k resolution, "
    "bold and punchy colors, intense contrast, sharp outlines, natural sunlight photography, "
    "captured on 35mm lens, f/11 aperture, unprocessed style, NO cartoon, NO letterbox"
)

# --- Untuk Veo 3 (Video) ---
vid_quality = (
    "veo 3 high-quality video, 9:16 vertical full-screen, 1080p, 60fps, "
    "dynamic camera movement, cinematic smooth motion, ultra-sharp focus on action, "
    "vivid color grading, natural light falloff, authentic fluid movements, "
    "no motion blur artifacts, highly detailed textures in motion, NO animation, NO CGI look"
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
        st.header("📋 Hasil Prompt (Bananan & Veo 3 Optimized)")
        for scene in filled_scenes:
            i = scene["num"]
            v_input = scene["desc"]
            
            # Auto-Expression Engine
            dialog_summary = " ".join([f"{d['name']} says {d['text']}" for d in scene['dialogs'] if d['text']])
            expression_instruction = (
                f"Analyze the drama: '{v_input}' and dialogue: '{dialog_summary}'. "
                "Render precise facial expressions and emotional eye contact to match this scene. "
            )
            
            detected_physique = []
            for char in characters:
                if char['name'] and char['name'].lower() in v_input.lower():
                    detected_physique.append(f"{char['name']} ({char['desc']})")
            
            char_ref = "Characters Appearance: " + ", ".join(detected_physique) + ". " if detected_physique else ""
            
            # Waktu Mapping (untuk Gambar & Video)
            time_map = {
                "Pagi hari": "vibrant morning sun, clear light",
                "Siang hari": "intense bright midday sun, vivid sky, punchy shadows",
                "Sore hari": "warm sunset orange glow, high contrast",
                "Malam hari": "ambient night lighting, deep rich blacks"
            }
            eng_time = time_map.get(scene["time"], "natural lighting")

            # --- Prompt Khusus untuk Bananan (Gambar) ---
            final_img = (
                f"buatkan saya sebuah gambar adegan ke {i}. ini adalah gambar referensi karakter saya. "
                f"tampilkan gambar secara full-screen portrait 1080x1920 tanpa border hitam. "
                f"{expression_instruction} Visual: {char_ref}{v_input}. Waktu: {scene['time']}. "
                f"Lighting: {eng_time}. {img_quality}"
            )

            # --- Prompt Khusus untuk Veo 3 (Video) ---
            final_vid = (
                f"Generate a 9:16 vertical full-screen video for Scene {i} in 1080p, 60fps. "
                f"Focus on dynamic camera, smooth motion, and sharp action. "
                f"{expression_instruction} Visual: {char_ref}{v_input}. Waktu: {scene['time']}. "
                f"Lighting: {eng_time}. {vid_quality}"
            )

            st.subheader(f"Adegan {i}")
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.caption(f"📸 PROMPT GAMBAR (Bananan 9:16 Optimized)")
                st.code(final_img, language="text")
            with res_col2:
                st.caption(f"🎥 PROMPT VIDEO (Veo 3 Optimized)")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA v4.1 - Bananan & Veo 3 Engine")
