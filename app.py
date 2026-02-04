import streamlit as st

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide", initial_sidebar_state="expanded")

# ==============================================================================
# 2. CUSTOM CSS
# ==============================================================================
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1c24 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff !important; }
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important; color: white !important;
        opacity: 1 !important; border-radius: 6px !important; border: 2px solid #ffffff !important;
        transform: scale(1.1); box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    .stTextArea textarea { font-size: 14px !important; line-height: 1.5 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 PINTAR MEDIA")
st.info("Mode: v9.38 | INFINITY CHARACTER | MASTER-SYNC | NO REDUCTION ❤️")

# ==============================================================================
# 3. SIDEBAR: DINAMIS KARAKTER
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Konfigurasi Utama")
    num_scenes = st.number_input("Jumlah Total Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("🎬 Gaya Visual (Keseluruhan)")
    tone_style = st.selectbox("Pilih Gaya Visual", ["None", "Sinematik", "Warna Menyala", "Dokumenter", "Film Jadul", "Film Thriller", "Dunia Khayalan"])

    st.divider()
    st.subheader("👥 Pengaturan Karakter")
    # INI KUNCINYA: Kamu bisa tentukan mau berapa karakter saja di sini
    num_chars = st.number_input("Jumlah Karakter", min_value=1, max_value=20, value=2)
    
    char_list = []
    for i in range(1, num_chars + 1):
        st.markdown(f"#### Tokoh {i}")
        c_n = st.text_input(f"Nama Tokoh {i}", placeholder=f"Nama {i}", key=f"sn_{i}")
        c_f = st.text_area(f"Fisik Dasar {i}", placeholder="Deskripsi wajah...", height=70, key=f"sf_{i}")
        c_p = st.text_input(f"Pakaian {i}", key=f"sp_{i}")
        char_list.append({"name": c_n, "base": c_f, "outfit": c_p})
        if i < num_chars: st.divider()

# ==============================================================================
# 4. LOGIKA MASTER-SYNC
# ==============================================================================
options_lighting = ["Bening dan Tajam", "Sejuk dan Terang", "Dramatis", "Jelas dan Solid", "Suasana Sore", "Mendung", "Suasana Malam", "Suasana Alami"]

if 'master_light' not in st.session_state:
    st.session_state.master_light = options_lighting[0]

def update_all_lights():
    if "light_1" in st.session_state:
        st.session_state.master_light = st.session_state["light_1"]
        for i in range(2, 51): st.session_state[f"light_{i}"] = st.session_state.master_light

no_text = "STRICTLY NO speech bubbles, NO text, NO typography, NO watermark, NO subtitles, NO letters."
img_q = "photorealistic surrealism, 16-bit color, 8k, absolute fidelity to character reference, " + no_text

# ==============================================================================
# 5. FORM INPUT ADEGAN (DINAMIS MENGIKUTI JUMLAH KARAKTER)
# ==============================================================================
st.subheader("📝 Detail Adegan")
adegan_storage = []
options_cond = ["Normal/Bersih", "Terluka/Lecet", "Kotor/Berdebu", "Hancur Parah"]

for idx_s in range(1, int(num_scenes) + 1):
    is_leader = (idx_s == 1)
    with st.expander(f"KONFIGURASI ADEGAN {idx_s}", expanded=is_leader):
        c_vis, c_light = st.columns([3, 1])
        with c_vis: v_in = st.text_area(f"Visual Scene {idx_s}", key=f"vis_{idx_s}", height=100)
        with c_light:
            if is_leader:
                l_val = st.selectbox("Cuaca", options_lighting, key="light_1", on_change=update_all_lights)
            else:
                if f"light_{idx_s}" not in st.session_state: st.session_state[f"light_{idx_s}"] = st.session_state.master_light
                l_val = st.selectbox(f"Cahaya {idx_s}", options_lighting, key=f"light_{idx_s}")

        st.markdown("---")
        # Layout Karakter yang fleksibel (2 karakter per baris)
        char_scene_data = []
        for i in range(0, num_chars, 2):
            cols = st.columns([1, 1.5, 1, 1.5])
            # Karakter pertama di baris ini
            c_idx = i
            c_name = char_list[c_idx]["name"] if char_list[c_idx]["name"] else f"T{c_idx+1}"
            with cols[0]: co = st.selectbox(f"Kond {c_name}", options_cond, key=f"cond_{c_idx}_{idx_s}")
            with cols[1]: di = st.text_input(f"Dialog {c_name}", key=f"diag_{c_idx}_{idx_s}")
            char_scene_data.append((co, di))
            
            # Karakter kedua di baris ini (jika ada)
            if c_idx + 1 < num_chars:
                c_idx2 = i + 1
                c_name2 = char_list[c_idx2]["name"] if char_list[c_idx2]["name"] else f"T{c_idx2+1}"
                with cols[2]: co2 = st.selectbox(f"Kond {c_name2}", options_cond, key=f"cond_{c_idx2}_{idx_s}")
                with cols[3]: di2 = st.text_input(f"Dialog {c_name2}", key=f"diag_{c_idx2}_{idx_s}")
                char_scene_data.append((co2, di2))

        adegan_storage.append({"num": idx_s, "visual": v_in, "lighting": l_val, "chars": char_scene_data})

# ==============================================================================
# 6. GENERATOR PROMPT
# ==============================================================================
if st.button("🚀 GENERATE SEMUA PROMPT", type="primary"):
    for adegan in [a for a in adegan_storage if a["visual"].strip() != ""]:
        l_t = adegan["lighting"]
        if l_t == "Mendung":
            f_l, f_a = "Intense moody overcast, vivid pigment.", "Moody atmosphere, 8000k ice-cold, thick clouds."
        elif l_t == "Suasana Malam":
            f_l, f_a = "Hyper-Chrome Fidelity, intense HMI.", "Pure vacuum-like atmosphere, 10000k white light."
        else: f_l, f_a = f"{l_t} lighting", f"Clear {l_t} atmosphere"

        style_map = {"Sinematik": "Gritty Cinematic", "Warna Menyala": "Vibrant Pop", "Dokumenter": "High-End Documentary", "Film Jadul": "Vintage Film 35mm", "Film Thriller": "Dark Thriller", "Dunia Khayalan": "Surreal Dreamy"}
        s_lock = f"Overall Visual Tone: {style_map.get(tone_style, '')}. " if tone_style != "None" else ""
        
        c_prompts = []
        status_map = {"Normal/Bersih": "clean skin.", "Terluka/Lecet": "scratches.", "Kotor/Berdebu": "covered in dust.", "Hancur Parah": "heavily damaged, cracks."}
        
        for i in range(num_chars):
            name = char_list[i]["name"]
            if name and name.lower() in adegan["visual"].lower():
                cond, diag = adegan["chars"][i]
                emo = f"Expression: reacting to '{diag}'. " if diag else ""
                c_prompts.append(f"CHARACTER REF: {char_list[i]['base']}, wearing {char_list[i]['outfit']}, status: {status_map[cond]}. {emo}")

        final_c = " ".join(c_prompts) + " "
        st.subheader(f"ADENGAN {adegan['num']}")
        st.code(f"{s_lock}{final_c}Visual Scene: {adegan['visual']}. Atmosphere: {f_a}. Lighting: {f_l}. {img_q}")
        st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v9.38 - Infinity Character Edition")


