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
        new_row = pd.DataFrame([{
            "Waktu": current_time, "User": user,
            "Total Adegan": total_scenes, "Visual Utama": first_visual[:150]
        }])
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated_df)
    except Exception as e: st.error(f"Gagal mencatat riwayat: {e}")

# ==============================================================================
# 4. CUSTOM CSS (FULL STYLE)
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
    .stTextArea textarea { font-size: 14px !important; line-height: 1.5 !important; min-height: 180px !important; }
    .small-label { font-size: 12px; font-weight: bold; color: #a1a1a1; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 5. HEADER APLIKASI
# ==============================================================================
c_header1, c_header2 = st.columns([8, 2])
with c_header1:
    st.title("📸 PINTAR MEDIA")
    st.info(f"Staf Aktif: {st.session_state.active_user} | Konten yang mantap lahir dari detail adegan yang tepat. 🚀❤️")
with c_header2:
    if st.button("Logout 🚪"): st.session_state.logged_in = False; st.rerun()

# ==============================================================================
# 6. MAPPING & SYNC LOGIC
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
indonesia_camera = ["Ikuti Karakter", "Diam (Tanpa Gerak)", "Zoom Masuk Pelan", "Zoom Keluar Pelan", "Geser Kiri ke Kanan", "Geser Kanan ke Kiri", "Dongak ke Atas", "Tunduk ke Bawah", "Ikuti Objek (Tracking)", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat (Detail)", "Dekat (Wajah)", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Sudut Rendah (Gagah)", "Sudut Tinggi (Kecil)"]
indonesia_angle = ["Normal (Depan)", "Samping (Arah Kamera)", "Berhadapan (Ngobrol)", "Intip Bahu (Framing)", "Wibawa/Gagah (Low Angle)", "Mata Karakter (POV)"]

camera_map = {"Ikuti Karakter": "AUTO_MOOD", "Diam (Tanpa Gerak)": "Static (No Move)", "Zoom Masuk Pelan": "Slow Zoom In", "Zoom Keluar Pelan": "Slow Zoom Out", "Geser Kiri ke Kanan": "Pan Left to Right", "Geser Kanan ke Kiri": "Pan Right to Left", "Dongak ke Atas": "Tilt Up", "Tunduk ke Bawah": "Tilt Down", "Ikuti Objek (Tracking)": "Tracking Shot", "Memutar (Orbit)": "Orbit Circular"}
shot_map = {"Sangat Dekat (Detail)": "Extreme Close-Up", "Dekat (Wajah)": "Close-Up", "Setengah Badan": "Medium Shot", "Seluruh Badan": "Full Body Shot", "Pemandangan Luas": "Wide Landscape Shot", "Sudut Rendah (Gagah)": "Low Angle Shot", "Sudut Tinggi (Kecil)": "High Angle Shot"}
angle_map = {"Normal (Depan)": "", "Samping (Arah Kamera)": "Side profile view, 90-degree angle.", "Berhadapan (Ngobrol)": "Two subjects in profile view, facing each other directly.", "Intip Bahu (Framing)": "Over-the-shoulder framing.", "Wibawa/Gagah (Low Angle)": "Heroic low angle shot.", "Mata Karakter (POV)": "First-person point of view."}

def global_sync_v920():
    st.session_state.m_light = st.session_state.light_input_1
    st.session_state.m_cam = st.session_state.camera_input_1
    st.session_state.m_shot = st.session_state.shot_input_1
    st.session_state.m_angle = st.session_state.angle_input_1
    for i in range(2, 51):
        if f"light_input_{i}" in st.session_state: st.session_state[f"light_input_{i}"] = st.session_state.m_light
        if f"camera_input_{i}" in st.session_state: st.session_state[f"camera_input_{i}"] = st.session_state.m_cam
        if f"shot_input_{i}" in st.session_state: st.session_state[f"shot_input_{i}"] = st.session_state.m_shot
        if f"angle_input_{i}" in st.session_state: st.session_state[f"angle_input_{i}"] = st.session_state.m_angle

# ==============================================================================
# 7. SIDEBAR (ADMIN MONITOR & CONFIG)
# ==============================================================================
with st.sidebar:
    if st.session_state.active_user == "admin":
        st.header("📊 Admin Monitor")
        if st.checkbox("Buka Log Google Sheets"):
            try:
                conn_a = st.connection("gsheets", type=GSheetsConnection)
                df_a = conn_a.read(worksheet="Sheet1", ttl=0)
                st.dataframe(df_a)
            except: st.warning("Gagal memuat Database.")
        st.divider()

    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)

