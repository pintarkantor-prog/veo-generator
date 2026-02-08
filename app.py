import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import time

st.set_page_config(page_title="PINTAR MEDIA", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
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
                    
                    # --- PERBAIKAN DI SINI ---
                    st.session_state.active_user = user_clean
                    st.session_state.login_time = time.time() 
                    # -------------------------
                    
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
# ==============================================================================
# 1 & 2. INISIALISASI MEMORI & SINKRONISASI (CLEAN VERSION)
# ==============================================================================
# Mengambil user aktif dari session login
active_user = st.session_state.active_user 

# 1. Siapkan Lemari Hasil Generate
if 'last_generated_results' not in st.session_state:
    st.session_state.last_generated_results = []

# 2. Inisialisasi Identitas Tokoh (Default Kosong)
if 'c_name_1_input' not in st.session_state: st.session_state.c_name_1_input = ""
if 'c_desc_1_input' not in st.session_state: st.session_state.c_desc_1_input = ""
if 'c_name_2_input' not in st.session_state: st.session_state.c_name_2_input = ""
if 'c_desc_2_input' not in st.session_state: st.session_state.c_desc_2_input = ""

# 3. Inisialisasi Adegan v1 - v50 (SINKRON DENGAN BAGIAN 6)
# Kita pastikan nilai default-nya ada di dalam pilihan menu kamu
for i in range(1, 51):
    for key, default in [
        (f"vis_input_{i}", ""),
        (f"light_input_{i}", "Siang"),       # Sesuai options_lighting
        (f"camera_input_{i}", "Diam (Tanpa Gerak)"), # Sesuai indonesia_camera
        (f"shot_input_{i}", "Setengah Badan"),       # Sesuai indonesia_shot
        (f"angle_input_{i}", "Normal"),      # Sesuai indonesia_angle
        (f"loc_sel_{i}", "jalan kampung")  # Sesuai options_lokasi
    ]:
        if key not in st.session_state: 
            st.session_state[key] = default
    
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
        font-size: 16px !important;
        border-radius: 10px !important;
        background-color: #0e1117 !important;
        border: 1px solid #31333f !important;
    }
    .small-label {
        font-size: 12px; font-weight: bold; color: #a1a1a1; margin-bottom: 2px;
    }
    /* 7. OPTIMASI KOTAK ADEGAN */
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
# 6. MAPPING TRANSLATION (REVISED & SYNCHRONIZED)
# ==============================================================================

# --- DAFTAR PILIHAN (Apa yang muncul di tombol) ---
indonesia_camera = ["Diam (Tanpa Gerak)", "Ikuti Karakter", "Zoom Masuk", "Zoom Keluar", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat", "Dekat Wajah", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Drone Shot"]
indonesia_angle = ["Normal", "Sudut Rendah", "Sudut Tinggi", "Samping", "Berhadapan", "Intip Bahu", "Belakang"]
options_lighting = ["Pagi", "Siang", "Sore", "Malam"]

# --- DNA LOKASI (Gudang Data Lokasi) ---
LOKASI_DNA = {
    "jalan kampung": "narrow dirt road in a quiet Indonesian village, lush banana trees, dusty atmosphere, raw textures, 8k resolution.",
    "jalan kota kecil": "small town asphalt road, old 90s shophouses, messy electricity wires, high-contrast, sharp focus.",
    "jalan kota besar": "busy metropolitan highway, skyscrapers background, heavy traffic, cinematic city contrast.",
    "pasar": "crowded traditional wet market, colorful fruit stalls, vibrant organic colors, sharp muddy textures, realistic.",
    "halaman rumah": "simple front yard, potted frangipani trees, cracked cement textures, sharp daylight, natural shadows.",
    "teras rumah": "comfortable house terrace, tiled floor, wooden chairs, jasmine flowers, sharp morning light, realistic depth.",
    "pinggir sawah": "narrow paved path, endless green rice fields, coconut trees, vibrant natural greens, sharp horizon.",
    "sawah": "lush green rice paddy fields, mud irrigation, realistic organic textures, mountains on the horizon.",
    "teras rumah miskin": "humble wooden porch, weathered grey timber grain, dusty floor, raw poverty aesthetic.",
    "dalam rumah kayu": "dim interior, old wood grain textures, dust motes in light beams, sharp focus on timber, raw photo.",
    "teras rumah kaya": "modern luxury mansion terrace, marble flooring textures, manicured garden, elite aesthetic.",
    "dalam rumah kaya": "spacious luxury living room, high ceiling, glass walls, premium sofa textures, sharp chandelier lighting."
}

