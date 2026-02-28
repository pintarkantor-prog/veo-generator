import streamlit as st
import requests  
import pandas as pd
import gspread 
import time
import pytz
import json
import re
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

def bersihkan_data(df):
    if df.empty: return df
    # Header jadi UPPERCASE secara aman
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Daftar kolom yang ingin dipastikan menjadi String Uppercase
    kolom_krusial = ['NAMA', 'STAF', 'STATUS', 'USERNAME', 'TANGGAL', 'DEADLINE', 'TIPE']
    
    for col in df.columns:
        if col in kolom_krusial:
            # PERBAIKAN: Gunakan .astype(str) dan .str aksesor
            df[col] = df[col].astype(str).str.strip().str.upper()
            
            # Opsional: Ubah 'NAN' string (dari data kosong) kembali menjadi string kosong
            df[col] = df[col].replace('NAN', '')
    return df

# ==============================================================================
# BAGIAN 1: PUSAT KENDALI OPSI (VERSI KLIMIS - NO REDUNDANCY)
# ==============================================================================
OPTS_STYLE = ["Sangat Nyata", "Animasi 3D Pixar", "Gaya Cyberpunk", "Anime Jepang"]
OPTS_LIGHT = ["Senja Cerah (Golden)", "Studio Bersih", "Neon Cyberpunk", "Malam Indigo", "Siang Alami"]
OPTS_ARAH  = ["Sejajar Mata", "Dari Atas", "Dari Bawah", "Dari Samping", "Berhadapan"]
OPTS_SHOT  = ["Sangat Dekat", "Wajah & Bahu", "Setengah Badan", "Seluruh Badan", "Drone (Jauh)"]
OPTS_CAM   = ["Diam (Tetap Napas)", "Maju Perlahan", "Ikuti Karakter", "Memutar", "Goyang (Handheld)"]
OPTS_RATIO = ["9:16", "16:9", "1:1"]

def rakit_prompt_sakral(aksi, style, light, arah, shot, cam):
    style_map = {
        "Sangat Nyata": "Cinematic RAW shot, PBR surfaces, 8k textures, macro-detail fidelity, f/1.8 lens focus, depth map rendering.",
        "Animasi 3D Pixar": "Disney style 3D, Octane render, ray-traced global illumination, premium subsurface scattering.",
        "Gaya Cyberpunk": "Futuristic neon aesthetic, volumetric fog, sharp reflections, high contrast.",
        "Anime Jepang": "Studio Ghibli style, hand-painted watercolor textures, soft cel shading, lush aesthetic."
    }
    
    light_map = {
        "Senja Cerah (Golden)": "4 PM golden hour, warm amber highlights, dramatic long shadows, high local contrast.",
        "Studio Bersih": "Professional studio setup, rim lighting, clean shadows, commercial photography look.",
        "Neon Cyberpunk": "Vibrant pink and blue rim light, deep noir shadows, cinematic volumetric lighting.",
        "Malam Indigo": "Cinematic night, moonlight shading, deep indigo tones, clean silhouettes.",
        "Siang Alami": "Daylight balanced exposure, neutral color temperature, crystal clear atmosphere."
    }

    s_cmd = style_map.get(style, "Cinematic optical clarity.")
    l_cmd = light_map.get(light, "Balanced exposure.")
    
    # --- PERBAIKAN: Hapus label "Technical:" agar lebih clean ---
    tech_logic = f"{shot} framing, {arah} angle, {cam} motion, cinematic optical rendering."

    return f"{s_cmd} {tech_logic} {l_cmd}"
    
DAFTAR_USER = {
    "dian": "QWERTY21ab", "icha": "udin99", "nissa": "tung22",
    "inggi": "udin33", "lisa": "tung66", "tamu": "123"
}
MASTER_CHAR = {
    "Custom": {"fisik": "", "versi_pakaian": {"Manual": ""}}, 
    
    "Udin": {
        "fisik": "",
        "versi_pakaian": {
            "Keseharian": "Black cotton t-shirt with the word 'UDIN' printed in bold white letters in the center, premium branded short denim jeans, and black rubber flip-flops.",
            "Kemeja": "Open-buttoned red and black plaid flannel shirt, plain white crewneck t-shirt underneath, black denim shorts, and white high-top sneakers. STRICTLY NO HAT, no headwear.",
            "Casual": "High-end designer oversized white t-shirt in heavy-weight premium cotton, paired with luxury light-wash distressed denim jeans. Limited-edition hypebeast sneakers. Accessorized with a diamond-encrusted watch, a solid gold bracelet, and a thick gold link chain necklace.",
            "Versi Gaul": "Vibrant pink short-sleeve button-up shirt with large tropical floral patterns, open over a white premium cotton tank top. Tailored white linen shorts. Thick gold link chain, wide gold bracelet, diamond-encrusted watch. White luxury designer sneakers.",
            "Versi Kaya": "Premium navy blue polo shirt, beige chino shorts. Sleek luxury gold watch. Brown suede boat shoes with white rubber soles.",
            "Versi Sultan": "Charcoal three-piece suit, metallic gold brocade patterns, fully buttoned. Black silk shirt, black bow tie. Thick gold link chain, large diamond-encrusted dollar pendant, gemstone rings. Black velvet loafers with shimmering micro-diamonds. Gold-rimmed sunglasses. No color bleeding; isolated gold and diamond textures.",
            "Versi Raja": "Royal crimson velvet tunic, heavy gold-threaded embroidery, high standing collar. Detailed gold metallic fibers woven throughout the fabric. Massive gemstone rings on fingers. Polished gold-tipped leather boots.",
            "Versi Miskin": "Stretched-out grey cotton t-shirt, faded fabric, visible stains. Short trousers with frayed hems. Thin blue rubber flip-flops. All fabrics feature rough, damaged, and pitted textures.",
            "Versi Gembel": "Tattered oversized undershirt, multiple irregular holes, heavy dark grime. Patchwork shorts held by a frayed rope. Mismatched worn-out sandals. Extremely distressed and soiled fabric textures with layered dirt. Surface of the orange head looks dusty and dull.",
            "Anak SD": "White short-sleeve button-up shirt, red embroidered school logo on the chest pocket. Red short trousers, elastic waistband. Red and white striped tie. Low-cut black canvas sneakers, white rubber soles. High-contrast red and white fabric textures.",
            "Anak SMA": "Short-sleeved white button-up shirt, embroidered school logo on chest pocket. Gray trousers, Slim black synthetic belt, silver buckle. Gray tie. Low-cut black canvas sneakers, white rubber sole. High contrast gray and white fabric texture."
        }
    },

    "Tung": {
        "fisik": "",
        "versi_pakaian": {
            "Keseharian 1": "Forest green cotton T-shirt. Charcoal grey long trousers. Brown rubber flip-flops. zero accessories.",
            "Keseharian 2": "A worn blue polo shirt, worn gray sweatpants and rubber flip-flops.",            
            "Kemeja": "Open-buttoned blue and white plaid flannel shirt, plain white crewneck t-shirt underneath, long blue denim jeans, and brown leather boots. STRICTLY NO HAT, no headwear.",
            "Casual": "dark gray polo shirt with honeycomb motif, dark gray twill shorts. shiny brown belt. shiny brown shoes.",
            "Versi Gaul": "Pink polo shirt, monogram pattern, silk-pique blend, shiny gold-rimmed buttons. Dark royal pink chino shorts, satin stitching, high-gloss finish. Chocolate brown crocodile leather belt, oversized gold 'T' logo buckle. Diamond-encrusted gold watch, heavy metallic link strap. White crocodile leather loafers, gold horsebit hardware. No sunglasses, zero headwear. Extravagant, high-contrast, and reflective material textures.",
            "Versi Kaya": "Electric orange silk-satin blazer, open front design, wide notched lapels. Matching orange silk waistcoat, tonal button details. Bright royal purple tailored long trousers, high-gloss satin finish. Chocolate brown crocodile-skin belt, oversized gold 'T' metallic buckle. Oversized gold-framed aviator sunglasses, dark gradient lenses. Solid gold wristwatch, fully iced diamond dial. Holographic silver leather footwear, translucent chunky soles. Multi-layered gold chain necklace with a small solid gold 'TUNG' pendant. Luminous, hyper-reflective, and extravagant material textures.",
            "Versi Sultan": "Iridescent silver silk textile, reflective glass-bead embroidery. Metallic gold-threaded denim fabric, deep indigo base, straight-cut long trousers. Chocolate brown crocodile-skin texture belt, oversized gold 'T' metallic buckle. Solid white-gold timekeeper, baguette-cut sapphire bezel, fully iced dial. High-gloss holographic leather footwear, translucent chunky soles. Horizontal solid 24k gold pendant spelling 'TUNG', high-mirror polish finish, encrusted with micro-diamond accents, attached to a fine gold micro-link chain. Hyper-reflective, multifaceted, and luminous material textures.",
            "Versi Miskin": "faded yellowish white t-shirt. The corduroy trousers are brown, the bottom edge is frayed, and there are sewn-on patches. Weathered rubber flip flops.",
            "Anak SD": "White short-sleeve button-up shirt, red embroidered school logo on the chest pocket. Red short trousers, elastic waistband. Red and white striped tie. Low-cut black canvas sneakers, white rubber soles. High-contrast red and white fabric textures.",
            "Anak SMA": "Short-sleeved white button-up shirt, embroidered school logo on chest pocket. Gray trousers, Slim black synthetic belt, silver buckle. Gray tie. Low-cut black canvas sneakers, white rubber sole. High contrast gray and white fabric texture."
        }
    },
    
    "Balerina": {
        "fisik": "",
        "versi_pakaian": {
            "Keseharian": "Dark brown linen dress, straight cut, knee length. Textile with a simple matte finish. Plain black leather flat shoes, thin rubber soles. No accessories. The surface of the material is smooth and opaque.",
            "Daster": "Loose-fit cotton rayon daster, vibrant purple and blue batik floral patterns. Wide-cut arm openings. Red rubber flip-flops, thinned soles, worn-out surface texture.",
            "Versi Gaul": "Soft pink cotton t-shirt, bright floral pattern print. Dark brown cotton skirt, flared A-line cut, no ruffles. White platform leather sneakers, thick see-through sole, colorful lace details.",
            "Wanita Karir": "Tailored charcoal gray striped wool blazer, sharp padded shoulders. Striped slim-fit trousers with pressed pleats. Black silk sleeveless turtleneck inner lining. Gold layered necklace with geometric pendant. Shiny black pointed stiletto heels.",
            "Versi Miskin": "Oversized faded brown cotton dress, stretched neckline, visible coarse hand-stitched repairs. The texture of the fabric is piled and thinned. Worn rubber flip flops.",
            "Anak SD": "Short-sleeved white button-up shirt, red embroidered school logo on chest pocket. Red skirt, elastic waist. Red and white striped tie. Low-cut black canvas sneakers, white rubber sole. High contrast red and white fabric texture.",
            "Anak SMA": "Short-sleeved white button-up shirt, embroidered school logo on the chest pocket. gray skirt, slim black synthetic belt, silver buckle. Gray tie. Low-cut black canvas sneakers, white rubber sole. High contrast gray and white fabric texture."
        }
    },

    "Emak": {
        "fisik": "",
        "versi_pakaian": {
            "Keseharian": "Long negligee in loose rayon cotton fabric, bright brown and pink batik floral motif. Wide cut sleeve openings. Green rubber flip flops, thin soles, worn surface texture.",
            "Daster Kerudung": "Long negligee made from loose rayon cotton, bright blue and red floral batik motifs combined with 'Bergo' (instant jersey hijab with white foam edges). Green rubber flip flops, thin sole, worn surface texture.",
            "Versi Miskin": "Long negligee made from loose rayon cotton with floral batik motifs in faded pink and shabby green. Red rubber flip flops. Two small white medicine patches are attached symmetrically to the right and left sides of the forehead.",
            "Versi Sultan": "remium Silk Kaftan with elegant gold embroidery, carrying a luxury designer handbag, wearing a large diamond ring and gold jewelry, with oversized designer sunglasses. shiny brown sandals, gold lines that look sharp and shiny."
        }
    },

    "Bapak": {
        "fisik": "",
        "versi_pakaian": {
            "Keseharian": "Plain white t-shirt, loose ends not tucked in, covering the waist. Long checkered cotton sarong, red and calm colors, straight vertical curtains. Blue rubber flip flops.",
            "Versi Kades": "Formal khaki-colored PDH (Indonesian civil servant uniform) with shoulder epaulets. On the right chest, there is a clear black name tag with white text that reads: 'KADES KONOHA'. Wearing black leather shoes and a leather belt.",
            "Versi Pak RT": "Short-sleeved batik shirt tucked into black trousers. holding a clip-on folder.",
            "Versi Batik": "Exclusive silk batik shirt with expensive intricate motifs. Wearing a large 'batu akik' gemstone ring, a gold watch, luxury sunglasses, and polished shiny leather shoes."
        }
    },

    "Rumi": {
        "fisik": "",
        "versi_pakaian": {
            "Keseharian": "Modern Cotton Batik Daster (house dress) with minimalist motifs. Her signature purple braided ponytail was tied a little lower. Wearing pink rubber flip-flops.",
            "Casual": "An oversized cream-colored knit sweater tucked into light blue high-waisted jeans. Wearing clean white minimalist sneakers.",
            "Versi Miskin": "A worn pink t-shirt and worn gray long jeans. wearing black flip flops.",
            "Versi Gaul": "Yellow cropped leather bomber jacket with floral embroidery, white crop top underneath, denim hot pants with a fuchsia pink belt, and high black boots.",
            "Wanita Karir": "A sharply designed white blazer over a soft light brown silk blouse, paired with charcoal gray trousers and black pointy heels.",
            "Versi Kaya": "Deep purple silk-satin midi dress, tailored wrap-around design, clean-cut V-neckline. A delicate string of brilliant-cut diamonds, set in white gold, resting on the fabric's neckline. Smooth high-luster textile. Black pointed-toe leather pumps, slim high heels, polished finish. Small structured gold metallic handbag, minimalist geometric shape.",
            "Anak SD": "Short-sleeved white button-up shirt, red embroidered school logo on chest pocket. Red skirt, elastic waist. Red and white striped tie. Low-cut black canvas sneakers, white rubber sole. High contrast red and white fabric texture.",
            "Anak SMA": "Short-sleeved white button-up shirt, embroidered school logo on the chest pocket. gray skirt, slim black synthetic belt, silver buckle. Gray tie. Low-cut black canvas sneakers, white rubber sole. High contrast gray and white fabric texture."
        }
    },

    "Dindin": {
        "fisik": "",
        "versi_pakaian": {
            "Keseharian ": "Bright yellow cotton T-shirt, featuring a large colorful cartoon dinosaur print on the center chest. Short navy blue denim overalls, small metallic buckle fastenings. Wears colorful sneakers with glowing LED lights.",
            "Versi Miskin": "The faded gray cotton T-shirt is oversized, the collar is stretchy, and the cartoon print is cracked and peeling. Worn brown corduroy shorts. black flip flops.",
            "Versi Gaul": "Mini cat-ear hoodie, denim jogger pants, glowing LED roller shoes, and bright neon plastic sunglasses.",
            "Versi Sultan": "Mini white silk tuxedo, tiny diamond-encrusted toy watch, holding a gold-plated smartphone, expensive designer sneakers.",
            "Anak SD": "White short-sleeve button-up shirt, red embroidered school logo on the chest pocket. Red short trousers, elastic waistband. Red and white striped tie. Low-cut black canvas sneakers, white rubber soles. High-contrast red and white fabric textures.",
            "Anak SMA": "Short-sleeved white button-up shirt, embroidered school logo on chest pocket. Gray trousers, Slim black synthetic belt, silver buckle. Gray tie. Low-cut black canvas sneakers, white rubber sole. High contrast gray and white fabric texture."
        }
    },

    "Tingting": {
        "fisik": "",
        "versi_pakaian": {
            "Keseharian ": "Blue polo shirt, dark blue sweatpants, and brown velcro strap sneakers.",
            "Casual": "A cool mini bomber jacket in olive green over a grey t-shirt, paired with khaki cargo jogger pants and small tactical boots.",
            "Versi Miskin": "Tunic made from a tattered flour sack with visible branding (karung terigu), scrap cloth shorts, carrying an old inner tube (ban dalam) as a toy.",
            "Versi Gaul": "Flannel shirt tied around the waist, multi-pocket cargo pants, backwards snapback hat, and large headphones around neck.",
            "Versi Sultan": "A crimson royal velvet robe, a small gold crown perched on his head. premium leather boots, holding a solid gold toy car.",
            "Anak SD": "White short-sleeve button-up shirt, red embroidered school logo on the chest pocket. Red short trousers, elastic waistband. Red and white striped tie. Low-cut black canvas sneakers, white rubber soles. High-contrast red and white fabric textures.",
            "Anak SMA": "Short-sleeved white button-up shirt, embroidered school logo on chest pocket. Gray trousers, Slim black synthetic belt, silver buckle. Gray tie. Low-cut black canvas sneakers, white rubber sole. High contrast gray and white fabric texture."
        }
    }
}

