import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(page_title="PINTAR MEDIA - Ultra Storyboard", layout="wide", initial_sidebar_state="expanded")

# ==============================================================================
# 2. SISTEM LOGIN
# ==============================================================================
USERS = {"admin": "QWERTY21ab", "icha": "udin99", "nissa": "tung22"}
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'active_user' not in st.session_state: st.session_state.active_user = ""

if not st.session_state.logged_in:
    st.title("🔐 PINTAR MEDIA - AKSES PRODUKSI")
    with st.form("form_login"):
        u, p = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("Masuk"):
            if u in USERS and USERS[u] == p:
                st.session_state.logged_in, st.session_state.active_user = True, u
                st.rerun()
            else: st.error("Akses Ditolak!")
    st.stop()

# ==============================================================================
# 3. DATABASE & CSS
# ==============================================================================
def record_to_sheets(user, first_visual, total_scenes):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(worksheet="Sheet1", ttl=0)
        new_row = pd.DataFrame([{"Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User": user, "Total Adegan": total_scenes, "Visual Utama": first_visual[:150]}])
        conn.update(worksheet="Sheet1", data=pd.concat([existing_data, new_row], ignore_index=True))
    except: pass

st.markdown("""<style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    button[title="Copy to clipboard"] { background-color: #28a745 !important; color: white !important; transform: scale(1.1); }
    .stTextArea textarea { font-size: 14px !important; min-height: 180px !important; }
</style>""", unsafe_allow_html=True)

# ==============================================================================
# 4. MAPPING DATA (VERSION 1.5.0 - THE LEAN MEAT)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
indonesia_camera = ["Ikuti Karakter", "Diam (Tanpa Gerak)", "Zoom Masuk Pelan", "Zoom Keluar Pelan", "Geser Kiri ke Kanan", "Geser Kanan ke Kiri", "Dongak ke Atas", "Tunduk ke Bawah", "Ikuti Objek (Tracking)", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat (Detail)", "Dekat (Wajah)", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Sudut Rendah (Gagah)", "Sudut Tinggi (Kecil)"]
indonesia_angle = ["Normal (Depan)", "Samping (Arah Kamera)", "Berhadapan (Ngobrol)", "Intip Bahu (Framing)", "Wibawa/Gagah (Low Angle)", "Mata Karakter (POV)"]

camera_map = {"Ikuti Karakter": "AUTO_MOOD", "Diam (Tanpa Gerak)": "Static", "Zoom Masuk Pelan": "Slow Zoom In", "Zoom Keluar Pelan": "Slow Zoom Out", "Geser Kiri ke Kanan": "Pan L-R", "Geser Kanan ke Kiri": "Pan R-L", "Dongak ke Atas": "Tilt Up", "Tunduk ke Bawah": "Tilt Down", "Ikuti Objek (Tracking)": "Tracking", "Memutar (Orbit)": "Orbit"}
shot_map = {"Sangat Dekat (Detail)": "Extreme Close-Up", "Dekat (Wajah)": "Close-Up", "Setengah Badan": "Medium Shot", "Seluruh Badan": "Full Body Shot", "Pemandangan Luas": "Wide Landscape", "Sudut Rendah (Gagah)": "Low Angle", "Sudut Tinggi (Kecil)": "High Angle"}

