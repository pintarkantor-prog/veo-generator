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
st.info("Mode: v9.27 | GIGANTIC EDITION | INDIVIDUAL DIALOG | NO REDUCTION ❤️")

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
    c1_base = st.text_area("Fisik Dasar C1", value="UDIN, character with a realistic orange fruit head, organic peel texture, vivid orange color, humanoid body.", height=70)
    c1_outfit = st.text_input("Pakaian C1", value="white t-shirt, gold necklace")

    st.divider()
    st.subheader("👥 Karakter 2 (TUNG)")
    c2_name = st.text_input("Nama Karakter 2", key="c_name_2_input", value="TUNG")
    c2_base = st.text_area("Fisik Dasar C2", value="TUNG, character with a realistic wood log head, natural tree bark texture, humanoid body.", height=70)
    c2_outfit = st.text_input("Pakaian C2", value="blue denim shirt, rustic style")

# ==============================================================================
# 4. PARAMETER KUALITAS (FULL VERSION - NO REDUCTION)
# ==============================================================================
no_text_lock = (
    "STRICTLY NO rain, NO puddles, NO raindrops, NO wet ground, NO water droplets, "
    "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters."
)

img_quality_base = (
    "photorealistic surrealism style, 16-bit color bit depth, hyper-saturated organic pigments, "
    "absolute fidelity to unique character reference, edge-to-edge optical sharpness, "
    "f/11 deep focus aperture, micro-contrast enhancement, intricate micro-textures on every surface, "
    "circular polarizer (CPL) filter effect, zero atmospheric haze, "
    "rich high-contrast shadows, unprocessed raw photography, 8k resolution, captured on high-end 35mm lens, "
    "STRICTLY NO over-exposure, NO motion blur, NO lens flare, " + no_text_lock
)

vid_quality_base = (
    "ultra-high-fidelity vertical video, 9:16, 60fps, photorealistic surrealism, "
    "strict character consistency, deep saturated pigments, "
    "hyper-vivid foliage textures, crystal clear background focus, "
    "extreme visual clarity, lossless texture quality, fluid organic motion, "
    "high contrast ratio, NO animation look, NO CGI look, " + no_text_lock
)

# ==============================================================================
# 5. FORM INPUT ADEGAN (INDIVIDUAL CONDITION & DIALOG)
# ==============================================================================
st.subheader("📝 Detail Adegan, Kondisi, & Dialog Terpisah")
adegan_storage = []
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
options_condition = ["Normal/Bersih", "Terluka/Lecet", "Kotor/Berdebu", "Hancur Parah"]

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {idx_s}", expanded=(idx_s == 1)):
        # Baris Pertama: Visual & Lighting
        row1_col1, row1_col2 = st.columns([3, 1])
        with row1_col1:
            vis_in = st.text_area(f"Visual Scene {idx_s}", key=f"vis_{idx_s}", height=100)
        with row1_col2:
            if global_weather != "Manual per Adegan":
                l_idx = options_lighting.index(global_weather)
                l_key = f"light_{idx_s}_{global_weather}"
            else:
                l_idx, l_key = 0, f"light_{idx_s}_manual"
            light_radio = st.radio("Cahaya", options_lighting, index=l_idx, key=l_key)

        # Baris Kedua: Kondisi & Dialog Individual
        st.markdown("---")
        c1_col1, c1_col2 = st.columns([1, 2])
        with c1_col1:
            cond_c1 = st.selectbox(f"Kondisi {c1_name}", options_condition, key=f"cond1_{idx_s}")
        with c1_col2:
            diag_c1 = st.text_input(f"Dialog {c1_name}", key=f"diag1_{idx_s}", placeholder=f"Apa yang dikatakan {c1_name}?")

        c2_col1, c2_col2 = st.columns([1, 2])
        with c2_col1:
            cond_c2 = st.selectbox(f"Kondisi {c2_name}", options_condition, key=f"cond2_{idx_s}")
        with c2_col2:
            diag_c2 = st.text_input(f"Dialog {c2_name}", key=f"diag2_{idx_s}", placeholder=f"Apa yang dikatakan {c2_name}?")

        adegan_storage.append({
            "num": idx_s, "visual": vis_in, "lighting": light_radio, 
            "cond1": cond_c1, "cond2": cond_c2, 
            "diag1": diag_c1, "diag2": diag_c2
        })

st.divider()

# ==============================================================================
# 6. LOGIKA GENERATOR PROMPT (DYNAMIC INDIVIDUAL SYNC - FULL EXPLICIT)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        for adegan in active:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["lighting"]
            
            # --- 1. MAPPING KONDISI INDIVIDUAL ---
            status_map = {
                "Normal/Bersih": "pristine condition, clean skin and clothes, perfect texture fidelity.",
                "Terluka/Lecet": "visible scratches, fresh scuff marks on face and body, pained look, raw textures.",
                "Kotor/Berdebu": "covered in dust and grime, muddy stains on clothes, messy organic appearance.",
                "Hancur Parah": "heavily damaged, deep cracks on surface, torn clothes, extreme physical trauma, broken parts."
            }
            
            # --- 2. FULL MAPPING LOGIKA LIGHTING (RE-VERIFIED FULL TEXT) ---
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
                f_light, f_atmos = "", ""

            # --- 3. AUTO-SYNC FISIK & EMOSI TERPISAH ---
            char_prompts = []
            style_lock = f"Overall Visual Tone: {tone_style}. " if tone_style != "None" else ""

            if c1_name and c1_name.lower() in v_txt.lower():
                e1 = f"Expression: reacting to saying '{adegan['diag1']}', intense facial fidelity. " if adegan['diag1'] else ""
                char_prompts.append(f"CHARACTER REF: {c1_base}, wearing {c1_outfit}, status: {status_map[adegan['cond1']]}. {e1}")
            
            if c2_name and c2_name.lower() in v_txt.lower():
                e2 = f"Expression: reacting to saying '{adegan['diag2']}', intense facial fidelity. " if adegan['diag2'] else ""
                char_prompts.append(f"CHARACTER REF: {c2_base}, wearing {c2_outfit}, status: {status_map[adegan['cond2']]}. {e2}")
            
            final_char_ref = " ".join(char_prompts) + " "

            # --- 4. FINAL ASSEMBLY ---
            final_img = (f"{style_lock}{final_char_ref}Visual Scene: {v_txt}. Atmosphere: {f_atmos} Lighting: {f_light}. {img_quality_base}")
            final_vid = (f"{style_lock}Video Scene: {v_txt}. {final_char_ref}Atmosphere: {f_atmos}. Lighting: {f_light}. {vid_quality_base}")

            st.subheader(f"ADENGAN {adegan['num']}")
            st.code(final_img, language="text")
            st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.27 - Gigantic Recovery Edition")
