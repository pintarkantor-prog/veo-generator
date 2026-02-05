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
# 2. SISTEM LOGIN & DATABASE USER
# ==============================================================================
USERS = {"admin": "QWERTY21ab", "icha": "udin99", "nissa": "tung22"}

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
                st.session_state.logged_in, st.session_state.active_user = True, input_user
                st.rerun()
            else: st.error("Username atau Password Salah!")
    st.stop()

# ==============================================================================
# 3. LOGIKA LOGGING GOOGLE SHEETS
# ==============================================================================
def record_to_sheets(user, first_visual, total_scenes):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(worksheet="Sheet1", ttl=0)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = pd.DataFrame([{"Waktu": current_time, "User": user, "Total Adegan": total_scenes, "Visual Utama": first_visual[:150]}])
        conn.update(worksheet="Sheet1", data=pd.concat([existing_data, new_row], ignore_index=True))
    except Exception as e: st.error(f"Gagal mencatat log: {e}")

# ==============================================================================
# 4. CUSTOM CSS
# ==============================================================================
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff !important; }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important; color: white !important; opacity: 1 !important; 
        border-radius: 6px !important; border: 2px solid #ffffff !important;
        transform: scale(1.1); box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    .stTextArea textarea { font-size: 14px !important; line-height: 1.5 !important; font-family: 'Inter', sans-serif !important; }
    .small-label { font-size: 12px; font-weight: bold; color: #a1a1a1; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 5. HEADER APLIKASI
# ==============================================================================
c_header1, c_header2 = st.columns([8, 2])
with c_header1:
    st.title("📸 PINTAR MEDIA")
    st.info(f"Staf Aktif: {st.session_state.active_user} | Hasil render maksimal lahir dari detail yang konsisten! 🚀❤️")
with c_header2:
    if st.button("Logout 🚪"): st.session_state.logged_in = False; st.rerun()

# ==============================================================================
# 6. MAPPING TRANSLATION (DIET MODE)
# ==============================================================================
indonesia_camera = ["Otomatis (Ikuti Mood Adegan)", "Diam (Tanpa Gerak)", "Zoom Masuk Pelan", "Zoom Keluar Pelan", "Geser Kiri ke Kanan", "Geser Kanan ke Kiri", "Dongak ke Atas", "Tunduk ke Bawah", "Ikuti Objek (Tracking)", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat (Detail)", "Dekat (Wajah)", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Sudut Rendah (Gagah)", "Sudut Tinggi (Kecil)"]
indonesia_angle = ["Normal (Depan)", "Samping (Melihat Jalan/Kedalaman)", "Berhadapan (Ngobrol)", "Intip Bahu (Framing)", "Wibawa/Gagah (Low Angle)", "Mata Karakter (POV)"]

camera_map = {"Otomatis (Ikuti Mood Adegan)": "AUTO_MOOD", "Diam (Tanpa Gerak)": "Static (No Move)", "Zoom Masuk Pelan": "Slow Zoom In", "Zoom Keluar Pelan": "Slow Zoom Out", "Geser Kiri ke Kanan": "Pan Left to Right", "Geser Kanan ke Kiri": "Pan Right to Left", "Dongak ke Atas": "Tilt Up", "Tunduk ke Bawah": "Tilt Down", "Ikuti Objek (Tracking)": "Tracking Shot", "Memutar (Orbit)": "Orbit Circular"}
shot_map = {"Sangat Dekat (Detail)": "Extreme Close-Up", "Dekat (Wajah)": "Close-Up", "Setengah Badan": "Medium Shot", "Seluruh Badan": "Full Body Shot", "Pemandangan Luas": "Wide Landscape Shot", "Sudut Rendah (Gagah)": "Low Angle Shot", "Sudut Tinggi (Kecil)": "High Angle Shot"}
angle_map = {
    "Normal (Depan)": "",
    "Samping (Melihat Jalan/Kedalaman)": "Side profile view, 90-degree angle, subject positioned on the side to show depth.",
    "Berhadapan (Ngobrol)": "Two subjects in profile view, facing each other directly, strict eye contact.",
    "Intip Bahu (Framing)": "Over-the-shoulder framing using foreground elements.",
    "Wibawa/Gagah (Low Angle)": "Heroic low angle shot, camera looking up at subject.",
    "Mata Karakter (POV)": "First-person point of view, immersive perspective."
}

options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

if 'm_light' not in st.session_state: st.session_state.m_light = options_lighting[0]
if 'm_cam' not in st.session_state: st.session_state.m_cam = indonesia_camera[0]
if 'm_shot' not in st.session_state: st.session_state.m_shot = indonesia_shot[2]
if 'm_angle' not in st.session_state: st.session_state.m_angle = indonesia_angle[0]

def global_sync_v920():
    lt1, cm1, st1, ag1 = st.session_state.light_input_1, st.session_state.camera_input_1, st.session_state.shot_input_1, st.session_state.angle_input_1
    st.session_state.m_light, st.session_state.m_cam, st.session_state.m_shot, st.session_state.m_angle = lt1, cm1, st1, ag1
    for key in st.session_state.keys():
        if key.startswith("light_input_"): st.session_state[key] = lt1
        if key.startswith("camera_input_"): st.session_state[key] = cm1
        if key.startswith("shot_input_"): st.session_state[key] = st1
        if key.startswith("angle_input_"): st.session_state[key] = ag1

# ==============================================================================
# 7. SIDEBAR (CHARACTER CONFIG - DINAMIS)
# ==============================================================================
with st.sidebar:
    if st.session_state.active_user == "admin":
        st.header("📊 Admin Monitor")
        if st.checkbox("Buka Log Google Sheets"):
            try:
                conn_a = st.connection("gsheets", type=GSheetsConnection)
                st.dataframe(conn_a.read(worksheet="Sheet1", ttl=0))
            except: st.warning("Gagal memuat log.")
        st.divider()

    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    st.divider()
    
    st.subheader("👥 Daftar Karakter (Identitas Tetap)")
    c_n1_v = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="UDIN")
    c_p1_v = st.text_area("Fisik Karakter 1", key="c_desc_1_input", height=80)
    st.divider()
    c_n2_v = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="TUNG")
    c_p2_v = st.text_area("Fisik Karakter 2", key="c_desc_2_input", height=80)
    
    num_extra = st.number_input("Jumlah Karakter Tambahan", min_value=0, max_value=10, value=0)
    
    # List untuk menampung semua karakter dari sidebar
    all_chars_list = []
    if c_n1_v: all_chars_list.append({"name": c_n1_v, "desc": c_p1_v})
    if c_n2_v: all_chars_list.append({"name": c_n2_v, "desc": c_p2_v})

    if num_extra > 0:
        for ex_idx in range(num_extra):
            st.divider()
            ex_name = st.text_input(f"Nama Karakter {ex_idx + 3}", key=f"ex_name_{ex_idx}")
            ex_phys = st.text_area(f"Fisik Karakter {ex_idx + 3}", key=f"ex_phys_{ex_idx}", height=80)
            if ex_name: all_chars_list.append({"name": ex_name, "desc": ex_phys})

