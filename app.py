import streamlit as st

st.set_page_config(page_title="Natural Storyboard Generator", layout="wide")

st.title("📸 Natural Storyboard Generator")
st.info("Isi detail adegan, tentukan waktunya, lalu klik **'BUAT PROMPT'** untuk melihat hasilnya.")

# --- SIDEBAR: PENGATURAN GLOBAL ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🖼️ Referensi Karakter")
    uploaded_file = st.file_uploader("Unggah Gambar Referensi", type=["jpg", "jpeg", "png"])
    
    char_global_desc = st.text_area("Deskripsi Fisik Karakter (Global)", 
                                    placeholder="Contoh: Pria wajah lokal, kulit sawo matang, rambut pendek rapi.")

    st.divider()
    st.subheader("👥 Nama Tokoh")
    # Bagian Default Nama dikosongkan agar Anda bisa isi manual
    char_a_name = st.text_input("Nama Karakter A", value="", placeholder="Isi Nama Karakter A")
    char_b_name = st.text_input("Nama Karakter B", value="", placeholder="Isi Nama Karakter B")
    char_c_name = st.text_input("Nama Karakter C", value="", placeholder="Isi Nama Karakter C")

# --- PARAMETER KUALITAS NATURAL ---
img_quality = (
    "hyper-realistic natural photography, raw photo, captured on 35mm lens, f/8 aperture, "
    "high resolution, sharp details, realistic skin texture, authentic colors, "
    "NO cartoon, NO anime, NO Pixar, NO 3D render, NO artificial lighting, NO AI-generated look"
)

vid_quality = (
    "natural handheld video, 60fps, realistic motion, authentic environment, "
    "clear high definition, real-life footage style, NO animation, NO CGI"
)

# --- FORM INPUT ---
st.subheader("📝 Detail Adegan")
scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        col_desc, col_time, col_diag_a, col_diag_b, col_diag_c = st.columns([2, 1, 1, 1, 1])
        
        with col_desc:
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"desc_{i}", height=100)
        
        with col_time:
            scene_time = st.selectbox(f"Waktu {i}", ["Pagi hari", "Siang hari", "Sore hari", "Malam hari"], key=f"time_{i}")
        
        with col_diag_a:
            # Label input dinamis mengikuti apa yang diketik di sidebar
            diag_a = st.text_input(f"Dialog {char_a_name if char_a_name else 'A'}", key=f"diag_a_{i}")
        with col_diag_b:
            diag_b = st.text_input(f"Dialog {char_b_name if char_b_name else 'B'}", key=f"diag_b_{i}")
        with col_diag_c:
            diag_c = st.text_input(f"Dialog {char_c_name if char_c_name else 'C'}", key=f"diag_c_{i}")
        
        scene_data.append({
            "num": i, 
            "desc": user_desc, 
            "time": scene_time,
            "da": diag_a, 
            "db": diag_b, 
            "dc": diag_c
        })

st.divider()

# --- TOMBOL GENERATE ---
if st.button("🚀 BUAT PROMPT", type="primary"):
    st.header("📋 Hasil Prompt")
    
    global_char = f"Character Appearance: {char_global_desc}. " if char_global_desc else ""
    
    for scene in scene_data:
        i = scene["num"]
        
        # Mapping cahaya
        time_map = {
            "Pagi hari": "morning golden hour light",
            "Siang hari": "bright midday natural sunlight",
            "Sore hari": "late afternoon warm sunset lighting",
            "Malam hari": "ambient night lighting, dark environment"
        }
        english_time = time_map.get(scene["time"], "natural lighting")
        
        # --- LOGIKA PROMPT GAMBAR ---
        ref_text = "ini adalah gambar referensi karakter saya. " if i == 1 else ""
        mandatory_text = "saya ingin membuat gambar secara konsisten adegan per adegan. "
        scene_num_text = f"buatkan saya sebuah gambar adegan ke {i}. "
        
        final_img = (
            f"{ref_text}{mandatory_text}{scene_num_text}\n"
            f"Visual: {global_char}{scene['desc']}. Waktu: {scene['time']}. "
            f"Lighting: {english_time}. {img_quality}"
        )

        # --- LOGIKA PROMPT VIDEO ---
        dialogs = []
        # Menggunakan nama yang diketik user atau inisial jika kosong
        name_a = char_a_name if char_a_name else "Character A"
        name_b = char_b_name if char_b_name else "Character B"
        name_c = char_c_name if char_c_name else "Character C"

        if scene["da"]: dialogs.append(f"{name_a}: \"{scene['da']}\"")
        if scene["db"]: dialogs.append(f"{name_b}: \"{scene['db']}\"")
        if scene["dc"]: dialogs.append(f"{name_c}: \"{scene['dc']}\"")
        
        dialog_part = ""
        if dialogs:
            dialog_part = f"\n\nDialog:\n" + "\n".join(dialogs)

        final_vid = (
            f"Generate a realistic natural video for Scene {i}. \n"
            f"Visual: {global_char}{scene['desc']}. Time context: {english_time}. {vid_quality}.{dialog_part}"
        )

        # TAMPILAN HASIL
        st.subheader(f"Adegan {i}")
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.caption(f"📸 PROMPT GAMBAR")
            st.code(final_img, language="text")
        with res_col2:
            st.caption(f"🎥 PROMPT VIDEO")
            st.code(final_vid, language="text")
        st.divider()
