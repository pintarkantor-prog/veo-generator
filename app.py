import streamlit as st

st.set_page_config(page_title="AI Storyboard Generator", layout="wide")

st.title("🎬 High-End Storyboard Prompt Generator")
st.markdown("Generator ini dirancang untuk hasil **Ultra-Realistic** (Bukan Kartun) dengan konsistensi antar adegan.")

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("Pengaturan Global")
    num_scenes = st.number_input("Jumlah Adegan", min_value=1, max_value=50, value=10)
    
    st.divider()
    st.subheader("Dialog Karakter")
    char_a_name = st.text_input("Nama Karakter A", value="Karakter A")
    char_b_name = st.text_input("Nama Karakter B", value="Karakter B")

# --- MAIN FORM ---
st.subheader("Konfigurasi Adegan")

# Template Kualitas Realistis (Bahasa Inggris agar AI paham teknis kamera)
# Namun instruksi khusus tetap dalam Bahasa Indonesia sesuai permintaan Anda.
quality_tags = (
    "ultra-realistic photography, cinematic lighting, shot on 8k RED V-Raptor XL, "
    "35mm lens, f/1.8, highly detailed skin texture, sharp focus, hyper-realistic, "
    "no cartoon, no 3D render, photorealistic, professional cinematography"
)

all_prompts = []

for i in range(1, int(num_scenes) + 1):
    with st.expander(f"Adegan Ke-{i}", expanded=(i == 1)):
        col1, col2 = st.columns(2)
        
        with col1:
            desc = st.text_area(f"Deskripsi Visual Adegan {i}", placeholder="Sedang apa? Di mana?", key=f"desc_{i}")
        
        with col2:
            diag_a = st.text_input(f"Dialog {char_a_name}", key=f"diag_a_{i}")
            diag_b = st.text_input(f"Dialog {char_b_name}", key=f"diag_b_{i}")

        # LOGIKA FORMULASI PROMPT
        ref_sentence = "ini adalah gambar referensi karakter saya. " if i == 1 else ""
        consistent_sentence = "saya ingin membuat gambar secara konsisten adegan per adegan. "
        scene_sentence = f"buatkan saya sebuah gambar adegan ke {i}. "
        
        # Penggabungan Dialog
        dialogue_part = ""
        if diag_a or diag_b:
            dialogue_part = f"\nDialog: [{char_a_name}: '{diag_a}'] | [{char_b_name}: '{diag_b}']"

        # Hasil Akhir Prompt per Adegan
        full_prompt = (
            f"{ref_sentence}{consistent_sentence}{scene_sentence}\n"
            f"Visual: {desc}. {quality_tags}.{dialogue_part}"
        )
        all_prompts.append(full_prompt)

# --- OUTPUT ---
st.divider()
st.header("Hasil Prompt Adegan")

if st.button("Generate Semua Prompt"):
    for idx, prompt in enumerate(all_prompts, 1):
        st.subheader(f"Prompt Adegan {idx}")
        st.code(prompt, language="text")

# Fitur Download
full_text = "\n\n".join([f"--- ADEGAN {i+1} ---\n{p}" for i, p in enumerate(all_prompts)])
st.download_button("Download Semua Prompt (.txt)", full_text, file_name="storyboard_prompts.txt")
