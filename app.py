import streamlit as st
from PIL import Image

st.set_page_config(page_title="Veo 3 Pro Storyboard", layout="wide")

st.title("🎬 Veo 3 Smart Storyboarder")
st.markdown("Generator ini membagi cerita menjadi 3 babak sinematik untuk hasil yang lebih dinamis.")

# --- SIDEBAR: REFERENSI ---
st.sidebar.header("👤 Karakter & Gaya")
uploaded_file = st.sidebar.file_uploader("Upload Foto Karakter", type=['png', 'jpg', 'jpeg'])
char_desc = st.sidebar.text_area("Detail Fisik Karakter:", "Contoh: Pria paruh baya, jubah kulit cokelat, pedang bercahaya biru")
visual_style = st.sidebar.selectbox("Gaya Visual:", ["Dark Fantasy", "Hyper-Realistic", "Cyberpunk 2077 Style", "Studio Ghibli Inspired"])

# --- INPUT UTAMA ---
story_concept = st.text_area("Masukkan Ide Cerita Besar (Shorts/Long Form):", 
                             placeholder="Contoh: Perjalanan robot tua mencari bunga terakhir di bumi yang gersang.")

if st.button("🚀 Bangun 15 Adegan Efektif"):
    if story_concept and char_desc:
        scenes_data = [
            {"babak": "BABAK I: PENGENALAN (Adegan 1-5)", "cams": "Wide Shot, Slow Pan", "vibe": "Melancholic"},
            {"babak": "BABAK II: KONFLIK (Adegan 6-10)", "cams": "Close-up, Shaky Cam, Fast Cuts", "vibe": "Tense/Action"},
            {"babak": "BABAK III: RESOLUSI (Adegan 11-15)", "cams": "Low Angle, Tracking Shot", "vibe": "Epic/Grand"}
        ]
        
        count = 1
        for section in scenes_data:
            st.header(section["babak"])
            for j in range(5):
                with st.expander(f"Adegan {count}: {'Mulai' if count==1 else 'Transisi' if count<11 else 'Puncak'}"):
                    prompt = f"""
**PROMPT VIDEO:** A {visual_style} video. Subject: {char_desc}. 
Scene Action: [Adegan {count}: Fokus pada {section['vibe']}]. 
Context: {story_concept[:100]}. 
Camera: {section['cams']}. 4k, Cinematic lighting.

**PROMPT AUDIO:** SFX: {section['vibe']} atmosphere, matching the {section['cams']}. 
Audio: Synchronized footsteps and ambient noise.
                    """
                    st.code(prompt, language="text")
                    count += 1
    else:
        st.error("Lengkapi Deskripsi Karakter dan Ide Cerita agar hasilnya tajam!")

