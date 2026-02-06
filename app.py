import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz #

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MANUAL SETUP - MEGA STRUCTURE)
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. SISTEM LOGIN & DATABASE USER (SINKRONISASI MEMORI TOTAL)
# ==============================================================================
USERS = {
    "admin": "QWERTY21ab",
    "icha": "udin99",
    "nissa": "tung22",
    "inggi": "udin33",
    "lisa": "tung66"
}

# --- 1. INISIALISASI DASAR ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'active_user' not in st.session_state:
    st.session_state.active_user = ""
if 'last_generated_results' not in st.session_state:
    st.session_state.last_generated_results = []

# --- 2. BOOKING MEMORI UNTUK INPUT (AGAR ANTI-HILANG SAAT REFRESH) ---
# Kita amankan input Tokoh
if 'c_name_1_input' not in st.session_state: st.session_state.c_name_1_input = ""
if 'c_desc_1_input' not in st.session_state: st.session_state.c_desc_1_input = ""
if 'c_name_2_input' not in st.session_state: st.session_state.c_name_2_input = ""
if 'c_desc_2_input' not in st.session_state: st.session_state.c_desc_2_input = ""

# Kita amankan input Adegan (v1 sampai v50) secara otomatis
for i in range(1, 51):
    vk = f"vis_input_{i}"
    lk = f"light_input_{i}"
    ck = f"camera_input_{i}"
    sk = f"shot_input_{i}"
    ak = f"angle_input_{i}"
    if vk not in st.session_state: st.session_state[vk] = ""
    if lk not in st.session_state: st.session_state[lk] = "Bening dan Tajam"
    if ck not in st.session_state: st.session_state[ck] = "Ikuti Karakter"
    if sk not in st.session_state: st.session_state[sk] = "Setengah Badan"
    if ak not in st.session_state: st.session_state[ak] = "Normal (Depan)"

# --- 3. FITUR ANTI-REFRESH URL ---
query_params = st.query_params
if not st.session_state.logged_in:
    if "u" in query_params and "p" in query_params:
        u_param = query_params["u"]
        p_param = query_params["p"]
        if u_param in USERS and USERS[u_param] == p_param:
            st.session_state.logged_in = True
            st.session_state.active_user = u_param

# --- 4. LAYAR LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 PINTAR MEDIA - AKSES PRODUKSI")
    with st.form("form_login_staf"):
        input_user = st.text_input("Username")
        input_pass = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk Ke Sistem"):
            if input_user in USERS and USERS[input_user] == input_pass:
                st.session_state.logged_in = True
                st.session_state.active_user = input_user
                st.query_params["u"] = input_user
                st.query_params["p"] = input_pass
                st.rerun()
            else:
                st.error("Username atau Password Salah!")
    st.stop()
    
# ==============================================================================
# 3. LOGIKA LOGGING GOOGLE SHEETS (SERVICE ACCOUNT MODE - FULL DATA)
# ==============================================================================
def record_to_sheets(user, data_packet, total_scenes):
    """Mencatat aktivitas. Jika data_packet adalah JSON (Draft), simpan utuh."""
    try:
        # 1. Koneksi (Gunakan TTL agar hemat kuota)
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 2. Baca data lama (Kasih TTL agar tidak kena Error 429)
        existing_data = conn.read(worksheet="Sheet1", ttl="5m")
        
        # 3. Setting Waktu Jakarta (WIB)
        tz = pytz.timezone('Asia/Jakarta')
        current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        
        # 4. Buat baris baru (PASTIKAN TIDAK ADA [:150])
        new_row = pd.DataFrame([{
            "Waktu": current_time,
            "User": user,
            "Total Adegan": total_scenes,
            "Visual Utama": data_packet # <--- Di sini data koper disimpan utuh
        }])
        
        # 5. Gabungkan data lama dan baru
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        
        # 6. Batasi history maksimal 300 baris agar tidak berat
        if len(updated_df) > 300:
            updated_df = updated_df.tail(300)
        
        # 7. Update kembali ke Google Sheets
        conn.update(worksheet="Sheet1", data=updated_df)
        
    except Exception as e:
        # Menampilkan error agar kamu tahu kalau koneksinya bermasalah
        st.error(f"Gagal mencatat ke Cloud: {e}")
        
