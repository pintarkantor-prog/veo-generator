import streamlit as st

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MEGA ARCHITECTURE)
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. CUSTOM CSS (STRICT PROFESSIONAL STYLE)
# ==============================================================================
st.markdown("""
    <style>
    /* Latar Belakang Sidebar */
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff !important; }
    
    /* Tombol Copy Hijau Ikonik */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important; color: white !important;
        opacity: 1 !important; border-radius: 6px !important; border: 2px solid #ffffff !important;
        transform: scale(1.1); box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    
    /* Input Area Styling */
    .stTextArea textarea { 
        font-size: 14px !important; 
        line-height: 1.5 !important; 
        font-family: 'Inter', sans-serif !important; 
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.28 | MEGA ARCHITECTURE | STABLE SYNC | NO REDUCTION ❤️")

# ==============================================================================
# 3. SIDEBAR: KONFIGURASI KARAKTER & GLOBAL STYLE
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🎬 Visual Tone Lock")
    tone_style = st.selectbox("Pilih Gaya Visual", 
                             ["None", "Gritty Cinematic", "Vibrant Pop", "High-End Documentary", "Vintage Film 35mm", "Dark Thriller", "Surreal Dreamy"])
    
    st.divider()
    st.subheader("☁️ Pencahayaan Global")
    global_light = st.selectbox("Set Pencahayaan Global", 
                               ["Manual per Adegan", "Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"])

    st.divider()
    st.subheader("👥 Identitas Karakter")
    
    # Karakter 1
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Karakter 1", value="UDIN", key="c1_name_28")
    c1_phys = st.text_area("Fisik Karakter 1 (Detail)", placeholder="Contoh: Kepala jeruk orange, tekstur pori-pori tajam...", height=90, key="c1_phys_28")
    
    st.divider()
    
    # Karakter 2
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Karakter 2", value="TUNG", key="c2_name_28")
    c2_phys = st.text_area("Fisik Karakter 2 (Detail)", placeholder="Contoh: Kepala kayu balok, serat kayu kasar...", height=90, key="c2_phys_28")

# ==============================================================================
# 4. KUALITAS FOTOGRAFI (ABSOLUTE MAXIMUM - NO REDUCTION)
# ==============================================================================
no_text_lock = (
    "STRICTLY NO rain, NO puddles, NO raindrops, NO wet ground, NO water droplets, "
    "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters."
)

img_quality_base = (
    "photorealistic surrealism style, 16-bit color bit depth, hyper-saturated organic pigments, "
    "absolute fidelity to unique character reference, edge-to-edge optical sharpness, "
    "f/11 deep focus aperture, micro-contrast enhancement, intricate micro-textures on every surface, "
    "circular polarizer (CPL) filter effect, zero atmospheric haze, "
    "rich high-contrast shadows, unprocessed raw photography, 8k resolution, captured on high-end 35mm lens, "
    "STRICTLY NO over-exposure, NO motion blur, NO lens flare, " + no_text_lock
)

# ==============================================================================
# 5. FORM INPUT ADEGAN (STRICT CHARACTER SYNC)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {idx_s}", expanded=(idx_s == 1)):
        cols_input = st.columns([5, 2, 1.5, 1.5])
        
        with cols_input[0]:
            vis_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_28_{idx_s}", height=150)
        
        with cols_input[1]:
            if global_light != "Manual per Adegan":
                l_idx = options_lighting.index(global_light)
                l_val = st.radio(f"Pencahayaan {idx_s}", options_lighting, index=l_idx, key=f"l_28_{idx_s}")
            else:
                l_val = st.radio(f"Pencahayaan {idx_s}", options_lighting, key=f"l_man_28_{idx_s}")
        
        with cols_input[2]:
            st.markdown(f"**{c1_name}**")
            diag_c1 = st.text_input(f"Dialog {c1_name}", key=f"d1_28_{idx_s}")
        
        with cols_input[3]:
            st.markdown(f"**{c2_name}**")
            diag_c2 = st.text_input(f"Dialog {c2_name}", key=f"d2_28_{idx_s}")
        
        adegan_storage.append({
            "num": idx_s, "visual": vis_in, "lighting": l_val, 
            "d1": diag_c1, "d2": diag_c2
        })

# ==============================================================================
# 6. LOGIKA GENERATOR PROMPT (FULL EXPLICIT INSTRUCTION)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        for adegan in active_adegan:
            # Mapping Cahaya Secara Detail
            l_type = adegan["lighting"]
            if l_type == "Mendung":
                f_l = "Intense moody overcast lighting, vivid pigment recovery, extreme local micro-contrast."
                f_a = "8000k ice-cold brilliance, gray-cobalt sky with heavy thick wispy clouds, zero haze."
            elif l_type == "Suasana Malam":
                f_l = "Hyper-Chrome Fidelity lighting, ultra-intense HMI studio illumination, extreme micro-shadows."
                f_a = "Pure vacuum-like atmosphere, 10000k ultra-cold industrial white light."
            else:
                f_l, f_a = f"{l_type} lighting", f"{l_type} atmosphere"

            # Logika Deteksi Karakter
            char_refs = []
            if c1_name and c1_name.lower() in adegan["visual"].lower():
                e1 = f"Expression reacting to: '{adegan['d1']}'. " if adegan['d1'] else ""
                char_refs.append(f"STRICT CHARACTER APPEARANCE: {c1_name} ({c1_phys}). {e1}")
            
            if c2_name and c2_name.lower() in adegan["visual"].lower():
                e2 = f"Expression reacting to: '{adegan['d2']}'. " if adegan['d2'] else ""
                char_refs.append(f"STRICT CHARACTER APPEARANCE: {c2_name} ({c2_phys}). {e2}")
            
            final_character_str = " ".join(char_refs)
            style_lock = f"Overall Visual Tone: {tone_style}. " if tone_style != "None" else ""

            # --- KALIMAT SAKTI (CORE INSTRUCTION) ---
            is_first_pre = "ini adalah referensi gambar karakter pada adegan per adegan. " if adegan['num'] == 1 else ""
            img_cmd_pre = f"buatkan saya sebuah gambar dari adegan ke {adegan['num']}. "

            st.subheader(f"ADENGAN {adegan['num']}")
            st.code(f"{style_lock}{is_first_pre}{img_cmd_pre}{final_character_str} Visual Scene: {adegan['visual']}. Atmosphere: {f_a} Lighting: {f_l}. {img_quality_base}")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.28 - Stable Architecture Edition")
