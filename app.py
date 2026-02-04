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
st.info("Mode: Dimmed Sunlight & Ultra-Texture ❤️")

# --- 3. SIDEBAR: KONFIGURASI TOKOH ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Tokoh")
    characters = []

    st.markdown("**Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="UDIN")
    c1_desc = st.text_area("Fisik 1", key="char_desc_0", placeholder="Ciri fisik...", height=68)
    characters.append({"name": c1_name, "desc": c1_desc})
    
    st.divider()
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="TUNG")
    c2_desc = st.text_area("Fisik 2", key="char_desc_1", placeholder="Ciri fisik...", height=68)
    characters.append({"name": c2_name, "desc": c2_desc})

    st.divider()
    num_chars = st.number_input("Tambah Karakter Lainnya", min_value=2, max_value=5, value=2)

    if num_chars > 2:
        for j in range(2, int(num_chars)):
            st.divider()
            st.markdown(f"**Karakter {j+1}**")
            cn = st.text_input(f"Nama Karakter {j+1}", key=f"sidebar_char_name_{j}")
            cd = st.text_area(f"Fisik Karakter {j+1}", key=f"sidebar_char_desc_{j}", height=68)
            characters.append({"name": cn, "desc": cd})

# --- 4. PARAMETER KUALITAS (DIMMED & SHARP) ---
# Di sini kita mengatur 'exposure' dan 'intensity' untuk mengurangi silau matahari
img_quality = (
    "full-frame DSLR photography style, 16-bit color depth, intricate micro-textures, "
    "edge-to-edge optical clarity, f/11 aperture for deep focus sharpness, "
    "dimmed sunlight, 50% less sun glare, muted light intensity, soft diffused shadows, "
    "unprocessed raw photography, 8k resolution, captured on 35mm lens, "
    "STRICTLY NO speech bubbles, NO text on image, NO over-exposure"
)

vid_quality = (
    "high-fidelity video, 9:16 vertical, 60fps, sharp background focus, "
    "fluid organic motion, dimmed sunlight atmosphere, muted exposure, "
    "intricate surface details, natural shadows, NO animation, NO motion blur"
)

# --- 5. FORM INPUT ADEGAN ---
st.subheader("📝 Detail Adegan")
scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        col_setup = [2, 1] + [1] * len(characters)
        cols = st.columns(col_setup)
        
        with cols[0]:
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"main_desc_{i}", height=100)
        
        with cols[1]:
            # Setting khusus untuk cahaya matahari yang diredupkan
            scene_time = st.selectbox(f"Suasana {i}", 
                                     ["10:00 AM (Dimmed Sunlight)", "10:00 AM (Deep Shadows)"], 
                                     key=f"time_{i}")
        
        scene_dialogs = []
        for idx, char in enumerate(characters):
            with cols[idx + 2]:
                char_label = char['name'] if char['name'] else f"Karakter {idx+1}"
                d_input = st.text_input(f"Dialog {char_label}", key=f"main_diag_{idx}_{i}")
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
        
        time_map = {
            "10:00 AM (Dimmed Sunlight)": "10:00 AM, 50% sun intensity, cool diffused light, moody atmosphere, no glare",
            "10:00 AM (Deep Shadows)": "10:00 AM, low-key lighting, soft filtered sun, rich shadow depth"
        }

        for scene in filled_scenes:
            i, v_in = scene["num"], scene["desc"]
            eng_time = time_map.get(scene["time"])
            
            ref_prefix = "ini adalah referensi gambar karakter pada adegan per adegan. " if i == 1 else ""
            img_command = f"buatkan saya sebuah gambar dari adegan ke {i}. "

            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            d_text = " ".join(dialog_lines) if dialog_lines else ""
            
            expression_logic = ""
            if d_text:
                expression_logic = (
                    f"Emotion Analight: Analyze 50% less glare, mood from '{d_text}'. "
                    "Apply realistic facial micro-expressions and muscle tension. "
                )

            phys = ", ".join([f"{c['name']} ({c['desc']})" for c in characters if c['name'] and c['name'].lower() in v_in.lower()])
            char_ref = f"Appearance: {phys}. " if phys else ""
            
            final_img = (
                f"{ref_prefix}{img_command}{expression_logic}Visual: {char_ref}{v_in}. "
                f"Lighting: {eng_time}. {img_quality}"
            )

            final_vid = (
                f"Video Adegan {i}. {expression_logic}Visual: {char_ref}{v_in}. "
                f"Lighting: {eng_time}. {vid_quality}. Dialog: {d_text}"
            )

            st.subheader(f"Adegan {i}")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("📸 PROMPT GAMBAR (Dimmed & Sharp)")
                st.code(final_img, language="text")
            with c2:
                st.caption("🎥 PROMPT VIDEO (Dimmed & Sharp)")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v6.0 - Dimmed Light Base")