# ==============================================================================
# 8. MASTER QUALITY & NEGATIVE PROMPT (DIET MODE)
# ==============================================================================
master_quality_anchor = (
    "Full-bleed cinematography, edge-to-edge pixel rendering, ultra-high-fidelity 8k resolution, "
    "micro-contrast enhancement, deep saturated pigments, vivid organic color punch, intricate textures, "
    "f/11 aperture for deep focus sharpness, zero digital noise."
)

negative_prompt_footer = (
    "STRICTLY NO rain, NO wet ground, NO raindrops, NO speech bubbles, NO text, NO typography, "
    "NO watermark, NO letters, NO black bars, NO subtitles."
)

# ==============================================================================
# 9. FORM INPUT ADEGAN
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []
for i_s in range(1, int(num_scenes) + 1):
    l_box_title = f"🟢 MASTER CONTROL - ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
    with st.expander(l_box_title, expanded=(i_s == 1)):
        col_v, col_l, col_c, col_s, col_a = st.columns([3, 1.2, 1.2, 1.2, 1.4])
        with col_v: visual_input = st.text_area(f"Visual Adegan {i_s}", key=f"vis_input_{i_s}", height=150)
        with col_l:
            st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
            l_val = st.selectbox(f"L{i_s}", options_lighting, key=f"light_input_{i_s}", label_visibility="collapsed") if i_s > 1 else st.selectbox("L1", options_lighting, key="light_input_1", on_change=global_sync_v920, label_visibility="collapsed")
        with col_c:
            st.markdown('<p class="small-label">🎥 Gerak Video</p>', unsafe_allow_html=True)
            c_val = st.selectbox(f"C{i_s}", indonesia_camera, key=f"camera_input_{i_s}", label_visibility="collapsed") if i_s > 1 else st.selectbox("C1", indonesia_camera, key="camera_input_1", on_change=global_sync_v920, label_visibility="collapsed")
        with col_s:
            st.markdown('<p class="small-label">📐 Shot</p>', unsafe_allow_html=True)
            s_val = st.selectbox(f"S{i_s}", indonesia_shot, key=f"shot_input_{i_s}", label_visibility="collapsed") if i_s > 1 else st.selectbox("S1", indonesia_shot, key="shot_input_1", on_change=global_sync_v920, label_visibility="collapsed")
        with col_a:
            st.markdown('<p class="small-label">📸 Sudut Kamera</p>', unsafe_allow_html=True)
            a_val = st.selectbox(f"A{i_s}", indonesia_angle, key=f"angle_input_{i_s}", label_visibility="collapsed") if i_s > 1 else st.selectbox("A1", indonesia_angle, key="angle_input_1", on_change=global_sync_v920, label_visibility="collapsed")
        
        # Dialog Area
        diag_cols = st.columns(max(len(all_chars_list), 1))
        scene_dialogs_list = []
        for i_char, char_data in enumerate(all_chars_list):
            with diag_cols[i_char]:
                char_label = char_data['name']
                d_in = st.text_input(f"Dialog {char_label}", key=f"diag_{i_s}_{i_char}")
                scene_dialogs_list.append({"name": char_label, "text": d_in})
        
        adegan_storage.append({"num": i_s, "visual": visual_input, "light": l_val, "cam": c_val, "shot": s_val, "angle": a_val, "dialogs": scene_dialogs_list})

