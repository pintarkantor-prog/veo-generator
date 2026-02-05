import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MANUAL SETUP - MEGA STRUCTURE)
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. DATABASE KARAKTER CEPAT (UDIN & TUNG)
# ==============================================================================
DB_KARAKTER = {
    "Pilih dari Database": {"deskripsi": "", "url": ""},
    "UDIN": {
        "deskripsi": "si kepala jeruk",
        "url": "https://drive.google.com/uc?export=download&id=1f51O-_PpHdXdGQkngsTh5b1fJjHtx5l5"
    },
    "TUNG": {
        "deskripsi": "si kepala kayu",
        "url": "https://drive.google.com/uc?export=download&id=1r94LHZSEwaurGViq1lGZ9ptPr0FOrcS5"
    }
}

# ==============================================================================
# 3. SISTEM LOGIN & DATABASE USER (MANUAL EXPLICIT - TIDAK DIRUBAH)
# ==============================================================================
USERS = {
    "admin": "QWERTY21ab",
    "icha": "udin99",
    "nissa": "tung22"
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'active_user' not in st.session_state:
    st.session_state.active_user = ""

# Layar Login Manual
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
# 4. LOGIKA LOGGING GOOGLE SHEETS (SERVICE ACCOUNT MODE)
# ==============================================================================
def record_to_sheets(user, first_visual, total_scenes):
    """Mencatat aktivitas karyawan menggunakan Service Account Secrets"""
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
        st.error(f"Gagal mencatat riwayat ke Google Sheets: {e}")


# ==============================================================================
# 5. CUSTOM CSS (FULL EXPLICIT STYLE - NO REDUCTION)
# ==============================================================================
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 2px solid #ffffff !important;
        transform: scale(1.1); 
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    .stTextArea textarea {
        font-size: 14px !important;
        line-height: 1.5 !important;
        font-family: 'Inter', sans-serif !important;
        min-height: 180px !important; 
    }
    .small-label {
        font-size: 12px;
        font-weight: bold;
        color: #a1a1a1;
        margin-bottom: 2px;
    }
    </style>
    """, unsafe_allow_html=True)


# ==============================================================================
# 6. HEADER APLIKASI
# ==============================================================================
c_header1, c_header2 = st.columns([8, 2])
with c_header1:
    st.title("📸 PINTAR MEDIA")
    st.info(f"Staf Aktif: {st.session_state.active_user} | Konten yang mantap lahir dari detail adegan yang tepat. Semangat kerjanya! 🚀❤️")
with c_header2:
    if st.button("Logout 🚪"):
        st.session_state.logged_in = False
        st.rerun()


# ==============================================================================
# 7. SIDEBAR: ADMIN MONITOR & KONFIGURASI (KEMBALI UTUH)
# ==============================================================================
with st.sidebar:
    # --- BLOK ADMIN MONITOR (SUDAH DIKEMBALIKAN) ---
    if st.session_state.active_user == "admin":
        st.header("📊 Admin Monitor")
        if st.checkbox("Buka Log Google Sheets"):
            try:
                conn_a = st.connection("gsheets", type=GSheetsConnection)
                df_a = conn_a.read(worksheet="Sheet1", ttl=0)
                st.dataframe(df_a)
            except Exception as e:
                st.warning(f"Gagal memuat Database: {e}")
        st.divider()

    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)


# ==============================================================================
# 8. MAPPING TRANSLATION (FULL EXPLICIT MANUAL - NO REDUCTION)
# ==============================================================================
indonesia_camera = ["Ikuti Karakter", "Diam (Tanpa Gerak)", "Zoom Masuk Pelan", "Zoom Keluar Pelan", "Geser Kiri ke Kanan", "Geser Kanan ke Kiri", "Dongak ke Atas", "Tunduk ke Bawah", "Ikuti Objek (Tracking)", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat (Detail)", "Dekat (Wajah)", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Sudut Rendah (Gagah)", "Sudut Tinggi (Kecil)"]
indonesia_angle = ["Normal (Depan)", "Samping (Arah Kamera)", "Berhadapan (Ngobrol)", "Intip Bahu (Framing)", "Wibawa/Gagah (Low Angle)", "Mata Karakter (POV)"]
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

camera_map = {
    "Ikuti Karakter": "AUTO_MOOD", "Diam (Tanpa Gerak)": "Static (No Move)", "Zoom Masuk Pelan": "Slow Zoom In", 
    "Zoom Keluar Pelan": "Slow Zoom Out", "Geser Kiri ke Kanan": "Pan Left to Right", "Geser Kanan ke Kiri": "Pan Right to Left", 
    "Dongak ke Atas": "Tilt Up", "Tunduk ke Bawah": "Tilt Down", "Ikuti Objek (Tracking)": "Tracking Shot", "Memutar (Orbit)": "Orbit Circular"
}
shot_map = {
    "Sangat Dekat (Detail)": "Extreme Close-Up", "Dekat (Wajah)": "Close-Up", "Setengah Badan": "Medium Shot",
    "Seluruh Badan": "Full Body Shot", "Pemandangan Luas": "Wide Landscape Shot", "Sudut Rendah (Gagah)": "Low Angle Shot", "Sudut Tinggi (Kecil)": "High Angle Shot"
}
angle_map = {
    "Normal (Depan)": "",
    "Samping (Arah Kamera)": "Side profile view, 90-degree angle, subject positioned on the side to show environmental depth and the street ahead.",
    "Berhadapan (Ngobrol)": "Two subjects in profile view, facing each other directly, strict eye contact, bodies turned away from the camera.",
    "Intip Bahu (Framing)": "Over-the-shoulder framing, using foreground elements like window frames or shoulders to create a voyeuristic look.",
    "Wibawa/Gagah (Low Angle)": "Heroic low angle shot, camera looking up at the subject to create a powerful and majestic presence.",
    "Mata Karakter (POV)": "First-person point of view, looking through the character's eyes, immersive perspective."
}

# DEFAULT SETTINGS (V.1.1.7)
if 'm_light' not in st.session_state: st.session_state.m_light = "Bening dan Tajam"
if 'm_cam' not in st.session_state: st.session_state.m_cam = "Ikuti Karakter"
if 'm_shot' not in st.session_state: st.session_state.m_shot = "Setengah Badan"
if 'm_angle' not in st.session_state: st.session_state.m_angle = "Normal (Depan)"

def global_sync_v920():
    lt1 = st.session_state.light_input_1
    cm1 = st.session_state.camera_input_1
    st1 = st.session_state.shot_input_1
    ag1 = st.session_state.angle_input_1
    st.session_state.m_light = lt1
    st.session_state.m_cam = cm1
    st.session_state.m_shot = st1
    st.session_state.m_angle = ag1
    for key in st.session_state.keys():
        if key.startswith("light_input_"): st.session_state[key] = lt1
        if key.startswith("camera_input_"): st.session_state[key] = cm1
        if key.startswith("shot_input_"): st.session_state[key] = st1
        if key.startswith("angle_input_"): st.session_state[key] = ag1


# ==============================================================================
# 9. PARAMETER KUALITAS (FULL EXPLICIT)
# ==============================================================================
sharp_natural_stack = (
    "Full-bleed cinematography, edge-to-edge pixel rendering, Full-frame vertical coverage, zero black borders, "
    "expansive background rendering to edges, Circular Polarizer (CPL) filter effect, eliminates light glare, "
    "ultra-high-fidelity resolution, micro-contrast enhancement, optical clarity, deep saturated pigments, "
    "vivid organic color punch, intricate organic textures, skin texture override with 8k details, "
    "f/11 aperture for deep focus sharpness, zero digital noise, zero atmospheric haze, crystal clear background focus."
)
no_text_strict = "STRICTLY NO rain, NO wet ground, NO raindrops, NO speech bubbles, NO text, NO typography, NO watermark, NO letters, NO black bars on top and bottom, NO subtitles."
img_quality_base = f"{sharp_natural_stack} {no_text_strict}"
vid_quality_base = f"vertical 9:16 full-screen mobile video, 60fps, fluid organic motion, {sharp_natural_stack} {no_text_strict}"


# ==============================================================================
# 10. FORM INPUT IDENTITAS (WITH DB SELECTOR & MANUAL OVERRIDE)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")

with st.expander("👥 Identitas & Fisik Karakter (WAJIB ISI)", expanded=True):
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        st.markdown("### Karakter 1")
        sel_db1 = st.selectbox("Cari di Database K1", list(DB_KARAKTER.keys()), key="sel_db_1")
        def_n1 = sel_db1 if sel_db1 != "Pilih dari Database" else "UDIN"
        def_p1 = DB_KARAKTER[sel_db1]["deskripsi"] if sel_db1 != "Pilih dari Database" else ""
        def_u1 = DB_KARAKTER[sel_db1]["url"] if sel_db1 != "Pilih dari Database" else ""
        c_n1_v = st.text_input("Nama Karakter 1", value=def_n1, key="c_name_1_input")
        c_p1_v = st.text_area("Fisik Karakter 1 (STRICT DNA)", value=def_p1, key="c_desc_1_input", height=100)
        c_u1_v = st.text_input("Link Foto Referensi 1", value=def_u1, key="c_url_1_input")
    
    with col_c2:
        st.markdown("### Karakter 2")
        sel_db2 = st.selectbox("Cari di Database K2", list(DB_KARAKTER.keys()), key="sel_db_2")
        def_n2 = sel_db2 if sel_db2 != "Pilih dari Database" else "TUNG"
        def_p2 = DB_KARAKTER[sel_db2]["deskripsi"] if sel_db2 != "Pilih dari Database" else ""
        def_u2 = DB_KARAKTER[sel_db2]["url"] if sel_db2 != "Pilih dari Database" else ""
        c_n2_v = st.text_input("Nama Karakter 2", value=def_n2, key="c_name_2_input")
        c_p2_v = st.text_area("Fisik Karakter 2 (STRICT DNA)", value=def_p2, key="c_desc_2_input", height=100)
        c_u2_v = st.text_input("Link Foto Referensi 2", value=def_u2, key="c_url_2_input")

    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=10, value=2)
    all_chars_list = []
    all_chars_list.append({"name": c_n1_v, "desc": c_p1_v, "url": c_u1_v})
    all_chars_list.append({"name": c_n2_v, "desc": c_p2_v, "url": c_u2_v})

    if num_extra > 2:
        extra_cols = st.columns(num_extra - 2)
        for ex_idx in range(2, int(num_extra)):
            with extra_cols[ex_idx - 2]:
                st.markdown(f"### Karakter {ex_idx + 1}")
                ex_name = st.text_input(f"Nama Karakter {ex_idx + 1}", key=f"ex_name_{ex_idx}")
                ex_phys = st.text_area(f"Fisik Karakter {ex_idx + 1}", key=f"ex_phys_{ex_idx}", height=100)
                ex_url = st.text_input(f"Link Foto {ex_idx + 1}", key=f"ex_url_{ex_idx}")
                all_chars_list.append({"name": ex_name, "desc": ex_phys, "url": ex_url})


# ==============================================================================
# 11. LIST ADEGAN (FULL GRID & SYNC)
# ==============================================================================
adegan_storage = []
for i_s in range(1, int(num_scenes) + 1):
    l_box_title = f"🟢 MASTER CONTROL - ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
    with st.expander(l_box_title, expanded=(i_s == 1)):
        col_v, col_ctrl = st.columns([6.5, 3.5])
        with col_v:
            visual_input = st.text_area(f"Visual Adegan {i_s}", key=f"vis_input_{i_s}", height=180)
        with col_ctrl:
            r1_c1, r1_c2 = st.columns(2)
            with r1_c1:
                st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
                idx_l = options_lighting.index(st.session_state.m_light)
                l_val = st.selectbox(f"L{i_s}", options_lighting, index=idx_l, key=f"light_input_{i_s}", on_change=global_sync_v920 if i_s == 1 else None, label_visibility="collapsed")
            with r1_c2:
                st.markdown('<p class="small-label">🎥 Gerak</p>', unsafe_allow_html=True)
                idx_c = indonesia_camera.index(st.session_state.m_cam)
                c_val = st.selectbox(f"C{i_s}", indonesia_camera, index=idx_c, key=f"camera_input_{i_s}", on_change=global_sync_v920 if i_s == 1 else None, label_visibility="collapsed")
            r2_c1, r2_c2 = st.columns(2)
            with r2_c1:
                st.markdown('<p class="small-label">📐 Shot</p>', unsafe_allow_html=True)
                idx_s = indonesia_shot.index(st.session_state.m_shot)
                s_val = st.selectbox(f"S{i_s}", indonesia_shot, index=idx_s, key=f"shot_input_{i_s}", on_change=global_sync_v920 if i_s == 1 else None, label_visibility="collapsed")
            with r2_c2:
                st.markdown('<p class="small-label">✨ Angle</p>', unsafe_allow_html=True)
                idx_a = indonesia_angle.index(st.session_state.m_angle)
                a_val = st.selectbox(f"A{i_s}", indonesia_angle, index=idx_a, key=f"angle_input_{i_s}", on_change=global_sync_v920 if i_s == 1 else None, label_visibility="collapsed")

        diag_cols = st.columns(len(all_chars_list))
        scene_dialogs_list = []
        for i_char, char_data in enumerate(all_chars_list):
            with diag_cols[i_char]:
                char_label = char_data['name'] if char_data['name'] else f"Tokoh {i_char+1}"
                d_in = st.text_input(f"Dialog {char_label}", key=f"diag_{i_s}_{i_char}")
                scene_dialogs_list.append({"name": char_label, "text": d_in})
        adegan_storage.append({"num": i_s, "visual": visual_input, "light": l_val, "cam": c_val, "shot": s_val, "angle": a_val, "dialogs": scene_dialogs_list})


# ==============================================================================
# 12. GENERATOR PROMPT (FULL MEGA STRUCTURE)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_scenes = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active_scenes:
        st.warning("Mohon isi deskripsi visual adegan!")
    else:
        record_to_sheets(st.session_state.active_user, active_scenes[0]["visual"], len(active_scenes))
        char_defs_full = ", ".join([f"Karakter {idx+1} ({c['name']}: {c['desc']})" for idx, c in enumerate(all_chars_list) if c['name']])
        master_lock_instruction = f"IMPORTANT: Remember ini characters: {char_defs_full}. "

        for item in active_scenes:
            vis_core = item["visual"]
            vis_lower = vis_core.lower()
            
            # CAMERA MOVEMENT AUTO (FULL V.1.1.8 LOGIC)
            if camera_map.get(item["cam"]) == "AUTO_MOOD":
                if any(x in vis_lower for x in ["lari", "jalan", "pergi", "mobil"]): e_cam_move = "Dynamic Tracking Shot"
                elif any(x in vis_lower for x in ["sedih", "menangis", "fokus"]): e_cam_move = "Slow Cinematic Zoom In"
                elif any(x in vis_lower for x in ["pemandangan", "kota", "luas"]): e_cam_move = "Slow Pan Left to Right"
                elif any(x in vis_lower for x in ["marah", "teriak", "berantem"]): e_cam_move = "Handheld Shaky Cam intensity"
                else: e_cam_move = "Subtle cinematic camera drift"
            else: e_cam_move = camera_map.get(item["cam"], "Static")

            if "teras" in vis_lower: vis_core_final = vis_core + " (Backrest fixed against the house wall, porch roof anchored)."
            else: vis_core_final = vis_core

            e_shot_size = shot_map.get(item["shot"], "Medium Shot")
            e_angle_cmd = angle_map.get(item["angle"], "")
            scene_id = item["num"]
            light_type = item["light"]
            
            # LIGHTING MAPPING (FULL MEGA)
            if "Bening" in light_type:
                l_cmd = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast."
                a_cmd = "10:00 AM mountain sun, deepest cobalt blue sky."
            elif "Mendung" in light_type:
                l_cmd = "Intense moody overcast lighting, vivid pigment recovery, thick wispy clouds."
                a_cmd = "Moody atmosphere, zero haze, gray-cobalt sky gradient."
            else:
                l_cmd = "Natural cinematic lighting, professional highlight control."
                a_cmd = "Clear atmosphere, 8k texture definition."

            d_all_text = " ".join([f"{d['name']}: \"{d['text']}\"" for d in item['dialogs'] if d['text']])
            emotion_ctx = f"Emotion Context (DO NOT RENDER TEXT): Reacting to: '{d_all_text}'. " if d_all_text else ""

            # DNA & URL INJECTION
            url_prefix, dna_str = "", ""
            for c in all_chars_list:
                if c['name'] and c['name'].lower() in vis_lower:
                    if c['url']: url_prefix += f"[{c['url']}] "
                    dna_str += f"STRICT CHARACTER FIDELITY: Maintain facial identity of {c['name']} ({c['desc']}). "

            st.subheader(f"✅ Hasil Adegan {scene_id}")
            img_final = f"{url_prefix}{master_lock_instruction if scene_id==1 else ''}STATIC photo, 9:16. {e_angle_cmd} {emotion_ctx}{dna_str} Visual: {vis_core_final}. {a_cmd} {l_cmd} {img_quality_base} --ar 9:16"
            vid_final = f"{url_prefix}{master_lock_instruction if scene_id==1 else ''}9:16 video. {e_shot_size} perspective. {e_angle_cmd} {e_cam_move}. {emotion_ctx}{dna_str} Visual: {vis_core_final}. {l_cmd} {vid_quality_base}"
            
            c1, c2 = st.columns(2)
            with c1: st.code(img_final)
            with c2: st.code(vid_final)
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA | V.1.2.5")
