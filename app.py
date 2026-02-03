import streamlit as st

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Natural Storyboard Generator", layout="wide")

st.title("📸 Natural Storyboard Generator")
st.info("""
**Logika Otomatis Aktif:**
1. Hanya adegan yang diisi **Visual Adegan**-nya yang akan diproses.
2. Deskripsi fisik tokoh hanya muncul jika namanya disebutkan dalam teks **Visual Adegan**.
3. Dialog hanya muncul di **Prompt Video**.
4. Instruksi khusus konsistensi hanya muncul di **Prompt Gambar**.
""")

# --- SIDEBAR: PENGATURAN GLOBAL ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Tokoh")
    
    # Karakter 1 & 2 (Selalu Ada)
    characters = []
    
    st.markdown("**Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="Contoh: UDIN")
    c1_desc = st.text_area("Fisik Karakter 1", key="char_desc_0", placeholder="Ciri fisik...", height=68)
    characters.append({"name": c1_name, "desc": c1_desc})
    
    st.divider()
    
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="Contoh: TUNG")
    c2_desc = st.text_area("Fisik Karakter 2", key="char_desc_1", placeholder="Ciri fisik...", height=68)
    characters.append({"name": c2_name, "desc": c2_desc})

    st.divider()
    
    # Input Jumlah Karakter diletakkan di bawah Karakter 2
    num_chars = st.number_input("Total Karakter (Minimal 2)", min_value=2, max_value=5, value=2)

    # Karakter Tambahan (3, 4, 5) jika num_chars > 2
    if num_chars > 2:
        for j in range(2, int(num_chars)):
            st.divider()
            st.markdown(f"**Karakter {j+1}**")
            cn = st.text_input(f"Nama Karakter {j+1}", key=f"char_name_{j}", placeholder=f"Contoh: TOKOH {j+1}")
            cd = st.text_area(f"Fisik Karakter {j+1}", key=f"char_desc_{j}", placeholder="Ciri fisik...", height=68)
            characters.append({"name": cn, "desc": cd})

# --- PARAMETER KUALITAS NATURAL (Tanpa kata 'Realistic') ---
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

# --- TOMBOL GENERATE ---
if st.button("🚀 BUAT PROMPT", type="primary"):
    # Filter: Hanya adegan yang deskripsinya tidak kosong
    filled_scenes = [s for s in scene_data if s["desc"].strip() != ""]
    
    if not filled_scenes:
        st.warning("Silakan isi kolom 'Visual Adegan' pada setidaknya satu form sebelum membuat prompt.")
    else:
        st.header("📋 Hasil Prompt")
        
        for scene in filled_scenes:
            i = scene["num"]
            visual_input = scene["desc"]
            
            # --- LOGIKA DETEKSI KARAKTER (Smart Trigger) ---
            # Deskripsi karakter hanya muncul jika namanya tertulis di 'Visual Adegan'
            detected_char_descs = []
            for char in characters:
                if char['name'] and char['name'].lower() in visual_input.lower():
                    detected_char_descs.append(f"{char['name']} ({char['desc']})")
            
            char_ref_text = "Characters Appearance: " + ", ".join(detected_char_descs) + ". " if detected_char_descs else ""
            
            # --- LOGIKA WAKTU (Mapping ke Inggris) ---
            time_map = {
                "Pagi hari": "morning golden hour light",
                "Siang hari": "bright midday natural sunlight",
                "Sore hari": "late afternoon warm sunset lighting",
                "Malam hari": "ambient night lighting, dark environment"
            }
            english_time = time_map.get(scene["time"], "natural lighting")
            
            # --- LOGIKA PROMPT GAMBAR (Poin 3: Bahasa Indonesia & Tanpa Dialog) ---
            ref_text = "ini adalah gambar referensi karakter saya. " if i == 1 else ""
            mandatory_text = "saya ingin membuat gambar secara konsisten adegan per adegan. "
            scene_num_text = f"buatkan saya sebuah gambar adegan ke {i}. "
            
            final_img = (
                f"{ref_text}{mandatory_text}{scene_num_text}\n"
                f"Visual: {char_ref_text}{visual_input}. Waktu: {scene['time']}. "
                f"Lighting: {english_time}. {img_quality}"
            )

            # --- LOGIKA PROMPT VIDEO (Poin 4: Ada Dialog & Bahasa Inggris) ---
            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            dialog_part = f"\n\nDialog:\n" + "\n".join(dialog_lines) if dialog_lines else ""

            final_vid = (
                f"Generate a natural video for Scene {i}. \n"
                f"Visual: {char_ref_text}{visual_input}. Time context: {english_time}. {vid_quality}.{dialog_part}"
            )

            # --- TAMPILAN HASIL ---
            st.subheader(f"Adegan {i}")
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.caption(f"📸 PROMPT GAMBAR (Nano Banana)")
                st.code(final_img, language="text")
            with res_col2:
                st.caption(f"🎥 PROMPT VIDEO (Veo 3)")
                st.code(final_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("Dibuat untuk kebutuhan konten konsisten.")
