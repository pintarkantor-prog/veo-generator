import streamlit as st

# ==========================================
# 1. KONFIGURASI HALAMAN (FULL SETUP)
# ==========================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. CUSTOM CSS (MANUAL & FULL MEGA STRUCTURE)
# ==========================================
st.markdown("""
    <style>
    /* Mengatur latar belakang sidebar menjadi sangat gelap */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    
    /* Mengatur semua teks di sidebar agar berwarna putih terang */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }

    /* Mengatur tampilan tombol Copy khusus (Warna Hijau Terang) */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 2px solid #ffffff !important;
        transform: scale(1.1); 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.4);
    }
    
    /* Efek hover/tekan pada tombol Copy */
    button[title="Copy to clipboard"]:active {
        background-color: #1e7e34 !important;
        transform: scale(1.0);
    }
    
    /* Mengatur font pada area input teks adegan */
    .stTextArea textarea {
        font-size: 14px !important;
        font-family: 'Inter', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: ULTRA-VIVID COBALT & AUTO-SYNC CHARACTER IDENTITY ❤️")

# ==========================================
# 3. SIDEBAR: KONFIGURASI TOKOH (MEGA SETUP)
# ==========================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    # Penampung data karakter (Mega List)
    all_characters = []

    # Setup Karakter 1 secara Eksplisit
    st.markdown("### Karakter 1")
    char1_name = st.text_input("Nama Karakter 1", key="input_c_name_1", placeholder="Contoh: UDIN")
    char1_physic = st.text_area("Fisik Karakter 1", key="input_c_desc_1", placeholder="Detail fisik...", height=70)
    all_characters.append({"name": char1_name, "desc": char1_physic})
    
    st.divider()

    # Setup Karakter 2 secara Eksplisit
    st.markdown("### Karakter 2")
    char2_name = st.text_input("Nama Karakter 2", key="input_c_name_2", placeholder="Contoh: TUNG")
    char2_physic = st.text_area("Fisik Karakter 2", key="input_c_desc_2", placeholder="Detail fisik...", height=70)
    all_characters.append({"name": char2_name, "desc": char2_physic})

    st.divider()
    
    # Menentukan jumlah karakter tambahan secara dinamis
    extra_count = st.number_input("Tambah Karakter Lainnya", min_value=2, max_value=5, value=2)

    # Input Karakter 3, 4, 5 (Jika dipilih)
    if extra_count > 2:
        for ex_i in range(2, int(extra_count)):
            st.divider()
            st.markdown(f"### Karakter {ex_i + 1}")
            ex_name = st.text_input(f"Nama Karakter {ex_i + 1}", key=f"ex_name_input_{ex_i}")
            ex_desc = st.text_area(f"Fisik Karakter {ex_i + 1}", key=f"ex_desc_input_{ex_i}", height=70)
            all_characters.append({"name": ex_name, "desc": ex_desc})

# ==========================================
# 4. PARAMETER KUALITAS (FULL MEGA LIST)
# ==========================================
no_text_strict = "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters, NO words on image, NO user interface labels."

# Variabel Kualitas Gambar (Ultra-Sharp & Cold)
img_quality_vivid_sharp = (
    "full-frame medium format photography, 16-bit color bit depth, hyper-saturated organic pigments, "
    "edge-to-edge optical sharpness, f/11 deep focus aperture, micro-contrast enhancement, "
    "circular polarizer (CPL) filter effect to darken blue sky and enhance saturation, "
    "deep cobalt blue sky, small wispy natural white clouds, natural sky depth, "
    "intricate micro-textures on foliage and tree barks, hyper-sharp vegetation, "
    "dry surfaces, dry environment, zero atmospheric haze, crystal clear visibility, "
    "10:00 AM morning crisp daylight, 50% sun intensity, cool white balance, 7000k cold color temperature, "
    "rich high-contrast shadows, unprocessed raw photography style, 8k resolution, captured on 35mm high-end lens, "
    "STRICTLY NO rain, NO wet surfaces, NO overcast sky, NO over-exposure, NO sun flare, " + no_text_strict
)

# Variabel Kualitas Video (Ultra-Sharp & Cold)
vid_quality_vivid_sharp = (
    "ultra-high-fidelity vertical video format, 9:16 aspect ratio, 60fps, crisp 10:00 AM cold daylight, "
    "deep saturated colors, deep cobalt blue sky, natural light white clouds, "
    "hyper-sharp background focus, sharp foliage and grass textures, dry landscape environment, "
    "extreme visual clarity, lossless texture quality, fluid organic motion, muted cool lighting, "
    "high contrast ratio, NO motion blur, NO animation look, NO CGI look, " + no_text_strict
)

# ==========================================
# 5. FORM INPUT ADEGAN (FULL LAYOUT)
# ==========================================
st.subheader("📝 Detail Adegan Storyboard")
scenes_list = []

for s_num in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {s_num}", expanded=(s_num == 1)):
        # Layout Kolom Manual
        layout_cols = st.columns([3, 1.8] + [1.2] * len(all_characters))
        
        with layout_cols[0]:
            visual_input = st.text_area(f"Visual Adegan {s_num}", key=f"main_v_input_{s_num}", height=110, placeholder="Contoh: UDIN dan TUNG sedang berjalan di hutan...")
        
        with layout_cols[1]:
            light_val_radio = st.radio(f"Lighting {s_num}", ["50% (Dingin)", "75% (Cerah)"], key=f"main_l_input_{s_num}", horizontal=True)
        
        # Penampung Dialog Per Karakter
        scene_dialogs_data = []
        for c_idx, c_info in enumerate(all_characters):
            with layout_cols[c_idx + 2]:
                char_label_name = c_info['name'] if c_info['name'] else f"Tokoh {c_idx + 1}"
                diag_input_text = st.text_input(f"Dialog {char_label_name}", key=f"main_diag_input_{c_idx}_{s_num}")
                scene_dialogs_data.append({"name": char_label_name, "text": diag_input_text})
        
        scenes_list.append({
            "num": s_num, 
            "visual": visual_input, 
            "lighting": light_val_radio, 
            "dialogs": scene_dialogs_data
        })

st.divider()

# ==========================================
# 6. LOGIKA GENERATOR PROMPT (AUTO-SYNC CHARACTER)
# ==========================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_scenes = [s for s in scenes_list if s["visual"].strip() != ""]
    
    if not active_scenes:
        st.warning("Mohon isi deskripsi visual adegan.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        
        for scene in active_scenes:
            id_scene = scene["num"]
            v_text = scene["visual"]
            
            # 1. Logic Lighting Eksplisit
            if "50%" in scene["lighting"]:
                final_lighting_prompt = "50% dimmed sunlight intensity, zero sun glare, crisp cool morning air, muted exposure, sharp contrast shadows"
            else:
                final_lighting_prompt = "75% sunlight intensity, brilliant clear daylight, vivid highlights, high-energy sharp colors"

            # 2. Logika Emosi Dialog (Anti-Text)
            current_dialog_list = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            full_dialog_string = " ".join(current_dialog_list) if current_dialog_list else ""
            
            emotion_instruction = ""
            if full_dialog_string:
                emotion_instruction = (
                    f"Emotion Context (DO NOT RENDER TEXT): Reacting to dialogue context: '{full_dialog_string}'. "
                    "Focus on realistic facial micro-expressions and muscle tension. "
                )

            # 3. FUNGSI OTOMATIS: CHARACTER IDENTITY SYNC (Penting!)
            # Memeriksa semua karakter (1 s/d 5) apakah ada di deskripsi visual adegan
            final_appearance_ref = ""
            detected_chars_physic = []
            
            for check_char in all_characters:
                # Jika nama karakter diisi DAN nama tersebut tertulis di deskripsi visual adegan (case insensitive)
                if check_char['name'] and check_char['name'].lower() in v_text.lower():
                    detected_chars_physic.append(f"{check_char['name']} ({check_char['desc']})")
            
            # Jika ada karakter yang terdeteksi, masukkan ke dalam prompt
            if detected_chars_physic:
                final_appearance_ref = "Character Identity Reference: " + ", ".join(detected_chars_physic) + ". "

            # 4. Perakitan Prompt (Mega Construction)
            is_first_scene_prefix = "ini adalah referensi gambar karakter pada adegan per adegan. " if id_scene == 1 else ""
            command_image_prefix = f"buatkan saya sebuah gambar dari adegan ke {id_scene}. "

            image_prompt_result = (
                f"{is_first_scene_prefix}{command_image_prefix}{emotion_instruction}Visual Scene: {final_appearance_ref}{v_text}. "
                f"Atmosphere: Locked 10:00 AM morning sun, deep cobalt blue sky, thin wispy white clouds, dry landscape, hyper-sharp vegetation. "
                f"Lighting Effect: {final_lighting_prompt}. {img_quality_vivid_sharp}"
            )

            video_prompt_result = (
                f"Video Adegan {id_scene}. {emotion_instruction}Visual Scene: {final_appearance_ref}{v_text}. "
                f"Atmosphere: 10:00 AM, crystal clear deep blue sky, hyper-vivid background, dry surfaces. "
                f"Lighting Effect: {final_lighting_prompt}. {vid_quality_vivid_sharp}. Dialog Reference: {full_dialog_string}"
            )

            # 5. Output Display
            st.subheader(f"ADENGAN {id_scene}")
            res_col_1, res_col_2 = st.columns(2)
            with res_col_1:
                st.caption("📸 PROMPT GAMBAR (Sync Active)")
                st.code(image_prompt_result, language="text")
            with res_col_2:
                st.caption("🎥 PROMPT VIDEO (Sync Active)")
                st.code(video_prompt_result, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v7.6 - Ultimate Character Sync")
