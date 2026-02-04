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
    /* Latar Belakang Sidebar Gelap */
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
    
    button[title="Copy to clipboard"]:active {
        background-color: #1e7e34 !important;
        transform: scale(1.0);
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
st.info("Mode: v9.0 | FIXED STABLE | WIDE VISUAL COLUMN | REFERENCE FIDELITY ❤️")

# ==============================================================================
# 3. SIDEBAR: KONFIGURASI TOKOH (EXPLICIT MEGA SETUP)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    characters_data_list = []

    # Karakter 1 (Eksplisit)
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c1_phys = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", placeholder="Detail fisik...", height=80)
    characters_data_list.append({"name": c1_name, "desc": c1_phys})
    
    st.divider()

    # Karakter 2 (Eksplisit)
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c2_phys = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", placeholder="Detail fisik...", height=80)
    characters_data_list.append({"name": c2_name, "desc": c2_phys})

    st.divider()
    
    # Input Karakter Tambahan
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=5, value=2)

    # Manual Loop Karakter Tambahan
    if num_extra > 2:
        for idx_ex in range(2, int(num_extra)):
            st.divider()
            st.markdown(f"### Karakter {idx_ex + 1}")
            ex_n = st.text_input(f"Nama Karakter {idx_ex + 1}", key=f"ex_name_{idx_ex}")
            ex_p = st.text_area(f"Fisik Karakter {idx_ex + 1}", key=f"ex_phys_{idx_ex}", height=80)
            characters_data_list.append({"name": ex_n, "desc": ex_p})

# ==============================================================================
# 4. PARAMETER KUALITAS (ZERO-NATURAL & ZERO-REALISTIC ABSOLUTE)
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
# 5. FORM INPUT ADEGAN (WIDE LAYOUT [5, 2])
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {idx_s}", expanded=(idx_s == 1)):
        
        # Kolom Visual Lebar [5], Kolom Lighting Ramping [2]
        cols_setup = st.columns([5, 2] + [1.2] * len(characters_data_list))
        
        with cols_setup[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=150, placeholder="Tulis deskripsi visual di sini...")
        
        with cols_setup[1]:
            # Pilihan Lighting (Mapping Label Indonesia)
            light_radio = st.radio(f"Pencahayaan", 
                                   [
                                       "Bening dan Tajam", 
                                       "Sejuk dan Terang", 
                                       "Dramatis", 
                                       "Jelas dan Solid", 
                                       "Senja",
                                       "Mendung"
                                   ], 
                                   key=f"light_input_{idx_s}", horizontal=False)
        
        # Penampung Dialog Per Karakter
        scene_dialog_list = []
        for idx_c, char_val in enumerate(characters_data_list):
            with cols_setup[idx_c + 2]:
                char_label = char_val['name'] if char_val['name'] else f"Tokoh {idx_c + 1}"
                diag_in = st.text_input(f"Dialog {char_label}", key=f"diag_input_{idx_c}_{idx_s}")
                scene_dialog_list.append({"name": char_label, "text": diag_in})
        
        adegan_storage.append({
            "num": idx_s, "visual": vis_in, "lighting": light_radio, "dialogs": scene_dialog_list
        })

st.divider()

# ==============================================================================
# 6. LOGIKA GENERATOR PROMPT (MAPPING & FIXING VARIABLES)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        
        for adegan in active_adegan:
            s_id = adegan["num"]
            # Variabel v_txt (Fixed Name)
            v_txt = adegan["visual"]
            
            # --- MAPPING LOGIKA LIGHTING ---
            if "Bening" in adegan["lighting"]:
                f_light = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
                f_atmos = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
            elif "Sejuk" in adegan["lighting"]:
                f_light = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
                f_atmos = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
            elif "Dramatis" in adegan["lighting"]:
                f_light = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
                f_atmos = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
            elif "Jelas" in adegan["lighting"]:
                f_light = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
                f_atmos = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
            elif "Mendung" in adegan["lighting"]:
                f_light = "Intense moody overcast lighting, diffuse soft light with high local contrast, ultra-saturated cool tones, deep blacks, high micro-contrast."
                f_atmos = "Damp-look cold atmosphere, STRICTLY NO rain, gray-cobalt sky, heavy thick wispy clouds, 7500k color temperature, extremely sharp object edges."
            else:
                # Senja
                f_light = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                f_atmos = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background."

            # --- LOGIKA EMOSI DIALOG (FIXED dialogs_combined) ---
            dialogs_combined = [f"{d['name']}: \"{d['text']}\"" for d in adegan['dialogs'] if d['text']]
            full_dialog_str = " ".join(dialogs_combined) if dialogs_combined else ""
            
            emotion_logic = f"Emotion Context (DO NOT RENDER TEXT): Reacting to dialogue context: '{full_dialog_str}'. Focus on high-fidelity facial expressions and muscle tension. " if full_dialog_str else ""

            # --- LOGIKA AUTO-SYNC KARAKTER (FIXED v_txt scan) ---
            detected_phys_list = []
            for c_check in characters_data_list:
                if c_check['name'] and c_check['name'].lower() in v_txt.lower():
                    detected_phys_list.append(f"STRICT CHARACTER APPEARANCE: {c_check['name']} ({c_check['desc']})")
            
            final_phys_ref = " ".join(detected_phys_list) + " " if detected_phys_list else ""

            # --- KONSTRUKSI PROMPT FINAL ---
            is_first_pre = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""
            img_cmd_pre = f"buatkan saya sebuah gambar dari adegan ke {s_id}. "

            final_img = (
                f"{is_first_pre}{img_cmd_pre}{emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: {f_atmos} Dry environment surfaces, no rain, no water. "
                f"Lighting Effect: {f_light}. {img_quality_base}"
            )

            final_vid = (
                f"Video Adegan {s_id}. {emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: {f_atmos} Hyper-vivid colors, sharp focus, dry surfaces. "
                f"Lighting Effect: {f_light}. {vid_quality_base}. Context: {full_dialog_str}"
            )

            # --- DISPLAY OUTPUT ---
            st.subheader(f"ADENGAN {s_id}")
            res_c1, res_c2 = st.columns(2)
            with res_c1:
                st.caption(f"📸 PROMPT GAMBAR ({adegan['lighting']})")
                st.code(final_img, language="text")
            with res_c2:
                st.caption("🎥 PROMPT VIDEO")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.0 - Final Wide Stable")
