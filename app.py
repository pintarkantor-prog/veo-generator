import streamlit as st

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MEGA STRUCTURE)
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
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 2px solid #ffffff !important;
        transform: scale(1.1); 
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    button[title="Copy to clipboard"]:hover { background-color: #218838 !important; }
    .stTextArea textarea { font-size: 14px !important; line-height: 1.5 !important; font-family: 'Inter', sans-serif !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.29 | MASTER-SYNC LOGIC | REAL-TIME OVERRIDE | NO REDUCTION ❤️")

# ==============================================================================
# 3. SIDEBAR: KONFIGURASI TOKOH & STYLE
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🎬 Director's Style Lock")
    tone_style = st.selectbox("Pilih Visual Tone Keseluruhan", 
                             ["None", "Gritty Cinematic", "Vibrant Pop", "High-End Documentary", "Vintage Film 35mm", "Dark Thriller", "Surreal Dreamy"])

    st.divider()
    st.subheader("👥 Karakter 1 (UDIN)")
    c1_name = st.text_input("Nama Karakter 1", value="UDIN")
    c1_base = st.text_area("Fisik Dasar C1", value="UDIN, character with a realistic orange fruit head, organic peel texture, vivid orange color, humanoid body.", height=70)
    c1_outfit = st.text_input("Pakaian C1", value="white t-shirt, gold necklace")

    st.divider()
    st.subheader("👥 Karakter 2 (TUNG)")
    c2_name = st.text_input("Nama Karakter 2", value="TUNG")
    c2_base = st.text_area("Fisik Dasar C2", value="TUNG, character with a realistic wood log head, natural tree bark texture, humanoid body.", height=70)
    c2_outfit = st.text_input("Pakaian C2", value="blue denim shirt, rustic style")

# ==============================================================================
# 4. LOGIKA MASTER-SYNC (SESSION STATE MANAGEMENT)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

# Inisialisasi State jika belum ada
if 'master_light' not in st.session_state:
    st.session_state.master_light = options_lighting[0]

# Fungsi callback saat Adegan 1 (Leader) berubah
def update_all_lights():
    new_val = st.session_state["light_1"]
    st.session_state.master_light = new_val
    # Paksa semua adegan follower mengikuti Master
    for i in range(2, 51):
        st.session_state[f"light_{i}"] = new_val

# ==============================================================================
# 5. PARAMETER KUALITAS (FULL VERSION)
# ==============================================================================
no_text_lock = "STRICTLY NO rain, NO water, STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters."
img_quality_base = "photorealistic surrealism style, 16-bit color, hyper-saturated organic pigments, 8k, absolute fidelity to character reference, " + no_text_lock
vid_quality_base = "ultra-high-fidelity vertical video, 9:16, 60fps, strict character consistency, fluid motion, " + no_text_lock

# ==============================================================================
# 6. FORM INPUT ADEGAN (MASTER-SYNC INTERFACE)
# ==============================================================================
st.subheader("📝 Detail Adegan (Adegan 1 adalah Leader)")
adegan_storage = []
options_condition = ["Normal/Bersih", "Terluka/Lecet", "Kotor/Berdebu", "Hancur Parah"]

# --- ADEGAN 1 (THE MASTER/LEADER) ---
with st.expander("KONFIGURASI ADEGAN 1 (LEADER)", expanded=True):
    col_l1, col_l2 = st.columns([3, 1])
    with col_l1:
        vis_1 = st.text_area("Visual Scene 1", key="vis_1", height=100)
    with col_l2:
        # Menggunakan on_change untuk memicu sinkronisasi ke bawah
        leader_light = st.radio("Cahaya (Master)", options_lighting, 
                                key="light_1", on_change=update_all_lights)
    
    st.markdown("---")
    l_c1_1, l_c1_2 = st.columns([1, 2])
    with l_c1_1: cond_1_c1 = st.selectbox(f"Kondisi {c1_name}", options_condition, key="cond1_1")
    with l_c1_2: diag_1_c1 = st.text_input(f"Dialog {c1_name}", key="diag1_1")
    
    l_c2_1, l_c2_2 = st.columns([1, 2])
    with l_c2_1: cond_1_c2 = st.selectbox(f"Kondisi {c2_name}", options_condition, key="cond2_1")
    with l_c2_2: diag_1_c2 = st.text_input(f"Dialog {c2_name}", key="diag2_1")

adegan_storage.append({"num": 1, "visual": vis_1, "lighting": leader_light, "cond1": cond_1_c1, "cond2": cond_1_c2, "diag1": diag_1_c1, "diag2": diag_1_c2})

# --- ADEGAN 2 DAN SETERUSNYA (THE FOLLOWERS) ---
for idx_s in range(2, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI ADEGAN {idx_s}", expanded=False):
        f_col1, f_col2 = st.columns([3, 1])
        with f_col1:
            vis_in = st.text_area(f"Visual Scene {idx_s}", key=f"vis_{idx_s}", height=100)
        with f_col2:
            # Inisialisasi nilai follower jika belum ada di session state
            if f"light_{idx_s}" not in st.session_state:
                st.session_state[f"light_{idx_s}"] = st.session_state.master_light
            
            f_light = st.radio(f"Cahaya Adegan {idx_s}", options_lighting, key=f"light_{idx_s}")

        st.markdown("---")
        f_c1_1, f_c1_2 = st.columns([1, 2])
        with f_c1_1: f_cond1 = st.selectbox(f"Kondisi {c1_name}", options_condition, key=f"cond1_{idx_s}")
        with f_c1_2: f_diag1 = st.text_input(f"Dialog {c1_name}", key=f"diag1_{idx_s}")

        f_c2_1, f_c2_2 = st.columns([1, 2])
        with f_c2_1: f_cond2 = st.selectbox(f"Kondisi {c2_name}", options_condition, key=f"cond2_{idx_s}")
        with f_c2_2: f_diag2 = st.text_input(f"Dialog {c2_name}", key=f"diag2_{idx_s}")

        adegan_storage.append({"num": idx_s, "visual": vis_in, "lighting": f_light, "cond1": f_cond1, "cond2": f_cond2, "diag1": f_diag1, "diag2": f_diag2})

st.divider()

# ==============================================================================
# 7. LOGIKA GENERATOR PROMPT (ABSOLUTE FULL EXPLICIT)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active:
        st.warning("Mohon isi deskripsi visual adegan.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        for adegan in active:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["lighting"]
            
            # --- FULL MAPPING LOGIKA LIGHTING (NO REDUCTION) ---
            if l_type == "Bening dan Tajam":
                f_light = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
                f_atmos = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
            elif l_type == "Sejuk dan Terang":
                f_light = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
                f_atmos = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
            elif l_type == "Dramatis":
                f_light = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
                f_atmos = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
            elif l_type == "Jelas dan Solid":
                f_light = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
                f_atmos = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
            elif l_type == "Suasana Sore":
                f_light = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                f_atmos = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background, zero atmospheric haze."
            elif l_type == "Mendung":
                f_light = "Intense moody overcast lighting with 16-bit color depth fidelity, absolute visual bite, vivid pigment recovery on every surface, extreme local micro-contrast, brilliant specular highlights on object edges, deep rich high-definition shadows."
                f_atmos = "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on foliage, wood grain, grass blades, house walls, concrete roads, and every environment object. Bone-dry surfaces, zero moisture, hyper-sharp edge definition across the entire frame."
            elif l_type == "Suasana Malam":
                f_light = "Hyper-Chrome Fidelity lighting, ultra-intense HMI studio lamp illumination, extreme micro-shadows on all textures, brutal contrast ratio, specular highlight glints on every edge, zero-black floor depth."
                f_atmos = "Pure vacuum-like atmosphere, zero light scattering, absolute visual bite, chrome-saturated pigments, hyper-defined micro-pores and wood grain textures, 10000k ultra-cold industrial white light."
            elif l_type == "Suasana Alami":
                f_light = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments, deep rich micro-shadows within foliage and soil textures."
                f_atmos = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures on every grass blade and soil particle, high-fidelity natural contrast across the entire frame, 5000k neutral soft-sun brilliance."
            else: f_light, f_atmos = "", ""

            # --- KONDISI & EMOTION ---
            status_map = {"Normal/Bersih": "pristine condition, clean skin.", "Terluka/Lecet": "visible scratches, scuff marks, pained look.", "Kotor/Berdebu": "covered in dust, messy.", "Hancur Parah": "heavily damaged, cracks, trauma."}
            style_lock = f"Overall Visual Tone: {tone_style}. " if tone_style != "None" else ""
            
            char_prompts = []
            if c1_name and c1_name.lower() in v_txt.lower():
                e1 = f"Expression: reacting to saying '{adegan['diag1']}', intense facial fidelity. " if adegan['diag1'] else ""
                char_prompts.append(f"CHARACTER REF: {c1_base}, wearing {c1_outfit}, status: {status_map[adegan['cond1']]}. {e1}")
            if c2_name and c2_name.lower() in v_txt.lower():
                e2 = f"Expression: reacting to saying '{adegan['diag2']}', intense facial fidelity. " if adegan['diag2'] else ""
                char_prompts.append(f"CHARACTER REF: {c2_base}, wearing {c2_outfit}, status: {status_map[adegan['cond2']]}. {e2}")
            
            final_char = " ".join(char_prompts) + " "
            final_img = f"{style_lock}{final_char}Visual Scene: {v_txt}. Atmosphere: {f_atmos} Lighting: {f_light}. {img_quality_base}"
            final_vid = f"{style_lock}Video Scene: {v_txt}. {final_char}Atmosphere: {f_atmos}. Lighting: {f_light}. {vid_quality_base}"

            st.subheader(f"ADENGAN {s_id}")
            st.code(final_img, language="text")
            st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.29 - Master-Sync Edition")
