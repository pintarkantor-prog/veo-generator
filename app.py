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
st.info("Mode: v9.17 | ULTRA-EXPLICIT RESTORATION | 300+ LINES SYSTEM ❤️")


# ==============================================================================
# 3. MAPPING TRANSLATION (MENU INDONESIA -> LOGIKA INGGRIS)
# ==============================================================================
indonesia_camera = [
    "Diam (Tanpa Gerak)", 
    "Zoom Masuk Pelan", 
    "Zoom Keluar Pelan", 
    "Geser Kiri ke Kanan", 
    "Geser Kanan ke Kiri", 
    "Dongak ke Atas", 
    "Tunduk ke Bawah", 
    "Ikuti Objek (Tracking)", 
    "Memutar (Orbit)"
]

indonesia_shot = [
    "Sangat Dekat (Detail)", 
    "Dekat (Wajah)", 
    "Setengah Badan", 
    "Seluruh Badan", 
    "Pemandangan Luas", 
    "Sudut Rendah (Gagah)", 
    "Sudut Tinggi (Kecil)"
]


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
options_lighting = [
    "Bening dan Tajam", 
    "Sejuk dan Terang", 
    "Dramatis", 
    "Jelas dan Solid", 
    "Suasana Sore", 
    "Mendung", 
    "Suasana Malam", 
    "Suasana Alami"
]


if 'm_light' not in st.session_state:
    st.session_state.m_light = options_lighting[0]

if 'm_cam' not in st.session_state:
    st.session_state.m_cam = indonesia_camera[0]

if 'm_shot' not in st.session_state:
    st.session_state.m_shot = indonesia_shot[2]


def global_sync_v917():
    """Menyamakan seluruh adegan dengan pilihan di Adegan 1"""
    
    new_l = st.session_state.light_input_1
    new_c = st.session_state.camera_input_1
    new_s = st.session_state.shot_input_1
    
    st.session_state.m_light = new_l
    st.session_state.m_cam = new_c
    st.session_state.m_shot = new_s
    
    # Update Lighting
    for key in st.session_state.keys():
        if key.startswith("light_input_"):
            st.session_state[key] = new_l
            
    # Update Camera
    for key in st.session_state.keys():
        if key.startswith("camera_input_"):
            st.session_state[key] = new_c
            
    # Update Shot Size
    for key in st.session_state.keys():
        if key.startswith("shot_input_"):
            st.session_state[key] = new_s


# ==============================================================================
# 5. SIDEBAR: KONFIGURASI TOKOH (MANUAL EXPLICIT - NO REDUCTION)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    # --- KARAKTER 1 ---
    st.markdown("### Karakter 1")
    c_name_1_val = st.text_input(
        "Nama Karakter 1", 
        key="c_name_1_input", 
        placeholder="Contoh: UDIN"
    )
    c_desc_1_val = st.text_area(
        "Fisik Karakter 1 (STRICT)", 
        key="c_desc_1_input", 
        placeholder="Detail fisik...", 
        height=100
    )
    
    st.divider()

    # --- KARAKTER 2 ---
    st.markdown("### Karakter 2")
    c_name_2_val = st.text_input(
        "Nama Karakter 2", 
        key="c_name_2_input", 
        placeholder="Contoh: TUNG"
    )
    c_desc_2_val = st.text_area(
        "Fisik Karakter 2 (STRICT)", 
        key="c_desc_2_input", 
        placeholder="Detail fisik...", 
        height=100
    )


# ==============================================================================
# 6. PARAMETER KUALITAS (ULTIMATE FIDELITY - NO REDUCTION)
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
# 7. FORM INPUT ADEGAN (MANUAL GRID - NO COMPRESSION)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    
    if idx_s == 1:
        header_text = f"🟢 MASTER CONTROL - ADEGAN {idx_s}"
        is_expanded = True
    else:
        header_text = f"🎬 ADEGAN {idx_s}"
        is_expanded = False
        
    with st.expander(header_text, expanded=is_expanded):
        
        # Grid System
        c_vis, c_light, c_move, c_shot = st.columns([4, 1.5, 1.5, 1.5])
        
        with c_vis:
            v_input = st.text_area(
                f"Visual Adegan {idx_s}", 
                key=f"vis_input_{idx_s}", 
                height=150
            )
        
        with c_light:
            st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
            if idx_s == 1:
                l_v = st.selectbox(
                    "L1", 
                    options_lighting, 
                    key="light_input_1", 
                    on_change=global_sync_v917, 
                    label_visibility="collapsed"
                )
            else:
                if f"light_input_{idx_s}" not in st.session_state:
                    st.session_state[f"light_input_{idx_s}"] = st.session_state.m_light
                l_v = st.selectbox(
                    f"L{idx_s}", 
                    options_lighting, 
                    key=f"light_input_{idx_s}", 
                    label_visibility="collapsed"
                )
        
        with c_move:
            st.markdown('<p class="small-label">🎥 Gerak Video</p>', unsafe_allow_html=True)
            if idx_s == 1:
                c_v = st.selectbox(
                    "C1", 
                    indonesia_camera, 
                    key="camera_input_1", 
                    on_change=global_sync_v917, 
                    label_visibility="collapsed"
                )
            else:
                if f"camera_input_{idx_s}" not in st.session_state:
                    st.session_state[f"camera_input_{idx_s}"] = st.session_state.m_cam
                c_v = st.selectbox(
                    f"C{idx_s}", 
                    indonesia_camera, 
                    key=f"camera_input_{idx_s}", 
                    label_visibility="collapsed"
                )

        with c_shot:
            st.markdown('<p class="small-label">📐 Ukuran Shot</p>', unsafe_allow_html=True)
            if idx_s == 1:
                s_v = st.selectbox(
                    "S1", 
                    indonesia_shot, 
                    key="shot_input_1", 
                    on_change=global_sync_v917, 
                    label_visibility="collapsed"
                )
            else:
                if f"shot_input_{idx_s}" not in st.session_state:
                    st.session_state[f"shot_input_{idx_s}"] = st.session_state.m_shot
                s_v = st.selectbox(
                    f"S{idx_s}", 
                    indonesia_shot, 
                    key=f"shot_input_{idx_s}", 
                    label_visibility="collapsed"
                )

        # Dialog Manual Karakter 1 & 2
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            label1 = c_name_1_val if c_name_1_val else "Tokoh 1"
            d1_text = st.text_input(f"Dialog {label1}", key=f"d1_in_{idx_s}")
            
        with col_d2:
            label2 = c_name_2_val if c_name_2_val else "Tokoh 2"
            d2_text = st.text_input(f"Dialog {label2}", key=f"d2_in_{idx_s}")
        
        adegan_storage.append({
            "num": idx_s, 
            "visual": v_input, 
            "light": l_v, 
            "cam": c_v, 
            "shot": s_v, 
            "t1_n": c_name_1_val, 
            "t1_d": d1_text, 
            "t2_n": c_name_2_val, 
            "t2_d": d2_text
        })


