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
st.info("Mode: v9.24 | BASE v9.22 | EMOTIONAL CONDITION | NO REDUCTION ❤️")

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
    st.subheader("☁️ Pencahayaan Global (Auto-Apply)")
    global_weather = st.selectbox("Set Pencahayaan untuk Semua Adegan", 
                                  ["Manual per Adegan", "Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"])

    st.divider()
    st.subheader("👥 Identitas & Detail Fisik Karakter")
    
    # Karakter 1 (Default: UDIN)
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Karakter 1", key="c_name_1_input", value="UDIN")
    c1_phys = st.text_area("Detail Fisik 1", key="c_desc_1_input", placeholder="Contoh: Kepala jeruk orange berpori, badan kekar...", height=80)
    
    st.divider()
    
    # Karakter 2 (Default: TUNG)
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Karakter 2", key="c_name_2_input", value="TUNG")
    c2_phys = st.text_area("Detail Fisik 2", key="c_desc_2_input", placeholder="Contoh: Kepala kayu balok, serat kayu kasar...", height=80)

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
# 5. FORM INPUT ADEGAN (REACTIVE SYNC LOGIC)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
options_cond = ["Normal/Bersih", "Sedih/Patah Hati", "Lusuh/Miskin", "Marah/Tegang", "Terluka/Lecet", "Kotor/Berdebu", "Hancur Parah"]

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {idx_s}", expanded=(idx_s == 1)):
        # Baris Utama: Visual & Pencahayaan
        row1_c1, row1_c2 = st.columns([5, 2])
        with row1_c1:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=150)
        with row1_c2:
            if global_weather != "Manual per Adegan":
                current_default = options_lighting.index(global_weather)
                radio_key = f"light_{idx_s}_{global_weather}" 
            else:
                current_default = 0
                radio_key = f"light_{idx_s}_manual"
            light_radio = st.radio(f"Pencahayaan Adegan {idx_s}", options_lighting, index=current_default, key=radio_key)

        st.divider()

        # Baris Sekunder: Kondisi & Dialog
        cols_setup = st.columns([1, 1, 1, 1])
        
        # Karakter 1
        with cols_setup[0]:
            label_c1 = c1_name if c1_name else "Karakter 1"
            cond_c1 = st.selectbox(f"Kondisi {label_c1}", options_cond, key=f"cond_1_{idx_s}")
        with cols_setup[1]:
            diag_c1 = st.text_input(f"Dialog {label_c1}", key=f"diag_1_{idx_s}")
            
        # Karakter 2
        with cols_setup[2]:
            label_c2 = c2_name if c2_name else "Karakter 2"
            cond_c2 = st.selectbox(f"Kondisi {label_c2}", options_cond, key=f"cond_2_{idx_s}")
        with cols_setup[3]:
            diag_c2 = st.text_input(f"Dialog {label_c2}", key=f"diag_2_{idx_s}")
        
        adegan_storage.append({
            "num": idx_s, 
            "visual": vis_in, 
            "lighting": light_radio, 
            "c1": {"cond": cond_c1, "diag": diag_c1},
            "c2": {"cond": cond_c2, "diag": diag_c2}
        })

st.divider()

