import streamlit as st

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. CUSTOM CSS (TAMPILAN SIDEBAR & TOMBOL HIJAU) ---
st.markdown("""
    <style>
    /* Sidebar Gelap Profesional */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    
    /* Teks Sidebar Putih */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: white !important;
    }

    /* Tombol Copy Hijau Terang */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 1px solid #ffffff !important;
        transform: scale(1.1); 
    }
    
    button[title="Copy to clipboard"]:active {
        background-color: #1e7e34 !important;
    }
    
    .stTextArea textarea {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: Mega Structure - locked Crisp Daylight & Deep Color ❤️")

# --- 3. SIDEBAR: KONFIGURASI TOKOH ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Tokoh")
    
    characters = []

    # Karakter 1
    st.markdown("**Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="Contoh: UDIN")
    c1_desc = st.text_area("Fisik Karakter 1", key="char_desc_0", placeholder="Ciri fisik...", height=68)
    characters.append({"name": c1_name, "desc": c1_desc})
    
    st.divider()

    # Karakter 2
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="Contoh: TUNG")
    c2_desc = st.text_area("Fisik Karakter 2", key="char_desc_1", placeholder="Ciri fisik...", height=68)
    characters.append({"name": c2_name, "desc": c2_desc})

    st.divider()
    num_chars = st.number_input("Tambah Karakter Lainnya", min_value=2, max_value=5, value=2)

    if num_chars > 2:
        for j in range(2, int(num_chars)):
            st.divider()
            st.markdown(f"**Karakter {j+1}**")
            cn = st.text_input(f"Nama Karakter {j+1}", key=f"sidebar_char_name_{j}")
            cd = st.text_area(f"Fisik Karakter {j+1}", key=f"sidebar_char_desc_{j}", height=68)
            characters.append({"name": cn, "desc": cd})

# --- 4. PARAMETER KUALITAS FULL (SANGAT DETAIL & PANJANG) ---
# Mengunci suasana 10:00 AM, Dingin, Kering, dan Tajam di sini
img_quality_standard = (
    "full-frame medium format photography, 16-bit color bit depth, hyper-saturated organic pigments, "
    "edge-to-edge optical sharpness, f/11 deep focus, micro-contrast enhancement, "
    "intricate micro-textures, dry surfaces, dry environment, clear atmosphere, "
    "10:00 AM crisp morning light, deep blue sky with thin wispy white clouds, natural sky depth, "
    "cool white balance, 7000k color temperature, rich color contrast, deep shadows, "
    "unprocessed raw photography, 8k resolution, captured on 35mm lens, "
    "STRICTLY NO rain, NO wet surfaces, NO overcast, NO over-exposure, NO dark clouds"
)

vid_quality_standard = (
    "ultra-high-fidelity vertical video, 60fps, crisp 10:00 AM cold daylight, dry environment, "
    "natural blue sky with light white clouds, deep color depth, extreme visual clarity, "
    "lossless texture quality, fluid organic motion, muted cool light, "
    "high contrast ratio, NO motion blur, NO animation look"
)

# --- 5. FORM INPUT ADEGAN ---
st.subheader("📝 Detail Adegan")
scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        # Layout kolom yang lega karena pilihan waktu dihapus
        col_setup = [3, 1.5] + [1] * len(characters)
        cols = st.columns(col_setup)
        
        with cols[0]:
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"main_desc_{i}", height=100, placeholder="Apa yang terlihat di kamera?")
        
        with cols[1]:
            # Kontrol Intensitas Cahaya (Pilihan yang baru kita tambahkan)
            light_choice = st.radio(f"Lighting Adegan {i}", 
                                    ["50% (Dingin)", "75% (Cerah)"], 
                                    key=f"light_{i}", horizontal=True)
        
        scene_dialogs = []
        for idx, char in enumerate(characters):
            with cols[idx + 2]:
                char_label = char['name'] if char['name'] else f"Karakter {idx+1}"
                d_input = st.text_input(f"Dialog {char_label}", key=f"main_diag_{idx}_{i}")
                scene_dialogs.append({"name": char_label, "text": d_input})
        
        scene_data.append({
            "num": i, "desc": user_desc, "light": light_choice, "dialogs": scene_dialogs
        })

st.divider()

# --- 6. TOMBOL GENERATE (LOGIKA FULL) ---
if st.button("🚀 BUAT PROMPT", type="primary"):
    filled_scenes = [s for s in scene_data if s["desc"].strip() != ""]
    
    if not filled_scenes:
        st.warning("Silakan isi setidaknya satu kolom 'Visual Adegan'.")
    else:
        st.header("📋 Hasil Prompt")
        
        for scene in filled_scenes:
            i = scene["num"]
            v_in = scene["desc"]
            
            # 1. Logika Lighting Terperinci
            if "50%" in scene["light"]:
                light_val = "50% dimmed sunlight intensity, zero glare, crisp cool morning air, muted exposure"
            else:
                light_val = "75% sunlight intensity, brilliant daylight, vivid highlights, high-energy sharp colors"

            # 2. Logika Otomatis Adegan 1
            ref_prefix = "ini adalah referensi gambar karakter pada adegan per adegan. " if i == 1 else ""
            img_command = f"buatkan saya sebuah gambar dari adegan ke {i}. "

            # 3. Logika Ekspresi Otomatis dari Dialog
            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            d_text = " ".join(dialog_lines) if dialog_lines else ""
            
            expr_logic = ""
            if d_text:
                expr_logic = f"Emotion Analysis: Analyze mood from '{d_text}'. Apply realistic facial micro-expressions and muscle tension. "

            # 4. Logika Pengecekan Karakter Manual (Agar Akurat)
            phys_list = []
            if characters[0]['name'] and characters[0]['name'].lower() in v_in.lower():
                phys_list.append(f"{characters[0]['name']} ({characters[0]['desc']})")
            
            if characters[1]['name'] and characters[1]['name'].lower() in v_in.lower():
                phys_list.append(f"{characters[1]['name']} ({characters[1]['desc']})")
            
            # Jika ada karakter tambahan (3, 4, 5)
            if len(characters) > 2:
                for extra_char in characters[2:]:
                    if extra_char['name'] and extra_char['name'].lower() in v_in.lower():
                        phys_list.append(f"{extra_char['name']} ({extra_char['desc']})")
            
            char_ref = "Appearance: " + ", ".join(phys_list) + ". " if phys_list else ""
            
            # --- KONSTRUKSI PROMPT GAMBAR (FULL) ---
            final_img = (
                f"{ref_prefix}{img_command}{expr_logic}Visual: {char_ref}{v_in}. "
                f"Atmosphere: 10:00 AM Locked, dry environment, wispy white clouds. "
                f"Lighting: {light_val}. {img_quality_standard}"
            )

            # --- KONSTRUKSI PROMPT VIDEO (FULL) ---
            final_vid = (
                f"Video Adegan {i}. {expr_logic}Visual: {char_ref}{v_in}. "
                f"Atmosphere: 10:00 AM Locked, clear blue sky, dry surfaces. "
                f"Lighting: {light_val}. {vid_quality_standard}. Dialog: {d_text}"
            )

            st.subheader(f"Adegan {i}")
            res_c1, res_c2 = st.columns(2)
            with res_c1:
                st.caption("📸 PROMPT GAMBAR")
                st.code(final_img, language="text")
            with res_c2:
                st.caption("🎥 PROMPT VIDEO")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v7.1 - Mega Structure Locked Time")
