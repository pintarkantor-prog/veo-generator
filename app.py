import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MANUAL SETUP - MEGA STRUCTURE)
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==============================================================================
# 2. SISTEM LOGIN & DATABASE USER (EKSPLISIT)
# ==============================================================================
USERS = {
    "admin": "admin123",
    "staf_01": "karya01",
    "staf_02": "karya02"
}

def record_activity_log(user, first_visual, total_scenes):
    """Mencatat aktivitas ke CSV secara manual"""
    log_file = "log_produksi.csv"
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "Waktu": [current_time],
        "User": [user],
        "Total Adegan": [total_scenes],
        "Visual Utama": [first_visual[:100]]
    }
    df_log = pd.DataFrame(log_entry)
    
    if not os.path.isfile(log_file):
        df_log.to_csv(log_file, index=False)
    else:
        df_log.to_csv(log_file, mode='a', header=False, index=False)

# Session State Login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'active_user' not in st.session_state:
    st.session_state.active_user = ""

# Layar Login (Eksplisit)
if not st.session_state.logged_in:
    st.title("🔐 PINTAR MEDIA - LOGIN SISTEM")
    
    with st.form("form_login_staf"):
        input_user = st.text_input("Username")
        input_pass = st.text_input("Password", type="password")
        btn_login = st.form_submit_button("Masuk Ke Ruang Produksi")
        
        if btn_login:
            if input_user in USERS and USERS[input_user] == input_pass:
                st.session_state.logged_in = True
                st.session_state.active_user = input_user
                st.rerun()
            else:
                st.error("Username atau Password Salah!")
    st.stop()


# ==============================================================================
# 3. CUSTOM CSS (FULL EXPLICIT STYLE - NO REDUCTION)
# ==============================================================================
st.markdown("""
    <style>
    /* Latar Belakang Sidebar Gelap Profesional */
    [data-testid="stSidebar"] {
        background-color: #1a1c24 !important;
    }
    
    /* Warna Teks Sidebar Putih Terang */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }

    /* Tombol Copy Hijau Terang Ikonik */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important; 
        border-radius: 6px !important;
        border: 2px solid #ffffff !important;
        transform: scale(1.1); 
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    
    /* Font Area Input Visual Deskripsi */
    .stTextArea textarea {
        font-size: 14px !important;
        line-height: 1.5 !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* Label kecil untuk Dropbox */
    .small-label {
        font-size: 12px;
        font-weight: bold;
        color: #a1a1a1;
        margin-bottom: 2px;
    }
    </style>
    """, unsafe_allow_html=True)


# ==============================================================================
# 4. HEADER APLIKASI
# ==============================================================================
col_title, col_logout = st.columns([8, 2])
with col_title:
    st.title("📸 PINTAR MEDIA")
    st.info(f"Staf Aktif: {st.session_state.active_user} | v9.18 | PRODUCTION MONITORING ❤️")
with col_logout:
    if st.button("Logout 🚪"):
        st.session_state.logged_in = False
        st.rerun()


