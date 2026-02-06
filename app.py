import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz  #

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MANUAL SETUP - MEGA STRUCTURE)
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. SISTEM LOGIN & DATABASE USER (ANTI-REFRESH MODE)
# ==============================================================================
USERS = {
    "admin": "QWERTY21ab",
    "icha": "udin99",
    "nissa": "tung22"
}

# Inisialisasi session state (pastikan semua variabel ada)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'active_user' not in st.session_state:
    st.session_state.active_user = ""
if 'last_generated_results' not in st.session_state:
    st.session_state.last_generated_results = []

# --- FITUR ANTI-REFRESH: Cek Jejak Login di URL ---
query_params = st.query_params
if not st.session_state.logged_in:
    # Cek apakah ada parameter 'u' (user) dan 'p' (pass) di link browser
    if "u" in query_params and "p" in query_params:
        u_param = query_params["u"]
        p_param = query_params["p"]
        # Validasi otomatis
        if u_param in USERS and USERS[u_param] == p_param:
            st.session_state.logged_in = True
            st.session_state.active_user = u_param

# Tampilkan Layar Login hanya jika tidak ada jejak login
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
                
                # --- SIMPAN KE URL ---
                # Ini yang bikin browser "ingat" Icha/Nissa meskipun di-refresh
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
# 7. SIDEBAR: KONFIGURASI UTAMA (CLEAN UI - NO DRAFT TITLE)
# ==============================================================================
with st.sidebar:
    
    # --- A. LOGIKA ADMIN (Hanya tampil untuk admin) ---
    if st.session_state.active_user == "admin":
        if st.checkbox("🚀 Buka Dashboard Utama", value=True):
            try:
                conn_a = st.connection("gsheets", type=GSheetsConnection)
                df_a = conn_a.read(worksheet="Sheet1", ttl="1m")
                if not df_a.empty:
                    st.markdown("### 📊 Ringkasan Produksi")
                    total_prod = len(df_a)
                    user_counts = df_a["User"].value_counts()
                    c1, c2 = st.columns(2)
                    with c1: st.metric("Total Klik", total_prod)
                    with c2: 
                        top_staf = user_counts.idxmax() if not user_counts.empty else "-"
                        st.metric("MVP Staf", top_staf)
                    with st.expander("👁️ Lihat Detail Log", expanded=False):
                        search = st.text_input("🔍 Filter Nama/Cerita", placeholder="Cari...")
                        df_show = df_a.iloc[::-1].copy()
                        if search:
                            df_show = df_show[df_show['Visual Utama'].str.contains(search, case=False, na=False) | 
                                             df_show['User'].str.contains(search, case=False, na=False)]
                        st.dataframe(df_show, use_container_width=True, hide_index=True)
            except: pass
        st.divider()

    # --- B. KONFIGURASI UMUM (SEKARANG DITARIK KELUAR AGAR SEMUA USER BISA LIHAT) ---
    num_scenes = st.number_input("Tambah Jumlah Adegan", min_value=1, max_value=50, value=6)
    
    # STATUS PRODUKSI
    if st.session_state.last_generated_results:
        st.markdown("### 🗺️ STATUS PRODUKSI")
        st.caption("Tandai disini jika sudah selesai!:")
        
        for res in st.session_state.last_generated_results:
            done_key = f"mark_done_{res['id']}"
            if done_key not in st.session_state:
                st.session_state[done_key] = False
            st.checkbox(f"Adegan {res['id']}", key=done_key)
        
        # Progress Bar Minimalis
        total_p = len(st.session_state.last_generated_results)
        done_p = sum(1 for r in st.session_state.last_generated_results if st.session_state.get(f"mark_done_{r['id']}", False))
        st.write("") 
        st.progress(done_p / total_p)
        
        if done_p == total_p:
            st.balloons()
            st.success("🎉 Selesai!")

    # --- C. BUTTONS ONLY (TANPA JUDUL DRAFT MANAGEMENT) ---
    c_s, c_r = st.columns(2)
    with c_s:
        if st.button("💾 SAVE", use_container_width=True):
            import json
            try:
                captured_scenes = {}
                for i in range(1, int(num_scenes) + 1):
                    v_key = f"vis_input_{i}"
                    if v_key in st.session_state and st.session_state[v_key].strip() != "":
                        captured_scenes[f"v{i}"] = st.session_state[v_key]
                draft_packet = {
                    "n1": st.session_state.get("c_name_1_input", ""), "p1": st.session_state.get("c_desc_1_input", ""),
                    "n2": st.session_state.get("c_name_2_input", ""), "p2": st.session_state.get("c_desc_2_input", ""),
                    "scenes": captured_scenes
                }
                record_to_sheets(f"DRAFT_{st.session_state.active_user}", json.dumps(draft_packet), len(captured_scenes))
                st.toast("Draft Tersimpan! ✅")
            except: st.error("Gagal simpan")

    with c_r:
        if st.button("🔄 RESTORE", use_container_width=True):
            import json
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_log = conn.read(worksheet="Sheet1", ttl="5s")
                my_data = df_log[df_log['User'].str.contains(st.session_state.active_user, na=False)]
                if not my_data.empty:
                    raw_data = my_data.iloc[-1]['Visual Utama']
                    data = json.loads(raw_data)
                    st.session_state.c_name_1_input = data.get("n1", "")
                    st.session_state.c_desc_1_input = data.get("p1", "")
                    st.session_state.c_name_2_input = data.get("n2", "")
                    st.session_state.c_desc_2_input = data.get("p2", "")
                    for k, v in data.get("scenes", {}).items():
                        st.session_state[f"vis_input_{k.replace('v','')}"] = v
                    st.session_state.restore_counter += 1
                    st.rerun()
            except: st.error("Gagal tarik data")
    st.sidebar.caption(f"📸 PINTAR MEDIA V.1.2.2 | 👤 {st.session_state.active_user.upper()}")

