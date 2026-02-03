import streamlit as st
from PIL import Image

# Konfigurasi Halaman
st.set_page_config(page_title="Veo 3 Pro: Consistent Character", layout="wide")

st.title("🎬 Veo 3: Professional Image & Video Suite")
st.markdown("Fokus pada Konsistensi Karakter Berbasis Referensi Gambar (Tanpa Backsound).")

# --- SIDEBAR: REFERENSI KARAKTER ---
st.sidebar.header("👤 Character Reference")
uploaded_file = st.sidebar.file_uploader("Upload Foto Karakter Utama", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    st.sidebar.image(Image.open(uploaded_file), caption="REFERENSI UTAMA", use_container_width=True)

char_desc = st.sidebar.text_area("Detail Fisik Karakter (PENTING):", 
                                 placeholder="Sebutkan detail dari foto: warna rambut, pakaian, ciri wajah, dll.")

st.sidebar.divider()
st.sidebar.warning("🔇 **Mode No Backsound:** Aktif.")

# --- MAIN FORM: 15 SCENES ---
st.subheader("📑 Storyboard Adegan (15 Slot)")

all_scenes_data = []

# Preset Kamera 8K Realistis
camera_presets = {
    "Extreme Close-up (ARRI Alexa 8k)": "Extreme close-up shot, shot on ARRI Alexa 35, 8k resolution, macro cinematography, sharp focus on eyes, ultra-photorealistic skin textures.",
    "Medium Shot (Panavision 8k)": "Medium cinematic shot, shot on Panavision Millennium DXL2, 8k UHD, lifelike textures, natural lighting.",
    "Wide Angle (RED V-Raptor 8k)": "Grand wide-angle panoramic shot, RED V-Raptor XL 8k, sharp focus foreground to background, hyper-realistic environment.",
    "Over-the-shoulder (Cinema Glass)": "Over-the-shoulder shot, 8k resolution, cinematic bokeh, realistic skin tones."
}

for i in range(1, 16):
    with st.expander(f"📍 ADEGAN {i}", expanded=(i == 1)):
        col1, col2 = st.columns([1, 1])
        with col1:
            action_context = st.text_area(f"Aksi & Latar Adegan {i}", key=f"act_{i}", 
                                         placeholder="Contoh: Berjalan di tengah hutan bambu yang berkabut.")
        with col2:
            dialogue = st.text_area(f"Dialog {i}", key=f"dial_{i}", placeholder="Isi ucapan karakter (jika ada)...")
            cam_choice = st.selectbox(f"Sudut Kamera {i}", list(camera_presets.keys()), key=f"cam_{i}")

        all_scenes_data.append({
            "id": i, "action": action_context, "dialogue": dialogue, "camera": camera_presets[cam_choice]
        })

st.divider()

# --- GENERATE OUTPUT ---
if st.button("🚀 BUILD ALL PROMPTS"):
    if not char_desc or not uploaded_file:
        st.error("Pastikan Anda sudah UPLOAD GAMBAR dan ISI DESKRIPSI KARAKTER di sidebar!")
    else:
        st.header("📋 Hasil Prompt Terstruktur")
        
        for scene in all_scenes_data:
            if scene["action"]:
                st.subheader(f"Adegan {scene['id']}")
                
                res_col1, res_col2 = st.columns(2)
                
                # --- PROMPT GAMBAR (KALIMAT BAHASA INDONESIA TETAP) ---
                with res_col1:
                    st.info("🖼️ Prompt Gambar (Static)")
                    
                    if scene["id"] == 1:
                        default_txt = "ini adalah referensi gambar karakter saya"
                    else:
                        default_txt = "saya ingin membuat beberapa adegan secara konsisten, menggunakan referensi gambar yang saya kirim"
                    
                    img_p = f"""{default_txt}.
Detail Karakter: {char_desc}.
Photo-realistic 8k, highly detailed.
Scene & Environment: {scene['action']}.
Style: Cinematic photography, professional lighting, realistic as real life."""
                    st.code(img_p, language="text")
                
                # --- PROMPT VIDEO (TANPA BACKSOUND) ---
                with res_col2:
                    st.success("📹 Prompt Video (Veo 3)")
                    vid_p = f"""VIDEO PROMPT:
A cinematic 8k video featuring the EXACT SAME character from the reference image: {char_desc}.
CAMERA: {scene['camera']}
ACTION: {scene['action']}.

AUDIO:
No background music. No score.
Dialogue: "{scene['dialogue'] if scene['dialogue'] else 'No dialogue'}".
Only natural ambient sounds matching the environment.
Sync: Lip-sync and facial muscles must be perfect."""
                    st.code(vid_p, language="text")
                st.divider()
