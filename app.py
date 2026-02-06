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
        existing_data = conn.read(worksheet="Sheet1", ttl="1m")
        
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
    "Geser Kiri ke Kanan", 
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
    "Geser Kiri ke Kanan": "Pan Left to Right", 
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
# 7. SIDEBAR: KONFIGURASI UTAMA (V.1.2.2 - PROGRESS TRACKER & STANDARD BUTTONS)
# ==============================================================================
with st.sidebar:
    st.title("📸 PINTAR MEDIA")
    if st.session_state.active_user == "admin":
        st.header("🔍 CEK KERJAAN")
        
        if st.checkbox("🚀 Buka Dashboard Utama", value=True):
            try:
                conn_a = st.connection("gsheets", type=GSheetsConnection)
                df_a = conn_a.read(worksheet="Sheet1", ttl="1m")
                
                if not df_a.empty:
                    # --- 1. METRIK PERFORMANCE ---
                    st.markdown("### 📊 Ringkasan Produksi")
                    total_prod = len(df_a)
                    user_counts = df_a["User"].value_counts()
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Total Klik", total_prod)
                    with c2:
                        top_staf = user_counts.idxmax() if not user_counts.empty else "-"
                        st.metric("MVP Staf", top_staf)

                    st.divider()

                    # --- 2. VISUAL TRICK: EXPANDER UNTUK DETAIL LOG ---
                    with st.expander("👁️ Lihat Detail Log", expanded=False):
                        search = st.text_input("🔍 Filter Nama/Cerita", placeholder="Cari...")
                        
                        df_show = df_a.iloc[::-1].copy()
                        df_show["Status"] = "✅ Done"
                        
                        if search:
                            df_show = df_show[
                                df_show['Visual Utama'].str.contains(search, case=False, na=False) | 
                                df_show['User'].str.contains(search, case=False, na=False)
                            ]

                        st.dataframe(
                            df_show, 
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Status": st.column_config.TextColumn("Stat"),
                                "Waktu": st.column_config.TextColumn("⏰ Jam"),
                                "User": st.column_config.TextColumn("👤 Staf"),
                                "Total Adegan": st.column_config.NumberColumn("🎬"),
                                "Visual Utama": st.column_config.TextColumn("📝 Ringkasan")
                            }
                        )

                    st.write("") 
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        csv = df_a.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Export", data=csv, file_name="log_produksi.csv", mime="text/csv", use_container_width=True)
                    
                    with col_btn2:
                        if st.button("🗑️ Reset", use_container_width=True):
                            empty_df = pd.DataFrame(columns=["Waktu", "User", "Total Adegan", "Visual Utama"])
                            conn_a.update(worksheet="Sheet1", data=empty_df)
                            st.success("Log Reset!")
                            st.rerun()
                else:
                    st.info("Belum ada aktivitas hari ini.")
                    
            except Exception as e:
                st.error(f"Koneksi GSheets Delay: {e}")
                
        st.divider()

    # --- KONFIGURASI UNTUK SEMUA USER ---
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    # --- PROGRESS TRACKER ---
    st.divider()
    filled_scenes = sum(1 for i in range(1, int(num_scenes) + 1) 
                        if f"vis_input_{i}" in st.session_state and st.session_state[f"vis_input_{i}"].strip() != "")
    
    progress_val = filled_scenes / int(num_scenes)
    st.markdown(f"📊 **Progress: {filled_scenes} / {num_scenes} Adegan**")
    st.progress(progress_val)
    st.write("") 
    
    # --- TOMBOL DRAFT (KEMBALI KE STANDAR TANPA TYPE) ---
    
    # 1. TOMBOL SIMPAN
    if st.button("💾 SAVE DATA", use_container_width=True):
        import json
        try:
            captured_scenes = {}
            for i in range(1, int(num_scenes) + 1):
                v_key = f"vis_input_{i}"
                if v_key in st.session_state and st.session_state[v_key].strip() != "":
                    captured_scenes[f"v{i}"] = st.session_state[v_key]

            draft_packet = {
                "n1": st.session_state.get("c_name_1_input", ""),
                "p1": st.session_state.get("c_desc_1_input", ""),
                "n2": st.session_state.get("c_name_2_input", ""),
                "p2": st.session_state.get("c_desc_2_input", ""),
                "scenes": captured_scenes
            }
            packet_string = json.dumps(draft_packet)
            record_to_sheets(f"DRAFT_{st.session_state.active_user}", packet_string, len(captured_scenes))
            st.toast(f"Berhasil! {len(captured_scenes)} Adegan tersimpan. ✅")
        except Exception as e:
            st.error(f"Gagal simpan draft: {e}")

    # 2. TOMBOL TARIK
    if st.button("🔄 RESTORE DATA", use_container_width=True):
        import json
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_log = conn.read(worksheet="Sheet1", ttl="5s")
            my_data = df_log[df_log['User'].str.contains(st.session_state.active_user, na=False)]
            
            if not my_data.empty:
                raw_data = my_data.iloc[-1]['Visual Utama']
                if raw_data.strip().startswith("{"):
                    data = json.loads(raw_data)
                    st.session_state.c_name_1_input = data.get("n1", "")
                    st.session_state.c_desc_1_input = data.get("p1", "")
                    st.session_state.c_name_2_input = data.get("n2", "")
                    st.session_state.c_desc_2_input = data.get("p2", "")
                    scenes_data = data.get("scenes", {})
                    for key_v, val_v in scenes_data.items():
                        num_idx = key_v.replace('v', '')
                        st.session_state[f"vis_input_{num_idx}"] = val_v
                    st.success("Draft Pulih! ✅")
                else:
                    st.session_state["vis_input_1"] = raw_data
                st.session_state.restore_counter += 1 
                st.rerun()
            else:
                st.warning("Belum ada draft.")
        except Exception as e:
            st.error(f"Gagal tarik draft: {e}")

    st.markdown("---")
    st.sidebar.caption(f"🎨 PINTAR MEDIA | V.1.2.2 | 👤 {st.session_state.active_user.upper()}")
    
