import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ==============================================================================
# 1. KONFIGURASI HALAMAN (MEGA STRUCTURE)
# ==============================================================================
st.set_page_config(
    page_title="PINTAR MEDIA - Storyboard Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. SISTEM LOGIN
# ==============================================================================
USERS = {"admin": "QWERTY21ab", "icha": "udin99", "nissa": "tung22"}
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'active_user' not in st.session_state: st.session_state.active_user = ""

if not st.session_state.logged_in:
    st.title("🔐 PINTAR MEDIA - AKSES PRODUKSI")
    with st.form("form_login_staf"):
        input_user = st.text_input("Username")
        input_pass = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk"):
            if input_user in USERS and USERS[input_user] == input_pass:
                st.session_state.logged_in, st.session_state.active_user = True, input_user
                st.rerun()
            else: st.error("Akses Ditolak!")
    st.stop()

# ==============================================================================
# 3. DATABASE & CSS
# ==============================================================================
def record_to_sheets(user, first_visual, total_scenes):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(worksheet="Sheet1", ttl=0)
        new_row = pd.DataFrame([{"Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User": user, "Total Adegan": total_scenes, "Visual Utama": first_visual[:150]}])
        conn.update(worksheet="Sheet1", data=pd.concat([existing_data, new_row], ignore_index=True))
    except: pass

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    button[title="Copy to clipboard"] { background-color: #28a745 !important; color: white !important; }
    .stTextArea textarea { font-size: 14px !important; min-height: 180px !important; }
    .small-label { font-size: 12px; font-weight: bold; color: #a1a1a1; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 4. MAPPING FULL EXPLICIT (KEMBALI KE VERSI ASLI KAMU)
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]
indonesia_camera = ["Ikuti Karakter", "Diam (Tanpa Gerak)", "Zoom Masuk Pelan", "Zoom Keluar Pelan", "Geser Kiri ke Kanan", "Geser Kanan ke Kiri", "Dongak ke Atas", "Tunduk ke Bawah", "Ikuti Objek (Tracking)", "Memutar (Orbit)"]
indonesia_shot = ["Sangat Dekat (Detail)", "Dekat (Wajah)", "Setengah Badan", "Seluruh Badan", "Pemandangan Luas", "Sudut Rendah (Gagah)", "Sudut Tinggi (Kecil)"]
indonesia_angle = ["Normal (Depan)", "Samping (Arah Kamera)", "Berhadapan (Ngobrol)", "Intip Bahu (Framing)", "Wibawa/Gagah (Low Angle)", "Mata Karakter (POV)"]

camera_map = {"Ikuti Karakter": "AUTO_MOOD", "Diam (Tanpa Gerak)": "Static (No Move)", "Zoom Masuk Pelan": "Slow Zoom In", "Zoom Keluar Pelan": "Slow Zoom Out", "Geser Kiri ke Kanan": "Pan Left to Right", "Geser Kanan ke Kiri": "Pan Right to Left", "Dongak ke Atas": "Tilt Up", "Tunduk ke Bawah": "Tilt Down", "Ikuti Objek (Tracking)": "Tracking Shot", "Memutar (Orbit)": "Orbit Circular"}
shot_map = {"Sangat Dekat (Detail)": "Extreme Close-Up", "Dekat (Wajah)": "Close-Up", "Setengah Badan": "Medium Shot", "Seluruh Badan": "Full Body Shot", "Pemandangan Luas": "Wide Landscape Shot", "Sudut Rendah (Gagah)": "Low Angle Shot", "Sudut Tinggi (Kecil)": "High Angle Shot"}

# Kembalikan Deskripsi Angle yang Panjang
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
    st.session_state.m_light, st.session_state.m_cam = st.session_state.light_input_1, st.session_state.camera_input_1
    st.session_state.m_shot, st.session_state.m_angle = st.session_state.shot_input_1, st.session_state.angle_input_1
    for i in range(2, 51):
        for k in ["light", "camera", "shot", "angle"]:
            key = f"{k}_input_{i}"
            if key in st.session_state: st.session_state[key] = st.session_state[f"m_{k[:3]}"]

# ==============================================================================
# 5. SIDEBAR & ADMIN MONITOR
# ==============================================================================
with st.sidebar:
    if st.session_state.active_user == "admin" and st.checkbox("📊 Admin Monitor"):
        try: st.dataframe(st.connection("gsheets", type=GSheetsConnection).read(worksheet="Sheet1", ttl=0))
        except: st.warning("Database Error.")
    num_scenes = st.number_input("Jumlah Adegan", 1, 50, 10)

# ==============================================================================
# 6. IDENTITAS & KARAKTER
# ==============================================================================
st.subheader("📝 Detail Adegan Storyboard")
with st.expander("👥 Identitas & Fisik Karakter", expanded=True):
    c1, c2 = st.columns(2)
    n1 = c1.text_input("Nama Karakter 1", key="c_name_1_input").strip()
    p1 = c1.text_area("Fisik 1", key="c_desc_1_input", height=100)
    n2 = c2.text_input("Nama Karakter 2", key="c_name_2_input").strip()
    p2 = c2.text_area("Fisik 2", key="c_desc_2_input", height=100)
    
    num_extra = st.number_input("Total Karakter", 2, 10, 2)
    all_chars = []
    if n1: all_chars.append({"name": n1, "desc": p1})
    if n2: all_chars.append({"name": n2, "desc": p2})

    if num_extra > 2:
        cols = st.columns(num_extra - 2)
        for i in range(2, int(num_extra)):
            ex_n = cols[i-2].text_input(f"Nama {i+1}", key=f"ex_name_{i}").strip()
            ex_p = cols[i-2].text_area(f"Fisik {i+1}", key=f"ex_phys_{i}", height=100)
            if ex_n: all_chars.append({"name": ex_n, "desc": ex_p})

# ==============================================================================
# 7. GRID INPUT
# ==============================================================================
adegan_storage = []
for i in range(1, int(num_scenes) + 1):
    with st.expander(f"{'🟢 MASTER' if i==1 else '🎬 ADEGAN'} {i}", expanded=(i==1)):
        v_col, c_col = st.columns([6.5, 3.5])
        v_in = v_col.text_area(f"Visual {i}", key=f"vis_input_{i}", height=180)
        r1c1, r1c2 = c_col.columns(2)
        l_v = r1c1.selectbox(f"💡 Cahaya {i}", options_lighting, index=options_lighting.index(st.session_state.m_light), key=f"light_input_{i}", on_change=(global_sync_v920 if i==1 else None))
        c_v = r1c2.selectbox(f"🎥 Gerak {i}", indonesia_camera, index=indonesia_camera.index(st.session_state.m_cam), key=f"camera_input_{i}", on_change=(global_sync_v920 if i==1 else None))
        r2c1, r2c2 = c_col.columns(2)
        s_v = r2c1.selectbox(f"📐 Shot {i}", indonesia_shot, index=indonesia_shot.index(st.session_state.m_shot), key=f"shot_input_{i}", on_change=(global_sync_v920 if i_s==1 else None))
        a_v = r2c2.selectbox(f"✨ Angle {i}", indonesia_angle, index=indonesia_angle.index(st.session_state.m_angle), key=f"angle_input_{i}", on_change=(global_sync_v920 if i_s==1 else None))
        
        diag_cols = st.columns(len(all_chars) if all_chars else 1)
        diags = []
        for ic, cd in enumerate(all_chars):
            d_t = diag_cols[ic].text_input(f"Dialog {cd['name']}", key=f"diag_{i}_{ic}")
            if d_t: diags.append({"name": cd['name'], "text": d_t})
        adegan_storage.append({"num": i, "visual": v_in, "light": l_v, "cam": c_v, "shot": s_v, "angle": a_v, "dialogs": diags})

# ==============================================================================
# 8. HIERARCHICAL PROMPT GENERATOR (ULTRA QUALITY + STABILITY)
# ==============================================================================
if st.button("🚀 GENERATE ALL PROMPTS", type="primary"):
    active = [a for a in adegan_storage if a["visual"].strip() != ""]
    if not active: st.warning("Isi visual!")
    else:
        record_to_sheets(st.session_state.active_user, active[0]["visual"], len(active))
        
        # KEMBALIKAN MEGA QUALITY STACK ASLI KAMU
        full_quality_stack = (
            "Full-bleed cinematography, edge-to-edge pixel rendering, Full-frame vertical coverage, "
            "zero black borders, expansive background rendering to edges, Circular Polarizer (CPL) filter effect, "
            "eliminates light glare, ultra-high-fidelity resolution, micro-contrast enhancement, optical clarity, "
            "deep saturated pigments, vivid organic color punch, intricate organic textures, skin texture override with 8k details, "
            "f/11 aperture for deep focus sharpness, zero digital noise, zero atmospheric haze, crystal clear background focus. "
            "STRICTLY NO rain, NO wet ground, NO raindrops, NO speech bubbles, NO text, NO typography, "
            "NO watermark, NO letters, NO black bars on top and bottom, NO subtitles. --ar 9:16"
        )

        for item in active:
            v_low = item["visual"].lower()
            
            # --- TIER 1: CHARACTER DNA (PENJAGA KONSISTENSI) ---
            dna_parts = []
            for c in all_chars:
                if c['name'].lower() in v_low:
                    dna_parts.append(f"IDENTICAL CHARACTER ANCHOR: {c['name']} is ({c['desc']}). STRICT FIDELITY: Maintain identity in 8k detail.")
            dna_final = " ".join(dna_parts)

            # --- TIER 2: LIGHTING MAPPING (KEMBALIKAN DESKRIPSI PANJANG ASLI KAMU) ---
            l_type = item["light"]
            if "Bening" in l_type:
                l_cmd = "Ultra-high altitude light visibility, thin air clarity, extreme micro-contrast, zero haze."
                a_cmd = "10:00 AM mountain altitude sun, deepest cobalt blue sky, authentic wispy clouds, bone-dry environment."
            elif "Sejuk" in l_type:
                l_cmd = "8000k ice-cold color temperature, zenith sun position, uniform illumination, zero sun glare."
                a_cmd = "12:00 PM glacier-clear atmosphere, crisp cold light, deep blue sky, organic wispy clouds."
            elif "Dramatis" in l_type:
                l_cmd = "Hard directional side-lighting, pitch-black sharp shadows, high dynamic range (HDR) contrast."
                a_cmd = "Late morning sun, dramatic light rays, hyper-sharp edge definition, deep sky contrast."
            elif "Jelas" in l_type:
                l_cmd = "Deeply saturated matte pigments, circular polarizer (CPL) effect, vivid organic color punch, zero reflections."
                a_cmd = "Early morning atmosphere, hyper-saturated foliage colors, deep blue cobalt sky, crystal clear objects."
            elif "Mendung" in l_type:
                l_cmd = "Intense moody overcast lighting with 16-bit color depth fidelity, absolute visual bite, vivid pigment recovery, extreme micro-contrast."
                a_cmd = "Moody atmosphere zero atmospheric haze, 8000k ice-cold temp, gray-cobalt sky with heavy thick wispy clouds. Tactile texture definition on every object."
            elif "Suasana Malam" in l_type:
                l_cmd = "Cinematic Night lighting, dual-tone HMI spotlighting, sharp rim light highlights, 9000k cold moonlit glow."
                a_cmd = "Clear night atmosphere, deep indigo-black sky, hyper-defined textures."
            elif "Suasana Alami" in l_type:
                l_cmd = "Low-exposure natural sunlight, high local contrast amplification, extreme chlorophyll color depth."
                a_cmd = "Crystal clear forest humidity (zero haze), hyper-defined micro-pores on leaves and tree bark, intricate micro-textures."
            else: # Sore
                l_cmd = "4:00 PM indigo atmosphere, sharp rim lighting, low-intensity cold highlights, crisp silhouette definition."
                a_cmd = "Late afternoon cold sun, long sharp shadows, indigo-cobalt sky gradient, hyper-clear background."

            # --- TIER 3: RENDER FINAL ---
            st.subheader(f"✅ Adegan {item['num']}")
            
            # URUTAN HIERARKI: DNA (T1) -> VISUAL (T2) -> ATMOSPHERE/LIGHT (T2.5) -> MEGA QUALITY (T3)
            img_prompt = (
                f"IDENTICAL CHARACTER SESSION. {dna_final} "
                f"Visual: {item['visual']}. {angle_map[item['angle']]}. "
                f"Atmosphere: {a_cmd} Lighting: {l_cmd} "
                f"{full_quality_stack}"
            )
            
            vid_prompt = (
                f"IDENTICAL CHARACTER SESSION. {dna_final} "
                f"9:16 vertical video. {shot_map[item['shot']]} {camera_map[item['cam']]}. "
                f"Visual: {item['visual']}. Lighting: {l_cmd}. "
                f"60fps, fluid motion, {full_quality_stack}"
            )

            c1, c2 = st.columns(2)
            c1.markdown("**📸 Prompt Gambar**")
            c1.code(img_prompt, language="text")
            c2.markdown("**🎥 Prompt Video**")
            c2.code(vid_prompt, language="text")
            st.divider()

st.sidebar.caption("PINTAR MEDIA | V.1.4.0-FINAL")
