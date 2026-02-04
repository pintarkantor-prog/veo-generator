import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PINTAR MEDIA - Storyboard Generator", layout="wide")

# --- 2. KONFIGURASI API OTOMATIS ---
# API Key ditanam langsung agar tidak perlu isi manual tiap buka aplikasi
MY_API_KEY = "AIzaSyBJdViWnCZ7cnQE3Wx-c_WJQpWH_zsEHpI"
genai.configure(api_key=MY_API_KEY)

# --- 3. CUSTOM CSS (TOMBOL COPY HIJAU & STYLING HASIL) ---
st.markdown("""
    <style>
    /* Tombol Copy Hijau Terang agar terlihat jelas */
    button[title="Copy to clipboard"] {
        background-color: #28a745 !important;
        color: white !important;
        opacity: 1 !important;
        border-radius: 6px !important;
        border: 1px solid #ffffff !important;
        transform: scale(1.1);
    }
    button[title="Copy to clipboard"]:active {
        background-color: #1e7e34 !important;
    }
    /* Styling Hasil Gambar API agar rapi dengan border hijau */
    .stImage > img {
        border-radius: 12px;
        border: 3px solid #28a745;
    }
    /* Mengatur jarak area input */
    .stTextArea textarea {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Judul Utama & Pesan Penyemangat
st.title("📸 PINTAR MEDIA")
st.info("semangat buat alur cerita nya guys ❤️❤️❤️")

# --- 4. SIDEBAR: KONFIGURASI TOKOH ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas & Fisik Tokoh")
    st.caption("Masukkan detail fisik dari foto referensi kamu agar karakter konsisten.")
    
    characters = []

    # Karakter 1
    st.markdown("**Karakter 1**")
    c1_name = st.text_input("Nama Karakter 1", key="char_name_0", placeholder="Contoh: UDIN")
    c1_desc = st.text_area("Fisik Karakter 1 (Gunakan Detail Foto)", key="char_desc_0", 
                          placeholder="Contoh: Pria, topi orange, kaos putih, wajah bulat...", height=80)
    characters.append({"name": c1_name, "desc": c1_desc})
    
    st.divider()

    # Karakter 2
    st.markdown("**Karakter 2**")
    c2_name = st.text_input("Nama Karakter 2", key="char_name_1", placeholder="Contoh: TUNG")
    c2_desc = st.text_area("Fisik Karakter 2 (Gunakan Detail Foto)", key="char_desc_1", 
                          placeholder="Contoh: Kepala balok kayu, kemeja flanel, badan kayu...", height=80)
    characters.append({"name": c2_name, "desc": c2_desc})

    st.divider()

    # Pilihan Tambah Karakter (3-5)
    num_chars = st.number_input("Total Karakter (Minimal 2)", min_value=2, max_value=5, value=2)

    if num_chars > 2:
        for j in range(2, int(num_chars)):
            st.divider()
            st.markdown(f"**Karakter {j+1}**")
            cn = st.text_input(f"Nama Karakter {j+1}", key=f"char_name_{j}", placeholder=f"Contoh: TOKOH {j+1}")
            cd = st.text_area(f"Fisik Karakter {j+1}", key=f"char_desc_{j}", placeholder="Ciri fisik...", height=68)
            characters.append({"name": cn, "desc": cd})

# --- 5. PARAMETER KUALITAS (Tanpa kata 'Realistic') ---
img_quality = (
    "natural photography style, raw photo, captured on 35mm lens, f/8, "
    "authentic skin texture, natural lighting, sharp details, "
    "unprocessed look, NO 3D, NO render, NO cartoon, high resolution"
)

vid_quality = (
    "natural handheld video, 60fps, authentic motion, real-world environment, "
    "clear high definition, raw footage style, NO animation, NO CGI, life-like movement"
)

# --- 6. FORM INPUT ADEGAN ---
st.subheader("📝 Detail Adegan")
scene_data = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"INPUT DATA ADEGAN {i}", expanded=(i == 1)):
        # Layout: Visual (2) + Waktu (1) + Dialog Tokoh (1 per karakter)
        col_setup = [2, 1] + [1] * len(characters)
        cols = st.columns(col_setup)
        
        with cols[0]:
            user_desc = st.text_area(f"Visual Adegan {i}", key=f"desc_{i}", height=100)
        
        with cols[1]:
            scene_time = st.selectbox(f"Waktu {i}", ["Pagi hari", "Siang hari", "Sore hari", "Malam hari"], key=f"time_{i}")
        
        scene_dialogs = []
        for idx, char in enumerate(characters):
            with cols[idx + 2]:
                char_label = char['name'] if char['name'] else f"Karakter {idx+1}"
                d_input = st.text_input(f"Dialog {char_label}", key=f"diag_{idx}_{i}")
                scene_dialogs.append({"name": char_label, "text": d_input})
        
        scene_data.append({
            "num": i, 
            "desc": user_desc, 
            "time": scene_time,
            "dialogs": scene_dialogs
        })

st.divider()

# --- 7. TOMBOL GENERATE (LOGIKA UTAMA) ---
if st.button("🚀 BUAT PROMPT & GENERATE VISUAL", type="primary"):
    # Filter adegan yang tidak kosong
    filled_scenes = [s for s in scene_data if s["desc"].strip() != ""]
    
    if not filled_scenes:
        st.warning("Silakan isi kolom 'Visual Adegan' pada form yang tersedia.")
    else:
        st.header("📋 Hasil Output PINTAR MEDIA")
        
        for scene in filled_scenes:
            i = scene["num"]
            v_input = scene["desc"]
            
            # Deteksi Karakter Pintar (Smart Trigger Deskripsi Fisik)
            detected_physique = []
            for char in characters:
                if char['name'] and char['name'].lower() in v_input.lower():
                    detected_physique.append(f"{char['name']} ({char['desc']})")
            
            char_ref = "Characters Appearance: " + ", ".join(detected_physique) + ". " if detected_physique else ""
            
            # Waktu Mapping ke Inggris
            time_map = {
                "Pagi hari": "morning golden hour",
                "Siang hari": "midday bright sunlight",
                "Sore hari": "sunset warm glow",
                "Malam hari": "night ambient light"
            }
            eng_time = time_map.get(scene["time"], "natural light")
            
            # --- PROMPT GAMBAR (Fokus Referensi & Konsistensi) ---
            ref_instr = "Gunakan deskripsi fisik karakter berikut sebagai referensi utama agar konsisten di setiap adegan. "
            mand_instr = "Saya sedang membangun alur cerita visual yang koheren. "
            
            final_img = (
                f"{ref_instr}{mand_instr}Adegan ke-{i}: \n"
                f"Visual: {char_ref}{v_input}. Waktu: {scene['time']}. "
                f"Lighting: {eng_time}. {img_quality}"
            )

            # --- PROMPT VIDEO (Copy Manual untuk Veo 3) ---
            dialog_lines = [f"{d['name']}: \"{d['text']}\"" for d in scene['dialogs'] if d['text']]
            dialog_part = f"\n\nDialog:\n" + "\n".join(dialog_lines) if dialog_lines else ""

            final_vid = (
                f"Generate natural motion for Scene {i}. \n"
                f"Visual: {char_ref}{v_input}. Time: {eng_time}. {vid_quality}.{dialog_part}"
            )

            # --- TAMPILAN OUTPUT PER ADEGAN ---
            st.subheader(f"Adegan {i}")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.caption("📸 PROMPT & GENERATE GAMBAR")
                st.code(final_img, language="text")
                
                # Tombol Generate Gambar via API
                if st.button(f"Generate Visual Adegan {i}", key=f"btn_{i}"):
                    with st.spinner(f"Memproses visual berdasarkan referensi deskripsi adegan {i}..."):
                        try:
                            # Memanggil model Imagen 3 (Gunakan ID model yang aktif di akun Anda)
                            model = genai.GenerativeModel('imagen-3.0-generate-001')
                            response = model.generate_content(final_img)
                            # Menampilkan Hasil Gambar
                            st.image(response.images[0], use_container_width=True, caption=f"Visual Adegan {i}")
                        except Exception as e:
                            st.error(f"Gagal generate: {e}. Pastikan model 'imagen-3.0-generate-001' tersedia.")

            with col_b:
                st.caption("🎥 PROMPT VIDEO (Copy ke Veo 3)")
                st.code(final_vid, language="text")
            
            st.divider()

st.sidebar.markdown("---")
st.sidebar.caption("PINTAR MEDIA Storyboard v3.2 (Auto-API)")
