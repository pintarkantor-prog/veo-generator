import streamlit as st

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. CUSTOM CSS ---
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
st.info("Mode: Tajam Menyeluruh (Karakter & Latar Belakang) ❤️")

# --- 3. SIDEBAR: KONFIGURASI TOKOH ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas Tokoh")
    characters = []
    st.markdown("**Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="UDIN")
    c1_desc = st.text_area("Fisik 1", key="char_desc_0", placeholder="Pria kepala jeruk...", height=68)
    characters.append({"name": c1_name, "desc": c1_desc})
    
    st.divider()
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="TUNG")
    c2_desc = st.text_area("Fisik 2", key="char_desc_1", placeholder="Manusia kayu...", height=68)
    characters.append({"name": c2_name, "desc": c2_desc})

# --- 4. PARAMETER KUALITAS (FULL FRAME SHARPNESS) ---
# Menggunakan f/11 untuk memastikan latar belakang setajam karakter
# Menggunakan 'organic color depth' untuk warna yang kuat tapi tidak menyilaukan
img_quality = (
    "full body vertical portrait, 1080x1920 pixels, 9:16 aspect ratio, edge-to-edge frame, "
    "edge-to-edge sharpness, deep focus, f/11 aperture, maximum texture detail on every object, "
    "sharp background, high-resolution scenery, organic color depth, balanced exposure, "
    "soft morning light at 10:00 AM, diffused illumination, no harsh sunbeams, no lens flare, "
    "unprocessed raw photography, 8k resolution, captured on 35mm lens, "
    "STRICTLY NO speech bubbles, NO text on image, NO watermarks, NO subtitles, NO cartoon"
)

vid_quality = (
    "veo 3 high-quality video, 9:16 vertical 1080p, 60fps, "
    "10:00 AM diffused lighting, sharp background details, deep focus, "
    "organic colors, authentic fluid movements, NO motion blur, NO animation"
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
            # Setting khusus untuk cahaya pukul 10 pagi yang sejuk namun tajam
            scene_time = st.selectbox(f"Suasana {i}", 
                                     ["10:00 AM (Sejuk & Tajam)", "10:00 AM (Berawan Tipis)"], 
                                     key=f"time_{i}")
        
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
        st.header("📋 Hasil Prompt (Full Sharpness Mode)")
        
        time_map = {
            "10:00 AM (Sejuk & Tajam)": "10:00 AM, cool temperature, clear visibility, soft shadow, sharp background scenery",
            "10:00 AM (Berawan Tipis)": "10:00 AM, filtered light, no glare, organic color saturation, high detail on surroundings"
        }

        for scene in filled_scenes:
            i = scene["num"]
            v_input = scene["desc"]
            eng_time = time_map.get(scene["time"])
            
            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            dialog_text = " ".join(dialog_lines) if dialog_lines else ""
            
            expression_instruction = (
                f"Emotion Analysis: mood from '{dialog_text}'. "
                "Render facial micro-expressions with organic surface textures. "
                "Do NOT include any speech bubbles, NO text."
            )
            
            detected_physique = []
            for char in characters:
                if char['name'] and char['name'].lower() in v_input.lower():
                    detected_physique.append(f"{char['name']} ({char['desc']})")
            char_ref = "Appearance: " + ", ".join(detected_physique) + ". " if detected_physique else ""
            
            # PROMPT GAMBAR
            final_img = (
                f"buatkan saya sebuah gambar adegan ke {i}. portrait 1080x1920. "
                f"ketajaman menyeluruh pada karakter dan seluruh latar belakang. "
                f"{expression_instruction} Visual: {char_ref}{v_input}. "
                f"Time: {eng_time}. {img_quality}"
            )

            # PROMPT VIDEO
            dialog_block_vid = f"\n\nDialog:\n{dialog_text}" if dialog_text else ""
            final_vid = (
                f"Generate video for Scene {i}, 9:16 vertical full-screen. "
                f"Sharp background, deep focus, smooth motion. "
                f"{expression_instruction} Visual: {char_ref}{v_input}. "
                f"Time: {eng_time}. {vid_quality}{dialog_block_vid}"
            )

            st.subheader(f"Adegan {i}")
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.caption("📸 PROMPT GAMBAR (Sharp Foreground & Background)")
                st.code(final_img, language="text")
            with res_col2:
                st.caption("🎥 PROMPT VIDEO (Full Detail Video)")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA v5.0 - Full Sharpness Mode")
