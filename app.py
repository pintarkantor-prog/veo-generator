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
# 2. CUSTOM CSS (STRICT STYLE - NO REDUCTION)
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
st.info("Mode: v9.35 | REMOVE CHARACTER REF | PURE VISUAL FLOW | NO REDUCTION ❤️")

# ==============================================================================
# 3. SIDEBAR: KONFIGURASI (BAHASA INDONESIA SEDERHANA)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Total Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🎬 Kunci Gaya Sutradara")
    tone_style = st.selectbox("Pilih Estetika Visual", 
                             ["None", "Sinematik", "Warna Menyala", "Dokumenter", "Film Jadul", "Film Thriller", "Dunia Khayalan"])

    st.divider()
    st.subheader("👥 Pengaturan Karakter 1")
    c1_name = st.text_input("Nama Tokoh 1", placeholder="Contoh: UDIN")
    c1_base = st.text_area("Ciri Fisik Dasar (Wajah/Kepala)", placeholder="Sebutkan detail fisik untuk menjaga fidelitas gambar referensi...", height=70)
    c1_outfit = st.text_input("Pakaian & Aksesoris", placeholder="Contoh: Kaos putih, kalung emas")

    st.divider()
    st.subheader("👥 Pengaturan Karakter 2")
    c2_name = st.text_input("Nama Tokoh 2", placeholder="Contoh: TUNG")
    c2_base = st.text_area("Ciri Fisik Dasar (Wajah/Kayu)", placeholder="Sebutkan detail fisik untuk menjaga fidelitas gambar referensi...", height=70)
    c2_outfit = st.text_input("Pakaian & Aksesoris ", placeholder="Contoh: Kemeja jeans biru")

# ==============================================================================
# 4. LOGIKA MASTER-SYNC (SESSION STATE)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

if 'master_light' not in st.session_state:
    st.session_state.master_light = options_lighting[0]

def update_all_lights():
    if "light_1" in st.session_state:
        new_val = st.session_state["light_1"]
        st.session_state.master_light = new_val
        for i in range(2, 51):
            st.session_state[f"light_{i}"] = new_val

# ==============================================================================
# 5. PARAMETER KUALITAS (FULL EXPLICIT - NO REDUCTION)
# ==============================================================================
no_text_lock = (
    "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters, NO rain, NO water."
)

img_quality_base = (
    "photorealistic surrealism style, 16-bit color bit depth, hyper-saturated organic pigments, "
    "edge-to-edge optical sharpness, f/11 deep focus aperture, micro-contrast enhancement, "
    "intricate micro-textures on every surface, circular polarizer (CPL) filter effect, zero atmospheric haze, "
    "rich high-contrast shadows, unprocessed raw photography, 8k resolution, captured on high-end 35mm lens, "
    "STRICTLY NO over-exposure, NO motion blur, NO lens flare, " + no_text_lock
)

# ==============================================================================
# 6. FORM INPUT ADEGAN (MASTER-SYNC INTERFACE)
# ==============================================================================
st.subheader("📝 Detail Adegan (Adegan 1 adalah Leader)")
adegan_storage = []
options_condition = ["Normal/Bersih", "Terluka/Lecet", "Kotor/Berdebu", "Hancur Parah"]

for idx_s in range(1, int(num_scenes) + 1):
    is_leader = (idx_s == 1)
    with st.expander(f"KONFIGURASI ADEGAN {idx_s} {'(MASTER CONTROL)' if is_leader else ''}", expanded=is_leader):
        col_l1, col_l2 = st.columns([3, 1])
        with col_l1:
            vis_in = st.text_area(f"Deskripsi Visual {idx_s}", key=f"vis_{idx_s}", height=100)
        with col_l2:
            if is_leader:
                l_val = st.selectbox("Cuaca/Cahaya", options_lighting, key="light_1", on_change=update_all_lights)
            else:
                if f"light_{idx_s}" not in st.session_state:
                    st.session_state[f"light_{idx_s}"] = st.session_state.master_light
                l_val = st.selectbox(f"Cahaya {idx_s}", options_lighting, key=f"light_{idx_s}")
        
        st.markdown("---")
        # Karakter 1
        l_c1_1, l_c1_2 = st.columns([1, 2])
        with l_c1_1: cond1 = st.selectbox(f"Kondisi {c1_name if c1_name else 'Tokoh 1'}", options_condition, key=f"cond1_{idx_s}")
        with l_c1_2: diag1 = st.text_input(f"Dialog {c1_name if c1_name else 'Tokoh 1'}", key=f"diag1_{idx_s}")
        
        # Karakter 2
        l_c2_1, l_c2_2 = st.columns([1, 2])
        with l_c2_1: cond2 = st.selectbox(f"Kondisi {c2_name if c2_name else 'Tokoh 2'}", options_condition, key=f"cond2_{idx_s}")
        with l_c2_2: diag2 = st.text_input(f"Dialog {c2_name if c2_name else 'Tokoh 2'}", key=f"diag2_{idx_s}")

        adegan_storage.append({"num": idx_s, "visual": vis_in, "lighting": l_val, "cond1": cond1, "cond2": cond2, "diag1": diag1, "diag2": diag2})

