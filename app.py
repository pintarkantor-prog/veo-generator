import streamlit as st
from PIL import Image

# Konfigurasi Halaman
st.set_page_config(page_title="Veo 3 Image & Video Director", layout="wide")

# Custom CSS untuk tampilan yang lebih profesional
st.markdown("""
    <style>
    .stTextArea textarea { font-size: 14px; }
    .stCodeBlock { border: 1px solid #444; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎬 Veo 3: Gambar & Video Prompt Generator")
st.markdown("Hasilkan prompt terpisah untuk gambar statis dan video dinamis dengan detail 8K.")

# --- SIDEBAR: REFERENSI KARAKTER & VISUAL ---
st.sidebar.header("👤 Global Character Reference")
uploaded_file = st.sidebar.file_uploader("Upload Foto Karakter", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    st.sidebar.image(Image.open(uploaded_file), caption="Target Visual", use_container_width=True)

char_desc = st.sidebar.text_area("Deskripsi Fisik Karakter (Tetap):", 
                                 placeholder="Contoh: Pria umur 30-an, wajah simetris, kulit detail, memakai kemeja linen putih.")

st.sidebar.divider()
st.sidebar.info("💡 **Tips Kualitas:** Setiap prompt akan dioptimalkan untuk kualitas 8K, foto-realistis, dan kamera profesional.")

# --- MAIN FORM: 15 SCENES ---
st.subheader("📑 Storyboard & Dialog (15 Adegan)")

all_scenes_data = []

# Definisi Parameter Kamera Pro untuk VIDEO
video_camera_presets = {
    "Extreme Close-up (ARRI Alexa 35)": "Extreme close-up shot, shot on ARRI Alexa 35 with Zeiss Master Prime lenses, cinematic motion, dynamic lighting, smooth camera movement, 8k resolution, ultra-photorealistic, impeccable facial detail, macro cinematography, sharp focus on eyes, 4:4:4 color depth.",
    "Medium Shot (Panavision DXL2)": "Medium cinematic shot, shot on Panavision Millennium DXL2, fluid camera motion, natural light transitions, 8k UHD, lifelike textures, professional color grading, high dynamic range, sharp edges, zero noise, IMAX quality.",
    "Wide Angle (RED V-Raptor 8k)": "Grand wide-angle panoramic shot, shot on RED V-Raptor XL in 8k, smooth crane shot, deep depth of field, hyper-realistic environment, sharp focus from foreground to background, realistic atmospheric effects.",
    "Over-the-shoulder (Cinema Glass)": "Over-the-shoulder shot, subtle camera sway, shallow depth of field, 8k resolution, cinematic bokeh, realistic skin tones, high-end film production quality."
}

# Loop untuk membuat 15 Form Adegan
for i in range(1, 16):
    with st.expander(f"📍 ADEGAN {i}", expanded=(i == 1)):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            action = st.text_area(f"Aksi Visual Adegan {i}", key=f"act_{i}", 
                                  placeholder="Contoh: Karakter berjalan perlahan mendekati jendela sambil menatap hujan.")
        
        with col2:
            dialogue = st.text_area(f"Dialog/Percakapan Adegan {i}", key=f"dial_{i}", 
                                    placeholder="Apa yang diucapkan? (Kosongkan jika tidak ada)")
            cam_choice = st.selectbox(f"Setting Kamera Adegan {i}", list(video_camera_presets.keys()), key=f"cam_{i}")

        all_scenes_data.append({
            "id": i,
            "action": action,
            "dialogue": dialogue,
            "camera_video_tech": video_camera_presets[cam_choice]
        })

st.divider()

# --- GENERATE BUTTON ---
if st.button("🚀 GENERATE ALL IMAGE & VIDEO PROMPTS"):
    if not char_desc:
        st.error("Mohon isi 'Deskripsi Fisik Karakter' di sidebar terlebih dahulu agar visual konsisten!")
    else:
        st.header("📋 Daftar Prompt (Gambar & Video)")
        
        for scene in all_scenes_data:
            if scene["action"] or scene["dialogue"]:
                st.subheader(f"Adegan {scene['id']}")
                
                # --- PROMPT GAMBAR (STATIC) ---
                st.markdown("**1. Prompt Gambar (Untuk Thumbnail/Referensi):**")
                image_prompt = f"""
Ultra-realistic 8K photograph of {char_desc}.
CAMERA: Professional studio photography, incredibly detailed, perfect lighting.
ACTION: {scene['action']}.
MOOD: Cinematic, high-resolution, static image.
"""
                st.code(image_prompt, language="text")

                # --- PROMPT VIDEO (MOTION) ---
                st.markdown("**2. Prompt Video (Untuk Veo 3):**")
                video_prompt = f"""
VIDEO PROMPT:
A hyper-realistic cinematic video of {char_desc}.
CAMERA: {scene['camera_video_tech']}
ACTION: {scene['action']}.

DIALOGUE/SPEECH:
Character says: "{scene['dialogue'] if scene['dialogue'] else 'No dialogue'}"
Note: Perfect lip-syncing and natural facial muscle movement required. 8k, highly detailed, realistic as real life.
"""
                st.code(video_prompt, language="text")

            else:
                st.caption(f"Adegan {scene['id']} dilewati karena kosong.")

st.markdown("---")
st.caption("Veo 3 Advanced Generator v1.1 | Fokus: Gambar & Video Profesional")
