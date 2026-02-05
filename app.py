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
# 2. SISTEM LOGIN & DATABASE USER (MANUAL EXPLICIT)
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
# 3. LOGIKA LOGGING GOOGLE SHEETS (SERVICE ACCOUNT MODE)
# ==============================================================================
def record_to_sheets(user, first_visual, total_scenes):
    """Mencatat aktivitas karyawan menggunakan Service Account Secrets"""
    try:
        # Membangun koneksi ke Google Sheets melalui Secrets
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Membaca data lama (Worksheet harus bernama Sheet1)
        existing_data = conn.read(worksheet="Sheet1", ttl=0)
        
        # Membuat baris data baru secara eksplisit
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_row = pd.DataFrame([{
            "Waktu": current_time,
            "User": user,
            "Total Adegan": total_scenes,
            "Visual Utama": first_visual[:150]
        }])
        
        # Menggabungkan data lama dan baru
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        
        # Menulis kembali ke Cloud (Update)
        conn.update(worksheet="Sheet1", data=updated_df)
        
    except Exception as e:
        st.error(f"Gagal mencatat riwayat ke Google Sheets: {e}")


# ==============================================================================
# 4. CUSTOM CSS (FULL EXPLICIT STYLE - NO REDUCTION)
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
# 5. HEADER APLIKASI
# ==============================================================================
c_header1, c_header2 = st.columns([8, 2])
with c_header1:
    st.title("📸 PINTAR MEDIA")
    st.info(f"Staf Aktif: {st.session_state.active_user} | SEMANGAT KERJANYA GUYS! BUAT KONTEN YANG BENER MANTEP YOW 🚀❤️")
with c_header2:
    if st.button("Logout 🚪"):
        st.session_state.logged_in = False
        st.rerun()


# ==============================================================================
# 6. MAPPING TRANSLATION (INDONESIA -> INGGRIS)
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

def global_sync_v920():
    lt1 = st.session_state.light_input_1
    cm1 = st.session_state.camera_input_1
    st1 = st.session_state.shot_input_1
    
    st.session_state.m_light = lt1
    st.session_state.m_cam = cm1
    st.session_state.m_shot = st1
    
    for key in st.session_state.keys():
        if key.startswith("light_input_"): st.session_state[key] = lt1
        if key.startswith("camera_input_"): st.session_state[key] = cm1
        if key.startswith("shot_input_"): st.session_state[key] = st1


# ==============================================================================
# 7. SIDEBAR: KONFIGURASI TOKOH (EXPLICIT MANUAL - NO REDUCTION)
# ==============================================================================
with st.sidebar:
# FITUR ADMIN MONITORING
    if st.session_state.active_user == "admin":
        st.header("📊 Admin Monitor")
        if st.checkbox("Buka Log Google Sheets"):
            try:
                conn_a = st.connection("gsheets", type=GSheetsConnection)
                # UBAH BAGIAN INI:
                df_a = conn_a.read(worksheet="Sheet1", ttl=0) # Pastikan ttl=0
                st.dataframe(df_a)
            except:
                st.warning("Gagal memuat. Periksa setting Secrets atau Nama Worksheet Anda.")  
        st.divider()

    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    # --- Karakter 1 ---
    st.markdown("### Karakter 1")
    c_n1_v = st.text_input("Nama Karakter 1", key="c_name_1_input", placeholder="Contoh: UDIN")
    c_p1_v = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", height=100)
    
    st.divider()
    
    # --- Karakter 2 ---
    st.markdown("### Karakter 2")
    c_n2_v = st.text_input("Nama Karakter 2", key="c_name_2_input", placeholder="Contoh: TUNG")
    c_p2_v = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", height=100)

    # --- Tambah Karakter (v9.15 Mode) ---
    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=10, value=2)
    
    all_chars_list = []
    all_chars_list.append({"name": c_n1_v, "desc": c_p1_v})
    all_chars_list.append({"name": c_n2_v, "desc": c_p2_v})

    if num_extra > 2:
        for ex_idx in range(2, int(num_extra)):
            st.divider()
            st.markdown(f"### Karakter {ex_idx + 1}")
            ex_name = st.text_input(f"Nama Karakter {ex_idx + 1}", key=f"ex_name_{ex_idx}")
            ex_phys = st.text_area(f"Fisik Karakter {ex_idx + 1}", key=f"ex_phys_{ex_idx}", height=100)
            all_chars_list.append({"name": ex_name, "desc": ex_phys})


