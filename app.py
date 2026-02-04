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
st.info("Mode: v9.17 | PONDASI v9.15 | RESTORED CHARACTER ADD-ON | UI INDONESIA ❤️")

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
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

if 'm_light' not in st.session_state: st.session_state.m_light = options_lighting[0]
if 'm_cam' not in st.session_state: st.session_state.m_cam = indonesia_camera[0]
if 'm_shot' not in st.session_state: st.session_state.m_shot = indonesia_shot[2]

def global_sync_v917():
    """Fungsi Master Sync untuk semua Dropbox berdasarkan Adegan 1"""
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
# 5. SIDEBAR: KONFIGURASI TOKOH (RESTORED FULL EXPLICIT)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    characters_data_list = []

    # Karakter 1 (Eksplisit)
    st.markdown("### Karakter 1")
    c1_n = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c1_p = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", height=80)
    characters_data_list.append({"name": c1_n, "desc": c1_p})
    
    st.divider()

    # Karakter 2 (Eksplisit)
    st.markdown("### Karakter 2")
    c2_n = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c2_p = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", height=80)
    characters_data_list.append({"name": c2_n, "desc": c2_p})

    # --- FITUR TAMBAH KARAKTER LAIN (RESTORED DARI v9.15) ---
    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=10, value=2)
    
    if num_extra > 2:
        for idx_ex in range(2, int(num_extra)):
            st.divider()
            st.markdown(f"### Karakter {idx_ex + 1}")
            ex_n = st.text_input(f"Nama Karakter {idx_ex + 1}", key=f"ex_name_{idx_ex}")
            ex_p = st.text_area(f"Fisik Karakter {idx_ex + 1}", key=f"ex_phys_{idx_ex}", height=80)
            characters_data_list.append({"name": ex_n, "desc": ex_p})

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
# 7. FORM INPUT ADEGAN (MANUAL GRID INTERFACE)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    label_box = f"🟢 MASTER CONTROL - ADEGAN {idx_s}" if idx_s == 1 else f"🎬 ADEGAN {idx_s}"
    with st.expander(label_box, expanded=(idx_s == 1)):
        
        cols = st.columns([4, 1.5, 1.5, 1.5])
        
        with cols[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=150)
        
        with cols[1]:
            st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
            if idx_s == 1:
                l_val = st.selectbox("L1", options_lighting, key="light_input_1", on_change=global_sync_v917, label_visibility="collapsed")
            else:
                if f"light_input_{idx_s}" not in st.session_state: st.session_state[f"light_input_{idx_s}"] = st.session_state.m_light
                l_val = st.selectbox(f"L{idx_s}", options_lighting, key=f"light_input_{idx_s}", label_visibility="collapsed")
        
        with cols[2]:
            st.markdown('<p class="small-label">🎥 Gerak Video</p>', unsafe_allow_html=True)
            if idx_s == 1:
                c_val = st.selectbox("C1", indonesia_camera, key="camera_input_1", on_change=global_sync_v917, label_visibility="collapsed")
            else:
                if f"camera_input_{idx_s}" not in st.session_state: st.session_state[f"camera_input_{idx_s}"] = st.session_state.m_cam
                c_val = st.selectbox(f"C{idx_s}", indonesia_camera, key=f"camera_input_{idx_s}", label_visibility="collapsed")

        with cols[3]:
            st.markdown('<p class="small-label">📐 Ukuran Shot</p>', unsafe_allow_html=True)
            if idx_s == 1:
                s_val = st.selectbox("S1", indonesia_shot, key="shot_input_1", on_change=global_sync_v917, label_visibility="collapsed")
            else:
                if f"shot_input_{idx_s}" not in st.session_state: st.session_state[f"shot_input_{idx_s}"] = st.session_state.m_shot
                s_val = st.selectbox(f"S{idx_s}", indonesia_shot, key=f"shot_input_{idx_s}", label_visibility="collapsed")

        # Dialog Rows - Dinamis mengikuti jumlah karakter sidebar
        diag_cols = st.columns(len(characters_data_list))
        scene_dialogs = []
        for idx_c, c_data in enumerate(characters_data_list):
            with diag_cols[idx_c]:
                c_lbl = c_data['name'] if c_data['name'] else f"Tokoh {idx_c+1}"
                d_in = st.text_input(f"Dialog {c_lbl}", key=f"diag_{idx_s}_{idx_c}")
                scene_dialogs.append({"name": c_lbl, "text": d_in})
        
        adegan_storage.append({"num": idx_s, "visual": vis_in, "light": l_val, "cam": c_val, "shot": s_val, "dialogs": scene_dialogs})

st.divider()

# ==============================================================================
# 8. GENERATOR PROMPT (THE ULTIMATE MEGA STRUCTURE - NO REDUCTION)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        for adegan in active:
            # KONVERSI KE BAHASA INGGRIS TEKNIS UNTUK AI
            eng_cam = camera_map.get(adegan["cam"], "Static")
            eng_shot = shot_map.get(adegan["shot"], "Medium Shot")
            s_id, v_txt, l_sel = adegan["num"], adegan["visual"], adegan["light"]
            
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
                f_light = "Intense moody overcast lighting with 16-bit color depth fidelity, absolute visual bite, vivid pigment recovery on every surface, extreme local micro-contrast, brilliant specular highlights on object edges, deep rich high-definition shadows."
                f_atmos = "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on foliage, wood grain, grass blades, house walls, concrete roads, and every environment object in frame. Bone-dry surfaces, zero moisture, hyper-sharp edge definition across the entire frame."
            elif "Suasana Malam" in l_sel:
                f_light = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim light highlights, 9000k cold moonlit glow, visible background detail."
                f_atmos = "Clear night atmosphere, deep indigo-black sky, hyper-defined textures on every object."
            elif "Suasana Alami" in l_sel:
                f_light = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments."
                f_atmos = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures."
            else: # Suasana Sore
                f_light = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                f_atmos = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background, zero atmospheric haze."

            # LOGIKA EMOSI & CHARACTER DNA
            d_comb = " ".join([f"{d['name']}: \"{d['text']}\"" for d in adegan['dialogs'] if d['text']])
            emotion = f"Emotion Context (DO NOT RENDER TEXT): Reacting to context: '{d_comb}'. Focus on high-fidelity facial expressions. " if d_comb else ""
            char_refs = " ".join([f"STRICT CHARACTER APPEARANCE: {c['name']} ({c['desc']})" for c in characters_data_list if c['name'] and c['name'].lower() in v_txt.lower()])

            st.subheader(f"HASIL PRODUKSI ADEGAN {s_id}")
            
            # Prompt Gambar: Murni tanpa instruksi gerak
            img_p = f"buatkan gambar adegan {s_id}. {emotion}{char_refs} Visual: {v_txt}. Atmosphere: {f_atmos}. Lighting: {f_light}. {img_quality_base}"
            
            # Prompt Video: Disuntikkan Camera Move & Shot Size khusus untuk Veo 3
            vid_p = f"Video Adegan {s_id}. {eng_shot} perspective. {eng_cam} movement. {emotion}{char_refs} Visual: {v_txt}. Lighting: {f_light}. {vid_quality_base}"
            
            c1, c2 = st.columns(2)
            with c1:
                st.caption("📸 IMAGE PROMPT (STATIC)")
                st.code(img_p, language="text")
            with c2:
                st.caption(f"🎥 VIDEO PROMPT ({eng_shot} + {eng_cam})")
                st.code(vid_p, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.17 - Restored Full Edition")
