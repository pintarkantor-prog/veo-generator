import streamlit as st
from PIL import Image

st.set_page_config(page_title="Consistent Storyboard Generator", layout="wide")

st.title("🎬 High-End Storyboard Generator")
st.info("Gunakan tombol **'Generate Semua Prompt'** setelah mengisi detail adegan.")

# --- SIDEBAR: PENGATURAN GLOBAL ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🖼️ Referensi Karakter")
    # Fitur Upload Gambar
    uploaded_file = st.file_uploader("Unggah Gambar Referensi Karakter", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="Referensi Utama", use_container_width=True)
    
    # Deskripsi Karakter yang akan selalu muncul di setiap prompt
    char_global_desc = st.text_area("Deskripsi Fisik Karakter (Global)", 
                                    placeholder="Contoh: Pria umur 30th, rambut cepak hitam, memakai kemeja flanel biru, wajah kotak.",
                                    help="Deskripsi ini akan otomatis masuk ke semua prompt adegan agar karakter tetap konsisten.")

    st.divider()
    st.subheader("👥 Nama Tokoh")
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
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"desc_{i}", height=100, placeholder="Contoh: Sedang berdiri di balkon.")
        with col_diag_a:
            diag_a = st.text_input(f"Dialog {char_a_name}", key=f"diag_a_{i}")
        with col_diag_b:
            diag_b = st.text_input(f"Dialog {char_b_name}", key=f"diag_b_{i}")
        with col_cam:
            cam_move = st.selectbox(f"Kamera {i}", ["Static", "Zoom In", "Tracking", "Pan", "Handheld"], key=f"cam_{i}")
        
        scene_data.append({
            "num": i, "desc": user_desc, "da": diag_a, "db": diag_b, "cam": cam_move
        })

st.divider()

# --- TOMBOL GENERATE ---
if st.button("🚀 Generate Semua Prompt", type="primary"):
    st.header("📋 Hasil Generate Prompt")
    
    # Tambahkan deskripsi global jika diisi
    global_char = f"Character Appearance: {char_global_desc}. " if char_global_desc else ""
    
    for scene in scene_data:
        i = scene["num"]
        
        # LOGIKA PROMPT GAMBAR
        ref_text = "ini adalah gambar referensi karakter saya. " if i == 1 else ""
        mandatory_text = "saya ingin membuat gambar secara konsisten adegan per adegan. "
        scene_num_text = f"buatkan saya sebuah gambar adegan ke {i}. "
        
        final_img = (
            f"{ref_text}{mandatory_text}{scene_num_text}\n"
            f"Visual: {global_char}{scene['desc']}. {img_quality}"
        )

        # LOGIKA PROMPT VIDEO
        dialog_part = ""
        if scene["da"] or scene["db"]:
            dialog_part = f"\n\nDialog:\n- {char_a_name}: \"{scene['da']}\"\n- {char_b_name}: \"{scene['db']}\""

        final_vid = (
            f"Generate a cinematic video sequence for Scene {i}. \n"
            f"Visual: {global_char}{scene['desc']}. {vid_quality}. Camera: {scene['cam']}.{dialog_part}"
        )

        # TAMPILAN HASIL
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
    st.write("Silakan isi data dan klik tombol Generate.")
