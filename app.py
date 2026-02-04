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
    /* Sidebar Styling */
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff !important; }
    
    /* Green Copy Button */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important; color: white !important;
        opacity: 1 !important; border-radius: 6px !important; border: 2px solid #ffffff !important;
        transform: scale(1.1); box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    
    /* Text Area Styling */
    .stTextArea textarea { 
        font-size: 14px !important; 
        line-height: 1.5 !important; 
        font-family: 'Inter', sans-serif !important; 
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.42 | MASTER LIGHTING | AUTO-DETECTION | VEO 3 READY ❤️")

# ==============================================================================
# 3. LOGIKA INTERNAL: AUTO-DETECTION ENGINE
# ==============================================================================
def detect_visual_logic(text):
    text = text.lower()
    # Deteksi Emosi & Ekspresi
    emotion = "neutral facial expression."
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
# 4. SIDEBAR: KONFIGURASI & IDENTITAS KARAKTER
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("💡 Master Lighting Control")
    sync_lighting = st.checkbox("Gunakan Adegan 1 sebagai Master Cahaya", value=True, 
                                help="Jika aktif, semua adegan akan mengikuti pilihan cahaya di Adegan 1 secara otomatis.")
    
    st.divider()
    st.subheader("🎬 Estetika Visual")
    tone_style = st.selectbox("Pilih Visual Tone", 
                             ["None", "Sinematik", "Warna Menyala", "Dokumenter", "Film Jadul", "Film Thriller", "Dunia Khayalan"])

    st.divider()
    st.subheader("👥 Karakter (Ikuti Gambar Referensi)")
    all_characters = []
    for i in range(1, 3):
        st.markdown(f"### Karakter {i}")
        c_n = st.text_input(f"Nama Karakter {i}", value="", key=f"c_n_{i}")
        c_p = st.text_area(f"Detail Fisik {i}", placeholder="Input detail spesifik dari gambar referensi...", height=80, key=f"c_p_{i}")
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
# 6. FORM INPUT ADEGAN (MASTER LIGHTING LOGIC)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

# ADEGAN 1 (MASTER)
with st.expander("ADEGAN 1 (MASTER CONTROL)", expanded=True):
    v_col1, l_col1 = st.columns([3, 1])
    with v_col1:
        v_in1 = st.text_area("Visual Scene 1", key="vis_1", height=150, placeholder="Ceritakan adegan di sini...")
    with l_col1:
        l_val1 = st.radio("Cahaya (Master)", options_lighting, key="l_1")
    adegan_storage.append({"num": 1, "visual": v_in1, "light": l_val1})

# ADEGAN 2 DAN SETERUSNYA
for idx_s in range(2, int(num_scenes) + 1):
    with st.expander(f"ADEGAN {idx_s}", expanded=False):
        v_col, l_col = st.columns([3, 1])
        with v_col:
            v_in = st.text_area(f"Visual Scene {idx_s}", key=f"vis_{idx_s}", height=150)
        with l_col:
            if sync_lighting:
                st.info(f"Mengikuti Master: **{l_val1}**")
                current_light = l_val1
            else:
                current_light = st.radio(f"Cahaya {idx_s}", options_lighting, key=f"l_{idx_s}")
        
        adegan_storage.append({"num": idx_s, "visual": v_in, "light": current_light})

# ==============================================================================
# 7. GENERATOR PROMPT (IMAGE & VEO 3)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        for adegan in active:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["light"]
            
            # --- AUTO-DETECTION ---
            auto_logic = detect_visual_logic(v_txt)

            # --- MEGA STRUCTURE LIGHTING ---
            if l_type == "Mendung":
                f_l, f_a = "Intense moody overcast lighting, vivid pigment recovery.", "Moody atmosphere, gray-cobalt sky."
            elif l_type == "Suasana Malam":
                f_l, f_a = "Hyper-Chrome Fidelity lighting, HMI studio lamp illumination.", "Pure vacuum-like atmosphere, absolute visual bite."
            elif l_type == "Suasana Sore":
                f_l, f_a = "4:00 PM indigo atmosphere, sharp rim lighting.", "Late afternoon cold sun, indigo-cobalt sky gradient."
            else:
                f_l, f_a = f"{l_type} lighting", f"{l_type} atmosphere"

            # --- CHARACTER INSTRUCTION ---
            char_prompts = []
            for char in all_characters:
                if char['name'] and char['name'].lower() in v_txt.lower():
                    char_prompts.append(f"Follow exact visual appearance of {char['name']} from reference: {char['phys']}, wearing {char['wear']}. {auto_logic}.")

            final_c = " ".join(char_prompts)
            style_map = {"Sinematik": "Gritty Cinematic", "Warna Menyala": "Vibrant Pop", "Dokumenter": "High-End Documentary", "Film Jadul": "Vintage Film 35mm", "Film Thriller": "Dark Thriller", "Dunia Khayalan": "Surreal Dreamy"}
            style_lock = f"Visual Tone: {style_map.get(tone_style, '')}. " if tone_style != "None" else ""
            is_ref = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""

            st.subheader(f"ADENGAN {s_id}")
            st.caption(f"🧠 {auto_logic} | 💡 Mode: {'Master Sync' if sync_lighting and s_id > 1 else 'Manual'}")
            
            # OUTPUT
            st.write("**📸 Image Prompt:**")
            st.code(f"{style_lock}{is_ref}buatkan gambar adegan {s_id}: {final_c} Visual: {v_txt}. Atmosphere: {f_a}. Lighting: {f_l}. {img_quality}")
            
            st.write("**🎥 Veo 3 Prompt:**")
            st.code(f"{style_lock}Video adegan {s_id}: {final_c} Visual: {v_txt}, organic motion. Atmosphere: {f_a}. Lighting: {f_l}. {veo_quality}")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA v9.42 - The Final Logic")