# ==============================================================================
# 8. PARAMETER KUALITAS (V.1.0.3 - MASTER LIGHTING & FULL-BLEED)
# ==============================================================================
sharp_natural_stack = (
    "Full-bleed cinematography, edge-to-edge pixel rendering, Full-frame vertical coverage, zero black borders, "
    "expansive background rendering to edges, Circular Polarizer (CPL) filter effect, eliminates light glare, "
    "ultra-high-fidelity resolution, micro-contrast enhancement, optical clarity, deep saturated pigments, "
    "vivid organic color punch, intricate organic textures, skin texture override with 8k details, "
    "f/11 aperture for deep focus sharpness, zero digital noise, zero atmospheric haze, crystal clear background focus."
)

no_text_strict = (
    "STRICTLY NO rain, NO wet ground, NO raindrops, NO speech bubbles, NO text, NO typography, "
    "NO watermark, NO letters, NO black bars on top and bottom, NO subtitles."
)

img_quality_base = f"{sharp_natural_stack} {no_text_strict}"
vid_quality_base = f"vertical 9:16 full-screen mobile video, 60fps, fluid organic motion, {sharp_natural_stack} {no_text_strict}"

# ==============================================================================
# 8.5 FUNGSI SINKRONISASI OTOMATIS (TARUH DI SINI)
# ==============================================================================
def global_sync_v920():
    """Menyamakan setelan Master Control (Adegan 1) ke semua adegan secara otomatis"""
    try:
        count = st.session_state.get("restore_counter", 0)
        
        # Ambil nilai dari widget Adegan 1 (Master)
        # Nama key di sini HARUS sama dengan key di selectbox (l_i, c_i, s_i, a_i)
        lt1 = st.session_state.get(f"l_i_1_{count}")
        cm1 = st.session_state.get(f"c_i_1_{count}")
        sh1 = st.session_state.get(f"s_i_1_{count}")
        an1 = st.session_state.get(f"a_i_1_{count}")

        # Update Master State Global
        st.session_state.m_light = lt1
        st.session_state.m_cam = cm1
        st.session_state.m_shot = sh1
        st.session_state.m_angle = an1

        # Sebarkan ke adegan 2 sampai seterusnya
        for i in range(2, int(num_scenes) + 1):
            st.session_state[f"l_i_{i}_{count}"] = lt1
            st.session_state[f"c_i_{i}_{count}"] = cm1
            st.session_state[f"s_i_{i}_{count}"] = sh1
            st.session_state[f"a_i_{i}_{count}"] = an1
    except:
        pass

