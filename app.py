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
st.info("Mode: v9.24 | DYNAMIC CHARACTER LOGIC | CONDITION SYNC | NO REDUCTION ❤️")

# ==============================================================================
# 3. SIDEBAR: IDENTITAS DASAR, OUTFIT & DIRECTOR SETTINGS
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Global")
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
    st.subheader("👥 Karakter 1 (UDIN)")
    c1_name = st.text_input("Nama Karakter 1", key="c_name_1_input", value="UDIN")
    c1_base = st.text_area("Identitas Fisik Dasar (Kepala/Wajah)", value="UDIN, character with a realistic orange fruit head, organic peel texture, vivid orange color, humanoid body.", height=70)
    c1_outfit = st.text_input("Pakaian & Aksesoris Saat Ini", value="white t-shirt, gold necklace")

    st.divider()
    st.subheader("👥 Karakter 2 (TUNG)")
    c2_name = st.text_input("Nama Karakter 2", key="c_name_2_input", value="TUNG")
    c2_base = st.text_area("Identitas Fisik Dasar (Kepala/Kayu)", value="TUNG, character with a realistic wood log head, natural tree bark texture, humanoid body.", height=70)
    c2_outfit = st.text_input("Pakaian & Aksesoris Saat Ini ", value="blue denim shirt, rustic style")

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

vid_quality_base = (
    "ultra-high-fidelity vertical video, 9:16, 60fps, photorealistic surrealism, "
    "strict character consistency, deep saturated pigments, "
    "hyper-vivid foliage textures, crystal clear background focus, "
    "extreme visual clarity, lossless texture quality, fluid organic motion, "
    "high contrast ratio, NO animation look, NO CGI look, " + no_text_no_rain_lock
)

# ==============================================================================
# 5. FORM INPUT ADEGAN (DYNAMIC LOGIC)
# ==============================================================================
st.subheader("📝 Detail Adegan & Kondisi Dinamis")
adegan_storage = []
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
options_condition = ["Normal/Bersih", "Terluka/Lecet", "Kotor/Berdebu", "Hancur Parah"]

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {idx_s}", expanded=(idx_s == 1)):
        cols_setup = st.columns([4, 2, 2, 2])
        
        with cols_setup[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=120)
        
        with cols_setup[1]:
            # Reactive Lighting Sync
            if global_weather != "Manual per Adegan":
                current_default = options_lighting.index(global_weather)
                radio_key = f"light_{idx_s}_{global_weather}" 
            else:
                current_default = 0
                radio_key = f"light_{idx_s}_manual"
            light_radio = st.radio(f"Pencahayaan", options_lighting, index=current_default, key=radio_key)
        
        with cols_setup[2]:
            cond_radio = st.radio(f"Kondisi Fisik Tokoh", options_condition, key=f"cond_{idx_s}")
            
        with cols_setup[3]:
            diag_in = st.text_input(f"Dialog (Untuk Emosi)", key=f"diag_{idx_s}")
        
        adegan_storage.append({
            "num": idx_s, "visual": vis_in, "lighting": light_radio, 
            "condition": cond_radio, "dialog": diag_in
        })

st.divider()

# ==============================================================================
# 6. LOGIKA GENERATOR PROMPT (DYNAMIC INJECTION - NO REDUCTION)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        for adegan in active_adegan:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["lighting"]
            
            # --- 1. MAPPING KONDISI FISIK DINAMIS ---
            cond_map = {
                "Normal/Bersih": "pristine condition, clean skin and clothes, perfect texture fidelity.",
                "Terluka/Lecet": "visible scratches, fresh scuff marks on face and body, pained distressed look, raw textures.",
                "Kotor/Berdebu": "covered in dust and grime, muddy stains on clothes, messy organic appearance.",
                "Hancur Parah": "heavily damaged, deep cracks on head surface, torn clothes, extreme physical trauma, broken parts."
            }
            active_status = cond_map[adegan["condition"]]

            # --- 2. FULL MAPPING LOGIKA LIGHTING ---
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
            else:
                f_light = ""
                f_atmos = ""
            
            # --- 3. TONE STYLE & EMOTION SYNC ---
            style_lock = f"Overall Visual Tone: {tone_style}. " if tone_style != "None" else ""
            emotion_logic = f"Expression: reacting to dialog '{adegan['dialog']}', intense high-fidelity facial expressions. " if adegan['dialog'] else ""
            
            # --- 4. AUTO-SYNC FISIK TOKOH DINAMIS ---
            detected_phys_list = []
            if c1_name and c1_name.lower() in v_txt.lower():
                detected_phys_list.append(f"CHARACTER REF: {c1_base}, wearing {c1_outfit}, status: {active_status}")
            if c2_name and c2_name.lower() in v_txt.lower():
                detected_phys_list.append(f"CHARACTER REF: {c2_base}, wearing {c2_outfit}, status: {active_status}")
            final_char_ref = " ".join(detected_phys_list) + " "

            # --- 5. KONSTRUKSI PROMPT FINAL ---
            final_img = (f"{style_lock}{final_char_ref}{emotion_logic}Visual Scene: {v_txt}. Atmosphere: {f_atmos} Lighting: {f_light}. {img_quality_base}")
            final_vid = (f"{style_lock}Video Scene: {v_txt}. {final_char_ref}{emotion_logic}Atmosphere: {f_atmos}. Lighting: {f_light}. {vid_quality_base}")

            # --- DISPLAY ---
            st.subheader(f"ADENGAN {s_id}")
            st.code(final_img, language="text")
            st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.24 - Dynamic & Reactive Edition")