# --- PERBAIKAN: DAFTAR OPSI LOKASI UNTUK DROP DOWN ---
# Ini yang tadi hilang! Kita ambil otomatis dari kunci LOKASI_DNA di atas
options_lokasi = ["--- KETIK MANUAL ---"] + list(LOKASI_DNA.keys())

# --- KAMUS TERJEMAHAN UNTUK AI ---
camera_map = {
    "Diam (Tanpa Gerak)": "Static camera, no movement, stable shot",
    "Ikuti Karakter": "Dynamic tracking shot following the subject's movement",
    "Zoom Masuk": "Slow cinematic zoom-in, intensifying focus",
    "Zoom Keluar": "Slow cinematic zoom-out, revealing environment",
    "Memutar (Orbit)": "360-degree orbital circular camera rotation"
}

shot_map = {
    "Sangat Dekat": "Extreme Close-Up shot, macro photography, hyper-detailed micro textures",
    "Dekat Wajah": "Close-Up shot, focus on facial expressions and skin details",
    "Setengah Badan": "Medium Shot, waist-up framing, cinematic depth",
    "Seluruh Badan": "Full body shot, head-to-toe framing, environment visible",
    "Pemandangan Luas": "Wide landscape shot, expansive scenery, subject is small in frame",
    "Drone Shot": "Cinematic Aerial Drone shot, high altitude, bird's-eye view from above"
}

angle_map = {
    "Normal": "eye-level shot, straight on perspective, natural head-on view",
    "Sudut Rendah": "heroic low angle shot, looking up from below, monumental framing",
    "Sudut Tinggi": "high angle shot, looking down at the subject, making it look smaller",
    "Samping": "side profile view, 90-degree side angle, parallel to camera, full profile perspective",
    "Berhadapan": "dual profile view, two subjects facing each other, face-to-face, symmetrical",
    "Intip Bahu": "over-the-shoulder shot, foreground shoulder blur, cinematic dialogue depth",
    "Belakang": "shot from behind, back view, following the subject, looking away from camera"
}

# --- INISIALISASI SESSION STATE AWAL ---
if 'm_light' not in st.session_state: st.session_state.m_light = "Siang"
if 'm_cam' not in st.session_state: st.session_state.m_cam = "Diam (Tanpa Gerak)"
if 'm_shot' not in st.session_state: st.session_state.m_shot = "Setengah Badan"
if 'm_angle' not in st.session_state: st.session_state.m_angle = "Normal"

def global_sync_v920():
    if "light_input_1" in st.session_state:
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