st.set_page_config(page_title="PINTAR MEDIA | Studio", layout="wide")

# ==============================================================================
# FUNGSI ABSENSI OTOMATIS (MESIN ABSEN)
# ==============================================================================
def log_absen_otomatis(nama_user):
    if nama_user.lower() in ["dian", "tamu"]: return
    
    url_gsheet = "https://docs.google.com/spreadsheets/d/16xcIqG2z78yH_OxY5RC2oQmLwcJpTs637kPY-hewTTY/edit?usp=sharing"
    tz_wib = pytz.timezone('Asia/Jakarta')
    waktu_skrg = datetime.now(tz_wib)
    
    jam = waktu_skrg.hour
    tgl_skrg = waktu_skrg.strftime("%Y-%m-%d")
    jam_skrg = waktu_skrg.strftime("%H:%M")

    if 8 <= jam < 10: 
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(st.secrets["service_account"], scopes=scope)
            client = gspread.authorize(creds)
            sheet_absen = client.open_by_url(url_gsheet).worksheet("Absensi")
            
            # AMBIL DATA & BERSIHKAN
            data_mentah = sheet_absen.get_all_records()
            df_absen = bersihkan_data(pd.DataFrame(data_mentah))
            
            nama_up = nama_user.upper()
            
            # CEK APAKAH SUDAH ADA (Tanpa bingung Huruf Besar/Kecil)
            sudah_absen = False
            if not df_absen.empty:
                sudah_absen = any((df_absen['TANGGAL'].astype(str) == tgl_skrg) & (df_absen['NAMA'] == nama_up))
            
            if not sudah_absen:
                sheet_absen.append_row([nama_up, tgl_skrg, jam_skrg, "HADIR"])
                st.toast(f"⏰ Absen Berhasil (Jam {jam_skrg})", icon="✅")
        except:
            pass

# ==============================================================================
# BAGIAN 2: SISTEM KEAMANAN & INISIALISASI DATA (SESSION STATE)
# ==============================================================================
def inisialisasi_keamanan():
    if 'sudah_login' not in st.session_state:
        st.session_state.sudah_login = False
    
# INISIALISASI MASTER DATA (VERSI CLEAN)
    if 'data_produksi' not in st.session_state:
        st.session_state.data_produksi = {
            "jumlah_karakter": 2,
            "karakter": [ {"nama": "", "wear": "", "fisik": ""} for _ in range(4) ],
            "jumlah_adegan": 5,
            "adegan": {i: {
                "aksi": "", 
                "style": OPTS_STYLE[0], 
                "light": OPTS_LIGHT[0], 
                "arah": OPTS_ARAH[0], 
                "shot": OPTS_SHOT[0], 
                "cam": OPTS_CAM[0], 
                "loc": "", 
                "dialogs": [""]*4
            } for i in range(1, 51)}, 
            "form_version": 0
        }

    # Perbaikan: Jangan update session login otomatis dari params di sini jika bikin bentrok
    params = st.query_params
    if "auth" in params and params["auth"] == "true":
        if not st.session_state.sudah_login:
            st.session_state.sudah_login = True
            st.session_state.user_aktif = params.get("user", "User")
            st.session_state.waktu_login = datetime.now()

def proses_login(user, pwd):
    if user in DAFTAR_USER and DAFTAR_USER[user] == pwd:
        st.session_state.sudah_login = True
        st.session_state.user_aktif = user
        st.session_state.waktu_login = datetime.now()
        
        # AKTIVASI ABSEN
        log_absen_otomatis(user)
        
        st.query_params.update({"auth": "true", "user": user})
        st.rerun()
    else:
        st.error("Username atau Password salah.")

def tampilkan_halaman_login():
    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([2, 1, 2]) 
    with col_m:
        try:
            st.image("PINTAR.png", use_container_width=True)
        except:
            st.markdown("<h2 style='text-align: center;'>PINTAR MEDIA</h2>", unsafe_allow_html=True)
        
        with st.form("login_station"):
            u = st.text_input("Username", placeholder="Username...", key="login_user").lower()
            p = st.text_input("Password", type="password", placeholder="Password...", key="login_pass")
            submit = st.form_submit_button("MASUK KE SISTEM 🚀", use_container_width=True)
            if submit: 
                proses_login(u, p)
        st.markdown("<p style='text-align: center; color: #484f58; font-size: 11px; margin-top: 15px;'>Secure Access - PINTAR MEDIA</p>", unsafe_allow_html=True)

def cek_autentikasi():
    if st.session_state.sudah_login:
        if 'waktu_login' in st.session_state:
            durasi = datetime.now() - st.session_state.waktu_login
            if durasi > timedelta(hours=10):
                proses_logout()
                return False
        return True
    return False

def proses_logout():
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

# FUNGSI BACKUP (Fokus GSheet lewat Secrets)
def simpan_ke_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Pakai st.secrets (tidak pakai file kunci.json)
        creds = Credentials.from_service_account_info(st.secrets["service_account"], scopes=scope)
        client = gspread.authorize(creds)
        
        url_gsheet = "https://docs.google.com/spreadsheets/d/16xcIqG2z78yH_OxY5RC2oQmLwcJpTs637kPY-hewTTY/edit?usp=sharing"
        sheet = client.open_by_url(url_gsheet).sheet1
        
        # --- PERBAIKAN: SET ZONA WAKTU KE WIB (GMT+7) ---
        tz_wib = pytz.timezone('Asia/Jakarta')
        waktu = datetime.now(tz_wib).strftime("%d/%m/%Y %H:%M:%S")
        
        # PERBAIKAN: Paksa nama user jadi huruf BESAR
        user = st.session_state.get("user_aktif", "STAFF").upper() 
        data_json = json.dumps(st.session_state.data_produksi)
        
        # Urutan kolom: USERNAME, WAKTU, DATA_NASKAH
        sheet.append_row([user, waktu, data_json])
        st.toast("🚀 Berhasil disimpan ke Cloud!", icon="☁️")
    except Exception as e:
        st.error(f"Gagal Simpan Cloud: {e}")

def muat_dari_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["service_account"], scopes=scope)
        client = gspread.authorize(creds)
        
        url_gsheet = "https://docs.google.com/spreadsheets/d/16xcIqG2z78yH_OxY5RC2oQmLwcJpTs637kPY-hewTTY/edit?usp=sharing"
        sheet = client.open_by_url(url_gsheet).sheet1
        
        # 1. Ambil data dan bersihkan lewat helper
        semua_data = sheet.get_all_records()
        df_temp = pd.DataFrame(semua_data)
        df_temp = bersihkan_data(df_temp) 
        
        # 2. Ambil username aktif dan paksa ke UPPERCASE
        user_up = st.session_state.get("user_aktif", "").upper()
        
        # 3. Cari baris di df_temp (bukan semua_data) pada kolom USERNAME
        # Karena bersihkan_data sudah mengubah header menjadi UPPERCASE
        user_rows = df_temp[df_temp['USERNAME'] == user_up].to_dict('records')
        
        if user_rows:
            # Ambil naskah dari baris paling bawah yang ada isinya
            naskah_mentah = None
            for row in reversed(user_rows):
                if row.get('DATA_NASKAH'):
                    naskah_mentah = row.get('DATA_NASKAH')
                    break
            
            if naskah_mentah:
                data_termuat = json.loads(naskah_mentah)
            
            # --- PROSES PERBAIKAN STRUKTUR (VERSI KLIMIS) ---
            if "adegan" in data_termuat:
                adegan_baru = {}
                for k, v in data_termuat["adegan"].items():
                    # Hapus sampah data lama agar tidak memenuhi memori
                    v.pop("ekspresi", None)
                    v.pop("cuaca", None)
                    v.pop("vibe", None)
                    v.pop("ratio", None)
                    
                    # Paksa kunci kembali jadi angka agar loop Streamlit tidak error
                    adegan_baru[int(k)] = v 
                data_termuat["adegan"] = adegan_baru
            
            # Masukkan ke laci utama
            st.session_state.data_produksi = data_termuat
            
            # Update versi form agar layar dipaksa gambar ulang
            if 'form_version' not in st.session_state:
                st.session_state.form_version = 0
            st.session_state.form_version += 1
            
            st.success(f"🔄 Naskah {user_up} Berhasil Dipulihkan!")
            st.rerun()
        else:
            st.warning("⚠️ Data tidak ditemukan di Cloud.")
    except Exception as e:
        st.error(f"Gagal memuat: {e}")
        
