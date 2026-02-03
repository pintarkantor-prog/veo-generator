import streamlit as st
from PIL import Image

st.set_page_config(page_title="Veo 3 Scriptwriter", layout="wide")

st.title("🎬 Veo 3: 15-Scene Dialogue & Visual Director")
st.markdown("Fokus pada percakapan dan aksi visual tanpa gangguan input audio tambahan.")

# --- SIDEBAR: REFERENSI ---
st.sidebar.header("👤 Character Design")
uploaded_file = st.sidebar.file_uploader("Upload Foto Karakter", type=['png', 'jpg', 'jpeg'])
char_desc = st.sidebar.text_area("Deskripsi Fisik Karakter:", "Contoh: Pria berjas hujan kuning, wajah lelah, rambut basah.")
global_style = st.sidebar.selectbox("Gaya Visual", ["Cinematic Movie", "Moody Noir", "Anime", "Realistic"])

# --- MAIN FORM ---
st.subheader("📑 Naskah & Timeline")

all_scenes_input = []

for i in range(1, 16):
    with st.expander(f"📍 ADEGAN {i}", expanded=(i == 1)):
        col1, col2 = st.columns([1, 1])
        with col1:
            action = st.text_area(f"Aksi Visual Adegan {i}", key=f"action_{i}", 
                                  placeholder="Apa yang dilakukan karakter di kamera?")
        with col2:
            dialogue = st.text_area(f"Dialog/Percakapan {i}", key=f"dialog_{i}", 
                                    placeholder="Apa yang diucapkan karakter? (Kosongkan jika tidak ada)")
            camera = st.selectbox(f"Sudut Kamera {i}", 
                                  ["Close-up (Fokus Wajah)", "Medium Shot", "Wide Shot", "Over-the-shoulder"], key=f"cam_{i}")
        
        all_scenes_input.append({"scene": i, "action": action, "dialogue": dialogue, "camera": camera})

st.divider()

# --- GENERATE OUTPUT ---
if st.button("🚀 GENERATE NASKAH VEO"):
    st.header("📋 Hasil Prompt Skenario")
    for item in all_scenes_input:
        if item["action"] or item["dialogue"]:
            st.subheader(f"Adegan {item['scene']}")
            
            # Format Prompt yang mengutamakan Dialog dan Visual
            final_p = f"""
**VIDEO PROMPT:** A {global_style} shot of {char_desc}. 
**Camera:** {item['camera']}. 
**Action:** {item['action']}. 

**DIALOGUE/SPEECH:** The character says: "{item['dialogue']}". 
(Note: Ensure lip-sync matches the dialogue naturally in {global_style} style).
            """
            st.code(final_p, language="text")
        else:
            st.info(f"Adegan {item['scene']} belum diisi.")
