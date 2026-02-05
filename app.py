import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - AI Storyboard Ultimate",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk UI yang profesional
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff !important; }
    .stTextArea textarea { font-size: 14px !important; line-height: 1.5 !important; }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important; color: white !important; opacity: 1 !important; 
        border-radius: 6px !important; border: 2px solid #ffffff !important;
        transform: scale(1.1); box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. SISTEM LOGIN & LOGGING GOOGLE SHEETS (DIPERTAHANKAN)
# ==============================================================================
USERS = {"admin": "QWERTY21ab", "icha": "udin99", "nissa": "tung22"}

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 AKSES PRODUKSI - PINTAR MEDIA")
    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk"):
            if u in USERS and USERS[u] == p:
                st.session_state.logged_in = True
                st.session_state.active_user = u
                st.rerun()
            else: st.error("Username atau Password Salah!")
    st.stop()

def record_to_sheets(user, first_visual, total_scenes):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(worksheet="Sheet1", ttl=0)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = pd.DataFrame([{
            "Waktu": current_time, 
            "User": user, 
            "Total Adegan": total_scenes, 
            "Visual Utama": first_visual[:150]
        }])
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated_df)
    except Exception as e:
        st.warning(f"Catatan: Koneksi Google Sheets tidak terdeteksi, log tidak tersimpan. ({e})")

# ==============================================================================
# 3. SIDEBAR (UNIVERSAL CHARACTER ENGINE)
# ==============================================================================
with st.sidebar:
    if st.session_state.active_user == "admin":
        st.header("📊 Admin Monitor")
        if st.checkbox("Lihat Log Produksi"):
            try:
                conn_a = st.connection("gsheets", type=GSheetsConnection)
                st.dataframe(conn_a.read(worksheet="Sheet1", ttl=0))
            except: st.error("Gagal memuat Database.")
        st.divider()

    st.header("⚙️ Project Setup")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=5)
    st.divider()
    
    st.subheader("👥 Database Karakter")
    total_char_input = st.number_input("Total Karakter", min_value=1, max_value=20, value=2)
    
    project_characters = []
    for i in range(int(total_char_input)):
        st.markdown(f"**Karakter {i+1}**")
        c_name = st.text_input(f"Nama", key=f"cn_{i}", placeholder="Misal: UDIN")
        c_desc = st.text_area(f"DNA Fisik", key=f"cd_{i}", height=70, placeholder="Detail material, baju, ciri khas...")
        if c_name:
            project_characters.append({"name": c_name, "desc": c_desc})

# ==============================================================================
# 4. MASTER QUALITY (THE "GALAK" STACK)
# ==============================================================================
master_quality = (
    "Full-bleed cinematography, edge-to-edge pixel rendering, 8k resolution, "
    "micro-contrast enhancement, vivid organic color punch, intricate textures, "
    "f/11 aperture for deep focus sharpness, zero digital noise."
)

negative_footer = (
    "STRICTLY NO rain, NO wet ground, NO raindrops, NO speech bubbles, NO text, "
    "NO typography, NO watermark, NO letters, NO black bars, NO subtitles."
)

options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

# ==============================================================================
# 5. INPUT ADEGAN
# ==============================================================================
st.subheader("📝 Alur Cerita & Visual")
adegan_storage = []

for i_s in range(1, num_scenes + 1):
    with st.expander(f"🎬 ADEGAN {i_s}", expanded=(i_s==1)):
        col_v, col_l, col_a = st.columns([3, 1, 1])
        with col_v: 
            v_input = st.text_area(f"Visual", key=f"v_in_{i_s}", height=100)
        with col_l: 
            l_val = st.selectbox(f"Cahaya", options_lighting, key=f"l_in_{i_s}")
        with col_a: 
            a_val = st.selectbox(f"Angle", ["Normal", "Samping", "Low Angle", "POV", "Wide Shot"], key=f"a_in_{i_s}")
        
        adegan_storage.append({"num": i_s, "visual": v_input, "light": l_val, "angle": a_val})

# ==============================================================================
# 6. ENGINE PROMPT GENERATOR (V.1.5.7)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_scenes = [a for a in adegan_storage if a["visual"].strip()]
    
    if not active_scenes:
        st.warning("Mohon isi deskripsi visual adegan!")
    else:
        # Jalankan Log ke Google Sheets
        record_to_sheets(st.session_state.active_user, active_scenes[0]["visual"], len(active_scenes))
        
        # Mantra Sakti Bos
        boss_mantra = "Ini adalah referensi gambar dari cerita yang akan saya buat. Saya membutuhkan sebuah gambar yang konsisten adegan demi adegan. "

        for item in active_scenes:
            vis_lower = item["visual"].lower()
            
            # 1. MOOD MAPPING (DIPERTAHANKAN LENGKAP)
            if "Mendung" in item["light"]:
                mood = "Intense moody overcast, 16-bit color depth, gray-cobalt sky, thick clouds, tactile texture definition."
            elif "Malam" in item["light"]:
                mood = "Cinematic Night, dual-tone HMI spotlighting, sharp rim lights, indigo-black sky."
            elif "Sejuk" in item["light"]:
                mood = "8000k ice-cold temp brilliance, glacier-clear atmosphere, zenith sun position."
            else:
                mood = f"{item['light']} atmosphere, high clarity, natural lighting contrast."

            # 2. DYNAMIC CHARACTER LOCK (Anti-Campur)
            dna_parts = []
            for char in project_characters:
                if char['name'].lower() in vis_lower:
                    dna_parts.append(f"### STRICT {char['name'].upper()} IDENTITY: ONLY {char['desc']} material. DO NOT mix textures. ###")
            
            dna_final = " ".join(dna_parts)

            # 3. SPATIAL ANCHOR (Anti-Melayang)
            vis_final = item["visual"]
            if any(x in vis_lower for x in ["teras", "porch", "halaman"]):
                vis_final += " (Backrest fixed against house wall, under porch roof)."

            # RAKITAN PROMPT
            final_prompt = (
                f"{boss_mantra}Buatkan saya adegan ke {item['num']}: "
                f"{dna_final} Visual: {vis_final}. "
                f"Mood: {mood}. "
                f"{master_quality} {negative_footer} --ar 9:16"
            )
            
            st.subheader(f"✅ Hasil Adegan {item['num']}")
            st.code(final_prompt, language="text")
            st.divider()

st.sidebar.caption("PINTAR MEDIA | V.1.5.7 | MASTER CONTINUITY")
