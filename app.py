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
# 2. CUSTOM CSS (FULL EXPLICIT STYLE - TIDAK ADA PENGURANGAN)
# ==============================================================================
st.markdown("""
    <style>
    /* Latar Belakang Sidebar agar Gelap Profesional */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    
    /* Warna Teks Sidebar agar Putih Terang */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }

    /* Tombol Copy Hijau Terang yang Ikonik */
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
    
    /* Pengaturan Font Area Input Visual */
    .stTextArea textarea {
        font-size: 14px !important;
        line-height: 1.5 !important;
        font-family: 'Inter', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: FIXED v8.2 | POLARIZED HIGH-CONTRAST | NO RAIN LOCK ❤️")

# ==============================================================================
# 3. SIDEBAR: KONFIGURASI TOKOH (EXPLICIT SETUP)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    # Penampung data karakter (Mega List)
    characters_data_list = []

    # Karakter 1 (Penulisan Eksplisit)
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c1_phys = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", placeholder="Detail fisik...", height=80)
    characters_data_list.append({"name": c1_name, "desc": c1_phys})
    
    st.divider()

    # Karakter 2 (Penulisan Eksplisit)
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c2_phys = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", placeholder="Detail fisik...", height=80)
    characters_data_list.append({"name": c2_name, "desc": c2_phys})

    st.divider()
    
    # Menentukan jumlah karakter tambahan
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=5, value=2)

    # Loop Manual untuk Karakter 3, 4, dan 5
    if num_extra > 2:
        for idx_ex in range(2, int(num_extra)):
            st.divider()
            st.markdown(f"### Karakter {idx_ex + 1}")
            ex_n = st.text_input(f"Nama Karakter {idx_ex + 1}", key=f"ex_name_{idx_ex}")
            ex_p = st.text_area(f"Fisik Karakter {idx_ex + 1}", key=f"ex_phys_{idx_ex}", height=80)
            characters_data_list.append({"name": ex_n, "desc": ex_p})

# ==============================================================================
# 4. PARAMETER KUALITAS (FULL COLOSSAL - ANTI RAIN LOCK)
# ==============================================================================
# Perintah negatif yang sangat keras untuk memblokir teks dan efek air
no_text_no_rain_lock = (
    "STRICTLY NO rain, NO puddles, NO raindrops, NO wet ground, NO water droplets, "
    "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters."
)

img_quality_base = (
    "photorealistic surrealism style, 16-bit color bit depth, hyper-saturated organic pigments, "
    "absolute fidelity to unique character reference, edge-to-edge optical sharpness, "
    "f/11 deep focus aperture, micro-contrast enhancement, intricate micro-textures on every surface, "
    "circular polarizer (CPL) filter effect, deep cobalt blue sky, crisp white wispy clouds, "
    "hyper-sharp foliage and vegetation textures, zero atmospheric haze, "
    "rich high-contrast shadows, unprocessed raw photography, 8k resolution, captured on high-end 35mm lens, "
    "STRICTLY NO over-exposure, NO motion blur, NO lens flare, " + no_text_no_rain_lock
)

vid_quality_base = (
    "ultra-high-fidelity vertical video, 9:16, 60fps, photorealistic surrealism, "
    "strict character consistency, deep saturated pigments, deep cobalt blue sky, "
    "hyper-vivid foliage textures, crystal clear background focus, "
    "extreme visual clarity, lossless texture quality, fluid organic motion, "
    "high contrast ratio, NO animation look, NO CGI look, " + no_text_no_rain_lock
)

# ==============================================================================
# 5. FORM INPUT ADEGAN (FULL LAYOUT)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {idx_s}", expanded=(idx_s == 1)):
        
        # Penentuan layout kolom secara manual (Visual, Lighting, Dialogs)
        cols_setup = st.columns([3, 2.8] + [1.2] * len(characters_data_list))
        
        with cols_setup[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=120)
        
        with cols_setup[1]:
            # Pilihan Lighting
            light_radio = st.radio(f"Pilih Efek Cahaya (Adegan {idx_s})", 
                                   [
                                       "50% (Dingin & Kristal)", 
                                       "75% (Cerah & Tajam)", 
                                       "Lembap Dingin (Deep Saturation)", 
                                       "Sore Jam 4 (Low Sun & Cold Contrast)"
                                   ], 
                                   key=f"light_input_{idx_s}", horizontal=False)
        
        # Penampung Dialog Per Karakter
        scene_dialog_list = []
        for idx_c, char_val in enumerate(characters_data_list):
            with cols_setup[idx_c + 2]:
                char_label = char_val['name'] if char_val['name'] else f"Karakter {idx_c + 1}"
                diag_in = st.text_input(f"Dialog {char_label}", key=f"diag_input_{idx_c}_{idx_s}")
                scene_dialog_list.append({"name": char_label, "text": diag_in})
        
        adegan_storage.append({
            "num": idx_s, "visual": vis_in, "lighting": light_radio, "dialogs": scene_dialog_list
        })

st.divider()

# ==============================================================================
# 6. LOGIKA GENERATOR PROMPT (AUTO-SYNC & BUG-FIXED MEGA LOGIC)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        
        for adegan in active_adegan:
            s_id = adegan["num"]
            # Variabel utama deskripsi visual
            v_txt = adegan["visual"]
            
            # --- LOGIKA LIGHTING (FIXED & DETAIL) ---
            if "50%" in adegan["lighting"]:
                f_light = "50% dimmed sunlight, crisp cool morning air, muted exposure, sharp shadows, 7000k temp."
                f_atmos = "10:00 AM morning sun, deep cobalt blue sky, thin wispy clouds, dry environment."
            
            elif "75%" in adegan["lighting"]:
                f_light = "75% brilliant sunlight, vivid sharp highlights, high-energy vibrant colors, dry landscape."
                f_atmos = "10:00 AM bright daylight, deep cobalt blue sky, crystal clear visibility."
            
            elif "Lembap" in adegan["lighting"]:
                f_light = "Deep matte color saturation, specular highlights on edges, cold ambient light, no direct glare, high micro-contrast."
                f_atmos = "Early morning dew atmosphere, bone-dry ground, no puddles, crisp clear air, 8000k extreme cold temperature, hyper-saturated foliage colors."
            
            else:
                f_light = "Low-angle 4:00 PM sun position, minimal light intensity, cold long shadows, extreme edge sharpness."
                f_atmos = "4:00 PM clear late afternoon, indigo-cobalt sky, zero haze, dry surfaces, crisp high-contrast background."

            # --- LOGIKA EMOSI DIALOG (FIXED NAME ERROR) ---
            # Perbaikan: Menggunakan 'dialogs_combined' secara konsisten sesuai instruksi
            dialogs_combined = [f"{d['name']}: \"{d['text']}\"" for d in adegan['dialogs'] if d['text']]
            # Perbaikan: Mendefinisikan 'full_dialog_str' dari 'dialogs_combined'
            full_dialog_str = " ".join(dialogs_combined) if dialogs_combined else ""
            
            emotion_logic = f"Emotion Context (DO NOT RENDER TEXT): Reacting to dialogue context: '{full_dialog_str}'. Focus on micro-expressions. " if full_dialog_str else ""

            # --- LOGIKA AUTO-SYNC KARAKTER (FIXED v_txt ERROR) ---
            detected_phys_list = []
            for c_check in characters_data_list:
                # Memeriksa nama karakter terhadap variabel 'v_txt' (BUKAN 'v_text')
                if c_check['name'] and c_check['name'].lower() in v_txt.lower():
                    detected_phys_list.append(f"STRICT CHARACTER APPEARANCE: {c_check['name']} ({c_check['desc']})")
            
            final_phys_ref = " ".join(detected_phys_list) + " " if detected_phys_list else ""

            # --- KONSTRUKSI PROMPT FINAL (MANUAL & PANJANG) ---
            is_first_pre = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""
            img_cmd_pre = f"buatkan saya sebuah gambar dari adegan ke {s_id}. "

            # Prompt Gambar
            final_img = (
                f"{is_first_pre}{img_cmd_pre}{emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: {f_atmos} Dry environment, no rain, no water. "
                f"Lighting Effect: {f_light}. {img_quality_base}"
            )

            # Prompt Video
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
st.sidebar.caption("PINTAR MEDIA Storyboard v8.2 - FIXED Mega Structure")
