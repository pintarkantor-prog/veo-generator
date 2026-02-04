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
st.info("PINTAR MEDIA - Versi 1.2 (Unified & Video) ❤️")

# --- 3. SIDEBAR: KONFIGURASI TOKOH ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas Tokoh")
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

# --- 4. PARAMETER KUALITAS (VERSI 1.2) ---
img_quality = (
    "Ultra-realistic photorealistic cinematic image, professional full-frame DSLR photography, 8K ultra HD, "
    "extreme sharp focus, HDR, high dynamic range, vibrant yet natural colors, rich color contrast, "
    "true-to-life color accuracy, deep blues and vivid greens, bright tropical daylight, natural sunlight, "
    "cinematic lighting with soft realistic shadows, perfectly balanced exposure, no overexposure, "
    "highly detailed textures, hyper-detailed surfaces, realistic skin texture with visible pores, "
    "realistic fabric texture with sharp fibers, clean fine details, micro-details clearly visible, "
    "cinematic composition, eye-level camera angle, subject in perfect focus, subtle shallow depth of field, "
    "clean background separation, professional color grading, crisp clarity, premium photography quality"
)

# Kualitas Video dioptimalkan untuk Veo 3
vid_quality = (
    "Professional 8K video, high-frame rate, cinematic motion, realistic textures, "
    "fluid natural movements, perfectly balanced exposure, crisp details, "
    "professional color grading, no motion blur, premium cinematography"
)

negative_prompt = (
    "cartoon, illustration, anime, CGI, 3D render, low resolution, blur, motion blur, soft focus, "
    "noise, grain, artifacts, color banding, oversharpen, overprocessed, flat lighting, "
    "washed out colors, dull colors, STRICTLY NO speech bubbles, NO text on image"
)

# --- 5. FORM INPUT ADEGAN ---
st.subheader("📝 Detail Adegan")
scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        col_setup = [3] + [1] * len(characters)
        cols = st.columns(col_setup)
        
        with cols[0]:
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"desc_{i}", height=100, placeholder="Deskripsikan visual di sini...")
        
        scene_dialogs = []
        for idx, char in enumerate(characters):
            with cols[idx + 1]:
                char_label = char['name'] if char['name'] else f"Karakter {idx+1}"
                d_input = st.text_input(f"Dialog {char_label}", key=f"diag_{idx}_{i}")
                scene_dialogs.append({"name": char_label, "text": d_input})
        
        scene_data.append({"num": i, "desc": user_desc, "dialogs": scene_dialogs})

st.divider()

# --- 6. TOMBOL GENERATE ---
if st.button("🚀 BUAT PROMPT", type="primary"):
    filled_scenes = [s for s in scene_data if s["desc"].strip() != ""]
    
    if not filled_scenes:
        st.warning("Silakan isi kolom 'Visual Adegan'.")
    else:
        st.header("📋 Hasil Prompt Versi 1.2")
        
        for scene in filled_scenes:
            i = scene["num"]
            v_input = scene["desc"]
            
            # Analisa emosi dari dialog
            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            dialog_text = " ".join(dialog_lines) if dialog_lines else ""
            
            expression_instruction = (
                f"Analyze mood from '{dialog_text}'. Apply realistic facial tension. No text on image. "
            )
            
            detected_physique = []
            for char in characters:
                if char['name'] and char['name'].lower() in v_input.lower():
                    detected_physique.append(f"{char['name']} ({char['desc']})")
            char_ref = "Appearance: " + ", ".join(detected_physique) + ". " if detected_physique else ""
            
            # --- Prompt Gambar Terpadu (Positive + Negative dalam satu kotak) ---
            final_img = (
                f"buatkan saya sebuah gambar adegan ke {i}. "
                f"{expression_instruction} Visual: {char_ref}{v_input}. {img_quality}. "
                f"Negative Prompt: {negative_prompt}"
            )
            
            # --- Prompt Video Terpadu (Positive + Negative dalam satu kotak) ---
            dialog_block_vid = f"\n\nDialog Context:\n{dialog_text}" if dialog_text else ""
            final_vid = (
                f"Generate video for adegan {i}. "
                f"{expression_instruction} Visual: {char_ref}{v_input}. {vid_quality}. {dialog_block_vid}. "
                f"Negative Prompt: {negative_prompt}"
            )

            st.subheader(f"Adegan {i}")
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.caption("📸 PROMPT GAMBAR (Bananan)")
                st.code(final_img, language="text")
            with res_col2:
                st.caption("🎥 PROMPT VIDEO (Veo 3)")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA - v1.2 Unified")