# ==============================================================================
# 8. PARAMETER KUALITAS (ULTIMATE FIDELITY - NO REDUCTION)
# ==============================================================================
no_text_strict = (
    "STRICTLY NO rain, NO puddles, NO raindrops, NO wet ground, NO water droplets, "
    "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters."
)

img_quality_base = (
    "photorealistic surrealism style, 16-bit color bit depth, hyper-saturated organic pigments, "
    "absolute fidelity to unique character reference, edge-to-edge optical sharpness, "
    "f/11 deep focus aperture, micro-contrast enhancement, intricate micro-textures, "
    "circular polarizer (CPL) filter effect, zero atmospheric haze, 8k resolution, " + no_text_strict
)

vid_quality_base = (
    "ultra-high-fidelity vertical video, 9:16, 60fps, photorealistic surrealism, "
    "strict character consistency, deep saturated pigments, "
    "hyper-vivid foliage textures, crystal clear background focus, "
    "lossless texture quality, fluid organic motion, " + no_text_strict
)


# ==============================================================================
# 9. FORM INPUT ADEGAN (MANUAL GRID - NO COMPRESSION)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for i_s in range(1, int(num_scenes) + 1):
    
    l_box_title = f"🟢 MASTER CONTROL - ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
    
    with st.expander(l_box_title, expanded=(i_s == 1)):
        
        # Grid System Manual
        col_v, col_l, col_c, col_s = st.columns([4, 1.5, 1.5, 1.5])
        
        with col_v:
            visual_input = st.text_area(f"Visual Adegan {i_s}", key=f"vis_input_{i_s}", height=150)
        
        with col_l:
            st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
            if i_s == 1:
                l_val = st.selectbox("L1", options_lighting, key="light_input_1", on_change=global_sync_v920, label_visibility="collapsed")
            else:
                if f"light_input_{i_s}" not in st.session_state: st.session_state[f"light_input_{i_s}"] = st.session_state.m_light
                l_val = st.selectbox(f"L{i_s}", options_lighting, key=f"light_input_{i_s}", label_visibility="collapsed")
        
        with col_c:
            st.markdown('<p class="small-label">🎥 Gerak Video</p>', unsafe_allow_html=True)
            if i_s == 1:
                c_val = st.selectbox("C1", indonesia_camera, key="camera_input_1", on_change=global_sync_v920, label_visibility="collapsed")
            else:
                if f"camera_input_{i_s}" not in st.session_state: st.session_state[f"camera_input_{i_s}"] = st.session_state.m_cam
                c_val = st.selectbox(f"C{i_s}", indonesia_camera, key=f"camera_input_{i_s}", label_visibility="collapsed")

        with col_s:
            st.markdown('<p class="small-label">📐 Ukuran Shot</p>', unsafe_allow_html=True)
            if i_s == 1:
                s_val = st.selectbox("S1", indonesia_shot, key="shot_input_1", on_change=global_sync_v920, label_visibility="collapsed")
            else:
                if f"shot_input_{i_s}" not in st.session_state: st.session_state[f"shot_input_{i_s}"] = st.session_state.m_shot
                s_val = st.selectbox(f"S{i_s}", indonesia_shot, key=f"shot_input_{i_s}", label_visibility="collapsed")

        # Dialog Dinamis Manual
        diag_cols = st.columns(len(all_chars_list))
        scene_dialogs_list = []
        for i_char, char_data in enumerate(all_chars_list):
            with diag_cols[i_char]:
                char_label = char_data['name'] if char_data['name'] else f"Tokoh {i_char+1}"
                d_in = st.text_input(f"Dialog {char_label}", key=f"diag_{i_s}_{i_char}")
                scene_dialogs_list.append({"name": char_label, "text": d_in})
        
        adegan_storage.append({
            "num": i_s, "visual": visual_input, "light": l_val, "cam": c_val, "shot": s_val, "dialogs": scene_dialogs_list
        })


