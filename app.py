import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import time

# ==============================================================================
# 0. SISTEM LOGIN TUNGGAL (FULL STABLE: 10-HOUR SESSION + NEW USER)
# ==============================================================================
USER_PASSWORDS = {
    "admin": "QWERTY21ab",
    "icha": "udin99",
    "nissa": "tung22",
    "inggi": "udin33",
    "lisa": "tung66",
    "ezaalma": "aprihgino"
}

# --- 1. FITUR AUTO-LOGIN & SESSION CHECK ---
if 'active_user' not in st.session_state:
    q_user = st.query_params.get("u")
    if q_user in USER_PASSWORDS:
        st.session_state.active_user = q_user
        if 'login_time' not in st.session_state:
            st.session_state.login_time = time.time()

# --- 2. LAYAR LOGIN (Muncul jika belum login) ---
if 'active_user' not in st.session_state:
    st.set_page_config(page_title="Login | PINTAR MEDIA", page_icon="🔐", layout="centered")
    
    placeholder = st.empty()
    with placeholder.container():
        st.write("")
        st.write("")
        _, col_login, _ = st.columns([1, 2, 1])
        
        with col_login:
            try:
                st.image("PINTAR.png", use_container_width=True) 
            except:
                st.markdown("<h1 style='text-align: center;'>📸 PINTAR MEDIA</h1>", unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                user_input = st.text_input("Username", placeholder="Masukkan nama user Anda...")
                pass_input = st.text_input("Password", type="password", placeholder="Masukkan password Anda...")
                submit_button = st.form_submit_button("MASUK KE SISTEM 🚀", use_container_width=True, type="primary")
            
            if submit_button:
                user_clean = user_input.lower().strip()
                if user_clean in USER_PASSWORDS and pass_input == USER_PASSWORDS[user_clean]:
                    st.query_params["u"] = user_clean
                    st.session_state.active_user = user_clean
                    st.session_state.login_time = time.time() # CATAT WAKTU LOGIN
                    
                    placeholder.empty() 
                    with placeholder.container():
                        st.write("")
                        st.markdown("<h3 style='text-align: center; color: #28a745;'>✅ AKSES DITERIMA!</h3>", unsafe_allow_html=True)
                        st.markdown(f"<h1 style='text-align: center;'>Selamat bekerja, {user_clean.capitalize()}!</h1>", unsafe_allow_html=True)
                        _, col_spin, _ = st.columns([2, 1, 2])
                        with col_spin:
                            with st.spinner(""):
                                time.sleep(3.0)
                    st.rerun()
                else:
                    st.error("❌ Username atau Password salah.")
            
            st.caption("<p style='text-align: center;'>🛡️ Secure Access - PINTAR MEDIA</p>", unsafe_allow_html=True)
    st.stop() 

# --- 3. PROTEKSI SESI (AUTO-LOGOUT 10 JAM) ---
if 'active_user' in st.session_state and 'login_time' in st.session_state:
    selisih_detik = time.time() - st.session_state.login_time
    if selisih_detik > (10 * 60 * 60): # 10 Jam
        st.query_params.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.warning("Sesi Anda telah berakhir (Batas 10 jam). Silakan login kembali.")
        time.sleep(2.5)
        st.rerun()

# --- 4. CONFIG DASHBOARD (Area Kerja Utama) ---
st.set_page_config(page_title="PINTAR MEDIA", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
# ==============================================================================
# 1. INISIALISASI MEMORI (ANTI-HILANG SAAT REFRESH)
# ==============================================================================
active_user = st.session_state.active_user # Kunci identitas tunggal

if 'last_generated_results' not in st.session_state:
    st.session_state.last_generated_results = []

# Ambil data Identitas Tokoh
if 'c_name_1_input' not in st.session_state: st.session_state.c_name_1_input = ""
if 'c_desc_1_input' not in st.session_state: st.session_state.c_desc_1_input = ""
if 'c_name_2_input' not in st.session_state: st.session_state.c_name_2_input = ""
if 'c_desc_2_input' not in st.session_state: st.session_state.c_desc_2_input = ""

# Ambil data Adegan (v1 sampai v50)
for i in range(1, 51):
    for key, default in [
        (f"vis_input_{i}", ""),
        (f"light_input_{i}", "Bening dan Tajam"),
        (f"camera_input_{i}", "Ikuti Karakter"),
        (f"shot_input_{i}", "Setengah Badan"),
        (f"angle_input_{i}", "Normal (Depan)")
    ]:
        if key not in st.session_state: st.session_state[key] = default
# ==============================================================================
# 2. SISTEM LOGIN & DATABASE USER (SINKRONISASI MEMORI TOTAL)
# ==============================================================================
# (Variabel USERS boleh tetap ada atau dihapus karena sudah ada di Bagian 0)

# --- 1. INISIALISASI DASAR (KITA SEDERHANAKAN) ---
if 'last_generated_results' not in st.session_state:
    st.session_state.last_generated_results = []

# --- 2. BOOKING MEMORI UNTUK INPUT (TETAP PERTAHANKAN INI) ---
if 'c_name_1_input' not in st.session_state: st.session_state.c_name_1_input = ""
if 'c_desc_1_input' not in st.session_state: st.session_state.c_desc_1_input = ""
if 'c_name_2_input' not in st.session_state: st.session_state.c_name_2_input = ""
if 'c_desc_2_input' not in st.session_state: st.session_state.c_desc_2_input = ""

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

# --- 3. KUNCI AKSES (HANYA SATU BARIS) ---
active_user = st.session_state.active_user
    
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
# 4. CUSTOM CSS (VERSION: BOLD FOCUS & INSTANT RESPONSE)
# ==============================================================================
st.markdown("""
    <style>
    /* A. CUSTOM SCROLLBAR */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0e1117; }
    ::-webkit-scrollbar-thumb { background: #31333f; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #1d976c; }

    /* 1. FIXED HEADER */
    [data-testid="stMainViewContainer"] section.main div.block-container > div:nth-child(1) {
        position: fixed;
        top: 0;
        left: 310px;
        right: 0;
        z-index: 99999;
        background-color: #0e1117;
        padding: 10px 2rem;
        border-bottom: 2px solid #31333f;
    }

    @media (max-width: 768px) {
        [data-testid="stMainViewContainer"] section.main div.block-container > div:nth-child(1) {
            left: 0;
        }
    }

    /* 2. STYLE SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
        border-right: 1px solid rgba(29, 151, 108, 0.1) !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }

    /* 3. TOMBOL GENERATE (KEMBALI KE RESPONS INSTAN - TANPA TRANSISI) */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(to right, #1d976c, #11998e) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: bold !important;
        font-size: 16px !important;
        width: 100%;
        box-shadow: 0 4px 12px rgba(29, 151, 108, 0.2) !important;
        /* Transition dihapus agar kembali instan */
    }

    div.stButton > button[kind="primary"]:hover {
        background: #11998e !important;
        box-shadow: 0 6px 15px rgba(29, 151, 108, 0.3) !important;
    }

    /* 4. MODIFIKASI BOX STAF AKTIF (HIJAU TEGAS & FLAT - TANPA EFEK SAMPING) */
    .staff-header-premium {
        background: rgba(29, 151, 108, 0.2) !important; /* Warna hijau background lebih nyata */
        border: 2px solid #1d976c !important; /* Garis bingkai rata di semua sisi */
        border-radius: 10px !important;
        padding: 15px 20px !important;
        margin-bottom: 25px !important;
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        /* Menghilangkan efek shadow dan border-left tebal agar terlihat flat/rata */
        box-shadow: none !important; 
    }
    
    .staff-header-premium b {
        color: #ffffff !important; /* Nama Staf dibuat putih agar kontras dan jelas */
        font-size: 1.1em !important;
    }

    .staff-header-premium span {
        color: #1d976c !important; /* Icon orangnya yang diberi warna hijau */
    }

    .staff-header-premium i {
        color: #e0e0e0 !important;
        font-style: normal !important; /* Menghilangkan miring jika ingin lebih tegas */
    }
    
    .staff-header-premium b {
        color: #1d976c !important; /* Nama Admin jadi hijau terang */
        font-size: 1.15em !important;
        text-shadow: 0 0 10px rgba(29, 151, 108, 0.3) !important; /* Efek glow halus pada teks */
    }

    .staff-header-premium i {
        color: #e0e0e0 !important; /* Quote jadi lebih putih agar mudah dibaca */
    }
    
    .staff-header-premium b {
        color: #1d976c;
        font-size: 1.1em;
    }

    /* 5. EFEK FOKUS (DIKEMBALIKAN KE STANDAR) */
    .stTextArea textarea:focus, .stTextInput input:focus {
        border: 1px solid #31333f !important; /* Kembali ke warna border asli */
        background-color: #0e1117 !important; /* Tetap gelap */
        box-shadow: none !important;
        outline: none !important;
    }

    /* 6. STYLE LAINNYA */
    h1, h2, h3, .stMarkdown h3 {
        color: #ffffff !important;
        background: none !important;
        -webkit-text-fill-color: initial !important;
    }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        border-radius: 6px !important;
        transform: scale(1.1);
    }
    .stTextArea textarea {
        font-size: 14px !important;
        border-radius: 10px !important;
        background-color: #0e1117 !important;
        border: 1px solid #31333f !important;
    }
    .small-label {
        font-size: 12px; font-weight: bold; color: #a1a1a1; margin-bottom: 2px;
    }
    /* 7. OPTIMASI KOTAK ADEGAN (WARUNG TUNGTUNG NOIR) */
    .stExpander {
        border: 1px solid rgba(29, 151, 108, 0.3) !important;
        border-radius: 12px !important;
        background-color: #161922 !important;
        margin-bottom: 15px !important;
    }

    /* Label dropdown agar lebih tegas dan sinematik */
    .small-label {
        color: #1d976c !important; /* Hijau branding kamu */
        letter-spacing: 1px;
        text-transform: uppercase;
        font-size: 10px !important;
        font-weight: 800 !important;
    }

    /* Membuat garis pemisah adegan lebih halus */
    hr {
        margin: 2em 0 !important;
        border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    }

    /* Menjaga teks area visual tetap rapi */
    .stTextArea textarea {
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 5. HEADER STAF (ELEGANT VERSION)
# ==============================================================================
nama_display = st.session_state.active_user.capitalize()

st.markdown(f"""
    <div class="staff-header-premium">
        <span style="font-size:20px;">👤</span>
        <div>
            <b>Staf Aktif: {nama_display}</b> 
            <span style="color:rgba(255,255,255,0.1); margin: 0 10px;">|</span>
            <span style="color:#aaa; font-style:italic;">Konten yang mantap lahir dari detail adegan yang tepat. 🚀❤️</span>
        </div>
    </div>
""", unsafe_allow_html=True)
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
    "Fokus Karakter", 
    "Detail Wajah", 
    "Sinematik Luas"
]

indonesia_angle = [
    "Normal",
    "Wibawa",
    "Intip",
    "Samping",
    "Berhadapan",
    "Belakang"
]
camera_map = {
    "Ikuti Karakter": "Dynamic tracking shot following the subject's movement", 
    "Diam (Tanpa Gerak)": "Locked-off static camera, no movement", 
    "Zoom Masuk Pelan": "Slow cinematic zoom-in, intensifying the focus", 
    "Zoom Keluar Pelan": "Slow cinematic zoom-out, revealing the environment",
    "Geser Kiri ke Nanan": "Smooth cinematic pan from left to right", 
    "Geser Kanan ke Kiri": "Smooth cinematic pan from right to left", 
    "Dongak ke Atas": "Cinematic tilt-up movement",
    "Tunduk ke Bawah": "Cinematic tilt-down movement", 
    "Ikuti Objek (Tracking)": "Smooth tracking shot with parallax depth", 
    "Memutar (Orbit)": "360-degree orbital circular camera rotation"
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
    "Normal": "eye-level shot, straight on perspective, balanced composition.",
    "Wibawa": "heroic low angle shot, looking up at the subject to create a powerful presence.",
    "Intip": "over-the-shoulder framing, voyeuristic depth, foreground element blocking part of the frame.",
    "Samping": "side profile view, 90-degree angle, showing the subject from the side.",
    "Berhadapan": "profile view of two subjects facing each other directly, intense eye contact.",
    "Belakang": "shot from behind the subject, back view, the character is facing away from the camera looking into the distance, emphasizing what the character sees."
}

options_lighting = [
    "Malam", 
    "Siang", 
    "Remang-remang"
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
# 7. SIDEBAR: KONFIGURASI UTAMA (CLEAN UI + LOGO)
# ==============================================================================
with st.sidebar:
    # --- 1. LOGO SIDEBAR ---
    try:
        st.image("PINTAR.png", use_container_width=True)
    except:
        st.title("📸 PINTAR MEDIA")
    
    st.write("") 
    
    # --- 2. LOGIKA ADMIN ---
    if st.session_state.active_user == "admin":
        if st.checkbox("🚀 Buka Dashboard Utama", value=False):
            st.info("Log aktivitas tercatat di Cloud.")
            
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_monitor = conn.read(worksheet="Sheet1", ttl="0")
                
                if not df_monitor.empty:
                    st.markdown("#### 🏆 Top Staf (MVP)")
                    mvp_count = df_monitor['User'].value_counts().reset_index()
                    mvp_count.columns = ['Staf', 'Total Input']
                    st.dataframe(mvp_count, use_container_width=True, hide_index=True)
                    
                    # --- TABEL AKTIVITAS DENGAN ICON (DIKEMBALIKAN) ---
                    st.markdown("#### 📅 Log Aktivitas Terbaru")
                    
                    # Kita beri nama kolom yang ada icon-nya agar keren
                    df_display = df_monitor.tail(10).copy()
                    df_display.columns = ["🕒 Waktu", "👤 User", "🎬 Total", "📝 Visual Utama"]
                    
                    st.dataframe(
                        df_display, 
                        use_container_width=True, 
                        hide_index=True
                    )
                else:
                    st.warning("Belum ada data aktivitas tercatat.")
            
            except Exception as e:
                st.error(f"Gagal memuat data Cloud: {e}")
                
        st.divider()

    # --- 3. KONFIGURASI UMUM ---
    num_scenes = st.number_input("Tambah Jumlah Adegan", min_value=1, max_value=50, value=6)
    
    # --- 4. STATUS PRODUKSI ---
    if st.session_state.last_generated_results:
        st.markdown("### 🗺️ STATUS PRODUKSI")
        total_p = len(st.session_state.last_generated_results)
        done_p = 0
        
        for res in st.session_state.last_generated_results:
            done_key = f"mark_done_{res['id']}"
            if st.checkbox(f"Adegan {res['id']}", key=done_key):
                done_p += 1
        
        st.progress(done_p / total_p)
        
        if done_p == total_p and total_p > 0:
            st.balloons() 
            st.success("🎉 Semua Adegan Selesai!")
    
    st.divider()

    # --- C. TOMBOL SAVE & RESTORE ---
    c_s, c_r = st.columns(2)
    
    with c_s:
        if st.button("💾 SAVE", use_container_width=True):
            import json
            try:
                captured_scenes = {}
                for i in range(1, int(num_scenes) + 1):
                    v_val = st.session_state.get(f"vis_input_{i}", "")
                    if v_val:
                        captured_scenes[f"v{i}"] = {
                            "vis": v_val,
                            "loc": st.session_state.get(f"loc_input_{i}", "jalan kampung")
                        }
                
                captured_dialogs = {k: v for k, v in st.session_state.items() if k.startswith("diag_") and v}

                draft_packet = {
                    "n1": st.session_state.get("c_name_1_input", ""), 
                    "p1": st.session_state.get("c_desc_1_input", ""),
                    "n2": st.session_state.get("c_name_2_input", ""), 
                    "p2": st.session_state.get("c_desc_2_input", ""),
                    "scenes": captured_scenes,
                    "dialogs": captured_dialogs 
                }
                record_to_sheets(f"DRAFT_{st.session_state.active_user}", json.dumps(draft_packet), len(captured_scenes))
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
                        st.session_state.c_name_1_input = data.get("n1", "")
                        st.session_state.c_desc_1_input = data.get("p1", "")
                        st.session_state.c_name_2_input = data.get("n2", "")
                        st.session_state.c_desc_2_input = data.get("p2", "")
                        
                        for k, v in data.get("scenes", {}).items():
                            idx = k.replace('v','')
                            if isinstance(v, dict):
                                st.session_state[f"vis_input_{idx}"] = v.get("vis", "")
                                st.session_state[f"loc_input_{idx}"] = v.get("loc", "jalan kampung")
                            else:
                                st.session_state[f"vis_input_{idx}"] = v
                        
                        for d_key, d_text in data.get("dialogs", {}).items():
                            st.session_state[d_key] = d_text
                        
                        st.session_state["sidebar_success_msg"] = "Data Berhasil Dipulihkan! 🔄"
                        st.rerun()
                else:
                    st.error("Draft tidak ditemukan.")
            except Exception as e:
                st.error(f"Gagal restore: {str(e)}")

    if "sidebar_success_msg" in st.session_state:
        st.success(st.session_state["sidebar_success_msg"])
        del st.session_state["sidebar_success_msg"]

    st.divider()

    # --- TOMBOL LOGOUT (ICON BARU: POWER OFF) ---
    if st.sidebar.button("LOGOUT⚡", use_container_width=True):
        st.query_params.clear() 
        if 'active_user' in st.session_state:
            del st.session_state.active_user
        st.rerun()
# ==============================================================================
# 8. PARAMETER KUALITAS (VERSION: APEX SHARPNESS & VIVID)
# ==============================================================================
# --- STACK UNTUK FOTO (Tajam, Statis, Tekstur Pori-pori) ---
img_quality_stack = (
    "photorealistic RAW photo, shot on Fujifilm XT-4, " # Merk kamera tetap ada
    "extremely detailed natural skin texture, visible pores and slight blemishes, "
    "subsurface scattering, authentic skin tones, natural film grain, "
    "cinematic lighting, masterpiece quality."
)

# --- STACK UNTUK VIDEO (Motion Blur Natural, Cinematic, Smooth) ---
vid_quality_stack = (
    "ultra-high definition cinematic video, 8k UHD, high dynamic range, "
    "professional color grading, vibrant organic colors, ray-traced reflections, "
    "hyper-detailed textures, zero digital noise, clean pixels, "
    "smooth motion, professional cinematography, masterpiece quality."
)

# --- PENGUAT NEGATIF (Mencegah Glitch & Teks) ---
no_text_strict = (
    "STRICTLY NO text, NO typography, NO watermark, NO letters, NO subtitles, "
    "NO captions, NO speech bubbles, NO labels, NO black bars."
)

negative_motion_strict = (
    "STRICTLY NO morphing, NO extra limbs, NO distorted faces, NO teleporting objects, "
    "NO flickering textures, NO sudden lighting jumps, NO floating hair artifacts."
)

# --- HASIL AKHIR (SANGAT BERBEDA ANTARA GAMBAR & VIDEO) ---
img_quality_base = f"{img_quality_stack} {no_text_strict}"
vid_quality_base = f"60fps, ultra-clear motion, {vid_quality_stack} {no_text_strict} {negative_motion_strict}"
# ==============================================================================
# 9. FORM INPUT ADEGAN (OPTIMIZED FOR WARUNG TUNGTUNG)
# ==============================================================================
if "restore_counter" not in st.session_state:
    st.session_state.restore_counter = 0

st.subheader("📝 Detail Adegan Storyboard")

# --- IDENTITAS TOKOH (VERSI ELEGANT GRID) ---
with st.expander("👥 Nama Karakter & Detail Fisik! (WAJIB ISI)", expanded=True):
    num_total_char = st.number_input("Total Karakter dalam Project", min_value=1, max_value=10, value=2)
    st.write("") 

    all_chars_list = []
    for i in range(1, num_total_char + 1, 2):
        cols = st.columns(2)
        for idx_offset in range(2):
            idx = i + idx_offset
            if idx <= num_total_char:
                with cols[idx_offset]:
                    st.markdown(f"##### 👤 Karakter {idx}")
                    name = st.text_input("Nama", key=f"c_name_{idx}_input", placeholder=f"Nama Tokoh {idx}", label_visibility="collapsed")
                    desc = st.text_area("Detail Fisik", key=f"c_desc_{idx}_input", height=120, placeholder=f"Ciri fisik Karakter {idx}...", label_visibility="collapsed")
                    all_chars_list.append({"name": name, "desc": desc})
        st.write("---") 

# --- LIST ADEGAN ---
adegan_storage = []
for i_s in range(1, int(num_scenes) + 1):
    l_box_title = f"🟢 ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
    with st.expander(l_box_title, expanded=(i_s == 1)):
        col_v, col_ctrl = st.columns([6.5, 3.5])
        
        with col_v:
            visual_input = st.text_area(f"Visual Adegan {i_s}", key=f"vis_input_{i_s}", height=180, placeholder="Ceritakan detail adegannya di sini...")
        
        with col_ctrl:
            r1 = st.columns(2)
            r2 = st.columns(2)
            with r1[0]:
                st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
                light_val = st.selectbox(f"L{i_s}", options_lighting, key=f"light_input_{i_s}", label_visibility="collapsed")
            with r1[1]:
                st.markdown('<p class="small-label">📐 Shot</p>', unsafe_allow_html=True)
                shot_val = st.selectbox(f"S{i_s}", indonesia_shot, key=f"shot_input_{i_s}", label_visibility="collapsed")
            with r2[0]:
                st.markdown('<p class="small-label">✨ Angle</p>', unsafe_allow_html=True)
                angle_val = st.selectbox(f"A{i_s}", indonesia_angle, key=f"angle_input_{i_s}", label_visibility="collapsed")
            with r2[1]:
                st.markdown('<p class="small-label">📍 Lokasi</p>', unsafe_allow_html=True)
                options_lokasi = ["jalan kampung", "jalan kota kecil", "jalan kota besar", "pasar", "halaman rumah", "teras rumah", "pinggir sawah", "sawah", "teras rumah miskin", "dalam rumah kayu", "teras rumah kaya", "dalam rumah kaya"]
                location_val = st.selectbox(f"Loc{i_s}", options=options_lokasi, key=f"loc_input_{i_s}", label_visibility="collapsed")
            cam_val = "Ikuti Karakter"

        # --- BAGIAN DIALOG ---
        diag_cols = st.columns(len(all_chars_list))
        scene_dialogs_list = []
        for i_char, char_data in enumerate(all_chars_list):
            with diag_cols[i_char]:
                char_label = char_data['name'] if char_data['name'] else f"Tokoh {i_char+1}"
                d_in = st.text_input(f"Dialog {char_label}", key=f"diag_{i_s}_{i_char}")
                scene_dialogs_list.append({"name": char_label, "text": d_in})
        
        adegan_storage.append({
            "num": i_s, "visual": visual_input, "light": light_val,
            "location": location_val, "cam": cam_val, "shot": shot_val,
            "angle": angle_val, "dialogs": scene_dialogs_list
        })

# ==============================================================================
# 10. GENERATOR PROMPT & MEGA-DRAFT (NOIR ENGINE)
# ==============================================================================
st.write("")
if st.button("🚀 GENERATE ALL PROMPTS", type="primary", use_container_width=True):
    nama_tokoh_utama = st.session_state.get("c_name_1_input", "").strip()
    active_scenes = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not nama_tokoh_utama:
        st.warning("⚠️ **Nama Karakter 1 belum diisi!**")
    elif not active_scenes:
        st.warning("⚠️ **Mohon isi deskripsi visual adegan!**")
    else:
        with st.spinner(f"⏳ Sedang meracik prompt Warung Tungtung..."):
            st.session_state.last_generated_results = []
            
            # --- [MASTER ASSETS & DNA] ---
            URL_UDIN, URL_TUNG, URL_RUMI = "https://i.ibb.co.com/4w8sJ0rR/UDIN.png", "https://i.ibb.co.com/v7Hpd1b/TUNGG.png", "https://i.ibb.co.com/DHGc9X9y/RUMI.png"
            LOKASI_DNA = {
                "jalan kampung": "narrow dirt road in a quiet Indonesian village, lush banana trees, dusty atmosphere, simple wooden fences, late afternoon sun.",
                "jalan kota kecil": "small town asphalt road, old 90s shophouses (ruko), electricity poles with messy wires, tropical town vibe.",
                "jalan kota besar": "busy metropolitan highway like Jakarta, skyscrapers background, heavy traffic, hazy atmosphere, hot sunny day.",
                "pasar": "crowded traditional wet market, colorful fruit stalls, hanging meat, muddy floor, busy vendors, vibrant chaotic atmosphere.",
                "halaman rumah": "simple front yard, potted frangipani trees, chickens roaming, cracked cement floor, bright daylight.",
                "teras rumah": "comfortable house terrace, tiled floor, wooden chairs, jasmine flowers in pots, peaceful morning vibe.",
                "pinggir sawah": "narrow paved path beside endless green rice fields, coconut trees, wide open blue sky, windy and bright.",
                "sawah": "lush green rice paddy fields, mud irrigation, mountains on the horizon, panoramic rural view.",
                "teras rumah miskin": "humble wooden porch of a shack, weathered grey timber, dusty floor, hanging tattered clothes, rural poverty aesthetic.",
                "dalam rumah kayu": "dim interior of a traditional wooden house, bamboo floor, old oil lamps, dust motes in the air, warm nostalgic vibe.",
                "teras rumah kaya": "modern luxury mansion terrace, marble flooring, minimalist outdoor furniture, manicured garden, elite aesthetic.",
                "dalam rumah kaya": "spacious luxury living room, high ceiling, glass walls, premium sofa, chandelier lighting, polished atmosphere."
            }

            ref_images = ""
            all_names_joined = " ".join([c['name'] for c in all_chars_list]).lower()
            if "udin" in all_names_joined: ref_images += f"{URL_UDIN} "
            if "tung" in all_names_joined: ref_images += f"{URL_TUNG} "
            if "rumi" in all_names_joined: ref_images += f"{URL_RUMI} "

            char_defs = ", ".join([f"{c['name']} ({c['desc']})" for c in all_chars_list if c['name']])
            base_character_lock = f"ACTOR REFERENCE: {ref_images}. Maintain strict facial identity for: {char_defs}."

            for item in active_scenes:
                dna_env = LOKASI_DNA.get(item["location"].lower(), "neutral studio.")
                e_shot = shot_map.get(item["shot"], "Medium Shot")
                e_angle = angle_map.get(item["angle"], "")
                e_cam = camera_map.get(item["cam"], "Static")
                
                # Lighting Logic
                if "Malam" in item["light"]: l_cmd = "cinematic night noir, heavy shadows, flickering tungsten."
                elif "Siang" in item["light"]: l_cmd = "harsh midday sun, high-contrast, gritty heat haze."
                else: l_cmd = "moody low-light, mysterious silhouettes."

                d_text = " ".join([f"{d['name']}: {d['text']}" for d in item['dialogs'] if d['text']])
                emo = f"Acting: '{d_text}'." if d_text else ""

                master_lock = f"{base_character_lock} ENVIRONMENT DNA: {dna_env}."
                
                img_final = f"{master_lock} RAW film still, Arri Alexa, 35mm. Visual: {item['visual']}. {e_angle} {e_shot}. {emo} {l_cmd}. {img_quality_base} --ar 9:16 --style raw"
                vid_final = f"{master_lock} 9:16 Vertical Cinematography. Action: {item['visual']}. {emo} Camera: {e_shot}, {e_cam}. {l_cmd}. {vid_quality_base}"

                st.session_state.last_generated_results.append({
                    "id": item["num"], "img": img_final, "vid": vid_final, "cam_info": f"{e_shot} + {e_cam}"
                })
        st.toast("Prompt Warung Tungtung Siap! 🚀")
        st.rerun()

# ==============================================================================
# 11. DISPLAY MEGA-DRAFT (VERSI FIX - ANTI ERROR DUPLICATE)
# ==============================================================================
if st.session_state.last_generated_results:
    st.divider()
    st.markdown(f"### 🎬 HASIL PROMPT: {st.session_state.active_user.upper()} ❤️")
    st.caption("Gunakan checkbox di Sidebar (Status Produksi) untuk menandai progres.")

    for res in st.session_state.last_generated_results:
        # Ambil status dari checkbox yang ada di sidebar (Bagian 7)
        done_key_sidebar = f"mark_done_{res['id']}"
        is_done = st.session_state.get(done_key_sidebar, False)
        
        # Label Status
        status_tag = "✅ SELESAI" if is_done else "⏳ PROSES"
        
        # Tampilan Expander (Otomatis tertutup jika sudah selesai)
        with st.expander(f"{status_tag} | ADEGAN {res['id']} | 🎥 {res['cam_info']}", expanded=not is_done):
            if is_done:
                st.success(f"Adegan {res['id']} sudah selesai. Cek progress bar di sidebar!")
            
            col_img, col_vid = st.columns(2)
            
            with col_img:
                st.markdown("**📸 IMAGE PROMPT**")
                st.code(res['img'], language="text")
                
            with col_vid:
                st.markdown("**🎥 VIDEO PROMPT**")
                st.code(res['vid'], language="text")
            
            # Info tambahan agar staf tidak bingung
            if not is_done:
                st.info("💡 Klik checkbox di sidebar sebelah kiri jika adegan ini sudah selesai.")