st.divider()

# ==============================================================================
# 7. LOGIKA GENERATOR PROMPT (PURE VISUAL FLOW - NO CHARACTER REF LABEL)
# ==============================================================================
if st.button("🚀 GENERATE SEMUA PROMPT", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        for adegan in active:
            s_id, v_txt, l_type = adegan["num"], adegan["visual"], adegan["lighting"]
            
            style_map = {"Sinematik": "Gritty Cinematic", "Warna Menyala": "Vibrant Pop", "Dokumenter": "High-End Documentary", "Film Jadul": "Vintage Film 35mm", "Film Thriller": "Dark Thriller", "Dunia Khayalan": "Surreal Dreamy"}
            active_style = style_map.get(tone_style, "")
            style_lock = f"Overall Visual Tone: {active_style}. " if tone_style != "None" else ""

            status_map = {
                "Normal/Bersih": "pristine condition, clean skin and clothes.",
                "Terluka/Lecet": "visible scratches and scuff marks, pained expression.",
                "Kotor/Berdebu": "covered in dust and grime.",
                "Hancur Parah": "heavily damaged, deep cracks, torn clothes."
            }

            # --- FULL MAPPING LOGIKA LIGHTING ---
            if l_type == "Bening dan Tajam":
                f_light, f_atmos = "Ultra-high altitude light visibility, extreme micro-contrast.", "10:00 AM mountain altitude sun, cobalt sky."
            elif l_type == "Sejuk dan Terang":
                f_light, f_atmos = "8000k ice-cold temperature, zero sun glare.", "12:00 PM glacier-clear atmosphere."
            elif l_type == "Dramatis":
                f_light, f_atmos = "Hard directional side-lighting, pitch-black shadows.", "Late morning sun, dramatic light rays."
            elif l_type == "Mendung":
                f_light = "Intense moody overcast lighting, 16-bit color depth fidelity, absolute visual bite."
                f_atmos = "Moody atmosphere, 8000k ice-cold brilliance, gray-cobalt sky."
            elif l_type == "Suasana Malam":
                f_light = "Hyper-Chrome Fidelity lighting, ultra-intense HMI studio lamp illumination."
                f_atmos = "Pure vacuum-like atmosphere, absolute visual bite, chrome-saturated pigments."
            else: f_light, f_atmos = f"{l_type} lighting", f"{l_type} atmosphere"

            # --- LOGIKA TOKOH (LABEL CHARACTER REF DIHAPUS) ---
            char_prompts = []
            if c1_name and c1_name.lower() in v_txt.lower():
                e1 = f"reacting with intense facial muscles to: '{adegan['diag1']}'. " if adegan['diag1'] else ""
                char_prompts.append(f"{c1_name} is described as {c1_base}, wearing {c1_outfit}, in {status_map[adegan['cond1']]}. {e1}")
            if c2_name and c2_name.lower() in v_txt.lower():
                e2 = f"reacting with intense facial muscles to: '{adegan['diag2']}'. " if adegan['diag2'] else ""
                char_prompts.append(f"{c2_name} is described as {c2_base}, wearing {c2_outfit}, in {status_map[adegan['cond2']]}. {e2}")
            
            final_char = " ".join(char_prompts) + " "
            
            # --- KONSTRUKSI PROMPT ---
            is_first_pre = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""
            img_cmd_pre = f"buatkan saya sebuah gambar dari adegan ke {s_id}. "

            final_img = f"{style_lock}{is_first_pre}{img_cmd_pre}{final_char}Visual Scene: {v_txt}. Atmosphere: {f_atmos} Lighting: {f_light}. {img_quality_base}"

            st.subheader(f"ADENGAN {s_id}")
            st.code(final_img, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.35 - Pure Visual Edition")
