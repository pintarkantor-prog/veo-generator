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
# 2. DATABASE LINK FOTO (Gunakan Direct Link .png / .jpg)
# ==============================================================================
LINK_REFERENSI = {
    "UDIN": "https://i.ibb.co/qbssssw/UDIN.png",
    "TUNG": "https://i.ibb.co/RG9CgHNx/TUNG.png"
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
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff !important; }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 2px solid #ffffff !important;
        transform: scale(1.1); 
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    .stTextArea textarea { font-size: 14px !important; line-height: 1.5 !important; min-height: 180px !important; }
    .small-label { font-size: 12px; font-weight: bold; color: #a1a1a1; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 6. HEADER APLIKASI (KALIMAT MOTIVASI DIPERTAHANKAN)
# ==============================================================================
c_header1, c_header2 = st.columns([8, 2])
with c_header1:
    st.title("📸 PINTAR MEDIA")
    st.info(f"Staf Aktif: {st.session_state.active_user} | Fokus: Structural Character Match V.1.3.16 🚀❤️")
with c_header2:
    if st.button("Logout 🚪"):
        st.session_state.logged_in = False
        st.rerun()

# ==============================================================================
# 7. MAPPING TRANSLATION (FULL EXPLICIT MANUAL - NO REDUCTION)
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
# 8. SIDEBAR: ADMIN MONITOR & KONFIGURASI (UTUH V.1.1.8)
# ==============================================================================
with st.sidebar:
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
# 9. PARAMETER KUALITAS (FULL MEGA V.1.1.8)
# ==============================================================================
sharp_natural_stack = "Full-bleed cinematography, edge-to-edge pixel rendering, Full-frame vertical coverage, zero black borders, expansive background rendering to edges, Circular Polarizer (CPL) filter effect, eliminates light glare, ultra-high-fidelity resolution, micro-contrast enhancement, optical clarity, deep saturated pigments, vivid organic color punch, intricate organic textures, skin texture override with 8k details, f/11 aperture for deep focus sharpness, zero digital noise, zero atmospheric haze, crystal clear background focus."
no_text_strict = "STRICTLY NO rain, NO wet ground, NO raindrops, NO speech bubbles, NO text, NO typography, NO watermark, NO letters, NO black bars on top and bottom, NO subtitles."
img_quality_base = f"{sharp_natural_stack} {no_text_strict}"
vid_quality_base = f"vertical 9:16 full-screen mobile video, 60fps, fluid organic motion, {sharp_natural_stack} {no_text_strict}"

# ==============================================================================
# 10. FORM INPUT IDENTITAS (AUTO-MATCH LINK)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
with st.expander("👥 Identitas & Fisik Karakter (WAJIB ISI)", expanded=True):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("### Karakter 1")
        c_n1_v = st.text_input("Nama Karakter 1", value="UDIN", key="c_name_1_input")
        c_p1_v = st.text_area("Fisik Karakter 1 (STRICT DNA)", value="", key="c_desc_1_input", height=100)
    with col_c2:
        st.markdown("### Karakter 2")
        c_n2_v = st.text_input("Nama Karakter 2", value="TUNG", key="c_name_2_input")
        c_p2_v = st.text_area("Fisik Karakter 2 (STRICT DNA)", value="", key="c_desc_2_input", height=100)

    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=10, value=2)
    u1_auto = LINK_REFERENSI.get(c_n1_v.upper().strip(), "")
    u2_auto = LINK_REFERENSI.get(c_n2_v.upper().strip(), "")
    all_chars_list = []
    all_chars_list.append({"name": c_n1_v, "desc": c_p1_v, "url": u1_auto})
    all_chars_list.append({"name": c_n2_v, "desc": c_p2_v, "url": u2_auto})
    if num_extra > 2:
        extra_cols = st.columns(num_extra - 2)
        for ex_idx in range(2, int(num_extra)):
            with extra_cols[ex_idx - 2]:
                ex_name = st.text_input(f"Nama Karakter {ex_idx + 1}", key=f"ex_name_{ex_idx}")
                ex_phys = st.text_area(f"Fisik Karakter {ex_idx + 1}", key=f"ex_phys_{ex_idx}", height=100)
                ex_url_auto = LINK_REFERENSI.get(ex_name.upper().strip(), "") if ex_name else ""
                all_chars_list.append({"name": ex_name, "desc": ex_phys, "url": ex_url_auto})

