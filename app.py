import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Final Chroma & Secure", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. SISTEM LOGIN (RESTORED)
# ==============================================================================
USERS = {
    "admin": "QWERTY21ab", 
    "icha": "udin99", 
    "nissa": "tung22"
}

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'active_user' not in st.session_state: st.session_state.active_user = ""

if not st.session_state.logged_in:
    st.title("🔐 PINTAR MEDIA - AKSES PRODUKSI")
    with st.form("form_login_staf"):
        input_user = st.text_input("Username")
        input_pass = st.text_input("Password", type="password")
        btn_login = st.form_submit_button("Masuk Ke Sistem")
        if btn_login:
            if input_user in USERS and USERS[input_user] == input_pass:
                st.session_state.logged_in = True
                st.session_state.active_user = input_user
                st.rerun()
            else: 
                st.error("Username atau Password Salah!")
    st.stop()

# ==============================================================================
# 3. DATABASE LOGGING & CSS
# ==============================================================================
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
    except: 
        pass

st.markdown("""<style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    button[title="Copy to clipboard"] { background-color: #28a745 !important; color: white !important; transform: scale(1.1); }
    .stTextArea textarea { font-size: 14px !important; min-height: 180px !important; }
</style>""", unsafe_allow_html=True)

# ==============================================================================
# 4. MAPPING DATA (ULTRA CHROMA ENGINE)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
indonesia_camera = ["Ikuti Karakter", "Diam (Tanpa Gerak)", "Zoom Masuk Pelan", "Zoom Keluar Pelan", "Geser Kiri ke Kanan", "Geser Kanan ke Kiri", "Dongak ke Atas", "Tunduk ke Bawah", "Ikuti Objek (Tracking)", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat (Detail)", "Dekat (Wajah)", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Sudut Rendah (Gagah)", "Sudut Tinggi (Kecil)"]
indonesia_angle = ["Normal (Depan)", "Samping (Arah Kamera)", "Berhadapan (Ngobrol)", "Intip Bahu (Framing)", "Wibawa/Gagah (Low Angle)", "Mata Karakter (POV)"]

camera_map = {"Ikuti Karakter": "AUTO_MOOD", "Diam (Tanpa Gerak)": "Static", "Zoom Masuk Pelan": "Slow Zoom In", "Zoom Keluar Pelan": "Slow Zoom Out", "Geser Kiri ke Kanan": "Pan L-R", "Geser Kanan ke Kiri": "Pan R-L", "Dongak ke Atas": "Tilt Up", "Tunduk ke Bawah": "Tilt Down", "Ikuti Objek (Tracking)": "Tracking", "Memutar (Orbit)": "Orbit"}
shot_map = {"Sangat Dekat (Detail)": "Extreme Close-Up", "Dekat (Wajah)": "Close-Up", "Setengah Badan": "Medium Shot", "Seluruh Badan": "Full Body Shot", "Pemandangan Luas": "Wide Landscape", "Sudut Rendah (Gagah)": "Low Angle", "Sudut Tinggi (Kecil)": "High Angle"}

angle_map = {
    "Normal (Depan)": "",
    "Samping (Arah Kamera)": "90-degree side profile view.",
    "Berhadapan (Ngobrol)": "Facing each other directly.",
    "Intip Bahu (Framing)": "Over-the-shoulder framing for cinematic depth.",
    "Wibawa/Gagah (Low Angle)": "Heroic low-angle perspective.",
    "Mata Karakter (POV)": "First-person character POV."
}

if 'm_light' not in st.session_state: st.session_state.m_light = "Bening dan Tajam"
if 'm_cam' not in st.session_state: st.session_state.m_cam = "Ikuti Karakter"
if 'm_shot' not in st.session_state: st.session_state.m_shot = "Setengah Badan"
if 'm_angle' not in st.session_state: st.session_state.m_angle = "Normal (Depan)"

def global_sync_v920():
    st.session_state.m_light = st.session_state.light_input_1
    st.session_state.m_cam = st.session_state.camera_input_1
    st.session_state.m_shot = st.session_state.shot_input_1
    st.session_state.m_angle = st.session_state.angle_input_1
    for idx in range(2, 51):
        if f"light_input_{idx}" in st.session_state: st.session_state[f"light_input_{idx}"] = st.session_state.m_light
        if f"camera_input_{idx}" in st.session_state: st.session_state[f"camera_input_{idx}"] = st.session_state.m_cam
        if f"shot_input_{idx}" in st.session_state: st.session_state[f"shot_input_{idx}"] = st.session_state.m_shot
        if f"angle_input_{idx}" in st.session_state: st.session_state[f"angle_input_{idx}"] = st.session_state.m_angle

# ==============================================================================
# 5. SIDEBAR & ADMIN MONITOR
# ==============================================================================
with st.sidebar:
    if st.session_state.active_user == "admin":
        st.header("📊 Admin Monitor")
        if st.checkbox("Buka Log Google Sheets"):
            try:
                conn_a = st.connection("gsheets", type=GSheetsConnection)
                df_a = conn_a.read(worksheet="Sheet1", ttl=0)
                st.dataframe(df_a)
            except: 
                st.warning("Gagal memuat database.")
        st.divider()
    
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", 1, 50, 10)
    if st.button("Logout 🚪"):
        st.session_state.logged_in = False
        st.rerun()

