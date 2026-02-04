import streamlit as st

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MANUAL SETUP - MEGA STRUCTURE)
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. CUSTOM CSS (FULL EXPLICIT STYLE - NO REDUCTION)
# ==============================================================================
st.markdown("""
    <style>
    /* Latar Belakang Sidebar Gelap Profesional */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    
    /* Warna Teks Sidebar Putih Terang */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }

    /* Tombol Copy Hijau Terang Ikonik */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 2px solid #ffffff !important;
        transform: scale(1.1); 
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    
    button[title="Copy to clipboard"]:hover {
        background-color: #218838 !important;
    }
    
    /* Font Area Input Visual Deskripsi */
    .stTextArea textarea {
        font-size: 14px !important;
        line-height: 1.5 !important;
        font-family: 'Inter', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.22 | THE REAL MEGA STRUCTURE | CHARACTER EXPANSION | NO REDUCTION ❤️")

# ==============================================================================
# 3. SIDEBAR: KONFIGURASI UTAMA & DIRECTOR SETTINGS
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🎬 Director's Style Lock")
    tone_style = st.selectbox("Pilih Visual Tone Keseluruhan", 
                             ["None", "Gritty Cinematic", "Vibrant Pop", "High-End Documentary", "Vintage Film 35mm", "Dark Thriller", "Surreal Dreamy"])
    
    st.divider()
    st.subheader("☁️ Cuaca Global (Auto-Apply)")
    global_weather = st.selectbox("Set Cuaca untuk Semua Adegan", 
                                  ["Manual per Adegan", "Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"])

    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    all_characters = []
    
    # Karakter 1 (Default: UDIN)
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Karakter 1", key="c_name_1_input", value="UDIN")
    c1_phys = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", placeholder="Detail fisik...", height=80)
    all_characters.append({"name": c1_name, "phys": c1_phys})
    
    st.divider()
    
    # Karakter 2 (Default: TUNG)
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Karakter 2", key="c_name_2_input", value="TUNG")
    c2_phys = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", placeholder="Detail fisik...", height=80)
    all_characters.append({"name": c2_name, "phys": c2_phys})

    # FITUR EKSPANSI MANUAL (Sesuai Permintaan)
    st.divider()
    extra_chars = st.number_input("Tambah Karakter Tambahan?", min_value=0, max_value=10, value=0)
    if extra_chars > 0:
        for i in range(extra_chars):
            st.markdown(f"### Karakter Tambahan {i+1}")
            ex_n = st.text_input(f"Nama Karakter Tambahan {i+1}", key=f"ex_n_{i}")
            ex_f = st.text_area(f"Fisik Karakter Tambahan {i+1}", key=f"ex_f_{i}", height=80)
            all_characters.append({"name": ex_n, "phys": ex_f})

# ==============================================================================
# 4. PARAMETER KUALITAS (FULL VERSION - NO REDUCTION)
# ==============================================================================
no_text_no_rain_lock = (
    "STRICTLY NO rain, NO puddles, NO raindrops, NO wet ground, NO water droplets, "
    "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters."
)

img_quality_base = (
    "photorealistic surrealism style, 16-bit color bit depth, hyper-saturated organic pigments, "
    "absolute fidelity to unique character reference, edge-to-edge optical sharpness, "
    "f/11 deep focus aperture, micro-contrast enhancement, intricate micro-textures on every surface, "
    "circular polarizer (CPL) filter effect, zero atmospheric haze, "
    "rich high-contrast shadows, unprocessed raw photography, 8k resolution, captured on high-end 35mm lens, "
    "STRICTLY NO over-exposure, NO motion blur, NO lens flare, " + no_text_no_rain_lock
)

# ==============================================================================
# 5. FORM INPUT ADEGAN (REACTIVE SYNC LOGIC)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {idx_s}", expanded=(idx_s == 1)):
        cols_setup = st.columns([5, 2])
        
        with cols_setup[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=150)
        
        with cols_setup[1]:
            if global_weather != "Manual per Adegan":
                current_default = options_lighting.index(global_weather)
                radio_key = f"light_{idx_s}_{global_weather}" 
            else:
                current_default = 0
                radio_key = f"light_{idx_s}_manual"

            light_radio = st.radio(f"Pencahayaan {idx_s}", options_lighting, index=current_default, key=radio_key)
        
        # Dialog dinamis untuk semua karakter yang aktif
        st.markdown("**Dialog Karakter**")
        dialog_data = {}
        char_cols = st.columns(len(all_characters))
        for i, char in enumerate(all_characters):
            with char_cols[i]:
                d_val = st.text_input(f"Dialog {char['name']}", key=f"diag_{i}_{idx_s}")
                dialog_data[char['name']] = d_val
        
        adegan_storage.append({"num": idx_s, "visual": vis_in, "lighting": light_radio, "dialogs": dialog_data})

st.divider()

# ==============================================================================
# 6. LOGIKA GENERATOR PROMPT (ABSOLUTE FULL EXPLICIT - NO REDUCTION)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        for adegan in active_adegan:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["lighting"]
            
            # --- FULL MAPPING LOGIKA LIGHTING (KEMBALI KE MEGA STRUCTURE) ---
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
                f_atmos = "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on foliage, wood grain, grass blades, house walls, concrete roads, and every environment object."
            elif l_type == "Suasana Malam":
                f_light = "Hyper-Chrome Fidelity lighting, ultra-intense HMI studio lamp illumination, extreme micro-shadows on all textures, brutal contrast ratio, specular highlight glints on every edge, zero-black floor depth."
                f_atmos = "Pure vacuum-like atmosphere, zero light scattering, absolute visual bite, chrome-saturated pigments, hyper-defined micro-pores and wood grain textures, 10000k ultra-cold industrial white light."
            elif l_type == "Suasana Alami":
                f_light = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments, deep rich micro-shadows within foliage and soil textures."
                f_atmos = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures on every grass blade and soil particle, high-fidelity natural contrast across the entire frame."
            else:
                f_light, f_atmos = "", ""
            
            # --- TONE STYLE LOCK ---
            style_lock = f"Overall Visual Tone: {tone_style}. " if tone_style != "None" else ""
            
            # --- AUTO-SYNC FISIK & EMOTION SEMUA KARAKTER ---
            char_refs = []
            for char in all_characters:
                if char['name'] and char['name'].lower() in v_txt.lower():
                    diag = adegan['dialogs'].get(char['name'], "")
                    emotion_logic = f"Expression Context: Reacting to dialogue context: '{diag}'. Focus on high-fidelity facial expressions. " if diag else ""
                    char_refs.append(f"STRICT CHARACTER APPEARANCE: {char['name']} ({char['phys']}). {emotion_logic}")
            
            final_phys_ref = " ".join(char_refs) + " "

            # --- KONSTRUKSI PROMPT FINAL (KALIMAT SAKTI UTUH) ---
            is_first_pre = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""
            img_cmd_pre = f"buatkan saya sebuah gambar dari adegan ke {s_id}. "

            final_img = (f"{style_lock}{is_first_pre}{img_cmd_pre}{final_phys_ref}Visual Scene: {v_txt}. Atmosphere: {f_atmos} Lighting: {f_light}. {img_quality_base}")

            # --- DISPLAY ---
            st.subheader(f"ADENGAN {s_id}")
            st.code(final_img, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.22 - Absolute Mega Structure Edition")
