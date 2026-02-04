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
# 2. CUSTOM CSS (FULL STYLE NO REFACTORED)
# ==========================================
st.markdown("""
    <style>
    /* Mengatur latar belakang sidebar menjadi gelap */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    
    /* Mengatur warna teks di sidebar agar putih bersih */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }

    /* Mengatur tombol copy khusus agar berwarna hijau terang */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 2px solid #ffffff !important;
        transform: scale(1.1); 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    
    /* Efek saat tombol copy ditekan */
    button[title="Copy to clipboard"]:active {
        background-color: #1e7e34 !important;
        transform: scale(1.0);
    }
    
    /* Mengatur ukuran font di area teks */
    .stTextArea textarea {
        font-size: 14px !important;
        font-family: 'Inter', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: MEGA STRUCTURE - Hyper Fidelity, No Text, Locked 10 AM Daylight ❤️")

# ==========================================
# 3. SIDEBAR: KONFIGURASI TOKOH (MANUAL SETUP)
# ==========================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    # List untuk menampung data karakter
    characters_data = []

    # Setup Karakter 1 secara eksplisit
    st.markdown("### Karakter 1")
    char1_name = st.text_input("Nama Karakter 1", key="c_name_1", placeholder="Contoh: UDIN")
    char1_physic = st.text_area("Deskripsi Fisik 1", key="c_desc_1", placeholder="Contoh: Kepala jeruk orange, baju denim...", height=70)
    characters_data.append({"name": char1_name, "desc": char1_physic})
    
    st.divider()

    # Setup Karakter 2 secara eksplisit
    st.markdown("### Karakter 2")
    char2_name = st.text_input("Nama Karakter 2", key="c_name_2", placeholder="Contoh: TUNG")
    char2_physic = st.text_area("Deskripsi Fisik 2", key="c_desc_2", placeholder="Contoh: Kepala kayu log, baju cokelat...", height=70)
    characters_data.append({"name": char2_name, "desc": char2_physic})

    st.divider()
    
    # Input untuk jumlah karakter tambahan
    extra_chars_count = st.number_input("Tambah Karakter Lain", min_value=2, max_value=5, value=2)

    # Logika penambahan karakter ekstra jika lebih dari 2
    if extra_chars_count > 2:
        for extra_idx in range(2, int(extra_chars_count)):
            st.divider()
            st.markdown(f"### Karakter {extra_idx + 1}")
            extra_name = st.text_input(f"Nama Karakter {extra_idx + 1}", key=f"ex_name_{extra_idx}")
            extra_desc = st.text_area(f"Fisik Karakter {extra_idx + 1}", key=f"ex_desc_{extra_idx}", height=70)
            characters_data.append({"name": extra_name, "desc": extra_desc})

# ==========================================
# 4. PARAMETER KUALITAS (FULL LIST - NO REFACTORING)
# ==========================================
# Perintah negatif untuk memblokir teks dan balon kata secara total
negative_instruction = "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters, NO words on image, NO user interface."

# Parameter Kualitas Gambar (Sangat Detail)
img_quality_full = (
    "full-frame medium format photography style, 16-bit color bit depth, hyper-saturated organic pigments, "
    "edge-to-edge optical sharpness, f/11 deep focus aperture, micro-contrast enhancement, "
    "intricate micro-textures on every surface, dry surfaces, dry environment, clear atmosphere visibility, "
    "10:00 AM morning crisp light, deep blue sky, thin wispy white clouds, natural sky depth, "
    "cool white balance, 7000k color temperature, rich color contrast, deep shadows, "
    "unprocessed raw photography, 8k resolution, captured on 35mm high-end lens, "
    "STRICTLY NO rain, NO wet surfaces, NO overcast sky, NO over-exposure, NO sun flare, " + negative_instruction
)

# Parameter Kualitas Video (Sangat Detail)
vid_quality_full = (
    "ultra-high-fidelity vertical video format, 9:16 aspect ratio, 60fps, crisp 10:00 AM cold daylight, "
    "dry environment landscape, natural blue sky with light wispy clouds, deep color depth, extreme visual clarity, "
    "lossless texture quality, fluid organic motion, muted cool lighting, "
    "high contrast ratio, NO motion blur, NO animation look, NO CGI look, " + negative_instruction
)

# ==========================================
# 5. FORM INPUT ADEGAN (FULL LAYOUT)
# ==========================================
st.subheader("📝 Detail Adegan Storyboard")
final_scene_storage = []

for scene_num in range(1, int(num_scenes) + 1):
    with st.expander(f"KONFIGURASI DATA ADEGAN {scene_num}", expanded=(scene_num == 1)):
        # Membuat kolom-kolom untuk input visual, lighting, dan dialog karakter
        scene_cols = st.columns([3, 1.8] + [1.2] * len(characters_data))
        
        with scene_cols[0]:
            visual_desc = st.text_area(f"Visual Adegan {scene_num}", key=f"v_desc_{scene_num}", height=110, placeholder="Tulis aksi dan latar belakang di sini...")
        
        with scene_cols[1]:
            # Pilihan lighting sesuai permintaan: 50% vs 75%
            lighting_val = st.radio(f"Lighting {scene_num}", 
                                    ["50% (Dingin & Kristal)", "75% (Cerah & Tajam)"], 
                                    key=f"l_val_{scene_num}", horizontal=True)
        
        # Input dialog untuk setiap karakter yang sudah didaftarkan
        current_scene_dialogs = []
        for char_idx, char_info in enumerate(characters_data):
            with scene_cols[char_idx + 2]:
                display_label = char_info['name'] if char_info['name'] else f"Tokoh {char_idx + 1}"
                dialog_input = st.text_input(f"Dialog {display_label}", key=f"diag_{char_idx}_{scene_num}")
                current_scene_dialogs.append({"name": display_label, "text": dialog_input})
        
        final_scene_storage.append({
            "id": scene_num, 
            "visual": visual_desc, 
            "lighting": lighting_val, 
            "dialogs": current_scene_dialogs
        })

st.divider()

# ==========================================
# 6. LOGIKA GENERATOR PROMPT (FULL LOGIC)
# ==========================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    # Filter hanya adegan yang sudah diisi visualnya
    valid_scenes = [s for s in final_scene_storage if s["visual"].strip() != ""]
    
    if not valid_scenes:
        st.warning("Mohon isi deskripsi visual terlebih dahulu.")
    else:
        st.header("📋 Hasil Produksi Prompt")
        
        for scene in valid_scenes:
            s_id = scene["id"]
            v_input = scene["visual"]
            
            # Penentuan Nilai Lighting secara eksplisit
            if "50%" in scene["lighting"]:
                lighting_final_str = "50% dimmed sunlight intensity, zero sun glare, crisp cool atmosphere, muted exposure balance"
            else:
                lighting_final_str = "75% sunlight intensity, brilliant clear daylight, vivid highlights on edges, high-energy sharp colors"

            # Logika Otomatis untuk Adegan 1 (Referensi Karakter)
            prefix_logic = "ini adalah referensi gambar karakter pada adegan per adegan. " if s_id == 1 else ""
            command_logic = f"buatkan saya sebuah gambar dari adegan ke {s_id}. "

            # Logika Emosi dari Dialog (Anti-Text Lock)
            dialog_list = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            combined_dialog = " ".join(dialog_list) if dialog_list else ""
            
            emotion_logic = ""
            if combined_dialog:
                # Instruksi tegas agar dialog hanya jadi referensi emosi, bukan teks di gambar
                emotion_logic = (
                    f"Emotion Context (DO NOT RENDER TEXT ON IMAGE): The characters are reacting to this dialogue: '{combined_dialog}'. "
                    "Apply realistic facial micro-expressions, muscle tension, and eye focus based on the mood. "
                )

            # Logika Sinkronisasi Fisik Karakter secara manual
            active_physic_list = []
            for c_data in characters_data:
                if c_data['name'] and c_data['name'].lower() in v_input.lower():
                    active_physic_list.append(f"{c_data['name']} ({c_data['desc']})")
            
            appearance_str = "Appearance Reference: " + ", ".join(active_physic_list) + ". " if active_physic_list else ""
            
            # --- PERAKITAN PROMPT GAMBAR ---
            prompt_gambar_final = (
                f"{prefix_logic}{command_logic}{emotion_logic}Visual Scene: {appearance_str}{v_input}. "
                f"Atmosphere: 10:00 AM morning sun, dry environment, thin wispy white clouds. "
                f"Lighting Effect: {lighting_final_str}. {img_quality_full}"
            )

            # --- PERAKITAN PROMPT VIDEO ---
            prompt_video_final = (
                f"Video Adegan {s_id}. {emotion_logic}Visual Scene: {appearance_str}{v_input}. "
                f"Atmosphere: 10:00 AM, crystal clear blue sky, dry surfaces. "
                f"Lighting Effect: {lighting_final_str}. {vid_quality_full}. Dialog Reference: {combined_dialog}"
            )

            # Menampilkan hasil ke layar
            st.subheader(f"ADENGAN {s_id}")
            col_res1, col_res2 = st.columns(2)
            
            with col_res1:
                st.caption("📸 PROMPT GAMBAR (Locked 10 AM & No Text)")
                st.code(prompt_gambar_final, language="text")
            
            with col_res2:
                st.caption("🎥 PROMPT VIDEO (Locked 10 AM & No Text)")
                st.code(prompt_video_final, language="text")
            
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v7.3 - The Ultimate Mega-Code")
