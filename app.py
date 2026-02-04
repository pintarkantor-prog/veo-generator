import streamlit as st

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MEGA ARCHITECTURE)
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. CUSTOM CSS (STRICT PROFESSIONAL STYLE)
# ==============================================================================
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff !important; }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important; color: white !important;
        opacity: 1 !important; border-radius: 6px !important; border: 2px solid #ffffff !important;
        transform: scale(1.1); box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    .stTextArea textarea { font-size: 14px !important; line-height: 1.5 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.47 | CHARACTER DNA FIDELITY | AUTOMATIC MASTER SYNC | VEO 3 ❤️")

# ==============================================================================
# 3. LOGIKA MASTER-SYNC (SESSION STATE)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

if 'master_light_val' not in st.session_state:
    st.session_state.master_light_val = options_lighting[0]

def on_master_light_change():
    # Menangkap perubahan di adegan 1 dan menyebarkannya secara instan ke adegan lain
    new_light = st.session_state.l_1
    st.session_state.master_light_val = new_light
    for i in range(2, 51):
        st.session_state[f"l_{i}"] = new_light

# ==============================================================================
# 4. LOGIKA AUTO-DETECTION: EMOTION CONTEXT
# ==============================================================================
def detect_visual_logic(text):
    text = text.lower()
    # Deteksi emosi untuk panduan ekspresi wajah (bukan untuk render teks)
    if any(w in text for w in ["sedih", "menangis", "sad", "crying"]):
        return "Reacting to sorrowful context: Focus on high-fidelity weeping facial expressions and surface tear streaks."
    elif any(w in text for w in ["marah", "teriak", "geram", "angry", "furious"]):
        return "Reacting to aggressive context: Focus on intense facial muscle tension and aggressive expression."
    return "Neutral high-fidelity facial expression and relaxed muscle tension."

# ==============================================================================
# 5. SIDEBAR: IDENTITAS KARAKTER (DNA MAPPING)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🎬 Visual Tone")
    tone_style = st.selectbox("Pilih Visual Tone", ["None", "Sinematik", "Warna Menyala", "Dokumenter", "Film Jadul", "Film Thriller", "Dunia Khayalan"])

    st.divider()
    st.subheader("👥 Karakter (Ikuti DNA Visual)")
    all_characters = []
    for i in range(1, 3):
        st.markdown(f"### Karakter {i}")
        c_n = st.text_input(f"Nama Karakter {i}", value="", key=f"cn_{i}")
        c_p = st.text_area(f"Detail DNA Fisik {i}", placeholder="Contoh: si kepala jeruk berpori tajam, badan muscular kekar berurat...", height=80, key=f"cp_{i}")
        c_w = st.text_input(f"Pakaian {i}", key=f"cw_{i}")
        all_characters.append({"name": c_n, "phys": c_p, "wear": c_w})

# ==============================================================================
# 6. PARAMETER KUALITAS: ENHANCED CINEMATIC RENDER
# ==============================================================================
# Menghilangkan 'pixel-lock' dan menggantinya dengan peningkatan kualitas render global
quality_boost = (
    "hyper-realistic cinematic render, 8k resolution, Unreal Engine 5 style, masterwork, "
    "deep global illumination, ray-traced reflections, professional color grading, "
    "STRICTLY NO speech bubbles, NO text, NO watermarks, NO dialogue boxes."
)

# ==============================================================================
# 7. FORM INPUT ADEGAN (INVISIBLE SYNC LOGIC)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

# ADEGAN 1 (MASTER)
with st.expander("ADEGAN 1 (LEADER)", expanded=True):
    v_col1, l_col1 = st.columns([3, 1])
    with v_col1:
        v_in1 = st.text_area("Visual Scene 1", key="vis_1", height=150, placeholder="Ceritakan adegan di sini...")
    with l_col1:
        l_val1 = st.radio("Cahaya Dasar", options_lighting, key="l_1", on_change=on_master_light_change)
    adegan_storage.append({"num": 1, "visual": v_in1, "light": l_val1})

# ADEGAN 2 DAN SETERUSNYA
for idx_s in range(2, int(num_scenes) + 1):
    with st.expander(f"ADEGAN {idx_s}", expanded=False):
        v_col, l_col = st.columns([3, 1])
        with v_col:
            v_in = st.text_area(f"Visual Scene {idx_s}", key=f"vis_{idx_s}", height=150)
        with l_col:
            if f"l_{idx_s}" not in st.session_state:
                st.session_state[f"l_{idx_s}"] = st.session_state.master_light_val
            current_light = st.radio(f"Cahaya {idx_s}", options_lighting, key=f"l_{idx_s}")
        adegan_storage.append({"num": idx_s, "visual": v_in, "light": current_light})

# ==============================================================================
# 8. GENERATOR PROMPT (DNA FIDELITY LOGIC)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        for adegan in active:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["light"]
            emotion_logic = detect_visual_logic(v_txt)
            
            # Mapping Lighting
            light_map = {
                "Mendung": "Overcast lighting, moody atmosphere, gray-cobalt sky.",
                "Suasana Malam": "Cinematic night lighting, high contrast, 10000k cold light.",
                "Suasana Sore": "Golden hour lighting, sharp rim lighting, long dramatic shadows."
            }
            f_l = light_map.get(l_type, f"{l_type} lighting, high-fidelity contrast.")

            # Menyusun instruksi karakter: STRICT CHARACTER APPEARANCE
            char_prompts = []
            for char in all_characters:
                if char['name'] and char['name'].lower() in v_txt.lower():
                    # Fokus pada Identitas (DNA) tanpa memaksa kualitas gambar sama dengan referensi
                    char_prompts.append(f"STRICT CHARACTER APPEARANCE: {char['name']} ({char['phys']}, memakai {char['wear']})")

            final_c = ". ".join(char_prompts)
            is_ref = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""

            st.subheader(f"ADENGAN {s_id}")
            
            # --- OUTPUT PROMPT GAMBAR ---
            img_prompt = (
                f"{is_ref}buatkan gambar adegan {s_id}: "
                f"Emotion Context (DO NOT RENDER TEXT): {emotion_logic}. "
                f"{final_c}. "
                f"Visual Scene: {v_txt}. "
                f"Atmosphere: {f_l}. "
                f"{quality_boost}"
            )
            st.write("**📸 Image Prompt (DNA Fidelity):**")
            st.code(img_prompt)
            
            # --- OUTPUT PROMPT VEO 3 ---
            veo_prompt = (
                f"Video adegan {s_id}: {final_c}. "
                f"Visual Scene: {v_txt}, organic cinematic movement. "
                f"Atmosphere: {f_l}. "
                f"{quality_boost}"
            )
            st.write("**🎥 Veo 3 Prompt (Motion Fidelity):**")
            st.code(veo_prompt)
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA v9.47 - DNA Fidelity Edition")
