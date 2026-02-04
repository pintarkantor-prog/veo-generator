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

    /* Style untuk Box Preview Cinematic */
    .preview-box {
        border-radius: 12px;
        padding: 12px;
        background: #262730;
        border: 1px solid #464b5d;
        text-align: center;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.16 | STANDARD VIDEO | CINEMATIC PREVIEW | NO REDUCTION ❤️")

# ==============================================================================
# 3. SIDEBAR: KONFIGURASI TOKOH (EXPLICIT MEGA SETUP)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    characters_data_list = []
    # Karakter 1
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c1_phys = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", placeholder="Detail fisik...", height=80)
    characters_data_list.append({"name": c1_name, "desc": c1_phys})
    
    st.divider()
    # Karakter 2
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c2_phys = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", placeholder="Detail fisik...", height=80)
    characters_data_list.append({"name": c2_name, "desc": c2_phys})

    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=5, value=2)
    if num_extra > 2:
        for idx_ex in range(2, int(num_extra)):
            st.divider()
            st.markdown(f"### Karakter {idx_ex + 1}")
            ex_n = st.text_input(f"Nama Karakter {idx_ex + 1}", key=f"ex_name_{idx_ex}")
            ex_p = st.text_area(f"Fisik Karakter {idx_ex + 1}", key=f"ex_phys_{idx_ex}", height=80)
            characters_data_list.append({"name": ex_n, "desc": ex_p})

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
# 5. FORM INPUT ADEGAN (WIDE LAYOUT)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {idx_s}", expanded=(idx_s == 1)):
        cols_setup = st.columns([5, 2] + [1.2] * len(characters_data_list))
        with cols_setup[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=150, placeholder="Tulis deskripsi visual di sini...")
        with cols_setup[1]:
            light_radio = st.radio(f"Pencahayaan", 
                                   ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"], 
                                   key=f"light_input_{idx_s}", horizontal=False)
        scene_dialog_list = []
        for idx_c, char_val in enumerate(characters_data_list):
            with cols_setup[idx_c + 2]:
                char_label = char_val['name'] if char_val['name'] else f"Tokoh {idx_c + 1}"
                diag_in = st.text_input(f"Dialog {char_label}", key=f"diag_input_{idx_c}_{idx_s}")
                scene_dialog_list.append({"name": char_label, "text": diag_in})
        adegan_storage.append({"num": idx_s, "visual": vis_in, "lighting": light_radio, "dialogs": scene_dialog_list})

st.divider()

# ==============================================================================
# 6. LOGIKA GENERATOR PROMPT & CINEMATIC PREVIEW
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
            l_type = adegan["lighting"]
            
            # --- FULL IF-ELSE LOGIKA LIGHTING & PREVIEW URL (RECOVERED) ---
            if l_type == "Bening dan Tajam":
                f_light = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
                f_atmos = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
                img_url = "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=400&q=80"
            elif l_type == "Sejuk dan Terang":
                f_light = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
                f_atmos = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
                img_url = "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=400&q=80"
            elif l_type == "Dramatis":
                f_light = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
                f_atmos = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
                img_url = "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=400&q=80"
            elif l_type == "Jelas dan Solid":
                f_light = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
                f_atmos = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
                img_url = "https://images.unsplash.com/photo-1473448912268-2022ce9509d8?auto=format&fit=crop&w=400&q=80"
            elif l_type == "Suasana Sore":
                f_light = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                f_atmos = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background, zero atmospheric haze."
                img_url = "https://images.unsplash.com/photo-1472120482482-d42077454d2e?auto=format&fit=crop&w=400&q=80"
            elif l_type == "Mendung":
                f_light = "Intense moody overcast lighting with 16-bit color depth fidelity, absolute visual bite, vivid pigment recovery on every surface, extreme local micro-contrast, brilliant specular highlights on object edges, deep rich high-definition shadows."
                f_atmos = "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on foliage, wood grain, grass blades, house walls, concrete roads, and every environment object. Bone-dry surfaces, zero moisture, hyper-sharp edge definition across the entire frame."
                img_url = "https://images.unsplash.com/photo-1483977399921-6cf34967481f?auto=format&fit=crop&w=400&q=80"
            elif l_type == "Suasana Malam":
                f_light = "Hyper-Chrome Fidelity lighting, ultra-intense HMI studio lamp illumination, extreme micro-shadows on all textures, brutal contrast ratio, specular highlight glints on every edge, zero-black floor depth."
                f_atmos = "Pure vacuum-like atmosphere, zero light scattering, absolute visual bite, chrome-saturated pigments, hyper-defined micro-pores and wood grain textures, 10000k ultra-cold industrial white light."
                img_url = "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?auto=format&fit=crop&w=400&q=80"
            elif l_type == "Suasana Alami":
                f_light = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments, deep rich micro-shadows within foliage and soil textures."
                f_atmos = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures on every grass blade and soil particle, high-fidelity natural contrast across the entire frame, 5000k neutral soft-sun brilliance."
                img_url = "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=400&q=80"
            else:
                f_light = ""
                f_atmos = ""
                img_url = ""

            # --- LOGIKA EMOSI & CHARACTER SYNC (FULL) ---
            dialogs_combined = [f"{d['name']}: \"{d['text']}\"" for d in adegan['dialogs'] if d['text']]
            full_dialog_str = " ".join(dialogs_combined) if dialogs_combined else ""
            emotion_logic = f"Emotion Context (DO NOT RENDER TEXT): Reacting to dialogue context: '{full_dialog_str}'. Focus on high-fidelity facial expressions and muscle tension. " if full_dialog_str else ""
            
            detected_phys_list = []
            for c_check in characters_data_list:
                if c_check['name'] and c_check['name'].lower() in v_txt.lower():
                    detected_phys_list.append(f"STRICT CHARACTER APPEARANCE: {c_check['name']} ({c_check['desc']})")
            final_phys_ref = " ".join(detected_phys_list) + " " if detected_phys_list else ""

            # --- KONSTRUKSI PROMPT FINAL (TANPA OPTIMIZER VEO) ---
            is_first_pre = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""
            img_cmd_pre = f"buatkan saya sebuah gambar dari adegan ke {s_id}. "

            final_img = (f"{is_first_pre}{img_cmd_pre}{emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. Atmosphere: {f_atmos} Dry surfaces. Lighting: {f_light}. {img_quality_base}")
            final_vid = (f"Video Adegan {s_id}. {emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. Atmosphere: {f_atmos}. Lighting: {f_light}. {vid_quality_base}")

            # --- DISPLAY RENDERING ---
            st.subheader(f"ADENGAN {s_id}")
            c_prompt, c_preview = st.columns([7, 3])
            with c_prompt:
                st.caption(f"📸 PROMPT GAMBAR ({l_type})")
                st.code(final_img, language="text")
                st.caption("🎥 PROMPT VIDEO")
                st.code(final_vid, language="text")
            
            with c_preview:
                st.markdown(f"""
                <div class="preview-box">
                    <p style="color:white; font-size:12px; margin-bottom:8px;">REF: {l_type.upper()}</p>
                    <img src="{img_url}" style="width:100%; border-radius:8px;">
                    <p style="color:#aaa; font-size:10px; margin-top:8px;">Visual Target: High-Contrast Texture Lock</p>
                </div>
                """, unsafe_allow_html=True)
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.16 - Standard Video Recovery")