st.divider()


# ==============================================================================
# 8. GENERATOR PROMPT (THE ULTIMATE MEGA STRUCTURE - EXPLICIT MANUAL)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    
    active_list = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_list:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        
        for item in active_list:
            
            # --- TRANSLASI MANUAL ---
            final_camera_eng = camera_map.get(item["cam"], "Static")
            final_shot_eng = shot_map.get(item["shot"], "Medium Shot")
            
            s_id_num = item["num"]
            visual_desc = item["visual"]
            light_sel = item["light"]
            
            # --- MAPPING LIGHTING (NO REDUCTION - BARIS DEMI BARIS) ---
            
            if "Bening" in light_sel:
                f_light_text = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
                f_atmos_text = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
            
            elif "Sejuk" in light_sel:
                f_light_text = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
                f_atmos_text = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
            
            elif "Dramatis" in light_sel:
                f_light_text = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
                f_atmos_text = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
            
            elif "Jelas" in light_sel:
                f_light_text = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
                f_atmos_text = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
            
            elif "Mendung" in light_sel:
                f_light_text = (
                    "Intense moody overcast lighting with 16-bit color depth fidelity, absolute visual bite, "
                    "vivid pigment recovery on every surface, extreme local micro-contrast, "
                    "brilliant specular highlights on object edges, deep rich high-definition shadows."
                )
                f_atmos_text = (
                    "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, "
                    "gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on foliage, wood grain, "
                    "grass blades, house walls, concrete roads, and every environment object in frame. "
                    "Bone-dry surfaces, zero moisture, hyper-sharp edge definition across the entire frame."
                )
            
            elif "Suasana Malam" in light_sel:
                f_light_text = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim light highlights, 9000k cold moonlit glow, visible background detail."
                f_atmos_text = "Clear night atmosphere, deep indigo-black sky, hyper-defined textures on every object."
            
            elif "Suasana Alami" in light_sel:
                f_light_text = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments."
                f_atmos_text = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures."
            
            else:
                f_light_text = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                f_atmos_text = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background, zero atmospheric haze."

            # --- LOGIKA DIALOG ---
            txt_d1 = f"{item['t1_n']}: \"{item['t1_d']}\"" if item['t1_d'] else ""
            txt_d2 = f"{item['t2_n']}: \"{item['t2_d']}\"" if item['t2_d'] else ""
            combined_dialog = f"{txt_d1} {txt_d2}".strip()
            
            emotion_final = f"Emotion Context (DO NOT RENDER TEXT): Reacting to context: '{combined_dialog}'. Focus on high-fidelity facial expressions. " if combined_dialog else ""

            # --- CHARACTER DNA SYNC ---
            char_dna_ref = ""
            if item['t1_n'] and item['t1_n'].lower() in visual_desc.lower():
                char_dna_ref += f"STRICT CHARACTER APPEARANCE: {item['t1_n']} ({c_desc_1_val}) "
                
            if item['t2_n'] and item['t2_n'].lower() in visual_desc.lower():
                char_dna_ref += f"STRICT CHARACTER APPEARANCE: {item['t2_n']} ({c_desc_2_val}) "

            # --- RENDER HASIL ---
            st.subheader(f"HASIL PRODUKSI ADEGAN {s_id_num}")
            
            # IMAGE PROMPT
            img_res = (
                f"ini adalah referensi gambar karakter pada adegan per adegan. buatkan saya sebuah gambar dari adegan ke {s_id_num}. "
                f"{emotion_final}{char_dna_ref}Visual Scene: {visual_desc}. "
                f"Atmosphere: {f_atmos_text} Dry environment surfaces, no water droplets. "
                f"Lighting Effect: {f_light_text}. {img_quality_base}"
            )
            
            # VIDEO PROMPT
            vid_res = (
                f"Video Adegan {s_id_num}. {final_shot_eng} perspective. {final_camera_eng} movement. "
                f"{emotion_final}{char_dna_ref}Visual Scene: {visual_desc}. "
                f"Atmosphere: {f_atmos_text} Hyper-vivid colors, sharp focus, dry surfaces. "
                f"Lighting Effect: {f_light_text}. {vid_quality_base}. Context: {combined_dialog}"
            )
            
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.caption(f"📸 PROMPT GAMBAR")
                st.code(img_res, language="text")
            with col_res2:
                st.caption(f"🎥 PROMPT VIDEO ({final_shot_eng} + {final_camera_eng})")
                st.code(vid_res, language="text")
            
            st.divider()


st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.17 - Ultra Explicit Edition")