# ==============================================================================
# 4. CUSTOM CSS (VERSION: BRUTE FORCE FIXED HEADER)
# ==============================================================================
st.markdown("""
    <style>
    /* 1. PAKSA BARIS PERTAMA (INFO STAF) UNTUK FIXED */
    /* Kita tembak container urutan pertama di area main */
    [data-testid="stMainViewContainer"] section.main div.block-container > div:nth-child(1) {
        position: fixed;
        top: 0;
        left: 310px; /* Lebar Sidebar */
        right: 0;
        z-index: 99999;
        background-color: #0e1117;
        padding: 10px 2rem;
        border-bottom: 2px solid #31333f;
    }

    /* Penyesuaian Mobile */
    @media (max-width: 768px) {
        [data-testid="stMainViewContainer"] section.main div.block-container > div:nth-child(1) {
            left: 0;
        }
    }

    /* 2. STYLE SIDEBAR & WIDGET (TETAP SAMA) */
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
        font-size: 12px; font-weight: bold; color: #a1a1a1; margin-bottom: 2px;
    }
    </style>
    """, unsafe_allow_html=True)
# ==============================================================================
# 5. HEADER STAF (AUTO-FIXED BY CSS)
# ==============================================================================
# Elemen ini otomatis akan diam di atas karena CSS nth-child(1) di atas
col_staf, col_logout = st.columns([8, 2])

with col_staf:
    nama_display = st.session_state.active_user.capitalize()
    st.success(f"👤 **Staf Aktif: {nama_display}** | Konten yang mantap lahir dari detail adegan yang tepat. 🚀❤️")

with col_logout:
    if st.button("Logout 🚪", use_container_width=True, key="btn_logout_fix"):
        st.query_params.clear()
        st.session_state.logged_in = False
        st.session_state.active_user = ""
        st.session_state.last_generated_results = []
        st.rerun()
        
# ==============================================================================
# 6. MAPPING TRANSLATION (FULL EXPLICIT MANUAL)
# ==============================================================================
indonesia_camera = [
    "Ikuti Karakter", 
    "Diam (Tanpa Gerak)", 
    "Zoom Masuk Pelan", 
    "Zoom Keluar Pelan", 
    "Geser Kiri ke Nanan", 
    "Geser Kanan ke Kiri", 
    "Dongak ke Atas", 
    "Tunduk ke Bawah", 
    "Ikuti Objek (Tracking)", 
    "Memutar (Orbit)"
]

indonesia_shot = [
    "Sangat Dekat (Detail)", 
    "Dekat (Wajah)", 
    "Setengah Badan", 
    "Seluruh Badan", 
    "Pemandangan Luas", 
    "Sudut Rendah (Gagah)", 
    "Sudut Tinggi (Kecil)"
]

indonesia_angle = [
    "Normal (Depan)",
    "Samping (Arah Kamera)", 
    "Berhadapan (Ngobrol)", 
    "Intip Bahu (Framing)", 
    "Wibawa/Gagah (Low Angle)", 
    "Mata Karakter (POV)"
]

camera_map = {
    "Ikuti Karakter": "AUTO_MOOD", 
    "Diam (Tanpa Gerak)": "Static (No Move)", 
    "Zoom Masuk Pelan": "Slow Zoom In", 
    "Zoom Keluar Pelan": "Slow Zoom Out",
    "Geser Kiri ke Nanan": "Pan Left to Right", 
    "Geser Kanan ke Kiri": "Pan Right to Left", 
    "Dongak ke Atas": "Tilt Up",
    "Tunduk ke Bawah": "Tilt Down", 
    "Ikuti Objek (Tracking)": "Tracking Shot", 
    "Memutar (Orbit)": "Orbit Circular"
}