# --- C. TOMBOL SAVE & LOAD (SIMETRIS) ---
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        # Tombol Simpan
        save_trigger = st.button("💾 SAVE", use_container_width=True)
        if save_trigger:
            import json
            try:
                # ... (logika save kamu tetap sama seperti sebelumnya)
                char_data = {str(idx): {"name": st.session_state.get(f"c_name_{idx}_input", ""), "desc": st.session_state.get(f"c_desc_{idx}_input", "")} for idx in range(1, 11)}
                scene_data = {str(i): {"vis": st.session_state.get(f"vis_input_{i}", ""), "light": st.session_state.get(f"light_input_{i}", "Siang"), "shot": st.session_state.get(f"shot_input_{i}", "Setengah Badan"), "angle": st.session_state.get(f"angle_input_{i}", "Normal"), "loc": st.session_state.get(f"loc_sel_{i}", "jalan kampung")} for i in range(1, 51)}
                dialog_data = {k: v for k, v in st.session_state.items() if k.startswith("diag_") and v}
                
                master_packet = {"num_char": st.session_state.get("num_total_char", 2), "chars": char_data, "scenes": scene_data, "dialogs": dialog_data}
                record_to_sheets(f"DRAFT_{st.session_state.active_user}", json.dumps(master_packet), len([s for s in scene_data.values() if s['vis']]))
                st.toast("Project Tersimpan! ✅")
            except Exception as e:
                st.error(f"Gagal simpan: {e}")

    with btn_col2:
        # Kita ganti teksnya jadi 'LOAD' agar sejajar dengan 'SAVE'
        load_trigger = st.button("🔄 LOAD", use_container_width=True)
        if load_trigger:
            import json
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_log = conn.read(worksheet="Sheet1", ttl="1s")
                my_data = df_log[df_log['User'] == f"DRAFT_{st.session_state.active_user}"]
                
                if not my_data.empty:
                    data = json.loads(str(my_data.iloc[-1]['Visual Utama']))
                    # ... (logika restore kamu tetap sama)
                    st.session_state["num_total_char"] = data.get("num_char", 2)
                    for i_str, val in data.get("chars", {}).items():
                        st.session_state[f"c_name_{i_str}_input"] = val.get("name", "")
                        st.session_state[f"c_desc_{i_str}_input"] = val.get("desc", "")
                    for i_str, val in data.get("scenes", {}).items():
                        if isinstance(val, dict):
                            st.session_state[f"vis_input_{i_str}"] = val.get("vis", "")
                            st.session_state[f"light_input_{i_str}"] = val.get("light", "Siang")
                            st.session_state[f"shot_input_{i_str}"] = val.get("shot", "Setengah Badan")
                            st.session_state[f"angle_input_{i_str}"] = val.get("angle", "Normal")
                            st.session_state[f"loc_sel_{i_str}"] = val.get("loc", "jalan kampung")
                    for k, v in data.get("dialogs", {}).items(): st.session_state[k] = v
                    
                    st.toast("Data Dipulihkan! 🔄")
                    st.rerun()
                else:
                    st.error("Draft kosong.")
            except Exception as e:
                st.error(f"Gagal: {e}")
                
    # --- NOTIFIKASI SUKSES ---
    if "sidebar_success_msg" in st.session_state:
        st.success(st.session_state["sidebar_success_msg"])
        del st.session_state["sidebar_success_msg"]

    st.divider()

    # --- TOMBOL LOGOUT (Power Off Icon) ---
    if st.button("KELUAR SISTEM ⚡", use_container_width=True):
        st.query_params.clear() 
        if 'active_user' in st.session_state:
            del st.session_state.active_user
        st.rerun()
