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

    .small-label {
        font-size: 12px;
        font-weight: bold;
        color: #a1a1a1;
        margin-bottom: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.16 | PONDASI v9.15 | VIDEO CINEMATOGRAPHY SYNC ❤️")

# ==============================================================================
# 3. LOGIKA MASTER SYNC & OPTIONS (EXPLICIT)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
options_camera = ["Static (No Move)", "Slow Zoom In", "Slow Zoom Out", "Pan Left to Right", "Pan Right to Left", "Tilt Up", "Tilt Down", "Tracking Shot", "Orbit Circular"]
options_shot = ["Extreme Close-Up", "Close-Up", "Medium Shot", "Full Body Shot", "Wide Landscape Shot", "Low Angle Shot", "High Angle Shot"]

# Inisialisasi state master
if 'master_l' not in st.session_state: st.session_state.master_l = options_lighting[0]
if 'master_c' not in st.session_state: st.session_state.master_c = options_camera[0]
if 'master_s' not in st.session_state: st.session_state.master_s = options_shot[2]

def global_sync_v916():
    """Fungsi Master Sync untuk semua Dropbox berdasarkan Adegan 1"""
    new_l = st.session_state.light_input_1
    new_c = st.session_state.camera_input_1
    new_s = st.session_state.shot_input_1
    
    st.session_state.master_l = new_l
    st.session_state.master_c = new_c
    st.session_state.master_s = new_s
    
    for key in st.session_state.keys():
        if key.startswith("light_input_"): st.session_state[key] = new_l
        if key.startswith("camera_input_"): st.session_state[key] = new_c
        if key.startswith("shot_input_"): st.session_state[key] = new_s

# ==============================================================================
# 4. SIDEBAR: KONFIGURASI TOKOH (MANUAL EXPLICIT - NO REDUCTION)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    characters_data_list = []

    # Karakter 1 (Manual Entry)
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c1_phys = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", placeholder="Detail fisik...", height=80)
    characters_data_list.append({"name": c1_name, "desc": c1_phys})
    
    st.divider()

    # Karakter 2 (Manual Entry)
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c2_phys = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", placeholder="Detail fisik...", height=80)
    characters_data_list.append({"name": c2_name, "desc": c2_phys})

# ==============================================================================
# 5. PARAMETER KUALITAS (ULTIMATE FIDELITY - RESTORED)
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
# 6. FORM INPUT ADEGAN (DROPBOX MASTER SYNC INTERFACE)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    label_box = f"🟢 MASTER CONTROL - ADEGAN {idx_s}" if idx_s == 1 else f"🎬 ADEGAN {idx_s}"
    with st.expander(label_box, expanded=(idx_s == 1)):
        
        # Grid System: Visual (4), Lighting (1.5), Video Move (1.5), Video Shot (1.5)
        cols_setup = st.columns([4, 1.5, 1.5, 1.5])
        
        with cols_setup[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=150, placeholder="Tulis deskripsi visual di sini...")
        
        with cols_setup[1]:
            st.markdown('<p class="small-label">💡 Lighting</p>', unsafe_allow_html=True)
            if idx_s == 1:
                light_val = st.selectbox("L1", options_lighting, key="light_input_1", on_change=global_sync_v916, label_visibility="collapsed")
            else:
                if f"light_input_{idx_s}" not in st.session_state: st.session_state[f"light_input_{idx_s}"] = st.session_state.master_l
                light_val = st.selectbox(f"L{idx_s}", options_lighting, key=f"light_input_{idx_s}", label_visibility="collapsed")

        with cols_setup[2]:
            st.markdown('<p class="small-label">🎥 Video Move</p>', unsafe_allow_html=True)
            if idx_s == 1:
                cam_val = st.selectbox("C1", options_camera, key="camera_input_1", on_change=global_sync_v916, label_visibility="collapsed")
            else:
                if f"camera_input_{idx_s}" not in st.session_state: st.session_state[f"camera_input_{idx_s}"] = st.session_state.master_c
                cam_val = st.selectbox(f"C{idx_s}", options_camera, key=f"camera_input_{idx_s}", label_visibility="collapsed")

        with cols_setup[3]:
            st.markdown('<p class="small-label">📐 Video Shot</p>', unsafe_allow_html=True)
            if idx_s == 1:
                shot_val = st.selectbox("S1", options_shot, key="shot_input_1", on_change=global_sync_v916, label_visibility="collapsed")
            else:
                if f"shot_input_{idx_s}" not in st.session_state: st.session_state[f"shot_input_{idx_s}"] = st.session_state.master_s
                shot_val = st.selectbox(f"S{idx_s}", options_shot, key=f"shot_input_{idx_s}", label_visibility="collapsed")

        # Dialog Rows (Manual Entry)
        diag_cols = st.columns(len(characters_data_list))
        scene_dialog_list = []
        for idx_c, char_val in enumerate(characters_data_list):
            with diag_cols[idx_c]:
                char_label = char_val['name'] if char_val['name'] else f"Tokoh {idx_c + 1}"
                diag_in = st.text_input(f"Dialog {char_label}", key=f"diag_input_{idx_c}_{idx_s}")
                scene_dialog_list.append({"name": char_label, "text": diag_in})
        
        adegan_storage.append({
            "num": idx_s, "visual": vis_in, "lighting": light_val, "camera": cam_val, "shot": shot_val, "dialogs": scene_dialog_list
        })

st.divider()

# ==============================================================================
# 7. LOGIKA GENERATOR PROMPT (THE ULTIMATE OVERCAST LOGIC - NO REDUCTION)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        
        for adegan in active_adegan:
            s_id = adegan["num"]
            v_txt = adegan["visual"]
            l_choice = adegan["lighting"]
            c_move = adegan["camera"]
            s_size = adegan["shot"]
            
            # --- MAPPING LOGIKA LIGHTING (FULL EXPLICIT RESTORED) ---
            if "Bening" in l_choice:
                f_light = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
                f_atmos = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
            elif "Sejuk" in l_choice:
                f_light = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
                f_atmos = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
            elif "Dramatis" in l_choice:
                f_light = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
                f_atmos = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
            elif "Jelas" in l_choice:
                f_light = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
                f_atmos = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
            elif "Mendung" in l_choice:
                f_light = (
                    "Intense moody overcast lighting with 16-bit color depth fidelity, absolute visual bite, "
                    "vivid pigment recovery on every surface, extreme local micro-contrast, "
                    "brilliant specular highlights on object edges, deep rich high-definition shadows."
                )
                f_atmos = (
                    "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, "
                    "gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on foliage, wood grain, "
                    "grass blades, house walls, concrete roads, and every environment object in frame. "
                    "Bone-dry surfaces, zero moisture, hyper-sharp edge definition across the entire frame."
                )
            elif "Suasana Malam" in l_choice:
                f_light = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim light highlights, 9000k cold moonlit glow, visible background detail."
                f_atmos = "Clear night atmosphere, deep indigo-black sky, hyper-defined textures on every object."
            elif "Suasana Alami" in l_choice:
                f_light = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments."
                f_atmos = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures."
            else: # Suasana Sore
                f_light = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                f_atmos = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background, zero atmospheric haze."

            # --- LOGIKA EMOSI DIALOG ---
            dialogs_combined = [f"{d['name']}: \"{d['text']}\"" for d in adegan['dialogs'] if d['text']]
            full_dialog_str = " ".join(dialogs_combined) if dialogs_combined else ""
            emotion_logic = f"Emotion Context (DO NOT RENDER TEXT): Reacting to dialogue context: '{full_dialog_str}'. Focus on high-fidelity facial expressions. " if full_dialog_str else ""

            # --- LOGIKA AUTO-SYNC KARAKTER ---
            detected_phys_list = []
            for c_check in characters_data_list:
                if c_check['name'] and c_check['name'].lower() in v_txt.lower():
                    detected_phys_list.append(f"STRICT CHARACTER APPEARANCE: {c_check['name']} ({c_check['desc']})")
            
            final_phys_ref = " ".join(detected_phys_list) + " " if detected_phys_list else ""

            # --- KONSTRUKSI PROMPT FINAL ---
            is_first_pre = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""
            img_cmd_pre = f"buatkan saya sebuah gambar dari adegan ke {s_id}. "

            # Prompt Gambar: Murni tanpa instruksi gerak
            final_img = (
                f"{is_first_pre}{img_cmd_pre}{emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: {f_atmos} Dry environment surfaces, no water droplets. "
                f"Lighting Effect: {f_light}. {img_quality_base}"
            )

            # Prompt Video: Disuntikkan Camera Move & Shot Size khusus untuk Veo 3
            final_vid = (
                f"Video Adegan {s_id}. {s_size} perspective. {c_move} motion. {emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: {f_atmos} Hyper-vivid colors, sharp focus, dry surfaces. "
                f"Lighting Effect: {f_light}. {vid_quality_base}. Context: {full_dialog_str}"
            )

            # --- DISPLAY OUTPUT ---
            st.subheader(f"ADENGAN {s_id}")
            res_c1, res_c2 = st.columns(2)
            with res_c1:
                st.caption(f"📸 PROMPT GAMBAR ({l_choice})")
                st.code(final_img, language="text")
            with res_c2:
                st.caption(f"🎥 PROMPT VIDEO ({s_size} + {c_move})")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.16 - Cinematic Video Edition")