shot_map = {
    "Sangat Dekat (Detail)": "Extreme Close-Up", 
    "Dekat (Wajah)": "Close-Up", 
    "Setengah Badan": "Medium Shot",
    "Seluruh Badan": "Full Body Shot", 
    "Pemandangan Luas": "Wide Landscape Shot", 
    "Sudut Rendah (Gagah)": "Low Angle Shot",
    "Sudut Tinggi (Kecil)": "High Angle Shot"
}

angle_map = {
    "Normal (Depan)": "",
    "Samping (Arah Kamera)": "Side profile view, 90-degree angle, subject positioned on the side to show environmental depth and the street ahead.",
    "Berhadapan (Ngobrol)": "Two subjects in profile view, facing each other directly, strict eye contact, bodies turned away from the camera.",
    "Intip Bahu (Framing)": "Over-the-shoulder framing, using foreground elements like window frames or shoulders to create a voyeuristic look.",
    "Wibawa/Gagah (Low Angle)": "Heroic low angle shot, camera looking up at the subject to create a powerful and majestic presence.",
    "Mata Karakter (POV)": "First-person point of view, looking through the character's eyes, immersive perspective."
}

options_lighting = [
    "Bening dan Tajam", 
    "Sejuk dan Terang", 
    "Dramatis", 
    "Jelas dan Solid", 
    "Suasana Sore", 
    "Mendung", 
    "Suasana Malam", 
    "Suasana Alami"
]

