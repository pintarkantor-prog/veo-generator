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
st.info("Mode: Warna Tajam & Cahaya Lembut (Cinematic) ❤️")

# --- 3. SIDEBAR: KONFIGURASI TOKOH ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas Tokoh")
    characters = []
    st.markdown("**Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="UDIN")
    c1_desc = st.text_area("Fisik 1", key="char_desc_0", placeholder="Contoh: Pria kepala jeruk, jaket denim...", height=68)
    characters.append({"name": c1_name, "desc": c1_desc})
    
    st.divider()
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="TUNG")
    c2_desc = st.text_area("Fisik 2", key="char_desc_1", placeholder="Contoh: Manusia kayu, mata biru...", height=68)
    characters.append({"name": c2_name, "desc": c2_desc})

# --- 4. PARAMETER KUALITAS (CINEMATIC SOFT LIGHT & SHARP TEXTURE) ---
# Fokus pada tekstur mikro dan pencahayaan alami (diffused)
img_quality = (
    "full body vertical portrait, 1080x1920 pixels, 9:16 aspect ratio, edge-to-edge frame, "
    "diffused natural light, cinematic soft shadows, high dynamic range, sharp micro-textures, "
    "hyper-realistic skin and material details, ultra-detailed 8k resolution, organic color tones, "
    "deep contrast without over-exposure, captured on 35mm lens, f/4.0 aperture for realistic depth, "
    "STRICTLY NO speech bubbles, NO text on image, NO watermarks, NO cartoon"
)

vid_quality = (
    "veo 3 high-quality cinematic video, 9:16 vertical 1080p, 60fps, "
    "soft natural diffused lighting, realistic shadows, sharp texture details, "
    "cinematic color grading, authentic fluid movements, NO motion blur, NO animation"
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
            # Memberikan pilihan suasana cahaya yang tidak menyilaukan
            scene_time = st.selectbox(f"Suasana Cahaya {i}", 
                                     ["Cahaya Pagi Lembut", "Siang Berawan (Soft)", "Sore Emas (Mellow)", "Malam Sunyi"], 
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
        st.header("📋 Hasil Prompt (Cinematic Mode)")
        
        # Mapping suasana cahaya ke instruksi teknis yang lebih 'adem'
        time_map = {
            "Cahaya Pagi Lembut": "soft diffused morning sunlight, cinematic natural tones, gentle light",
            "Siang Berawan (Soft)": "overcast midday lighting, soft shadows, realistic colors, no harsh glare, diffused sky",
            "Sore Emas (Mellow)": "mellow golden hour, soft warm backlight, gentle contrast, cinematic glow",
            "Malam Sunyi": "dim ambient night light, soft moonlit shadows, realistic dark tones, subtle illumination"
        }

        for scene in filled_scenes:
            i = scene["num"]
            v_input = scene["desc"]
            eng_time = time_map.get(scene["time"])
            
            # Pengolahan Dialog untuk Analisa Emosi
            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            dialog_text = " ".join(dialog_lines) if dialog_lines else ""
            
            expression_instruction = (
                f"Emotion Analysis: Analyze mood from '{dialog_text}'. "
                "Render realistic facial micro-expressions with natural skin texture and facial tension. "
                "Do NOT include any speech bubbles, NO text, NO subtitles."
            )
            
            # Deteksi Karakter dalam Visual
            detected_physique = []
            for char in characters:
                if char['name'] and char['name'].lower() in v_input.lower():
                    detected_physique.append(f"{char['name']} ({char['desc']})")
            char_ref = "Appearance: " + ", ".join(detected_physique) + ". " if detected_physique else ""
            
            # PROMPT GAMBAR (Bananan)
            final_img = (
                f"buatkan saya sebuah gambar adegan ke {i}. portrait 1080x1920. "
                f"fokus pada ketajaman tekstur dan cahaya alami. "
                f"{expression_instruction} Visual: {char_ref}{v_input}. "
                f"Lighting: {eng_time}. {img_quality}"
            )

            # PROMPT VIDEO (Veo 3)
            dialog_block_vid = f"\n\nDialog:\n{dialog_text}" if dialog_text else ""
            final_vid = (
                f"Generate cinematic video for Scene {i}, 9:16 vertical full-screen. "
                f"Smooth motion, sharp action, realistic lighting. "
                f"{expression_instruction} Visual: {char_ref}{v_input}. "
                f"Lighting: {eng_time}. {vid_quality}{dialog_block_vid}"
            )

            st.subheader(f"Adegan {i}")
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.caption("📸 PROMPT GAMBAR (Bananan Optimized)")
                st.code(final_img, language="text")
            with res_col2:
                st.caption("🎥 PROMPT VIDEO (Veo 3 Optimized)")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA v4.7 - Soft Lighting Edition")