# ==============================================================================
# 6. LOGIKA GENERATOR PROMPT (ABSOLUTE FULL EXPLICIT)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        for adegan in active_adegan:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["lighting"]
            
            # --- FULL MAPPING LOGIKA LIGHTING ---
            if l_type == "Bening dan Tajam":
                f_light, f_atmos = "Ultra-high altitude light visibility, extreme micro-contrast.", "10:00 AM mountain altitude sun, deepest cobalt blue sky."
            elif l_type == "Sejuk dan Terang":
                f_light, f_atmos = "8000k ice-cold color temperature, zenith sun position.", "12:00 PM glacier-clear atmosphere, crisp cold light."
            elif l_type == "Dramatis":
                f_light, f_atmos = "Hard directional side-lighting, pitch-black sharp shadows.", "Late morning sun, dramatic light rays."
            elif l_type == "Jelas dan Solid":
                f_light, f_atmos = "Deeply saturated matte pigments, circular polarizer effect.", "Early morning atmosphere, hyper-saturated foliage colors."
            elif l_type == "Suasana Sore":
                f_light, f_atmos = "4:00 PM indigo atmosphere, sharp rim lighting.", "Late afternoon cold sun, indigo-cobalt sky gradient."
            elif l_type == "Mendung":
                f_light = "Intense moody overcast lighting with 16-bit color depth fidelity, vivid pigment recovery, extreme local micro-contrast."
                f_atmos = "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, gray-cobalt sky."
            elif l_type == "Suasana Malam":
                f_light = "Hyper-Chrome Fidelity lighting, ultra-intense HMI studio lamp illumination, extreme micro-shadows."
                f_atmos = "Pure vacuum-like atmosphere, absolute visual bite, chrome-saturated pigments."
            elif l_type == "Suasana Alami":
                f_light = "Low-exposure natural sunlight, high local contrast amplification.", "Crystal clear forest humidity, hyper-defined micro-pores."
            else: f_light, f_atmos = "", ""
            
            # --- MAPPING KONDISI EMOSIONAL/SOSIAL ---
            status_map = {
                "Normal/Bersih": "pristine look, calm neutral expression.",
                "Sedih/Patah Hati": "tearful eyes, devastating sorrow expression, messy unkempt hair, emotional distress.",
                "Lusuh/Miskin": "impoverished look, dusty worn-out skin, weary face, unkempt appearance.",
                "Marah/Tegang": "furious expression, intense eyes, tensed facial muscles, aggressive posture.",
                "Terluka/Lecet": "visible scratches and bruises, pained look, skin abrasions.",
                "Kotor/Berdebu": "covered in thick grime and dirt, sweating.",
                "Hancur Parah": "heavily damaged surface, physical cracks, defeated posture."
            }
            
            style_lock = f"Overall Visual Tone: {tone_style}. " if tone_style != "None" else ""
            
            # --- AUTO-SYNC FISIK & KONDISI TOKOH ---
            detected_phys_list = []
            # Karakter 1
            if c1_name and c1_name.lower() in v_txt.lower():
                e1 = f"Expression reacting to saying: '{adegan['c1']['diag']}'. " if adegan['c1']['diag'] else ""
                detected_phys_list.append(f"STRICT CHARACTER APPEARANCE: {c1_name} ({c1_phys}), status: {status_map[adegan['c1']['cond']]}. {e1}")
            # Karakter 2
            if c2_name and c2_name.lower() in v_txt.lower():
                e2 = f"Expression reacting to saying: '{adegan['c2']['diag']}'. " if adegan['c2']['diag'] else ""
                detected_phys_list.append(f"STRICT CHARACTER APPEARANCE: {c2_name} ({c2_phys}), status: {status_map[adegan['c2']['cond']]}. {e2}")
            
            final_phys_ref = " ".join(detected_phys_list) + " "

            # --- KONSTRUKSI PROMPT FINAL ---
            is_first_pre = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""
            img_cmd_pre = f"buatkan saya sebuah gambar dari adegan ke {s_id}. "

            final_img = (f"{style_lock}{is_first_pre}{img_cmd_pre}{final_phys_ref}Visual Scene: {v_txt}. Atmosphere: {f_atmos} Lighting: {f_light}. {img_quality_base}")
            final_vid = (f"{style_lock}Video Adegan {s_id}. {final_phys_ref}Visual Scene: {v_txt}. Atmosphere: {f_atmos}. Lighting: {f_light}. {vid_quality_base}")

            # --- DISPLAY ---
            st.subheader(f"ADENGAN {s_id}")
            st.code(final_img, language="text")
            st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.24 - Emotional Condition Edition")