# INISIALISASI SESSION STATE AWAL (Mencegah ValueError)
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
# 7. SIDEBAR: KONFIGURASI UTAMA (CLEAN UI + DOUBLE NOTIF SUCCESS)
# ==============================================================================
with st.sidebar:
    st.title("📸 PINTAR MEDIA")
    
    # --- A. LOGIKA ADMIN ---
    if st.session_state.active_user == "admin":
        if st.checkbox("🚀 Buka Dashboard Utama", value=False):
            st.info("Log aktivitas tercatat di Cloud.")
        st.divider()

    # --- B. KONFIGURASI UMUM ---
    num_scenes = st.number_input("Tambah Jumlah Adegan", min_value=1, max_value=50, value=6)
    
    # --- STATUS PRODUKSI (Hanya muncul jika sudah ada hasil) ---
    if st.session_state.last_generated_results:
        st.markdown("### 🗺️ STATUS PRODUKSI")
        total_p = len(st.session_state.last_generated_results)
        done_p = 0
        
        # List adegan dengan checkbox
        for res in st.session_state.last_generated_results:
            done_key = f"mark_done_{res['id']}"
            if st.checkbox(f"Adegan {res['id']}", key=done_key):
                done_p += 1
        
        # Progress Bar
        st.progress(done_p / total_p)
        
        # --- EFEK SELEBRASI (BALON) ---
        if done_p == total_p and total_p > 0:
            st.balloons() # Munculkan balon di layar
            st.success("🎉 Semua Adegan Selesai!")
    
    st.divider()

    # --- C. TOMBOL SAVE & RESTORE ---
    c_s, c_r = st.columns(2)
    
    with c_s:
        if st.button("💾 SAVE", use_container_width=True):
            import json
            try:
                # 1. Ambil Visual yang terisi
                captured_scenes = {f"v{i}": st.session_state.get(f"vis_input_{i}") for i in range(1, int(num_scenes) + 1) if st.session_state.get(f"vis_input_{i}")}
                
                # 2. Ambil SEMUA Dialog
                captured_dialogs = {}
                for i_s in range(1, int(num_scenes) + 1):
                    for i_char in range(7): 
                        d_key = f"diag_{i_s}_{i_char}"
                        if d_key in st.session_state and st.session_state[d_key]:
                            captured_dialogs[d_key] = st.session_state[d_key]

                draft_packet = {
                    "n1": st.session_state.get("c_name_1_input", ""), 
                    "p1": st.session_state.get("c_desc_1_input", ""),
                    "n2": st.session_state.get("c_name_2_input", ""), 
                    "p2": st.session_state.get("c_desc_2_input", ""),
                    "scenes": captured_scenes,
                    "dialogs": captured_dialogs 
                }
                record_to_sheets(f"DRAFT_{st.session_state.active_user}", json.dumps(draft_packet), len(captured_scenes))
                
                # TITIP PESAN SUKSES SAVE
                st.session_state["sidebar_success_msg"] = "Data Berhasil Disimpan! ✅"
                st.rerun()
            except Exception as e:
                st.error(f"Gagal simpan: {str(e)}")

    with c_r:
        if st.button("🔄 RESTORE", use_container_width=True):
            import json
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_log = conn.read(worksheet="Sheet1", ttl="1s")
                user_draft_tag = f"DRAFT_{st.session_state.active_user}"
                my_data = df_log[df_log['User'] == user_draft_tag]
                
                if not my_data.empty:
                    raw_data = str(my_data.iloc[-1]['Visual Utama']).strip()
                    if raw_data.startswith("{"):
                        data = json.loads(raw_data)
                        
                        # Restore Identitas
                        st.session_state.c_name_1_input = data.get("n1", "")
                        st.session_state.c_desc_1_input = data.get("p1", "")
                        st.session_state.c_name_2_input = data.get("n2", "")
                        st.session_state.c_desc_2_input = data.get("p2", "")
                        
                        # Restore Visual
                        for k, v in data.get("scenes", {}).items():
                            st.session_state[f"vis_input_{k.replace('v','')}"] = v
                        
                        # Restore Dialog
                        for d_key, d_text in data.get("dialogs", {}).items():
                            st.session_state[d_key] = d_text
                        
                        # TITIP PESAN SUKSES RESTORE
                        st.session_state["sidebar_success_msg"] = "Data Berhasil Dipulihkan! 🔄"
                        st.session_state.restore_counter += 1
                        st.rerun()
                    else:
                        st.session_state["vis_input_1"] = raw_data
                        st.session_state["sidebar_success_msg"] = "Data Lama Dipulihkan ke Adegan 1! ⚠️"
                        st.rerun()
                else:
                    st.error("Draft tidak ditemukan.")
            except Exception as e:
                st.error(f"Gagal koneksi: {str(e)}")

    # --- MENAMPILKAN NOTIFIKASI SUKSES (DARI SAVE ATAU RESTORE) ---
    if "sidebar_success_msg" in st.session_state:
        st.success(st.session_state["sidebar_success_msg"])
        del st.session_state["sidebar_success_msg"]

    st.sidebar.caption(f"📸 PINTAR MEDIA V.1.2.2 | 👤 {st.session_state.active_user.upper()}")
# ==============================================================================
# 8. PARAMETER KUALITAS (VERSION: APEX SHARPNESS & VIVID)
# ==============================================================================
sharp_natural_stack = (
    "photorealistic raw photo, 8k UHD, extremely high-resolution, shot on 35mm lens, f/1.8, ISO 100, "
    "ultra-sharp focus, crystal clear optical clarity, vibrant organic colors, deep color saturation, "
    "ray-traced global illumination, hyper-detailed skin pores and fabric fibers, "
    "zero digital noise, clean pixels, masterpiece quality."
)

no_text_strict = (
    "STRICTLY NO text, NO typography, NO watermark, NO letters, NO subtitles, "
    "NO captions, NO speech bubbles, NO labels, NO black bars, NO grain, NO blur."
)

img_quality_base = f"{sharp_natural_stack} {no_text_strict}"
vid_quality_base = f"60fps, ultra-clear motion, {sharp_natural_stack} {no_text_strict}"

# ==============================================================================
# 9. FORM INPUT ADEGAN (FIXED: ANTI-HILANG & AUTO-SYNC)
# ==============================================================================

# 1. Inisialisasi Counter (Tetap ada untuk fungsi Restore di Sidebar)
if "restore_counter" not in st.session_state:
    st.session_state.restore_counter = 0

