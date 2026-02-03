import streamlit as st

st.set_page_config(page_title="Natural Storyboard Generator", layout="wide")

st.title("📸 Natural Storyboard Generator")
st.info("Isi detail adegan, tentukan waktunya, lalu klik **'BUAT PROMPT'** untuk melihat hasilnya.")

# --- SIDEBAR: PENGATURAN GLOBAL ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Tokoh")
    
    characters = []

    # Karakter 1
    st.markdown("**Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="Contoh: Udin")
    c1_desc = st.text_area("Fisik Karakter 1", key="char_desc_0", placeholder="Ciri fisik...", height=68)
    characters.append({"name": c1_name, "desc": c1_desc})
    
    st.divider()

    # Karakter 2
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="Contoh: Tung")
    c2_desc = st.text_area("Fisik Karakter 2", key="char_desc_1", placeholder="Ciri fisik...", height=68)
    characters.append({"name": c2_name, "desc": c2_desc})

    st.divider()

    # Form Jumlah Karakter di bawah Karakter 2
    num_chars = st.number_input("Tambah Karakter Lainnya (Total)", min_value=2, max_value=5, value=2)

    if num_chars > 2:
        for j in range(2, num_chars):
            st.divider()
            st.markdown(f"**Karakter {j+1}**")
            c_name = st.text_input(f"Nama Karakter {j+1}", key=f"char_name_{j}", placeholder=f"Contoh: Tokoh {j+1}")
            c_desc = st.text_area(f"Fisik Karakter {j+1}", key=f"char_desc_{j}", placeholder="Ciri fisik...", height=68)
            characters.append({"name": c_name, "desc": c_desc})

# --- PARAMETER KUALITAS (Menghapus kata 'Realistic') ---
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

# --- FORM INPUT ADEGAN ---
st.subheader("📝 Detail Adegan")
scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
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

# --- TOMBOL GENERATE ---
if st.button("🚀 BUAT PROMPT", type="primary"):
    st.header("📋 Hasil Prompt")
    
    all_char_refs = []
    for char in characters:
        if char['name'] and char['desc']:
            all_char_refs.append(f"{char['name']} ({char['desc']})")
    
    combined_physique = "Characters Appearance: " + ", ".join(all_char_refs) + ". " if all_char_refs else ""
    
    for scene in scene_data:
        i = scene["num"]
        
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
            f"Visual: {combined_physique}{scene['desc']}. Waktu: {scene['time']}. "
            f"Lighting: {english_time}. {img_quality}"
        )

        # --- LOGIKA PROMPT VIDEO ---
        dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
        dialog_part = f"\n\nDialog:\n" + "\n".join(dialog_lines) if dialog_lines else ""

        final_vid = (
            f"Generate a natural video for Scene {i}. \n"
            f"Visual: {combined_physique}{scene['desc']}. Time context: {english_time}. {vid_quality}.{dialog_part}"
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
