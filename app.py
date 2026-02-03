import streamlit as st

st.set_page_config(page_title="Consistent Storyboard Generator", layout="wide")

st.title("🎬 High-End Storyboard Generator")
st.info("Gunakan tombol **'Generate Semua Prompt'** di bawah setelah mengisi detail adegan.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas Karakter")
    char_a_name = st.text_input("Nama Karakter A", value="Udin")
    char_b_name = st.text_input("Nama Karakter B", value="Tung")

# --- PARAMETER KUALITAS REALISTIS ---
img_quality = "ultra-realistic photography, 8k resolution, cinema camera, sharp focus, highly detailed skin textures, cinematic lighting, masterpiece, NO cartoon, NO anime, NO 3D render, realistic live-action"
vid_quality = "cinematic video, photorealistic, 24fps, natural motion blur, professional cinematography, high-end production, no CGI look, real-life motion"

# --- FORM INPUT ---
st.subheader("📝 Detail Adegan")

scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        col_desc, col_diag_a, col_diag_b, col_cam = st.columns([2, 1, 1, 1])
        
        with col_desc:
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"desc_{i}", height=100, placeholder="Contoh: Berjalan di trotoar kota yang ramai.")
        with col_diag_a:
            diag_a = st.text_input(f"Dialog {char_a_name}", key=f"diag_a_{i}")
        with col_diag_b:
            diag_b = st.text_input(f"Dialog {char_b_name}", key=f"diag_b_{i}")
        with col_cam:
            cam_move = st.selectbox(f"Kamera {i}", ["Static", "Zoom In", "Tracking", "Pan", "Handheld"], key=f"cam_{i}")
        
        scene_data.append({
            "num": i,
            "desc": user_desc,
            "da": diag_a,
            "db": diag_b,
            "cam": cam_move
        })

st.divider()

# --- TOMBOL GENERATE ---
if st.button("🚀 Generate Semua Prompt", type="primary"):
    st.header("📋 Hasil Generate Prompt")
    
    for scene in scene_data:
        i = scene["num"]
        
        # --- LOGIKA KHUSUS PROMPT GAMBAR (Poin 3) ---
        # 1. Kalimat referensi hanya di adegan 1
        ref_text = "ini adalah gambar referensi karakter saya. " if i == 1 else ""
        
        # 2. Kalimat wajib (Bahasa Indonesia) di semua adegan gambar
        mandatory_text = "saya ingin membuat gambar secara konsisten adegan per adegan. "
        
        # 3. Penomoran otomatis adegan
        scene_num_text = f"buatkan saya sebuah gambar adegan ke {i}. "
        
        # Prompt Gambar Final (Tanpa Dialog)
        final_img = (
            f"{ref_text}{mandatory_text}{scene_num_text}\n"
            f"Visual: {scene['desc']}. {img_quality}"
        )

        # --- LOGIKA KHUSUS PROMPT VIDEO ---
        # Dialog hanya muncul di video (Poin 4)
        dialog_part = ""
        if scene["da"] or scene["db"]:
            dialog_part = f"\n\nDialog:\n- {char_a_name}: \"{scene['da']}\"\n- {char_b_name}: \"{scene['db']}\""

        # Prompt Video Final (Tanpa instruksi teks Indonesia di poin 3)
        final_vid = (
            f"Generate a cinematic video sequence for Scene {i}. \n"
            f"Visual: {scene['desc']}. {vid_quality}. Camera: {scene['cam']}.{dialog_part}"
        )

        # --- TAMPILAN HASIL ---
        st.subheader(f"Adegan {i}")
        res_col1, res_col2 = st.columns(2)
        
        with res_col1:
            st.caption(f"📸 PROMPT GAMBAR (Banana)")
            st.code(final_img, language="text")
        
        with res_col2:
            st.caption(f"🎥 PROMPT VIDEO (Veo 3)")
            st.code(final_vid, language="text")
        st.divider()
else:
    st.write("Silakan isi data di atas dan klik tombol Generate.")
