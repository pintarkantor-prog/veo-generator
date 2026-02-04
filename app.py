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
st.info("Mode: v9.45 | REAL-TIME MASTER SYNC | AUTO-DETECTION | VEO 3 ❤️")

# ==============================================================================
# 3. LOGIKA MASTER-SYNC (SESSION STATE)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

# Inisialisasi memori master jika belum ada
if 'master_light_val' not in st.session_state:
    st.session_state.master_light_val = options_lighting[0]

# Fungsi Pemicu Otomatis untuk Sinkronisasi Cahaya
def on_master_light_change():
    # Mengambil nilai dari radio button Adegan 1 dan menyebarkannya ke memori global
    new_light = st.session_state.l_1
    st.session_state.master_light_val = new_light
    # Memperbarui semua widget cahaya lainnya di session_state secara paksa
    for i in range(2, 51):
        st.session_state[f"l_{i}"] = new_light

# ==============================================================================
# 4. LOGIKA INTERNAL: AUTO-DETECTION ENGINE
# ==============================================================================
def detect_visual_logic(text):
    text = text.lower()
    # Deteksi Emosi & Ekspresi secara otomatis dari teks
    emotion = "neutral facial expression."
    if any(w in text for w in ["sedih", "menangis", "lemas", "sad", "crying"]):
        emotion = "tearful eyes, devastating sorrow facial expression, emotional distress."
    elif any(w in text for w in ["marah", "teriak", "geram", "tegang", "angry", "furious"]):
        emotion = "furious expression, intense facial muscles, aggressive posture."
    
    # Deteksi Kondisi Fisik secara otomatis dari teks
    condition = "pristine condition, clean skin and clothes."
    if any(w in text for w in ["luka", "berdarah", "lecet", "injured", "scuff"]):
        condition = "visible scratches, fresh scuff marks, pained look, raw textures."
    elif any(w in text for w in ["hancur", "retak", "pecah", "broken", "cracked"]):
        condition = "heavily damaged surface, deep physical cracks, extreme texture detail."
    
    return f"Status: {condition} Expression: {emotion}"

# ==============================================================================
# 5. SIDEBAR: PENGATURAN KARAKTER (REFERENSI GAMBAR)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🎬 Visual Tone")
    tone_style = st.selectbox("Pilih Visual Tone", ["None", "Sinematik", "Warna Menyala", "Dokumenter", "Film Jadul", "Film Thriller", "Dunia Khayalan"])

    st.divider()
    st.subheader("👥 Karakter (Ikuti Gambar)")
    all_characters = []
    # Loop untuk membuat input dua karakter utama secara dinamis
    for i in range(1, 3):
        st.markdown(f"### Karakter {i}")
        c_n = st.text_input(f"Nama Karakter {i}", value="", key=f"c_n_{i}")
        c_p = st.text_area(f"Detail Fisik {i}", placeholder="Input detail spesifik dari gambar referensi...", height=80, key=f"c_p_{i}")
        c_w = st.text_input(f"Pakaian {i}", key=f"c_w_{i}")
        all_characters.append({"name": c_n, "phys": c_p, "wear": c_w})

# ==============================================================================
# 6. PARAMETER KUALITAS (STRICT ANTI-TEXT & FIDELITY)
# ==============================================================================
no_text_lock = "STRICTLY NO speech bubbles, NO text, NO letters, NO subtitles, NO captions, NO watermark, NO dialogue boxes."
img_quality = "photorealistic surrealism, 16-bit color, absolute fidelity to reference, 8k, raw photography, " + no_text_lock
veo_quality = "cinematic video, high-fidelity motion, 60fps, 4k, organic character movement, strict consistency, " + no_text_lock

# ==============================================================================
# 7. FORM INPUT ADEGAN (MASTER-SYNC INTERFACE)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

# ADEGAN 1 (BERTINDAK SEBAGAI MASTER CONTROL)
with st.expander("ADEGAN 1 (MASTER CONTROL)", expanded=True):
    v_col1, l_col1 = st.columns([3, 1])
    with v_col1:
        v_in1 = st.text_area("Visual Scene 1", key="vis_1", height=150, placeholder="Ceritakan adegan di sini...")
    with l_col1:
        # Menggunakan on_change untuk memicu fungsi sinkronisasi cahaya ke adegan lain
        l_val1 = st.radio("Cahaya Dasar", options_lighting, key="l_1", on_change=on_master_light_change)
    adegan_storage.append({"num": 1, "visual": v_in1, "light": l_val1})

# ADEGAN 2 DAN SETERUSNYA (OTOMATIS MENGIKUTI ADEGAN 1)
for idx_s in range(2, int(num_scenes) + 1):
    with st.expander(f"ADEGAN {idx_s}", expanded=False):
        v_col, l_col = st.columns([3, 1])
        with v_col:
            v_in = st.text_area(f"Visual Scene {idx_s}", key=f"vis_{idx_s}", height=150)
        with l_col:
            # Mengisi session state adegan ini dengan nilai master jika belum ada entri manual
            if f"l_{idx_s}" not in st.session_state:
                st.session_state[f"l_{idx_s}"] = st.session_state.master_light_val
            
            current_light = st.radio(f"Cahaya {idx_s}", options_lighting, key=f"l_{idx_s}")
        
        adegan_storage.append({"num": idx_s, "visual": v_in, "light": current_light})

# ==============================================================================
# 8. GENERATOR PROMPT (IMAGE & VEO 3)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        for adegan in active:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["light"]
            
            # Mendeteksi emosi dan kondisi fisik berdasarkan teks visual
            auto_logic = detect_visual_logic(v_txt)
            
            # Pemetaan teknis pencahayaan (Mega Structure)
            light_map = {
                "Mendung": "Intense moody overcast lighting, vivid pigment recovery.",
                "Suasana Malam": "Hyper-Chrome Fidelity lighting, HMI studio lamp illumination.",
                "Suasana Sore": "4:00 PM indigo atmosphere, sharp rim lighting."
            }
            f_l = light_map.get(l_type, f"{l_type} lighting, high contrast.")

            # Menyusun instruksi karakter berdasarkan penyebutan nama di visual scene
            char_prompts = []
            for char in all_characters:
                if char['name'] and char['name'].lower() in v_txt.lower():
                    char_prompts.append(f"Follow exact visual of {char['name']} from reference: {char['phys']}, wearing {char['wear']}. {auto_logic}.")

            final_c = " ".join(char_prompts)
            is_ref = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""

            # Menampilkan hasil produksi prompt
            st.subheader(f"ADENGAN {s_id}")
            st.caption(f"🧠 Detected State: {auto_logic}")
            
            st.write("**📸 Image Prompt (DALL-E/Midjourney):**")
            st.code(f"{is_ref}buatkan gambar adegan {s_id}: {final_c} Visual: {v_txt}. Atmosphere: {f_l}. {img_quality}")
            
            st.write("**🎥 Veo 3 Prompt (Video Generation):**")
            st.code(f"Video adegan {s_id}: {final_c} Visual: {v_txt}, organic motion. Atmosphere: {f_l}. {veo_quality}")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA v9.45 - Master-Sync Final")
