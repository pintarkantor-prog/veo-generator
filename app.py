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

    /* Label kecil untuk Dropbox */
    .small-label {
        font-size: 12px;
        font-weight: bold;
        color: #a1a1a1;
        margin-bottom: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.17 | FULL EXPLICIT RESTORATION | UI INDONESIA ❤️")

# ==============================================================================
# 3. MAPPING TRANSLATION (MENU INDONESIA -> LOGIKA INGGRIS)
# ==============================================================================
indonesia_camera = ["Diam (Tanpa Gerak)", "Zoom Masuk Pelan", "Zoom Keluar Pelan", "Geser Kiri ke Kanan", "Geser Kanan ke Kiri", "Dongak ke Atas", "Tunduk ke Bawah", "Ikuti Objek (Tracking)", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat (Detail)", "Dekat (Wajah)", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Sudut Rendah (Gagah)", "Sudut Tinggi (Kecil)"]

camera_map = {
    "Diam (Tanpa Gerak)": "Static (No Move)", 
    "Zoom Masuk Pelan": "Slow Zoom In", 
    "Zoom Keluar Pelan": "Slow Zoom Out",
    "Geser Kiri ke Kanan": "Pan Left to Right", 
    "Geser Kanan ke Kiri": "Pan Right to Left", 
    "Dongak ke Atas": "Tilt Up",
    "Tunduk ke Bawah": "Tilt Down", 
    "Ikuti Objek (Tracking)": "Tracking Shot", 
    "Memutar (Orbit)": "Orbit Circular"
}

shot_map = {
    "Sangat Dekat (Detail)": "Extreme Close-Up", 
    "Dekat (Wajah)": "Close-Up", 
    "Setengah Badan": "Medium Shot",
    "Seluruh Badan": "Full Body Shot", 
    "Pemandangan Luas": "Wide Landscape Shot", 
    "Sudut Rendah (Gagah)": "Low Angle Shot",
    "Sudut Tinggi (Kecil)": "High Angle Shot"
}

# ==============================================================================
# 4. LOGIKA MASTER SYNC & OPTIONS
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

if 'm_light' not in st.session_state: st.session_state.m_light = options_lighting[0]
if 'm_cam' not in st.session_state: st.session_state.m_cam = indonesia_camera[0]
if 'm_shot' not in st.session_state: st.session_state.m_shot = indonesia_shot[2]

def global_sync_v917():
    new_l = st.session_state.light_input_1
    new_c = st.session_state.camera_input_1
    new_s = st.session_state.shot_input_1
    st.session_state.m_light = new_l
    st.session_state.m_cam = new_c
    st.session_state.m_shot = new_s
    for key in st.session_state.keys():
        if key.startswith("light_input_"): st.session_state[key] = new_l
        if key.startswith("camera_input_"): st.session_state[key] = new_c
        if key.startswith("shot_input_"): st.session_state[key] = new_s

# ==============================================================================
# 5. SIDEBAR: KONFIGURASI TOKOH (MANUAL EXPLICIT - NO LOOPING)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    # Karakter 1 (Eksplisit)
    st.markdown("### Karakter 1")
    c_name_1_val = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c_desc_1_val = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", placeholder="Detail fisik...", height=80)
    
    st.divider()

    # Karakter 2 (Eksplisit)
    st.markdown("### Karakter 2")
    c_name_2_val = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c_desc_2_val = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", placeholder="Detail fisik...", height=80)

# ==============================================================================
# 6. PARAMETER KUALITAS (ULTIMATE FIDELITY - RESTORED)
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
# 7. FORM INPUT ADEGAN (MANUAL GRID - NO LOOPING FOR DIALOGS)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    label_box = f"🟢 MASTER CONTROL - ADEGAN {idx_s}" if idx_s == 1 else f"🎬 ADEGAN {idx_s}"
    with st.expander(label_box, expanded=(idx_s == 1)):
        
        cols_setup = st.columns([4, 1.5, 1.5, 1.5])
        
        with cols_setup[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=150)
        
        with cols_setup[1]:
            st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
            if idx_s == 1:
                l_val = st.selectbox("L1", options_lighting, key="light_input_1", on_change=global_sync_v917, label_visibility="collapsed")
            else:
                if f"light_input_{idx_s}" not in st.session_state: st.session_state[f"light_input_{idx_s}"] = st.session_state.m_light
                l_val = st.selectbox(f"L{idx_s}", options_lighting, key=f"light_input_{idx_s}", label_visibility="collapsed")
        
        with cols_setup[2]:
            st.markdown('<p class="small-label">🎥 Gerak Video</p>', unsafe_allow_html=True)
            if idx_s == 1:
                c_val = st.selectbox("C1", indonesia_camera, key="camera_input_1", on_change=global_sync_v917, label_visibility="collapsed")
            else:
                if f"camera_input_{idx_s}" not in st.session_state: st.session_state[f"camera_input_{idx_s}"] = st.session_state.m_cam
                c_val = st.selectbox(f"C{idx_s}", indonesia_camera, key=f"camera_input_{idx_s}", label_visibility="collapsed")

        with cols_setup[3]:
            st.markdown('<p class="small-label">📐 Ukuran Shot</p>', unsafe_allow_html=True)
            if idx_s == 1:
                s_val = st.selectbox("S1", indonesia_shot, key="shot_input_1", on_change=global_sync_v917, label_visibility="collapsed")
            else:
                if f"shot_input_{idx_s}" not in st.session_state: st.session_state[f"shot_input_{idx_s}"] = st.session_state.m_shot
                s_val = st.selectbox(f"S{idx_s}", indonesia_shot, key=f"shot_input_{idx_s}", label_visibility="collapsed")

        # Dialog Manual (Eksplisit Tanpa Looping)
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            diag_1 = st.text_input(f"Dialog {c_name_1_val if c_name_1_val else 'Tokoh 1'}", key=f"diag_1_{idx_s}")
        with d_col2:
            diag_2 = st.text_input(f"Dialog {c_name_2_val if c_name_2_val else 'Tokoh 2'}", key=f"diag_2_{idx_s}")
        
        adegan_storage.append({
            "num": idx_s, 
            "visual": vis_in, 
            "lighting": l_val, 
            "camera": c_val, 
            "shot": s_val, 
            "tokoh1_nama": c_name_1_val, 
            "tokoh1_dialog": diag_1, 
            "tokoh2_nama": c_name_2_val, 
            "tokoh2_dialog": diag_2
        })

st.divider()

# ==============================================================================
# 8. GENERATOR PROMPT (THE ULTIMATE MEGA STRUCTURE - MANUAL EXPLICIT)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        
        for adegan in active_adegan:
            # Mapping manual untuk hasil prompt
            eng_camera_cmd = camera_map.get(adegan["camera"], "Static")
            eng_shot_cmd = shot_map.get(adegan["shot"], "Medium Shot")
            
            s_id = adegan["num"]
            v_txt = adegan["visual"]
            l_sel = adegan["lighting"]
            
            # --- FULL MEGA STRUCTURE LIGHTING LOGIC (RESTORED MANUAL) ---
            if "Bening" in l_sel:
                f_light = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
                f_atmos = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
            elif "Sejuk" in l_sel:
                f_light = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
                f_atmos = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
            elif "Dramatis" in l_sel:
                f_light = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
                f_atmos = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
            elif "Jelas" in l_sel:
                f_light = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
                f_atmos = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
            elif "Mendung" in l_sel:
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
            elif "Suasana Malam" in l_sel:
                f_light = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim light highlights, 9000k cold moonlit glow, visible background detail."
                f_atmos = "Clear night atmosphere, deep indigo-black sky, hyper-defined textures on every object."
            elif "Suasana Alami" in l_sel:
                f_light = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments."
                f_atmos = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures."
            else: # Suasana Sore
                f_light = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                f_atmos = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background, zero atmospheric haze."

            # --- LOGIKA EMOSI DIALOG (EKSPLISIT) ---
            d1_p = f"{adegan['tokoh1_nama']}: \"{adegan['tokoh1_dialog']}\"" if adegan['tokoh1_dialog'] else ""
            d2_p = f"{adegan['tokoh2_nama']}: \"{adegan['tokoh2_dialog']}\"" if adegan['tokoh2_dialog'] else ""
            full_d_str = f"{d1_p} {d2_p}".strip()
            
            emotion_logic = f"Emotion Context (DO NOT RENDER TEXT): Reacting to context: '{full_d_str}'. Focus on high-fidelity facial expressions. " if full_d_str else ""

            # --- LOGIKA AUTO-SYNC KARAKTER (EKSPLISIT) ---
            final_phys_ref = ""
            if adegan['tokoh1_nama'] and adegan['tokoh1_nama'].lower() in v_txt.lower():
                final_phys_ref += f"STRICT CHARACTER APPEARANCE: {adegan['tokoh1_nama']} ({c_desc_1_val}) "
            if adegan['tokoh2_nama'] and adegan['tokoh2_nama'].lower() in v_txt.lower():
                final_phys_ref += f"STRICT CHARACTER APPEARANCE: {adegan['tokoh2_nama']} ({c_desc_2_val}) "

            # --- DISPLAY HASIL AKHIR ---
            st.subheader(f"HASIL PRODUKSI ADEGAN {s_id}")
            
            # PROMPT GAMBAR (TETAP MURNI)
            img_p_cmd = (
                f"ini adalah referensi gambar karakter pada adegan per adegan. buatkan saya sebuah gambar dari adegan ke {s_id}. "
                f"{emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: {f_atmos} Dry environment surfaces, no water droplets. "
                f"Lighting Effect: {f_light}. {img_quality_base}"
            )
            
            # PROMPT VIDEO (SINEMATOGRAFI)
            vid_p_cmd = (
                f"Video Adegan {s_id}. {eng_shot_cmd} perspective. {eng_camera_cmd} movement. "
                f"{emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: {f_atmos} Hyper-vivid colors, sharp focus, dry surfaces. "
                f"Lighting Effect: {f_light}. {vid_quality_base}. Context: {full_d_str}"
            )
            
            res_col_a, res_col_b = st.columns(2)
            with res_col_a:
                st.caption(f"📸 PROMPT GAMBAR ({l_sel})")
                st.code(img_p_cmd, language="text")
            with res_col_b:
                st.caption(f"🎥 PROMPT VIDEO ({eng_shot_cmd} + {eng_camera_cmd})")
                st.code(vid_p_cmd, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.17 - Explicit Restoration Edition")
