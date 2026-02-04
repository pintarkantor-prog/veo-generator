import streamlit as st

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MANUAL SETUP - TIDAK ADA RINGKASAN)
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. CUSTOM CSS (FULL EXPLICIT STYLE - MEGA STRUCTURE)
# ==============================================================================
st.markdown("""
    <style>
    /* Pengaturan Latar Belakang Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    
    /* Pengaturan Warna Teks Sidebar secara Eksplisit */
    [data-testid="stSidebar"] p {
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] span {
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }

    /* Pengaturan Tombol Copy Warna Hijau Terang (Manual Style) */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 2px solid #ffffff !important;
        transform: scale(1.1); 
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    
    /* Hover State Tombol Copy */
    button[title="Copy to clipboard"]:hover {
        background-color: #218838 !important;
    }
    
    /* Active State Tombol Copy */
    button[title="Copy to clipboard"]:active {
        background-color: #1e7e34 !important;
        transform: scale(1.0);
    }
    
    /* Pengaturan Font Area Input Deskripsi Visual */
    .stTextArea textarea {
        font-size: 14px !important;
        line-height: 1.5 !important;
        font-family: 'Inter', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: ADVANCED LIGHTING & ULTRA-HIGH CONTRAST FIDELITY ❤️")

# ==============================================================================
# 3. SIDEBAR: KONFIGURASI TOKOH (EXPLICIT MEGA SETUP)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    
    # Input Jumlah Adegan
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    # List penampung data karakter
    characters_data_list = []

    # Karakter 1 (Penulisan Manual)
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c1_phys = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", placeholder="Detail fisik yang sangat spesifik...", height=80)
    characters_data_list.append({"name": c1_name, "desc": c1_phys})
    
    st.divider()

    # Karakter 2 (Penulisan Manual)
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c2_phys = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", placeholder="Detail fisik yang sangat spesifik...", height=80)
    characters_data_list.append({"name": c2_name, "desc": c2_phys})

    st.divider()
    
    # Kontrol Karakter Tambahan
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
# 4. PARAMETER KUALITAS (FULL COLOSSAL STRUCTURE - NO REDUCTION)
# ==============================================================================
no_text_lock = "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters, NO words on image, NO user interface."

# Parameter Kualitas Gambar Utama (Reference Fidelity & High Sharpness)
img_quality_base = (
    "photorealistic surrealism style, 16-bit color bit depth, hyper-saturated organic pigments, "
    "absolute fidelity to unique character reference, edge-to-edge optical sharpness, "
    "f/11 deep focus aperture, micro-contrast enhancement, intricate micro-textures on every surface, "
    "circular polarizer (CPL) filter effect, deep cobalt blue sky, crisp white wispy clouds, "
    "hyper-sharp foliage and vegetation textures, zero atmospheric haze, "
    "rich high-contrast shadows, unprocessed raw photography, 8k resolution, captured on high-end 35mm lens, "
    "STRICTLY NO over-exposure, NO motion blur, NO lens flare, " + no_text_lock
)

# Parameter Kualitas Video Utama
vid_quality_base = (
    "ultra-high-fidelity vertical video, 9:16 aspect ratio, 60fps, photorealistic surrealism, "
    "strict character consistency, deep saturated pigments, deep cobalt blue sky, "
    "hyper-vivid foliage textures, crystal clear background focus, "
    "extreme visual clarity, lossless texture quality, fluid organic motion, "
    "high contrast ratio, NO animation look, NO CGI look, " + no_text_lock
)

# ==============================================================================
# 5. FORM INPUT ADEGAN (FULL MEGA LAYOUT)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {idx_s}", expanded=(idx_s == 1)):
        
        # Penentuan Kolom Secara Eksplisit (Visual, Lighting, Dialogs)
        cols_setup = st.columns([3, 2.5] + [1.2] * len(characters_data_list))
        
        with cols_setup[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=120, placeholder="Sebutkan nama tokoh agar fisiknya muncul...")
        
        with cols_setup[1]:
            # Penambahan Opsi Lighting Sesuai Permintaan
            light_radio = st.radio(f"Pilih Efek Cahaya (Adegan {idx_s})", 
                                   [
                                       "50% (Dingin & Kristal)", 
                                       "75% (Cerah & Tajam)", 
                                       "Basah & Dingin (Tanpa Hujan)", 
                                       "Sore Jam 4 (Dingin & Kontras)"
                                   ], 
                                   key=f"light_input_{idx_s}", horizontal=False)
        
        # Penampung Dialog Per Adegan
        scene_dialog_list = []
        for idx_c, char_val in enumerate(characters_data_list):
            with cols_setup[idx_c + 2]:
                char_label = char_val['name'] if char_val['name'] else f"Karakter {idx_c + 1}"
                diag_in = st.text_input(f"Dialog {char_label}", key=f"diag_input_{idx_c}_{idx_s}")
                scene_dialog_list.append({"name": char_label, "text": diag_in})
        
        adegan_storage.append({
            "num": idx_s, 
            "visual": vis_in, 
            "lighting": light_radio, 
            "dialogs": scene_dialog_list
        })

st.divider()

# ==============================================================================
# 6. LOGIKA GENERATOR PROMPT (AUTO-SYNC & ADVANCED LIGHTING)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    
    # Validasi adegan yang diisi
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        
        for adegan in active_adegan:
            s_id = adegan["num"]
            v_txt = adegan["visual"]
            
            # --- LOGIKA LIGHTING EKSPLISIT (MANUAL & DETAIL) ---
            if "50%" in adegan["lighting"]:
                f_light = "50% dimmed sunlight, crisp cool morning air, muted exposure, sharp contrast shadows, 7000k temp."
                f_atmos = "10:00 AM crisp morning sun, deep cobalt blue sky, thin wispy clouds, dry environment."
            
            elif "75%" in adegan["lighting"]:
                f_light = "75% brilliant sunlight, vivid sharp highlights, high-energy vibrant colors, crystal clear day."
                f_atmos = "10:00 AM bright daylight, deep cobalt blue sky, high visibility, dry environment."
            
            elif "Basah" in adegan["lighting"]:
                # Logika Dingin & Basah Tanpa Hujan
                f_light = "Cold moist lighting, damp surfaces with high reflectivity, ultra-saturated colors, deep blacks, high micro-contrast."
                f_atmos = "Post-dew morning atmosphere, STRICTLY NO RAIN, wet ground and leaves, high-gloss textures, deep blue overcast-clear sky mix, 8000k cold temp."
            
            else:
                # Logika Sore Jam 4 Dingin & Kontras
                f_light = "Low-angle 4:00 PM sun, minimal golden light, dominating cold shadows, extreme edge-to-edge sharpness, high dynamic range."
                f_atmos = "4:00 PM late afternoon, cold mountain air visibility, deep cobalt sky turning indigo, long sharp shadows, hyper-clear background."

            # --- LOGIKA EMOSI DIALOG ---
            dialogs_combined = [f"{d['name']}: \"{d['text']}\"" for d in adegan['dialogs'] if d['text']]
            full_dialog_str = " ".join(dialogs_combined) if dialogs_combined else ""
            
            emotion_logic = ""
            if full_dialog_str:
                emotion_logic = (
                    f"Emotion Context (DO NOT RENDER TEXT): Reacting to dialogue: '{full_dialog_str}'. "
                    "Focus on high-definition facial expressions and character muscle tension. "
                )

            # --- LOGIKA AUTO-SYNC KARAKTER (PENULISAN MANUAL) ---
            detected_phys_list = []
            for c_check in characters_data_list:
                if c_check['name'] and c_check['name'].lower() in v_txt.lower():
                    # Memberikan tag PRIORITAS TERTINGGI agar karakter unik tetap konsisten
                    detected_phys_list.append(f"STRICT CHARACTER APPEARANCE: {c_check['name']} ({c_check['desc']})")
            
            final_phys_ref = " ".join(detected_phys_list) + " " if detected_phys_list else ""

            # --- KONSTRUKSI PROMPT FINAL (MANUAL ASSEMBLY) ---
            is_first_pre = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""
            img_cmd_pre = f"buatkan saya sebuah gambar dari adegan ke {s_id}. "

            # Prompt Gambar
            final_img = (
                f"{is_first_pre}{img_cmd_pre}{emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: {f_atmos} Hyper-sharp vegetation textures and clear objects. "
                f"Lighting Effect: {f_light}. {img_quality_base}"
            )

            # Prompt Video
            final_vid = (
                f"Video Adegan {s_id}. {emotion_logic}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: {f_atmos} Sharp background focus, hyper-vivid colors. "
                f"Lighting Effect: {f_light}. {vid_quality_base}. Context: {full_dialog_str}"
            )

            # --- DISPLAY OUTPUT ---
            st.subheader(f"ADENGAN {s_id}")
            c1, c2 = st.columns(2)
            
            with c1:
                st.caption(f"📸 PROMPT GAMBAR ({adegan['lighting']})")
                st.code(final_img, language="text")
            
            with c2:
                st.caption(f"🎥 PROMPT VIDEO ({adegan['lighting']})")
                st.code(final_vid, language="text")
            
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v7.9 - Advanced Lighting Structure")