st.divider()

# ==============================================================================
# 10. GENERATOR PROMPT (V.1.5.1 - DYNAMIC CHARACTER LOCK)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_scenes = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active_scenes: st.warning("Mohon isi deskripsi visual adegan!")
    else:
        record_to_sheets(st.session_state.active_user, active_scenes[0]["visual"], len(active_scenes))
        
        # --- LOGIKA DYNAMIC MASTER LOCK (Absensi semua tokoh di Sidebar) ---
        full_roster = ", ".join([f"{c['name']} ({c['desc']})" for c in all_chars_list])
        master_lock_instruction = f"IMPORTANT CHARACTER MEMORY: Throughout this session, accurately remember and maintain the visual identity of these characters: {full_roster}. Do not deviate from their established physical traits. "

        for item in active_scenes:
            scene_id, vis_core, light_type = item["num"], item["visual"], item["light"]
            vis_lower = vis_core.lower()
            
            # --- LOGIKA SMART ANCHOR ---
            vis_core_final = vis_core + " (Backrest fixed against house wall, under porch roof)." if "teras" in vis_lower else vis_core

            # --- LOGIKA SMART CAMERA ---
            if camera_map.get(item["cam"]) == "AUTO_MOOD":
                if any(x in vis_lower for x in ["lari", "jalan", "pergi", "mobil", "motor"]): e_cam_move = "Dynamic Tracking Shot"
                elif any(x in vis_lower for x in ["sedih", "menangis", "fokus", "melihat"]): e_cam_move = "Slow Cinematic Zoom In"
                elif any(x in vis_lower for x in ["pemandangan", "luas", "halaman"]): e_cam_move = "Slow Pan Right"
                else: e_cam_move = "Subtle camera drift"
            else: e_cam_move = camera_map.get(item["cam"], "Static")

            # --- MOOD CMD (LEBURAN LIGHTING & ATMOSPHERE) ---
            if "Bening" in light_type: mood_cmd = "Ultra-high clarity mountain altitude light, deepest cobalt blue sky, bone-dry environment."
            elif "Sejuk" in light_type: mood_cmd = "8000k ice-cold temp brilliance, glacier-clear atmosphere, zenith sun position."
            elif "Dramatis" in light_type: mood_cmd = "Hard directional side-lighting, pitch-black sharp shadows, high HDR contrast."
            elif "Jelas" in light_type: mood_cmd = "Deeply saturated matte pigments, vivid organic color punch, zero reflections."
            elif "Mendung" in light_type: mood_cmd = "Intense moody overcast lighting, 16-bit color depth, gray-cobalt sky with thick clouds, tactile texture definition."
            elif "Suasana Malam" in light_type: mood_cmd = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim lights, deep indigo-black sky."
            elif "Suasana Alami" in light_type: mood_cmd = "Low-exposure natural sunlight, high local contrast, saturated chlorophyll pigments, micro-textures on leaves."
            else: mood_cmd = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold sun, long sharp shadows."

            # Logika Dialog & DNA Khusus (Hanya yang disebut di Visual)
            d_all_text = " ".join([f"{d['name']}: \"{d['text']}\"" for d in item['dialogs'] if d['text']])
            emotion_ctx = f"Emotion: Reacting to context '{d_all_text}'. " if d_all_text else ""
            dna_str = " ".join([f"STRICT CHARACTER FIDELITY: Maintain facial structure of {c['name']} ({c['desc']}) with 8k skin texture." for c in all_chars_list if c['name'] and c['name'].lower() in vis_lower])

            # Suntik Master Lock hanya di Adegan 1
            current_lock = master_lock_instruction if scene_id == 1 else ""

            st.subheader(f"HASIL PRODUKSI ADEGAN {scene_id}")
            img_final = f"{current_lock}create STATIC photo, 9:16 full-frame. {angle_map.get(item['angle'], '')} {dna_str} {emotion_ctx} Visual: {vis_core_final}. Mood: {mood_cmd}. {master_quality_anchor} {negative_prompt_footer} --ar 9:16"
            vid_final = f"{current_lock}9:16 full-screen video. {shot_map.get(item['shot'], 'Medium Shot')} {e_cam_move}. {dna_str} {emotion_ctx} Visual: {vis_core_final}. Mood: {mood_cmd}. {master_quality_anchor} {negative_prompt_footer}"
            
            c1, c2 = st.columns(2)
            with c1: st.caption("📸 IMAGE PROMPT"); st.code(img_final, language="text")
            with c2: st.caption("🎥 VIDEO PROMPT"); st.code(vid_final, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA | V.1.5.1 | 🪄 JANGAN LUPA GUNAKAN PERCANTIK VISUAL")