st.subheader("📝 Detail Adegan Storyboard")

# --- IDENTITAS TOKOH (FULL VERSION - KUNCI MATI) ---
with st.expander("👥 Nama Karakter & Detail Fisik! (WAJIB ISI)", expanded=True):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("### Karakter 1")
        # Menggunakan key langsung ke session_state agar tidak hilang saat refresh
        st.text_input("Nama Karakter 1", key="c_name_1_input")
        st.text_area("Detail Fisik Karakter 1", key="c_desc_1_input", height=100)
        
    with col_c2:
        st.markdown("### Karakter 2")
        st.text_input("Nama Karakter 2", key="c_name_2_input")
        st.text_area("Detail Fisik Karakter 2", key="c_desc_2_input", height=100)

    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=6, value=2)
    st.caption("⚠️ *Pastikan Nama Karakter diisi agar muncul di pilihan dialog adegan.*")
    
    # Ambil data dari session_state untuk list dialog
    all_chars_list = [
        {"name": st.session_state.c_name_1_input, "desc": st.session_state.c_desc_1_input}, 
        {"name": st.session_state.c_name_2_input, "desc": st.session_state.c_desc_2_input}
    ]

# --- LIST ADEGAN (ANTI-HILANG MODE) ---
adegan_storage = []

for i_s in range(1, int(num_scenes) + 1):
    l_box_title = f"🟢 ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
    with st.expander(l_box_title, expanded=(i_s == 1)):
        col_v, col_ctrl = st.columns([6.5, 3.5])
        
        with col_v:
            v_key = f"vis_input_{i_s}"
            # KUNCI: Key statis membuat teks nempel permanen di browser
            visual_input = st.text_area(f"Visual Adegan {i_s}", key=v_key, height=180)
        
        with col_ctrl:
            r1, r2 = st.columns(2), st.columns(2)
            
            # --- BARIS 1: CAHAYA & GERAK ---
            with r1[0]:
                st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
                l_key = f"light_input_{i_s}"
                light_val = st.selectbox(f"L{i_s}", options_lighting, key=l_key, label_visibility="collapsed")
            
            with r1[1]:
                st.markdown('<p class="small-label">🎥 Gerak</p>', unsafe_allow_html=True)
                c_key = f"camera_input_{i_s}"
                cam_val = st.selectbox(f"C{i_s}", indonesia_camera, key=c_key, label_visibility="collapsed")
            
            # --- BARIS 2: SHOT & ANGLE ---
            with r2[0]:
                st.markdown('<p class="small-label">📐 Shot</p>', unsafe_allow_html=True)
                s_key = f"shot_input_{i_s}"
                shot_val = st.selectbox(f"S{i_s}", indonesia_shot, key=s_key, label_visibility="collapsed")
            
            with r2[1]:
                st.markdown('<p class="small-label">✨ Angle</p>', unsafe_allow_html=True)
                a_key = f"angle_input_{i_s}"
                angle_val = st.selectbox(f"A{i_s}", indonesia_angle, key=a_key, label_visibility="collapsed")

        # --- BAGIAN DIALOG ---
        diag_cols = st.columns(len(all_chars_list))
        scene_dialogs_list = []
        for i_char, char_data in enumerate(all_chars_list):
            with diag_cols[i_char]:
                char_label = char_data['name'] if char_data['name'] else f"Tokoh {i_char+1}"
                # Dialog juga dikunci pakai key statis
                d_key = f"diag_{i_s}_{i_char}"
                d_in = st.text_input(f"Dialog {char_label}", key=d_key)
                scene_dialogs_list.append({"name": char_label, "text": d_in})
        
        adegan_storage.append({
            "num": i_s, 
            "visual": visual_input, 
            "light": light_val,
            "cam": cam_val,
            "shot": shot_val,
            "angle": angle_val,
            "dialogs": scene_dialogs_list
        })
# ==============================================================================
# 10. GENERATOR PROMPT & MEGA-DRAFT (VERSION: ANTI-CAPTION & APEX SHARPNESS)
# ==============================================================================
import json

