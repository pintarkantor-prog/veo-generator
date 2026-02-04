import streamlit as st

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. CUSTOM CSS (SIDEBAR & TOMBOL HIJAU) ---
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
st.info("masih tahap ujicoba dulu ya guys ❤️")

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
    c1_desc = st.text_area("Fisik 1", key="char_desc_0", placeholder="Contoh: Pria kepala jeruk...", height=68)
    characters.append({"name": c1_name, "desc": c1_desc})
    
    st.divider()
    # Karakter 2
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="TUNG")
    c2_desc = st.text_area("Fisik 2", key="char_desc_1", placeholder="Contoh: Manusia kayu...", height=68)
    characters.append({"name": c2_name, "desc": c2_desc})

    st.divider()
    num_chars = st.number_input("Tambah Karakter Lainnya", min_value=2, max_value=5, value=2)

    if num_chars > 2:
        for j in range(2, int(num_chars)):
            st.divider()
            st.markdown(f"**Karakter {j+1}**")
            cn = st.text_input(f"Nama Karakter {j+1}", key=f"char_name_{j}")
            cd = st.text_area(f"Fisik {j+1}", key=f"char_desc_{j}", height=68)
            characters.append({"name": cn, "desc": cd})

# --- 4. PARAMETER KUALITAS (ASPECT RATIO FORCE) ---
# Menaruh instruksi 9:16 di posisi PALING DEPAN untuk memaksa Bananan
img_quality = (
    "ULTRA-PORTRAIT 9:16, 1080x1920 pixels resolution, vertical orientation, "
    "edge-to-edge full screen frame, no black bars, no borders, no padding, "
    "ultra-vivid color saturation, extreme sharpness, hyper-detailed textures, "
    "8k resolution, bold and punchy colors, intense contrast, sharp outlines, "
    "natural sunlight photography, captured on 35mm lens, f/11 aperture, "
    "STRICTLY NO speech bubbles, NO text on image, NO subtitles, NO cartoon"
)

vid_quality = (
    "veo 3 high-quality video, 9:16 vertical full-screen, 1080p, 60fps, "
    "dynamic camera movement, cinematic smooth motion, vivid color grading, "
    "authentic fluid movements, no motion blur artifacts, NO animation"
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
        st.header("📋 Hasil Prompt (v4.5 Aspect Ratio Fixed)")
        
        time_map = {
            "Pagi hari": "vibrant morning sun",
            "Siang hari": "intense bright midday sun, vivid sky",
            "Sore hari": "warm sunset orange glow, high contrast",
            "Malam hari": "ambient night lighting, deep rich blacks"
        }

        for scene in filled_scenes:
            i = scene["num"]
            v_input = scene["desc"]
            eng_time = time_map.get(scene["time"], "natural lighting")
            
            # --- LOGIKA DIALOG (Hidden for Image) ---
            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            dialog_text = " ".join(dialog_lines) if dialog_lines else ""
            
            # Analisa Emosi (Tetap dibaca AI tapi tidak digambar teksnya)
            expression_instruction = (
                f"Emotion Analysis: Analyze the dramatic mood from this dialogue: '{dialog_text}'. "
                "Apply realistic facial expressions, micro-expressions, and eye emotions. "
                "Do NOT include any speech bubbles or text in the image. "
            )
            
            detected_physique = []
            for char in characters:
                if char['name'] and char['name'].lower() in v_input.lower():
                    detected_physique.append(f"{char['name']} ({char['desc']})")
            
            char_ref = "Appearance: " + ", ".join(detected_physique) + ". " if detected_physique else ""
            
            # --- Prompt Gambar (Bananan) ---
            # Fokus 9:16 ditaruh di depan deskripsi visual
            final_img = (
                f"ULTRA-PORTRAIT 1080x1920. buatkan saya adegan ke {i}. "
                f"ini adalah gambar referensi karakter saya. {expression_instruction} "
                f"Visual: {char_ref}{v_input}. Waktu: {scene['time']}. "
                f"Lighting: {eng_time}. {img_quality}"
            )

            # --- Prompt Video (Veo 3) ---
            dialog_block_vid = f"\n\nDialog Context:\n{dialog_text}" if dialog_text else ""
            final_vid = (
                f"Generate 9:16 vertical 1080p 60fps video for Scene {i}. "
                f"{expression_instruction} Visual: {char_ref}{v_input}. "
                f"Lighting: {eng_time}. {vid_quality}{dialog_block_vid}"
            )

            st.subheader(f"Adegan {i}")
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.caption(f"📸 PROMPT GAMBAR (Bananan - Forced 9:16)")
                st.code(final_img, language="text")
            with res_col2:
                st.caption(f"🎥 PROMPT VIDEO (Veo 3)")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA v4.5 - Aspect Ratio Force Mode")
