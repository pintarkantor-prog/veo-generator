import streamlit as st

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. CUSTOM CSS (TOMBOL COPY HIJAU & TAMPILAN) ---
st.markdown("""
    <style>
    /* Mengubah tombol copy bawaan menjadi Hijau Terang agar mudah terlihat */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; /* Selalu muncul tanpa perlu di-hover */
        border-radius: 6px !important;
        border: 1px solid #ffffff !important;
        transform: scale(1.1); /* Sedikit diperbesar agar jelas */
    }
    /* Warna saat tombol diklik */
    button[title="Copy to clipboard"]:active {
        background-color: #1e7e34 !important;
    }
    /* Styling kotak input agar rapi */
    .stTextArea textarea {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Judul Utama & Pesan Penyemangat
st.title("📸 PINTAR MEDIA")
st.info("semangat buat alur cerita nya guys ❤️❤️❤️")

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

    # Form Jumlah Karakter (Manual di bawah Karakter 2)
    num_chars = st.number_input("Tambah Karakter Lainnya (Total)", min_value=2, max_value=5, value=2)

    if num_chars > 2:
        for j in range(2, int(num_chars)):
            st.divider()
            st.markdown(f"**Karakter {j+1}**")
            cn = st.text_input(f"Nama Karakter {j+1}", key=f"char_name_{j}", placeholder=f"Contoh: TOKOH {j+1}")
            cd = st.text_area(f"Fisik Karakter {j+1}", key=f"char_desc_{j}", placeholder="Ciri fisik...", height=68)
            characters.append({"name": cn, "desc": cd})

# --- 4. PARAMETER KUALITAS NATURAL (Tanpa kata 'Realistic') ---
img_quality = (
    "natural photography, raw photo style, captured on 35mm lens, f/8 aperture, "
    "high resolution, sharp details, authentic skin texture, natural colors, "
    "unprocessed look, NO cartoon, NO anime, NO Pixar, NO 3D render, "
    "NO artificial lighting, NO AI-generated look, true to life appearance"
)

vid_quality = (
    "natural handheld video, 60fps, authentic motion, real-world environment, "
    "clear high definition, raw footage style, NO animation, NO CGI, life-like movement"
)

# --- 5. FORM INPUT ADEGAN ---
st.subheader("📝 Detail Adegan")
scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        # Kolom dinamis: Visual (2) + Waktu (1) + Dialog per karakter (1)
        col_setup = [2, 1] + [1] * len(characters)
        cols = st.columns(col_setup)
        
        with cols[0]:
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"desc_{i}", height=100)
        
        with cols[1]:
            scene_time = st.selectbox(f"Waktu {i}", ["Pagi hari", "Siang hari", "Sore hari", "Malam hari"], key=f"time_{i}")
        
        scene_dialogs = []
        for idx, char in enumerate(characters):
            with cols[idx + 2]:
                char_label = char['name'] if char['name'] else f"Karakter {idx+1}"
                d_input = st.text_input(f"Dialog {char_label}", key=f"diag_{idx}_{i}")
                scene_dialogs.append({"name": char_label, "text": d_input})
        
        scene_data.append({
            "num": i, 
            "desc": user_desc, 
            "time": scene_time,
            "dialogs": scene_dialogs
        })

st.divider()

# --- 6. TOMBOL GENERATE (BUAT PROMPT) ---
if st.button("🚀 BUAT PROMPT", type="primary"):
    # Filter: Hanya memproses adegan yang visualnya tidak kosong
    filled_scenes = [s for s in scene_data if s["desc"].strip() != ""]
    
    if not filled_scenes:
        st.warning("Silakan isi kolom 'Visual Adegan' pada adegan yang ingin diproses.")
    else:
        st.header("📋 Hasil Prompt")
        
        for scene in filled_scenes:
            i = scene["num"]
            v_input = scene["desc"]
            
            # Deteksi Nama Tokoh dalam Visual Adegan (Smart Trigger)
            detected_physique = []
            for char in characters:
                if char['name'] and char['name'].lower() in v_input.lower():
                    detected_physique.append(f"{char['name']} ({char['desc']})")
            
            char_ref = "Characters Appearance: " + ", ".join(detected_physique) + ". " if detected_physique else ""
            
            # Waktu Mapping
            time_map = {
                "Pagi hari": "morning golden hour light",
                "Siang hari": "bright midday natural sunlight",
                "Sore hari": "late afternoon warm sunset lighting",
                "Malam hari": "ambient night lighting, dark environment"
            }
            eng_time = time_map.get(scene["time"], "natural lighting")
            
            # --- PROMPT GAMBAR (Instruksi Indo & No Dialog) ---
            ref_t = "ini adalah gambar referensi karakter saya. " if i == 1 else ""
            mand_t = "saya ingin membuat gambar secara konsisten adegan per adegan. "
            sc_num_t = f"buatkan saya sebuah gambar adegan ke {i}. "
            
            final_img = (
                f"{ref_t}{mand_t}{sc_num_t}\n"
                f"Visual: {char_ref}{v_input}. Waktu: {scene['time']}. "
                f"Lighting: {eng_time}. {img_quality}"
            )

            # --- PROMPT VIDEO (Dialog & No Instruksi Indo) ---
            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            dialog_part = f"\n\nDialog:\n" + "\n".join(dialog_lines) if dialog_lines else ""

            final_vid = (
                f"Generate a natural video for Scene {i}. \n"
                f"Visual: {char_ref}{v_input}. Time context: {eng_time}. {vid_quality}.{dialog_part}"
            )

            # Tampilan Output
            st.subheader(f"Adegan {i}")
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.caption(f"📸 PROMPT GAMBAR")
                st.code(final_img, language="text")
            with res_col2:
                st.caption(f"🎥 PROMPT VIDEO")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v3.0")