# ==============================================================================
# 5. MAPPING TRANSLATION (INDONESIA -> INGGRIS)
# ==============================================================================
indonesia_camera = [
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

camera_map = {
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


# ==============================================================================
# 6. LOGIKA MASTER SYNC & OPTIONS
# ==============================================================================
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

if 'm_light' not in st.session_state: st.session_state.m_light = options_lighting[0]
if 'm_cam' not in st.session_state: st.session_state.m_cam = indonesia_camera[0]
if 'm_shot' not in st.session_state: st.session_state.m_shot = indonesia_shot[2]

def global_sync_v918():
    l_1 = st.session_state.light_input_1
    c_1 = st.session_state.camera_input_1
    s_1 = st.session_state.shot_input_1
    
    st.session_state.m_light = l_1
    st.session_state.m_cam = c_1
    st.session_state.m_shot = s_1
    
    for key in st.session_state.keys():
        if key.startswith("light_input_"): st.session_state[key] = l_1
        if key.startswith("camera_input_"): st.session_state[key] = c_1
        if key.startswith("shot_input_"): st.session_state[key] = s_1


# ==============================================================================
# 7. SIDEBAR: KONFIGURASI TOKOH (MANUAL EXPLICIT - NO LOOPING)
# ==============================================================================
with st.sidebar:
    # FITUR ADMIN: MONITORING LOG
    if st.session_state.active_user == "admin":
        st.header("📊 Admin Control")
        if st.checkbox("Lihat Riwayat Kerja Karyawan"):
            if os.path.isfile("log_produksi.csv"):
                st.dataframe(pd.read_csv("log_produksi.csv"))
            else:
                st.write("Belum ada riwayat tercatat.")
        st.divider()

    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    # Karakter 1 (Eksplisit Manual)
    st.markdown("### Karakter 1")
    c_name_1_v = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c_desc_1_v = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", height=100)
    
    st.divider()

    # Karakter 2 (Eksplisit Manual)
    st.markdown("### Karakter 2")
    c_name_2_v = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c_desc_2_v = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", height=100)

    # TAMBAH KARAKTER MANUAL (EKSPLISIT)
    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=10, value=2)
    
    characters_data_list = []
    characters_data_list.append({"name": c_name_1_v, "desc": c_desc_1_v})
    characters_data_list.append({"name": c_name_2_v, "desc": c_desc_2_v})

    if num_extra > 2:
        for idx_ex in range(2, int(num_extra)):
            st.divider()
            st.markdown(f"### Karakter {idx_ex + 1}")
            ex_n = st.text_input(f"Nama Karakter {idx_ex + 1}", key=f"ex_name_{idx_ex}")
            ex_p = st.text_area(f"Fisik Karakter {idx_ex + 1}", key=f"ex_phys_{idx_ex}", height=100)
            characters_data_list.append({"name": ex_n, "desc": ex_p})


# ==============================================================================
# 8. PARAMETER KUALITAS (ULTIMATE FIDELITY - NO REDUCTION)
# ==============================================================================
no_text_no_rain_lock = (
    "STRICTLY NO rain, NO puddles, NO raindrops, NO wet ground, NO water droplets, "
    "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters."
)

img_quality_base = (
    "photorealistic surrealism style, 16-bit color bit depth, hyper-saturated organic pigments, "
    "absolute fidelity to unique character reference, edge-to-edge optical sharpness, "
    "f/11 deep focus aperture, micro-contrast enhancement, intricate micro-textures on every surface, "
    "circular polarizer (CPL) filter effect, zero atmospheric haze, "
    "rich high-contrast shadows, unprocessed raw photography, 8k resolution, captured on high-end 35mm lens, "
    "STRICTLY NO over-exposure, NO motion blur, NO lens flare, " + no_text_no_rain_lock
)

vid_quality_base = (
    "ultra-high-fidelity vertical video, 9:16, 60fps, photorealistic surrealism, "
    "strict character consistency, deep saturated pigments, "
    "hyper-vivid foliage textures, crystal clear background focus, "
    "extreme visual clarity, lossless texture quality, fluid organic motion, "
    "high contrast ratio, NO animation look, NO CGI look, " + no_text_no_rain_lock
)


# ==============================================================================
# 9. FORM INPUT ADEGAN (MANUAL GRID - NO COMPRESSION)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    
    label_h = f"🟢 MASTER CONTROL - ADEGAN {idx_s}" if idx_s == 1 else f"🎬 ADEGAN {idx_s}"
    with st.expander(label_h, expanded=(idx_s == 1)):
        
        # Grid System Eksplisit
        col_vis, col_lit, col_cam, col_sht = st.columns([4, 1.5, 1.5, 1.5])
        
        with col_vis:
            v_in = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=150)
        
        with col_lit:
            st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
            if idx_s == 1:
                l_v = st.selectbox("L1", options_lighting, key="light_input_1", on_change=global_sync_v918, label_visibility="collapsed")
            else:
                if f"light_input_{idx_s}" not in st.session_state: st.session_state[f"light_input_{idx_s}"] = st.session_state.m_light
                l_v = st.selectbox(f"L{idx_s}", options_lighting, key=f"light_input_{idx_s}", label_visibility="collapsed")
        
        with col_cam:
            st.markdown('<p class="small-label">🎥 Gerak Video</p>', unsafe_allow_html=True)
            if idx_s == 1:
                c_v = st.selectbox("C1", indonesia_camera, key="camera_input_1", on_change=global_sync_v918, label_visibility="collapsed")
            else:
                if f"camera_input_{idx_s}" not in st.session_state: st.session_state[f"camera_input_{idx_s}"] = st.session_state.m_cam
                c_v = st.selectbox(f"C{idx_s}", indonesia_camera, key=f"camera_input_{idx_s}", label_visibility="collapsed")

        with col_sht:
            st.markdown('<p class="small-label">📐 Ukuran Shot</p>', unsafe_allow_html=True)
            if idx_s == 1:
                s_v = st.selectbox("S1", indonesia_shot, key="shot_input_1", on_change=global_sync_v918, label_visibility="collapsed")
            else:
                if f"shot_input_{idx_s}" not in st.session_state: st.session_state[f"shot_input_{idx_s}"] = st.session_state.m_shot
                s_v = st.selectbox(f"S{idx_s}", indonesia_shot, key=f"shot_input_{idx_s}", label_visibility="collapsed")

        # Dialog Manual Karakter 1 & 2 (Eksplisit)
        d_c1, d_c2 = st.columns(2)
        with d_c1:
            l1 = c_name_1_v if c_name_1_v else "Tokoh 1"
            dt_1 = st.text_input(f"Dialog {l1}", key=f"d1_idx_{idx_s}")
        with d_c2:
            l2 = c_name_2_v if c_name_2_v else "Tokoh 2"
            dt_2 = st.text_input(f"Dialog {l2}", key=f"d2_idx_{idx_s}")
            
        adegan_storage.append({
            "num": idx_s, "visual": v_in, "light": l_v, "cam": c_v, "shot": s_v, 
            "t1_n": c_name_1_v, "t1_d": dt_1, "t2_n": c_name_2_v, "t2_d": dt_2
        })


