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
# 2. DATABASE LINK FOTO (INVISIBLE - AUTO-MATCHING SYSTEM)
# ==============================================================================
# Sistem akan mencocokkan Nama Karakter (Case-Insensitive) dengan link di bawah
LINK_REFERENSI = {
    "UDIN": "https://drive.google.com/uc?export=view&id=1f51O-_PpHdXdGQkngsTh5b1fJjHtx5l5",
    "TUNG": "https://drive.google.com/uc?export=view&id=1r94LHZSEwaurGViq1lGZ9ptPr0FOrcS5"
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
# 6. HEADER APLIKASI (KALIMAT MOTIVASI DIPERTAHANKAN)
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
# 7. MAPPING TRANSLATION (FULL EXPLICIT MANUAL - NO REDUCTION)
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
# 9. PARAMETER KUALITAS (V.1.0.3 - MASTER LIGHTING & FULL-BLEED)
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
# 10. FORM INPUT IDENTITAS (CLEAN & MANUAL - AUTO-MATCH DB)
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")

with st.expander("👥 Identitas & Fisik Karakter (WAJIB ISI)", expanded=True):
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        st.markdown("### Karakter 1")
        c_n1_v = st.text_input("Nama Karakter 1", value="UDIN", key="c_name_1_input")
        c_p1_v = st.text_area("Fisik Karakter 1 (STRICT DNA)", value="", key="c_desc_1_input", height=100, placeholder="Wajah, baju, celana, aksesoris...")
    
    with col_c2:
        st.markdown("### Karakter 2")
        c_n2_v = st.text_input("Nama Karakter 2", value="TUNG", key="c_name_2_input")
        c_p2_v = st.text_area("Fisik Karakter 2 (STRICT DNA)", value="", key="c_desc_2_input", height=100, placeholder="Wajah, baju, celana, aksesoris...")

    st.divider()
    num_extra = st.number_input("Tambah Karakter Lain", min_value=2, max_value=10, value=2)
    
    # Matching logic otomatis di balik layar (Case Insensitive)
    u1_auto = LINK_REFERENSI.get(c_n1_v.upper().strip(), "")
    u2_auto = LINK_REFERENSI.get(c_n2_v.upper().strip(), "")
    
    all_chars_list = []
    all_chars_list.append({"name": c_n1_v, "desc": c_p1_v, "url": u1_auto})
    all_chars_list.append({"name": c_n2_v, "desc": c_p2_v, "url": u2_auto})

    if num_extra > 2:
        extra_cols = st.columns(num_extra - 2)
        for ex_idx in range(2, int(num_extra)):
            with extra_cols[ex_idx - 2]:
                st.markdown(f"### Karakter {ex_idx + 1}")
                ex_name = st.text_input(f"Nama Karakter {ex_idx + 1}", key=f"ex_name_{ex_idx}")
                ex_phys = st.text_area(f"Fisik Karakter {ex_idx + 1}", key=f"ex_phys_{ex_idx}", height=100)
                ex_url_auto = LINK_REFERENSI.get(ex_name.upper().strip(), "") if ex_name else ""
                all_chars_list.append({"name": ex_name, "desc": ex_phys, "url": ex_url_auto})

# ==============================================================================
# 11. LIST ADEGAN (STRUKTUR PANJANG V.1.1.8)
# ==============================================================================
adegan_storage = []

for i_s in range(1, int(num_scenes) + 1):
    l_box_title = f"🟢 MASTER CONTROL - ADEGAN {i_s}" if i_s == 1 else f"🎬 ADEGAN {i_s}"
    
    with st.expander(l_box_title, expanded=(i_s == 1)):
        # Grid Layout 
        col_v, col_ctrl = st.columns([6.5, 3.5])
        
        with col_v:
            visual_input = st.text_area(f"Visual Adegan {i_s}", key=f"vis_input_{i_s}", height=180)
        
        with col_ctrl:
            r1_c1, r1_c2 = st.columns(2)
            with r1_c1:
                st.markdown('<p class="small-label">💡 Cahaya</p>', unsafe_allow_html=True)
                idx_l = options_lighting.index(st.session_state.m_light)
                if i_s == 1:
                    l_val = st.selectbox("L1", options_lighting, index=idx_l, key="light_input_1", on_change=global_sync_v920, label_visibility="collapsed")
                else:
                    if f"light_input_{i_s}" not in st.session_state: st.session_state[f"light_input_{i_s}"] = st.session_state.m_light
                    l_val = st.selectbox(f"L{i_s}", options_lighting, index=options_lighting.index(st.session_state[f"light_input_{i_s}"]), key=f"light_input_{i_s}", label_visibility="collapsed")
            with r1_c2:
                st.markdown('<p class="small-label">🎥 Gerak</p>', unsafe_allow_html=True)
                idx_c = indonesia_camera.index(st.session_state.m_cam)
                if i_s == 1:
                    c_val = st.selectbox("C1", indonesia_camera, index=idx_c, key="camera_input_1", on_change=global_sync_v920, label_visibility="collapsed")
                else:
                    if f"camera_input_{i_s}" not in st.session_state: st.session_state[f"camera_input_{i_s}"] = st.session_state.m_cam
                    c_val = st.selectbox(f"C{i_s}", indonesia_camera, index=indonesia_camera.index(st.session_state[f"camera_input_{i_s}"]), key=f"camera_input_{i_s}", label_visibility="collapsed")
            
            r2_c1, r2_c2 = st.columns(2)
            with r2_c1:
                st.markdown('<p class="small-label">📐 Shot</p>', unsafe_allow_html=True)
                idx_s = indonesia_shot.index(st.session_state.m_shot)
                if i_s == 1:
                    s_val = st.selectbox("S1", indonesia_shot, index=idx_s, key="shot_input_1", on_change=global_sync_v920, label_visibility="collapsed")
                else:
                    if f"shot_input_{i_s}" not in st.session_state: st.session_state[f"shot_input_{i_s}"] = st.session_state.m_shot
                    s_val = st.selectbox(f"S{i_s}", indonesia_shot, index=indonesia_shot.index(st.session_state[f"shot_input_{i_s}"]), key=f"shot_input_{i_s}", label_visibility="collapsed")
            with r2_c2:
                st.markdown('<p class="small-label">✨ Angle</p>', unsafe_allow_html=True)
                idx_a = indonesia_angle.index(st.session_state.m_angle)
                if i_s == 1:
                    a_val = st.selectbox("A1", indonesia_angle, index=idx_a, key="angle_input_1", on_change=global_sync_v920, label_visibility="collapsed")
                else:
                    if f"angle_input_{i_s}" not in st.session_state: st.session_state[f"angle_input_{i_s}"] = st.session_state.m_angle
                    a_val = st.selectbox(f"A{i_s}", indonesia_angle, index=indonesia_angle.index(st.session_state[f"angle_input_{i_s}"]), key=f"angle_input_{i_s}", label_visibility="collapsed")

        # Dialog Dinamis
        diag_cols = st.columns(len(all_chars_list))
        scene_dialogs_list = []
        for i_char, char_data in enumerate(all_chars_list):
            with diag_cols[i_char]:
                char_label = char_data['name'] if char_data['name'] else f"Tokoh {i_char+1}"
                d_in = st.text_input(f"Dialog {char_label}", key=f"diag_{i_s}_{i_char}")
                scene_dialogs_list.append({"name": char_label, "text": d_in})
        
        adegan_storage.append({"num": i_s, "visual": visual_input, "light": l_val, "cam": c_val, "shot": s_val, "angle": a_val, "dialogs": scene_dialogs_list})


st.divider()


# ==============================================================================
# 12. GENERATOR PROMPT (PEMISAHAN TUGAS OPTIMIZED - V.1.3.7)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    
    active_scenes = [a for a in adegan_storage if a["visual"].strip() != ""]
    
    if not active_scenes:
        st.warning("Mohon isi deskripsi visual adegan!")
    else:
        # LOGGING CLOUD
        record_to_sheets(st.session_state.active_user, active_scenes[0]["visual"], len(active_scenes))
        
        # 1. LINK URL DITARUH DI DEPAN DENGAN LABEL JELAS
        ref_header = "Character Visual References: " + " ".join([f"{c['name']}: [{c['url']}]" for c in all_chars_list if c['url']]) + ". "
        
        # 2. MASTER LOCK (ADEGAN 1)
        char_defs_full = ", ".join([f"Karakter {idx+1} ({c['name']}: {c['desc']})" for idx, c in enumerate(all_chars_list) if c['name']])
        master_lock_instruction = f"IMPORTANT: Remember ini characters and their physical traits for this entire session: {char_defs_full}. "

        for item in active_scenes:
            
            # --- LOGIKA SMART CAMERA MOVEMENT (FULL V.1.1.8 - NO REDUCTION) ---
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

            # Konversi Teknis Lainnya
            e_shot_size = shot_map.get(item["shot"], "Medium Shot")
            e_angle_cmd = angle_map.get(item["angle"], "")
            
            scene_id = item["num"]
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

            # 3. DNA FOKUS PADA WAJAH (IDENTITAS DARI LINK)
            dna_injection = ""
            for n in [c['name'] for c in all_chars_list]:
                if n.lower() in vis_lower:
                    dna_injection += f"Use facial identity of {n} from reference link. "

            # --- DISPLAY HASIL AKHIR ---
            st.subheader(f"✅ Hasil Adegan {scene_id}")
            
            img_final = (
                f"{ref_header}{master_lock_instruction if scene_id==1 else ''}STATIC photograph, 9:16. "
                f"{e_angle_cmd} {emotion_ctx}{dna_injection} Visual scene: {vis_core_final}. "
                f"Atmosphere: {a_cmd}. Lighting: {l_cmd}. {img_quality_base} --ar 9:16"
            )
            
            vid_final = (
                f"{ref_header}{master_lock_instruction if scene_id==1 else ''}9:16 video. {e_shot_size} perspective. "
                f"{e_angle_cmd} {e_cam_move}. {emotion_ctx}{dna_injection} Visual scene: {vis_core_final}. "
                f"Lighting: {l_cmd}. {vid_quality_base}"
            )
            
            c1, c2 = st.columns(2)
            with c1:
                st.caption("📸 PROMPT GAMBAR (STATIC)")
                st.code(img_final, language="text")
            with c2:
                st.caption(f"🎥 PROMPT VIDEO ({e_shot_size} + {e_cam_move})")
                st.code(vid_final, language="text")
            
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA | V.1.3.7")