# --- MULAI DARI SINI SEMUA DITARIK KE KIRI (RATA KIRI) AGAR ICHA & NISSA BISA LIHAT ---

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
# 9. FORM INPUT ADEGAN (FULL VERSION - CLEAN UI & AUTO-SYNC)
# ==============================================================================

# 1. Inisialisasi Counter & Memori (WAJIB ADA untuk sinkronisasi)
if "restore_counter" not in st.session_state:
    st.session_state.restore_counter = 0

# --- BAGIAN TOMBOL RESTORE SUDAH PINDAH KE SIDEBAR (BAGIAN 7) ---

st.subheader("📝 Detail Adegan Storyboard")

# --- IDENTITAS TOKOH (FULL VERSION - UTUH) ---
with st.expander("👥 Nama Karakter & Detail Fisik! (WAJIB ISI)", expanded=True):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("### Karakter 1")
        c_n1_v = st.text_input("Nama Karakter 1", value=st.session_state.get("c_name_1_input", ""), key=f"w_n1_{st.session_state.restore_counter}")
        c_p1_v = st.text_area("Detail Fisik Karakter 1", value=st.session_state.get("c_desc_1_input", ""), key=f"w_p1_{st.session_state.restore_counter}", height=100)
        st.session_state.c_name_1_input, st.session_state.c_desc_1_input = c_n1_v, c_p1_v
    with col_c2:
        st.markdown("### Karakter 2")
        c_n2_v = st.text_input("Nama Karakter 2", value=st.session_state.get("c_name_2_input", ""), key=f"w_n2_{st.session_state.restore_counter}")
        c_p2_v = st.text_area("Detail Fisik Karakter 2", value=st.session_state.get("c_desc_2_input", ""), key=f"w_p2_{st.session_state.restore_counter}", height=100)
        st.session_state.c_name_2_input, st.session_state.c_desc_2_input = c_n2_v, c_p2_v

    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=6, value=2)
    st.caption("⚠️ *Pastikan Nama Karakter diisi agar muncul di pilihan dialog adegan.*")
    all_chars_list = [{"name": c_n1_v, "desc": c_p1_v}, {"name": c_n2_v, "desc": c_p2_v}]
    if num_extra > 2:
        extra_cols = st.columns(num_extra - 2)
        for ex_idx in range(2, int(num_extra)):
            with extra_cols[ex_idx - 2]:
                kn, kp = f"ex_name_{ex_idx}", f"ex_phys_{ex_idx}"
                ex_name = st.text_input(f"Nama Karakter {ex_idx+1}", value=st.session_state.get(kn, ""), key=f"w_en_{ex_idx}_{st.session_state.restore_counter}")
                ex_phys = st.text_area(f"Detail Fisik Karakter {ex_idx+1}", value=st.session_state.get(kp, ""), key=f"w_ep_{ex_idx}_{st.session_state.restore_counter}", height=100)
                st.session_state[kn], st.session_state[kp] = ex_name, ex_phys
                all_chars_list.append({"name": ex_name, "desc": ex_phys})

# --- LIST ADEGAN (FULL VERSION + SYNC LOGIC) ---
adegan_storage = []
count = st.session_state.restore_counter