# 1. Siapkan Lemari Penyimpanan Hasil Generate
if 'last_generated_results' not in st.session_state:
    st.session_state.last_generated_results = []

st.write("")

# 2. PROSES GENERATE (Saat tombol diklik)
if st.button("🚀 GENERATE ALL PROMPTS", type="primary", use_container_width=True):
    
    active_scenes = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_scenes:
        st.warning("Mohon isi deskripsi visual adegan!")
    else:
        nama_staf = st.session_state.active_user.capitalize()
        
        # --- [BLOCK 1: AUTO-SAVE KOPER LENGKAP SEBELUM GENERATE] ---
        try:
            captured_scenes_auto = {f"v{i}": st.session_state.get(f"vis_input_{i}") for i in range(1, int(num_scenes) + 1) if st.session_state.get(f"vis_input_{i}")}
            auto_packet = {
                "n1": st.session_state.get("c_name_1_input", ""), "p1": st.session_state.get("c_desc_1_input", ""),
                "n2": st.session_state.get("c_name_2_input", ""), "p2": st.session_state.get("c_desc_2_input", ""),
                "scenes": captured_scenes_auto
            }
            record_to_sheets(f"AUTO_{st.session_state.active_user}", json.dumps(auto_packet), len(captured_scenes_auto))
        except: pass
        
        with st.spinner(f"⏳ Sedang meracik prompt Vivid 4K untuk {nama_staf}..."):
            # Reset isi lemari sebelum diisi yang baru
            st.session_state.last_generated_results = []
            
            # LOGGING CLOUD UTAMA
            record_to_sheets(st.session_state.active_user, active_scenes[0]["visual"], len(active_scenes))
            
            # --- LOGIKA MASTER LOCK ---
            char_defs = ", ".join([f"{c['name']} ({c['desc']})" for c in all_chars_list if c['name']])
            master_lock_instruction = (
                f"IMPORTANT: Remember these characters and their physical traits for this entire session. "
                f"Do not deviate from these visuals: {char_defs}. "
                f"Maintain strict facial identity and clothing structure from the initial references. "
            )

            for item in active_scenes:
                # --- LOGIKA SMART CAMERA MOVEMENT ---
                vis_core = item["visual"]
                vis_lower = vis_core.lower()
                
                if camera_map.get(item["cam"]) == "AUTO_MOOD":
                    if any(x in vis_lower for x in ["lari", "jalan", "pergi", "mobil", "motor"]): 
                        e_cam_move = "Dynamic Tracking Shot, sharp focus on motion"
                    elif any(x in vis_lower for x in ["sedih", "menangis", "fokus", "detail", "melihat", "terkejut"]): 
                        e_cam_move = "Slow Cinematic Zoom In, micro-detail focus"
                    elif any(x in vis_lower for x in ["pemandangan", "kota", "luas", "halaman", "jalan raya"]): 
                        e_cam_move = "Slow Pan, edge-to-edge clarity"
                    else: 
                        e_cam_move = "Subtle cinematic camera drift"
                else:
                    e_cam_move = camera_map.get(item["cam"], "Static")

                # --- SMART ANCHOR TERAS ---
                vis_core_final = vis_core + " (Backrest fixed against the house wall, porch structure anchored)" if "teras" in vis_lower else vis_core

                # Konversi Teknis
                e_shot_size = shot_map.get(item["shot"], "Medium Shot")
                e_angle_cmd = angle_map.get(item["angle"], "")
                scene_id = item["num"]
                light_type = item["light"]
                
                # --- LIGHTING MAPPING ---
                if "Bening" in light_type:
                    l_cmd = "Hard sunlight photography, vivid high-contrast, realistic shadows, sharp optical clarity, color-graded foliage."
                elif "Sejuk" in light_type:
                    l_cmd = "8000k cold daylight, vibrant color temperature, crisp shadows, refreshing morning atmosphere."
                elif "Dramatis" in light_type:
                    l_cmd = "Cinematic side-lighting, deep realistic high-contrast shadows, chiaroscuro effect, saturated mood."
                elif "Jelas" in light_type:
                    l_cmd = "Vivid midday sun, realistic deep pigments, morning sun brilliance, sharp texture definition, raw color punch."
                elif "Mendung" in light_type:
                    l_cmd = "Soft diffused overcast light, realistic gray-cobalt sky, rich cinematic tones, moody but sharp textures."
                elif "Suasana Malam" in light_type:
                    l_cmd = "Cinematic night photography, indigo moonlit shadows, dual-tone spotlighting, sharp rim lights, vivid night colors."
                elif "Suasana Alami" in light_type:
                    l_cmd = "Natural sunlight, golden hour highlights, vibrant forest green, realistic humidity, intricate organic textures."
                else: # Suasana Sore
                    l_cmd = "4:00 PM sunset, long sharp high-contrast shadows, golden-indigo gradient, high-fidelity rim lighting."

                # Logika Dialog
                d_all_text = " ".join([f"{d['name']}: {d['text']}" for d in item['dialogs'] if d['text']])
                emotion_ctx = f"Invisible Mood (DO NOT RENDER TEXT): Acting based on '{d_all_text}'. Focus on authentic facial muscle tension. " if d_all_text else ""

                # --- RAKIT PROMPT AKHIR ---
                img_final = (
                    f"{master_lock_instruction} NO TEXT, Clean of any lettering, extremely detailed raw color photography, cinematic still, 9:16 vertical. "
                    f"Masterpiece quality, uncompressed 8k, vivid color punch, edge-to-edge sharpness. {e_angle_cmd} {emotion_ctx} "
                    f"Visual: {vis_core_final}. Atmosphere: {l_cmd}. "
                    f"Final Rendering: {img_quality_base} --ar 9:16 --v 6.0 --style raw --q 2 --stylize 250 --no text typography watermark characters letters captions subtitles"
                )
                
                vid_final = (
                    f"{master_lock_instruction} 9:16 full-screen mobile video. {e_shot_size} {e_cam_move}. "
                    f"{emotion_ctx} Visual: {vis_core_final}. "
                    f"Lighting: {l_cmd}. {vid_quality_base}"
                )

                # --- SIMPAN KE LEMARI ---
                st.session_state.last_generated_results.append({
                    "id": scene_id, "img": img_final, "vid": vid_final, "cam_info": f"{e_shot_size} + {e_cam_move}"
                })

        st.toast("Prompt Berhasil & Cadangan Otomatis Disimpan! 🚀", icon="🎨")
        
        # --- [RAHASIA SAKTI: REFRESH HALAMAN AGAR SIDEBAR LANGSUNG MUNCUL] ---
        st.rerun()

# ==============================================================================
# AREA TAMPILAN HASIL (REVISED: NO DUPLICATE KEYS)
# ==============================================================================
if st.session_state.last_generated_results:
    st.divider()
    st.markdown(f"### 🎬 Hasil Prompt: {st.session_state.active_user.capitalize()}❤️")
    st.caption("⚠️ *Copy prompt ini, jangan lupa tandai di Status Produksi!*")
    
    for res in st.session_state.last_generated_results:
        done_key = f"mark_done_{res['id']}"
        is_done = st.session_state.get(done_key, False)
        
        if is_done:
            with st.expander(f"✅ ADEGAN {res['id']} (DONE)", expanded=False):
                st.info("Prompt ini sudah ditandai selesai di sidebar.")
                st.code(res['img'], language="text")
                st.code(res['vid'], language="text")
        else:
            with st.container():
                st.subheader(f"🚀 ADEGAN {res['id']}")
                c1, c2 = st.columns(2)
                with c1:
                    st.caption("📸 PROMPT GAMBAR")
                    st.code(res['img'], language="text")
                with c2:
                    st.caption("🎥 PROMPT VIDEO")
                    st.code(res['vid'], language="text")
                st.divider()
















