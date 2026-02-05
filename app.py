import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Universal Ultra Storyboard", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. SISTEM LOGIN (FULL SECURE)
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
# 3. INITIALIZE SESSION STATE (FIXED ATTRIBUTE ERROR)
# ==============================================================================
if 'm_light' not in st.session_state: st.session_state.m_light = "Bening dan Tajam"
if 'm_camera' not in st.session_state: st.session_state.m_camera = "Ikuti Karakter"
if 'm_shot' not in st.session_state: st.session_state.m_shot = "Setengah Badan"
if 'm_angle' not in st.session_state: st.session_state.m_angle = "Normal (Depan)"

# ==============================================================================
# 4. DATABASE LOGGING & CSS
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
# 5. HEADER APLIKASI (RESTORED - MERAH & SEMANGAT)
# ==============================================================================
c_header1, c_header2 = st.columns([8, 2])
with c_header1:
    st.title("📸 PINTAR MEDIA")
    st.info(f"Staf Aktif: {st.session_state.active_user} | SEMANGAT KERJANYA GUYS! BUAT KONTEN YANG BENER MANTEP YOW 🚀 ❤️")

with c_header2:
    if st.button("Logout 🚪", key="logout_btn_top"):
        st.session_state.logged_in = False
        st.rerun()

# ==============================================================================
# 6. MAPPING & GLOBAL SYNC (FIXED KEY ERROR)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
indonesia_camera = ["Ikuti Karakter", "Diam (Tanpa Gerak)", "Zoom Masuk Pelan", "Zoom Keluar Pelan", "Geser Kiri ke Kanan", "Geser Kanan ke Kiri", "Dongak ke Atas", "Tunduk ke Bawah", "Ikuti Objek (Tracking)", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat (Detail)", "Dekat (Wajah)", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Sudut Rendah (Gagah)", "Sudut Tinggi (Kecil)"]
indonesia_angle = ["Normal (Depan)", "Samping (Arah Kamera)", "Berhadapan (Ngobrol)", "Intip Bahu (Framing)", "Wibawa/Gagah (Low Angle)", "Mata Karakter (POV)"]

camera_map = {"Ikuti Karakter": "AUTO_MOOD", "Diam (Tanpa Gerak)": "Static (No Move)", "Zoom Masuk Pelan": "Slow Zoom In", "Zoom Keluar Pelan": "Slow Zoom Out", "Geser Kiri ke Kanan": "Pan L-R", "Geser Kanan ke Kiri": "Pan R-L", "Dongak ke Atas": "Tilt Up", "Tunduk ke Bawah": "Tilt Down", "Ikuti Objek (Tracking)": "Tracking Shot", "Memutar (Orbit)": "Orbit Circular"}
shot_map = {"Sangat Dekat (Detail)": "Extreme Close-Up", "Dekat (Wajah)": "Close-Up", "Setengah Badan": "Medium Shot", "Seluruh Badan": "Full Body Shot", "Pemandangan Luas": "Wide Landscape", "Sudut Rendah (Gagah)": "Low Angle", "Sudut Tinggi (Kecil)": "High Angle"}

angle_map = {
    "Normal (Depan)": "",
    "Samping (Arah Kamera)": "90-degree side profile view, subject positioned to show environmental depth.",
    "Berhadapan (Ngobrol)": "Two subjects in profile view, facing each other directly, strict eye contact.",
    "Intip Bahu (Framing)": "Over-the-shoulder framing, using foreground elements for a voyeuristic look.",
    "Wibawa/Gagah (Low Angle)": "Heroic low angle shot, camera looking up at the subject.",
    "Mata Karakter (POV)": "First-person point of view, looking through the character's eyes."
}

def global_sync_v920():
    st.session_state.m_light = st.session_state.light_input_1
    st.session_state.m_camera = st.session_state.camera_input_1
    st.session_state.m_shot = st.session_state.shot_input_1
    st.session_state.m_angle = st.session_state.angle_input_1
    for idx in range(2, 51):
        if f"light_input_{idx}" in st.session_state: st.session_state[f"light_input_{idx}"] = st.session_state.m_light
        if f"camera_input_{idx}" in st.session_state: st.session_state[f"camera_input_{idx}"] = st.session_state.m_camera
        if f"shot_input_{idx}" in st.session_state: st.session_state[f"shot_input_{idx}"] = st.session_state.m_shot
        if f"angle_input_{idx}" in st.session_state: st.session_state[f"angle_input_{idx}"] = st.session_state.m_angle

# ==============================================================================
# 7. SIDEBAR & ADMIN MONITOR
# ==============================================================================
with st.sidebar:
    if st.session_state.active_user == "admin":
        st.header("📊 Admin Monitor")
        if st.checkbox("Buka Log Google Sheets"):
            try:
                conn_a = st.connection("gsheets", type=GSheetsConnection)
                df_a = conn_a.read(worksheet="Sheet1", ttl=0)
                st.dataframe(df_a)
            except: st.warning("Database Error.")
        st.divider()
    
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", 1, 50, 10)

# ==============================================================================
# 8. IDENTITAS KARAKTER (UNIVERSAL SETUP)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
with st.expander("👥 Identitas & Fisik Karakter", expanded=True):
    num_chars = st.number_input("Total Karakter", 1, 10, 2)
    all_chars = []
    char_cols = st.columns(2)
    for i in range(num_chars):
        with char_cols[i % 2]:
            c_name = st.text_input(f"Nama Karakter {i+1}", key=f"c_name_{i}").strip()
            c_desc = st.text_area(f"Fisik {i+1}", key=f"c_desc_{i}", height=80)
            if c_name: 
                all_chars.append({"name": c_name, "desc": c_desc, "ref_id": i+1})