# ==============================================================================
# BAGIAN 3: PENGATURAN TAMPILAN (CSS) - TOTAL BORDERLESS & STATIC
# ==============================================================================
def pasang_css_kustom():
    st.markdown("""
        <style>
        /* 1. DASAR APLIKASI & SCROLLBAR */
        .stApp { background-color: #0b0e14; color: #e0e0e0; }
        [data-testid="stSidebar"] { 
            background-color: #1a1c24 !important; 
            border-right: 1px solid rgba(29, 151, 108, 0.1) !important; 
        }
        
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #0e1117; }
        ::-webkit-scrollbar-thumb { background: #31333f; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #1d976c; }

        /* 2. FIXED HEADER (STATION & JAM) */
        [data-testid="stMainViewContainer"] section.main div.block-container > div:nth-child(1) {
            position: fixed; top: 0; left: 310px; right: 0; z-index: 99999;
            background-color: #0e1117; padding: 10px 2rem; border-bottom: 2px solid #31333f;
        }
        @media (max-width: 768px) {
            [data-testid="stMainViewContainer"] section.main div.block-container > div:nth-child(1) { left: 0; }
        }

        /* 3. HANYA TOMBOL GENERATE YANG HIJAU (PRIMARY) */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(to right, #1d976c, #11998e) !important;
            color: white !important; 
            border: none !important; 
            border-radius: 8px !important;
            padding: 10px 20px !important;
            margin-top: 15px !important;
            margin-bottom: 10px !important;
            font-weight: bold !important;
            font-size: 14px !important;
            width: 100%; 
            box-shadow: 0 4px 12px rgba(29, 151, 108, 0.2) !important;
        }

        /* 4. MODE TANPA GARIS (BORDERLESS) PADA SEMUA INPUT */
        .stTextArea textarea, 
        .stTextInput input, 
        div[data-testid="stNumberInput"], 
        div[data-baseweb="input"],
        div[data-baseweb="textarea"],
        [data-baseweb="base-input"] {
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
            background-color: #0d1117 !important;
            border-radius: 10px !important;
            color: #ffffff !important;
        }
        
        .stTextArea textarea:focus, 
        .stTextInput input:focus, 
        div[data-testid="stNumberInput"]:focus-within,
        div[data-baseweb="input"]:focus-within,
        [data-baseweb="base-input"]:focus-within {
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }

        /* 5. STAFF HEADER & LABEL */
        .staff-header-premium {
            background: rgba(29, 151, 108, 0.2) !important;
            border: 2px solid #1d976c !important;
            border-radius: 10px !important;
            padding: 15px 20px !important; margin-bottom: 25px !important;
            display: flex !important; align-items: center !important; gap: 12px !important;
        }
        .staff-header-premium b { color: #1d976c !important; font-size: 1.15em !important; }
        
        .small-label {
            color: #1d976c !important; font-size: 10px !important;
            font-weight: 800 !important; letter-spacing: 1px; text-transform: uppercase;
            margin-bottom: 5px !important; display: block;
        }

        /* 6. KOMPONEN LAIN - KETEBALAN STANDAR WARNA DEFAULT */
        .stExpander {
            /* 1px adalah ukuran standar yang paling pas, warna abu-abu gelap */
            border: 1px solid #30363d !important; 
            border-radius: 12px !important; 
            background-color: #161922 !important;
            margin-bottom: 10px !important;
        }
        
        .status-footer { font-size: 11px !important; color: #8b949e !important; font-family: monospace; }
        
        /* Garis pemisah (hr) tipis warna default */
        hr { 
            border: none !important;
            border-top: 1px solid #30363d !important; 
            opacity: 0.3 !important; /* Dibuat samar agar dashboard terlihat bersih */
            margin: 15px 0 !important;
        }

        /* 7. PENGATURAN INPUT HALAMAN LOGIN */
        .stForm div[data-baseweb="input"] {
            background-color: #1a1f26 !important;
            border: 1px solid #30363d !important;
        }
        .stForm input {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        .stForm label p {
            color: #e0e0e0 !important;
            font-weight: 600 !important;
            font-size: 14px !important;
        }
        /* 8. COPY TO CLIPBOARD - BUTTON STYLING */
        /* Kotak kodenya kita buat lebih tegas */
        .stCodeBlock {
            border: 1px solid #30363d !important;
            border-radius: 10px !important;
            background-color: #0d1117 !important;
            padding: 10px !important;
        }
        
        /* Tombol copy bawaan Streamlit dibuat besar & berwarna hijau */
        button[title="Copy to clipboard"] {
            background-color: #238636 !important;
            color: white !important;
            transform: scale(1.6); /* Memperbesar ukuran ikon */
            margin-right: 15px !important;
            margin-top: 15px !important;
            border-radius: 6px !important;
            border: none !important;
            transition: all 0.2s ease-in-out !important;
        }
        
        /* Efek saat kursor menempel (Hover) */
        button[title="Copy to clipboard"]:hover {
            background-color: #2ea043 !important;
            transform: scale(1.8) !important;
            cursor: pointer !important;
        }

        /* Menghilangkan background bawaan agar warna hijau kita solid */
        button[title="Copy to clipboard"]:active {
            background-color: #3fb950 !important;
        }

        /* 9. PROTEKSI LAYAR (PC ONLY) - DI POSISI PALING BAWAH */
        @media (max-width: 1024px) {
            [data-testid="stAppViewContainer"], [data-testid="stSidebar"], .main { display: none !important; }
            body::before {
                content: "⚠️ Akses Diblokir!";
                display: flex; justify-content: center; align-items: center;
                height: 100vh; width: 100vw; background: #0e1117; color: white;
                position: fixed; top: 0; left: 0; z-index: 9999; text-align: center; padding: 20px;
                font-family: sans-serif; font-weight: bold;
            }
        }
        </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# BAGIAN 4: NAVIGASI SIDEBAR (VERSI CLOUD ONLY)
# ==============================================================================
def tampilkan_navigasi_sidebar():
    with st.sidebar:
        # 1. JUDUL DENGAN IKON (Sesuai Gambar)
        st.markdown("""
            <div style='display: flex; align-items: center; margin-bottom: 10px; margin-top: 10px;'>
                <span style='font-size: 20px; margin-right: 10px;'>🖥️</span>
                <span style='font-size: 14px; color: white; font-weight: bold; letter-spacing: 1px;'>
                    MAIN COMMAND
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        # 2. MENU RADIO (Daftar Pilihan)
        pilihan = st.radio(
            "COMMAND_MENU",
            [
                "🚀 RUANG PRODUKSI", 
                "🧠 PINTAR AI LAB", 
                "💡 GUDANG IDE", 
                "📋 TUGAS KERJA", 
                "⚡ KENDALI TIM"
            ],
            label_visibility="collapsed"
        )
        
        # 3. GARIS PEMISAH & SPASI KE BAWAH
        st.markdown("<hr style='margin: 20px 0; border-color: #30363d;'>", unsafe_allow_html=True)
        
        # 1. KOTAK DURASI FILM
        st.markdown("<p class='small-label'>🎬 DURASI FILM (ADEGAN)</p>", unsafe_allow_html=True)
        st.session_state.data_produksi["jumlah_adegan"] = st.number_input(
            "Jumlah Adegan", 1, 50, 
            value=st.session_state.data_produksi["jumlah_adegan"],
            label_visibility="collapsed"
        )
        
        # 2. SISTEM DATABASE CLOUD (GSHEET)
        st.markdown("<p class='small-label'>☁️ CLOUD DATABASE (GSHEET)</p>", unsafe_allow_html=True)
        
        # Tombol Backup & Restore Berdampingan dengan tampilan default
        col1, col2 = st.columns(2)
        with col1:
            # type="primary" dihapus agar warnanya default (abu-abu)
            if st.button("📤 BACKUP", use_container_width=True): 
                simpan_ke_gsheet()
        with col2:
            if st.button("🔄 RESTORE", use_container_width=True):
                muat_dari_gsheet()
                
        st.markdown('<div style="margin-top: 50px;"></div>', unsafe_allow_html=True)   
        
        if st.button("⚡ KELUAR SISTEM", use_container_width=True):
            proses_logout()
        
        user = st.session_state.get("user_aktif", "USER").upper()
        st.markdown(f'''
            <div style="border-top: 1px solid #30363d; padding-top: 15px; margin-top: 10px;">
                <p class="status-footer">
                    🛰️ STATION: {user}_SESSION<br>
                    🟢 STATUS: AKTIF
                </p>
            </div>
        ''', unsafe_allow_html=True)
        
    return pilihan

# ==============================================================================
# BAGIAN 5: PINTAR AI LAB - PRO EDITION (SYNCHRONIZED MANTRA)
# ==============================================================================

def tampilkan_ai_lab():
    st.title("🧠 PINTAR AI LAB")
    st.info("🚀 **Gaskeun!** Ide cerita di mode **Manual**, atau langsung jadi naskah di mode **Otomatis**!")
    
    # --- 1. KONFIGURASI & SESSION STATE ---
    if 'lab_hasil_otomatis' not in st.session_state: st.session_state.lab_hasil_otomatis = ""
    if 'jumlah_karakter' not in st.session_state: st.session_state.jumlah_karakter = 2
    if 'memori_n' not in st.session_state: st.session_state.memori_n = {}
    if 'memori_s' not in st.session_state: st.session_state.memori_s = {}
    
    # 4 NICHE UTAMA
    opsi_pola = [
        "Revenge (Direndahkan -> Balas Dendam)",
        "Empathy (Iba -> Pesan Moral)",
        "Absurd Race (Lomba Konyol -> Interaktif CTA)",
        "Knowledge (Fakta Harian -> Edukasi)"
    ]
    opsi_visual = ["Sangat Nyata", "Gaya Cyberpunk", "3D Pixar Style", "Anime Style"]

    try:
        api_key_groq = st.secrets["GROQ_API_KEY"]
    except:
        api_key_groq = None

    # --- 2. AREA PENGATURAN KARAKTER ---
    st.subheader("👤 Pengaturan Karakter")
    c_add, c_rem, c_spacer = st.columns([0.25, 0.25, 0.5])
    with c_add:
        if st.button("➕ Tambah Karakter", use_container_width=True) and st.session_state.jumlah_karakter < 4:
            st.session_state.jumlah_karakter += 1
            st.rerun()
    with c_rem:
        if st.button("➖ Kurang Karakter", use_container_width=True) and st.session_state.jumlah_karakter > 1:
            st.session_state.jumlah_karakter -= 1
            st.rerun()

    list_karakter = []
    with st.expander("👥 DETAIL KARAKTER", expanded=True):
        char_cols = st.columns(2)
        for i in range(st.session_state.jumlah_karakter):
            if i not in st.session_state.memori_n: st.session_state.memori_n[i] = ""
            if i not in st.session_state.memori_s: st.session_state.memori_s[i] = ""
            with char_cols[i % 2]:
                with st.container(border=True):
                    label_k = "Karakter Utama" if i == 0 else f"Karakter {i+1}"
                    st.markdown(f"**{label_k}**")
                    st.session_state.memori_n[i] = st.text_input(f"N{i}", value=st.session_state.memori_n[i], key=f"inp_n_{i}", placeholder="Nama...", label_visibility="collapsed")
                    st.session_state.memori_s[i] = st.text_input(f"S{i}", value=st.session_state.memori_s[i], key=f"inp_s_{i}", placeholder="Detail sifat/fisik...", label_visibility="collapsed")
                    n_f = st.session_state.memori_n[i] if st.session_state.memori_n[i] else label_k
                    list_karakter.append(f"{i+1}. {n_f.upper()}: {st.session_state.memori_s[i]}")

    st.write("---")

    # --- 3. TAB MENU (MANUAL & OTOMATIS) ---
    tab_manual, tab_otomatis = st.tabs(["🛠️ Mode Manual", "⚡ Mode Otomatis"])

    # MODE MANUAL
    with tab_manual:
        with st.expander("📝 KONFIGURASI MANUAL", expanded=True):
            col_m1, col_m2 = st.columns([2, 1])
            with col_m1:
                st.markdown("**📝 Topik Utama**")
                topik_m = st.text_area("T", placeholder="Ketik ide ceritanya di sini...", height=245, key="m_topik", label_visibility="collapsed")
            with col_m2:
                st.markdown("**🎭 Pola & Style**")
                pola_m = st.selectbox("Pola", opsi_pola, key="m_pola")
                visual_m = st.selectbox("Visual", opsi_visual, key="m_visual")
                adegan_m = st.number_input("Jumlah Adegan", 3, 15, 12, key="m_adegan")

            if st.button("✨ GENERATE NASKAH CERITA", use_container_width=True, type="primary"):
                if topik_m:
                    str_k = "\n".join(list_karakter)
                    mantra_sakti = f"""Kamu adalah Scriptwriter Pro Pintar Media. 
Buatkan naskah YouTube Shorts VIRAL dalam format TABEL MARKDOWN (Siap Copy-Paste ke GSheet).

--- DAFTAR KARAKTER & DETAIL FISIK ---
{str_k}

--- KONSEP UTAMA ---
Topik: {topik_m}
Pola: {pola_m}
Total Adegan: {adegan_m} (WAJIB {adegan_m} ADEGAN)

--- LOGIKA ALUR PER POLA (DIBAGI DALAM {adegan_m} ADEGAN) ---
{f''' - ALUR REVENGE: Adegan 1-5 (Protagonis dihina/hartanya dirusak Antagonis), Adegan 6 (CTA Like/Subs via Dialog), Adegan 7-10 (Balas Dendam Savage/Anomali secara realistis), Adegan 11-12 (Ending Kepuasan Penonton).''' if pola_m == opsi_pola[0] else ''}
{f''' - ALUR EMPATHY: Adegan 1-5 (Hook masalah nyesek/iba), Adegan 6 (CTA Like/Subs via Dialog), Adegan 7-10 (Perjuangan emosional karakter), Adegan 11-12 (Ending Haru).''' if pola_m == opsi_pola[1] else ''}
{f''' - ALUR ABSURD RACE: Adegan 1-4 (Lomba konyol dimulai), Adegan 5-8 (Lomba chaos/lucu), Adegan 9-10 (Momen kritis), Adegan 11-12 (Hasil lomba & WAJIB CTA penonton tentukan pemenang via Like/Subs).''' if pola_m == opsi_pola[2] else ''}
{f''' - ALUR KNOWLEDGE: Adegan 1-3 (Fakta unik awal), Adegan 4-6 (Dampak jangka pendek), Adegan 7-10 (Dampak jangka panjang/1 tahun kemudian), Adegan 11-12 (Edukasi penutup).''' if pola_m == opsi_pola[3] else ''}

--- STANDAR PRODUKSI (WAJIB PATUH) ---
1. LOKASI: Wajib DESKRIPTIF & DETAIL (Minimal 10-15 kata, gambarkan suasana lingkungan, benda sekitar, dan cuaca).
2. NO MORAL: Jangan ada pesan moral atau nasihat bijak di akhir cerita.
3. NO TEXT: Tanpa teks di layar, semua pesan disampaikan lewat visual dan dialog.
4. BAHASA: Sehari hari (mudah dimengerti oleh penonton).

--- FORMAT TABEL (KOLOM GSHEET) ---
ID_IDE | JUDUL | STATUS | NASKAH_VISUAL | DIALOG_ACTOR_1 | DIALOG_ACTOR_2 | STYLE | UKURAN_GAMBAR | LIGHTING | ARAH_KAMERA | GERAKAN | LOKASI

--- DROPDOWN VALID ---
- STYLE: [{visual_m}]
- UKURAN_GAMBAR: [Seluruh Badan / Setengah Badan / Sangat Dekat / Wajah & Bahu]
- LIGHTING: [Siang Alami / Malam Indigo / Senja Cerah / Neon Cyberpunk / Fajar]
- ARAH_KAMERA: [Sejajar Mata / Dari Atas / Dari Bawah / Dari Samping / Dari Belakang]
- GERAKAN: [Diam (Tetap Napas) / Maju Perlahan / Ikuti Karakter / Goyang (Handheld)]

Balas HANYA tabel Markdown.
"""
                    st.divider()
                    st.success("✨ **Mantra ide cerita Siap!**")
                    st.code(mantra_sakti, language="text")

    # MODE OTOMATIS
    with tab_otomatis:
        with st.expander("⚡ KONFIGURASI OTOMATIS", expanded=True):
            col_o1, col_o2 = st.columns([2, 1])
            with col_o1:
                st.markdown("**📝 Topik Utama**")
                topik_o = st.text_area("O", placeholder="Ketik ide ceritanya di sini...", height=245, key="o_topik", label_visibility="collapsed")
            with col_o2:
                st.markdown("**⚙️ Konfigurasi Otomatis**")
                pola_o = st.selectbox("Pola Cerita", opsi_pola, key="o_pola")
                adegan_o = st.number_input("Jumlah Adegan", 3, 15, 12, key="o_adegan_api")

            if st.button("🔥 GENERATE NASKAH CERITA", use_container_width=True, type="primary"):
                if api_key_groq and topik_o:
                    with st.spinner("lagi ngetik naskah..."):
                        try:
                            import requests
                            headers = {"Authorization": f"Bearer {api_key_groq}", "Content-Type": "application/json"}
                            str_k = "\n".join(list_karakter)
                            
                            prompt_otomatis = f"""Kamu adalah Creative Director & Scriptwriter Pro Pintar Media. 
Buatkan naskah YouTube Shorts VIRAL dalam format TABEL MARKDOWN.

--- DAFTAR KARAKTER & DETAIL FISIK ---
{str_k}

KONSEP:
Topik: {topik_o}
Pola: {pola_o}
Total Adegan: {adegan_o} (WAJIB {adegan_o} ADEGAN)

--- ATURAN MAIN (STRICT PRODUKSI) ---
1. NASKAH_VISUAL: WAJIB DESKRIPTIF & PANJANG (Minimal 30-40 kata per adegan) Jelaskan aksi karakter, ekspresi wajah secara detail, dan interaksi dengan benda di sekitarnya.
2. LOKASI: Harus Detail (Minimal 15 kata) Gambarkan suasana lingkungan, dan tumpukan benda/detail latar belakang agar terlihat nyata.
3. DIALOG: Buat dialog yang natural, emosional. Gunakan bahasa sehari-hari yang luwes.
4. NO MORAL & NO TEXT: Tanpa pesan moral dan tanpa teks di layar.
5. STRUKTUR: Bagi {adegan_o} adegan menjadi fase Awal (Konflik), Tengah (Puncak/CTA Like & Subs), dan Akhir (Pembalasan Savage/Anomali).

--- FORMAT TABEL (WAJIB 5 KOLOM) ---
JUDUL | NASKAH_VISUAL | DIALOG_ACTOR_1 | DIALOG_ACTOR_2 | LOKASI

Balas HANYA tabel Markdown tanpa penjelasan apa pun.
"""
                            payload = {
                                "model": "llama-3.3-70b-versatile", 
                                "messages": [{"role": "user", "content": prompt_otomatis}],
                                "temperature": 0.7
                            }
                            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                            st.session_state.lab_hasil_otomatis = res.json()['choices'][0]['message']['content']
                            st.toast("Naskah Berhasil Dibuat!", icon="✅")
                        except Exception as e:
                            st.error(f"Error: {e}")

        if st.session_state.lab_hasil_otomatis:
            with st.expander("🎬 NASKAH JADI (OTOMATIS)", expanded=True):
                st.markdown(st.session_state.lab_hasil_otomatis)
                st.divider()
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button("🚀 KIRIM KE RUANG PRODUKSI", use_container_width=True):
                        if 'data_produksi' not in st.session_state: st.session_state.data_produksi = {}
                        st.session_state.naskah_siap_produksi = st.session_state.lab_hasil_otomatis
                        st.toast("Naskah sukses terkirim!", icon="🚀")
                with btn_col2:
                    if st.button("🗑️ BERSIHKAN NASKAH", use_container_width=True):
                        st.session_state.lab_hasil_otomatis = ""
                        st.rerun()
                with btn_col3:
                    st.download_button("📥 DOWNLOAD (.txt)", st.session_state.lab_hasil_otomatis, file_name="naskah.txt", use_container_width=True)
                
def tampilkan_gudang_ide():
    # --- 1. CSS OVERLAY (TETEP ADA UNTUK PROSES) ---
    st.markdown("""
        <style>
        .loading-overlay {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background-color: rgba(0, 0, 0, 0.85);
            z-index: 999999;
            display: flex; flex-direction: column;
            justify-content: center; align-items: center;
            color: white; font-family: 'Segoe UI', sans-serif;
            text-align: center;
        }
        .spinner {
            border: 6px solid #333;
            border-top: 6px solid #1d976c;
            border-radius: 50%;
            width: 70px; height: 70px;
            animation: spin 1s linear infinite;
            margin-bottom: 25px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    """, unsafe_allow_html=True)

    st.title("💡 GUDANG IDE KONTEN")
    st.info("⚡ Pilih ide konten di bawah. Sekali klik, Otomatis masuk ke Ruang Produksi!")
    
    if "sedang_proses_id" not in st.session_state:
        st.session_state.sedang_proses_id = None
    if "status_sukses" not in st.session_state:
        st.session_state.status_sukses = False

    # --- 2. LOGIKA TAMPILAN OVERLAY ---
    if st.session_state.sedang_proses_id:
        if st.session_state.status_sukses:
            st.markdown(f"""
                <div class="loading-overlay">
                    <h1 style="font-size: 60px; margin-bottom: 10px;">✅</h1>
                    <h2 style='color: white; letter-spacing: 2px;'>BERHASIL TERPASANG</h2>
                    <p style='color: #1d976c; font-weight: bold;'>CEK RUANG PRODUKSI SEKARANG</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="loading-overlay">
                    <div class="spinner"></div>
                    <h2 style='color: white; letter-spacing: 2px;'>MENGAMBIL DATA...</h2>
                    <p style='color: #8b949e;'>Sinkronisasi ke Cloud Database PINTAR</p>
                </div>
            """, unsafe_allow_html=True)
            
    # --- 3. DATA & GRID RENDER ---
    url_gsheet = "https://docs.google.com/spreadsheets/d/16xcIqG2z78yH_OxY5RC2oQmLwcJpTs637kPY-hewTTY/edit?usp=sharing"
    user_sekarang = st.session_state.get("user_aktif", "tamu").lower()
    tz_wib = pytz.timezone('Asia/Jakarta')

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_url(url_gsheet)
        sheet_gudang = sh.worksheet("Gudang_Ide")
        sheet_tugas = sh.worksheet("Tugas")
        
        data_gudang = sheet_gudang.get_all_records()
        df_gudang = pd.DataFrame(data_gudang)
        df_gudang = bersihkan_data(df_gudang)
        
        df_tersedia = df_gudang[df_gudang['STATUS'] == 'TERSEDIA'].copy()
        list_judul_unik = df_tersedia['JUDUL'].unique()[:12]

        if len(list_judul_unik) == 0:
            st.warning("📭 Belum ada ide baru di gudang.")
        else:
            is_loading = st.session_state.sedang_proses_id is not None
            for i in range(0, len(list_judul_unik), 3):
                cols = st.columns(3)
                batch_judul = list_judul_unik[i:i+3]
                for j, judul in enumerate(batch_judul):
                    with cols[j]:
                        row_info = df_tersedia[df_tersedia['JUDUL'] == judul].iloc[0]
                        id_ini = str(row_info['ID_IDE'])
                        
                        with st.container(border=True):
                            # Aksen Hijau PINTAR (Garis Tipis Tetap Ada di Atas)
                            st.markdown(f'<div style="height: 3px; background-color: #1d976c; border-radius: 10px; margin-bottom: 10px;"></div>', unsafe_allow_html=True)
                            
                            # ID Polos (Warna Abu-abu Netral)
                            st.markdown(f"<p style='color: #888; font-size: 15px; margin-bottom: -10px;'>ID: {id_ini}</p>", unsafe_allow_html=True)
                            
                            # Judul Konten
                            st.markdown(f"### {judul}")
                            
                            st.write("") 
                            if st.button(f"🚀 AMBIL IDE", key=f"btn_{id_ini}", use_container_width=True, disabled=is_loading):
                                st.session_state.sedang_proses_id = id_ini
                                st.session_state.status_sukses = False
                                st.rerun()

            # --- 4. PROSES DATA ---
            if st.session_state.sedang_proses_id and not st.session_state.status_sukses:
                target_id = st.session_state.sedang_proses_id
                row_proses = df_tersedia[df_tersedia['ID_IDE'].astype(str) == target_id].iloc[0]
                judul_proses = row_proses['JUDUL']
                
                cells = sheet_gudang.findall(target_id)
                for cell in cells:
                    sheet_gudang.update_cell(cell.row, 3, f"DIAMBIL ({user_sekarang.upper()})")
                
                adegan_rows = df_gudang[df_gudang['ID_IDE'].astype(str) == target_id]
                st.session_state.data_produksi["jumlah_adegan"] = len(adegan_rows)
                
                for idx, (_, a_row) in enumerate(adegan_rows.iterrows(), 1):
                    st.session_state.data_produksi["adegan"][idx] = {
                        "aksi": a_row['NASKAH_VISUAL'], "dialogs": [a_row['DIALOG_ACTOR_1'], a_row['DIALOG_ACTOR_2'], "", ""],
                        "style": a_row['STYLE'], "shot": a_row['UKURAN_GAMBAR'], "light": a_row['LIGHTING'], 
                        "arah": a_row['ARAH_KAMERA'], "cam": a_row['GERAKAN'], "loc": a_row['LOKASI']
                    }
                
                t_id = f"T{datetime.now(tz_wib).strftime('%m%d%H%M%S')}"
                sheet_tugas.append_row([t_id, user_sekarang.upper(), datetime.now(tz_wib).strftime("%Y-%m-%d"), f"TUGAS: {judul_proses}", "PROSES", "-", "", ""])

                st.session_state.naskah_siap_produksi = f"🎬 **ALUR CERITA:** {judul_proses}"
                st.session_state.status_sukses = True 
                st.rerun()

    except Exception as e:
        st.error(f"⚠️ Gagal: {e}")
        st.session_state.sedang_proses_id = None
        st.rerun()

    # --- 5. CLEANUP ---
    if st.session_state.status_sukses:
        time.sleep(3) 
        st.session_state.sedang_proses_id = None
        st.session_state.status_sukses = False
        st.rerun()
        
def kirim_notif_wa(pesan):
    """Fungsi otomatis untuk kirim laporan ke Grup WA YT YT 🔥"""
    token = "f4CApLBAJDTPrVHHZCDF"
    target = "120363407726656878@g.us"
    url = "https://api.fonnte.com/send"
    payload = {'target': target, 'message': pesan, 'countryCode': '62'}
    headers = {'Authorization': token}
    try:
        requests.post(url, data=payload, headers=headers, timeout=10)
    except:
        pass

def hitung_logika_performa_dan_bonus(df_arsip_user, df_absen_user, bulan_pilih, tahun_pilih):
    # --- 1. INISIALISASI ---
    bonus_video_total = 0
    uang_absen_total = 0
    pot_sp = 0
    level_sp = "NORMAL"
    
    # Ambil waktu sekarang (WIB)
    tz_wib = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_wib)
    tgl_skrg = sekarang.day
    bln_skrg = sekarang.month
    thn_skrg = sekarang.year

    # Proteksi data kosong
    if df_arsip_user.empty and df_absen_user.empty:
        return 0, 0, 0, "BELUM ADA DATA"

    # --- 2. HITUNG BONUS (Sama seperti sebelumnya) ---
    df_arsip_user = bersihkan_data(df_arsip_user)
    df_absen_user = bersihkan_data(df_absen_user)
    
    if 'TANGGAL' in df_absen_user.columns and 'STATUS' in df_arsip_user.columns:
        df_absen_user['TANGGAL_DT'] = pd.to_datetime(df_absen_user['TANGGAL'], errors='coerce').dt.date
        if 'TGL_SIMPLE' in df_arsip_user.columns:
            rekap_harian = df_arsip_user[df_arsip_user['STATUS'] == 'FINISH'].groupby('TGL_SIMPLE').size().to_dict()
            for tgl in df_absen_user['TANGGAL_DT'].dropna().unique():
                jml_v = rekap_harian.get(str(tgl), 0)
                if jml_v >= 3: uang_absen_total += 30000 
                if jml_v >= 4: bonus_video_total += (jml_v - 3) * 25000

    # --- 3. LOGIKA SP CERDAS (SUDAH DENGAN SP 3) ---
    total_v_bulan = len(df_arsip_user[df_arsip_user['STATUS'] == 'FINISH'])
    
    # A. CEK APAKAH INI BULAN DEPAN?
    if tahun_pilih > thn_skrg or (tahun_pilih == thn_skrg and bulan_pilih > bln_skrg):
        pot_sp = 0
        level_sp = "MASA DEPAN (BELUM MULAI)"
        
    # B. CEK APAKAH INI BULAN SEKARANG?
    elif tahun_pilih == thn_skrg and bulan_pilih == bln_skrg:
        if tgl_skrg <= 6:
            pot_sp = 0
            level_sp = "NORMAL (MASA PROTEKSI)"
        else:
            if total_v_bulan >= 15: pot_sp = 0; level_sp = "NORMAL"
            elif 10 <= total_v_bulan < 15: pot_sp = 300000; level_sp = "SP 1"
            elif 5 <= total_v_bulan < 10: pot_sp = 700000; level_sp = "SP 2"
            else: pot_sp = 1000000; level_sp = "SP 3 (SANKSI BERAT / CUT OFF)"
            
    # C. CEK APAKAH INI BULAN LALU (ARSIP)?
    else:
        if total_v_bulan >= 15: pot_sp = 0; level_sp = "NORMAL"
        elif 10 <= total_v_bulan < 15: pot_sp = 300000; level_sp = "SP 1"
        elif 5 <= total_v_bulan < 10: pot_sp = 700000; level_sp = "SP 2"
        else: pot_sp = 1000000; level_sp = "SP 3 (SANKSI BERAT / CUT OFF)"
            
    return bonus_video_total, uang_absen_total, pot_sp, level_sp