# ==============================================================================
# 8. MEGA QUALITY STACK (UNIVERSAL)
# ==============================================================================
full_quality_stack = (
    "Full-bleed cinematography, edge-to-edge pixel rendering, Full-frame vertical coverage, "
    "zero black borders, expansive background rendering to edges, Circular Polarizer (CPL) filter effect, "
    "eliminates light glare, ultra-high-fidelity resolution, micro-contrast enhancement, optical clarity, "
    "deep saturated pigments, vivid organic color punch, intricate organic textures, skin texture override with 8k details, "
    "f/11 aperture for deep focus sharpness, zero digital noise, zero atmospheric haze, crystal clear background focus. "
    "STRICTLY NO rain, NO wet ground, NO raindrops, NO speech bubbles, NO text, NO typography, NO watermark, NO letters, NO black bars on top and bottom, NO subtitles. --ar 9:16"
)
# Kualitas video yang sedikit berbeda
video_quality_stack = (
    "60fps, fluid motion, professional cinematic quality, deep saturated pigments, zero digital noise, "
    "full-bleed cinematography, edge-to-edge rendering. --ar 9:16"
)

# ==============================================================================
# 9. FORM INPUT ADEGAN
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
with st.expander("👥 Identitas & Fisik Karakter (WAJIB ISI)", expanded=True):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("### Karakter 1")
        c_n1_v = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN").strip()
        c_p1_v = st.text_area("Fisik Karakter 1", key="c_desc_1_input", height=100)
    with col_c2:
        st.markdown("### Karakter 2")
        c_n2_v = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG").strip()
        c_p2_v = st.text_area("Fisik Karakter 2", key="c_desc_2_input", height=100)

    st.divider()
    num_extra = st.number_input("Total Karakter", min_value=2, max_value=10, value=2)
    
    all_chars_list = []
    if c_n1_v: all_chars_list.append({"name": c_n1_v, "desc": c_p1_v})
    if c_n2_v: all_chars_list.append({"name": c_n2_v, "desc": c_p2_v})

    if num_extra > 2:
        extra_cols = st.columns(num_extra - 2)
        for ex_idx in range(2, int(num_extra)):
            with extra_cols[ex_idx - 2]:
                ex_name = st.text_input(f"Nama Karakter {ex_idx + 1}", key=f"ex_name_{ex_idx}").strip()
                ex_phys = st.text_area(f"Fisik Karakter {ex_idx + 1}", key=f"ex_phys_{ex_idx}", height=100)
                if ex_name: all_chars_list.append({"name": ex_name, "desc": ex_phys})

adegan_storage = []
for i_s in range(1, int(num_scenes) + 1):
    l_box_title = f"🟢 MASTER CONTROL - ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
    with st.expander(l_box_title, expanded=(i_s == 1)):
        col_v, col_ctrl = st.columns([6.5, 3.5])
        with col_v:
            visual_input = st.text_area(f"Visual Adegan {i_s}", key=f"vis_input_{i_s}", height=180)
        with col_ctrl:
            r1c1, r1c2 = st.columns(2)
            l_val = r1c1.selectbox(f"💡 Cahaya {i_s}", options_lighting, key=f"light_input_{i_s}", on_change=(global_sync_v920 if i_s==1 else None))
            c_val = r1c2.selectbox(f"🎥 Gerak {i_s}", indonesia_camera, key=f"camera_input_{i_s}", on_change=(global_sync_v920 if i_s==1 else None))
            r2c1, r2c2 = st.columns(2)
            s_val = r2c1.selectbox(f"📐 Shot {i_s}", indonesia_shot, key=f"shot_input_{i_s}", on_change=(global_sync_v920 if i_s==1 else None))
            a_val = r2c2.selectbox(f"✨ Angle {i_s}", indonesia_angle, key=f"angle_input_{i_s}", on_change=(global_sync_v920 if i_s==1 else None))

        diag_cols = st.columns(len(all_chars_list) if all_chars_list else 1)
        scene_dialogs = []
        for i_char, char_data in enumerate(all_chars_list):
            d_in = diag_cols[i_char].text_input(f"Dialog {char_data['name']}", key=f"diag_{i_s}_{i_char}")
            scene_dialogs.append({"name": char_data['name'], "text": d_in})
        
        adegan_storage.append({"num": i_s, "visual": visual_input, "light": l_val, "cam": c_val, "shot": s_val, "angle": a_val, "dialogs": scene_dialogs})