angle_map = {
    "Normal (Depan)": "",
    "Samping (Arah Kamera)": "90-degree side profile, cinematic depth.",
    "Berhadapan (Ngobrol)": "Direct eye-contact profile, facing each other.",
    "Intip Bahu (Framing)": "Over-the-shoulder framing, voyeuristic depth.",
    "Wibawa/Gagah (Low Angle)": "Majestic low-angle, heroic perspective.",
    "Mata Karakter (POV)": "First-person POV, immersive character-eye view."
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
# 5. SIDEBAR
# ==============================================================================
with st.sidebar:
    if st.session_state.active_user == "admin" and st.checkbox("📊 Admin Monitor"):
        try: st.dataframe(st.connection("gsheets", type=GSheetsConnection).read(worksheet="Sheet1", ttl=0))
        except: st.warning("DB Error.")
    num_scenes = st.number_input("Jumlah Adegan", 1, 50, 10)

# ==============================================================================
# 6. IDENTITAS KARAKTER
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
with st.expander("👥 Identitas & Fisik Karakter", expanded=True):
    c1, c2 = st.columns(2)
    n1, p1 = c1.text_input("Nama Karakter 1", key="c_name_1_input").strip(), c1.text_area("Fisik 1", key="c_desc_1_input", height=100)
    n2, p2 = c2.text_input("Nama Karakter 2", key="c_name_2_input").strip(), c2.text_area("Fisik 2", key="c_desc_2_input", height=100)
    
    num_extra = st.number_input("Total Karakter", 2, 10, 2)
    all_chars = []
    if n1: all_chars.append({"name": n1, "desc": p1})
    if n2: all_chars.append({"name": n2, "desc": p2})

    if num_extra > 2:
        cols = st.columns(num_extra - 2)
        for idx in range(2, int(num_extra)):
            ex_n = cols[idx-2].text_input(f"Nama {idx+1}", key=f"ex_name_{idx}").strip()
            ex_p = cols[idx-2].text_area(f"Fisik {idx+1}", key=f"ex_phys_{idx}", height=100)
            if ex_n: all_chars.append({"name": ex_n, "desc": ex_p})

# ==============================================================================
# 7. GRID INPUT ADEGAN (FIXED LOOP)
# ==============================================================================
adegan_storage = []
for i in range(1, int(num_scenes) + 1):
    with st.expander(f"{'🟢 MASTER' if i==1 else '🎬 ADEGAN'} {i}", expanded=(i==1)):
        v_col, c_col = st.columns([6.5, 3.5])
        v_in = v_col.text_area(f"Visual {i}", key=f"vis_input_{i}", height=180)
        
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
            if d_t: diags.append({"name": cd['name'], "text": d_t})
        adegan_storage.append({"num": i, "visual": v_in, "light": l_v, "cam": c_v, "shot": s_v, "angle": a_v, "dialogs": diags})

# ==============================================================================
# 8. GENERATOR PROMPT (TIERED HIERARCHY)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active: st.warning("Mohon isi visual adegan!")
    else:
        record_to_sheets(st.session_state.active_user, active[0]["visual"], len(active))
        
        # MEGA STACK (PANGKAS LEMAK - TINGGALKAN DAGING TEKNIS)
        ultra_quality = (
            "8k resolution, extreme micro-contrast enhancement, deep saturated matte pigments, vivid color punch, "
            "optical clarity, f/11 aperture, zero noise, CPL-filter effect, intricate hyper-textures. "
            "STRICTLY NO AI-blur, NO text, NO speech bubbles, NO black bars. --ar 9:16"
        )

        for item in active:
            v_low = item["visual"].lower()
            
            # T1: DNA (DI DEPAN)
            dna_parts = [f"IDENTICAL CHARACTER ANCHOR: {c['name']} is ({c['desc']}). STRICT FIDELITY." for c in all_chars if c['name'].lower() in v_low]
            dna_final = " ".join(dna_parts)

            # T2: LIGHTING (VERSI DAGING - TAJAM & KONTRAS)
            l_t = item["light"]
            if "Bening" in l_t: l_cmd = "Ultra-altitude sunlight, zero haze, extreme micro-contrast, crisp sky."
            elif "Mendung" in l_t: l_cmd = "8000k moody overcast, 16-bit color depth, tactile texture bite, ice-cold temp."
            elif "Dramatis" in l_t: l_cmd = "Hard directional side-lighting, HDR contrast, sharp pitch-black shadows."
            elif "Jelas" in l_t: l_cmd = "Deeply saturated matte pigments, CPL polarizer, zero reflections, vivid color depth."
            elif "Malam" in l_t: l_cmd = "Cinematic Night HMI lighting, sharp rim light, 9000k moonlit glow, indigo-black."
            elif "Alami" in l_t: l_cmd = "Low-exposure sunlight, local contrast amplification, hyper-saturated chlorophyll pigments."
            else: l_cmd = "4:00 PM indigo sun, sharp rim highlights, crisp silhouette, long sharp shadows."

            st.subheader(f"✅ Adegan {item['num']}")
            
            # RAKITAN FINAL
            final_p = f"PERMANENT SESSION IDENTITY. {dna_final} Visual Scene: {item['visual']}. {angle_map[item['angle']]}. {l_cmd} {ultra_quality}"
            final_v = f"PERMANENT SESSION IDENTITY. {dna_final} 9:16 vertical video. {shot_map[item['shot']]} {camera_map[item['cam']]}. {item['visual']}. {l_cmd} 60fps, fluid motion, {ultra_quality}"

            c1, c2 = st.columns(2)
            c1.code(final_p, language="text")
            c2.code(final_v, language="text")
            st.divider()

st.sidebar.caption("PINTAR MEDIA | V.1.5.0-LEAN-ULTRA")
