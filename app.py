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
# 2. CUSTOM CSS (STRICT STYLE - NO REDUCTION)
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
st.info("Mode: v9.36 | COLOSSAL MULTI-CHAR | MASTER-SYNC | NO REDUCTION ❤️")

# ==============================================================================
# 3. SIDEBAR: KONFIGURASI UTAMA & 4 KARAKTER EKSPLISIT
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Total Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🎬 Gaya Visual (Keseluruhan)")
    tone_style = st.selectbox("Pilih Gaya Visual", 
                             ["None", "Sinematik", "Warna Menyala", "Dokumenter", "Film Jadul", "Film Thriller", "Dunia Khayalan"])

    st.divider()
    st.subheader("👥 Pengaturan Karakter (Maksimal 4)")
    
    # Karakter 1
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Tokoh 1", placeholder="Contoh: UDIN", key="s_c1_n")
    c1_base = st.text_area("Fisik Dasar 1", placeholder="Deskripsi wajah/kepala...", height=70, key="s_c1_f")
    c1_outfit = st.text_input("Pakaian 1", placeholder="Baju, celana...", key="s_c1_p")
    
    st.divider()
    # Karakter 2
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Tokoh 2", placeholder="Contoh: TUNG", key="s_c2_n")
    c2_base = st.text_area("Fisik Dasar 2", placeholder="Deskripsi wajah/kepala...", height=70, key="s_c2_f")
    c2_outfit = st.text_input("Pakaian 2", placeholder="Baju, celana...", key="s_c2_p")

    st.divider()
    # Karakter 3
    st.markdown("### Karakter 3")
    c3_name = st.text_input("Nama Tokoh 3", key="s_c3_n")
    c3_base = st.text_area("Fisik Dasar 3", height=70, key="s_c3_f")
    c3_outfit = st.text_input("Pakaian 3", key="s_c3_p")

    st.divider()
    # Karakter 4
    st.markdown("### Karakter 4")
    c4_name = st.text_input("Nama Tokoh 4", key="s_c4_n")
    c4_base = st.text_area("Fisik Dasar 4", height=70, key="s_c4_f")
    c4_outfit = st.text_input("Pakaian 4", key="s_c4_p")

# ==============================================================================
# 4. LOGIKA MASTER-SYNC
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

if 'master_light' not in st.session_state:
    st.session_state.master_light = options_lighting[0]

def update_all_lights():
    if "light_1" in st.session_state:
        new_val = st.session_state["light_1"]
        st.session_state.master_light = new_val
        for i in range(2, 51):
            st.session_state[f"light_{i}"] = new_val

# ==============================================================================
# 5. PARAMETER KUALITAS (FULL VERSION - NO REDUCTION)
# ==============================================================================
no_text_lock = "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters, NO rain, NO water."
img_quality_base = "photorealistic surrealism style, 16-bit color, hyper-saturated organic pigments, 8k, absolute fidelity to character reference, " + no_text_lock
vid_quality_base = "ultra-high-fidelity vertical video, 9:16, 60fps, strict character consistency, fluid organic motion, high contrast, " + no_text_lock

# ==============================================================================
# 6. FORM INPUT ADEGAN (EKSPLISIT 4 TOKOH)
# ==============================================================================
st.subheader("📝 Detail Adegan (Adegan 1 adalah Leader)")
adegan_storage = []
options_condition = ["Normal/Bersih", "Terluka/Lecet", "Kotor/Berdebu", "Hancur Parah"]