# ==============================================================================
# 9. FORM INPUT ADEGAN (FULL VERSION - CLEAN UI & AUTO-SYNC)
# ==============================================================================

# 1. Inisialisasi Counter & Memori (WAJIB ADA untuk sinkronisasi)
if "restore_counter" not in st.session_state:
    st.session_state.restore_counter = 0

# --- BAGIAN TOMBOL RESTORE SUDAH PINDAH KE SIDEBAR (BAGIAN 7) ---

st.subheader("📝 Detail Adegan Storyboard")

# --- IDENTITAS TOKOH (FULL VERSION - UTUH) ---
with st.expander("👥 Identitas & Fisik Karakter (WAJIB ISI)", expanded=True):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("### Karakter 1")
        c_n1_v = st.text_input("Nama Karakter 1", value=st.session_state.get("c_name_1_input", ""), key=f"w_n1_{st.session_state.restore_counter}")
        c_p1_v = st.text_area("Fisik Karakter 1", value=st.session_state.get("c_desc_1_input", ""), key=f"w_p1_{st.session_state.restore_counter}", height=100)
        st.session_state.c_name_1_input, st.session_state.c_desc_1_input = c_n1_v, c_p1_v
    with col_c2:
        st.markdown("### Karakter 2")
        c_n2_v = st.text_input("Nama Karakter 2", value=st.session_state.get("c_name_2_input", ""), key=f"w_n2_{st.session_state.restore_counter}")
        c_p2_v = st.text_area("Fisik Karakter 2", value=st.session_state.get("c_desc_2_input", ""), key=f"w_p2_{st.session_state.restore_counter}", height=100)
        st.session_state.c_name_2_input, st.session_state.c_desc_2_input = c_n2_v, c_p2_v

    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=10, value=2)
    st.caption("⚠️ *Pastikan Nama Karakter diisi agar muncul di pilihan dialog adegan.*")
    all_chars_list = [{"name": c_n1_v, "desc": c_p1_v}, {"name": c_n2_v, "desc": c_p2_v}]
    if num_extra > 2:
        extra_cols = st.columns(num_extra - 2)
        for ex_idx in range(2, int(num_extra)):
            with extra_cols[ex_idx - 2]:
                kn, kp = f"ex_name_{ex_idx}", f"ex_phys_{ex_idx}"
                ex_name = st.text_input(f"Nama Karakter {ex_idx+1}", value=st.session_state.get(kn, ""), key=f"w_en_{ex_idx}_{st.session_state.restore_counter}")
                ex_phys = st.text_area(f"Fisik Karakter {ex_idx+1}", value=st.session_state.get(kp, ""), key=f"w_ep_{ex_idx}_{st.session_state.restore_counter}", height=100)
                st.session_state[kn], st.session_state[kp] = ex_name, ex_phys
                all_chars_list.append({"name": ex_name, "desc": ex_phys})

# --- LIST ADEGAN (FULL VERSION + SYNC LOGIC) ---
adegan_storage = []
count = st.session_state.restore_counter

