import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. SISTEM LOGIN
# ==============================================================================
USERS = {"admin": "QWERTY21ab", "icha": "udin99", "nissa": "tung22"}
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'active_user' not in st.session_state: st.session_state.active_user = ""

if not st.session_state.logged_in:
    st.title("🔐 PINTAR MEDIA - AKSES PRODUKSI")
    with st.form("form_login_staf"):
        input_user = st.text_input("Username")
        input_pass = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk"):
            if input_user in USERS and USERS[input_user] == input_pass:
                st.session_state.logged_in, st.session_state.active_user = True, input_user
                st.rerun()
            else: st.error("Salah!")
    st.stop()

# ==============================================================================
# 3. LOGGING & CSS
# ==============================================================================
def record_to_sheets(user, first_visual, total_scenes):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(worksheet="Sheet1", ttl=0)
        new_row = pd.DataFrame([{"Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User": user, "Total Adegan": total_scenes, "Visual Utama": first_visual[:150]}])
        conn.update(worksheet="Sheet1", data=pd.concat([existing_data, new_row], ignore_index=True))
    except: pass

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    button[title="Copy to clipboard"] { background-color: #28a745 !important; color: white !important; transform: scale(1.1); }
    .stTextArea textarea { font-size: 14px !important; min-height: 180px !important; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 4. MAPPING & SYNC
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
indonesia_camera = ["Ikuti Karakter", "Diam (Tanpa Gerak)", "Zoom Masuk Pelan", "Zoom Keluar Pelan", "Geser Kiri ke Kanan", "Geser Kanan ke Kiri", "Dongak ke Atas", "Tunduk ke Bawah", "Ikuti Objek (Tracking)", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat (Detail)", "Dekat (Wajah)", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Sudut Rendah (Gagah)", "Sudut Tinggi (Kecil)"]
indonesia_angle = ["Normal (Depan)", "Samping (Arah Kamera)", "Berhadapan (Ngobrol)", "Intip Bahu (Framing)", "Wibawa/Gagah (Low Angle)", "Mata Karakter (POV)"]

camera_map = {"Ikuti Karakter": "AUTO_MOOD", "Diam (Tanpa Gerak)": "Static", "Zoom Masuk Pelan": "Slow Zoom In", "Zoom Keluar Pelan": "Slow Zoom Out", "Geser Kiri ke Kanan": "Pan Left to Right", "Geser Kanan ke Kiri": "Pan Right to Left", "Dongak ke Atas": "Tilt Up", "Tunduk ke Bawah": "Tilt Down", "Ikuti Objek (Tracking)": "Tracking Shot", "Memutar (Orbit)": "Orbit Circular"}
shot_map = {"Sangat Dekat (Detail)": "Extreme Close-Up", "Dekat (Wajah)": "Close-Up", "Setengah Badan": "Medium Shot", "Seluruh Badan": "Full Body Shot", "Pemandangan Luas": "Wide Landscape Shot", "Sudut Rendah (Gagah)": "Low Angle Shot", "Sudut Tinggi (Kecil)": "High Angle Shot"}
angle_map = {"Normal (Depan)": "", "Samping (Arah Kamera)": "Side profile view, 90-degree.", "Berhadapan (Ngobrol)": "Facing each other directly.", "Intip Bahu (Framing)": "Over-the-shoulder framing.", "Wibawa/Gagah (Low Angle)": "Heroic low angle.", "Mata Karakter (POV)": "First-person POV."}

if 'm_light' not in st.session_state: st.session_state.m_light = "Bening dan Tajam"
if 'm_cam' not in st.session_state: st.session_state.m_cam = "Ikuti Karakter"
if 'm_shot' not in st.session_state: st.session_state.m_shot = "Setengah Badan"
if 'm_angle' not in st.session_state: st.session_state.m_angle = "Normal (Depan)"

def global_sync():
    st.session_state.m_light, st.session_state.m_cam = st.session_state.light_input_1, st.session_state.camera_input_1
    st.session_state.m_shot, st.session_state.m_angle = st.session_state.shot_input_1, st.session_state.angle_input_1
    for i in range(2, 51):
        for k in ["light", "camera", "shot", "angle"]:
            key = f"{k}_input_{i}"
            if key in st.session_state: st.session_state[key] = st.session_state[f"m_{k[:3]}"]

# ==============================================================================
# 5. SIDEBAR & CONFIG
# ==============================================================================
with st.sidebar:
    if st.session_state.active_user == "admin" and st.checkbox("📊 Admin Monitor"):
        try: st.dataframe(st.connection("gsheets", type=GSheetsConnection).read(worksheet="Sheet1", ttl=0))
        except: st.warning("Database error.")
    num_scenes = st.number_input("Jumlah Adegan", 1, 50, 10)

# ==============================================================================
# 6. IDENTITAS & FISIK
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
with st.expander("👥 Identitas & Fisik Karakter", expanded=True):
    c1, c2 = st.columns(2)
    n1 = c1.text_input("Nama Karakter 1", key="c_name_1_input").strip()
    p1 = c1.text_area("Fisik 1", key="c_desc_1_input", height=100)
    n2 = c2.text_input("Nama Karakter 2", key="c_name_2_input").strip()
    p2 = c2.text_area("Fisik 2", key="c_desc_2_input", height=100)
    
    num_extra = st.number_input("Total Karakter", 2, 10, 2)
    all_chars = []
    if n1: all_chars.append({"name": n1, "desc": p1})
    if n2: all_chars.append({"name": n2, "desc": p2})

    if num_extra > 2:
        cols = st.columns(num_extra - 2)
        for i in range(2, int(num_extra)):
            ex_n = cols[i-2].text_input(f"Nama {i+1}", key=f"ex_name_{i}").strip()
            ex_p = cols[i-2].text_area(f"Fisik {i+1}", key=f"ex_phys_{i}", height=100)
            if ex_n: all_chars.append({"name": ex_n, "desc": ex_p})

# ==============================================================================
# 7. GRID INPUT ADEGAN
# ==============================================================================
adegan_storage = []
for i in range(1, int(num_scenes) + 1):
    with st.expander(f"{'🟢 MASTER' if i==1 else '🎬 ADEGAN'} {i}", expanded=(i==1)):
        v_col, c_col = st.columns([6.5, 3.5])
        v_in = v_col.text_area(f"Visual {i}", key=f"vis_input_{i}", height=150)
        
        r1c1, r1c2 = c_col.columns(2)
        l_v = r1c1.selectbox(f"💡 Cahaya {i}", options_lighting, key=f"light_input_{i}", on_change=(global_sync if i==1 else None))
        c_v = r1c2.selectbox(f"🎥 Gerak {i}", indonesia_camera, key=f"camera_input_{i}", on_change=(global_sync if i==1 else None))
        r2c1, r2c2 = c_col.columns(2)
        s_v = r2c1.selectbox(f"📐 Shot {i}", indonesia_shot, key=f"shot_input_{i}", on_change=(global_sync if i==1 else None))
        a_v = r2c2.selectbox(f"✨ Angle {i}", indonesia_angle, key=f"angle_input_{i}", on_change=(global_sync if i==1 else None))

        diag_cols = st.columns(len(all_chars) if all_chars else 1)
        diags = []
        for ic, cd in enumerate(all_chars):
            d_t = diag_cols[ic].text_input(f"Dialog {cd['name']}", key=f"diag_{i}_{ic}")
            if d_t: diags.append({"name": cd['name'], "text": d_t})
        adegan_storage.append({"num": i, "visual": v_in, "light": l_v, "cam": c_v, "shot": s_v, "angle": a_v, "dialogs": diags})

# ==============================================================================
# 8. GENERATOR PROMPT (THE STABLE QUALITY METHOD)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active: st.warning("Isi visual!")
    else:
        record_to_sheets(st.session_state.active_user, active[0]["visual"], len(active))
        
        # --- QUALITY CORE (Dibuat Padat Agar Tidak Memakan Fokus AI) ---
        quality_core = (
            "ultra-high-fidelity, 8k resolution, micro-contrast, deep saturated pigments, vivid organic color, "
            "f/11 aperture sharpness, zero digital noise, zero atmospheric haze, crystal clear background. "
            "Full-bleed cinematography, edge-to-edge pixel rendering, 9:16 vertical. "
            "STRICTLY NO text, NO speech bubbles, NO watermark, NO black bars."
        )

        for item in active:
            v_low = item["visual"].lower()
            
            # --- 1. DNA ANCHOR (PRIORITAS NOMOR SATU) ---
            dna_list = []
            for c in all_chars:
                if c['name'].lower() in v_low:
                    # Kita gunakan instruksi "DISTINCT IDENTITY" untuk memisahkan antar karakter
                    dna_list.append(f"DISTINCT IDENTITY for {c['name']}: {c['desc']}. (Strict fidelity to reference {all_chars.index(c)+1})")
            
            dna_final = " ".join(dna_list)
            
            # --- 2. ACTION & EMOTION ---
            d_all = " ".join([f"{d['name']}: {d['text']}" for d in item["dialogs"]])
            emotion = f"Emotion: reacting to '{d_all}'. Focus on 8k facial texture expressions." if d_all else ""
            
            # --- 3. LIGHTING & ATMOSPHERE ---
            l_t = item["light"]
            if "Bening" in l_t: l_cmd = "Crystal clear 10:00 AM sun, zero haze, micro-contrast."
            elif "Mendung" in l_t: l_cmd = "Overcast lighting, 8000k cold temperature, tactile textures."
            elif "Suasana Malam" in l_t: l_cmd = "Cinematic Night, indigo-black sky, sharp rim light."
            else: l_cmd = "Professional high-contrast natural lighting."

            # --- 4. RENDER FINAL (HIERARKI BARU) ---
            st.subheader(f"✅ Adegan {item['num']}")
            
            # URUTAN: IDENTITAS -> VISUAL -> KUALITAS
            img_p = (
                f"IDENTICAL CHARACTER SESSION. {dna_final}. "
                f"Visual: {item['visual']}. {emotion} "
                f"Setting: {l_cmd}. Camera: {angle_map[item['angle']]}. "
                f"Final Specs: {quality_core} --ar 9:16"
            )
            
            vid_p = (
                f"IDENTICAL CHARACTER SESSION. {dna_final}. "
                f"Video Visual: {item['visual']}. {shot_map[item['shot']]} {camera_map[item['cam']]}. "
                f"Specs: 60fps, fluid motion, {quality_core}"
            )

            c1, c2 = st.columns(2)
            c1.markdown("**📸 Prompt Gambar**")
            c1.code(img_p, language="text")
            c2.markdown("**🎥 Prompt Video**")
            c2.code(vid_p, language="text")
            st.divider()

st.sidebar.caption("PINTAR MEDIA | V.1.3.7-STABLE")