# ==============================================================================
# 10. GENERATOR PROMPT (HIERARCHICAL PRIORITY LOGIC & VIDEO PROMPT RESTORED)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_scenes = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active_scenes: st.warning("Mohon isi deskripsi visual adegan!")
    else:
        record_to_sheets(st.session_state.active_user, active_scenes[0]["visual"], len(active_scenes))
        
        # Sesi Global (Paling Depan)
        master_lock = "STRICT VISUAL SESSION: Characters must remain 100% identical to their initial reference. "

        for item in active_scenes:
            v_low = item["visual"].lower()
            
            # --- TIER 1: CHARACTER DNA (PRIORITAS UTAMA) ---
            dna_parts = []
            for c in all_chars_list:
                if c['name'].lower() in v_low:
                    dna_instruction = (
                        f"IDENTICAL CHARACTER ANCHOR: {c['name']} is ({c['desc']}). "
                        f"STRICT FIDELITY: Re-render this specific identity with 8k skin texture, "
                        f"enhanced contrast, and professional cinematic sharpness. "
                    )
                    dna_parts.append(dna_instruction)
            dna_final = " ".join(dna_parts)

            # --- TIER 2: SCENE & ACTION (VISUALISASI) ---
            vis_core_final = item["visual"] + " (Backrest fixed against house wall, positioned under porch roof)." if "teras" in v_low else item["visual"]
            d_all_text = " ".join([f"{d['name']}: {d['text']}" for d in item['dialogs'] if d['text']])
            emotion_ctx = f"Emotion Context: Reacting to '{d_all_text}'. Focus on facial expressions. " if d_all_text else ""

            # --- TIER 3: LIGHTING & ATMOSPHERE ---
            l_type = item["light"]
            if "Bening" in l_type: l_cmd, a_cmd = "Ultra-high altitude light clarity, extreme micro-contrast.", "10:00 AM mountain sun, deepest cobalt blue sky."
            elif "Mendung" in l_type: l_cmd, a_cmd = "Intense moody overcast, 8000k cold temperature.", "Gray-cobalt sky, tactile texture definition."
            elif "Suasana Malam" in l_type: l_cmd, a_cmd = "Cinematic Night lighting, 9000k moonlit glow.", "Deep indigo-black sky, hyper-defined textures."
            elif "Suasana Sore" in l_type: l_cmd, a_cmd = "4:00 PM indigo atmosphere, sharp rim lighting.", "Late afternoon cold sun, long sharp shadows."
            else: l_cmd, a_cmd = "Natural professional lighting.", "Crystal clear atmosphere." # Default
            
            st.subheader(f"✅ Hasil Adegan {item['num']}")
            c1, c2 = st.columns(2) # Dua kolom untuk Gambar dan Video
            current_lock = master_lock if item['num'] == 1 else ""
            
            # SUSUNAN HIERARKI UNTUK GAMBAR: DNA Karakter -> Visual Adegan -> Kualitas Gambar
            img_final = (
                f"{current_lock} {dna_final} " # DNA Karakter dibaca AI paling awal
                f"Visual Scene: {vis_core_final}. "
                f"Camera: {angle_map.get(item['angle'], '')} {emotion_ctx} "
                f"Atmosphere: {a_cmd}. Lighting: {l_cmd}. "
                f"{full_quality_stack}" # Detail teknis gambar diletakkan paling akhir
            )
            
            # SUSUNAN HIERARKI UNTUK VIDEO: DNA Karakter -> Visual Adegan -> Kualitas Video
            vid_final = (
                f"{current_lock} {dna_final} " # DNA Karakter dibaca AI paling awal
                f"9:16 vertical video. {shot_map.get(item['shot'], 'Medium Shot')} {camera_map.get(item['cam'], 'Static')}. "
                f"Visual Scene: {vis_core_final}. "
                f"Camera: {angle_map.get(item['angle'], '')} {emotion_ctx} "
                f"Atmosphere: {a_cmd}. Lighting: {l_cmd}. "
                f"{video_quality_stack}" # Detail teknis video diletakkan paling akhir
            )

            with c1:
                st.markdown("**🖼️ Prompt Gambar:**")
                st.code(img_final, language="text")
            with c2:
                st.markdown("**▶️ Prompt Video:**")
                st.code(vid_final, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA | V.1.3.6-ULTRA-FIX")
