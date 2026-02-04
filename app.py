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
# 2. CUSTOM CSS (STRICT STYLE - NO REDUCTION)
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
    .stTextArea textarea { font-size: 14px !important; line-height: 1.5 !important; font-family: 'Inter', sans-serif !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.41 | AUTO-DETECTION ENGINE | VEO 3 | CHARACTER FIDELITY ❤️")

# ==============================================================================
# 3. LOGIKA INTERNAL: AUTO-DETECTION ENGINE
# ==============================================================================
def detect_visual_logic(text):
    text = text.lower()
    # Deteksi Emosi & Ekspresi
    emotion = "neutral and calm facial expression."
    if any(w in text for w in ["sedih", "menangis", "lemas", "kecewa", "sad", "crying"]):
        emotion = "tearful eyes, devastating sorrow facial expression, emotional distress."
    elif any(w in text for w in ["marah", "teriak", "geram", "tegang", "angry", "furious"]):
        emotion = "furious expression, intense facial muscles, aggressive posture."
    elif any(w in text for w in ["senang", "tertawa", "bahagia", "happy", "laugh"]):
        emotion = "joyful expression, bright eyes, genuine smile."

    # Deteksi Kondisi Fisik
    condition = "pristine condition, clean skin and clothes."
    if any(w in text for w in ["luka", "berdarah", "lecet", "injured", "scuff"]):
        condition = "visible scratches, fresh scuff marks, pained look, raw textures."
    elif any(w in text for w in ["kotor", "debu", "lumpur", "dirty", "muddy"]):
        condition = "covered in thick grime and dust, messy organic appearance."
    elif any(w in text for w in ["hancur", "retak", "pecah", "broken", "cracked"]):
        condition = "heavily damaged surface, deep physical cracks, torn elements, extreme texture detail."

    return f"Status: {condition} Expression: {emotion}"

# ==============================================================================
# 4. SIDEBAR: IDENTITAS KARAKTER (REFERENSI GAMBAR)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🎬 Estetika Visual")
    tone_style = st.selectbox("Pilih Visual Tone", 
                             ["None", "Sinematik", "Warna Menyala", "Dokumenter", "Film Jadul", "Film Thriller", "Dunia Khayalan"])

    st.divider()
    st.subheader("👥 Karakter Utama")
    all_characters = []
    for i in range(1, 3):
        st.markdown(f"### Karakter {i}")
        c_n = st.text_input(f"Nama Karakter {i}", value="", key=f"c_n_{i}")
        c_p = st.text_area(f"Detail Fisik {i} (Sesuai Gambar)", placeholder="Input detail spesifik...", height=90, key=f"c_p_{i}")
        c_w = st.text_input(f"Pakaian {i}", key=f"c_w_{i}")
        all_characters.append({"name": c_n, "phys": c_p, "wear": c_w})

# ==============================================================================
# 5. PARAMETER KUALITAS (STRICT ANTI-TEXT & FIDELITY)
# ==============================================================================
no_text_lock = (
    "STRICTLY NO speech bubbles, NO text, NO letters, NO subtitles, NO captions, NO watermark, "
    "NO dialogue boxes, NO labels, NO typography. The frame is 100% clean visual content."
)

img_quality = (
    "photorealistic surrealism, 16-bit color, extreme fidelity to provided visual reference, "
    "edge-to-edge optical sharpness, f/11 deep focus, macro-textures, 8k resolution, raw photography, " + no_text_lock
)

veo_quality = (
    "cinematic video, high-fidelity motion, 60fps, 4k, organic character movement, "
    "strict consistency with provided visual reference, fluid interaction, lossless textures, " + no_text_lock
)

# ==============================================================================
# 6. FORM INPUT ADEGAN
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI ADEGAN {idx_s}", expanded=(idx_s == 1)):
        v_col, l_col = st.columns([3, 1])
        with v_col:
            v_in = st.text_area(f"Visual Scene {idx_s}", key=f"vis_{idx_s}", height=150, placeholder="Ceritakan adegannya di sini (Sistem akan mendeteksi emosi secara otomatis)...")
        with l_col:
            l_val = st.radio(f"Cahaya {idx_s}", options_lighting, key=f"l_{idx_s}")
        
        adegan_storage.append({"num": idx_s, "visual": v_in, "light": l_val})

# ==============================================================================
# 7. GENERATOR PROMPT (AUTO-DETECTION LOGIC)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        for adegan in active:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["light"]
            
            # --- AUTO-DETECTION SYSTEM ---
            auto_logic = detect_visual_logic(v_txt)

            # Lighting Mapping (Mega Structure)
            if l_type == "Mendung":
                f_l, f_a = "Intense moody overcast lighting, 16-bit color.", "Moody atmosphere, gray-cobalt sky."
            elif l_type == "Suasana Malam":
                f_l, f_a = "Hyper-Chrome Fidelity lighting, HMI studio lamp illumination.", "Pure vacuum-like atmosphere, absolute visual bite."
            else:
                f_l, f_a = f"{l_type} lighting", f"{l_type} atmosphere"

            # Character Instruction
            char_prompts = []
            for char in all_characters:
                if char['name'] and char['name'].lower() in v_txt.lower():
                    char_prompts.append(f"Follow exact visual appearance of {char['name']} from reference: {char['phys']}, wearing {char['wear']}. {auto_logic}.")

            final_c = " ".join(char_prompts)
            style_map = {"Sinematik": "Gritty Cinematic", "Warna Menyala": "Vibrant Pop", "Dokumenter": "High-End Documentary", "Film Jadul": "Vintage Film 35mm", "Film Thriller": "Dark Thriller", "Dunia Khayalan": "Surreal Dreamy"}
            style_lock = f"Visual Tone: {style_map.get(tone_style, '')}. " if tone_style != "None" else ""
            is_ref = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""

            st.subheader(f"ADENGAN {s_id}")
            st.info(f"🧠 Detected: {auto_logic}")
            
            # OUTPUT PROMPTS
            st.write("**📸 Image Prompt:**")
            st.code(f"{style_lock}{is_ref}buatkan gambar adegan {s_id}: {final_c} Visual Scene: {v_txt}. Atmosphere: {f_a}. Lighting: {f_l}. {img_quality}")
            
            st.write("**🎥 Veo 3 Prompt:**")
            st.code(f"{style_lock}Video adegan {s_id}: {final_c} Visual Scene: {v_txt}, organic cinematic movement. Atmosphere: {f_a}. Lighting: {f_l}. {veo_quality}")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA v9.41 - Auto-Detection Engine")