# ==============================================================================
# 6. IDENTITAS KARAKTER (UNIVERSAL)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
with st.expander("👥 Identitas & Fisik Karakter", expanded=True):
    num_chars = st.number_input("Total Karakter", 1, 10, 2)
    all_chars = []
    char_cols = st.columns(2)
    for i in range(num_chars):
        with char_cols[i % 2]:
            c_name = st.text_input(f"Nama Karakter {i+1}", key=f"c_name_{i}").strip()
            c_desc = st.text_area(f"Deskripsi {i+1}", key=f"c_desc_{i}", height=80)
            if c_name: 
                all_chars.append({"name": c_name, "desc": c_desc, "ref_id": i+1})

# ==============================================================================
# 7. GRID INPUT ADEGAN
# ==============================================================================
adegan_storage = []
for i in range(1, int(num_scenes) + 1):
    with st.expander(f"{'🟢 MASTER' if i==1 else '🎬 ADEGAN'} {i}", expanded=(i==1)):
        v_col, c_col = st.columns([6.5, 3.5])
        v_in = v_col.text_area(f"Visual {i}", key=f"vis_input_{i}", height=150)
        
        r1c1, r1c2 = c_col.columns(2)
        l_v = r1c1.selectbox(f"💡 Cahaya {i}", options_lighting, index=options_lighting.index(st.session_state.m_light), key=f"light_input_{i}", on_change=(global_sync_v920 if i==1 else None))
        c_v = r1c2.selectbox(f"🎥 Gerak {i}", indonesia_camera, index=indonesia_camera.index(st.session_state.m_cam), key=f"camera_input_{i}", on_change=(global_sync_v920 if i==1 else None))
        
        r2c1, r2c2 = c_col.columns(2)
        s_v = r2c1.selectbox(f"📐 Shot {i}", indonesia_shot, index=indonesia_shot.index(st.session_state.m_shot), key=f"shot_input_{i}", on_change=(global_sync_v920 if i==1 else None))
        a_v = r2c2.selectbox(f"✨ Angle {i}", indonesia_angle, index=indonesia_angle.index(st.session_state.m_angle), key=f"angle_input_{i}", on_change=(global_sync_v920 if i==1 else None))
        
        diags = []
        diag_cols = st.columns(len(all_chars) if all_chars else 1)
        for ic, cd in enumerate(all_chars):
            d_t = diag_cols[ic].text_input(f"Dialog {cd['name']}", key=f"diag_{i}_{ic}")
            if d_t: 
                diags.append({"name": cd['name'], "text": d_t})
        adegan_storage.append({"num": i, "visual": v_in, "light": l_v, "cam": c_v, "shot": s_v, "angle": a_v, "dialogs": diags})

# ==============================================================================
# 8. GENERATOR PROMPT (ISOLATION TAG + CHROMA PARAMETERS)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active: 
        st.warning("Mohon isi visual adegan!")
    else:
        record_to_sheets(st.session_state.active_user, active[0]["visual"], len(active))
        
        # PARAMETER KUALITAS TAJAM & WARNA BERANI
        ultra_quality = (
            "8k resolution, extreme micro-contrast enhancement, vivid organic color punch, "
            "f/11 aperture sharpness, zero digital noise, high dynamic range. "
            "(Contrast:1.3), (Saturation:1.4), hyper-realistic-texture-bite. "
            "STRICTLY NO AI-blur, NO text, NO speech bubbles, NO black bars. --ar 9:16"
        )

        for item in active:
            v_low = item["visual"].lower()
            
            # T1: DNA ISOLATION (Prioritas Tertinggi)
            dna_parts = [f"((STRICT IDENTITY LOCK IMAGE_REF_{c['ref_id']}: {c['name']} as {c['desc']}))" for c in all_chars if c['name'].lower() in v_low]
            dna_final = " ".join(dna_parts)

            # T2: LIGHTING (TAJAM & KONTRAS)
            l_t = item["light"]
            if "Bening" in l_t: 
                l_cmd = "Ultra-high altitude sunlight, zero haze, crisp micro-contrast, extreme sky clarity."
            elif "Mendung" in l_t: 
                l_cmd = "8000k moody overcast, 16-bit color depth, tactile micro-texture bite, gray-cobalt sky."
            elif "Dramatis" in l_t: 
                l_cmd = "Hard directional side-lighting, HDR shadows, deep dynamic range contrast."
            elif "Alami" in l_t: 
                l_cmd = "Hyper-saturated chlorophyll, low-exposure natural sunlight, defined micro-textures on leaves."
            else: 
                l_cmd = "Professional high-contrast natural lighting, clear sky gradient."

            st.subheader(f"✅ Adegan {item['num']}")
            
            # RAKITAN FINAL: DNA -> VISUAL -> LIGHT -> QUALITY
            final_p = f"{dna_final} Visual: {item['visual']}. {angle_map[item['angle']]}. Lighting: {l_cmd}. {ultra_quality}"
            final_v = f"9:16 vertical video. {dna_final} {shot_map[item['shot']]} {camera_map[item['cam']]}. {item['visual']}. {l_cmd}. {ultra_quality}"

            c1, c2 = st.columns(2)
            c1.markdown("**🖼️ Prompt Gambar**")
            c1.code(final_p, language="text")
            c2.markdown("**▶️ Prompt Video**")
            c2.code(final_v, language="text")
            st.divider()

st.sidebar.caption("PINTAR MEDIA | V.1.8.1-ULTRA-SECURE")
