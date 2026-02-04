import streamlit as st

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MANUAL SETUP)
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. CUSTOM CSS (FULL EXPLICIT STYLE - TIDAK ADA RINGKASAN)
# ==============================================================================
st.markdown("""
    <style>
    /* Pengaturan Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    
    /* Pengaturan Teks di Sidebar */
    [data-testid="stSidebar"] p {
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] span {
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }

    /* Pengaturan Tombol Copy Hijau Terang */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 2px solid #ffffff !important;
        transform: scale(1.1); 
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    
    /* Hover dan Active State Tombol Copy */
    button[title="Copy to clipboard"]:hover {
        background-color: #218838 !important;
    }
    
    button[title="Copy to clipboard"]:active {
        background-color: #1e7e34 !important;
        transform: scale(1.0);
    }
    
    /* Pengaturan Font di Area Teks */
    .stTextArea textarea {
        font-size: 14px !important;
        line-height: 1.5 !important;
        font-family: 'Inter', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: REFERENCE FIDELITY - Strict Unique Character Integrity & Deep Cobalt ❤️")

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

    # Karakter 1 (Manual Entry)
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c1_phys = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", placeholder="Detail unik...", height=80)
    characters_data_list.append({"name": c1_name, "desc": c1_phys})
    
    st.divider()

    # Karakter 2 (Manual Entry)
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c2_phys = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", placeholder="Detail unik...", height=80)
    characters_data_list.append({"name": c2_name, "desc": c2_phys})

    st.divider()
    
    # Input Tambahan Karakter
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
# 4. PARAMETER KUALITAS (FULL EXPLICIT - NO SHORTHAND)
# ==============================================================================
# Filter blokir teks yang sangat ketat
no_text_lock = "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters, NO words on image, NO user interface."

# Parameter Kualitas Gambar: Menghapus 'Natural' untuk menjaga fidelitas karakter unik
img_quality_base = (
    "photorealistic surrealism photography, 16-bit color bit depth, hyper-saturated organic pigments, "
    "absolute fidelity to unique character reference, edge-to-edge optical sharpness, "
    "f/11 deep focus aperture, micro-contrast enhancement, intricate micro-textures on every surface, "
    "circular polarizer (CPL) filter effect, deep cobalt blue sky, crisp white wispy clouds, "
    "hyper-sharp foliage and vegetation textures, dry landscape environment, zero atmospheric haze, "
    "10:00 AM morning crisp daylight, 50% sun intensity, cool white balance, 7000k cold color temperature, "
    "rich high-contrast shadows, unprocessed raw photography, 8k resolution, captured on high-end 35mm lens, "
    "STRICTLY NO rain, NO wet surfaces, NO overcast sky, NO over-exposure, NO motion blur, " + no_text_lock
)

# Parameter Kualitas Video: Menjaga kejernihan gerak dan detail latar
vid_quality_base = (
    "ultra-high-fidelity vertical video, 9:16 aspect ratio, 60fps, photorealistic surrealism, "
    "strict character consistency, deep saturated pigments, deep cobalt blue sky, "
    "hyper-vivid foliage textures, crystal clear background focus, dry environment surfaces, "
    "extreme visual clarity, lossless texture quality, fluid organic motion, muted cool light, "
    "high contrast ratio, NO animation look, NO CGI look, " + no_text_lock
)

# ==============================================================================
# 5. FORM INPUT ADEGAN (FULL MEGA LAYOUT)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {idx_s}", expanded=(idx_s == 1)):
        
        # Penentuan Kolom Secara Eksplisit
        cols_setup = st.columns([3, 1.8] + [1.2] * len(characters_data_list))
        
        with cols_setup[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=120)
        
        with cols_setup[1]:
            # Pilihan Lighting 50% atau 75%
            light_radio = st.radio(f"Lighting {idx_s}", 
                                   ["50% (Dingin & Kristal)", "75% (Cerah & Tajam)"], 
                                   key=f"light_input_{idx_s}", horizontal=True)
        
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
# 6. LOGIKA GENERATOR PROMPT (AUTO-SYNC & FIDELITY)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    
    # Filter adegan aktif
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        
        for adegan in active_adegan:
            s_id = adegan["num"]
            v_txt = adegan["visual"]
            
            # 1. Logika Lighting (Ditulis Secara Manual)
            if "50%" in adegan["lighting"]:
                final_light_str = "50% dimmed sunlight intensity, zero sun glare, crisp cool morning air, muted exposure, sharp contrast shadows"
            else:
                final_light_str = "75% sunlight intensity, brilliant clear daylight, vivid sharp highlights, high-energy vibrant colors"

            # 2. Logika Emosi Dialog (Anti-Text Lock)
            dialogs_combined = [f"{d['name']}: \"{d['text']}\"" for d in adegan['dialogs'] if d['text']]
            full_dialog_str = " ".join(dialogs_combined) if dialogs_combined else ""
            
            emotion_logic_str = ""
            if full_dialog_str:
                emotion_logic_str = (
                    f"Emotion Context (DO NOT RENDER TEXT ON IMAGE): Characters react to this dialogue: '{full_dialog_str}'. "
                    "Focus on realistic facial micro-expressions and high-definition muscle tension. "
                )

            # 3. FUNGSI AUTO-SYNC KARAKTER (PENULISAN MANUAL & PANJANG)
            # Men-scan karakter yang ada di deskripsi visual
            detected_phys_list = []
            for c_check in characters_data_list:
                if c_check['name'] and c_check['name'].lower() in v_txt.lower():
                    # Menambahkan tag 'STRICT APPEARANCE' agar AI tidak menghaluskan detail unik
                    detected_phys_list.append(f"STRICT CHARACTER APPEARANCE: {c_check['name']} ({c_check['desc']})")
            
            final_phys_ref = " ".join(detected_phys_list) + " " if detected_phys_list else ""

            # 4. Konstruksi Prompt (Mega Construction - Tidak Ada yang Diringkas)
            is_first_prefix = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""
            img_cmd_prefix = f"buatkan saya sebuah gambar dari adegan ke {s_id}. "

            # Perakitan Manual Prompt Gambar
            final_prompt_img = (
                f"{is_first_prefix}{img_cmd_prefix}{emotion_logic_str}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: Locked 10:00 AM morning sun, deep cobalt blue sky, thin wispy clouds, dry environment, hyper-sharp vegetation textures. "
                f"Lighting Effect: {final_light_str}. {img_quality_base}"
            )

            # Perakitan Manual Prompt Video
            final_prompt_vid = (
                f"Video Adegan {s_id}. {emotion_logic_str}{final_phys_ref}Visual Scene: {v_txt}. "
                f"Atmosphere: 10:00 AM Locked Time, crystal clear deep cobalt sky, hyper-vivid foliage, dry surfaces. "
                f"Lighting Effect: {final_light_str}. {vid_quality_base}. Dialog Reference: {full_dialog_str}"
            )

            # 5. Output Display
            st.subheader(f"ADENGAN {s_id}")
            col_res_1, col_res_2 = st.columns(2)
            
            with col_res_1:
                st.caption("📸 PROMPT GAMBAR (Strict Reference Fidelity)")
                st.code(final_prompt_img, language="text")
            
            with col_res_2:
                st.caption("🎥 PROMPT VIDEO (Strict Reference Fidelity)")
                st.code(final_prompt_vid, language="text")
            
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v7.8 - The Colossal Structure")
