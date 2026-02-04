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
# 2. CUSTOM CSS (STRICT STYLE - NO REDUCTION)
# ==============================================================================
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff !important; }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important; color: white !important;
        opacity: 1 !important; border-radius: 6px !important; border: 2px solid #ffffff !important;
        transform: scale(1.1); box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    .stTextArea textarea { font-size: 14px !important; line-height: 1.5 !important; font-family: 'Inter', sans-serif !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.39 | PURE VISUAL FOCUS | NO EMOTION/DIALOGUE INPUT | VEO 3 READY ❤️")

# ==============================================================================
# 3. SIDEBAR: IDENTITAS KARAKTER (REFERENSI GAMBAR)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🎬 Estetika Visual")
    tone_style = st.selectbox("Pilih Visual Tone", 
                             ["None", "Gritty Cinematic", "Vibrant Pop", "High-End Documentary", "Vintage Film 35mm", "Dark Thriller", "Surreal Dreamy"])

    st.divider()
    st.subheader("👥 Karakter (Ikuti Gambar Referensi)")
    
    all_characters = []
    # Karakter 1 (UDIN)
    st.markdown("### Karakter 1")
    c1_name = st.text_input("Nama Karakter 1", value="", key="c1_n_39")
    c1_phys = st.text_area("Fisik Karakter 1 (Gunakan Detail dari Gambar)", placeholder="Input detail spesifik dari gambar referensi untuk menjaga kemiripan...", height=90, key="c1_f_39")
    c1_wear = st.text_input("Pakaian 1", placeholder="Sesuai gambar...", key="c1_w_39")
    all_characters.append({"name": c1_name, "phys": c1_phys, "wear": c1_wear})
    
    st.divider()
    # Karakter 2 (TUNG)
    st.markdown("### Karakter 2")
    c2_name = st.text_input("Nama Karakter 2", value="", key="c2_n_39")
    c2_phys = st.text_area("Fisik Karakter 2 (Gunakan Detail dari Gambar)", placeholder="Input detail spesifik dari gambar referensi untuk menjaga kemiripan...", height=90, key="c2_f_39")
    c2_wear = st.text_input("Pakaian 2", placeholder="Sesuai gambar...", key="c2_w_39")
    all_characters.append({"name": c2_name, "phys": c2_phys, "wear": c2_wear})

# ==============================================================================
# 4. PARAMETER KUALITAS (STRICT ANTI-TEXT & FIDELITY)
# ==============================================================================
# KEBIJAKAN NOL TEKS (ZERO TEXT POLICY)
zero_text_policy = (
    "STRICTLY NO speech bubbles, NO text, NO letters, NO subtitles, NO captions, NO watermark, "
    "NO dialogue boxes, NO labels, NO typography, NO on-screen text, NO written words. "
    "The frame is 100% clean and pure visual content, without any textual overlays."
)

img_quality = (
    "photorealistic surrealism, 16-bit color, extreme fidelity to provided visual reference, "
    "edge-to-edge optical sharpness, f/11 deep focus, macro-textures, 8k resolution, " + zero_text_policy
)

veo_quality = (
    "cinematic video, high-fidelity motion, 60fps, 4k, organic character movement, "
    "strict consistency with provided visual reference, fluid interaction, lossless textures, " + zero_text_policy
)

# ==============================================================================
# 5. FORM INPUT ADEGAN (NO EMOTION/DIALOGUE INPUT)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
options_cond = ["Normal/Bersih", "Sedih", "Lusuh", "Marah", "Hancur Parah"] # Opsi kondisi disederhanakan

for idx_s in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI ADEGAN {idx_s}", expanded=(idx_s == 1)):
        v_col, l_col = st.columns([3, 1])
        with v_col:
            v_in = st.text_area(f"Visual Scene {idx_s}", key=f"vis_{idx_s}", height=120)
        with l_col:
            l_val = st.radio(f"Cahaya {idx_s}", options_lighting, key=f"l_{idx_s}")

        st.markdown("**Kondisi Karakter (Visual Saja)**")
        c_data = []
        char_cols = st.columns(len(all_characters))
        for i, char in enumerate(all_characters):
            with char_cols[i]:
                name = char['name'] if char['name'] else f"K{i+1}"
                co = st.selectbox(f"Kondisi {name}", options_cond, key=f"co_{i}_{idx_s}")
                c_data.append({"cond": co}) # Hanya kondisi, dialog dihapus
        
        adegan_storage.append({"num": idx_s, "visual": v_in, "light": l_val, "chars": c_data})

# ==============================================================================
# 6. GENERATOR PROMPT (IMAGE & VEO 3)
# ==============================================================================
if st.button("🚀 GENERATE PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    for adegan in active:
        s_id = adegan["num"]
        
        # Lighting Mapping (tetap lengkap)
        if adegan["light"] == "Mendung":
            f_l = "Intense moody overcast lighting with 16-bit color depth fidelity, vivid pigment recovery, extreme local micro-contrast."
            f_a = "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on every surface."
        elif adegan["light"] == "Bening dan Tajam":
            f_l = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
            f_a = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
        elif adegan["light"] == "Sejuk dan Terang":
            f_l = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
            f_a = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
        elif adegan["light"] == "Dramatis":
            f_l = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
            f_a = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
        elif adegan["light"] == "Jelas dan Solid":
            f_l = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
            f_a = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
        elif adegan["light"] == "Suasana Sore":
            f_l = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
            f_a = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background, zero atmospheric haze."
        elif adegan["light"] == "Suasana Malam":
            f_l = "Hyper-Chrome Fidelity lighting, ultra-intense HMI studio lamp illumination, extreme micro-shadows on all textures, brutal contrast ratio, specular highlight glints on every edge, zero-black floor depth."
            f_a = "Pure vacuum-like atmosphere, zero light scattering, absolute visual bite, chrome-saturated pigments, hyper-defined micro-pores and wood grain textures, 10000k ultra-cold industrial white light."
        elif adegan["light"] == "Suasana Alami":
            f_l = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments, deep rich micro-shadows within foliage and soil textures."
            f_a = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures on every grass blade and soil particle, high-fidelity natural contrast across the entire frame, 5000k neutral soft-sun brilliance."
        else: f_l, f_a = f"{adegan['light']} lighting", f"{adegan['light']} atmosphere"

        # Character Instruction (Based on Image Reference - No Emotion/Dialogue)
        char_prompts = []
        status_map = {
            "Normal/Bersih": "pristine condition, neutral expression.", "Sedih": "sad facial expression, downcast eyes.",
            "Lusuh": "worn-out look, dusty appearance.", "Marah": "angry facial expression, tensed muscles.",
            "Hancur Parah": "heavily damaged textures on head surface, broken elements."
        }

        for i, char in enumerate(all_characters):
            if char['name'] and char['name'].lower() in adegan['visual'].lower():
                # Ekspresi kini langsung dari kondisi, tidak ada lagi dari dialog
                condition_desc = status_map[adegan['chars'][i]['cond']]
                char_prompts.append(f"Follow the exact visual appearance of {char['name']} from reference: {char['phys']}, wearing {char['wear']}, in {condition_desc}.")

        final_c = " ".join(char_prompts)
        style_lock = f"Visual Tone: {tone_style}. " if tone_style != "None" else ""
        is_ref = "Gunakan gambar ini sebagai referensi karakter utama. " if s_id == 1 else ""
        
        # PROMPT GAMBAR
        final_img = f"{style_lock}{is_ref}Buatkan gambar adegan {s_id}: {final_c} Visual Scene: {adegan['visual']}. Atmosphere: {f_a}. Lighting: {f_l}. {img_quality}"
        
        # PROMPT VEO 3
        final_veo = f"{style_lock}Video adegan {s_id}: {final_c} Visual Scene: {adegan['visual']}, showing organic cinematic movement and fluid interaction. Atmosphere: {f_a}. Lighting: {f_l}. {veo_quality}"

        st.subheader(f"ADENGAN {s_id}")
        st.write("**📸 Image Prompt:**")
        st.code(final_img, language="text")
        st.write("**🎥 Veo 3 Prompt:**")
        st.code(final_veo, language="text")
        st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.39 - Pure Visual Focus")