# ==============================================================================
# 9. GRID INPUT ADEGAN (FIXED SYNC)
# ==============================================================================
adegan_storage = []
for i in range(1, int(num_scenes) + 1):
    with st.expander(f"{'🟢 MASTER' if i==1 else '🎬 ADEGAN'} {i}", expanded=(i==1)):
        v_col, c_col = st.columns([6.5, 3.5])
        v_in = v_col.text_area(f"Visual {i}", key=f"vis_input_{i}", height=150)
        
        r1c1, r1c2 = c_col.columns(2)
        l_v = r1c1.selectbox(f"💡 Cahaya {i}", options_lighting, index=options_lighting.index(st.session_state.m_light), key=f"light_input_{i}", on_change=(global_sync_v920 if i==1 else None))
        c_v = r1c2.selectbox(f"🎥 Gerak {i}", indonesia_camera, index=indonesia_camera.index(st.session_state.m_camera), key=f"camera_input_{i}", on_change=(global_sync_v920 if i==1 else None))
        
        r2c1, r2c2 = c_col.columns(2)
        s_v = r2c1.selectbox(f"📐 Shot {i}", indonesia_shot, index=indonesia_shot.index(st.session_state.m_shot), key=f"shot_input_{i}", on_change=(global_sync_v920 if i==1 else None))
        a_v = r2c2.selectbox(f"✨ Angle {i}", indonesia_angle, index=indonesia_angle.index(st.session_state.m_angle), key=f"angle_input_{i}", on_change=(global_sync_v920 if i==1 else None))
        
        diag_cols = st.columns(len(all_chars) if all_chars else 1)
        diags = []
        for ic, cd in enumerate(all_chars):
            d_t = diag_cols[ic].text_input(f"Dialog {cd['name']}", key=f"diag_{i}_{ic}")
            if d_t: diags.append({"name": cd['name'], "text": d_t})
        adegan_storage.append({"num": i, "visual": v_in, "light": l_v, "cam": c_v, "shot": s_v, "angle": a_v, "dialogs": diags})

# ==============================================================================
# 10. GENERATOR PROMPT (UNIVERSAL MAXIMUM DETAIL)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active: 
        st.warning("Mohon isi visual adegan!")
    else:
        record_to_sheets(st.session_state.active_user, active[0]["visual"], len(active))
        
        # MEGA QUALITY STACK (WARNA & KONTRAS TAJAM)
        ultra_quality = (
            "8k resolution, extreme micro-contrast enhancement, deep saturated pigments, vivid organic color punch, "
            "intricate organic textures, f/11 aperture for deep focus sharpness, zero digital noise, zero atmospheric haze. "
            "(Contrast:1.3), (Saturation:1.5), hyper-realistic-texture-bite. "
            "STRICTLY NO AI-blur, NO text, NO speech bubbles, NO black bars. --ar 9:16"
        )

        for item in active:
            v_low = item["visual"].lower()
            
            # T1: DYNAMIC IDENTITY ANCHOR (UNIVERSAL)
            dna_parts = []
            for c in all_chars:
                if c['name'].lower() in v_low:
                    # Logic Adegan 1 kirim Full, Adegan lain kirim Reference Lock
                    if item['num'] == 1:
                        dna_parts.append(f"((ABSOLUTE IDENTITY MATCH IMAGE_REF_{c['ref_id']}: {c['name']} is {c['desc']}))")
                    else:
                        dna_parts.append(f"((CONTINUE IDENTITY MATCH IMAGE_REF_{c['ref_id']}: {c['name']} remains identical))")
            dna_final = " ".join(dna_parts)

            # T2: MEGA LIGHTING (DESKRIPSI PANJANG KEMBALI)
            l_t = item["light"]
            if "Bening" in l_t: 
                l_cmd = "Ultra-high altitude light visibility, extreme micro-contrast, zero haze. 10:00 AM altitude sun, deepest cobalt blue sky."
            elif "Mendung" in l_t: 
                l_cmd = "Intense moody overcast lighting, 16-bit color depth fidelity, vivid pigment recovery, 8000k ice-cold temp, gray-cobalt sky. Tactile texture definition on every object."
            elif "Dramatis" in l_t: 
                l_cmd = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast, dramatic light rays."
            elif "Jelas" in l_t: 
                l_cmd = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections. Early morning atmosphere."
            elif "Alami" in l_t: 
                l_cmd = "Low-exposure natural sunlight, extreme chlorophyll color depth, hyper-defined micro-textures on leaves and tree bark, intricate organic textures."
            elif "Suasana Malam" in l_t:
                l_cmd = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim light highlights, 9000k cold moonlit glow, deep indigo-black sky."
            else: # Sore
                l_cmd = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, long sharp shadows, indigo-cobalt sky gradient."

            st.subheader(f"✅ Adegan {item['num']}")
            
            # RAKITAN FINAL (DENGAN PENJAGA VISUAL ADEGAN 3)
            env_action = f"ENVIRONMENTAL ACTION PRIORITY: {item['visual']}. All background objects must be present."
            
            final_p = f"{dna_final} {env_action}. Angle: {angle_map[item['angle']]}. Lighting: {l_cmd}. {ultra_quality}"
            final_v = f"9:16 vertical video. {dna_final} {shot_map[item['shot']]} {camera_map[item['m_camera']]}. SCENE: {item['visual']}. {l_cmd}. {ultra_quality}"

            c1, c2 = st.columns(2)
            c1.markdown("**🖼️ Prompt Gambar**")
            c1.code(final_p, language="text")
            c2.markdown("**▶️ Prompt Video**")
            c2.code(final_v, language="text")
            st.divider()

st.sidebar.caption("PINTAR MEDIA | V.1.9.6-FINAL-MAX")