for i_s in range(1, int(num_scenes) + 1):
    l_box_title = f"🟢 MASTER CONTROL - ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
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
                # HAPUS index=idx_l, biarkan session_state yang pegang kendali
                st.selectbox(f"L{i_s}", options_lighting, 
                             key=f"l_i_{i_s}_{count}", 
                             on_change=(global_sync_v920 if i_s == 1 else None),
                             label_visibility="collapsed")
            
            with r1[1]:
                st.markdown('<p class="small-label">🎥 Gerak</p>', unsafe_allow_html=True)
                st.selectbox(f"C{i_s}", indonesia_camera, 
                             key=f"c_i_{i_s}_{count}", 
                             on_change=(global_sync_v920 if i_s == 1 else None),
                             label_visibility="collapsed")
            
            # --- BARIS 2: SHOT & ANGLE ---
            with r2[0]:
                st.markdown('<p class="small-label">📐 Shot</p>', unsafe_allow_html=True)
                st.selectbox(f"S{i_s}", indonesia_shot, 
                             key=f"s_i_{i_s}_{count}", 
                             on_change=(global_sync_v920 if i_s == 1 else None),
                             label_visibility="collapsed")
            
            with r2[1]:
                st.markdown('<p class="small-label">✨ Angle</p>', unsafe_allow_html=True)
                st.selectbox(f"A{i_s}", indonesia_angle, 
                             key=f"a_i_{i_s}_{count}", 
                             on_change=(global_sync_v920 if i_s == 1 else None),
                             label_visibility="collapsed")

        # --- BAGIAN DIALOG (INDENTASI DIPERBAIKI) ---
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
# 10. GENERATOR PROMPT & MEGA-DRAFT (FULL VERSION - UTUH TANPA POTONGAN)
# ==============================================================================
import json # <--- WAJIB ADA di paling atas blok ini

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
        
        with st.spinner(f"⏳ Sedang meracik prompt AI untuk {nama_staf}..."):
            # Reset isi lemari sebelum diisi yang baru
            st.session_state.last_generated_results = []
            
            # LOGGING CLOUD (FINAL VERSION - Simpan visual utama saja untuk log harian)
            record_to_sheets(st.session_state.active_user, active_scenes[0]["visual"], len(active_scenes))
            
            # --- LOGIKA MASTER LOCK ---
            char_defs = ", ".join([f"Karakter {idx+1} ({c['name']}: {c['desc']})" for idx, c in enumerate(all_chars_list) if c['name']])
            master_lock_instruction = f"IMPORTANT: Remember these characters and their physical traits for this entire session. Do not deviate from these visuals: {char_defs}. "

            for item in active_scenes:
                # --- LOGIKA SMART CAMERA MOVEMENT ---
                vis_core = item["visual"]
                vis_lower = vis_core.lower()
                
                if camera_map.get(item["cam"]) == "AUTO_MOOD":
                    if any(x in vis_lower for x in ["lari", "jalan", "pergi", "mobil", "motor"]): 
                        e_cam_move = "Dynamic Tracking Shot, follow subject motion"
                    elif any(x in vis_lower for x in ["sedih", "menangis", "fokus", "detail", "melihat", "terkejut"]): 
                        e_cam_move = "Slow Cinematic Zoom In"
                    elif any(x in vis_lower for x in ["pemandangan", "kota", "luas", "halaman", "jalan raya"]): 
                        e_cam_move = "Slow Pan Left to Right"
                    elif any(x in vis_lower for x in ["marah", "teriak", "berantem", "aksi"]): 
                        e_cam_move = "Handheld Shaky Cam intensity"
                    else: 
                        e_cam_move = "Subtle cinematic camera drift"
                else:
                    e_cam_move = camera_map.get(item["cam"], "Static")

                # --- SMART ANCHOR TERAS ---
                if "teras" in vis_lower:
                    vis_core_final = vis_core + " (Backrest fixed against the house wall, positioned under the porch roof roof, chair anchored to house structure)."
                else:
                    vis_core_final = vis_core

                # Konversi Teknis
                e_shot_size = shot_map.get(item["shot"], "Medium Shot")
                e_angle_cmd = angle_map.get(item["angle"], "")
                scene_id = item["num"]
                light_type = item["light"]
                
                # --- FULL LIGHTING MAPPING ---
                if "Bening" in light_type:
                    l_cmd = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
                    a_cmd = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
                elif "Sejuk" in light_type:
                    l_cmd = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
                    a_cmd = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
                elif "Dramatis" in light_type:
                    l_cmd = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
                    a_cmd = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
                elif "Jelas" in light_type:
                    l_cmd = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
                    a_cmd = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
                elif "Mendung" in light_type:
                    l_cmd = "Intense moody overcast lighting with 16-bit color depth fidelity, absolute visual bite, vivid pigment recovery."
                    a_cmd = "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, gray-cobalt sky."
                elif "Suasana Malam" in light_type:
                    l_cmd = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim light highlights, 9000k cold moonlit glow."
                    a_cmd = "Clear night atmosphere, deep indigo-black sky, hyper-defined textures."
                elif "Suasana Alami" in light_type:
                    l_cmd = "Low-exposure natural sunlight, high local contrast amplification, extreme chlorophyll color depth."
                    a_cmd = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves, intricate micro-textures."
                else: # Suasana Sore
                    l_cmd = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                    a_cmd = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background."

                # Logika Dialog & Emosi
                d_all_text = " ".join([f"{d['name']}: \"{d['text']}\"" for d in item['dialogs'] if d['text']])
                emotion_ctx = f"Emotion Context (DO NOT RENDER TEXT): Reacting to context: '{d_all_text}'. Focus on high-fidelity facial expressions. " if d_all_text else ""

                # DNA Anchor
                dna_str = " ".join([f"STRICT CHARACTER FIDELITY: Maintain facial identity structure of {c['name']} ({c['desc']}) but re-render surface with 8k skin texture." for c in all_chars_list if c['name'] and c['name'].lower() in vis_lower])

                # Logika Penyuntikan Master Lock
                current_lock = master_lock_instruction if scene_id == 1 else ""

                # --- RAKIT PROMPT AKHIR ---
                img_final = (
                    f"{current_lock}create a STATIC high-quality photograph, 9:16 vertical aspect ratio, edge-to-edge full frame coverage. "
                    f"{e_angle_cmd} {emotion_ctx}{dna_str} Visual: {vis_core_final}. "
                    f"Atmosphere: {a_cmd}. Lighting: {l_cmd}. {img_quality_base} --ar 9:16"
                )
                
                vid_final = (
                    f"{current_lock}9:16 full-screen mobile video. {e_shot_size} perspective. {e_angle_cmd} {e_cam_move}. "
                    f"{emotion_ctx}{dna_str} Visual: {vis_core_final}. "
                    f"Lighting: {l_cmd}. {vid_quality_base}"
                )

                # --- SIMPAN KE LEMARI (SESSION STATE) ---
                st.session_state.last_generated_results.append({
                    "id": scene_id,
                    "img": img_final,
                    "vid": vid_final,
                    "cam_info": f"{e_shot_size} + {e_cam_move}"
                })

        # Notifikasi Berhasil
        pesan_toast = "Prompt Berhasil Dibuat! 🚀" if st.session_state.active_user == "admin" else f"Kerjaan {nama_staf} Berhasil Dibuat! 🚀"
        st.toast(pesan_toast, icon="🎨")

# 3. AREA TAMPILAN
if st.session_state.last_generated_results:
    st.divider()
    nama_staf = st.session_state.active_user.capitalize()
    st.success(f"✅ Mantap! Prompt untuk {nama_staf} sudah siap digunakan.")

    for res in st.session_state.last_generated_results:
        st.subheader(f"🎬 Hasil Adegan {res['id']}")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("📸 PROMPT GAMBAR (STATIC)")
            st.code(res['img'], language="text")
        with c2:
            st.caption(f"🎥 PROMPT VIDEO ({res['cam_info']})")
            st.code(res['vid'], language="text")
        st.divider()

