# ==============================================================================
# 11. LIST ADEGAN (FULL MEGA V.1.1.8)
# ==============================================================================
adegan_storage = []
for i_s in range(1, int(num_scenes) + 1):
    l_box_title = f"🟢 MASTER CONTROL - ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
    with st.expander(l_box_title, expanded=(i_s == 1)):
        col_v, col_ctrl = st.columns([6.5, 3.5])
        with col_v:
            visual_input = st.text_area(f"Visual Adegan {i_s}", key=f"vis_input_{i_s}", height=180)
        with col_ctrl:
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
                idx_l = options_lighting.index(st.session_state.m_light)
                l_val = st.selectbox(f"L{i_s}", options_lighting, index=idx_l, key=f"light_input_{i_s}", on_change=global_sync_v920 if i_s == 1 else None, label_visibility="collapsed")
            with r1c2:
                st.markdown('<p class="small-label">🎥 Gerak</p>', unsafe_allow_html=True)
                idx_c = indonesia_camera.index(st.session_state.m_cam)
                c_val = st.selectbox(f"C{i_s}", indonesia_camera, index=idx_c, key=f"camera_input_{i_s}", on_change=global_sync_v920 if i_s == 1 else None, label_visibility="collapsed")
            r2c1, r2c2 = st.columns(2)
            with r2c1:
                st.markdown('<p class="small-label">📐 Shot</p>', unsafe_allow_html=True)
                idx_s = indonesia_shot.index(st.session_state.m_shot)
                s_val = st.selectbox(f"S{i_s}", indonesia_shot, index=idx_s, key=f"shot_input_{i_s}", on_change=global_sync_v920 if i_s == 1 else None, label_visibility="collapsed")
            with r2c2:
                st.markdown('<p class="small-label">✨ Angle</p>', unsafe_allow_html=True)
                idx_a = indonesia_angle.index(st.session_state.m_angle)
                a_val = st.selectbox(f"A{i_s}", indonesia_angle, index=idx_a, key=f"angle_input_{i_s}", on_change=global_sync_v920 if i_s == 1 else None, label_visibility="collapsed")
        diag_cols = st.columns(len(all_chars_list))
        scene_dialogs_list = []
        for i_char, char_data in enumerate(all_chars_list):
            with diag_cols[i_char]:
                d_in = st.text_input(f"Dialog {char_data['name']}", key=f"diag_{i_s}_{i_char}")
                scene_dialogs_list.append({"name": char_data['name'], "text": d_in})
        adegan_storage.append({"num": i_s, "visual": visual_input, "light": l_val, "cam": c_val, "shot": s_val, "angle": a_val, "dialogs": scene_dialogs_list})

st.divider()

# ==============================================================================
# 12. GENERATOR PROMPT (PEMISAHAN TUGAS - STRUCTURAL ANCHOR V.1.3.16)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active_scenes = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active_scenes:
        st.warning("Mohon isi deskripsi visual adegan!")
    else:
        record_to_sheets(st.session_state.active_user, active_scenes[0]["visual"], len(active_scenes))
        
        # FIX: LINK TELANJANG DI PALING DEPAN (IMAGE PROMPT MODE)
        ref_links_only = " ".join([f"[{c['url']}]" for c in all_chars_list if c['url']]) + " "
        
        # MASTER IDENTITY (Hanya bicara struktur wajah dan tubuh dari link)
        master_identity = "STRUCTURAL CHARACTER ANCHOR: Use the provided image links as the absolute reference for facial identity and body proportions. "

        for item in active_scenes:
            vis_lower = item["visual"].lower()
            
            # CAMERA MOVEMENT & LIGHTING (FULL EXPLICIT V.1.1.8)
            if camera_map.get(item["cam"]) == "AUTO_MOOD":
                if any(x in vis_lower for x in ["lari", "jalan", "mobil"]): e_cam_move = "Dynamic Tracking Shot"
                elif "sedih" in vis_lower: e_cam_move = "Slow Cinematic Zoom In"
                else: e_cam_move = "Subtle cinematic camera drift"
            else: e_cam_move = camera_map.get(item["cam"], "Static")

            l_type = item["light"]
            if "Bening" in l_type:
                l_cmd, a_cmd = "Ultra-high altitude light visibility, extreme micro-contrast.", "10:00 AM sun, deepest cobalt blue sky."
            elif "Mendung" in l_type:
                l_cmd, a_cmd = "Intense moody overcast lighting, vivid recovery.", "Gray-cobalt sky gradient."
            else:
                l_cmd, a_cmd = "Natural cinematic lighting.", "Clear 8k definition, zero digital noise."

            # DNA INJECTION (STRICT FACE & BODY)
            dna_injection = ""
            for idx, c in enumerate(all_chars_list):
                if c['name'].lower() in vis_lower:
                    dna_injection += f"ABSOLUTE CHARACTER FIDELITY: Maintain face and body anatomy of {c['name']} from link #{idx+1}. "

            # Karakter Deskripsi (BAJU & AKSESORIS) diletakkan di bagian VISUAL SCENE agar tidak menimpa WAJAH
            char_visual_traits = ", ".join([f"{c['name']} wearing ({c['desc']})" for c in all_chars_list if c['name'] and c['name'].lower() in vis_lower])

            st.subheader(f"✅ Hasil Adegan {item['num']}")
            # HASIL AKHIR: [URL] [MASTER IDENTITY] [DNA] Visual Scene + Baju ...
            img_final = f"{ref_links_only}{master_identity}STATIC photograph, 9:16. {dna_injection} Visual scene: {item['visual']}. {char_visual_traits}. {a_cmd} {l_cmd} {img_quality_base} --ar 9:16"
            vid_final = f"{ref_links_only}{master_identity}9:16 video. {shot_map.get(item['shot'], 'Medium')} perspective. {dna_injection} Visual scene: {item['visual']}. {char_visual_traits}. {e_cam_move}. {l_cmd} {vid_quality_base}"
            
            c1, c2 = st.columns(2)
            with c1: st.code(img_final)
            with c2: st.code(vid_final)
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA | V.1.3.16")