st.divider()


# ==============================================================================
# 10. GENERATOR PROMPT (MEGA STRUCTURE - FULL RESTORED MANUAL)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    
    active_ad = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_ad:
        st.warning("Mohon isi deskripsi visual adegan!")
    else:
        # PENCATATAN LOG KE KARYAWAN
        record_activity_log(st.session_state.active_user, active_ad[0]["visual"], len(active_ad))
        
        for item in active_ad:
            
            # Konversi Manual
            e_cam = camera_map.get(item["cam"], "Static")
            e_shot = shot_map.get(item["shot"], "Medium Shot")
            s_id = item["num"]
            v_t = item["visual"]
            l_s = item["light"]
            
            # --- FULL LIGHTING MAPPING (EKSPLISIT NO REDUCTION) ---
            if "Bening" in l_s:
                f_l = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
                f_a = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
            
            elif "Sejuk" in l_s:
                f_l = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
                f_a = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
            
            elif "Dramatis" in l_s:
                f_l = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
                f_a = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
            
            elif "Jelas" in l_s:
                f_l = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
                f_a = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
            
            elif "Mendung" in l_s:
                f_l = "Intense moody overcast lighting with 16-bit color depth fidelity, absolute visual bite, vivid pigment recovery on every surface, extreme local micro-contrast, brilliant specular highlights on object edges, deep rich high-definition shadows."
                f_a = "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on foliage, wood grain, grass blades, house walls, concrete roads, and every environment object in frame. Bone-dry surfaces, zero moisture, hyper-sharp edge definition across the entire frame."
            
            elif "Suasana Malam" in l_s:
                f_l = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim light highlights, 9000k cold moonlit glow, visible background detail."
                f_a = "Clear night atmosphere, deep indigo-black sky, hyper-defined textures on every object."
            
            elif "Suasana Alami" in l_s:
                f_l = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments."
                f_a = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures."
            
            else: # Suasana Sore
                f_l = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                f_a = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background, zero atmospheric haze."

            # --- LOGIKA DIALOG MANUAL ---
            p1 = f"{item['t1_n']}: \"{item['t1_d']}\"" if item['t1_d'] else ""
            p2 = f"{item['t2_n']}: \"{item['t2_d']}\"" if item['t2_d'] else ""
            d_full = f"{p1} {p2}".strip()
            
            emotion = f"Emotion Context (DO NOT RENDER TEXT): Reacting to context: '{d_full}'. Focus on high-fidelity facial expressions. " if d_full else ""

            # --- DNA SYNC ---
            c_refs = ""
            if item['t1_n'] and item['t1_n'].lower() in v_t.lower():
                c_refs += f"STRICT CHARACTER APPEARANCE: {item['t1_n']} ({c_desc_1_v}) "
            if item['t2_n'] and item['t2_n'].lower() in v_t.lower():
                c_refs += f"STRICT CHARACTER APPEARANCE: {item['t2_n']} ({c_desc_2_v}) "

            # --- DISPLAY ---
            st.subheader(f"HASIL PRODUKSI ADEGAN {s_id}")
            
            img_res = f"buatkan gambar adegan {s_id}. {emotion}{c_refs} Visual: {v_t}. Atmosphere: {f_a}. Lighting: {f_l}. {img_quality_base}"
            vid_res = f"Video Adegan {s_id}. {e_shot} perspective. {e_cam} movement. {emotion}{c_refs} Visual: {v_t}. Lighting: {f_l}. {vid_quality_base}"
            
            col_1, col_2 = st.columns(2)
            with col_1:
                st.caption("📸 PROMPT GAMBAR")
                st.code(img_res, language="text")
            with col_2:
                st.caption(f"🎥 PROMPT VIDEO ({e_shot} + {e_cam})")
                st.code(vid_res, language="text")
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.18 - Ultimate Production Edition")
