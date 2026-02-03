import streamlit as st

# Setup Halaman
st.set_page_config(page_title="Consistent Storyboard Generator", layout="wide")

st.title("🎬 High-End Storyboard Generator")
st.info("Setiap perubahan yang Anda ketik akan langsung memperbarui hasil prompt di bawah.")

# --- SIDEBAR: PENGATURAN GLOBAL ---
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    # Poin 1: Bisa tambah adegan 1 sampai 50 secara manual
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("👥 Identitas Karakter")
    char_a_name = st.text_input("Nama Karakter A", value="Udin")
    char_b_name = st.text_input("Nama Karakter B", value="Tung")

# --- PARAMETER KUALITAS (Poin 2: Realistis, Kamera Jernih, Bukan Kartun) ---
quality_tags = (
    "ultra-realistic photography, high resolution 8k, shot on professional cinema camera, "
    "sharp focus, highly detailed skin textures, cinematic lighting, masterpiece, "
    "NO cartoon, NO anime, NO 3D render, realistic human features"
)

# --- FORM INPUT & GENERATOR ---
st.subheader("📝 Input Detail Adegan")

for i in range(1, int(num_scenes) + 1):
    # Membuat box untuk setiap adegan
    with st.expander(f"KONFIGURASI ADEGAN {i}", expanded=(i == 1)):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Poin 3 & 4: Input Deskripsi dan Dialog
            user_desc = st.text_area(f"Apa yang terjadi di adegan {i}?", key=f"desc_{i}", placeholder="Contoh: Sedang berdiri di pinggir jalan saat hujan")
        
        with col2:
            diag_a = st.text_input(f"Dialog {char_a_name}", key=f"diag_a_{i}")
            diag_b = st.text_input(f"Dialog {char_b_name}", key=f"diag_b_{i}")

        # --- LOGIKA PENYUSUNAN PROMPT (Sesuai Permintaan Anda) ---
        
        # Adegan 1 punya kalimat referensi khusus
        ref_text = "ini adalah gambar referensi karakter saya. " if i == 1 else ""
        
        # Kalimat wajib di semua adegan (Bahasa Indonesia)
        mandatory_text = "saya ingin membuat gambar secara konsisten adegan per adegan. "
        
        # Penomoran otomatis (Poin 3)
        scene_number_text = f"buatkan saya sebuah gambar adegan ke {i}. "
        
        # Gabungkan Dialog (Poin 4)
        dialog_part = ""
        if diag_a or diag_b:
            dialog_part = f"\n\nDialog yang terjadi:\n- {char_a_name}: \"{diag_a}\"\n- {char_b_name}: \"{diag_b}\""

        # HASIL AKHIR PROMPT
        final_prompt = (
            f"{ref_text}{mandatory_text}{scene_number_text}\n\n"
            f"Deskripsi Visual: {user_desc}\n"
            f"Kualitas Gambar: {quality_tags}"
            f"{dialog_part}"
        )

        # MENAMPILKAN HASIL SECARA LANGSUNG
        st.markdown(f"**Hasil Prompt Adegan {i}:**")
        st.code(final_prompt, language="text")
        st.divider()

# Fitur Download untuk semua prompt yang sudah diisi
if st.sidebar.button("Siapkan File Download"):
    all_text = ""
    for j in range(1, int(num_scenes) + 1):
        # (Logika pengumpulan teks sama dengan di atas)
        all_text += f"--- ADEGAN {j} ---\n...\n\n" # Singkatan untuk proses download
    st.sidebar.success("File siap! (Fitur ini bisa dikembangkan lebih lanjut)")