def tampilkan_tugas_kerja():
    st.title("📋 TUGAS KERJA & MONITORING")
    wadah_radar = st.empty()
    
    url_gsheet = "https://docs.google.com/spreadsheets/d/16xcIqG2z78yH_OxY5RC2oQmLwcJpTs637kPY-hewTTY/edit?usp=sharing"
    user_sekarang = st.session_state.get("user_aktif", "tamu").lower()
    tz_wib = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_wib)
    
    foto_staff_default = "https://cdn-icons-png.flaticon.com/512/847/847969.png"
    foto_staff = {
        "icha": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png", 
        "nissa": "https://cdn-icons-png.flaticon.com/512/6997/6997674.png",
        "inggi": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png",
        "lisa": "https://cdn-icons-png.flaticon.com/512/6997/6997674.png"
    }

    # --- INISIALISASI (PENTING BIAR GAK NAME ERROR) ---
    df_arsip_user = pd.DataFrame()
    df_absen_user = pd.DataFrame()
    # -------------------------------------------------
    
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_url(url_gsheet) 
        
        sheet_tugas = sh.worksheet("Tugas")
        sheet_log = sh.worksheet("Log_Aktivitas")
        sheet_staff = sh.worksheet("Staff")
        sheet_absensi = sh.worksheet("Absensi")
        
        data_tugas = sheet_tugas.get_all_records()
        df_all_tugas = pd.DataFrame(data_tugas)
        df_all_tugas = bersihkan_data(df_all_tugas)

        # 1. SETUP FILTER BULAN (DI LUAR IF)
        df_all_tugas['DEADLINE_DT'] = pd.to_datetime(df_all_tugas['DEADLINE'], errors='coerce')
        mask_bulan = (df_all_tugas['DEADLINE_DT'].dt.month == sekarang.month) & \
                     (df_all_tugas['DEADLINE_DT'].dt.year == sekarang.year)

        # 2. LOGIKA RADAR (KHUSUS STAF)
        if user_sekarang != "dian" and user_sekarang != "tamu":
            t_norm = 10 if (sekarang.month == 2 and sekarang.year == 2026) else 40
            progres_h = min(sekarang.day, 25)
            target_h_ini = round((t_norm / 25) * progres_h, 1)
            
            mask_user = df_all_tugas['STAF'].str.strip() == user_sekarang.upper()
            mask_finish = df_all_tugas['STATUS'].str.strip() == 'FINISH'
            
            df_arsip_user = df_all_tugas[mask_user & mask_finish & mask_bulan].copy()
            v_finish = len(df_arsip_user)
            selisih = v_finish - target_h_ini

            try:
                data_absen_raw = sheet_absensi.get_all_records()
                df_absen_all = bersihkan_data(pd.DataFrame(data_absen_raw))
                df_absen_user = df_absen_all[df_absen_all['NAMA'] == user_sekarang.upper()].copy()
            except:
                df_absen_user = pd.DataFrame()

            _, _, pot_sp_r, level_sp_r = hitung_logika_performa_dan_bonus(
                df_arsip_user, df_absen_user, sekarang.month, sekarang.year
            )
            
            if sekarang.day <= 6:
                status_ikon, instruksi = "🛡️ PROTEKSI", "MASIH AMAN"
            elif "Level 3" in level_sp_r:
                status_ikon, instruksi = "🚨 BAHAYA", "EVALUASI KERJA"
            elif pot_sp_r > 0:
                status_ikon, instruksi = "⚠️ WARNING", "KEJAR TARGET"
            elif v_finish >= target_h_ini:
                status_ikon, instruksi = "✨ AMAN", "LANJUTKAN!"
            else:
                status_ikon, instruksi = "⚡ PANTAU", "TINGKATKAN"

            with wadah_radar.container(border=True):
                st.markdown("<style>.metric-label { color: #8b949e; font-size: 11px; font-weight: bold; text-transform: uppercase; } .metric-value { color: #ffffff; font-size: 22px; font-weight: 800; } .metric-sub { font-size: 14px; margin-left: 8px; }</style>", unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(f"<p class='metric-label'>📊 STATUS</p><p class='metric-value'>{status_ikon}</p>", unsafe_allow_html=True)
                with c2: 
                    w_sel = "#1d976c" if selisih >= 0 else "#ff4b4b"
                    st.markdown(f"<p class='metric-label'>🎬 VIDEO FINISH</p><p class='metric-value'>{v_finish}<span class='metric-sub' style='color: {w_sel};'>{selisih:+.1f}</span></p>", unsafe_allow_html=True)
                with c3: st.markdown(f"<p class='metric-label'>🎯 TARGET AMAN</p><p class='metric-value'>{target_h_ini}</p>", unsafe_allow_html=True)
                with c4: st.markdown(f"<p class='metric-label'>📢 INSTRUKSI</p><p class='metric-value' style='font-size: 16px;'>{instruksi}</p>", unsafe_allow_html=True)
            st.divider()

        df_staff_raw = pd.DataFrame(sheet_staff.get_all_records())
        staf_options = df_staff_raw['Nama'].unique().tolist()
        def catat_log(aksi):
            waktu_log = datetime.now(tz_wib).strftime("%d/%m/%Y %H:%M:%S")
            sheet_log.append_row([waktu_log, user_sekarang.upper(), aksi])

    except Exception as e:
        st.error(f"❌ Sistem Offline: {e}")
        return
        
    # --- 3. PANEL ADMIN ---
    if user_sekarang == "dian":
        with st.expander("✨ **KIRIM TUGAS BARU**", expanded=False):
            c2, c1 = st.columns([2, 1]) 
            with c2: isi_tugas = st.text_area("Instruksi Tugas", height=150)
            with c1: 
                staf_tujuan = st.selectbox("Pilih Editor", staf_options)
                pake_wa = st.checkbox("Kirim Notif WA?", value=True)
            if st.button("🚀 KIRIM KE EDITOR", use_container_width=True):
                if isi_tugas:
                    t_id = f"ID{datetime.now(tz_wib).strftime('%m%d%H%M%S')}"
                    sheet_tugas.append_row([t_id, staf_tujuan, sekarang.strftime("%Y-%m-%d"), isi_tugas, "PROSES", "-", "", ""])
                    catat_log(f"Kirim Tugas Baru {t_id}")
                    if pake_wa:
                        kirim_notif_wa(f"✨ *INFO TUGAS BARU*\n\n👤 *Untuk:* {staf_tujuan.upper()}\n🆔 *ID:* {t_id}\n📝 *Detail:* {isi_tugas[:100]}...")
                    st.success("✅ Terkirim!"); time.sleep(1); st.rerun()

    # --- 4. SETOR MANDIRI (FIXED INDENTATION) ---
    if user_sekarang != "dian" and user_sekarang != "tamu":
        with st.container(border=True):
            st.markdown("### 🚀 SETOR TUGAS MANDIRI")
            with st.form("form_mandiri", clear_on_submit=True):
                c1, c2 = st.columns([1.5, 2.5]) 
                with c1: judul_m = st.text_area("📝 Judul Pekerjaan:", height=70)
                with c2: link_m = st.text_area("🔗 Link GDrive:", height=70)
                
                submit_m = st.form_submit_button("🔥 KIRIM SEKARANG", use_container_width=True)
                
                if submit_m:
                    # Baris ini HARUS lebih masuk ke kanan (4 spasi dari if di atasnya)
                    if judul_m and link_m: 
                        t_id_m = f"M{datetime.now(tz_wib).strftime('%m%d%H%M%S')}"
                        sheet_tugas.append_row([
                            t_id_m, 
                            user_sekarang.upper(), 
                            sekarang.strftime("%Y-%m-%d"), 
                            judul_m, 
                            "WAITING QC", 
                            sekarang.strftime("%d/%m/%Y %H:%M"), 
                            link_m, 
                            ""
                        ])
                        kirim_notif_wa(f"⚡ *SETORAN MANDIRI*\n\n👤 *Editor:* {user_sekarang.upper()}\n🆔 *ID:* {t_id_m}\n📝 *Tugas:* {judul_m}")
                        st.success("✅ Terkirim!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("⚠️ Isi dulu Judul dan Link-nya!")

    # --- 5. RENDER KARTU TUGAS ---
    tugas_terfilter = []
    if not df_all_tugas.empty:
        if user_sekarang == "dian":
            tugas_terfilter = [t for t in data_tugas if str(t["Status"]).upper() not in ["FINISH", "CANCELED"]]
        else:
            tugas_terfilter = [t for t in data_tugas if str(t["Staf"]).lower() == user_sekarang and str(t["Status"]).upper() not in ["FINISH", "CANCELED"]]

    if tugas_terfilter:
        tugas_list = list(reversed(tugas_terfilter))
        for i in range(0, len(tugas_list), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(tugas_list):
                    t = tugas_list[i + j]
                    with cols[j]:
                        with st.container(border=True):
                            st.markdown(f"**{str(t['Staf']).upper()}** | `ID: {t['ID']}`")
                            status = str(t["Status"]).upper()
                            cb = "🔴" if status == "REVISI" else "🟡" if status == "WAITING QC" else "🟢"
                            st.markdown(f"{cb} `{status}`")
                            if st.toggle("🔍 Buka Detail", key=f"tgl_{t['ID']}"):
                                st.divider()
                                if t.get("Catatan_Revisi"): st.warning(f"⚠️ **REVISI:** {t['Catatan_Revisi']}")
                                st.markdown(f"> **INSTRUKSI:** \n> {t['Instruksi']}")
                                if user_sekarang == "dian":
                                    if t.get("Link_Hasil") and t["Link_Hasil"] != "-":
                                        st.link_button("🔗 CEK HASIL", t["Link_Hasil"].split(",")[0].strip(), use_container_width=True)
                                    cat_r = st.text_area("Catatan:", key=f"cat_{t['ID']}")
                                    b1, b2, b3 = st.columns(3)
                                    with b1:
                                        if st.button("🟢 ACC", key=f"f_{t['ID']}", use_container_width=True):
                                            cell = sheet_tugas.find(str(t['ID']).strip())
                                            sheet_tugas.update_cell(cell.row, 5, "FINISH")
                                            kirim_notif_wa(f"✅ *TUGAS SELESAI*\n\n👤 {t['Staf'].upper()}\n🆔 {t['ID']}")
                                            st.success("ACC!"); time.sleep(1); st.rerun()
                                    with b2:
                                        if st.button("🔴 REV", key=f"r_{t['ID']}", use_container_width=True):
                                            if cat_r:
                                                cell = sheet_tugas.find(str(t['ID']).strip())
                                                sheet_tugas.update_cell(cell.row, 5, "REVISI"); sheet_tugas.update_cell(cell.row, 8, cat_r)
                                                kirim_notif_wa(f"⚠️ *BUTUH REVISI*\n\n👤 {t['Staf'].upper()}\n🆔 {t['ID']}\n📝 *Pesan:* {cat_r}")
                                                st.warning("REVISI!"); time.sleep(1); st.rerun()
                                    with b3:
                                        if st.button("🚫 BATAL", key=f"c_{t['ID']}", use_container_width=True):
                                            if cat_r:
                                                cell = sheet_tugas.find(str(t['ID']).strip())
                                                sheet_tugas.update_cell(cell.row, 5, "CANCELED"); sheet_tugas.update_cell(cell.row, 8, f"BATAL: {cat_r}")
                                                kirim_notif_wa(f"🚫 *TUGAS DIBATALKAN*\n\n👤 {t['Staf'].upper()}\n🆔 {t['ID']}")
                                                st.error("BATAL!"); time.sleep(1); st.rerun()
                                elif user_sekarang != "tamu":
                                    l_in = st.text_input("Link GDrive:", value=t.get("Link_Hasil", ""), key=f"l_{t['ID']}")
                                    if st.button("🚀 SETOR", key=f"b_{t['ID']}", use_container_width=True):
                                        cell = sheet_tugas.find(str(t['ID']).strip())
                                        sheet_tugas.update_cell(cell.row, 5, "WAITING QC"); sheet_tugas.update_cell(cell.row, 7, l_in)
                                        st.success("Sent!"); time.sleep(1); st.rerun()

    # --- 4. LACI ARSIP (SATU DAFTAR CAMPUR) ---
    st.divider()
    with st.expander("📜 RIWAYAT TUGAS (BULAN INI)", expanded=False):
        if not df_all_tugas.empty:
            # 1. Filter Dasar (Bulan ini & User)
            mask_base = mask_bulan
            if user_sekarang != "dian":
                mask_base &= (df_all_tugas['STAF'] == user_sekarang.upper())
            
            # 2. Ambil yang statusnya FINISH atau CANCELED saja
            df_laci = df_all_tugas[mask_base & (df_all_tugas['STATUS'].isin(['FINISH', 'CANCELED']))].copy()

            if not df_laci.empty:
                # Hitung Statistik buat ditaruh di atas tabel
                total_f = len(df_laci[df_laci['STATUS'] == "FINISH"])
                total_c = len(df_laci[df_laci['STATUS'] == "CANCELED"])
                
                # Teks Laporan Singkat
                st.markdown(f"📊 **Statistik:** ✅ {total_f} Selesai | 🚫 {total_c} Dibatalkan")
                
                # Sortir: Yang terbaru (Deadline/ID) di paling atas
                df_laci = df_laci.sort_values(by='ID', ascending=False)
                
                # 3. Tampilkan Tabel Tunggal
                # Kita masukkan 'Catatan_Revisi' biar kalau ada yang batal, alasannya kelihatan
                kolom_laci = ['ID', 'STAF', 'DEADLINE', 'STATUS', 'Catatan_Revisi']
                kolom_fix = [c for c in kolom_laci if c in df_laci.columns]
                
                st.dataframe(
                    df_laci[kolom_fix],
                    column_config={
                        "ID": "🆔 ID",
                        "STAF": "👤 STAF",
                        "DEADLINE": "📅 TGL",
                        "STATUS": "🚩 STATUS",
                        "Catatan_Revisi": "📝 KETERANGAN/ALASAN"
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("📭 Belum ada riwayat tugas (Selesai/Batal) untuk bulan ini.")
        else:
            st.write("Belum ada data tugas.")
                
    # --- 5. GAJIAN (VERSI UTUH & SAKTI - FIX INDENTASI) ---
    if user_sekarang != "dian" and user_sekarang != "tamu":
        # A. AMBIL DATA ABSENSI DULU (Agar bisa dipakai untuk Radar & Slip)
        try:
            data_absensi = sheet_absensi.get_all_records()
            df_absensi = pd.DataFrame(data_absensi)
            
            # --- Bersihkan data sebelum di-filter ---
            df_absensi = bersihkan_data(df_absensi) 
            
            if not df_absensi.empty:
                # Pastikan kolom NAMA sudah menjadi UPPERCASE karena bersihkan_data
                user_up = user_sekarang.upper().strip()
                mask_ab = (df_absensi['NAMA'] == user_up)
                df_absen_user = df_absensi[mask_ab].copy()
            else:
                # Beri kolom default agar fungsi hitung_logika tidak KeyError TANGGAL
                df_absen_user = pd.DataFrame(columns=['NAMA', 'TANGGAL', 'JAM', 'STATUS'])
        except Exception as e:
            # Jika gagal, buat DataFrame kosong dengan struktur kolom yang benar
            df_absen_user = pd.DataFrame(columns=['NAMA', 'TANGGAL', 'JAM', 'STATUS'])

        # B. HITUNG LOGIKA (Bonus, Hadir, SP)
        b_video, u_hadir, pot_sp, level_sp = hitung_logika_performa_dan_bonus(
            df_arsip_user,
            df_absen_user, 
            sekarang.month, 
            sekarang.year
        )

        # --- TAMPILAN ATURAN GAJI (VERSI REVISI FINAL - KONSISTENSI) ---
        with st.expander("ℹ️ INFO PENTING: ATURAN & SIMULASI GAJI", expanded=False):
            st.write("### 📢 Panduan Kerja & Simulasi Penghasilan")
            
            tab_info, tab_simulasi = st.tabs(["📜 Aturan Dasar & SP", "💸 Simulasi Harian"])
            
            with tab_info:
                st.markdown("""
                Selamat bekerja! Agar penghasilan kamu maksimal, mohon perhatikan aturan berikut:
                
                * ⏰ **Bonus Kehadiran:** Tambahan **Rp 30.000** diberikan setiap hari jika kamu menyelesaikan minimal **3 video** dengan status **Finish**.
                * 🎬 **Apresiasi Produksi:** Untuk video ke-4 (berlaku kelipatan) di hari yang sama, ada tambahan **Rp 25.000** per video.
                * ⚠️ **Batas Minimal Bonus:** Jika hanya menyelesaikan **2 video** dalam sehari, status kamu **Aman** (tidak tercatat SP), namun kamu **tidak mendapatkan** Bonus Kehadiran maupun Bonus Produksi pada hari tersebut.
                * 📌 **Penting:** Perhitungan bonus dilakukan secara harian. Mari jaga konsistensi setiap hari agar bonus tidak terlewat.
                
                ---
                #### 🛡️ Mengenal Sistem Performa (SP)
                Sistem ini bertujuan untuk menjaga produktivitas tim agar tetap stabil:
                
                1. **Masa Proteksi:** Tanggal 1 sampai 6 tiap bulan adalah masa adaptasi, kamu aman dari penilaian SP.
                2. **Hari Kurang Produkif:** Jika dalam satu hari hanya menyelesaikan **0 atau 1 video**, hari tersebut dicatat sebagai 'Hari Kurang Produktif'.
                3. **Akumulasi SP:**
                    * **SP 1 (7 Hari):** Jika dalam sebulan terdapat 7 hari kurang produktif (Potongan Rp 300.000).
                    * **SP 2 (14 Hari):** Jika mencapai 14 hari kurang produktif (Potongan Rp 700.000).
                    * **SP 3 (21 Hari):** Jika mencapai 21 hari kurang produktif (Potongan Rp 1.000.000 + Pemutusan Kerja).
                """)
                st.info("💡 *Tips: Setor minimal 3 video setiap hari untuk mengaktifkan semua bonus kamu!*")

            with tab_simulasi:
                st.write("**Geser slider untuk melihat potensi penghasilan jika kamu bekerja konsisten:**")
                
                t_hari = st.select_slider(
                    "Target setoran video kamu per hari:",
                    options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                    value=3,
                    key="slider_final_v4"
                )
                
                # Logika Hitung (Asumsi 25 Hari Kerja)
                gapok_sim = 2000000
                if t_hari >= 3:
                    b_absen_bln = 30000 * 25
                    b_video_bln = (t_hari - 3) * 25000 * 25
                    p_sp = 0
                    status = "🌟 Performa Sangat Baik" if t_hari >= 5 else "✅ Performa Standar"
                elif t_hari == 2:
                    b_absen_bln, b_video_bln, p_sp = 0, 0, 0
                    status = "⚠️ Performa Cukup (Aman SP, Tanpa Bonus)"
                else:
                    b_absen_bln, b_video_bln, p_sp = 0, 0, 1000000
                    status = "❗ Performa Perlu Ditingkatkan (Risiko SP)"

                total_gaji = (gapok_sim + b_absen_bln + b_video_bln) - p_sp
                
                st.divider()
                st.markdown(f"**Status: {status}**")
                
                col_total, col_detail = st.columns(2)
                with col_total:
                    st.metric("ESTIMASI TERIMA", f"Rp {total_gaji:,}")
                with col_detail:
                    st.metric("POTENSI BONUS", f"Rp {b_absen_bln + b_video_bln:,}", 
                              delta=f"Cair Rp {(b_absen_bln + b_video_bln)//25 if t_hari >=3 else 0:,} / hari")

                if t_hari == 2:
                    st.error("Pada level ini, kamu hanya menerima Gaji Pokok karena Bonus Kehadiran baru aktif di angka 3 video/hari.")
                elif t_hari < 2:
                    st.error("Risiko potongan SP tinggi dan tidak ada bonus yang cair.")
                else:
                    st.success(f"Mantap! Dengan {t_hari} video/hari, rezeki bonus kamu lancar setiap hari.")

                st.caption(f"Catatan: Estimasi berdasarkan setoran stabil {t_hari} video/hari selama 25 hari kerja.")

        # D. --- SLIP GAJI PREMIUM V3 TURBO (BAHASA INDONESIA - FINAL) ---
        if sekarang.day >= 28: 
            with st.expander("💰 KLAIM SLIP GAJI BULAN INI", expanded=False):
                try:
                    # 1. KUNCI DATA STAFF (Anti-Tertukar)
                    S_VAR_NAMA = user_sekarang.upper().strip()
                    df_staff_fix = bersihkan_data(df_staff_raw)
                    row_staff = df_staff_fix[df_staff_fix['NAMA'] == S_VAR_NAMA]
                    
                    if not row_staff.empty:
                        res = row_staff.iloc[0]
                        S_VAR_GAPOK = int(pd.to_numeric(str(res.get('GAJI_POKOK')).replace('.',''), errors='coerce') or 0)
                        S_VAR_TUNJ = int(pd.to_numeric(str(res.get('TUNJANGAN')).replace('.',''), errors='coerce') or 0)
                        S_VAR_TOTAL = max(0, (S_VAR_GAPOK + S_VAR_TUNJ + b_video + u_hadir) - pot_sp)
                        
                        # --- TEMPLATE HTML PREMIUM INDONESIA (LOGO GEDE - KONTEN RAMPING) ---
                        slip_staff_html = f"""
                        <div style="background: #ffffff; color: #1a1a1a; padding: 25px; border-radius: 20px; border: 1px solid #eef2f3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; width: 300px; margin: auto; box-shadow: 0 15px 40px rgba(0,0,0,0.05);">
                            
                            <div style="text-align: center; margin-bottom: 20px;">
                                <img src="https://raw.githubusercontent.com/pintarkantor-prog/pintarmedia/main/PINTAR.png" 
                                     style="width: 220px; max-width: 100%; height: auto; margin-bottom: 5px;">
                                <div style="display: flex; align-items: center; justify-content: center; gap: 6px; margin-bottom: 8px;">
                                    <div style="height: 1px; background: #eee; flex: 1;"></div>
                                    <div style="height: 3px; background: #1d976c; width: 35px; border-radius: 10px;"></div>
                                    <div style="height: 1px; background: #eee; flex: 1;"></div>
                                </div>
                                <p style="margin: 0; font-size: 8px; color: #1d976c; letter-spacing: 3px; text-transform: uppercase; font-weight: 800;">Slip Gaji Resmi</p>
                            </div>

                            <div style="background: #fcfcfc; padding: 12px; border-radius: 12px; border: 1px solid #f0f0f0; margin-bottom: 15px;">
                                <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
                                    <tr><td style="color: #999; padding-bottom: 4px; font-weight: 600; font-size: 8px; text-transform: uppercase;">Staff</td><td align="right" style="padding-bottom: 4px;"><b>{S_VAR_NAMA}</b></td></tr>
                                    <tr><td style="color: #999; padding-bottom: 4px; font-weight: 600; font-size: 8px; text-transform: uppercase;">Periode</td><td align="right" style="padding-bottom: 4px;"><b>{sekarang.strftime('%B %Y')}</b></td></tr>
                                    <tr><td style="color: #999; font-weight: 600; font-size: 8px; text-transform: uppercase;">Status</td><td align="right"><span style="color: {'#1d976c' if pot_sp == 0 else '#e74c3c'}; font-weight: 800;">{level_sp}</span></td></tr>
                                </table>
                            </div>

                            <div style="margin-bottom: 20px; padding: 0 2px;">
                                <table style="width: 100%; font-size: 12px; line-height: 2; border-collapse: collapse;">
                                    <tr><td style="color: #666;">Gaji Pokok</td><td align="right" style="font-weight: 600;">Rp {S_VAR_GAPOK:,}</td></tr>
                                    <tr><td style="color: #666;">Tunjangan</td><td align="right" style="font-weight: 600;">Rp {S_VAR_TUNJ:,}</td></tr>
                                    <tr><td style="color: #1d976c; font-weight: 600;">Bonus Hadir</td><td align="right" style="color: #1d976c; font-weight: 700;">+ {u_hadir:,}</td></tr>
                                    <tr><td style="color: #1d976c; font-weight: 600;">Bonus Video</td><td align="right" style="color: #1d976c; font-weight: 700;">+ {b_video:,}</td></tr>
                                    <tr style="border-top: 1px solid #f0f0f0;"><td style="color: #e74c3c; font-weight: 600; padding-top: 4px;">Potongan SP</td><td align="right" style="color: #e74c3c; font-weight: 700; padding-top: 4px;">- {pot_sp:,}</td></tr>
                                </table>
                            </div>

                            <div style="background: #1a1a1a; color: white; padding: 10px 15px; border-radius: 12px; text-align: center;">
                                <p style="margin: 0; font-size: 8px; color: #55efc4; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;">Total Diterima</p>
                                <h2 style="margin: 2px 0 0; font-size: 22px; color: #55efc4; font-weight: 800; letter-spacing: -1px;">Rp {S_VAR_TOTAL:,}</h2>
                            </div>

                            <div style="margin-top: 30px; text-align: center; font-size: 8px; color: #ccc; line-height: 1.5; padding-top: 12px; border-top: 1px solid #f0f0f0;">
                                <b style="color: #888;">Diterbitkan Digital: Sistem PINTAR MEDIA</b><br>
                                Cetak: {datetime.now(tz_wib).strftime('%d/%m/%Y %H:%M:%S')} WIB<br>
                                <span style="background: #f9f9f9; padding: 1px 8px; border-radius: 4px; display: inline-block; margin-top: 4px; color: #bbb;">REF: {datetime.now(tz_wib).strftime('%y%m%d%H%M')}</span>
                            </div>
                        </div>
                        """
                        st.components.v1.html(slip_staff_html, height=650)

                        if st.button("🧧 KONFIRMASI TERIMA GAJI", use_container_width=True):
                            catat_log(f"Konfirmasi gaji Rp {S_VAR_TOTAL:,} oleh {S_VAR_NAMA}")
                            st.success(f"Berhasil Dikonfirmasi, {panggilan_fix}!")
                    else:
                        st.error("Data staff tidak ditemukan.")
                except Exception as e: 
                    st.warning(f"Gagal memproses slip: {e}")
        else:
            st.info("🔒 **Menu Klaim Gaji** akan terbuka otomatis pada tanggal 28 setiap bulannya.")
                
def tampilkan_kendali_tim():
    user_sekarang = st.session_state.get("user_aktif", "tamu").lower()
    
    # 1. PROTEKSI AKSES (Hanya Dian)
    if user_sekarang != "dian":
        st.title("⚡ KENDALI TIM")
        st.divider()
        st.warning("🔒 **AREA TERBATAS**")
        return

    # 2. HALAMAN KHUSUS ADMIN
    st.title("⚡ PUSAT KENDALI TIM (ADMIN)")
    
    url_gsheet = "https://docs.google.com/spreadsheets/d/16xcIqG2z78yH_OxY5RC2oQmLwcJpTs637kPY-hewTTY/edit?usp=sharing"
    tz_wib = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_wib)
    
    c_bln, c_thn = st.columns([2, 2])
    daftar_bulan = {1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"}
    pilihan_nama = c_bln.selectbox("📅 Pilih Bulan Laporan:", list(daftar_bulan.values()), index=sekarang.month - 1)
    bulan_dipilih = [k for k, v in daftar_bulan.items() if v == pilihan_nama][0]
    tahun_dipilih = c_thn.number_input("📅 Tahun:", value=sekarang.year, min_value=2024, max_value=2030)

    st.divider()

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_url(url_gsheet)
        
        # --- AMBIL DATA DASAR & NORMALISASI HEADER ---
        def ambil_data(nama_sheet):
            ws = sh.worksheet(nama_sheet)
            data = ws.get_all_records()
            df = pd.DataFrame(data)
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df

        df_staff = ambil_data("Staff")
        df_staff = bersihkan_data(df_staff)
        df_absen = ambil_data("Absensi")
        df_kas = ambil_data("Arus_Kas")
        ws_tugas = sh.worksheet("Tugas")

        # Ambil Data Tugas Manual
        raw_t = ws_tugas.get_all_values()
        if len(raw_t) > 1:
            h_t = [str(h).strip().upper() for h in raw_t[0]]
            df_tugas = pd.DataFrame(raw_t[1:], columns=h_t)
            if len(df_tugas.columns) >= 5:
                df_tugas.columns.values[4] = "STATUS"
        else:
            df_tugas = pd.DataFrame(columns=['STAF', 'DEADLINE', 'INSTRUKSI', 'STATUS'])

        # --- FUNGSI FILTER TANGGAL AMAN ---
        def saring_tgl(df, kolom, bln, thn):
            if df.empty or kolom.upper() not in df.columns: 
                return pd.DataFrame()
            df['TGL_TEMP'] = pd.to_datetime(df[kolom.upper()], dayfirst=True, errors='coerce')
            mask = df['TGL_TEMP'].apply(lambda x: x.month == bln and x.year == thn if pd.notnull(x) else False)
            return df[mask].copy()

        df_t_bln = saring_tgl(df_tugas, 'DEADLINE', bulan_dipilih, tahun_dipilih)
        df_a_f = saring_tgl(df_absen, 'TANGGAL', bulan_dipilih, tahun_dipilih)
        df_k_f = saring_tgl(df_kas, 'TANGGAL', bulan_dipilih, tahun_dipilih)

        # --- LOGIKA HITUNG KEUANGAN (SINKRON DENGAN ATURAN BARU) ---
        if not df_t_bln.empty:
            # Tambahkan .copy() di akhir filter untuk memutus hubungan dengan dataframe asli
            df_f_f = df_t_bln[df_t_bln['STATUS'].astype(str).str.upper() == "FINISH"].copy()
        else:
            df_f_f = pd.DataFrame()
        
        # Rekap Video per Nama per Tanggal
        rekap_harian_tim = {}
        if not df_f_f.empty:
            # Gunakan .str.upper() (DENGAN TITIK SETELAH .str)
            df_f_f['STAF'] = df_f_f['STAF'].astype(str).str.strip().str.upper()
            
            # Pastikan TGL_TEMP adalah datetime agar tidak error saat .dt
            df_f_f['TGL_TEMP'] = pd.to_datetime(df_f_f['TGL_TEMP'], errors='coerce')
            df_f_f['TGL_STR'] = df_f_f['TGL_TEMP'].dt.strftime('%Y-%m-%d')
            
            # Grouping
            rekap_harian_tim = df_f_f.groupby(['STAF', 'TGL_STR']).size().unstack(fill_value=0).to_dict('index')

        # Total Video per Nama
        if not df_f_f.empty:
            # Karena STAF sudah di-upper di atas, langsung value_counts saja
            rekap_total_video = df_f_f['STAF'].value_counts().to_dict()
        else:
            rekap_total_video = {}
        
        # Kalkulasi Pendapatan & Pengeluaran
        inc = 0
        ops = 0
        if not df_k_f.empty:
            # Pastikan kolom NOMINAL dibersihkan dari karakter non-angka (seperti Rp atau titik ribuan manual)
            for col_num in ['NOMINAL']:
                df_k_f[col_num] = df_k_f[col_num].astype(str).replace(r'[^\d.]', '', regex=True)
            
            inc = pd.to_numeric(df_k_f[df_k_f['TIPE'] == 'PENDAPATAN']['NOMINAL'], errors='coerce').fillna(0).sum()
            ops = pd.to_numeric(df_k_f[df_k_f['TIPE'] == 'PENGELUARAN']['NOMINAL'], errors='coerce').fillna(0).sum()
        
        # --- LOGIKA HITUNG KEUANGAN GLOBAL ---
        total_pengeluaran_gaji = 0
        
        # Penentu apakah bulan masa depan
        is_masa_depan = tahun_dipilih > sekarang.year or (tahun_dipilih == sekarang.year and bulan_dipilih > sekarang.month)
        
        # Jika bukan masa depan, jalankan perhitungan
        if not is_masa_depan:
            for _, s in df_staff.iterrows():
                n_up = str(s.get('NAMA', '')).strip().upper()
                if n_up == "" or n_up == "NAN": continue
                
                # A. Bonus & Absen
                u_absen_staf, b_lembur_staf = 0, 0
                if n_up in rekap_harian_tim:
                    for tgl, jml in rekap_harian_tim[n_up].items():
                        if jml >= 3: u_absen_staf += 30000
                        if jml >= 4: b_lembur_staf += (jml - 3) * 25000
                
                # B. Logika SP Smart Switch (Februari 10, Maret 40)
                tot_v = rekap_total_video.get(n_up, 0)
                p_sp = 0
                if tahun_dipilih == 2026 and bulan_dipilih == 2:
                    t_norm, t_s1, t_s2 = 10, 7, 4
                else:
                    t_norm, t_s1, t_s2 = 40, 30, 20
                
                # Hitung ambang batas berjalan
                progres_h = min(sekarang.day, 25)
                threshold = (t_norm / 25) * progres_h
                
                # Eksekusi Potongan
                if sekarang.day > 6 and tot_v < threshold:
                    if tot_v >= t_norm: p_sp = 0
                    elif t_s1 <= tot_v < t_norm: p_sp = 300000
                    elif t_s2 <= tot_v < t_s1: p_sp = 700000
                    else: p_sp = 1000000
                
                # C. Hitung Gaji Bersih per Orang
                g_pokok = int(pd.to_numeric(s.get('GAJI_POKOK'), errors='coerce') or 0)
                t_tunj = int(pd.to_numeric(s.get('TUNJANGAN'), errors='coerce') or 0)
                
                bersih_orang = (g_pokok + t_tunj + u_absen_staf + b_lembur_staf) - p_sp
                total_pengeluaran_gaji += max(0, bersih_orang)
        else:
            # Jika masa depan, pengeluaran dipaksa 0
            total_pengeluaran_gaji = 0

        # --- TAMPILAN HEADER (Pindahkan ke luar blok IF di atas) ---
        st.subheader(f"💰 LAPORAN KEUANGAN - {pilihan_nama} {tahun_dipilih}")
        
        # Reset variabel metrik jika masa depan
        if is_masa_depan:
            inc, total_pengeluaran_gaji, ops = 0, 0, 0
            
        # Tampilkan Metrik
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 PENDAPATAN", f"Rp {inc:,}")
        m2.metric("💸 PENGELUARAN", f"Rp {(total_pengeluaran_gaji + ops):,}")
        
        saldo_bersih = inc - (total_pengeluaran_gaji + ops)
        simbol = "+" if saldo_bersih >= 0 else "-"
        abs_saldo = abs(saldo_bersih)

        m3.metric(
            label="💎 BERSIH", 
            value=f"Rp {saldo_bersih:,}",
            delta=f"{simbol} Rp {abs_saldo:,}",
            delta_color="normal" 
        )
        # --- TAMPILAN 2: INPUT TRANSAKSI (POSISI KEDUA) ---
        with st.expander("📝 **INPUT TRANSAKSI KEUANGAN**", expanded=False):
            with st.form("form_kas", clear_on_submit=True):
                c_tipe, c_kat, c_nom = st.columns(3)
                f_tipe = c_tipe.selectbox("Jenis:", ["PENDAPATAN", "PENGELUARAN"])
                f_kat = c_kat.selectbox("Kategori:", ["YouTube", "Brand Deal", "Tool AI", "Internet", "Listrik", "Lainnya"])
                f_nom = c_nom.number_input("Nominal (Rp):", min_value=0, step=10000)
                f_ket = st.text_input("Keterangan:")
                if st.form_submit_button("Simpan Transaksi"):
                    sh.worksheet("Arus_Kas").append_row([sekarang.strftime('%Y-%m-%d'), f_tipe, f_kat, int(f_nom), f_ket, "Dian"])
                    st.success("Tersimpan!"); time.sleep(1); st.rerun()

        st.divider()

        # --- TAMPILAN 4: JADWAL PRODUKSI (VERSI EXPANDER) ---
        with st.expander("📅 JADWAL PRODUKSI", expanded=False):
            if not df_t_bln.empty:
                for _, t in df_t_bln.sort_values('TGL_TEMP').iterrows():
                    # Format tampilan lebih ringkas: Ikon - Tanggal - Instruksi - Staf
                    ikon = {"FINISH": "🟢", "WAITING QC": "🔵", "PROSES": "🟡", "REVISI": "🔴"}.get(str(t['STATUS']).upper(), "⚪")
                    st.write(f"{ikon} **{t['TGL_TEMP'].strftime('%d %b')}** — {t.get('INSTRUKSI')} — `{t.get('STAF')}`")
            else:
                st.caption("Tidak ada jadwal untuk periode ini.")

        # --- TAMPILAN 5: MONITORING PROGRES PRODUKSI (PENGGANTI GRAFIK) ---
        with st.expander("📊 MONITORING PROGRES PRODUKSI TIM", expanded=False):
            if rekap_total_video is not None:
                # --- LOGIKA TARGET SMART SWITCH ---
                if tahun_dipilih == 2026 and bulan_dipilih == 2:
                    t_normal = 10
                else:
                    t_normal = 40
                
                progres_hari = min(sekarang.day, 25)
                target_aman = round((t_normal / 25) * progres_hari, 1)
                
                data_monitor = []
                for _, s in df_staff.iterrows():
                    n_up = str(s.get('NAMA', '')).strip().upper()
                    if n_up == "" or n_up == "NAN": continue
                    
                    jml_v = rekap_total_video.get(n_up, 0)
                    selisih = jml_v - target_aman
                    
                    if jml_v >= target_aman: status = "🟢 AMAN"
                    elif jml_v >= (t_normal * 0.5 / 25) * progres_hari: status = "🟡 WASPADA"
                    else: status = "🔴 BAHAYA (SP 3)"
                    
                    data_monitor.append({
                        "NAMA STAF": n_up,
                        "HASIL": int(jml_v),
                        "TARGET MINIMAL": target_aman,
                        "SELISIH": round(selisih, 1),
                        "STATUS": status
                    })
                
                st.table(pd.DataFrame(data_monitor))
                st.info(f"💡 Target minimal hari ini (Tgl {sekarang.day}) adalah {target_aman} video (Standar {t_normal} video/bulan).")
            else:
                st.info("Belum ada aktivitas produksi yang tercatat 'FINISH' bulan ini.")

        # --- TAMPILAN 5.5: REKAP ABSENSI & HARI CAIR (SINKRON GSHEET) ---
        with st.expander("📅 REKAP ABSENSI & MONITORING CAIR", expanded=False):
            try:
                # 1. Ambil data absen asli dari GSheet
                df_absen_raw = df_a_f.copy() # Ini dari hasil saring_tgl di atas
                
                # 2. Buat tabel monitoring per staff
                rekap_absen_data = []
                for _, s in df_staff.iterrows():
                    n_up = str(s['NAMA']).strip().upper()
                    
                    # Hitung Total Hadir (Ada di sheet Absensi)
                    total_hadir = 0
                    if not df_absen_raw.empty:
                        total_hadir = len(df_absen_raw[df_absen_raw['NAMA'] == n_up]['TANGGAL'].unique())
                    
                    # Hitung Hari Cair (Minimal 3 Video Finish)
                    hari_cair = 0
                    if n_up in rekap_harian_tim:
                        for tgl, jml in rekap_harian_tim[n_up].items():
                            if jml >= 3:
                                hari_cair += 1
                                
                    # Hitung Hari Malas (Cuma 0-1 Video)
                    hari_malas = 0
                    if n_up in rekap_harian_tim:
                        for tgl, jml in rekap_harian_tim[n_up].items():
                            if jml <= 1:
                                hari_malas += 1
                    
                    rekap_absen_data.append({
                        "NAMA": n_up,
                        "TOTAL HADIR": f"{total_hadir} Hari",
                        "HARI CAIR ✨": f"{hari_cair} Hari",
                        "HARI MALAS ⚠️": f"{hari_malas} Hari",
                        "STATUS": "RAJIN" if hari_cair > hari_malas else "PERLU EVALUASI"
                    })
                
                # Tampilkan dalam bentuk tabel yang bersih
                if rekap_absen_data:
                    st.table(pd.DataFrame(rekap_absen_data))
                else:
                    st.info("Belum ada data absensi bulan ini.")
                    
            except Exception as e:
                st.error(f"Gagal memuat rekap absensi: {e}")

        # --- REVISI TAMPILAN SLIP GAJI PREMIUM (ADMIN) ---
        with st.expander("💰 RINCIAN GAJI & SLIP", expanded=False):
            ada_kerja = False
            df_staff_raw_slip = df_staff.copy()
            
            for _, s in df_staff_raw_slip.iterrows():
                n_up = str(s.get('NAMA', '')).strip().upper()
                if n_up == "" or n_up == "NAN": continue
                
                # 1. HITUNG LOGIKA KEUANGAN PER ORANG
                u_absen_staf = 0
                b_lembur_staf = 0
                if n_up in rekap_harian_tim:
                    for tgl, jml in rekap_harian_tim[n_up].items():
                        if jml >= 3: u_absen_staf += 30000
                        if jml >= 4: b_lembur_staf += (jml - 3) * 25000
                
                jml_v = rekap_total_video.get(n_up, 0)
                pot_sp_admin = 0
                t_normal = 10 if (tahun_dipilih == 2026 and bulan_dipilih == 2) else 40
                t_sp1, t_sp2 = (7, 4) if t_normal == 10 else (30, 20)

                # Logika Potongan SP
                if not (tahun_dipilih > sekarang.year or (tahun_dipilih == sekarang.year and bulan_dipilih > sekarang.month)):
                    if not (tahun_dipilih == sekarang.year and bulan_dipilih == sekarang.month and sekarang.day <= 6):
                        if jml_v >= t_normal: pot_sp_admin = 0
                        elif t_sp1 <= jml_v < t_normal: pot_sp_admin = 300000
                        elif t_sp2 <= jml_v < t_sp1: pot_sp_admin = 700000
                        else: pot_sp_admin = 1000000

                # 2. EKSEKUSI TAMPILAN
                ada_kerja = True
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.write(f"👤 **{n_up}**")
                    c1.caption(f"💼 {s.get('JABATAN', 'STAFF PRODUCTION')}")
                    c2.write(f"📅 {int(u_absen_staf/30000)} Hari Cair")
                    c3.write(f"🎬 {jml_v} Video")
                    
                    if st.button(f"📑 CETAK SLIP {n_up}", key=f"btn_slip_{n_up}"):
                        # Parsing Angka GSheet (Menghilangkan titik/koma jika ada)
                        v_gapok = int(pd.to_numeric(str(s.get('GAJI_POKOK')).replace('.',''), errors='coerce') or 0)
                        v_tunjangan = int(pd.to_numeric(str(s.get('TUNJANGAN')).replace('.',''), errors='coerce') or 0)
                        v_total_terima = (v_gapok + v_tunjangan + u_absen_staf + b_lembur_staf) - pot_sp_admin
                        
                        # --- DESAIN SLIP GAJI PREMIUM HTML (VERSI KENDALI TIM - RAMPING & GAHAR) ---
                        slip_html = f"""
                        <div style="background: #ffffff; color: #1a1a1a; padding: 25px; border-radius: 20px; border: 1px solid #eef2f3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; width: 300px; margin: auto; box-shadow: 0 15px 40px rgba(0,0,0,0.05);">
                            
                            <div style="text-align: center; margin-bottom: 20px;">
                                <img src="https://raw.githubusercontent.com/pintarkantor-prog/pintarmedia/main/PINTAR.png" 
                                     style="width: 220px; max-width: 100%; height: auto; margin-bottom: 5px;">
                                <div style="display: flex; align-items: center; justify-content: center; gap: 6px; margin-bottom: 8px;">
                                    <div style="height: 1px; background: #eee; flex: 1;"></div>
                                    <div style="height: 3px; background: #1d976c; width: 35px; border-radius: 10px;"></div>
                                    <div style="height: 1px; background: #eee; flex: 1;"></div>
                                </div>
                                <p style="margin: 0; font-size: 8px; color: #1d976c; letter-spacing: 3px; text-transform: uppercase; font-weight: 800;">Slip Gaji Resmi</p>
                            </div>

                            <div style="background: #fcfcfc; padding: 12px; border-radius: 12px; border: 1px solid #f0f0f0; margin-bottom: 15px;">
                                <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
                                    <tr><td style="color: #999; padding-bottom: 4px; font-weight: 600; font-size: 8px; text-transform: uppercase;">Nama</td><td align="right" style="padding-bottom: 4px;"><b>{n_up}</b></td></tr>
                                    <tr><td style="color: #999; padding-bottom: 4px; font-weight: 600; font-size: 8px; text-transform: uppercase;">Jabatan</td><td align="right" style="padding-bottom: 4px;"><b>{s.get('JABATAN', 'STAFF')}</b></td></tr>
                                    <tr><td style="color: #999; font-weight: 600; font-size: 8px; text-transform: uppercase;">Periode</td><td align="right"><b>{pilihan_nama} {tahun_dipilih}</b></td></tr>
                                </table>
                            </div>

                            <div style="margin-bottom: 20px; padding: 0 2px;">
                                <table style="width: 100%; font-size: 12px; line-height: 2; border-collapse: collapse;">
                                    <tr><td style="color: #666;">Gaji Pokok</td><td align="right" style="font-weight: 600;">Rp {v_gapok:,}</td></tr>
                                    <tr><td style="color: #666;">Tunjangan</td><td align="right" style="font-weight: 600;">Rp {v_tunjangan:,}</td></tr>
                                    <tr><td style="color: #1d976c; font-weight: 600;">Bonus Absen</td><td align="right" style="color: #1d976c; font-weight: 700;">+ {u_absen_staf:,}</td></tr>
                                    <tr><td style="color: #1d976c; font-weight: 600;">Bonus Video</td><td align="right" style="color: #1d976c; font-weight: 700;">+ {b_lembur_staf:,}</td></tr>
                                    <tr style="border-top: 1px solid #f0f0f0;"><td style="color: #e74c3c; font-weight: 600; padding-top: 4px;">Potongan SP</td><td align="right" style="color: #e74c3c; font-weight: 700; padding-top: 4px;">- {pot_sp_admin:,}</td></tr>
                                </table>
                            </div>

                            <div style="background: #1a1a1a; color: white; padding: 10px 15px; border-radius: 12px; text-align: center;">
                                <p style="margin: 0; font-size: 8px; color: #55efc4; text-transform: uppercase; letter-spacing: 2px; font-weight: 700;">Total Diterima</p>
                                <h2 style="margin: 2px 0 0; font-size: 22px; color: #55efc4; font-weight: 800; letter-spacing: -1px;">Rp {v_total_terima:,}</h2>
                            </div>

                            <div style="margin-top: 30px; text-align: center; font-size: 8px; color: #ccc; line-height: 1.5; padding-top: 15px; border-top: 1px solid #f0f0f0;">
                                <b style="color: #888;">Diterbitkan secara digital oleh Sistem Produksi PINTAR MEDIA</b><br>
                                Waktu Cetak: {datetime.now(tz_wib).strftime('%d/%m/%Y %H:%M:%S')} WIB<br>
                                <span style="background: #f9f9f9; padding: 2px 8px; border-radius: 4px; display: inline-block; margin-top: 6px; color: #bbb; font-family: monospace;">REF: PM-{datetime.now(tz_wib).strftime('%y%m%d%H%M')}</span>
                            </div>
                        </div>
                        """
                        st.components.v1.html(slip_html, height=650)

            if not ada_kerja:
                st.info("Belum ada aktivitas tim yang divalidasi 'FINISH' untuk periode ini.")
            
    except Exception as e:
        st.error(f"⚠️ Terjadi Kendala Sistem: {e}")
        
    # --- TAMPILAN 7: PENGELOLA AKUN AI (VERSI SEJAJAR SEMPURNA) ---    
    with st.expander("🔐 DATABASE AKUN AI", expanded=False):
        try:
            # 1. AMBIL DATA
            ws_akun = sh.worksheet("Akun_AI")
            data_akun_raw = ws_akun.get_all_records()
            df_ai = pd.DataFrame(data_akun_raw)
            
            # 2. TOMBOL TAMBAH DATA (Toggle Form)
            if st.button("➕ Tambah Akun Baru", use_container_width=True):
                st.session_state.buka_form = not st.session_state.get('buka_form', False)
            
            if st.session_state.get('buka_form', False):
                with st.form("form_ai_simple", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    f_ai = c1.text_input("Nama AI")
                    f_mail = c2.text_input("Email")
                    f_pass = c1.text_input("Password")
                    f_exp = c2.date_input("Tanggal Expired")
                    if st.form_submit_button("Simpan Ke Cloud"):
                        ws_akun.append_row([f_ai, f_mail, f_pass, str(f_exp)])
                        st.success("Data Tersimpan!")
                        time.sleep(1)
                        st.rerun()

            st.write("") # Jarak

            # 3. DAFTAR AKUN (LOGIKA AUTO-HIDE H+1)
            if not df_ai.empty:
                df_ai['EXPIRED'] = pd.to_datetime(df_ai['EXPIRED']).dt.date
                hari_ini = sekarang.date()
                df_tampil = df_ai[df_ai['EXPIRED'] + timedelta(days=1) >= hari_ini]

                for _, row in df_tampil.iterrows():
                    sisa = (row['EXPIRED'] - hari_ini).days
                    
                    if sisa > 7:
                        label = "🟢 Aman"
                    elif 0 <= sisa <= 3:
                        label = "🟠 Segera Habis"
                    elif sisa < 0:
                        label = "🔴 Expired"
                    else:
                        label = "⚪ Standby"

                    # Box Tiap Akun - SEMUA SEJAJAR
                    with st.container(border=True):
                        col1, col2 = st.columns([2.5, 1.5])
                        with col1:
                            # Sisi Kiri: Nama AI, Email, dan Password sejajar
                            st.write(f"**{row['AI']}** — `{row['EMAIL']}` — Pass: `{row['PASSWORD']}`")
                        with col2:
                            # Sisi Kanan: Label Status dan Tanggal sejajar dalam satu baris
                            st.write(f"**{label}** — `{row['EXPIRED'].strftime('%d %b %Y')}`")
            else:
                st.caption("Belum ada data akun.")

        except Exception as e:
            st.info("💡 Pastikan tab 'Akun_AI' sudah ada di Google Sheets.")
        
# ==============================================================================
# BAGIAN 6: MODUL UTAMA - RUANG PRODUKSI (VERSI TOTAL FULL - NO CUT)
# ==============================================================================
def simpan_ke_memori():
    st.session_state.data_produksi = st.session_state.data_produksi
def tampilkan_ruang_produksi():
    # 1. PENGATURAN WAKTU & USER
    sekarang = datetime.utcnow() + timedelta(hours=7) 
    hari_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    bulan_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    
    nama_hari = hari_id[sekarang.weekday()]
    tgl = sekarang.day
    nama_bulan = bulan_id[sekarang.month - 1]
    user_aktif = st.session_state.get("user_aktif", "User").upper()

    # 2. KUNCI DATA DARI SESSION STATE (SUMBER UTAMA)
    # Kita ambil data di baris paling atas agar tidak tertimpa/reset
    data = st.session_state.data_produksi
    ver = st.session_state.get("form_version", 0)

    # --- QUALITY BOOSTER & NEGATIVE CONFIG (VERSI FINAL KLIMIS) ---
    QB_IMG = (
        "8k RAW optical clarity, cinematic depth of field, f/1.8 aperture, "
        "bokeh background, razor-sharp focus on subject detail, "
        "high-index lens glass look, CPL filter, sub-surface scattering, "
        "physically-based rendering, hyper-detailed surface micro-textures, "
        "anisotropic filtering, ray-traced ambient occlusion"
    )

    QB_VID = (
        "Unreal Engine 5.4, 24fps cinematic motion, ultra-clear, 8k UHD, high dynamic range, "
        "professional color grading, ray-traced reflections, hyper-detailed textures, "
        "temporal anti-aliasing, zero digital noise, clean pixels, "
        "smooth motion interpolation, high-fidelity physical interaction"
    )

    # --- INI DIA YANG KURANG: NEGATIVE BASE ---
    negative_base = (
        "muscular, bodybuilder, shredded, male anatomy, human skin, human anatomy, "
        "realistic flesh, skin pores, blurry, distorted surface, "
    )
    
    no_text_strict = (
        "STRICTLY NO text, NO typography, NO watermark, NO letters, NO subtitles, "
        "NO captions, NO speech bubbles, NO dialogue boxes, NO labels, NO black bars, "
        "NO burned-in text, NO characters speaking with visible words, "
        "the image must be a CLEAN cinematic shot without any written characters."
    )
    
    negative_motion_strict = (
        "STRICTLY NO morphing, NO extra limbs, NO distorted faces, NO teleporting objects, "
        "NO flickering textures, NO sudden lighting jumps, NO floating hair artifacts."
    )

    # HEADER UI
    c1, c_kosong, c2 = st.columns([2, 0.5, 1.5]) 
    with c1:
        st.markdown("# 🚀 RUANG PRODUKSI")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.success(f"🛰️ {nama_hari}, {tgl} {nama_bulan} | Staf: {user_aktif}")
    
    data = st.session_state.data_produksi
    ver = st.session_state.get("form_version", 0)

    # 1. INTEGRASI REFERENSI NASKAH
    if 'naskah_siap_produksi' in st.session_state and st.session_state.naskah_siap_produksi:
        with st.expander("📖 NASKAH REFERENSI PINTAR AI LAB", expanded=True):
            st.markdown(st.session_state.naskah_siap_produksi)
            if st.button("🗑️ Bersihkan Naskah Referensi", use_container_width=True):
                st.session_state.naskah_siap_produksi = ""
                st.rerun()

    # 2. IDENTITY LOCK
    with st.expander("🛡️ IDENTITY LOCK - Detail Karakter", expanded=False):
        data["jumlah_karakter"] = st.number_input("Jumlah Karakter", 1, 4, data["jumlah_karakter"], label_visibility="collapsed", key=f"num_char_{ver}")
        cols_char = st.columns(data["jumlah_karakter"])
        
        for i in range(data["jumlah_karakter"]):
            with cols_char[i]:
                st.markdown(f"👤 **Karakter {i+1}**")
                
                # --- LOGIKA AUTO-FILL ---
                nama_pilihan = st.selectbox("Pilih Karakter", list(MASTER_CHAR.keys()), key=f"sel_nama_{i}_{ver}", label_visibility="collapsed")
                pilih_versi = "Manual" 
                current_char = MASTER_CHAR[nama_pilihan]
                
                if nama_pilihan != "Custom":
                    list_versi = list(current_char["versi_pakaian"].keys())
                    pilih_versi = st.selectbox("Versi", list_versi, key=f"sel_ver_{i}_{ver}", label_visibility="collapsed")
                    
                    def_wear = current_char["versi_pakaian"][pilih_versi]
                    def_fisik = current_char["fisik"]
                    nama_final = nama_pilihan
                else:
                    def_wear = data["karakter"][i]["wear"]
                    def_fisik = data["karakter"][i]["fisik"]
                    nama_final = data["karakter"][i]["nama"]

                # --- INPUT WIDGET DENGAN ON_CHANGE (PENGUNCI DATA) ---
                data["karakter"][i]["nama"] = st.text_input(
                    "Nama", value=nama_final, 
                    key=f"char_nama_{i}_{ver}_{nama_pilihan}", 
                    on_change=simpan_ke_memori,
                    placeholder="Nama...", label_visibility="collapsed"
                )
                data["karakter"][i]["wear"] = st.text_input(
                    "Pakaian", value=def_wear, 
                    key=f"char_wear_{i}_{ver}_{nama_pilihan}_{pilih_versi}", 
                    on_change=simpan_ke_memori,
                    placeholder="Pakaian...", label_visibility="collapsed"
                )
                data["karakter"][i]["fisik"] = st.text_area(
                    "Ciri Fisik", value=def_fisik, 
                    key=f"char_fix_{i}_{ver}_{nama_pilihan}", 
                    on_change=simpan_ke_memori,
                    height=80, placeholder="Diisi detail fisik, jika tidak ada referensi gambar...", label_visibility="collapsed"
                )
    # 3. INPUT ADEGAN (LENGKAP: LIGHTING, RATIO, DLL)
    for s in range(data["jumlah_adegan"]):
        scene_id = s + 1
        if scene_id not in data["adegan"]:
            data["adegan"][scene_id] = {
                "aksi": "", "style": OPTS_STYLE[0], "light": OPTS_LIGHT[0], 
                "arah": OPTS_ARAH[0], "shot": OPTS_SHOT[0], "ratio": OPTS_RATIO[0], 
                "cam": OPTS_CAM[0], "loc": "", "dialogs": [""]*4
            }

        with st.expander(f"🎬 ADEGAN {scene_id}", expanded=(scene_id == 1)):
            col_text, col_set = st.columns([1.5, 1])
            with col_text:
                st.markdown('<p class="small-label">📸 NASKAH VISUAL & AKSI</p>', unsafe_allow_html=True)
                # Formatnya dibuat menurun supaya rapi dan tidak bingung
                data["adegan"][scene_id]["aksi"] = st.text_area(
                    f"Aksi_{scene_id}", 
                    value=data["adegan"][scene_id]["aksi"], 
                    height=230, 
                    key=f"act_{scene_id}_{ver}", 
                    label_visibility="collapsed",
                    on_change=simpan_ke_memori # <--- Cukup tempel ini di akhir
                )
            
            with col_set:
                # --- LOGIKA PENGAMAN INDEX (Mencegah ValueError) ---
                def get_index(option_list, current_val):
                    try:
                        return option_list.index(current_val)
                    except ValueError:
                        return 0 # Kembali ke pilihan pertama jika data lama tidak cocok

                # BARIS 1: STYLE & SHOT
                sub1, sub2 = st.columns(2)
                with sub1:
                    st.markdown('<p class="small-label">✨ STYLE</p>', unsafe_allow_html=True)
                    curr_s = data["adegan"][scene_id].get("style", OPTS_STYLE[0])
                    data["adegan"][scene_id]["style"] = st.selectbox(
                        f"S_{scene_id}", OPTS_STYLE, 
                        index=get_index(OPTS_STYLE, curr_s), 
                        key=f"mood_{scene_id}_{ver}", label_visibility="collapsed"
                    )
                with sub2:
                    st.markdown('<p class="small-label">🔍 UKURAN GAMBAR</p>', unsafe_allow_html=True)
                    curr_sh = data["adegan"][scene_id].get("shot", OPTS_SHOT[0])
                    data["adegan"][scene_id]["shot"] = st.selectbox(
                        f"Sh_{scene_id}", OPTS_SHOT, 
                        index=get_index(OPTS_SHOT, curr_sh), 
                        key=f"shot_{scene_id}_{ver}", label_visibility="collapsed"
                    )

                # BARIS 2: LIGHTING & ARAH KAMERA
                sub3, sub4 = st.columns(2)
                with sub3:
                    st.markdown('<p class="small-label">💡 LIGHTING & ATMOSPHERE</p>', unsafe_allow_html=True)
                    curr_l = data["adegan"][scene_id].get("light", OPTS_LIGHT[0])
                    data["adegan"][scene_id]["light"] = st.selectbox(
                        f"L_{scene_id}", OPTS_LIGHT, 
                        index=get_index(OPTS_LIGHT, curr_l), 
                        key=f"light_{scene_id}_{ver}", label_visibility="collapsed"
                    )
                with sub4:
                    st.markdown('<p class="small-label">📐 ARAH KAMERA</p>', unsafe_allow_html=True)
                    curr_a = data["adegan"][scene_id].get("arah", OPTS_ARAH[0])
                    data["adegan"][scene_id]["arah"] = st.selectbox(
                        f"A_{scene_id}", OPTS_ARAH, 
                        index=get_index(OPTS_ARAH, curr_a), 
                        key=f"arah_{scene_id}_{ver}", label_visibility="collapsed"
                    )

                # BARIS 3: GERAKAN & LOKASI
                sub5, sub6 = st.columns([1, 1.5])
                with sub5:
                    st.markdown('<p class="small-label">🎥 GERAKAN</p>', unsafe_allow_html=True)
                    curr_c = data["adegan"][scene_id].get("cam", OPTS_CAM[0])
                    data["adegan"][scene_id]["cam"] = st.selectbox(
                        f"C_{scene_id}", OPTS_CAM, 
                        index=get_index(OPTS_CAM, curr_c), 
                        key=f"cam_{scene_id}_{ver}", label_visibility="collapsed"
                    )
                with sub6:
                    st.markdown('<p class="small-label">📍 LOKASI</p>', unsafe_allow_html=True)
                    data["adegan"][scene_id]["loc"] = st.text_input(
                        f"Loc_{scene_id}", value=data["adegan"][scene_id]["loc"], 
                        key=f"loc_{scene_id}_{ver}", label_visibility="collapsed", 
                        placeholder="Lokasi...", on_change=simpan_ke_memori
                    )

            # --- DIALOG SECTION (SINKRONISASI IDENTITAS) ---
            cols_d = st.columns(data["jumlah_karakter"])
            for i in range(data["jumlah_karakter"]):
                with cols_d[i]:
                    # Ambil nama dan paksa jadi Kapital agar sinkron dengan Scan Karakter
                    raw_nama = data["karakter"][i]["nama"] or f"Karakter {i+1}"
                    char_n = raw_nama.upper()
                    
                    # Beri label Token agar kamu tahu ini akan jadi ACTOR_1, ACTOR_2, dst.
                    st.markdown(f'<p class="small-label" style="color:#FFA500;">🎭 {char_n} (ACTOR_{i+1})</p>', unsafe_allow_html=True)
                    
                    data["adegan"][scene_id]["dialogs"][i] = st.text_input(
                        f"D_{scene_id}_{i}", 
                        value=data["adegan"][scene_id]["dialogs"][i], 
                        key=f"d_{scene_id}_{i}_{ver}", 
                        label_visibility="collapsed",
                        placeholder=f"Ketik dialog {char_n}...",
                        on_change=simpan_ke_memori
                    )

# --- 4. GLOBAL COMPILER LOGIC ---
    st.markdown("---")
    if st.button("🚀 GENERATE SEMUA PROMPT", use_container_width=True, type="primary"):
        adegan_terisi = [s_id for s_id, isi in data["adegan"].items() if isi["aksi"].strip() != ""]
        if not adegan_terisi:
            st.error("⚠️ Isi NASKAH dulu!")
        else:
            user_nama = st.session_state.get("user_aktif", "User").capitalize()
            st.markdown(f"## 🎬 Hasil Prompt: {user_nama} ❤️")
            
            for scene_id in adegan_terisi:
                sc = data["adegan"][scene_id]
                v_text_low = sc["aksi"].lower()
                
                # A. SCAN KARAKTER
                found = []
                jml_kar = data.get("jumlah_karakter", 2)
                for i in range(jml_kar):
                    c = data["karakter"][i]
                    if c['nama'] and re.search(rf'\b{re.escape(c["nama"].lower())}\b', v_text_low):
                        found.append({"id": i+1, "nama": c['nama'].upper(), "wear": c['wear']})

                # B. RAKIT IDENTITAS & CUE (SOLUSI NAMEERROR)
                clean_parts = [f"[[ ACTOR_{m['id']}_SKS ({m['nama']}): refer to PHOTO #{m['id']} ONLY. WEAR: {m['wear']} ]]" for m in found]
                final_identity = " AND ".join(clean_parts) if clean_parts else "[[ IDENTITY: UNKNOWN ]]"
                
                # Logika Acting Cue Otomatis
                cue_parts = [f"[{m['nama']}]: Memberikan ekspresi akting yang mendalam dan emosional sesuai narasi adegan." for m in found]
                acting_cue_text = "\n".join(cue_parts) if cue_parts else "Neutral cinematic expression."

                # Dialog Sync
                list_dialog = [f"[ACTOR_{f['id']}_SKS ({f['nama']}) SPEAKING]: '{sc['dialogs'][f['id']-1]}'" for f in found if sc["dialogs"][f['id']-1].strip()]
                dialog_text = " | ".join(list_dialog) if list_dialog else "Silent interaction."

                # C. MASTER COMPILER (SINKRONISASI TOTAL: MINIMALIS & SAKTI)
                with st.expander(f"💎 MASTERPIECE RESULT | ADEGAN {scene_id}", expanded=True):
                    
                    # 1. Mantra VIDEO (Suntikan Brutal Sharpness f/11)
                    mantra_video = rakit_prompt_sakral(sc['aksi'], sc['style'], sc['light'], sc['arah'], sc['shot'], sc['cam'])
                    
                    # 2. Mantra IMAGE (Infinte Depth of Field)
                    style_map_img = {
                        "Sangat Nyata": "Cinematic RAW shot, PBR surfaces, 8k textures, tactile micro-textures, f/11 aperture, infinite depth of field.",
                        "Animasi 3D Pixar": "Disney style 3D, Octane render, ray-traced global illumination, premium subsurface scattering.",
                        "Gaya Cyberpunk": "Futuristic neon aesthetic, volumetric fog, sharp reflections, high contrast.",
                        "Anime Jepang": "Studio Ghibli style, hand-painted watercolor textures, soft cel shading, lush aesthetic."
                    }
                    s_img = style_map_img.get(sc['style'], "Cinematic optical clarity.")
                    mantra_statis = f"{s_img} {sc['shot']} framing, {sc['arah']} angle, razor-sharp optical focus, {sc['light']}."

                    # Logika Acting Cue Gaya Baru (ANTI-DIALOG DOBEL & LEBIH EKSPRESIF)
                    raw_dialogs = [f"[{data['karakter'][i]['nama'].upper()}]: '{sc['dialogs'][i].strip()}'" for i in range(data["jumlah_karakter"]) if sc['dialogs'][i].strip()]
                    
                    emotional_ref = " | ".join(raw_dialogs) if raw_dialogs else "No dialogue, focus on cinematic body language."
                    
                    acting_cue_custom = (
                        f"ACTING RULE: {emotional_ref}. "
                        "Identify the speaker by name and sync lip movement perfectly. "
                        "Non-speaking characters must maintain natural idle facial expressions (blinking, slight head tilts)."
                    )


                    # RAKIT PROMPT GAMBAR
                    img_p = (
                        f"IMAGE REFERENCE RULE: Use uploaded photos for each character. Interaction required.\n"
                        f"{final_identity}\n"
                        f"SCENE: {sc['aksi']}\n"
                        f"LOCATION: {sc['loc']}\n"
                        f"VISUAL: {mantra_statis} NO SOFTENING, extreme edge-enhancement.\n"
                        f"QUALITY: {QB_IMG}\n"
                        f"NEGATIVE: {negative_base} {no_text_strict}\n"
                        f"FORMAT: 9:16 Vertical Framing"
                    )


                    # RAKIT PROMPT VIDEO (DIBERSIHKAN DARI DIALOG DOBEL)
                    vid_p = (
                        f"IMAGE REFERENCE RULE: Refer to PHOTO #1 for ACTOR_1, PHOTO #2 for ACTOR_2, etc.\n"
                        f"{final_identity}\n"
                        f"SCENE: {sc['aksi']} in {sc['loc']}. Motion: {sc['cam']}.\n"
                        f"PHYSICS: High-fidelity clothing simulation, natural hair physics, no clipping.\n"
                        f"ACTING: {acting_cue_custom}\n"            
                        f"VISUAL: {mantra_video} 8k UHD, clean textures.\n"
                        f"NEGATIVE: {negative_base} {no_text_strict} {negative_motion_strict}\n"
                        f"FORMAT: 9:16 Vertical Video"
                    )

                    c1, c2 = st.columns(2)
                    with c1: 
                        st.markdown("📷 **PROMPT GEMINI**")
                        st.code(img_p, language="text")
                    with c2: 
                        st.markdown("🎥 **PROMPT VEO**")
                        st.code(vid_p, language="text")

                st.markdown('<div style="margin-bottom: -15px;"></div>', unsafe_allow_html=True)
                
# ==============================================================================
# BAGIAN 7: PENGENDALI UTAMA
# ==============================================================================
def utama():
    inisialisasi_keamanan() 
    pasang_css_kustom() # Tambahkan ini agar CSS kamu langsung aktif saat login
    
    if not cek_autentikasi():
        tampilkan_halaman_login()
    else:
        # Panggil Sidebar & Menu setelah login berhasil
        menu = tampilkan_navigasi_sidebar()
        
        # Logika Menu
        if menu == "🚀 RUANG PRODUKSI": tampilkan_ruang_produksi()
        elif menu == "🧠 PINTAR AI LAB": tampilkan_ai_lab()
        elif menu == "💡 GUDANG IDE": tampilkan_gudang_ide()
        elif menu == "📋 TUGAS KERJA": tampilkan_tugas_kerja()
        elif menu == "⚡ KENDALI TIM": tampilkan_kendali_tim()

# --- BAGIAN PALING BAWAH ---
if __name__ == "__main__":
    utama()



