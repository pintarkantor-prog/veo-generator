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

# GANTI DENGAN URL GOOGLE SHEETS ANDA (SHARE SEBAGAI EDITOR)
SQL_URL = "https://docs.google.com/spreadsheets/d/1nS0fQ-rCCUA3JcjV1YYqqI3RlSg7Q0_LtMJlPRzkZPE/edit?usp=sharing"


# ==============================================================================
# 2. SISTEM LOGIN & DATABASE USER (MANUAL EXPLICIT)
# ==============================================================================
USERS = {
    "admin": "QWERTY21ab",
    "icha01": "mnbvc098",
    "nisa02": "zxcv123"
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
# 3. LOGIKA LOGGING GOOGLE SHEETS (CLOUD STORAGE)
# ==============================================================================
def record_to_sheets(user, first_visual, total_scenes):
    """Mencatat aktivitas karyawan langsung ke Google Sheets secara Cloud"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Membaca data lama
        existing_data = conn.read(spreadsheet=SQL_URL)
        
        # Membuat entri data baru secara eksplisit
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_row = pd.DataFrame([{
            "Waktu": current_time,
            "User": user,
            "Total Adegan": total_scenes,
            "Visual Utama": first_visual[:150]
        }])
        
        # Menggabungkan data
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        
        # Kirim kembali ke Cloud
        conn.update(spreadsheet=SQL_URL, data=updated_df)
        
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
c_tit, c_out = st.columns([8, 2])
with c_tit:
    st.title("📸 PINTAR MEDIA")
    st.info(f"Staf Aktif: {st.session_state.active_user} | v9.19 | CLOUD PRODUCTION ❤️")
with c_out:
    if st.button("Logout 🚪"):
        st.session_state.logged_in = False
        st.rerun()


# ==============================================================================
# 6. MAPPING TRANSLATION & OPTIONS
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

def global_sync_v919():
    l1 = st.session_state.light_input_1
    c1 = st.session_state.camera_input_1
    s1 = st.session_state.shot_input_1
    
    st.session_state.m_light = l1
    st.session_state.m_cam = c1
    st.session_state.m_shot = s_1
    
    for key in st.session_state.keys():
        if key.startswith("light_input_"): st.session_state[key] = l1
        if key.startswith("camera_input_"): st.session_state[key] = c1
        if key.startswith("shot_input_"): st.session_state[key] = s1


# ==============================================================================
# 7. SIDEBAR: KONFIGURASI TOKOH (MANUAL EXPLICIT - NO REDUCTION)
# ==============================================================================
with st.sidebar:
    # FITUR KHUSUS ADMIN
    if st.session_state.active_user == "admin":
        st.header("📊 Admin Monitor")
        if st.checkbox("Buka Database Google Sheets"):
            try:
                conn_a = st.connection("gsheets", type=GSheetsConnection)
                df_a = conn_a.read(spreadsheet=SQL_URL)
                st.dataframe(df_a)
            except:
                st.warning("Pastikan URL Sheets sudah benar.")
        st.divider()

    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Adegan Total", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Karakter")
    
    # --- Karakter 1 Manual ---
    st.markdown("### Karakter 1")
    c_n1 = st.text_input("Nama Karakter 1", key="c_name_1_input")
    c_p1 = st.text_area("Fisik Karakter 1 (STRICT)", key="c_desc_1_input", height=80)
    
    st.divider()
    
    # --- Karakter 2 Manual ---
    st.markdown("### Karakter 2")
    c_n2 = st.text_input("Nama Karakter 2", key="c_name_2_input")
    c_p2 = st.text_area("Fisik Karakter 2 (STRICT)", key="c_desc_2_input", height=80)

    # --- Tambah Karakter Manual (v9.15 Style) ---
    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=10, value=2)
    
    all_chars_data = []
    all_chars_data.append({"name": c_n1, "desc": c_p1})
    all_chars_data.append({"name": c_n2, "desc": c_p2})

    if num_extra > 2:
        for ex_idx in range(2, int(num_extra)):
            st.divider()
            st.markdown(f"### Karakter {ex_idx + 1}")
            ex_name = st.text_input(f"Nama Karakter {ex_idx + 1}", key=f"ex_name_{ex_idx}")
            ex_phys = st.text_area(f"Fisik Karakter {ex_idx + 1}", key=f"ex_phys_{ex_idx}", height=80)
            all_chars_data.append({"name": ex_name, "desc": ex_phys})


# ==============================================================================
# 8. PARAMETER KUALITAS (ULTIMATE FIDELITY - NO REDUCTION)
# ==============================================================================
no_text_lock = (
    "STRICTLY NO rain, NO wet ground, NO speech bubbles, NO text, NO watermark, NO letters, NO subtitles."
)

img_quality_base = (
    "photorealistic surrealism style, 16-bit color bit depth, hyper-saturated organic pigments, "
    "f/11 deep focus aperture, micro-contrast enhancement, intricate micro-textures, 8k resolution, " + no_text_lock
)

vid_quality_base = (
    "ultra-high-fidelity vertical video, 9:16, 60fps, photorealistic surrealism, "
    "fluid organic motion, lossless texture quality, " + no_text_lock
)


# ==============================================================================
# 9. FORM INPUT ADEGAN (MANUAL GRID - NO COMPRESSION)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
adegan_storage = []

for idx_s in range(1, int(num_scenes) + 1):
    
    label_box = f"🟢 MASTER CONTROL - ADEGAN {idx_s}" if idx_s == 1 else f"🎬 ADEGAN {idx_s}"
    
    with st.expander(label_box, expanded=(idx_s == 1)):
        
        c_vis, c_lit, c_cam, c_sht = st.columns([4, 1.5, 1.5, 1.5])
        
        with c_vis:
            v_input = st.text_area(f"Visual Adegan {idx_s}", key=f"vis_input_{idx_s}", height=150)
        
        with c_lit:
            st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
            if idx_s == 1:
                l_val = st.selectbox("L1", options_lighting, key="light_input_1", on_change=global_sync_v919, label_visibility="collapsed")
            else:
                if f"light_input_{idx_s}" not in st.session_state: st.session_state[f"light_input_{idx_s}"] = st.session_state.m_light
                l_val = st.selectbox(f"L{idx_s}", options_lighting, key=f"light_input_{idx_s}", label_visibility="collapsed")
        
        with c_cam:
            st.markdown('<p class="small-label">🎥 Gerak Video</p>', unsafe_allow_html=True)
            if idx_s == 1:
                c_val = st.selectbox("C1", indonesia_camera, key="camera_input_1", on_change=global_sync_v919, label_visibility="collapsed")
            else:
                if f"camera_input_{idx_s}" not in st.session_state: st.session_state[f"camera_input_{idx_s}"] = st.session_state.m_cam
                c_val = st.selectbox(f"C{idx_s}", indonesia_camera, key=f"camera_input_{idx_s}", label_visibility="collapsed")

        with c_sht:
            st.markdown('<p class="small-label">📐 Ukuran Shot</p>', unsafe_allow_html=True)
            if idx_s == 1:
                s_val = st.selectbox("S1", indonesia_shot, key="shot_input_1", on_change=global_sync_v919, label_visibility="collapsed")
            else:
                if f"shot_input_{idx_s}" not in st.session_state: st.session_state[f"shot_input_{idx_s}"] = st.session_state.m_shot
                s_val = st.selectbox(f"S{idx_s}", indonesia_shot, key=f"shot_input_{idx_s}", label_visibility="collapsed")

        # Dialog Dinamis Manual
        diag_cols = st.columns(len(all_chars_data))
        sc_dialogs = []
        for ic, cd in enumerate(all_chars_data):
            with diag_cols[ic]:
                clbl = cd['name'] if cd['name'] else f"Tokoh {ic+1}"
                din = st.text_input(f"Dialog {clbl}", key=f"diag_{idx_s}_{ic}")
                sc_dialogs.append({"name": clbl, "text": din})
        
        adegan_storage.append({
            "num": idx_s, "visual": v_input, "light": l_val, "cam": c_val, "shot": s_val, "dialogs": sc_dialogs
        })


st.divider()


# ==============================================================================
# 10. GENERATOR PROMPT (THE ULTIMATE MEGA STRUCTURE - MANUAL EXPLICIT)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    
    active_adegan = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_adegan:
        st.warning("Mohon isi deskripsi visual adegan!")
    else:
        # SIMPAN LOG KE GOOGLE SHEETS
        record_to_sheets(st.session_state.active_user, active_adegan[0]["visual"], len(active_adegan))
        
        for item in active_adegan:
            
            # Konversi Manual dari UI ke Teknis Inggris
            final_cam = camera_map.get(item["cam"], "Static")
            final_shot = shot_map.get(item["shot"], "Medium Shot")
            
            s_id_num = item["num"]
            visual_text = item["visual"]
            lighting_sel = item["light"]
            
            # --- FULL MEGA STRUCTURE LIGHTING LOGIC (RESTORED MANUAL) ---
            if "Bening" in lighting_sel:
                f_light_cmd = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
                f_atmos_cmd = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
            
            elif "Sejuk" in lighting_sel:
                f_light_cmd = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
                f_atmos_cmd = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
            
            elif "Dramatis" in lighting_sel:
                f_light_cmd = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
                f_atmos_cmd = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
            
            elif "Jelas" in lighting_sel:
                f_light_cmd = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
                f_atmos_cmd = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
            
            elif "Mendung" in lighting_sel:
                f_light_cmd = (
                    "Intense moody overcast lighting with 16-bit color depth fidelity, absolute visual bite, "
                    "vivid pigment recovery on every surface, extreme local micro-contrast, "
                    "brilliant specular highlights on object edges, deep rich high-definition shadows."
                )
                f_atmos_cmd = (
                    "Moody atmosphere with zero atmospheric haze, 8000k ice-cold temperature brilliance, "
                    "gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on foliage, wood grain, "
                    "grass blades, house walls, concrete roads, and every environment object in frame. "
                    "Bone-dry surfaces, zero moisture, hyper-sharp edge definition across the entire frame."
                )
            
            elif "Suasana Malam" in lighting_sel:
                f_light_cmd = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim light highlights, 9000k cold moonlit glow, visible background detail."
                f_atmos_cmd = "Clear night atmosphere, deep indigo-black sky, hyper-defined textures on every object."
            
            elif "Suasana Alami" in lighting_sel:
                f_light_cmd = "Low-exposure natural sunlight, high local contrast amplification on all environmental objects, extreme chlorophyll color depth, hyper-saturated organic plant pigments."
                f_atmos_cmd = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures."
            
            else: # Suasana Sore
                f_light_cmd = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                f_atmos_cmd = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background, zero atmospheric haze."

            # Logika Dialog Gabungan
            d_list_all = [f"{d['name']}: \"{d['text']}\"" for d in item['dialogs'] if d['text']]
            d_full_str = " ".join(d_list_all)
            
            emotion_logic = f"Emotion Context (DO NOT RENDER TEXT): Reacting to context: '{d_full_str}'. Focus on high-fidelity facial expressions. " if d_full_str else ""

            # Character Appearance DNA Sync
            char_dna_str = " ".join([f"STRICT CHARACTER APPEARANCE: {c['name']} ({c['desc']})" for c in all_chars_data if c['name'] and c['name'].lower() in visual_text.lower()])

            # --- DISPLAY HASIL AKHIR ---
            st.subheader(f"HASIL PRODUKSI ADEGAN {s_id_num}")
            
            # Prompt Gambar (Static)
            final_img_prompt = (
                f"buatkan gambar adegan {s_id_num}. {emotion_logic}{char_dna_str} Visual: {visual_text}. "
                f"Atmosphere: {f_atmos_cmd}. Lighting: {f_light_cmd}. {img_quality_base}"
            )
            
            # Prompt Video (Cinematic Move & Shot)
            final_vid_prompt = (
                f"Video Adegan {s_id_num}. {final_shot} perspective. {final_cam} movement. "
                f"{emotion_logic}{char_dna_str} Visual: {visual_text}. "
                f"Lighting: {f_light_cmd}. {vid_quality_base}"
            )
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.caption("📸 PROMPT GAMBAR")
                st.code(final_img_prompt, language="text")
            with col_r2:
                st.caption(f"🎥 PROMPT VIDEO ({final_shot} + {final_cam})")
                st.code(final_vid_prompt, language="text")
            
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.19 - Cloud Monitoring Edition")
