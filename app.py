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
# 2. SISTEM LOGIN (STRICT ACCESS)
# ==============================================================================
USERS = {"admin": "QWERTY21ab", "icha": "udin99", "nissa": "tung22"}

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'active_user' not in st.session_state: st.session_state.active_user = ""

if not st.session_state.logged_in:
    st.title("🔐 PINTAR MEDIA - AKSES PRODUKSI")
    with st.form("form_login_staf"):
        input_user = st.text_input("Username")
        input_pass = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk Ke Sistem"):
            if input_user in USERS and USERS[input_user] == input_pass:
                st.session_state.logged_in, st.session_state.active_user = True, input_user
                st.rerun()
            else: st.error("Username atau Password Salah!")
    st.stop()

# ==============================================================================
# 3. LOGIKA LOGGING & CSS
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
    .stTextArea textarea { font-size: 14px !important; min-height: 150px !important; }
    .small-label { font-size: 12px; font-weight: bold; color: #a1a1a1; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 4. HEADER & LOGOUT
# ==============================================================================
c_h1, c_h2 = st.columns([8, 2])
c_h1.title("📸 PINTAR MEDIA")
c_h1.info(f"Staf Aktif: {st.session_state.active_user} | Detail adegan menentukan kualitas konten! 🚀❤️")
if c_h2.button("Logout 🚪"):
    st.session_state.logged_in = False
    st.rerun()

# ==============================================================================
# 5. MAPPING DATA (ESTETIKA MASTER)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
indonesia_camera = ["Ikuti Karakter", "Diam (Tanpa Gerak)", "Zoom Masuk Pelan", "Zoom Keluar Pelan", "Geser Kiri ke Kanan", "Geser Kanan ke Kiri", "Dongak ke Atas", "Tunduk ke Bawah", "Ikuti Objek (Tracking)", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat (Detail)", "Dekat (Wajah)", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Sudut Rendah (Gagah)", "Sudut Tinggi (Kecil)"]
indonesia_angle = ["Normal (Depan)", "Samping (Arah Kamera)", "Berhadapan (Ngobrol)", "Intip Bahu (Framing)", "Wibawa/Gagah (Low Angle)", "Mata Karakter (POV)"]

camera_map = {"Ikuti Karakter": "AUTO_MOOD", "Diam (Tanpa Gerak)": "Static", "Zoom Masuk Pelan": "Slow Zoom In", "Zoom Keluar Pelan": "Slow Zoom Out", "Geser Kiri ke Kanan": "Pan Left to Right", "Geser Kanan ke Kiri": "Pan Right to Left", "Dongak ke Atas": "Tilt Up", "Tunduk ke Bawah": "Tilt Down", "Ikuti Objek (Tracking)": "Tracking Shot", "Memutar (Orbit)": "Orbit Circular"}
shot_map = {"Sangat Dekat (Detail)": "Extreme Close-Up", "Dekat (Wajah)": "Close-Up", "Setengah Badan": "Medium Shot", "Seluruh Badan": "Full Body Shot", "Pemandangan Luas": "Wide Landscape Shot", "Sudut Rendah (Gagah)": "Low Angle Shot", "Sudut Tinggi (Kecil)": "High Angle Shot"}
angle_map = {"Normal (Depan)": "", "Samping (Arah Kamera)": "Side profile view, 90-degree angle.", "Berhadapan (Ngobrol)": "Two subjects facing each other directly.", "Intip Bahu (Framing)": "Over-the-shoulder framing.", "Wibawa/Gagah (Low Angle)": "Heroic low angle shot.", "Mata Karakter (POV)": "First-person POV."}

if 'm_light' not in st.session_state: st.session_state.m_light = "Bening dan Tajam"
if 'm_cam' not in st.session_state: st.session_state.m_cam = "Ikuti Karakter"
if 'm_shot' not in st.session_state: st.session_state.m_shot = "Setengah Badan"
if 'm_angle' not in st.session_state: st.session_state.m_angle = "Normal (Depan)"

def global_sync_v920():
    st.session_state.m_light, st.session_state.m_cam = st.session_state.light_input_1, st.session_state.camera_input_1
    st.session_state.m_shot, st.session_state.m_angle = st.session_state.shot_input_1, st.session_state.angle_input_1
    for i in range(2, 51):
        for k in ["light", "camera", "shot", "angle"]:
            key = f"{k}_input_{i}"
            if key in st.session_state: st.session_state[key] = st.session_state[f"m_{k[:3]}"]

# ==============================================================================
# 6. SIDEBAR & SETTINGS
# ==============================================================================
with st.sidebar:
    if st.session_state.active_user == "admin" and st.checkbox("Buka Log Google Sheets"):
        try: st.dataframe(st.connection("gsheets", type=GSheetsConnection).read(worksheet="Sheet1", ttl=0))
        except: st.warning("Database offline.")
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", 1, 50, 10)

# ==============================================================================
# 7. IDENTITAS KARAKTER (MULTIPLE CHARACTERS RESTORED)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
with st.expander("👥 Identitas & Fisik Karakter (WAJIB ISI)", expanded=True):
    col_c1, col_c2 = st.columns(2)
    c_n1 = col_c1.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c_p1 = col_c1.text_area("Fisik Karakter 1", key="c_desc_1_input", height=80)
    c_n2 = col_c2.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c_p2 = col_c2.text_area("Fisik Karakter 2", key="c_desc_2_input", height=80)
    
    st.divider()
    num_extra = st.number_input("Total Karakter dalam Project", 2, 10, 2)
    
    all_chars_list = []
    if c_n1: all_chars_list.append({"name": c_n1, "desc": c_p1})
    if c_n2: all_chars_list.append({"name": c_n2, "desc": c_p2})

    if num_extra > 2:
        cols_ex = st.columns(num_extra - 2)
        for i_ex in range(2, int(num_extra)):
            with cols_ex[i_ex-2]:
                ex_n = st.text_input(f"Nama Karakter {i_ex+1}", key=f"ex_name_{i_ex}")
                ex_p = st.text_area(f"Fisik Karakter {i_ex+1}", key=f"ex_phys_{i_ex}", height=80)
                if ex_n: all_chars_list.append({"name": ex_n, "desc": ex_p})

# ==============================================================================
# 8. INPUT ADEGAN GRID
# ==============================================================================
adegan_storage = []
for i_s in range(1, int(num_scenes) + 1):
    with st.expander(f"{'🟢 MASTER CONTROL' if i_s==1 else '🎬 ADEGAN'} {i_s}", expanded=(i_s==1)):
        cv, cc = st.columns([6.5, 3.5])
        v_in = cv.text_area(f"Visual Adegan {i_s}", key=f"vis_input_{i_s}", height=150)
        
        # Grid Controls
        r1c1, r1c2 = cc.columns(2)
        l_v = r1c1.selectbox("💡 Cahaya", options_lighting, index=options_lighting.index(st.session_state.m_light), key=f"light_input_{i_s}", on_change=(global_sync_v920 if i_s==1 else None))
        c_v = r1c2.selectbox("🎥 Gerak", indonesia_camera, index=indonesia_camera.index(st.session_state.m_cam), key=f"camera_input_{i_s}", on_change=(global_sync_v920 if i_s==1 else None))
        r2c1, r2c2 = cc.columns(2)
        s_v = r2c1.selectbox("📐 Shot", indonesia_shot, index=indonesia_shot.index(st.session_state.m_shot), key=f"shot_input_{i_s}", on_change=(global_sync_v920 if i_s==1 else None))
        a_v = r2c2.selectbox("✨ Angle", indonesia_angle, index=indonesia_angle.index(st.session_state.m_angle), key=f"angle_input_{i_s}", on_change=(global_sync_v920 if i_s==1 else None))

        diag_cols = st.columns(len(all_chars_list) if all_chars_list else 1)
        sc_dialogs = []
        for ic, cd in enumerate(all_chars_list):
            d_t = diag_cols[ic].text_input(f"Dialog {cd['name']}", key=f"diag_{i_s}_{ic}")
            if d_t: sc_dialogs.append({"name": cd['name'], "text": d_t})
        
        adegan_storage.append({"num": i_s, "visual": v_in, "light": l_v, "cam": c_v, "shot": s_v, "angle": a_v, "dialogs": sc_dialogs})

# ==============================================================================
# 9. GENERATOR PROMPT (FULL LOGIC RESTORED)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active: st.warning("Isi deskripsi visual!")
    else:
        record_to_sheets(st.session_state.active_user, active[0]["visual"], len(active))
        
        # Quality Base
        quality_str = "Full-bleed cinematography, edge-to-edge pixel rendering, 8k resolution, deep saturated pigments, zero digital noise, STRICTLY NO text, NO speech bubbles. --ar 9:16"

        for item in active:
            v_low = item["visual"].lower()
            
            # --- Smart Anchor Teras ---
            final_visual = item["visual"] + " (Backrest fixed against house wall, positioned under porch roof)." if "teras" in v_low else item["visual"]

            # --- Logic DNA & Dialog Emotion ---
            dna_parts = [f"STRICT FIDELITY on {c['name']}: {c['desc']}." for c in all_chars_list if c['name'].lower() in v_low]
            dna_final = " ".join(dna_parts)
            
            d_all = " ".join([f"{d['name']}: {d['text']}" for d in item["dialogs"]])
            emotion = f"Emotion Context: Reacting to '{d_all}'. Focus on facial expressions. " if d_all else ""

            # --- Logic Smart Camera ---
            if camera_map[item["cam"]] == "AUTO_MOOD":
                if any(x in v_low for x in ["lari", "jalan", "mobil"]): cam_cmd = "Dynamic Tracking Shot"
                elif any(x in v_low for x in ["sedih", "menangis", "fokus"]): cam_cmd = "Slow Cinematic Zoom In"
                else: cam_cmd = "Subtle cinematic camera drift"
            else: cam_cmd = camera_map[item["cam"]]

            # --- Full Lighting Map ---
            l_t = item["light"]
            if "Bening" in l_t: l_cmd, a_cmd = "Ultra-high altitude light, extreme micro-contrast.", "10:00 AM mountain sun, deepest cobalt blue sky."
            elif "Mendung" in l_t: l_cmd, a_cmd = "Intense moody overcast, 8000k cold temp.", "Gray-cobalt sky, tactile texture definition."
            elif "Suasana Malam" in l_t: l_cmd, a_cmd = "Cinematic Night, 9000k moonlit glow.", "Deep indigo-black sky, hyper-defined textures."
            elif "Suasana Sore" in l_t: l_cmd, a_cmd = "4:00 PM indigo atmosphere, sharp rim lighting.", "Late afternoon cold sun, long sharp shadows."
            else: l_cmd, a_cmd = "Natural professional lighting.", "Crystal clear atmosphere."

            # Render
            st.subheader(f"✅ Adegan {item['num']}")
            m_lock = "SESSION ANTI-DRIFT: Maintain permanent consistency. " if item['num'] == 1 else ""
            
            img = f"{m_lock}STATIC photo, 9:16 vertical. {angle_map[item['angle']]} {emotion}{dna_final} Visual: {final_visual}. Atmosphere: {a_cmd}. Lighting: {l_cmd}. {quality_str}"
            vid = f"{m_lock}9:16 vertical video. {shot_map[item['shot']]} {cam_cmd}. {emotion}{dna_final} Visual: {final_visual}. Lighting: {l_cmd}. 60fps, fluid motion."

            c1, c2 = st.columns(2)
            c1.code(img, language="text")
            c2.code(vid, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA | V.1.2.5-FULL")
