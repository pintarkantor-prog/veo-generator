import streamlit as st

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. CUSTOM CSS (SIDEBAR GELAP & TOMBOL HIJAU) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: white !important;
    }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 1px solid #ffffff !important;
        transform: scale(1.1); 
    }
    button[title="Copy to clipboard"]:active {
        background-color: #1e7e34 !important;
    }
    .stTextArea textarea {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("semangat buat alur cerita nya guys ❤️❤️❤️")

# --- 3. SIDEBAR: KONFIGURASI TOKOH ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Tokoh")
    
    characters = []
    st.markdown("**Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="UDIN")
    c1_desc = st.text_area("Fisik Karakter 1", key="char_desc_0", placeholder="Ciri fisik...", height=68)
    characters.append({"name": c1_name, "desc": c1_desc})
    
    st.divider()
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="TUNG")
    c2_desc = st.text_area("Fisik Karakter 2", key="char_desc_1", placeholder="Ciri fisik...", height=68)
    characters.append({"name": c2_name, "desc": c2_desc})

    st.divider()
    num_chars = st.number_input("Tambah Karakter Lainnya (Total)", min_value=2, max_value=5, value=2)

    if num_chars > 2:
        for j in range(2, int(num_chars)):
            st.divider()
            st.markdown(f"**Karakter {j+1}**")
            cn = st.text_input(f"Nama Karakter {j+1}", key=f"char_name_{j}")
            cd = st.text_area(f"Fisik Karakter {j+1}", key=f"char_desc_{j}", height=68)
            characters.append({"name": cn, "desc": cd})

# --- 4. PARAMETER KUALITAS SUPRA-DETAIL (Update v3.2) ---
# Fokus pada ketajaman tekstur dan saturasi warna spesifik
img_quality = (
    "8k resolution, ultra-detailed textures, macro photography sharpness, "
    "vivid emerald green grass, deep azure blue sky, rich color pop, "
    "high contrast ratio, intense visual clarity, sharp outlines, "
    "accurate character color rendering, authentic skin textures with subsurface scattering, "
    "raw photo quality, captured on 35mm lens, f/11 aperture for edge-to-edge sharpness, "
    "NO soft focus, NO blur, NO cartoonish flat colors, --v 6.0"
)

vid_quality = (
    "ultra-vivid 4k video, extreme clarity, high frame rate, vivid color fidelity, "
    "vibrant natural environments, emerald foliage, deep blue sky tones, "
    "sharp focus on moving objects, high-resolution textures, NO motion blur"
)

# --- 5. FORM INPUT ADEGAN ---
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
        
        scene_data.append({"num": i, "desc": user_desc, "time": scene_time, "dialogs": scene_dialogs})

st.divider()

# --- 6. TOMBOL GENERATE (BUAT PROMPT) ---
if st.button("🚀 BUAT PROMPT", type="primary"):
    filled_scenes = [s for s in scene_data if s["desc"].strip() != ""]
    
    if not filled_scenes:
        st.warning("Silakan isi kolom 'Visual Adegan'!")
    else:
        st.header("📋 Hasil Prompt")
        for scene in filled_scenes:
            i = scene["num"]
            v_input = scene["desc"]
            
            detected_physique = []
            for char in characters:
                if char['name'] and char['name'].lower() in v_input.lower():
                    detected_physique.append(f"{char['name']} ({char['desc']})")
            
            char_ref = "Appearance: " + ", ".join(detected_physique) + ". " if detected_physique else ""
            
            # Waktu Mapping dengan penajaman elemen alam
            time_map = {
                "Pagi hari": "vibrant golden hour light, high contrast emerald and azure tones",
                "Siang hari": "bright intense midday sun, vivid deep blue sky, lush green grass contrast",
                "Sore hari": "warm sunset fiery orange sky, high saturation silhouette contrast",
                "Malam hari": "clear starry night, deep obsidian sky, sharp neon light reflections"
            }
            eng_time = time_map.get(scene["time"], "natural lighting")
            
            # PROMPT GAMBAR
            final_img = (
                f"buatkan saya sebuah gambar adegan ke {i}. ini adalah gambar referensi karakter saya. "
                f"fokus pada ketajaman objek, kejernihan warna langit, rumput, dan detail fisik karakter. "
                f"Visual: {char_ref}{v_input}. Waktu: {scene['time']}. "
                f"Environment: {eng_time}. {img_quality}"
            )

            # PROMPT VIDEO
            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            dialog_part = f"\n\nDialog:\n" + "\n".join(dialog_lines) if dialog_lines else ""

            final_vid = (
                f"Generate a supra-detailed vivid video for Scene {i}. "
                f"Focus on lush environment colors and sharp character textures. "
                f"Visual: {char_ref}{v_input}. Lighting: {eng_time}. {vid_quality}.{dialog_part}"
            )

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
st.sidebar.caption("PINTAR MEDIA Storyboard v3.2")