# ==============================================================================
# 8. PARAMETER KUALITAS (VERSION: APEX SHARPNESS & VIVID)
# ==============================================================================
# --- STACK UNTUK FOTO (Tajam, Statis, Tekstur Pori-pori) ---
img_quality_stack = (
    "hyper-realistic 8k RAW photo, infinite depth of field, f/11 aperture, "
    "zero bokeh, zero background blur, hyper-sharp focus on every object, "
    "ultra-clear optical clarity, tactile textures on sand and gravel, "
    "CPL filter effect, deep blue sky, high local contrast, "
    "vivid naturalism, realistic shadow recovery, masterpiece quality."
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
# 9. FORM INPUT ADEGAN
# ==============================================================================
if "restore_counter" not in st.session_state:
    st.session_state.restore_counter = 0

st.subheader("📝 Detail Adegan Storyboard")

# --- IDENTITAS TOKOH (VERSI ELEGANT GRID) ---
with st.expander("👥 Nama Karakter Utama & Penampilan Fisik! (WAJIB ISI)", expanded=True):
    num_total_char = st.number_input("Total Karakter Utama dalam Project", min_value=1, max_value=10, value=2)
    st.write("") 

    all_chars_list = []
    for i in range(1, num_total_char + 1, 2):
        cols = st.columns(2)
        for idx_offset in range(2):
            idx = i + idx_offset
            if idx <= num_total_char:
                with cols[idx_offset]:
                    st.markdown(f"##### 👤 Karakter Utama {idx}")
                    name = st.text_input("Nama", key=f"c_name_{idx}_input", placeholder=f"Nama Karakter Utama {idx}", label_visibility="collapsed")
                    desc = st.text_area("Penampilan Fisik", key=f"c_desc_{idx}_input", height=120, placeholder=f"Ciri fisik Karakter Utama {idx}...", label_visibility="collapsed")
                    all_chars_list.append({"name": name, "desc": desc})
        st.write("---") 

# --- LIST ADEGAN ---
adegan_storage = []
for i_s in range(1, int(num_scenes) + 1):
    l_box_title = f"🟢 ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
    with st.expander(l_box_title, expanded=(i_s == 1)):
        # Saya ubah sedikit ke [6, 4] agar kolom kontrol punya ruang lebih untuk teks manual
        col_v, col_ctrl = st.columns([6, 4])
        
        with col_v:
            # UBAH TINGGI DI SINI (265 adalah perkiraan sejajar dengan input manual)
            visual_input = st.text_area(
                f"Cerita Visual {i_s}", 
                key=f"vis_input_{i_s}", 
                height=265, 
                placeholder="Ceritakan detail adegannya di sini..."
            )
        
        with col_ctrl:
            # --- BARIS 1 ---
            r1 = st.columns(2)
            with r1[0]:
                st.markdown('<p class="small-label">💡 Suasana</p>', unsafe_allow_html=True)
                light_val = st.selectbox(f"L{i_s}", options_lighting, key=f"light_input_{i_s}", label_visibility="collapsed")
            with r1[1]:
                st.markdown('<p class="small-label">📐 Ukuran Gambar</p>', unsafe_allow_html=True)
                shot_val = st.selectbox(f"S{i_s}", indonesia_shot, key=f"shot_input_{i_s}", label_visibility="collapsed")
            
            # --- BARIS 2 ---
            r2 = st.columns(2)
            with r2[0]:
                st.markdown('<p class="small-label">✨ Arah Kamera</p>', unsafe_allow_html=True)
                angle_val = st.selectbox(f"A{i_s}", indonesia_angle, key=f"angle_input_{i_s}", label_visibility="collapsed")
            with r2[1]:
                st.markdown('<p class="small-label">🎬 Gerakan Kamera (khusus video)</p>', unsafe_allow_html=True)
                cam_val = st.selectbox(f"C{i_s}", indonesia_camera, index=0, key=f"camera_input_{i_s}", label_visibility="collapsed")
            
            # --- BARIS 3 ---
            r3 = st.columns(1)
            with r3[0]:
                st.markdown('<p class="small-label">📍 Lokasi</p>', unsafe_allow_html=True)
                loc_choice = st.selectbox(f"LocSelect{i_s}", options=options_lokasi, key=f"loc_sel_{i_s}", label_visibility="collapsed")
                
                if loc_choice == "--- KETIK MANUAL ---":
                    location_val = st.text_input(
                        "Tulis lokasi spesifik latar cerita di sini:", 
                        key=f"loc_custom_{i_s}", 
                        placeholder="Contoh: di dalam gerbong kereta api tua..."
                    )
                else:
                    location_val = loc_choice

        # --- BAGIAN DIALOG ---
        diag_cols = st.columns(len(all_chars_list))
        scene_dialogs_list = []
        for i_char, char_data in enumerate(all_chars_list):
            with diag_cols[i_char]:
                char_label = char_data['name'] if char_data['name'] else f"Karakter {i_char+1}"
                d_in = st.text_input(f"Dialog {char_label}", key=f"diag_{i_s}_{i_char}")
                scene_dialogs_list.append({"name": char_label, "text": d_in})
        
        adegan_storage.append({
            "num": i_s, 
            "visual": visual_input, 
            "light": light_val,
            "location": location_val, # Ini akan berisi 'Pasar' ATAU hasil ketikan manual
            "cam": cam_val, 
            "shot": shot_val,
            "angle": angle_val, 
            "dialogs": scene_dialogs_list
        })

# ==============================================================================
# 10. GENERATOR PROMPT & MEGA-DRAFT (OPTIMASI GEMINI IDENTITY) - REVISED SHARP
# ==============================================================================
import json

# 1. Siapkan Lemari Penyimpanan Hasil Generate
if 'last_generated_results' not in st.session_state:
    st.session_state.last_generated_results = []

st.write("")

# 2. PROSES GENERATE (Saat tombol diklik)
if st.button("🚀 GENERATE ALL PROMPTS", type="primary", use_container_width=True):
    nama_tokoh_utama = st.session_state.get("c_name_1_input", "").strip()
    active_scenes = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not nama_tokoh_utama:
        st.warning("⚠️ **Nama Karakter 1 belum diisi!**")
    elif not active_scenes:
        st.warning("⚠️ **Mohon isi deskripsi cerita visual!**")
    else:
        with st.spinner(f"⏳ Sedang meracik prompt tajam..."):
            st.session_state.last_generated_results = []
        
            # --- [BLOCK 1: AUTO-SAVE KOPER LENGKAP] ---
            try:
                captured_scenes_auto = {f"v{i}": st.session_state.get(f"vis_input_{i}") for i in range(1, int(num_scenes) + 1) if st.session_state.get(f"vis_input_{i}")}
                auto_packet = {
                    "n1": st.session_state.get("c_name_1_input", ""), "p1": st.session_state.get("c_desc_1_input", ""),
                    "n2": st.session_state.get("c_name_2_input", ""), "p2": st.session_state.get("c_desc_2_input", ""),
                    "scenes": captured_scenes_auto
                }
                record_to_sheets(f"AUTO_{st.session_state.active_user}", json.dumps(auto_packet), len(captured_scenes_auto))
            except: 
                pass
        
            record_to_sheets(st.session_state.active_user, active_scenes[0]["visual"], len(active_scenes))
            
            # --- MULAI PERULANGAN ADEGAN ---
            for item in active_scenes:
                import re
                mentioned_chars_list = []
                v_text_low = str(item.get('visual', "")).lower().strip()
                
                # 1. SCAN KARAKTER (LOGIKA KATA UTUH)
                for c in all_chars_list:
                    c_name_raw = str(c.get('name', "")).strip()
                    if c_name_raw:
                        if re.search(rf'\b{re.escape(c_name_raw.lower())}\b', v_text_low):
                            mentioned_chars_list.append({"name": c_name_raw.upper(), "desc": c.get('desc', '')})
                
                # 2. LOGIKA HEADER INSTRUKSI (UNTUK GEMINI)
                if len(mentioned_chars_list) == 1:
                    target_name = mentioned_chars_list[0]['name']
                    char_info = f"[[ CHARACTER_{target_name}: {mentioned_chars_list[0]['desc']} ]]"
                    instruction_header = (
                        f"IMAGE REFERENCE RULE: Use the uploaded photo for {target_name}'s face and body.\n"
                        f"STRICT LIMIT: This scene MUST ONLY feature {target_name}. Do NOT add other characters."
                    )
                elif len(mentioned_chars_list) > 1:
                    char_info = " AND ".join([f"[[ CHARACTER_{m['name']}: {m['desc']} ]]" for m in mentioned_chars_list])
                    instruction_header = "IMAGE REFERENCE RULE: Use uploaded photos for each character. Interaction required."
                else:
                    char_info = f"[[ CHARACTER_MAIN: {all_chars_list[0]['desc']} ]]"
                    instruction_header = "IMAGE REFERENCE RULE: Use the main character reference."

                # 3. RAKITAN LOKASI & TEKNIKAL
                raw_loc = item["location"].lower()
                dna_env = LOKASI_DNA.get(raw_loc, f"Location: {raw_loc}.")
                e_shot = shot_map.get(item["shot"], "Medium Shot")
                e_angle = angle_map.get(item["angle"], "")
                
                # --- [PERBAIKAN BESAR: LOGIKA CERDAS CAMERA SINKRON MENU] ---
                # A. Logika Drone
                if "drone" in e_shot.lower():
                    camera_final = f"{e_shot}, high-altitude view, expansive landscape, infinite focus, f/11"
                
                # B. Logika Intip Bahu (Cek dari e_angle sekarang, bukan e_shot)
                elif "over-the-shoulder" in e_angle.lower():
                    target_focus = "the character"
                    for m in mentioned_chars_list:
                        if m['name'].lower() in v_text_low:
                            target_focus = m['name']
                            break
                    camera_final = f"{e_angle} looking at {target_focus}, focus on {target_focus}'s facial expression, infinite depth of field"
                
                # C. Logika Standar (Solo/Duo) - Dibuat SUPER TAJAM
                else:
                    camera_final = f"{e_shot}, {e_angle}, infinite depth of field, f/11 aperture, ultra-sharp focus everywhere"
                
                # --- LIGHTING LOGIC (WARNA TAJAM & KONTRAS MANTAP) ---
                if "Pagi" in item["light"]: 
                    l_cmd = "6 AM crisp morning light, high-contrast, deep shadows, cold atmosphere."
                elif "Siang" in item["light"]: 
                    l_cmd = "Bright diffused midday light, vivid naturalism, cinematic contrast, deep black levels, polarizing filter for rich colors."
                elif "Sore" in item["light"]: 
                    l_cmd = "4 PM golden hour, warm saturated colors, long dramatic shadows, high-contrast glow."
                elif "Malam" in item["light"]: 
                    l_cmd = "Cinematic night, moonlit indigo atmosphere, sharp rim lighting, deep shadows."
                else: 
                    l_cmd = "Natural lighting, high contrast, balanced exposure."

                # --- 1. PROSES DIALOG & EMOSI ---
                try:
                    d_text = " ".join([f"{d['name']}: {d['text']}" for d in item.get('dialogs', []) if d.get('text')])
                except:
                    d_text = ""
                emo = f"Acting/Emotion: '{d_text}'." if d_text else ""

                # --- 4. OUTPUT AKHIR (VERSI ANTI-BLUR & LANGIT TAJAM) ---
                img_final = (
                    f"{instruction_header}\n\n"
                    f"FOCUS RULE: INFINITE DEPTH OF FIELD, EVERYTHING MUST BE ULTRA-SHARP FROM FOREGROUND TO BACKGROUND.\n"
                    f"CHARACTER DATA: {char_info}\n"
                    f"VISUAL ACTION: {item['visual']}. {emo}\n"
                    f"ENVIRONMENT: {dna_env}. hyper-detailed grit, sand, leaf veins, and realistic wood grain textures. NO BLURRY BACKGROUND.\n"
                    f"CAMERA: {camera_final}\n"
                    f"TECHNICAL: {img_quality_stack}, {l_cmd}, extreme edge-enhancement, every pixel is sharp, deep color saturation."
                )

                vid_final = (
                    f"{instruction_header}\n"
                    f"Action: {item['visual']}. {char_info}. Environment: {dna_env}. {l_cmd}"
                )

                st.session_state.last_generated_results.append({
                    "id": item["num"], 
                    "img": img_final, 
                    "vid": vid_final, 
                    "cam_info": f"{camera_final}"
                })

        st.toast("Prompt Berhasil Diracik! 🚀")
        st.rerun()
# ==============================================================================
# AREA TAMPILAN HASIL (REVISED: NO DUPLICATE KEYS)
# ==============================================================================
if st.session_state.last_generated_results:

    st.markdown(f"### 🎬 Hasil Prompt: {st.session_state.active_user.capitalize()}❤️")
    
    for res in st.session_state.last_generated_results:
        done_key = f"mark_done_{res['id']}"
        is_done = st.session_state.get(done_key, False)
        
        status_tag = "✅ SELESAI" if is_done else "⏳ PROSES"
        
        with st.expander(f"{status_tag} | ADEGAN {res['id']}", expanded=not is_done):
            if is_done:
                st.success(f"Adegan {res['id']} Selesai!")
            
            # --- GRID PROMPT ---
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**📸 PROMPT GAMBAR**")
                st.code(res['img'], language="text")
            with c2:
                st.markdown("**🎥 PROMPT VIDEO**")
                st.code(res['vid'], language="text")