for i_s in range(1, int(num_scenes) + 1):
    l_box_title = f"🟢 ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
    with st.expander(l_box_title, expanded=(i_s == 1)):
        col_v, col_ctrl = st.columns([6.5, 3.5])
        with col_v:
            v_key = f"vis_input_{i_s}"
            visual_input = st.text_area(f"Visual Adegan {i_s}", value=st.session_state.get(v_key, ""), key=f"w_vis_{i_s}_{count}", height=180)
            st.session_state[v_key] = visual_input
        
        with col_ctrl:
            r1, r2 = st.columns(2), st.columns(2)
            
            # --- BARIS 1: CAHAYA & GERAK ---
            with r1[0]:
                st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
                st.selectbox(f"L{i_s}", options_lighting, 
                             key=f"l_i_{i_s}_{count}", 
                             label_visibility="collapsed")
            
            with r1[1]:
                st.markdown('<p class="small-label">🎥 Gerak</p>', unsafe_allow_html=True)
                st.selectbox(f"C{i_s}", indonesia_camera, 
                             key=f"c_i_{i_s}_{count}", 
                             label_visibility="collapsed")
            
            # --- BARIS 2: SHOT & ANGLE ---
            with r2[0]:
                st.markdown('<p class="small-label">📐 Shot</p>', unsafe_allow_html=True)
                st.selectbox(f"S{i_s}", indonesia_shot, 
                             key=f"s_i_{i_s}_{count}", 
                             label_visibility="collapsed")
            
            with r2[1]:
                st.markdown('<p class="small-label">✨ Angle</p>', unsafe_allow_html=True)
                st.selectbox(f"A{i_s}", indonesia_angle, 
                             key=f"a_i_{i_s}_{count}", 
                             label_visibility="collapsed")

        # --- BAGIAN DIALOG ---
        diag_cols = st.columns(len(all_chars_list))
        scene_dialogs_list = []
        for i_char, char_data in enumerate(all_chars_list):
            with diag_cols[i_char]:
                char_label = char_data['name'] if char_data['name'] else f"Tokoh {i_char+1}"
                d_key = f"diag_{i_s}_{i_char}"
                d_in = st.text_input(f"Dialog {char_label}", value=st.session_state.get(d_key, ""), key=f"wd_{i_s}_{i_char}_{count}")
                st.session_state[d_key] = d_in
                scene_dialogs_list.append({"name": char_label, "text": d_in})
        
        adegan_storage.append({
            "num": i_s, "visual": visual_input, 
            "light": st.session_state.get(f"l_i_{i_s}_{count}", st.session_state.m_light),
            "cam": st.session_state.get(f"c_i_{i_s}_{count}", st.session_state.m_cam),
            "shot": st.session_state.get(f"s_i_{i_s}_{count}", st.session_state.m_shot),
            "angle": st.session_state.get(f"a_i_{i_s}_{count}", st.session_state.m_angle),
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
        
        with st.spinner(f"⏳ Sedang meracik prompt Vivid 4K untuk {nama_staf}..."):
            # Reset isi lemari sebelum diisi yang baru
            st.session_state.last_generated_results = []
            
            # LOGGING CLOUD
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
                    "id": scene_id,
                    "img": img_final,
                    "vid": vid_final,
                    "cam_info": f"{e_shot_size} + {e_cam_move}"
                })

        st.toast("Prompt Vivid & Crystal Clear Berhasil! 🚀", icon="🎨")

# ==============================================================================
# AREA TAMPILAN HASIL (REVISED: NO DUPLICATE KEYS)
# ==============================================================================
if st.session_state.last_generated_results:
    st.divider()
    st.markdown(f"### 🎬 Hasil Prompt: {st.session_state.active_user.capitalize()}❤️")
    st.caption("⚠️ *Copy prompt ini, jangan lupa tandai di Status Produksi!*")
    
    for res in st.session_state.last_generated_results:
        done_key = f"mark_done_{res['id']}"
        
        # LOGIKA: Cukup cek statusnya saja
        is_done = st.session_state.get(done_key, False)
        
        if is_done:
            # Jika SUDAH DICENTANG: Menciut (Collapse)
            with st.expander(f"✅ ADEGAN {res['id']} (DONE)", expanded=False):
                st.info("Prompt ini sudah ditandai selesai di sidebar.")
                st.code(res['img'], language="text")
                st.code(res['vid'], language="text")
        else:
            # Jika BELUM DICENTANG: Terbuka lebar (Focus)
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