for idx_s in range(1, int(num_scenes) + 1):
    is_leader = (idx_s == 1)
    with st.expander(f"KONFIGURASI ADEGAN {idx_s}", expanded=is_leader):
        # Baris Visual & Lighting
        r1_c1, r1_c2 = st.columns([3, 1])
        with r1_c1:
            vis_in = st.text_area(f"Visual Scene {idx_s}", key=f"vis_{idx_s}", height=120)
        with r1_c2:
            if is_leader:
                light_val = st.selectbox("Cuaca/Cahaya", options_lighting, key="light_1", on_change=update_all_lights)
            else:
                if f"light_{idx_s}" not in st.session_state:
                    st.session_state[f"light_{idx_s}"] = st.session_state.master_light
                light_val = st.selectbox(f"Cahaya {idx_s}", options_lighting, key=f"light_{idx_s}")

        st.markdown("---")
        # Baris Kondisi & Dialog Tokoh 1 & 2
        c1c1, c1c2, c2c1, c2c2 = st.columns([1, 1.5, 1, 1.5])
        with c1c1: cond_1 = st.selectbox(f"Kond {c1_name if c1_name else 'T1'}", options_condition, key=f"cond1_{idx_s}")
        with c1c2: diag_1 = st.text_input(f"Dialog {c1_name if c1_name else 'T1'}", key=f"diag1_{idx_s}")
        with c2c1: cond_2 = st.selectbox(f"Kond {c2_name if c2_name else 'T2'}", options_condition, key=f"cond2_{idx_s}")
        with c2c2: diag_2 = st.text_input(f"Dialog {c2_name if c2_name else 'T2'}", key=f"diag2_{idx_s}")

        # Baris Kondisi & Dialog Tokoh 3 & 4
        c3c1, c3c2, c4c1, c4c2 = st.columns([1, 1.5, 1, 1.5])
        with c3c1: cond_3 = st.selectbox(f"Kond {c3_name if c3_name else 'T3'}", options_condition, key=f"cond3_{idx_s}")
        with c3c2: diag_3 = st.text_input(f"Dialog {c3_name if c3_name else 'T3'}", key=f"diag3_{idx_s}")
        with c4c1: cond_4 = st.selectbox(f"Kond {c4_name if c4_name else 'T4'}", options_condition, key=f"cond4_{idx_s}")
        with c4c2: diag_4 = st.text_input(f"Dialog {c4_name if c4_name else 'T4'}", key=f"diag4_{idx_s}")

        adegan_storage.append({
            "num": idx_s, "visual": vis_in, "lighting": light_val,
            "c1": {"cond": cond_1, "diag": diag_1},
            "c2": {"cond": cond_2, "diag": diag_2},
            "c3": {"cond": cond_3, "diag": diag_3},
            "c4": {"cond": cond_4, "diag": diag_4}
        })

st.divider()

# ==============================================================================
# 7. LOGIKA GENERATOR PROMPT (ABSOLUTE FULL EXPLICIT - NO REDUCTION)
# ==============================================================================
if st.button("🚀 GENERATE SEMUA PROMPT", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active:
        st.warning("Mohon isi deskripsi visual adegan.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        for adegan in active:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["lighting"]
            
            # --- STYLE MAPPING ---
            style_map = {"Sinematik": "Gritty Cinematic", "Warna Menyala": "Vibrant Pop", "Dokumenter": "High-End Documentary", "Film Jadul": "Vintage Film 35mm", "Film Thriller": "Dark Thriller", "Dunia Khayalan": "Surreal Dreamy"}
            active_style = style_map.get(tone_style, "")
            style_lock = f"Overall Visual Tone: {active_style}. " if tone_style != "None" else ""

            # --- LIGHTING MAPPING (FULL TEXT UNTOUCHED) ---
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

            # --- CHARACTER LOGIC (EKSPLISIT 4 KALI) ---
            status_map = {"Normal/Bersih": "pristine condition, clean skin.", "Terluka/Lecet": "visible scratches, scuff marks, pained look.", "Kotor/Berdebu": "covered in dust.", "Hancur Parah": "heavily damaged, cracks."}
            char_prompts = []
            
            # C1
            if c1_name and c1_name.lower() in v_txt.lower():
                e1 = f"Expression: reacting to saying '{adegan['c1']['diag']}', intense facial fidelity. " if adegan['c1']['diag'] else ""
                char_prompts.append(f"CHARACTER REF: {c1_base}, wearing {c1_outfit}, status: {status_map[adegan['c1']['cond']]}. {e1}")
            # C2
            if c2_name and c2_name.lower() in v_txt.lower():
                e2 = f"Expression: reacting to saying '{adegan['c2']['diag']}', intense facial fidelity. " if adegan['c2']['diag'] else ""
                char_prompts.append(f"CHARACTER REF: {c2_base}, wearing {c2_outfit}, status: {status_map[adegan['c2']['cond']]}. {e2}")
            # C3
            if c3_name and c3_name.lower() in v_txt.lower():
                e3 = f"Expression: reacting to saying '{adegan['c3']['diag']}', intense facial fidelity. " if adegan['c3']['diag'] else ""
                char_prompts.append(f"CHARACTER REF: {c3_base}, wearing {c3_outfit}, status: {status_map[adegan['c3']['cond']]}. {e3}")
            # C4
            if c4_name and c4_name.lower() in v_txt.lower():
                e4 = f"Expression: reacting to saying '{adegan['c4']['diag']}', intense facial fidelity. " if adegan['c4']['diag'] else ""
                char_prompts.append(f"CHARACTER REF: {c4_base}, wearing {c4_outfit}, status: {status_map[adegan['c4']['cond']]}. {e4}")
            
            final_char = " ".join(char_prompts) + " "
            final_img = f"{style_lock}{final_char}Visual Scene: {v_txt}. Atmosphere: {f_atmos} Lighting: {f_light}. {img_quality_base}"
            final_vid = f"{style_lock}Video Scene: {v_txt}. {final_char}Atmosphere: {f_atmos}. Lighting: {f_light}. {vid_quality_base}"

            st.subheader(f"ADENGAN {s_id}")
            st.code(final_img, language="text")
            st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.36 - Colossal Multi-Character Edition")
