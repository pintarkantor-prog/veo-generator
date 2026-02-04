import streamlit as st

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. CUSTOM CSS
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
st.info("Mode: v9.47 | ULTRA-STRICT FIDELITY | REAL-TIME SYNC | VEO 3 ❤️")

# ==============================================================================
# 3. LOGIKA MASTER-SYNC (SESSION STATE)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

if 'master_light_val' not in st.session_state:
    st.session_state.master_light_val = options_lighting[0]

def on_master_light_change():
    new_light = st.session_state.l_1
    st.session_state.master_light_val = new_light
    for i in range(2, 51):
        if f"l_{i}" in st.session_state: # Pastikan key ada sebelum update
            st.session_state[f"l_{i}"] = new_light

# ==============================================================================
# 4. LOGIKA AUTO-DETECTION ENGINE (Disematkan ke pakaian/wujud)
# ==============================================================================
def detect_visual_logic(text):
    text = text.lower()
    emotion = "neutral facial expression, maintaining original character's base mesh."
    if any(w in text for w in ["sedih", "menangis", "sad", "crying"]):
        emotion = "visibly weeping, realistic tear streaks on surface texture, sorrowful face without altering original character geometry."
    elif any(w in text for w in ["marah", "teriak", "geram", "angry", "furious"]):
        emotion = "aggressive furious expression, intense facial muscles, maintaining character's base mesh."
    
    condition = "maintaining 100% original high-resolution textures from reference images."
    if any(w in text for w in ["luka", "berdarah", "injured"]):
        condition = "adding surface scratches and scuff marks while preserving original texture mapping and character geometry."
    elif any(w in text for w in ["hancur", "retak", "pecah", "broken", "cracked"]):
        condition = "hyper-detailed deep physical cracks, maintaining original texture mapping and character geometry without deviation."
    
    return f"State: {condition} Expression: {emotion}"

# ==============================================================================
# 5. SIDEBAR: IDENTITAS KARAKTER (SIMPLIFIED & STRICT)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Karakter (STRICT APPEARANCE)")
    all_characters = []
    for i in range(1, 3):
        st.markdown(f"### Karakter {i}")
        c_n = st.text_input(f"Nama Karakter {i}", value="", key=f"c_n_{i}")
        # HANYA C_W (Pakaian) yang akan menjadi fokus deskripsi karakter
        c_w = st.text_area(f"Wujud & Pakaian {i}", placeholder="Misal: 'si kepala jeruk, memakai kaos putih berlogo X, celana jeans, sepatu bot, berkalung emas logo dolar'", height=100, key=f"c_w_{i}")
        all_characters.append({"name": c_n, "wear": c_w})

# ==============================================================================
# 6. PARAMETER KUALITAS (ABSOLUTE FIDELITY CONSTRAINTS)
# ==============================================================================
zero_text = "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO dialogue boxes, NO labels, NO captions."

# Instruksi keras untuk mempertahankan tekstur dan bentuk dasar karakter
img_fidelity_lock = (
    "photorealistic hyper-surrealism, 16-bit color, maintain 100% pixel-perfect fidelity to ALL PROVIDED CHARACTER REFERENCE IMAGES, "
    "DO NOT DEVIATE from original character geometry and texture mapping, "
    "emphasize micro-textures (orange peel pores, wood grain fractures, muscle definition) from reference, "
    "edge-to-edge optical sharpness, f/11 deep focus, 8k resolution, raw photography, " + zero_text
)

veo_fidelity_lock = (
    "cinematic high-fidelity motion video, 60fps, 4k, organic character movement, "
    "ensure 100% temporal consistency with reference image textures and geometry, "
    "zero texture loss or 'boiling' effect during animation, fluid interaction, " + zero_text
)

# ==============================================================================
# 7. FORM INPUT ADEGAN
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

# ADEGAN 1 (MASTER CONTROL)
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
# 8. GENERATOR PROMPT (ULTRA-STRICT FIDELITY LOGIC)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        for adegan in active:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["light"]
            auto_logic_state = detect_visual_logic(v_txt) # Tangkap status dan ekspresi
            
            # Pemetaan pencahayaan
            light_map = {
                "Mendung": "Intense moody overcast lighting, vivid pigment recovery, gray-cobalt sky.",
                "Suasana Malam": "Hyper-Chrome Fidelity lighting, HMI studio illumination, 10000k cold industrial light.",
                "Suasana Sore": "4:00 PM indigo atmosphere, sharp rim lighting, long dramatic shadows."
            }
            final_lighting_atmos = light_map.get(l_type, f"{l_type} lighting, high local contrast.")

            # MEMBANGUN PROMPT KARAKTER DENGAN "STRICT CHARACTER APPEARANCE"
            char_prompts = []
            for char in all_characters:
                if char['name'] and char['name'].lower() in v_txt.lower():
                    # Gabungkan wujud dan pakaian di sini untuk kejelasan identitas karakter
                    char_desc = char['wear'] if char['wear'] else ""
                    char_prompts.append(f"STRICT CHARACTER APPEARANCE: {char['name']} ({char_desc}). {auto_logic_state}.")

            final_char_instruction = " ".join(char_prompts)
            is_ref_intro = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""

            st.subheader(f"ADENGAN {s_id}")
            st.caption(f"🧠 Detected State: {auto_logic_state}")
            
            # --- OUTPUT PROMPT GAMBAR ---
            st.write("**📸 Image Prompt (Fidelity Mode):**")
            st.code(
                f"{is_ref_intro}buatkan gambar adegan {s_id}. "
                f"{final_char_instruction} " # Instruksi karakter di awal
                f"Visual Scene: {v_txt}. "
                f"Atmosphere & Lighting: {final_lighting_atmos}. "
                f"{img_fidelity_lock}"
            )
            
            # --- OUTPUT PROMPT VEO 3 ---
            st.write("**🎥 Veo 3 Prompt (Motion Mode):**")
            st.code(
                f"Video adegan {s_id}. "
                f"{final_char_instruction} " # Instruksi karakter di awal
                f"Visual Scene: {v_txt}, organic cinematic movement. "
                f"Atmosphere & Lighting: {final_lighting_atmos}. "
                f"{veo_fidelity_lock}"
            )
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA v9.47 - Ultra-Strict Edition")