st.divider()


# ==============================================================================
# 10. GENERATOR PROMPT (MEGA STRUCTURE - FULL MANUAL EXPLICIT)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    
    active_scenes = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_scenes:
        st.warning("Mohon isi deskripsi visual adegan!")
    else:
        # SIMPAN KE GOOGLE SHEETS CLOUD (MENGGUNAKAN SERVICE ACCOUNT)
        record_to_sheets(st.session_state.active_user, active_scenes[0]["visual"], len(active_scenes))
        
        for item in active_scenes:
            
            # Konversi Teknis
            e_cam_move = camera_map.get(item["cam"], "Static")
            e_shot_size = shot_map.get(item["shot"], "Medium Shot")
            
            scene_id = item["num"]
            vis_core = item["visual"]
            light_type = item["light"]
            
            # --- FULL LIGHTING MAPPING (MANUAL EXPLICIT - NO REDUCTION) ---
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
                l_cmd = (
                    "Intense moody overcast lighting with 16-bit color depth fidelity, absolute visual bite, "
                    "vivid pigment recovery on every surface, extreme local micro-contrast, "
                    "brilliant specular highlights on object edges, deep rich high-definition shadows."
                )
                a_cmd = (
                    "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, "
                    "gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on foliage, wood grain, "
                    "grass blades, house walls, concrete roads, and every environment object in frame. "
                    "Bone-dry surfaces, zero moisture, hyper-sharp edge definition across the entire frame."
                )
            
            elif "Suasana Malam" in light_type:
                l_cmd = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim light highlights, 9000k cold moonlit glow, visible background detail."
                a_cmd = "Clear night atmosphere, deep indigo-black sky, hyper-defined textures on every object."
            
            elif "Suasana Alami" in light_type:
                l_cmd = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments."
                a_cmd = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures."
            
            else: # Suasana Sore
                l_cmd = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                a_cmd = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background, zero atmospheric haze."

            # Logika Dialog & Emosi
            d_all_text = " ".join([f"{d['name']}: \"{d['text']}\"" for d in item['dialogs'] if d['text']])
            emotion_ctx = f"Emotion Context (DO NOT RENDER TEXT): Reacting to context: '{d_all_text}'. Focus on high-fidelity facial expressions. " if d_all_text else ""

            # Character Appearance DNA Sync
            dna_str = " ".join([f"STRICT CHARACTER APPEARANCE: {c['name']} ({c['desc']})" for c in all_chars_list if c['name'] and c['name'].lower() in vis_core.lower()])

            # --- DISPLAY HASIL AKHIR ---
            st.subheader(f"HASIL PRODUKSI ADEGAN {scene_id}")
            
            # Prompt Gambar (Static)
            img_final = (
                f"buatkan gambar adegan {scene_id}. {emotion_ctx}{dna_str} Visual: {vis_core}. "
                f"Atmosphere: {a_cmd}. Lighting: {l_cmd}. {img_quality_base}"
            )
            
            # Prompt Video (Cinematic)
            vid_final = (
                f"Video Adegan {scene_id}. {e_shot_size} perspective. {e_cam_move} movement. "
                f"{emotion_ctx}{dna_str} Visual: {vis_core}. "
                f"Lighting: {l_cmd}. {vid_quality_base}"
            )
            
            c1, c2 = st.columns(2)
            with c1:
                st.caption("📸 PROMPT GAMBAR")
                st.code(img_final, language="text")
            with c2:
                st.caption(f"🎥 PROMPT VIDEO ({e_shot_size} + {e_cam_move})")
                st.code(vid_final, language="text")
            
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA | V.1.0.1")
