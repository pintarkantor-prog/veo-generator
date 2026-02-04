import streamlit as st

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: white !important; }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 1px solid #ffffff !important;
        transform: scale(1.1); 
    }
    button[title="Copy to clipboard"]:active { background-color: #1e7e34 !important; }
    .stTextArea textarea { font-size: 14px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("PINTAR MEDIA - Versi 1.7 (Fixed Key Error) ❤️")

# --- 3. SIDEBAR: KONFIGURASI TOKOH ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas Tokoh")
    characters = []
    
    # Menggunakan key yang berbeda dengan input di dalam adegan (sidebar_ prefix)
    for i in range(2):
        st.markdown(f"**Karakter {i+1}**")
        name = st.text_input(f"Nama", key=f"sidebar_name_{i}", placeholder="Contoh: UDIN")
        desc = st.text_area(f"Fisik", key=f"sidebar_desc_{i}", height=68)
        characters.append({"name": name, "desc": desc})

# --- 4. FORM INPUT ADEGAN ---
st.subheader("📝 Detail Adegan")
scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        col_setup = [3] + [1] * len(characters)
        cols = st.columns(col_setup)
        
        with cols[0]:
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"main_desc_{i}", height=100)
        
        scene_dialogs = []
        for idx, char in enumerate(characters):
            with cols[idx + 1]:
                char_label = char['name'] if char['name'] else f"Karakter {idx+1}"
                d_input = st.text_input(f"Dialog {char_label}", key=f"main_diag_{idx}_{i}")
                scene_dialogs.append({"name": char_label, "text": d_input})
        
        scene_data.append({"num": i, "desc": user_desc, "dialogs": scene_dialogs})

st.divider()

# --- 5. LOGIKA GENERATE ---
if st.button("🚀 BUAT PROMPT", type="primary"):
    filled_scenes = [s for s in scene_data if s["desc"].strip() != ""]
    
    if not filled_scenes:
        st.warning("Silakan isi kolom 'Visual Adegan'.")
    else:
        st.header("📋 Hasil Prompt")
        for scene in filled_scenes:
            i, v_in = scene["num"], scene["desc"]
            
            # Gabungkan Dialog
            d_text = " ".join([f"{d['name']}: {d['text']}" for d in scene['dialogs'] if d['text']])
            
            # Cek Fisik Tokoh yang disebut di Visual
            phys = ", ".join([f"{c['name']} ({c['desc']})" for c in characters if c['name'] and c['name'].lower() in v_in.lower()])
            char_ref = f"Appearance: {phys}. " if phys else ""
            
            # Output Murni (Pure Base)
            f_img = f"Adegan {i}. Visual: {char_ref}{v_in}."
            f_vid = f"Video Adegan {i}. Visual: {char_ref}{v_in}. Dialog: {d_text}."

            st.subheader(f"Adegan {i}")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("📸 PROMPT GAMBAR")
                st.code(f_img, language="text")
            with c2:
                st.caption("🎥 PROMPT VIDEO")
                st.code(f_vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA - v1.7 Pure")
