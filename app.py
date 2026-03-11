import streamlit as st
import requests  
import pandas as pd
import gspread 
import time
import pytz
import json
import re
import random
import plotly.express as px
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from supabase import create_client, Client

st.set_page_config(page_title="PINTAR MEDIA | Studio", layout="wide")

# ==============================================================================
# KONFIGURASI DASAR & KONEKSI (STABIL & HEMAT KUOTA)
# ==============================================================================
URL_MASTER = "https://docs.google.com/spreadsheets/d/16xcIqG2z78yH_OxY5RC2oQmLwcJpTs637kPY-hewTTY/edit?usp=sharing"

# --- 1. KONEKSI SUPABASE ---
url: str = st.secrets["supabase"]["url"]
key: str = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# --- 2. KONEKSI GSHEET (DI-CACHE BIAR RAMAH RAM) ---
@st.cache_resource
def get_gspread_sh():
    """Koneksi Google Sheets yang disimpan di RAM."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_url(URL_MASTER)

# --- 3. FUNGSI BACKUP GSHEET (YANG TADI ILANG) ---
def ambil_data_beneran_segar(nama_sheet):
    """Fungsi asli narik data langsung ke GSheet (Backup kalau Supabase mati)."""
    try:
        sh = get_gspread_sh()
        ws = sh.worksheet(nama_sheet)
        data = ws.get_all_records()
        # Kita kembalikan DataFrame yang sudah dibersihkan
        return bersihkan_data(pd.DataFrame(data))
    except Exception as e:
        print(f"GSheet Backup Error: {e}")
        return pd.DataFrame()

import calendar

@st.cache_data(ttl=60) 
def ambil_data_segar(target, bulan_pilihan=None, tahun_pilihan=None):
    try:
        tz_wib = pytz.timezone('Asia/Jakarta')
        skrg = datetime.now(tz_wib)
        bln = int(bulan_pilihan) if bulan_pilihan else skrg.month
        thn = int(tahun_pilihan) if tahun_pilihan else skrg.year
        
        # Logika Tanggal Akhir yang Akurat (Anti-Error Februari)
        last_day = calendar.monthrange(thn, bln)[1]
        tgl_awal = f"{thn}-{bln:02d}-01"
        tgl_akhir = f"{thn}-{bln:02d}-{last_day}" 

        query = supabase.table(target).select("*")
        
        if target == "Gudang_Ide":
            res = query.eq("STATUS", "Tersedia").order("ID_IDE", desc=True).execute()
        elif target == "Tugas":
            # Pakai Deadline sesuai dashboard kamu
            res = query.gte("Deadline", tgl_awal).lte("Deadline", tgl_akhir).order("id", desc=True).execute()
        elif target in ["Arus_Kas", "Absensi"]:
            res = query.gte("Tanggal", tgl_awal).lte("Tanggal", tgl_akhir).order("id", desc=True).execute()
        elif target == "Log_Aktivitas":
            res = query.order("Waktu", desc=True).limit(300).execute()
        else:
            res = query.execute()
            
        df = pd.DataFrame(res.data)
        if not df.empty:
            if 'id' in df.columns: df = df.drop(columns=['id'])
            return bersihkan_data(df)
        
        # JIKA SUPABASE KOSONG: 
        # Cek apakah ini pencarian bulan spesifik? 
        # Kalau iya, jangan asal lari ke GSheet (kecuali GSheet-nya juga disaring)
        if bulan_pilihan:
            return pd.DataFrame() # Kembalikan kosong agar muncul 'st.info'
            
        return ambil_data_beneran_segar(target) 
    except Exception as e:
        return ambil_data_beneran_segar(target)

# --- 5. FUNGSI PEMBERSIH DATA ---
def bersihkan_data(df):
    """Standardisasi data biar Python gak pusing (Versi Anti-NAN)."""
    if df.empty: return df
    df = df.dropna(how='all')
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.fillna('')
    kolom_krusial = ['NAMA', 'STAF', 'STATUS', 'USERNAME', 'TANGGAL', 'DEADLINE', 'TIPE']
    for col in df.columns:
        if col in kolom_krusial:
            df[col] = df[col].astype(str).str.strip().str.upper()
            df[col] = df[col].replace(['NAN', 'NONE', '<NA>'], '')
    return df

def tambah_log(user, aksi):
    """Mencatat aktivitas ke Supabase (Utama) & GSheet (Backup)."""
    if str(user).upper() == "DIAN": 
        return # Langsung keluar, tidak mencatat apa-apa kalau itu Dian

    try:
        tz_wib = pytz.timezone('Asia/Jakarta')
        # Pake format ini biar rapi kayak data lama lo di screenshot
        waktu_sekarang = datetime.now(tz_wib).strftime("%d/%m/%Y %H:%M:%S")
        
        # 1. KIRIM KE SUPABASE
        # 'Nama' diganti 'User' karena di database lo kolomnya itu
        supabase.table("Log_Aktivitas").insert({
            "Waktu": waktu_sekarang,
            "User": str(user).upper(),
            "Aksi": aksi
        }).execute()

        # 2. KIRIM KE GSHEET (Backup pasif)
        try:
            sh = get_gspread_sh()
            ws_log = sh.worksheet("Log_Aktivitas")
            ws_log.append_row([waktu_sekarang, str(user).upper(), aksi])
        except: 
            pass 

    except Exception as e:
        print(f"Gagal mencatat log: {e}")
        
# ==============================================================================
# 6. SETUP DATABASE HYBRID (SUPABASE + GSHEET BACKUP)
# ==============================================================================

def load_data_channel():
    """Narik data murni dari Supabase (Instan & Tajam)."""
    try:
        res = supabase.table("Channel_Pintar").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            return bersihkan_data(df)
        return pd.DataFrame(columns=["TANGGAL", "EMAIL", "STATUS", "HP"])
    except Exception as e:
        st.error(f"❌ Emergency: Supabase Error! {e}")
        return pd.DataFrame(columns=["TANGGAL", "EMAIL", "STATUS", "HP"])

@st.cache_data(ttl=600)
def load_data_hp():
    """Load data unit HP dari Supabase."""
    try:
        res = supabase.table("Data_HP").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame(columns=["NAMA_HP", "NOMOR_HP", "PROVIDER", "MASA_AKTIF"])

def simpan_perubahan_channel(df_edited, user_aktif):
    """VERSI FULL SUPABASE: Sekali klik langsung masuk, gak pake lama."""
    try:
        tz = pytz.timezone('Asia/Jakarta')
        tgl_now = datetime.now(tz).strftime("%d/%m/%Y %H:%M")
        
        # --- UPDATE SUPABASE (MASAL) ---
        # Satu request beres buat semua baris!
        data_to_supabase = df_edited.to_dict(orient='records')
        supabase.table("Channel_Pintar").upsert(data_to_supabase, on_conflict="EMAIL").execute()
        
        st.cache_data.clear()
        return True 

    except Exception as e:
        st.error(f"❌ Gagal Simpan Utama (Supabase): {e}")
        return False
        
# ==============================================================================
# BAGIAN 1: PUSAT KENDALI OPSI (VERSI TAJAM f/16 & GERAKAN NATURAL)
# ==============================================================================
OPTS_STYLE = ["Sangat Nyata", "Animasi 3D Pixar", "Gaya Cyberpunk", "Anime Jepang"]
OPTS_LIGHT = ["Senja Cerah (Golden)", "Studio Bersih", "Neon Cyberpunk", "Malam Indigo", "Siang Alami"]
OPTS_ARAH  = ["Sejajar Mata", "Dari Atas", "Dari Bawah", "Dari Samping", "Berhadapan"]
OPTS_SHOT  = ["Sangat Dekat", "Wajah & Bahu", "Setengah Badan", "Seluruh Badan", "Drone (Jauh)"]
OPTS_CAM   = ["Diam (Tetap Napas)", "Maju Perlahan", "Ikuti Karakter", "Memutar", "Goyang (Handheld)"]
OPTS_RATIO = ["9:16", "16:9", "1:1"]

def rakit_prompt_sakral(aksi, style, light, arah, shot, cam):
    style_map = {
        "Sangat Nyata": "Cinematic RAW shot, PBR surfaces, 8k textures, tactile micro-textures, f/16 aperture, infinite depth of field, pan-focal clarity, zero background blur.",
        "Animasi 3D Pixar": "Disney style 3D, Octane render, ray-traced global illumination, premium subsurface scattering.",
        "Gaya Cyberpunk": "Futuristic neon aesthetic, volumetric fog, sharp reflections, high contrast.",
        "Anime Jepang": "Studio Ghibli style, hand-painted watercolor textures, soft cel shading, lush aesthetic."
    }
    
    light_map = {
        "Senja Cerah (Golden)": "Late afternoon sun, soft amber glow, natural warm white balance, long soft shadows, reduced orange saturation.",
        "Studio Bersih": "Professional studio setup, rim lighting, clean shadows, commercial photography look.",
        "Neon Cyberpunk": "Vibrant pink and blue rim light, deep noir shadows, cinematic volumetric lighting.",
        "Malam Indigo": "Cinematic night, moonlight shading, deep indigo tones, clean silhouettes.",
        "Siang Alami": "Soft diffused daylight, overcast sky lighting, no harsh shadows, neutral color temperature, gentle ambient illumination."
    }

    s_cmd = style_map.get(style, "Cinematic optical clarity.")
    l_cmd = light_map.get(light, "Balanced exposure.")
    
    # --- UPDATE: Ganti "cinematic optical" jadi "high-fidelity natural" biar gerakan ga kaku/slowmo ---
    tech_logic = f"{shot} framing, {arah} angle, {cam} motion, high-fidelity natural movement, zero motion blur."

    return f"{s_cmd} {tech_logic} {l_cmd}"
    
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


# ==============================================================================
# FUNGSI ABSENSI OTOMATIS (MESIN ABSEN) - VERSI KASTA OWNER VIP + SUPABASE
# ==============================================================================
def log_absen_otomatis(nama_user):
    """Mesin Absen Otomatis: Anti-Double Input ke Supabase & GSheet."""
    
    # 1. SATPAM UTAMA: Jangan jalan kalau belum login!
    if not st.session_state.get('sudah_login', False):
        return

    # 2. CEK SESSION: Kalau sudah absen di turn ini, langsung balik kanan
    if st.session_state.get('absen_done_today', False):
        return

    # 3. FILTER OWNER / TAMU (KEBAL ABSENSI)
    user_level = st.session_state.get("user_level", "STAFF")
    if user_level == "OWNER" or str(nama_user).lower() == "tamu":
        st.session_state.absen_done_today = True
        return
    
    tz_wib = pytz.timezone('Asia/Jakarta')
    waktu_skrg = datetime.now(tz_wib)
    jam = waktu_skrg.hour
    tgl_skrg = waktu_skrg.strftime("%Y-%m-%d")
    jam_skrg = waktu_skrg.strftime("%H:%M")

    # 4. RANGE JAM OPERASIONAL ABSENSI (08:00 - 17:59)
    if 8 <= jam < 18: 
        try:
            nama_up = str(nama_user).upper().strip()
            
            # Cek Supabase (Safety Check Terakhir)
            res = supabase.table("Absensi").select("id").eq("Nama", nama_up).eq("Tanggal", tgl_skrg).execute()
            
            if len(res.data) == 0:
                # --- [PENTING] GEMBOK PROSES DI SINI ---
                # Set True SEBELUM insert biar kalau ada rerun pas proses, gak tembus lagi
                st.session_state.absen_done_today = True 
                
                # Logika Telat (Jam 10:01 ke atas = Telat)
                menit_total = waktu_skrg.hour * 60 + waktu_skrg.minute
                if menit_total <= 600: # 10:00 pagi
                    status_final = "HADIR"
                else:
                    status_final = f"TELAT ({jam_skrg})"
                
                # A. KIRIM KE SUPABASE
                supabase.table("Absensi").insert({
                    "Nama": nama_up, 
                    "Tanggal": tgl_skrg, 
                    "Jam Masuk": jam_skrg, 
                    "Status": status_final
                }).execute()

                # B. KIRIM KE GSHEET (Backup)
                try:
                    sh = get_gspread_sh() 
                    sheet_absen = sh.worksheet("Absensi")
                    sheet_absen.append_row([nama_up, tgl_skrg, jam_skrg, status_final])
                except Exception as e_gsheet:
                    # Kalau GSheet gagal, log aja tapi jangan bikin aplikasi mati
                    print(f"GSheet Gagal: {e_gsheet}")
                
                # Toast & Refresh
                st.toast(f"⏰ Absen Berhasil (Jam {jam_skrg})", icon="✅")
                time.sleep(1.5) # Kasih jeda biar user liat toast
                st.rerun() 
            else:
                # Kalau ternyata sudah ada datanya di Supabase, kunci session
                st.session_state.absen_done_today = True

        except Exception as e:
            # Jika error, reset session biar bisa coba lagi
            st.session_state.absen_done_today = False
            st.error(f"Sistem Absen Error: {e}")
    else:
        st.toast(f"Akses Malam/Lembur (Absen Tutup).", icon="🌙")
            
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

# ==============================================================================
# SISTEM AUTENTIKASI (LOGIN/LOGOUT) - VERSI SINKRON CLOUD
# ==============================================================================
def proses_login(user, pwd):
    try:
        # Pake ambil_data_segar biar sinkron sama Supabase/Sheet Staff
        df_staff = ambil_data_segar("Staff")
        
        if df_staff.empty:
            st.error("Database Staff tidak terbaca.")
            return

        # Standarisasi kolom & input (Paksa UPPER biar sinkron sama GSheet)
        df_staff.columns = [str(c).strip().upper() for c in df_staff.columns]
        u_input = str(user).strip().upper()
        p_input = str(pwd).strip()

        # Cari user di database
        user_row = df_staff[df_staff['NAMA'] == u_input]

        if not user_row.empty:
            # --- INI TETEP ADA (WAJIB) ---
            pwd_sheet = str(user_row.iloc[0]['PASSWORD']).strip()
            user_level = str(user_row.iloc[0]['LEVEL']).strip().upper()
            
            if pwd_sheet == p_input:
                # --- 1. SET STATUS LOGIN ---
                st.session_state.sudah_login = True
                user_key = u_input
                st.session_state.user_aktif = user_key
                st.session_state.waktu_login = datetime.now()

                # --- 2. KUNCI KASTA OWNER (CEK DULU) ---
                if user_key == "DIAN":
                    st.session_state.user_level = "OWNER"
                else:
                    st.session_state.user_level = user_level

                # --- 3. FILTER LOG (BARU PANGGIL DI SINI) ---
                if user_key != "DIAN":
                    tambah_log(user_key, "LOGIN KE SISTEM")

                current_lv = st.session_state.user_level

                # --- 3. LOGIKA ABSEN & NOTIF ---
                if current_lv in ["STAFF", "ADMIN"]:
                    log_absen_otomatis(user_key)
                    st.toast(f"Selamat bekerja, {user_key}!", icon="✅")
                else:
                    st.toast(f"Mode VIP Aktif: {user_key}", icon="👑")

                # --- 4. BERSIHKAN URL & REFRESH ---
                st.query_params.clear() 
                time.sleep(1) 
                st.rerun()
            else:
                st.error("Password salah.")
        else:
            st.error("Username tidak terdaftar.")

    except Exception as e:
        st.error(f"Sistem Login Error: {e}")

def tampilkan_halaman_login():
    # Gunakan Container agar tidak berantakan di HP
    with st.container():
        st.markdown("<br><br>", unsafe_allow_html=True)
        col_l, col_m, col_r = st.columns([1.5, 1, 1.5]) 
        
        with col_m:
            try:
                st.image("PINTAR.png", use_container_width=True)
            except:
                st.markdown("<h2 style='text-align:center;'>PINTAR MEDIA</h2>", unsafe_allow_html=True)
            
            # Key unik agar tidak bentrok
            with st.form("login_station", clear_on_submit=False):
                u = st.text_input("Username", placeholder="Username...", key="input_u").lower()
                p = st.text_input("Password", type="password", placeholder="Password...", key="input_p")
                submit = st.form_submit_button("MASUK KE SISTEM 🚀", use_container_width=True)
                
                if submit: 
                    if u.strip() and p.strip():
                        proses_login(u, p)
                    else:
                        st.warning("Isi dulu Bos!")

def cek_autentikasi():
    if st.session_state.get('sudah_login', False):
        if 'waktu_login' in st.session_state:
            durasi = datetime.now() - st.session_state.waktu_login
            if durasi > timedelta(hours=10):
                proses_logout()
                return False
        return True
    return False

def proses_logout():
    # Ambil nama user aktif, default 'unknown' kalau tidak ada
    u = st.session_state.get("user_aktif", "unknown")
    
    # --- OWNER STEALTH MODE (LOGOUT) ---
    # Cek dulu, kalau bukan DIAN baru catat ke CCTV
    if str(u).upper() != "DIAN":
        tambah_log(u, "LOGOUT / KELUAR SISTEM")
    
    # Hapus semua session state agar bersih total
    for key in list(st.session_state.keys()):
        del st.session_state[key]
        
    st.query_params.clear()
    st.rerun()
    
# FUNGSI BACKUP (Fokus GSheet lewat Secrets)
def simpan_ke_gsheet():
    try:
        sh = get_gspread_sh() 
        sheet = sh.sheet1 
        
        tz_wib = pytz.timezone('Asia/Jakarta')
        waktu = datetime.now(tz_wib).strftime("%d/%m/%Y %H:%M:%S")
        user = st.session_state.get("user_aktif", "STAFF").upper() 
        data_json = json.dumps(st.session_state.data_produksi)
        
        # --- 1. CEK APAKAH USER SUDAH PERNAH BACKUP? ---
        # Kita ambil semua nama di kolom A
        semua_user = sheet.col_values(1) 
        
        if user in semua_user:
            # 2. KALAU SUDAH ADA, KITA UPDATE (NIMPA)
            # index + 1 karena list python mulai dari 0, tapi baris GSheet mulai dari 1
            row_index = semua_user.index(user) + 1
            
            # Kita cuma update kolom B (Waktu) dan C (Data Naskah)
            # Formatnya: [[Data Kolom B, Data Kolom C]]
            sheet.update(f"B{row_index}:C{row_index}", [[waktu, data_json]])
            
            msg = "🔄 Cloud Backup Berhasil Diperbarui!"
        else:
            # 3. KALAU BELUM ADA, BARU TAMBAH BARIS BARU
            sheet.append_row([user, waktu, data_json])
            msg = "🚀 Baris Baru Dibuat & Tersimpan di Cloud!"
            
        st.toast(msg, icon="☁️")
        
    except Exception as e:
        st.error(f"Gagal Simpan Cloud: {e}")

def muat_dari_gsheet():
    try:
        sh = get_gspread_sh()
        sheet = sh.sheet1
        user_up = st.session_state.get("user_aktif", "").upper()
        
        try:
            cell = sheet.find(user_up)
            row_data = sheet.row_values(cell.row)
            naskah_mentah = row_data[2] if len(row_data) >= 3 else None
        except:
            st.warning(f"⚠️ Data untuk {user_up} tidak ditemukan di Cloud.")
            return

        if naskah_mentah:
            try:
                # Perbaikan: Validasi apakah ini beneran JSON?
                data_termuat = json.loads(naskah_mentah)
            except json.JSONDecodeError:
                st.error("❌ Data di Cloud rusak (Format JSON Ilegal). Hubungi Admin.")
                return
            
            # Logika restrukturisasi adegan tetap sama...
            if "adegan" in data_termuat:
                adegan_baru = {}
                for k, v in data_termuat["adegan"].items():
                    # Bersihkan junk
                    for junk in ["ekspresi", "cuaca", "vibe", "ratio"]:
                        v.pop(junk, None)
                    adegan_baru[int(k)] = v 
                data_termuat["adegan"] = adegan_baru
            
            st.session_state.data_produksi = data_termuat
            st.session_state.form_version = st.session_state.get('form_version', 0) + 1
            st.success(f"🔄 Data {user_up} Berhasil Dipulihkan!")
            st.rerun()
        else:
            st.error("⚠️ Data ditemukan, tapi kolom naskah kosong.")

    except Exception as e: # <--- PENUTUP Pintu 1 (Ini yang tadi hilang!)
        st.error(f"Gagal memuat dari Cloud: {e}")
        
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

        </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# BAGIAN 4: NAVIGASI SIDEBAR (VERSI CLOUD ONLY)
# ==============================================================================
def tampilkan_navigasi_sidebar():
    # Ambil level user dari session state (Default ke STAFF jika tidak ada)
    user_level = st.session_state.get("user_level", "STAFF")
    
    with st.sidebar:
        # 1. JUDUL DENGAN IKON
        st.markdown("""
            <div style='display: flex; align-items: center; margin-bottom: 10px; margin-top: 10px;'>
                <span style='font-size: 20px; margin-right: 10px;'>🖥️</span>
                <span style='font-size: 14px; color: white; font-weight: bold; letter-spacing: 1px;'>
                    MAIN COMMAND
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        # 2. LOGIKA FILTER MENU
        # Daftar menu dasar untuk semua orang
        menu_list = [
            "🚀 RUANG PRODUKSI", 
            "🧠 PINTAR AI LAB", 
            "💡 GUDANG IDE", 
            "📋 TUGAS KERJA",
            "📱 DATABASE CHANNEL", # Menu baru (Besok kita isi dagingnya)
            "📘 AREA STAF"         # Menu baru (Fokus kita sekarang)
        ]
        
        # OWNER dan ADMIN bisa lihat menu Kendali Tim
        if user_level in ["OWNER", "ADMIN"]:
            menu_list.append("⚡ KENDALI TIM")

        pilihan = st.radio(
            "COMMAND_MENU",
            menu_list,
            label_visibility="collapsed"
        )
        
        # 3. GARIS PEMISAH
        st.markdown("<hr style='margin: 20px 0; border-color: #30363d;'>", unsafe_allow_html=True)
        
        # 4. KOTAK DURASI FILM
        st.markdown("<p class='small-label'>🎬 DURASI FILM (ADEGAN)</p>", unsafe_allow_html=True)
        st.session_state.data_produksi["jumlah_adegan"] = st.number_input(
            "Jumlah Adegan", 1, 50, 
            value=st.session_state.data_produksi["jumlah_adegan"],
            label_visibility="collapsed"
        )
        
        # 5. SISTEM DATABASE CLOUD
        st.markdown("<p class='small-label'>☁️ CLOUD DATABASE (GSHEET)</p>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 BACKUP", use_container_width=True): 
                simpan_ke_gsheet()
        with col2:
            if st.button("🔄 RESTORE", use_container_width=True): 
                muat_dari_gsheet()
                
        st.markdown('<div style="margin-top: 50px;"></div>', unsafe_allow_html=True)   
        
        if st.button("⚡ KELUAR SISTEM", use_container_width=True):
            proses_logout()
        
        user = st.session_state.get("user_aktif", "USER").upper()
        # Kita tampilkan levelnya di footer biar kamu gampang ngecek
        st.markdown(f'''
            <div style="border-top: 1px solid #30363d; padding-top: 15px; margin-top: 10px;">
                <p class="status-footer">
                    🛰️ STATION: {user}_SESSION<br>
                    🟢 STATUS: {user_level}
                </p>
            </div>
        ''', unsafe_allow_html=True)
        
    return pilihan

def tampilkan_ai_lab():
    # --- 1. PINTU UTAMA: MANAJEMEN & STAFF ---
    user_sekarang = st.session_state.get("user_aktif", "tamu").lower()
    user_level = st.session_state.get("user_level", "ADMIN").upper()

    # Tambahin "STAFF" ke dalam list izin
    if user_level not in ["OWNER", "ADMIN"]:
        st.error("🚫 Maaf, Area Terbatas.")
        st.stop()

    st.title("🧠 PINTAR AI LAB")

    t_anatomi, t_grandma, t_transform, t_random = st.tabs(["🦴 ANATOMY", "👵 GRANDMA", "⚡ TRANSFORMATION", "🎲 RANDOM"])

    # ==========================================================================
    # TAB: ANATOMY (SULTAN AUTO-PILOT)
    # ==========================================================================
    with t_anatomi:
        # --- 2. MASTER DATA (DNA & AUDIO KONSISTEN) ---
        MASTER_CHAR_LAB = {
            "BALUNG": {
                "fisik": (
                    "FORENSIC PHOTOGRAPHY STYLE. A clean white anatomical human skeleton clearly visible "
                    "underneath a THIN, HIGHLY TRANSPARENT, and crystal-clear dermal membrane. "
                    "The flesh layer is sleek and thin, hugging the bones closely like a glass-like skin. "
                    "NO INTERNAL ORGANS inside, just the skeleton. The surface has realistic skin pores "
                    "but minimal glow, showing a matte-natural finish with subtle anatomical details. "
                    "Movement Physics: The thin transparent skin stretches and tightens realistically "
                    "over the skeletal joints during motion, with no excessive lighting or bloom."
                ),
                "pakaian": {
                    "Original": "Pure anatomical look, no clothes. Clear deep view of the white skeleton through thick transparent flesh.",
                    "Jas Lab Putih": "Professional white cotton lab coat. The fabric moves naturally over the thick transparent skeletal frame.",
                    "Baju Koko + Peci": "Wearing a clean white embroidered Baju Koko, a black velvet Peci (songkok) on the transparent skull, and a neat plaid Sarung. The clothes drape realistically over the gel-skin.",
                    "Jubah Kerajaan": "Royal crimson velvet tunic with gold embroidery. Heavy fabric showing realistic weight.",
                    "Baju Kantoran": "Crisp white button-up shirt and charcoal trousers. Sharp fabric textures reacting to skeletal motion.",
                    "Hoodie Hitam": "Oversized heavyweight black fleece hoodie. Soft matte texture folds around the thick transparent neck.",
                    "Versi Sultan": "Charcoal three-piece suit with gold brocade. Luxury materials with realistic light refractions."
                }
            },
            "BALUNG ORGAN": {
                "fisik": (
                    "NATIONAL GEOGRAPHIC FORENSIC STYLE. A clean human skeleton encased in a "
                    "THIN, SLEEK, and highly transparent dermal membrane. THE FLESH IS TIGHT "
                    "and hugs the skeletal structure closely with no excessive volume. "
                    "FULL INTERNAL ORGANS (heart, lungs, liver) are clearly visible deep inside the torso. "
                    "The organs exhibit a VERY SUBTLE, low-intensity internal glow, purely "
                    "contained within the tissues with NO EXTERNAL BLOOM or lens flare. "
                    "The white bones and organs are visible through the crystal-clear, "
                    "matte-finish transparent skin. Movement Physics: The thin skin layer "
                    "stretches realistically over the ribcage and organs during motion."
                ),
                "pakaian": {
                    "Original": "Pure anatomical look, no clothes. The glowing internal organs are visible through the thick clear volume.",
                    "Jas Lab Putih": "Professional white lab coat. The subtle bioluminescent glow of the organs is visible through the fabric.",
                    "Baju Koko + Peci": "Wearing a modest white Baju Koko, a black Peci on the glowing head, and a traditional Sarung. The internal bioluminescence subtly lights up the white shirt from within.",
                    "Jubah Kerajaan": "Royal crimson velvet. The glow from the chest organs creates a faint atmospheric light on the collar.",
                    "Baju Kantoran": "Sharp white shirt. The internal organ glow is subtly visible through the thin white fabric.",
                    "Hoodie Hitam": "Premium black hoodie. The glow is hidden except for the neck and face area.",
                    "Versi Sultan": "Luxury gold-brocade suit. Light refractions from the suit interact with the internal organ glow."
                }
            }
        }

        # --- 3. MASTER AUDIO LAB (NARRATOR: HUMAN-LIKE PRECISION) ---
        MASTER_AUDIO_LAB = {
            "Tipe": [
                "Pria (40th) - Gravely Baritone, Cinematic Raw (Gravely texture, audible inhales, Nat-Geo style)",
                "Pria (30th) - Sharp Tenor, Forensic Edge (Sharp articulation, subtle vocal fry, cold narrator)",
                "Wanita (35th) - Smoky & Mysterious (Smoky voice, slow cadence, heavy breathing tension)",
                "Pria (55th) - Weathered Old Master (Wisdom-heavy, husky, raspy texture, natural micro-pauses)",
                "Wanita (28th) - Clinical Precision (Professional, breathy, rhythmic clinical tone)",
                "Pria (30th) - Gritty Thriller (Sinis, low-pitched, raspy, provocative human tone)"
            ],
            "Aksen": [
                "Indonesia Formal (Standard Nat-Geo style with natural human inflections)",
                "Indonesia Narrative (Storytelling style, rhythmic flow, realistic dental sibilance)",
                "Melayu Klasik (Poetic, rhythmic, authentic human pauses)",
                "Technical/Medical (Precise, neutral but audible exhales between terms)",
                "Western-Lilt Indonesian (International style, realistic mouth clicks, subtle lilt)"
            ],
            "Mood": [
                "Cinematic & Dynamic (High emphasis, dramatic pauses, energetic human delivery)",
                "Dark & Intense (Low-pitched, atmospheric, heavy-breathing tension, 1x speed)",
                "Factual & Direct (Fast-paced, high clarity, audible micro-inhales)",
                "Emotional & Poetic (Soft, melodic flow, shaky breath, steady but raw delivery)",
                "High Pressure (Urgent, rapid delivery, breathy intensity, panicky human tone)"
            ]
        }

        # --- 3. AUTO-MAPPING LOGIC (ULTRA-WIDE DEFAULT) ---
        def auto_visual_mapping(prompt_teks):
            p = prompt_teks.lower()
            
            # --- DEFAULT: PEMANDANGAN LUAS + KAKI UTUH ---
            # Menggunakan 'Extreme Wide Shot' untuk background luas
            # Menggunakan 'Full Body' agar kaki tidak kepotong
            frame = "Wide Shot, Full Body standing figure, head to toe visible" 
            gerak = "Static camera" 
            
            # LOGIKA KATA KUNCI
            if any(x in p for x in ["medium", "setengah badan", "dada", "perut", "waist up"]):
                frame = "Medium Shot (Waist Up)"
            elif any(x in p for x in ["close up", "sangat dekat", "extreme", "detail", "macro", "wajah"]):
                frame = "Extreme Close-up"
                
            if any(x in p for x in ["zoom", "muter", "orbit", "dolly", "maju", "mundur", "pull-back", "camera moves"]):
                gerak = "Dynamic Motion (Orbit/Dolly)"
            
            return frame, gerak

        # --- 4. FETCH DATA FROM SUPABASE ---
        df_ide = pd.DataFrame()
        try:
            q = "or(and(status.eq.READY,locked_by.is.null),and(status.eq.PROCESSING,locked_by.eq.OWNER))"
            res = supabase.table("ide_pintar").select("*").or_(q).execute()
            df_ide = pd.DataFrame(res.data)
        except: pass

        topik_list = ["-- MODE MANUAL --"]
        if not df_ide.empty:
            topik_list += df_ide.drop_duplicates('topik')['topik'].tolist()
        topik_sel = st.selectbox("📥 Pilih Project (Anatomy):", topik_list)

        current_row = {}
        if topik_sel != "-- MODE MANUAL --":
            df_active = df_ide[df_ide['topik'] == topik_sel].sort_values('no_adegan')
            if not df_active.empty:
                current_row = df_active.iloc[0].to_dict()
                if current_row['status'] == 'READY':
                    supabase.table("ide_pintar").update({"status":"PROCESSING", "locked_by":"OWNER"}).eq("id", current_row['id']).execute()

        # --- 5. PRODUCTION BOARD (MULTI-CHARACTER & SULTAN AUDIO) ---
        with st.expander("🛠️ PINTAR BALUNG ENGINE", expanded=True):
            
            # --- VIEW MASTER SCRIPT ---
            st.markdown('<p class="small-label">🎙️ NASKAH FULL VO (MASTER SCRIPT)</p>', unsafe_allow_html=True)
            
            full_script = ""
            if current_row:
                try:
                    res_vo = supabase.table("ide_pintar").select("narasi_vo").eq("id_ide", current_row['id_ide']).order("no_adegan").execute()
                    if res_vo.data:
                        full_script = " ".join([str(r['narasi_vo']) for r in res_vo.data])
                except: 
                    pass
            
            # --- TEXT AREA DENGAN PLACEHOLDER SULTAN ---
            placeholder_text = (
                "Gunakan naskah ini untuk pengisian Voice Over secara utuh (Storytelling Mode)."
            )
            
            st.text_area(
                "MASTER_VO", 
                value=full_script, 
                height=100, 
                placeholder=placeholder_text,
                label_visibility="collapsed"
            )

            st.divider()

            # --- ROW 1: KARAKTER UTAMA & DNA ---
            col_char, col_dna = st.columns([1, 2])
            with col_char:
                st.markdown('<p class="small-label">👤 KARAKTER UTAMA</p>', unsafe_allow_html=True)
                char_pilih = st.selectbox("C_P", list(MASTER_CHAR_LAB.keys()), index=0, label_visibility="collapsed")
                
                outfit_opt = list(MASTER_CHAR_LAB[char_pilih]["pakaian"].keys())
                db_baju = current_row.get('wardrobe', "Original")
                idx_b = outfit_opt.index(db_baju) if db_baju in outfit_opt else 0
                wardrobe = st.selectbox("O_P", outfit_opt, index=idx_b, label_visibility="collapsed")
            
            with col_dna:
                st.markdown('<p class="small-label">🧬 DATA FISIK KARAKTER (AUTO-SYCH)</p>', unsafe_allow_html=True)
                
                # Mengambil data fisik dan pakaian
                dna_text = f"{MASTER_CHAR_LAB[char_pilih]['fisik']} Outfit: {MASTER_CHAR_LAB[char_pilih]['pakaian'][wardrobe]}".strip()
                
                # Placeholder Sultan untuk DNA
                dna_placeholder = (
                    "DNA karakter (anatomi, material, pakaian) akan terisi otomatis... "
                    "Data ini akan digabung dengan aksi untuk hasil visual yang konsisten."
                )
                
                dna_final = st.text_area(
                    "DNA_F", 
                    value=dna_text, 
                    height=100, 
                    placeholder=dna_placeholder,
                    label_visibility="collapsed"
                )

            # --- ROW 2: SETTING AUDIO (MASTER KONSISTEN) ---
            st.markdown('<p class="small-label">🔊 SETTING AUDIO (NARASI VO)</p>', unsafe_allow_html=True)
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                voice_type = st.selectbox("TIPE SUARA", MASTER_AUDIO_LAB["Tipe"])
            with ac2:
                accent_type = st.selectbox("LOGAT / AKSEN", MASTER_AUDIO_LAB["Aksen"])
            with ac3:
                mood_audio = st.selectbox("MOOD SUARA", MASTER_AUDIO_LAB["Mood"])

            st.divider()

            # --- ROW 3: KOTAK AKSI (LANGSUNG TANPA LABEL JUDUL BESAR) ---
            st.markdown('<p class="small-label">🎬 DESKRIPSI AKSI & VISUAL PROMPT</p>', unsafe_allow_html=True)
            
            # 1. Kotak Aksi (A_I) - Karakter Pendukung Dibuang
            aksi_in = st.text_area("A_I", 
                value=current_row.get('visual_prompt', ''), 
                height=150, 
                label_visibility="collapsed", 
                placeholder="Deskripsikan apa yang terjadi di adegan ini secara cinematic...")

            # --- LANJUT KE ENV & VO ---
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<p class="small-label">🌍 LATAR / ENV</p>', unsafe_allow_html=True)
                env_in = st.text_area(
                    "E_I", 
                    value=current_row.get('environment', ''), 
                    height=68, 
                    label_visibility="collapsed",
                    placeholder="Contoh: Kamar gelap, cahaya HP biru, debu beterbangan..."
                )
            with c2:
                st.markdown('<p class="small-label">🎙️ TEKS NARASI VO</p>', unsafe_allow_html=True)
                vo_ref = st.text_area(
                    "V_R", 
                    value=current_row.get('narasi_vo', ''), 
                    height=68, 
                    label_visibility="collapsed",
                    placeholder="Tulis narasi di sini (Maksimal 2 kalimat padat & bercerita)..."
                )

            # --- UPDATE LOGIKA BUTTON GENERATE (WAJIB DISESUAIKAN) ---
            f_auto, m_auto = auto_visual_mapping(aksi_in)

            # --- BUTTON GENERATE: SULTAN VIDEO ENGINE (ULTRA-REALISM EDITION) ---
            if st.button("🚀 GENERATE VIDEO PROMPT", type="primary", use_container_width=True):
                st.divider()
                
                # 1. LOGIKA OTOMATIS MOOD CAHAYA (FORENSIC & RAW LIGHTING)
                env_lower = env_in.lower()
                char_lower = char_pilih.lower()
                
                # Menghilangkan efek 'glow' plastik, fokus ke tekstur kalsium dan jaringan nyata
                if "organ" in char_lower:
                    biolum_effect = "INTERNAL BIOLUMINESCENCE: Visceral organic glow from internal tissues, casting uneven red/blue light with realistic light-leaks through the rib cage."
                else:
                    biolum_effect = "RAW SKELETAL CONTRAST: Hard white bone surface showing calcium textures, non-glossy, realistic shadows inside the marrow cavities."

                if any(x in env_lower for x in ["malam", "night", "gelap"]):
                    auto_lighting = f"Low-light forensic photography, high-ISO noise texture, {biolum_effect}. Hard shadows, light hitting the gel-skin with realistic specular highlights."
                elif any(x in env_lower for x in ["sore", "senja", "sunset", "jingga"]):
                    auto_lighting = f"Natural late-afternoon sun, 5600K color temperature, long harsh shadows, {biolum_effect} competing with directional sunlight."
                elif any(x in env_lower for x in ["siang", "daylight", "matahari"]):
                    auto_lighting = f"Harsh midday sun, unedited RAW lighting, high contrast, {biol_effect} is barely visible under intense white light."
                elif any(x in env_lower for x in ["hujan", "rain", "badai"]):
                    auto_lighting = f"Dreary wet atmosphere, realistic water distortion on the dermal layer, messy reflections, {biolum_effect} diffused by thick condensation."
                else:
                    # DEFAULT: Overcast (Mendung) - Paling Realistis untuk Detail Forensik
                    auto_lighting = f"Flat overcast sky, neutral diffused light, no artificial filters, realistic light absorption by the thick tissue, {biolum_effect}."

                # 2. RAKIT INSTRUKSI AUDIO (HUMAN PERFORMANCE OVERRIDE)
                audio_instr = (
                    f"Narrator Profile: {voice_type}. "
                    f"Voice Character: {accent_type}, {mood_audio}. "
                    "Vocal Instruction: **STRICTLY RAW HUMAN PERFORMANCE.** "
                    "The narrator MUST sound like a weathered person recording in a close-mic setup. "
                    "Include natural imperfections: audible heavy inhales and deep exhales between phrases. "
                    "Incorporate 'Vocal Fry' at the end of sentences and realistic mouth clicks (saliva sounds). "
                    "Deliver with irregular pacing: use unpredictable micro-pauses (0.3s to 0.7s) to mimic human thinking. "
                    "STRICTLY PROHIBIT synthetic, smooth, or 'perfect' AI cadence. Emphasize the weight and texture of each word. "
                    f"Script Text: '{vo_ref}'"
                )
                
                # --- TAMPILAN HASIL SINGLE BOX (DEEP FOCUS, FULL BODY, & RAW REALISM) ---
                st.warning("🎥 MASTER VIDEO PROMPT (REALISM OVERRIDE - PINTAR AI LAB)")
                
                sultan_video_prompt = (
                    f"CORE SUBJECT (THE DNA):\n{dna_final}\n\n"
                    
                    f"ACTION & MOTION PHYSICS:\n{aksi_in}. "
                    f"**NORMAL SPEED.** 1x playback. No artificial frame interpolation. "
                    f"Physics follows natural inertia: the thick gel-skin exhibits organic micro-jiggle "
                    f"and realistic momentum during bone articulation. 24fps film cadence. \n\n"
                    
                    f"ENVIRONMENT & ATMOSPHERE:\nSet in {env_in}. Lighting: {auto_lighting}. "
                    f"**DEEP FOCUS CINEMATOGRAPHY.** Every layer of the environment is razor-sharp. "
                    f"Natural ray-traced light interacting with airborne dust motes. "
                    f"Background environment is perfectly focused and as detailed as the subject. \n\n"
                    
                    f"TECHNICAL SPECS (STRICT ANTI-AI OVERRIDE):\n"
                    f"**RAW 4K DOCUMENTARY FOOTAGE.** Shot on Nikon D850, 24mm Prime, f/22. "
                    f"**ULTRA-WIDE ANGLE.** Framing: {f_auto}. Motion: {m_auto}. "
                    f"**HEAD-TO-TOE FULL BODY VISIBLE STANDING ON THE GROUND.** "
                    f"**FORENSIC TEXTURE DETAIL.** NO SMOOTH PLASTIC. NO ARTIFICIAL GLOSS. "
                    f"Visible organic imperfections: tiny surface scratches, realistic skin pores, and bone calcium textures. "
                    f"**ABSOLUTELY NO MOTION BLUR. NO BOKEH. NO DEPTH OF FIELD BLUR.** "
                    f"Subtle chromatic aberration on frame edges. Natural raw film grain texture. \n\n"
                    
                    f"AUDIO & SOUND DESIGN:\n{audio_instr}. "
                    f"Ambient Audio: Immersive 3D soundscape of {env_in} with hyper-detailed foley and realistic spatial reverb."
                )
                
                st.code(sultan_video_prompt, language="text")

            # --- NAVIGATION ---
            if current_row:
                if st.button("✅ SELESAI & LANJUT KE ADEGAN BERIKUTNYA", use_container_width=True):
                    try:
                        supabase.table("ide_pintar").update({"status": "DONE", "locked_by": "OWNER"}).eq("id", current_row['id']).execute()
                        st.rerun()
                    except:
                        st.error("Koneksi bermasalah saat update status.")

        with st.expander("💡 ASISTEN IDE GURU GEM", expanded=False):
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown('<p class="small-label">1. PILIH PILAR VIRAL</p>', unsafe_allow_html=True)
                tipe_cerita = st.selectbox("TIPE_C", [
                    "🩸 Biological Horror (Anatomi & Siksaan)",
                    "🏛️ Forbidden History (Konspirasi & Zaman)",
                    "⚖️ Micro-Dramatic (Lifestyle & Perbandingan)",
                    "🌀 Absurd What-If (Fisika & Kiamat)",
                    "🧬 Genetic Glitch (Mutasi & Kelainan)",
                    "🧠 Psychological Loop (Otak & Mental)",
                    "🔥 Survival Instinct (Uji Ketahanan)"
                ], label_visibility="collapsed")
            with col_t2:
                st.markdown('<p class="small-label">2. JUMLAH ADENGAN</p>', unsafe_allow_html=True)
                jml_adegan = st.selectbox("JML_A", ["10 Cut", "12 Cut", "15 Cut"], index=2, label_visibility="collapsed")

            st.markdown('<p class="small-label">3. IDE VIDEO</p>', unsafe_allow_html=True)
            ide_singkat = st.text_input("G_IDE", placeholder="Contoh: Jika jantung berhenti sedetik saja...", label_visibility="collapsed")
            
            if ide_singkat:
                # --- MASTER LOGIKA 7 PILAR (NARASI PADAT & LAYAK) ---
                logika_map = {
                    "🩸 Biological Horror (Anatomi & Siksaan)": {
                        "rules": (
                            "DIREKSI NARASI (WAJIB HIDUP):\n"
                            "- Mulai dengan trigger: 'Apa yang terjadi...' atau 'Bagaimana jika...'.\n"
                            "- Gunakan pola progresif: 'Satu hari pertama kamu akan...' dan '7 hari kemudian...'.\n"
                            "- JANGAN KAKU. Ceritakan proses kerusakan seolah penonton sedang mengalaminya sendiri.\n"
                            "- Deskripsikan sensasi fisik secara brutal: tercekik, terbakar, saraf yang gemetar ketakutan, hingga jaringan yang mengkerut hitam.\n"
                            "- Biarkan narasi mengalir bercerita tentang penderitaan organ yang kehilangan dayanya."
                        ),
                        "focus": (
                            "Extreme anatomical forensic detail, macro extreme close-up on vibrating nerves, "
                            "visceral organ decay texture (organ menghitam/kusam), active pulsating organs, "
                            "viscous bioluminescent fluid movement, micro-vibrations of the bone, "
                            "and realistic subsurface scattering on thick gel-skin."
                        ),
                    },
                    "🏛️ Forbidden History (Konspirasi & Zaman)": {
                        "rules": (
                            "DIREKSI NARASI (WAJIB HIDUP):\n"
                            "- Mulai dengan: 'Bagaimana jika...' atau 'Pernahkah kamu membayangkan...'.\n"
                            "- Gunakan alur: 'Satu hari pertama kamu nemuin benda ini...' dan '7 hari kemudian kamu sadar...'.\n"
                            "- Ceritakan kontras tekstur: batu candi yang kasar vs logam masa depan yang halus.\n"
                            "- Narasi harus megah, puitis, dan misterius. Seolah kamu lagi ngebongkar rahasia paling gelap di bumi.\n"
                            "- Gunakan kata-kata sensori: debu zaman, cahaya neon terlarang, bata retak, dinginnya batu kuno."
                        ),
                        "focus": (
                            "Cinematic Golden Hour, dynamic dust motes (debu bergerak), ancient stone texture (batu candi berlumut), "
                            "glowing circuit technology (sirkuit neon), ray-traced shadows, "
                            "and Balung's fingers interacting with rough historical surfaces."
                        ),
                    },
                    "⚖️ Micro-Dramatic (Lifestyle & Perbandingan)": {
                        "rules": (
                            "DIREKSI NARASI (WAJIB HIDUP):\n"
                            "- Mulai dengan: 'Pernahkah kamu membayangkan pertempuran di bawah kulitmu?' atau 'Lihat dua dunia yang berbeda ini...'.\n"
                            "- Gunakan alur kontras: 'Satu hari pertama, tim kiri masih terlihat kuat, tapi tim kanan mulai menyerah...'.\n"
                            "- 7 hari kemudian: Ceritakan kehancuran total di satu sisi (retak, kusam, busuk) vs keajaiban di sisi lain (glowing, kokoh, jernih).\n"
                            "- Gunakan diksi yang memprovokasi pilihan penonton: 'Pilihanmu hari ini adalah kerapuhanmu esok'.\n"
                            "- Fokus pada perubahan tekstur: dari kenyal menjadi rapuh, dari bening menjadi keruh cokelat."
                        ),
                        "focus": (
                            "Side-by-side split screen active interaction, texture contrast (Kusam vs Glowing), "
                            "real-time bone density transformation (tulang keropos vs padat), "
                            "liquid transparency turning murky, transition from organic elasticity to brittle fragility."
                        ),
                    },
                    "🌀 Absurd What-If (Fisika & Kiamat)": {
                        "rules": (
                            "DIREKSI NARASI (WAJIB HIDUP):\n"
                            "- Mulai dengan: 'Apa yang terjadi jika tiba-tiba...' atau 'Bagaimana jika duniamu mendadak...'.\n"
                            "- Satu hari pertama: Ceritakan keanehan kecil yang awalnya terasa lucu (misal: air di gelas mulai melayang pelan).\n"
                            "- 7 hari kemudian: Ceritakan kehancuran total (lautan terangkat ke langit, bangunan beton pecah jadi debu, oksigen kabur ke angkasa).\n"
                            "- Gunakan diksi vertigo: dunia terbalik, kehampaan sunyi, raksasa yang bangun, melayang tanpa arah.\n"
                            "- Jelaskan 'Efek Domino' kiamat ini dengan nada yang dingin namun mencekam."
                        ),
                        "focus": (
                            "Anti-gravity debris (puing melayang), floating water physics interacting with Balung, "
                            "chromatic aberration, volumetric fog, floating ocean particles, "
                            "and motion blur on high-speed flying objects."
                        ),
                    },
                    "🧬 Genetic Glitch (Mutasi & Kelainan Langka)": {
                        "rules": (
                            "DIREKSI NARASI (WAJIB HIDUP):\n"
                            "- Mulai dengan: 'Bagaimana jika tubuhmu memutuskan untuk mengkhianatimu?' atau 'Pernahkah kamu merasakan sesuatu yang salah di dalam tulangmu?'.\n"
                            "- Satu hari pertama: Ceritakan benjolan kecil yang keras, sepele, tapi mulai berdenyut aneh di tulang rusuk atau sendimu.\n"
                            "- 7 hari kemudian: Ceritakan mutasi liar. Benjolan itu meledak jadi duri kalsium tajam (bone spikes) yang merobek jaringan daging dan menembus kulit transparan.\n"
                            "- Gunakan diksi sensori: suara 'kretek' tulang yang berderit, rasa tajam yang menusuk dari dalam, kulit yang menegang maksimal, dan pertumbuhan yang tak terkendali.\n"
                            "- Buat penonton merinding dengan kengerian biologis yang terasa sangat dekat dan nyata."
                        ),
                        "focus": (
                            "Macro close-up on active bone spikes (tulang menusuk keluar), "
                            "skin tension and tearing textures (kulit menegang/robek), subcutaneous writhing movements, "
                            "cold medical neon lighting, and visceral sound-driven visuals."
                        ),
                    },
                    "🧠 Psychological Loop (Otak & Mental)": {
                        "rules": (
                            "DIREKSI NARASI (WAJIB HIDUP):\n"
                            "- Mulai dengan: 'Apa yang terjadi di dalam kepalamu saat duniamu mendadak sunyi?' atau 'Pernahkah kamu merasakan badai yang tak terlihat?'.\n"
                            "- Satu hari pertama: Ceritakan jalur dopamin yang meredup, warnanya berubah jadi biru kelabu yang dingin dan hampa.\n"
                            "- 7 hari kemudian: Jalur itu putus total. Ceritakan kilat merah api dari kortisol yang membakar saraf emosimu, menciptakan ledakan listrik yang tak terkendali.\n"
                            "- Hubungkan ke fisik: Jelaskan dadamu yang sesak bukan karena jantung rusak, tapi karena sarafmu sedang 'konslet' hebat akibat luka mental.\n"
                            "- Gunakan diksi: badai listrik, kesepian yang membakar, sirkuit yang putus, kehampaan yang mencekam."
                        ),
                        "focus": (
                            "Neural firing explosion, brain wave color shifts (Blue to Fire Red), "
                            "volumetric fog inside the skull, micro-gestures of despair (tangan gemetar hebat), "
                            "and motion blur on neural sparks spreading to the environment."
                        ),
                    },
                    "🔥 Survival Instinct (Uji Ketahanan Ekstrem)": {
                        "rules": (
                            "DIREKSI NARASI (WAJIB HIDUP):\n"
                            "- Mulai dengan: 'Bagaimana jika dunia mendadak membeku dan napasmu berubah jadi belati es?' atau 'Berapa lama kamu bisa bertahan saat oksigenmu mulai mendidih?'.\n"
                            "- Satu hari pertama: Ceritakan sensasi mati rasa yang perlahan merambat, ujung jari yang mulai membeku atau kulit yang mulai melepuh.\n"
                            "- 7 hari kemudian: Ceritakan kehancuran material tubuh. Darah membeku di dalam pembuluh transparan, tulang mulai retak (cracking) seperti kaca yang dipukul pelan.\n"
                            "- Gunakan diksi: kristal frost yang haus, retakan membara, napas yang membatu, perjuangan detik demi detik dalam kehampaan.\n"
                            "- Buat penonton merasakan kengerian saat tubuh kehilangan daya lawan terhadap alam yang kejam."
                        ),
                        "focus": (
                            "Dynamic frost spreading (es merambat), active bone cracking textures, "
                            "heat haze and boiling gel-skin effects, crystalline ice growth on transparent skin, "
                            "and struggling movements (merangkak/menahan) against extreme nature."
                        ),
                    }
                }

                # Sinkronisasi Data Aktif
                l_data = logika_map[tipe_cerita]
                try:
                    baju_list = ", ".join(list(MASTER_CHAR_LAB["BALUNG"]["pakaian"].keys()))
                except:
                    baju_list = "Original, Jas Lab Putih, Versi Sultan"

                # --- RAKIT MANTRA FINAL (SULTAN 7 PILAR - DYNAMIC SPATIAL VERSION) ---
                mantra_header = "Saya produser PINTAR AI. Karakter utama kami: BALUNG (Skeleton Transparan).\n"
                mantra_header += "Tugas kamu: Buatkan naskah video cinematic (" + jml_adegan + ") yang HIDUP, BERNYAWA, dan NYATA.\n"
                mantra_header += "TRIGGER IDE: " + ide_singkat + ".\n\n"
                
                mantra_body = "KONSEP UTAMA: " + tipe_cerita + "\n"
                mantra_body += l_data["rules"] + "\n\n"
                
                mantra_footer = "ATURAN WAJIB (DIRECTOR'S GUIDELINE):\n"
                mantra_footer += "- **STORYTELLING PROGRESIF**: Wajib gunakan pola 'Satu hari pertama kamu akan...' di awal adegan dan '7 hari kemudian...' menuju klimaks. Ceritakan prosesnya secara kronologis dan emosional.\n"
                mantra_footer += "- **LIVING NARRATION**: Buat Narasi VO yang padat dan 'berdaging' (Maksimal 3-4 kalimat per adegan). Gunakan kata-kata sensori (dingin, tajam, sesak). JANGAN KAKU.\n"
                mantra_footer += "- **SMART MID-SCENE CTA (WAJIB)**: Di tengah alur (sekitar adegan 7 atau 8), buatlah 1 kalimat ajakan subscribe/like yang MENYATU dengan cerita.\n"
                
                # SUNTIKAN ANTI-PATUNG & INTERAKSI LOKASI (SPATIAL INTERACTION)
                mantra_footer += "- **VISUAL SENSORY & DYNAMIC INTERACTION**: " + l_data["focus"] + ". JANGAN HANYA DESKRIPSIKAN BALUNG SENDIRIAN. Balung WAJIB berinteraksi dengan setting lokasi. (Contoh: Balung berjalan menyisir pinggiran gerbang istana, jemari tulangnya gemetar meraba ukiran relief batu).\n"
                mantra_footer += "- **MOTION & PHYSICS**: Deskripsikan gerakan subjek terhadap objek sekitar. Gunakan gerakan mikro: uap mengalir melewati pilar, gel skin yang bergetar saat bersenggolan dengan material, atau debu yang berputar tertiup napas Balung. Gunakan kamera dinamis: Slow Push-in, Handheld micro-shake, atau Rack Focus.\n"
                mantra_footer += "- **BALUNG MICRO-GESTURE**: Masukkan gerakan manusiawi: rahang gemetar, jemari meraba tekstur material secara nyata, menoleh perlahan mengikuti arah cahaya, atau tubuh terhuyung mengikuti gravitasi.\n"
                
                # PERBAIKAN LOKASI (SPATIAL IDENTITY):
                mantra_footer += "- **ENVIRONMENT ADAPTIF (SPATIAL DETAIL)**: Di kolom Environment Detail, WAJIB sebutkan NAMA LOKASI NYATA di awal kalimat. JANGAN cuma tekstur! Contoh: 'Setting: Lorong Istana Persepolis. Detail: Dinding batu pasir kasar, sisa pembakaran obor, Cinematic Golden Hour.'\n"
                mantra_footer += "  * Jika harian: Kamar kos sempit, Dapur kotor, Halte bus tua. Jika sejarah: Gerbang Istana, Terowongan rahasia, Kuil kuno. Jika kiamat: Reruntuhan Mall, Aspal pecah.\n"
                mantra_footer += "- **FORMAT OUTPUT**: TABEL 5 KOLOM (No Adegan, Narasi VO (Bercerita & Padat), Deskripsi Visual Detail (Gerakan Aksi Karakter + Interaksi Lingkungan + Kamera), Wardrobe (Pilih: " + baju_list + "), Environment Detail (Wajib: NAMA LOKASI NYATA + Tekstur, Material, & Lighting Engine))."

                mantra_final = mantra_header + mantra_body + mantra_footer

                st.markdown('<p class="small-label">4. SALIN MANTRA STORYTELLING INI KE GEMINI</p>', unsafe_allow_html=True)
                st.code(mantra_final, language="text")
                st.info(f"🚀 **MODE VIRAL AKTIF:** {tipe_cerita}. Visual kini dipaksa berinteraksi dengan dunia sekitarnya!")
                
    # ==========================================================================
    # TAB: THE FAMILY LEGACY (REAL HUMAN - NATURAL WIDE SHOT VERSION)
    # ==========================================================================
    with t_grandma:
        # --- 1. MASTER DNA MANUSIA ASLI (FULL BODY & NATURAL SKIN) ---
        MASTER_FAMILY_SOUL = {
            # ========================== KELOMPOK NENEK (Teduh & Berwibawa) ==========================
            "Nenek (The Matriarch)": (
                "Cinematic portrait of a graceful elderly Indonesian woman. Her face exudes a warm, motherly aura. "
                "Soft aesthetic wrinkles, healthy sawo matang skin with a gentle glow. Soulful, kind eyes. "
                "Detailed skin texture but with soft-focus lighting to maintain a peaceful, dignified beauty. Strictly no horror vibe."
            ),
            "Nenek Arum (The Grace)": (
                "A serene and elegant elderly Indonesian woman. Her aged skin is clean and glows under soft golden light. "
                "Fine, realistic wrinkles that look like a map of a happy life. Peaceful expression, calm smile. "
                "Anatomy is detailed but refined. She looks like a beloved royal grandmother from a village."
            ),
            "Nenek Sumi (The Wise)": (
                "A humble but beautiful elderly Indonesian woman. Weathered skin that looks healthy and sun-kissed. "
                "Her eyes sparkle with wisdom. Hands are detailed with realistic textures but look soft and caring. "
                "Atmospheric lighting that highlights her noble and hardworking spirit. Pure aesthetic."
            ),
            "Nenek Lastri (The Devotion)": (
                "Elderly Indonesian woman with a soft, glowing complexion. Her white hair looks like silk. "
                "The wrinkles are subtle and graceful. Soft-focus background, warm 'God-rays' lighting. "
                "She has a very comforting and 'adem' aura. High-fidelity skin detail with a polished cinematic finish."
            ),
            "Gadis Desa (The Natural)": (
                "Stunning young Indonesian woman with an authentic 'Gadis Desa' beauty. Radiant, flawless sawo matang skin. "
                "Soft natural lighting highlighting her high cheekbones and large, expressive brown eyes. "
                "Pure and fresh aura, long healthy black hair. Realistic skin texture but looks incredibly charming and modest."
            ),
            "Gadis Rumi (The Dreamer)": (
                "A young Indonesian woman with a poetic and elegant face. Matte skin texture with a soft pearlescent glow. "
                "Deep, beautiful eyes with realistic reflections. Her beauty is quiet and captivating. "
                "Highly detailed features, clean and unpolished, looking like a protagonist in a high-end cinematic movie."
            ),
            "Gadis Melati (The Fresh)": (
                "Young Indonesian girl with a bright, luminous face. Natural rosy tint on her cheeks and lips. "
                "Healthy tan skin that looks smooth and supple. Energetic and pure aura. "
                "The lighting is bright and airy, making her look like a ray of sunshine. Extremely aesthetic."
            ),
            "Gadis Anisa (The Modest)": (
                "A young Indonesian woman with a shy, angelic beauty. Soft facial contours and almond-shaped eyes. "
                "Smooth sawo matang skin with high-fidelity detail. Her presence is calm and soul-soothing. "
                "Cinematic soft-lighting, emphasizing her pure and modest village girl aesthetic."
            ),
            "Kakek (The Wise)": (
                "A handsome, elderly Indonesian man with a dignified and respected look. Leathery but clean skin. "
                "Thick white eyebrows and a neat mustache. His eyes are sharp but kind. "
                "Gagah (sturdy) posture, looking like a wise leader. Dramatic but warm lighting that emphasizes his noble aura."
            ),
            "Kakek Wiryo (The Artisan)": (
                "A strong, charismatic elderly Indonesian man. Rugged facial features that look artistic and bold. "
                "Tanned skin with a healthy texture. His hands look powerful and skilled. "
                "Cinematic side-lighting (Chiaroscuro) that makes him look like a legendary master craftsman. No scary elements."
            ),
            "Kakek Joyo (The Farmer)": (
                "An elderly Indonesian man with a warm, friendly face and a joyful aura. "
                "Beautifully aged skin with realistic 'laugh lines' around the eyes. "
                "Aura of contentment and gratitude. The light is warm and golden, making his presence feel very welcoming and grounded."
            ),
            "Kakek Usman (The Silent)": (
                "Tall, boney, but very elegant elderly Indonesian man. Sharp, intellectual facial structure. "
                "Peaceful and meditative aura. Long, slender fingers that look graceful. "
                "Cinematic twilight lighting, giving him a mystical but very holy and calm appearance."
            )
        }

        # --- 2. MASTER WARDROBE (6 VARIAN PER KARAKTER - DAILY & NEAT HIJAB) ---
        MASTER_FAMILY_WARDROBE = {
            # --- KELOMPOK NENEK ---
            "Nenek (The Matriarch)": {
                "Daster Batik & Bergo": "Daily long-sleeved batik daster, clean and well-ironed, paired with a fresh white bergo hijab. Neat and motherly.",
                "Gamis Harian Polos": "Simple wrinkle-free daily gamis made of smooth rayon, paired with a matching square hijab tucked in. Very 'adem' and clean.",
                "Setelan Tunik & Celana": "Long-sleeved cotton tunik paired with tidy loose trousers and a neat hijab. A respectable village grandmother look.",
                "Daster Kaos & Jilbab": "Comfortable cotton daster, fresh from laundry, paired with a tidy daily instant jilbab. No wrinkles, looking honest.",
                "Gamis Jersey & Bergo": "High-quality jersey gamis with perfect drape, paired with a fresh white instant bergo. Clean and very orderly.",
                "Blouse Batik & Hijab": "Simple daily batik blouse, well-pressed, paired with a clean black square hijab. Dignified and neat appearance."
            },
            "Nenek Arum (The Grace)": {
                "Daster Floral & Hijab": "Modest long-sleeved floral daster in soft pastel, paired with a clean jersey hijab. Serene and beautifully aged.",
                "Gamis Motif & Khimar": "Daily gamis with subtle geometric motifs, paired with a wide, clean khimar hijab. Well-presented and respected elder.",
                "Tunik Linen & Pashmina": "High-quality linen tunik with visible weave, paired with a neatly wrapped pashmina. Elegant, clean, and graceful.",
                "Daster Rayon & Bergo": "Cool rayon daster with modern print, paired with a fresh white bergo. Looking fresh and very tidy at home.",
                "Gamis Pastel & Hijab": "Soft-colored daily gamis, perfectly ironed, paired with a matching square hijab. Luminous and peaceful aura.",
                "Setelan Syar'i Harian": "Complete neat daily syar'i set, wrinkle-free, soft fabric texture. Looking very 'adem' and pure."
            },
            "Nenek Sumi (The Wise)": {
                "Daster Kaos & Jilbab": "Crisp cotton daster in earthy tones, paired with a tidy daily instant jilbab. No wrinkles, looking hardworking and orderly.",
                "Gamis Jersey & Bergo": "Smooth jersey gamis, perfectly maintained, paired with a fresh instant bergo. Clean, fresh, and soulful.",
                "Blouse Batik & Hijab": "Simple daily batik blouse, well-pressed, paired with a clean black hijab. A very neat and respectable daily appearance.",
                "Daster Batik Klasik": "Traditional brown batik daster, clean lines, paired with a neat white hijab. Authentic village grandmother aesthetic.",
                "Gamis Polos & Khimar": "Deep-colored daily gamis, paired with a clean wide khimar. Looking very orderly and well-groomed.",
                "Tunik Katun & Hijab": "Long-sleeved cotton tunik with tiny patterns, paired with a tidy hijab. Practical but very clean and decent."
            },
            "Nenek Lastri (The Devotion)": {
                "Gamis Putih & Bergo": "Crisp, bright white daily gamis paired with a fresh white bergo hijab. Luminous, holy, and perfectly clean.",
                "Daster Soft & Khimar": "Soft-toned long-sleeved daster, paired with a clean wide khimar. Very peaceful, tidy, and spiritually beautiful.",
                "Setelan Syar'i Harian": "Complete neat daily syar'i set, no wrinkles, soft fabric. Looking very 'adem' and pure for daily prayer vibe.",
                "Gamis Abu-abu & Hijab": "Elegant grey daily gamis, perfectly ironed, paired with a matching square hijab. Calm and dignified beauty.",
                "Daster Bordir & Bergo": "Soft cotton daster with subtle embroidery, paired with a fresh white bergo. Very clean and gracefully aged.",
                "Tunik Putih & Hijab": "Clean white tunik paired with tidy trousers and a neat hijab. Looking fresh, honest, and very respectable."
            },

            # --- KELOMPOK GADIS ---
            "Gadis Desa (The Natural)": {
                "Gamis Modern & Khimar": "Modern but loose gamis with a clean silhouette, perfectly pinned, paired with a fresh wide khimar hijab. Radiant, pure, and very modest village look.",
                "Tunik Katun & Pashmina": "Modest long cotton tunik, paired with a neatly wrapped pashmina and loose loose trousers. Fresh, youthful, and naturally charming.",
                "Daster Long-sleeve & Bergo": "Clean modest long-sleeve daster dress, not loose, paired with a fresh white bergo hijab. Neat, orderly, and naturellement beautiful.",
                "Blouse Floral & Segiempat": "Fresh floral long-sleeved blouse, paired with a neat matching square hijab tucked in. High-end cinematic natural beauty, completely modest.",
                "Setelan Syar'i Luminous": "Complete neat daily syar'i set, soft fabric texture. Looking very 'adem', pure, and orderly for a sacred atmosphere."
            },
            "Gadis Rumi (The Dreamer)": {
                "Gamis Linen & Segiempat": "Clean long gamis made of premium linen, perfect ironed, paired with a fresh square hijab. Artistic, pure, and luminous aesthetic.",
                "Tunik Aesthetic & Khimar": "Aesthetic long tunik in earth tones, paired with loose trousers and a fresh clean wide khimar hijab. Quiet, meditative, and captivating beauty.",
                "Kemeja Oversized & Bergo": "Simple but neat oversized modest shirt, paired with very loose loose pants and a clean bergo hijab. Fresh from the laundry look, pure modest.",
                "Daster Floral & Jilbab": "Modest long floral daster, paired with a fresh instant jilbab. looking fresh, honest, and naturellement graceful.",
                "Blouse Polos & Pashmina": "Elegant daily blouse, perfectly ironed, paired with a neatly styled pashmina hijab. Very orderly and dignified."
            },
            "Gadis Melati (The Fresh)": {
                "Tunik Pastel & Hijab": "Long-sleeved pastel tunik with clean lines, paired with loose white pants and matching neat hijab. Radiant, pure, and energetic.",
                "Gamis Modern & Bergo": "Simple modern daily gamis, not loose, paired with a fresh white bergo hijab. energetic, clean, and very ordered.",
                "Blouse Motif & Pashmina": "Fresh floral cotton blouse, well-pressed, paired with a neatly wraps pashmina. completely modest village figures.",
                "Daster Long-dress & Khimar": "Stylish long-sleeve daster dress, paired with a clean instant wide khimar. Neat, modest, and naturellement beautiful.",
                "Setelan Syar'i Harian": "Complete neat daily syar'i set, smooth jersey fabric. No open parts, very ordered."
            },
            "Gadis Anisa (The Modest)": {
                "Gamis Syar'i & Khimar": "Complete neat daily syar'i set, wide khimar hijab, not loose. Angelic, polite, and deeply humble village beauty.",
                "Tunik Putih & Hijab": "Modest clean white tunik paired with loose black trousers and a neat black square hijab. Pure, orderly, and adem spirit.",
                "Daster Soft & Bergo": "Soft-toned long daster, perfectly pressed, paired with a fresh white bergo. Peaceful and adem village spirit.",
                "Blouse Floral & Jilbab": "Fresh floral cotton blouse, paired with a neatly pinned jilbab. Completely modest and ordered.",
                "Setelan Harian Polos": "Simple elegant loose set with loose trousers and matching hijab. Very orderly."
            },

            # --- KELOMPOK KAKEK ---
            "Kakek (The Wise)": {
                "Baju Koko & Peci": "Crisp white long-sleeved koko shirt with sharp ironed lines, paired with a neat black peci and folded sarong.",
                "Kemeja Putih & Sarung": "Simple clean white button-up shirt, well-pressed, paired with a premium plaid sarong and black peci.",
                "Batik Lengan Panjang": "High-quality long-sleeved batik shirt with sharp traditional patterns. Dignified and respected look.",
                "Koko Harian & Peci": "Simple daily koko shirt, clean and well-maintained, paired with a neat sarung. Respectable village teacher vibe.",
                "Kemeja Flanel & Sarung": "Tidy buttoned-up flannel shirt, worn with a clean peci and neat sarung. Rugged but very orderly elder look.",
                "Batik Casual & Peci": "Short-sleeved batik with clean lines, paired with a black peci. A very neat and respected village figure."
            },
            "Kakek Wiryo (The Artisan)": {
                "Batik Kerajinan": "Clean, bold-patterned batik shirt, sturdy and well-fitted. The look of an orderly and charismatic master craftsman.",
                "Koko Hitam & Peci": "Neat black koko shirt with silver embroidery, paired with a black peci. Rugged, clean, and masculine.",
                "Kemeja Flanel Tidy": "Tidy buttoned-up flannel shirt in dark tones, worn with a clean peci and neat sarung. Orderly artisan look.",
                "Kemeja Denim & Peci": "Clean modest denim shirt, well-pressed, paired with a black peci and sarung. Strong and dignified craftsman.",
                "Batik Cokelat & Sarung": "Traditional brown batik shirt, looking fresh and neat, paired with a tidy sarung. A respected and skillful elder.",
                "Koko Putih & Peci": "Crisp white koko shirt, sharp ironed lines, looking very clean and ready for work or prayer."
            },
            "Kakek Joyo (The Farmer)": {
                "Kemeja Polo & Sarung": "Clean simple collared polo shirt that looks very tidy, paired with a perfectly wrapped sarong. Humble and respectable.",
                "Koko Harian & Peci": "Simple daily koko shirt, well-maintained and clean, paired with a neat sarung. Aura of gratitude and neatness.",
                "Batik Casual & Peci": "Short-sleeved batik with clean lines, paired with a black peci. A very neat version of a village farmer.",
                "Kemeja Kotak-kotak": "Tidy plaid shirt, well-ironed, paired with a neat sarung and peci. Looking honest, clean, and hardworking.",
                "Batik Tanah Liat": "Batik with earth-tone patterns, looking fresh and tidy, paired with a black peci. Very grounded and humble appearance.",
                "Koko Katun & Sarung": "Soft cotton koko shirt, perfectly pressed, paired with a tidy sarung. Looking peaceful and very orderly."
            },
            "Kakek Usman (The Silent)": {
                "Jubah Putih & Peci": "Long white robe (Jubah) that is perfectly pressed and clean, paired with a white skullcap. Luminous and ancient wisdom.",
                "Koko Panjang & Sarung": "Elegant long koko shirt with premium fabric texture, paired with a neat sarung. Meditative and very clean aura.",
                "Baju Takwa & Peci": "Traditional clean white 'Baju Takwa', well-ironed, paired with a black peci. Pure, holy, and aesthetic.",
                "Jubah Abu-abu & Peci": "Clean grey jubah with simple embroidery, paired with a white skullcap. Quiet, dignified, and very tidy.",
                "Koko Hitam & Sarung": "Neat black koko shirt, paired with a premium sarung and peci. High-contrast cinematic look, very respectable.",
                "Kemeja Putih & Peci": "Simple crisp white shirt, well-pressed, paired with a neat sarung. Looking very pure and orderly."
            }
        }

        # --- 3. MASTER BAHAN (ARCHITECTURAL PRECISION: 90% PROGRESS INTERACTIVE) ---
        MASTER_KONTEN_ALL = {
            "🕌 Miniatur Masjid": {
                "Golden Literary (Koran Bekas)": (
                    "A massive physical mosque model on a table. Built entirely from hand-rolled "
                    "recycled newspapers. The model has a clear large dome and 4 tall minarets. "
                    "The structure is HOLLOW with INTERNAL WARM LIGHTING glowing from inside the windows. "
                    "The textures of the black-and-white newspaper print are clearly visible on the walls. "
                    "The mosque is a COMPLETELY SEPARATE OBJECT from the artisan. "
                    "The artisan's hands are simply touching the base of the model. "
                    "Sharp architectural lines, realistic paper texture, no glowing body, no fusion."
                ),
                "Crystal Bottle (Botol Bekas)": (
                    "A GARGANTUAN TABLETOP ARCHITECTURAL MODEL. A massive mosque diorama "
                    "sitting firmly on the wooden table, built from thousands of hand-cut recycled "
                    "clear glass fragments. The structure is a PHYSICAL OBJECT on the bench. "
                    "The mosque is HOLLOW and ILLUMINATED FROM WITHIN by warm white LED lights. "
                    "The light refracts naturally through the glass edges. NO glass clothing, "
                    "NO glass body—the character is a normal human artisan. The character is "
                    "using a soft cloth to polish the central dome of the mosque on the table. "
                    "Exudes supreme, crystalline luxury and realistic physical scale."
                ),
                "Organic Dragon Fruit (Buah Naga)": (
                    "A MAGNIFICENT ORGANIC ARCHITECTURAL CATHEDRAL. A gargantuan mosque carved entirely "
                    "from fresh dragon fruit. The massive domes are the vibrant pink outer skin, "
                    "featuring intricate geometric patterns carved into the peel. The structure is HOLLOW, "
                    "with INTERNAL WARM LIGHTS glowing through the arched windows and translucent fruit flesh. "
                    "The pillars are carved from white fruit flesh with black seeds acting as natural "
                    "architectural ornaments. NO artificial marble—everything is organic. The internal "
                    "glow highlights the juicy, high-definition textures of the fruit. The character "
                    "is using a precision tool to carve a tiny window, emphasizing the massive scale "
                    "of this ephemeral masterpiece. Fresh, majestic, and elite."
                ),
                "Ivory Shell (Cangkang Telur)": (
                    "A SUPREME IVORY ARCHITECTURAL MASTERPIECE. A gargantuan mosque diorama "
                    "entirely covered in millions of hand-placed, microscopic white eggshell fragments. "
                    "The texture is a sophisticated matte ivory, resembling ancient marble. "
                    "The structure is HOLLOW and ILLUMINATED FROM WITHIN by soft warm LEDs "
                    "that shine through the arched windows and intricate geometric calligraphy "
                    "etched into the eggshell surface. This internal glow creates realistic "
                    "depth and highlights the million tiny fragments. NO fake external glows. "
                    "The scale is immense, roughly as large as a human torso. The character is "
                    "using fine-tip tweezers to place a microscopic piece, looking tiny next to "
                    "the towering minaret. Pure museum-grade luxury."
                ),
                "Royal Bamboo (Anyaman Bambu)": (
                    "A COLOSSAL ARCHITECTURAL BAMBOO MONUMENT. A sprawling complex with triple-tiered "
                    "Javanese roofs built from golden-aged bamboo. The walls feature microscopic "
                    "weaving (gedek) so fine it resembles silk lace. The mosque is HOLLOW, "
                    "with INTERNAL WARM LANTERNS glowing from inside the structure. "
                    "The light filters through the tiny gaps in the bamboo weave, casting "
                    "complex, sharp geometric shadows onto the workbench and the artisan's hands. "
                    "No magical mist—only the authentic internal radiance of a high-end traditional "
                    "masterpiece. The character is weaving the final strip into the towering roof crest, "
                    "looking small next to the massive structure. Grounded, rustic, and elite."
                ),
                "Emerald Plastic (Botol Aqua)": (
                    "A COLOSSAL ARCHITECTURAL PLASTIC MASTERPIECE. A sprawling mosque diorama "
                    "meticulously sculpted from thousands of hand-cut recycled blue and clear plastic bottles. "
                    "The material is turned into smooth architectural curves and translucent domes. "
                    "The structure is HOLLOW and ILLUMINATED FROM WITHIN by soft cyan LED lights "
                    "that shine ONLY through the arched windows and geometric calligraphy etched into "
                    "the plastic surface. NO futuristic neon—only the realistic internal radiance "
                    "of recycled acrylic. The scale is gargantuan, filling the entire workbench. "
                    "The character is using a micro-torch to seal a joint on a massive pillar, "
                    "looking small next to the towering structure. Clean, organic, and grand."
                ),
                "Silver Cutlery (Sendok Garpu)": (
                    "A COLOSSAL METALLIC ARCHITECTURAL DIORAMA. Constructed from over 5,000 polished "
                    "stainless steel spoons and forks. The grand central dome is a massive architectural "
                    "sphere made of layered spoon-heads, reflecting the workshop environment with "
                    "natural metallic luster. The structure is HOLLOW, with WARM AMBER INTERNAL LIGHTING "
                    "glowing through the gaps in the interlocking forks and carved metal doors. "
                    "NO fake glows—only the realistic light reflections on the silver surfaces. "
                    "The scale is immense, with towering minarets made of silver knives. "
                    "The character looks small next to the silver spires as they bend a final spoon. "
                    "Exudes a supreme, avant-garde, and ultra-luxurious metallic aura."
                ),
                "Rustic Matchsticks (Korek Kayu)": (
                    "A VAST RUSTIC ARCHITECTURAL MARVEL. A sprawling mosque complex built from 50,000 "
                    "natural wooden matchsticks. The architecture is incredibly complex, featuring "
                    "massive multi-tiered domes with natural wood grain textures. The structure is HOLLOW, "
                    "with INTERNAL AMBER LIGHTS glowing through thousands of microscopic windows and "
                    "arched walkways. The light filters through the tiny gaps in the matchstick walls, "
                    "casting realistic sharp shadows onto the wooden workbench. No magical mist—only "
                    "the authentic internal radiance of a wooden city. The character is placing a final "
                    "matchstick with glue, looking like a tiny creator next to the colossal structure. "
                    "Warm, earthy, and breathtakingly detailed."
                ),
                "Starlight Circuit (Kabel & Komponen)": (
                    "A MASSIVE ARCHITECTURAL COPPER MASTERPIECE. A gargantuan mosque diorama "
                    "woven from a dense, intricate web of natural golden copper wires and recycled "
                    "motherboard components. The central dome is a massive geodesic sphere of "
                    "burnished copper wire. The structure is HOLLOW and features INTERNAL WARM "
                    "WHITE LIGHTING that glows from within, shining ONLY through the gaps in the "
                    "woven wire and motherboard ARCHES. No fake digital glows—only the realistic "
                    "metallic reflection of copper under workshop lights. The scale is immense, "
                    "filling the entire workbench. The character is soldering a final wire to the "
                    "massive dome, looking small next to the industrial-elegant structure."
                ),
                "Terracotta Clay (Tanah Liat)": (
                    "A COLOSSAL ANCIENT EARTHEN MASTERPIECE. A massive mosque complex sculpted from "
                    "fine terracotta clay, standing as tall as the character's chest. Features 7 "
                    "sprawling hollow domes with deep, hand-carved Arabic calligraphy. The structure "
                    "is ILLUMINATED FROM WITHIN by soft amber lamps that glow through the intricate "
                    "clay latticework and arched windows. No magical mist—only the authentic, warm "
                    "internal radiance of baked earth. The rich reddish-brown matte surface shows "
                    "microscopic fingerprints and carving marks, highlighting the world-class "
                    "craftsmanship. The character looks tiny as they use a wet finger to smooth "
                    "the massive clay surface. Sanctity and grandeur."
                ),
                "Popsicle Palace (Stik Es Krim)": (
                    "A GARGANTUAN ARCHITECTURAL WOODEN CATHEDRAL-MOSQUE. Built from 20,000 "
                    "layered natural wooden sticks, showing authentic wood grain textures. "
                    "The architecture is immense, featuring a grand triple-tiered central dome. "
                    "The structure is HOLLOW, with INTERNAL WARM LEDS embedded within, making "
                    "the massive structure glow like a royal palace from the inside. The light "
                    "filters ONLY through the windows and balconies, casting realistic sharp "
                    "shadows on the workbench. No fake 'night' filters—just the honest, "
                    "high-end internal illumination of a wooden masterpiece. The character is "
                    "placing a final stick on a towering minaret, appearing as a tiny architect "
                    "in a giant wooden city."
                ),
                "Fruit Skin Mosaic (Kulit Buah)": (
                    "A MAGNIFICENT VIBRANT ECO-MARVEL. A sprawling mosque diorama built ENTIRELY from "
                    "thousands of dried orange, lime, and pomelo skins. NO stone or marble. The domes "
                    "feature a complex mosaic of natural citrus peels, creating a 'natural stained glass' "
                    "effect. The structure is HOLLOW with INTERNAL WARM LIGHTS glowing ONLY through "
                    "the translucent rinds and arched windows. The light highlights the natural oily "
                    "pores and zest textures of the fruit skins. The scale is gargantuan, filling the "
                    "entire workbench. The character is pressing a piece of citrus peel onto a massive "
                    "wall, looking tiny next to the eco-elegant masterpiece. Organic, grand, and pure."
                ),
                "Emerald Melon (Melon Ukir)": (
                    "A COLOSSAL FRUIT ARCHITECTURE MASTERPIECE. A gargantuan mosque carved ENTIRELY from "
                    "massive honeydew and cantaloupe melons. The central dome is a giant sphere of "
                    "carved green rind with Islamic geometric lace patterns. The structure is HOLLOW, "
                    "with INTENSE INTERNAL WHITE LIGHTING making the translucent green fruit flesh "
                    "glow from within like a natural emerald. NO actual gemstones—only the glowing "
                    "flesh of the melon. The 4 minarets are towering pillars of carved cantaloupe skin. "
                    "The character is using a surgical blade on the giant monument, appearing as a "
                    "tiny artisan. High-definition textures of juicy fruit and sharp rinds. Royal grandeur."
                ),
                "Golden Citrus (Kulit Jeruk)": (
                    "A MAGNIFICENT CITRUS CATHEDRAL-MOSQUE. A sprawling diorama built ENTIRELY from "
                    "thousands of dried, polished orange peels. The peels are cut into architectural "
                    "shingles covering the vast domes like natural scales. The structure is HOLLOW, "
                    "with INTERNAL AMBER LIGHTS shining through the gaps and carved pomelo rind arches. "
                    "The light creates a warm, organic glow that highlights the dimpled texture of "
                    "the orange skin. NO bronze or metal—everything is 100% citrus. The structure "
                    "is wide and immense, filling the entire frame. The character's hand appears "
                    "tiny while pressing the final peel. High-end organic architectural luxury."
                ),
                "Royal Velvet (Kain Beludru)": (
                    "A SUPREME LUXURY TEXTILE ARCHITECTURAL MASTERPIECE. A gargantuan mosque diorama "
                    "where the massive hollow domes are draped in deep emerald-green royal velvet fabric. "
                    "Features heavy gold thread embroidery and embossed floral patterns on cream silk walls. "
                    "The structure is HOLLOW with INTERNAL WARM LIGHTS glowing ONLY through the arched "
                    "windows and intricate fabric lace. The lighting highlights the rich, matte texture "
                    "of the fabric fibers. NO fake glows—only the realistic internal radiance. "
                    "The scale is overwhelming, filling the entire workbench. The character is a small figure "
                    "using a needle and gold thread to sew a final ornament on the gargantuan dome. "
                    "Pure sultanate luxury."
                ),
                "Crystal Ice (Es Batu)": (
                    "A COLOSSAL CRYSTAL ICE ARCHITECTURAL MARVEL. A gargantuan mosque diorama sculpted "
                    "ENTIRELY from massive, clear blocks of arctic ice. The structure is HOLLOW, with "
                    "INTERNAL PURE WHITE LED LIGHTS making the transparent ice blocks glow from within. "
                    "The light refracts naturally through the sharp crystalline edges and etched "
                    "calligraphy on the frozen surface. NO blue neon or magical mist—only the realistic "
                    "transparency and reflections of cold ice. The scale is immense, standing as tall "
                    "as the character's torso. The character is using a metal scraper on the massive "
                    "frozen monument, looking tiny next to the crystalline spires. Majestic and freezing."
                ),
                "Golden Spice (Kayu Manis & Cengkeh)": (
                    "A MAGNIFICENT SPICE EMPIRE ARCHITECTURAL DIORAMA. A vast mosque complex built "
                    "ENTIRELY from tens of thousands of natural cinnamon sticks and dried cloves. "
                    "The massive domes are perfect spheres of layered cinnamon with rhythmic floral "
                    "patterns made of cloves. The structure is HOLLOW with INTERNAL AMBER LIGHTING "
                    "glowing through the gaps in the spice layers and arched windows. The light "
                    "highlights the deep, rich brown matte texture of the spices. NO artificial gold— "
                    "the luxury comes from the intricate spice patterns. The character is a tiny figure "
                    "placing a final clove with tweezers, appearing as a small creator next to the "
                    "colossal spice city. Ancient, aromatic, and grand."
                ),
                "White Marble Eggshell (Cangkang Telur)": (
                    "A SUPREME LUXURY WHITE MARBLE ARCHITECTURAL MASTERPIECE. A massive mosque structure "
                    "covered in millions of hand-placed white eggshell fragments, appearing as seamless "
                    "matte marble. The structure is HOLLOW with INTERNAL WARM WHITE LIGHTING glowing "
                    "ONLY through the arched windows and intricate geometric calligraphy etched into "
                    "the eggshell surface. NO fake external glows—only the realistic internal radiance. "
                    "The scale is gargantuan, filling the entire frame. The character is a small figure "
                    "applying a final matte finish to the massive surface, looking tiny next to the "
                    "towering minarets with gold-leaf tips. Flawless, museum-grade architectural luxury."
                ),
                "Pearl & Oyster (Cangkang Kerang)": (
                    "A COLOSSAL IRIDESCENT PEARL PALACE. A gargantuan mosque diorama built ENTIRELY from "
                    "thousands of shimmering mother-of-pearl fragments. The central dome is a massive "
                    "polished oyster shell. The structure is HOLLOW, with INTERNAL SOFT WHITE LIGHTS "
                    "glowing through the translucent shell layers. This creates a natural iridescent "
                    "shimmer on the surface, NOT a rainbow glow. Features 8 towering boney-white minarets "
                    "with gold-leaf inlay. The scale is massive, stretching across the workbench. "
                    "The character is a tiny figure placing a final pearl at the tip of the crescent, "
                    "emphasizing the staggering architectural scale. Pure, natural elegance."
                ),
                "Banana Fiber Lace (Pelepah Pisang)": (
                    "A COLOSSAL ORGANIC ARCHITECTURAL MARVEL. A sprawling mosque diorama built ENTIRELY from "
                    "thousands of dried and pressed banana fibers, woven into intricate lace-like patterns. "
                    "Features massive multi-tiered cascading roofs (tumpang) with the texture of aged silk. "
                    "The structure is HOLLOW, with INTERNAL AMBER LIGHTS glowing intensely through the "
                    "translucent fiber walls and arched gates. The light highlights the natural organic "
                    "grain and textures of the fiber. NO fake glows—only the realistic internal radiance "
                    "of a handmade masterpiece. The character is a tiny artisan braiding the final "
                    "fiber around a towering minaret balcony. Ancient, majestic, and grounded."
                ),
                "Sapphire Glass (Pecahan Kaca Biru)": (
                    "A MAGNIFICENT GARGANTUAN SAPPHIRE ARCHITECTURAL MASTERPIECE. A massive mosque diorama "
                    "constructed ENTIRELY from thousands of hand-cut recycled cobalt-blue glass shards. "
                    "The structure is HOLLOW and ILLUMINATED FROM WITHIN by warm white lights, making "
                    "the crystalline blue domes glow with a deep, natural internal radiance. "
                    "The light refracts through the sharp glass edges, casting realistic blue geometric "
                    "patterns onto the workbench. NO fake LED strips or neon—only the honest internal "
                    "glow of sapphire glass. The scale is gargantuan, filling the frame. The character "
                    "appears tiny as they stabilize a glass joint on the massive entrance. Hyper-realistic."
                ),
                "Ivory Corn Husk (Kulit Jagung)": (
                    "A SUPREME IVORY-COLORED ORGANIC MASTERPIECE. A giant mosque diorama built ENTIRELY from "
                    "thousands of ironed and layered natural corn husks. The domes feature a 'pleated fabric' "
                    "architectural texture. The structure is HOLLOW with INTERNAL AMBER LIGHTS glowing "
                    "through the translucent ivory fibers and arched windows. The light highlights the "
                    "natural organic grain and micro-textures of the husks. NO artificial fabric—everything "
                    "is 100% corn husk. The scale is immense, stretching across the workbench. "
                    "The character's hand looks small while smoothing an ivory-colored leaf on the "
                    "gargantuan main dome. Pure, clean, and architecturally grand."
                ),
                "Obsidian Charcoal (Arang Kayu)": (
                    "A STUNNING MINIMALIST DARK MEGA-STRUCTURE. A massive mosque diorama carved ENTIRELY from "
                    "solid black charcoal blocks. The surface has a rich, matte black texture with "
                    "golden 'Kintsugi' cracks. The structure is HOLLOW, with INTERNAL WARM ORANGE LIGHTS "
                    "shining ONLY through the golden cracks and arched windows. The light creates a "
                    "realistic 'smoldering' amber effect, highlighting the sharp geometric minarets. "
                    "NO magical red glow—only the authentic internal radiance. The scale is gargantuan, "
                    "standing as tall as the character's torso. The character is a tiny figure "
                    "applying gold dust into a crack on the massive structure. Imposing and elite."
                ),
                "Amber Spice (Cengkeh & Kayu Manis)": (
                    "A COLOSSAL ARCHITECTURAL SPICE MONUMENT. A gargantuan mosque diorama built "
                    "ENTIRELY from natural dried cloves and polished cinnamon sticks. The massive "
                    "central dome is a sphere of tens of thousands of cloves in a geometric mandala pattern. "
                    "The structure is HOLLOW with INTERNAL AMBER LIGHTS glowing through the gaps in the "
                    "spice layers. The light highlights the deep, rich brown matte texture of the cloves "
                    "and the woody grain of the cinnamon pillars. NO fake golden glows—only the realistic "
                    "internal radiance. The scale is immense, filling the frame. The character looks "
                    "tiny as they meticulously place the final clove with tweezers. Ancient and grand."
                ),
                "Porcelain Duck-Spoon (Sendok Bebek)": (
                    "A MAGNIFICENT AVANT-GARDE GARGANTUAN MOSQUE. Built ENTIRELY from over a thousand "
                    "authentic white ceramic duck spoons, layered to form a majestic scalloped dome. "
                    "The structure is HOLLOW, with INTERNAL WARM WHITE LIGHTING glowing through the "
                    "arched openings and between the spoon handles. The glossy ceramic surface reflects "
                    "the workshop lights with a natural high-end porcelain luster. NO digital sparkles— "
                    "only the realistic refraction of light on polished ceramic. The scale is staggering, "
                    "filling the workbench. The character is a small figure stabilizing the peak, "
                    "looking like a tiny architect in a porcelain city. Pure architectural luxury."
                ),
                "Feathered Silk (Bulu Unggas & Kain)": (
                    "A COLOSSAL TEXTILE ARCHITECTURAL MASTERPIECE. A giant mosque diorama where the "
                    "massive hollow domes are covered in millions of natural pure white feathers "
                    "arranged like intricate architectural shingles. The sprawling walls are wrapped "
                    "in fine white silk with gold thread embroidery. The structure is HOLLOW, with "
                    "INTERNAL SOFT LIGHTS glowing through the silk windows and feather layers. "
                    "The lighting highlights the delicate, matte texture of the feathers and fabric fibers. "
                    "NO 'heavenly' mist or fake clouds—just the honest, high-end internal illumination "
                    "of a handmade textile masterpiece. The character is a tiny artisan using a needle "
                    "on the gargantuan dome. Stunning texture detail and organic grandeur."
                ),
            }, # Penutup MASTER_KONTEN_ALL
            # --- 3. MASTER KONTEN (🌍 WORLD MOSQUE DIORAMA - MEGA SCALE EDITION) ---
            "🌍 Diorama Masjid": {
                "Mega Diorama: Al-Aqsa Complex": (
                    "A SUPREME ARCHITECTURAL WORKSHOP RECONSTRUCTION of the entire Al-Aqsa complex. "
                    "The Dome of the Rock (Qubbat al-Sakhrah) is the central masterpiece with a "
                    "realistic matte-gold metallic finish. The mosque structure is HOLLOW with "
                    "INTERNAL WARM LIGHTING glowing ONLY through the arched windows and arched gates. "
                    "The surrounding courtyard is made of textured ancient stone cardstock. "
                    "NO fake glows—only the realistic internal radiance of a high-end model. "
                    "The scale is immense, filling a 2-meter wooden workbench. The character is "
                    "hunched over, adjusting a tiny gate with tweezers. Real craft tools and "
                    "sandpaper are visible on the table. Authentic, grounded, and holy."
                ),
                "Mega Diorama: Masjidil Haram": (
                    "A SUPREME PHYSICAL RECONSTRUCTION of the entire Holy Mosque. The scale is immense, "
                    "stretching across the entire workbench. The Kaaba is the focal point, wrapped in "
                    "authentic black textured silk with gold calligraphy. It sits at the center of a "
                    "VAST, OPEN WHITE MARBLE MATAF (courtyard) made of polished matte acrylic. "
                    "The structure is HOLLOW, with INTERNAL WHITE LEDs glowing from the multi-story "
                    "galleries and the tips of the 7 towering white minarets. Thousands of microscopic "
                    "white dots (pilgrims) are visible on the Mataf. NO magical mist—only realistic "
                    "overhead workshop light and internal mosque lighting. Absolute architectural accuracy."
                ),
                "Mega Diorama: Nabawi Cityscape": (
                    "A SPRAWLING URBAN CRAFT DIORAMA of the Prophet's Mosque in Medina. Features hundreds "
                    "of tiny physical green umbrellas and the iconic Green Dome with a realistic matte "
                    "paint finish. The structure is HOLLOW, with INTERNAL WARM AMBER LIGHTING "
                    "shining through the thousands of microscopic window cutouts. The light filters "
                    "naturally onto the white marble floors of the model. NO neon or fake sparkles. "
                    "The complex looks TOWERING and MASSIVE next to the artist's hands. Small piles of "
                    "scrapped wood and glue bottles are visible on the workbench, emphasizing the "
                    "handmade masterpiece vibe. Honest, majestic, and grounded."
                ),
                "Mega Diorama: Blue Mosque Plaza": (
                    "A SUPREME PHYSICAL MODEL of the Blue Mosque (Sultan Ahmed). Features massive "
                    "cascading domes and 6 towering minarets built from textured plaster and wood. "
                    "The structure is HOLLOW, with INTERNAL WARM WHITE LIGHTING glowing ONLY through "
                    "the hundreds of tiny arched windows. The surrounding plaza features microscopic "
                    "hand-painted trees and realistic fountain models on a stone-textured courtyard. "
                    "Natural indoor workshop lighting from a nearby window casts long, realistic "
                    "shadows on the workbench. NO fake glows—only the honest internal radiance of "
                    "a high-end architectural model. Grand, sharp, and grounded."
                ),
                "Mega Diorama: Sheikh Zayed Grandeur": (
                    "A COLOSSAL WHITE MARBLE RECONSTRUCTION on a massive workshop table. Features 82 "
                    "physical white domes and REFLECTIVE RESIN POOLS that mirror the mosque's "
                    "architecture like real water. The structure is HOLLOW, with INTERNAL SOFT BLUE "
                    "AND WHITE LEDS glowing from the base of the pillars and inside the domes, "
                    "matching the actual mosque's night lighting. NO magical mist—just realistic "
                    "room light reflecting off the polished white surfaces. Scraps of white material "
                    "and precision tools are visible on the table's edge. An aura of supreme wealth, "
                    "handcrafted holiness, and architectural perfection."
                ),
                "Mega Diorama: Hassan II Coastal": (
                    "A MASSIVE PHYSICAL DIORAMA of the Hassan II Mosque. The towering 210-meter "
                    "scale minaret dominates the vertical frame, built from textured stone-look material. "
                    "The mosque sits on a VAST ARCHITECTURAL PLATFORM over a realistic CLEAR RESIN OCEAN "
                    "with sculpted white-capped waves. The structure is HOLLOW, with INTERNAL WARM "
                    "LIGHTS glowing through the microscopic Moroccan zellij pattern cutouts on the walls. "
                    "A GREEN LASER LIGHT (physical model part) shines from the top of the minaret "
                    "towards the Qibla, grounded in reality. Standard indoor lighting highlights the "
                    "physical depth and shadows of the structure on the workbench. Breathtaking."
                ),
                "The Grand Mataf: Kaaba Center": (
                    "A COLOSSAL 3D WORKBENCH DIORAMA of the Mataf. The Kaaba at the center is a "
                    "physical cube wrapped in authentic black textured silk with 3D embossed golden "
                    "calligraphy. The surrounding Mataf floor is a VAST, OPEN CIRCULAR COURTYARD "
                    "made of polished white matte acrylic. The structure is HOLLOW, with "
                    "INTERNAL WARM WHITE LIGHTING glowing ONLY through the multi-story arched "
                    "galleries at the edges. NO pillars near the Kaaba—the Mataf area is vast and open. "
                    "Thousands of microscopic white dots (pilgrims) are visible. Standard indoor "
                    "workshop lighting casts realistic shadows onto the table. The character's hands "
                    "are visible at the edge, adjusting a tiny gate. Breathtaking physical scale."
                ),
                "The Clock Tower: Bird's Eye": (
                    "A STUNNING ARCHITECTURAL MODEL of the Makkah complex from a top-down workbench view. "
                    "The Abraj Al-Bait towers are tall physical models made of resin and plastic. "
                    "The massive GREEN CLOCK FACE is ILLUMINATED FROM WITHIN by soft green LEDs, "
                    "matching the actual tower's night look, but with a realistic matte finish. "
                    "The mosque complex below sprawls across the entire wooden table. "
                    "NO fake neon glows—only the honest internal radiance of the model and "
                    "standard ambient workshop light. Captured with a macro-lens, showing the "
                    "real depth and physical layers of the diorama. Grounded in a workshop environment."
                ),
                "Mina: The City of Tents": (
                    "A UNIQUE MEGA DIORAMA of the Valley of Mina. Features tens of thousands of "
                    "microscopic white tents made of folded paper, stretching across a 2-meter long "
                    "workbench. The structure is HOLLOW, with INTERNAL WARM LIGHTING glowing softly "
                    "from under the highway bridges and between the tent rows. NO glowing neon— "
                    "only natural ambient light highlighting the repetitive, physical textures of the "
                    "folded paper. Real tools like a precision cutter and glue bottle are visible "
                    "on the table, emphasizing the handmade work-in-progress vibe. "
                    "Extremely detailed, sprawling, and architecturally accurate."
                ),
                "Jabal Nur & Hira: Moonlight Path": (
                    "A DRAMATIC 3D PHYSICAL DIORAMA of Jabal Nur. The mountain is sculpted from rugged, "
                    "hand-painted grey plaster and rock-like materials. The structure is HOLLOW, with "
                    "INTERNAL AMBER LIGHTS acting as tiny lanterns along the winding mountain path. "
                    "At the base, a sprawling city reconstruction made of tiny plastic blocks sits "
                    "on the workshop table. NO fake AI glows—only the realistic internal radiance "
                    "shining through the carved rock crevices. The contrast is created by realistic "
                    "shadows from a single desk lamp. The scale is immense, filling the frame. "
                    "Hyper-realistic textures of rock vs. smooth city models. Majestic and authentic."
                ),
                "Safa & Marwa: The Marble Gallery": (
                    "A LONG-SCALE PHYSICAL DIORAMA of the Mas'a corridor stretching across the workbench. "
                    "Features thousands of physical white marble arches made of textured cardstock. "
                    "The corridor is HOLLOW and ILLUMINATED FROM WITHIN by soft warm white LEDs "
                    "hidden behind the arches, highlighting the deep architectural perspective. "
                    "NO fake glowing signals—only realistic internal lighting and shadows. "
                    "The mountains at each end (Safa and Marwa) are sculpted from hand-painted plaster "
                    "with visible stone grain. Crafting tools like a ruler and glue are visible nearby, "
                    "emphasizing the handmade work-in-progress vibe. Massive in scale."
                ),
                "The Gate of King Abdulaziz": (
                    "A FOCUS DIORAMA on the massive main gate. The towering twin minarets are tall physical "
                    "models built from wood and resin, dominating the vertical frame. The gate structure "
                    "is HOLLOW, with INTERNAL WARM LIGHTS glowing from the arched entrance and the "
                    "minaret balconies. NO fake LED glows—only the real physical depth of the inner "
                    "courtyards lit from within. The character's hand is actively working on the arched "
                    "entrance with a small brush, looking tiny compared to the towering spires. "
                    "Breathtaking handmade scale and architectural precision."
                ),
                "Mount Arafat: The Sea of Mercy": (
                    "A VAST LANDSCAPE ARCHITECTURAL DIORAMA of Jabal al-Rahmah. The mountain is a "
                    "physical sculpture of rugged grey plaster with visible rock textures. "
                    "Covered in thousands of tiny, hand-painted white dots representing pilgrims. "
                    "The structure is HOLLOW, with INTERNAL AMBER LIGHTS glowing softly through "
                    "microscopic window cutouts on the mountain-top monument. NO fake glowing figures. "
                    "The surrounding plains are textured sand and gravel on the workshop table. "
                    "Lit by a single desk lamp, creating realistic long shadows and a deep sense "
                    "of physical scale. Authentic work-in-progress atmosphere."
                ),
                "The Expansion Area: Modern Marvel": (
                    "A MEGA PHYSICAL DIORAMA of the King Abdullah expansion. Features a sprawling "
                    "complex of domes and marble facades made of polished white acrylic. "
                    "The structure is HOLLOW, with INTERNAL WHITE LEDs glowing through the "
                    "thousands of microscopic architectural window patterns etched into the walls. "
                    "The lighting is honest and bright, reflecting off the smooth matte surfaces "
                    "of the model. NO neon or fake sparkles—only the realistic internal radiance "
                    "of a high-end architectural model in a professional studio. The scale is "
                    "immense, filling the entire workbench. Pure, clean, and grand."
                ),
                "Mecca Old City: Historical Vibes": (
                    "A NOSTALGIC MEGA DIORAMA of historical Mecca. Features thousands of tiny "
                    "physical stone houses with wooden window frames (roshan) and narrow alleys. "
                    "The houses are HOLLOW, with INTERNAL WARM AMBER LIGHTS glowing from within "
                    "the tiny windows, creating a soulful, ancient city atmosphere. NO fake glowing "
                    "jewels—only the honest radiance of a physical model. The Holy Mosque is "
                    "the detailed physical centerpiece. Standard workshop environment with natural "
                    "shadows and real textures. The character is carefully placing a tiny house "
                    "into the urban grid, appearing as a small creator next to the massive city."
                ),
                "Diorama Al-Aqsa: Complete Complex": (
                    "A COLOSSAL PHYSICAL ARCHITECTURAL DIORAMA of the entire Al-Aqsa compound. "
                    "The Dome of the Rock is the central focal point with a realistic matte gold-leaf "
                    "finish. The structure is HOLLOW, with INTERNAL WARM LIGHTS glowing ONLY through "
                    "the arched windows and ancient gates. The compound sprawling across a 2-meter "
                    "wooden table, detailed with tiny physical olive trees and textured stone pathways. "
                    "Standard indoor workshop lighting highlights the physical depth. NO fake glowing "
                    "effects—only the honest internal radiance of the model. The character's hands "
                    "are seen adjusting a microscopic gate with tweezers. Pure handmade aesthetic."
                ),
                "Diorama Blue Mosque: Istanbul Night": (
                    "A GRAND SCALE PHYSICAL MODEL of the Blue Mosque on a workshop table. Features 6 "
                    "towering minarets and cascading domes made of textured grey plaster and wood. "
                    "The structure is HOLLOW, with INTERNAL WARM WHITE LEDS glowing from within the "
                    "hundreds of tiny windows. The surrounding Bosporus strait is made of dark, "
                    "glossy blue resin that reflects the natural overhead room light. NO fake neon— "
                    "only the realistic internal lighting and surface reflections. The scale is "
                    "immense, filling the entire wide frame at an eye-level view to show the "
                    "architectural depth of the handmade city reconstruction. Grounded and sharp."
                ),
                "Diorama Hassan II: The Ocean Giant": (
                    "A MASSIVE PHYSICAL DIORAMA of the Hassan II mosque by the sea. The towering minaret "
                    "is a tall vertical stone-look structure dominating the frame. The mosque "
                    "foundation features high-definition etched Moroccan zellij tilework. The structure "
                    "is HOLLOW with INTERNAL WARM LIGHTS glowing through the wall cutouts. It sits "
                    "over a VAST CLEAR RESIN OCEAN with realistic sculpted white-capped waves. "
                    "Lit by a single desk lamp, creating natural shadows on the workbench. The "
                    "artisan's hand is visible, meticulously polishing the resin water, looking "
                    "tiny next to the massive monument. Breathtakingly grand and authentic."
                )
            }
        }

        # --- 3. MASTER LOKASI (FIXED: REALISTIC WORKSHOP NO GLOW) ---
        MASTER_GRANDMA_SETTING = {
            "Atelier Maestro (Living Studio)": (
                "Inside a professional architectural workshop. The wooden workbench is realistically "
                "cluttered with functional micro-tools: fine-tip tweezers, small jars of matte paint, "
                "precision cutters, and a used cup of coffee. In the background, technical sketches "
                "of the mosque are pinned to a wooden board. A desk magnifying lamp is positioned over "
                "the table. The lighting is bright and practical, coming from overhead workshop bulbs, "
                "casting natural, honest shadows. Focus on the raw, creative atmosphere of a master artisan."
            ),
            "Galeri Antik (The Collector's Vault)": (
                "A sophisticated private gallery with dark oak shelves. The background features other "
                "finished architectural models under clear glass covers with natural matte reflections. "
                "No fake glows. The workbench is clean but shows signs of active work with small "
                "polishing cloths and jars of wax nearby. Lighting is a focused warm spotlight on the "
                "main diorama, creating high-contrast but realistic depth and shadows. "
                "Exudes a prestigious, museum-quality workshop vibe."
            ),
            "Workshop Loteng (The Dreamer's Attic)": (
                "A rustic attic workshop with exposed wooden beams and a large window showing a "
                "neutral evening sky. The workbench is covered in realistic wood shavings, tiny sandpaper strips, "
                "and scraps of raw materials. A single vintage desk lamp provides the primary light source, "
                "casting long, sharp, realistic shadows across the diorama and the artisan's hands. "
                "No magical effects—just a peaceful, authentic, and hardworking workshop environment."
            ),
            "Ruang Kerja Kerajaan (Royal Library)": (
                "A sophisticated study room with tall mahogany bookshelves filled with antique books. "
                "The large wooden desk is an active workspace, featuring a silver tray of dates and "
                "realistic architectural drafting tools. The window frames have deep Islamic geometric carvings. "
                "Lighting is NATURAL AND GROUNDED, coming from a single direction to create realistic "
                "physical depth and shadows on the mosque diorama. NO magical glows or fake particles— "
                "just the rich, matte textures of wood, paper, and stone. High-end, historical, and authentic."
            ),
            "Studio Kaca (The Modern Sanctuary)": (
                "A sleek, minimalist professional studio with large glass windows overlooking a garden. "
                "The white desk is clean but functional, holding a small bonsai and various architectural "
                "modeling tools like precision calipers and cutters. Background features a soft-focus "
                "textured wall. Lighting is BRIGHT, CLEAN, AND EVEN, coming from modern ceiling panels, "
                "highlighting the flawless surfaces of the diorama. NO fake blue neon, NO glowing tablets, "
                "and NO artificial lens flares. Minimalist architectural luxury and pure reality."
            ),
            "Bengkel Klasik (The Clockmaker's Style)": (
                "A rustic, authentic workshop with antique brass tools and gears displayed on the walls. "
                "The workbench is made of thick, scarred reclaimed wood, cluttered with jars of "
                "colored sand, crushed minerals, and small bottles of wood stain. Standard workshop "
                "lighting with a SINGLE ADJUSTABLE DESK LAMP that focuses SHARPLY on the diorama, "
                "casting realistic, deep shadows. NO glowing tubes, NO cinematic filters, and NO mist— "
                "just the raw, honest atmosphere of a high-end traditional craft studio. Grounded and tactile."
            ),
            "Pendopo (The Zen Pavilion)": (
                "An elegant open-air Javanese pavilion with polished teak pillars. The background shows "
                "a calm koi pond with floating lilies. The workbench is a low wooden table (meja lesehan) "
                "where the character sits cross-legged. Traditional 'Wayang' puppets are subtly visible "
                "on the pillars. NATURAL DAYLIGHT provides a clear, honest view of the mosque's "
                "intricate surfaces and sharp, realistic shadows. NO magical smoke, NO glowing particles— "
                "just a peaceful, authentic outdoor workshop atmosphere. Grounded in a traditional setting."
            ),
            "Bilik Rahasia (The Hidden Archive)": (
                "A dedicated workspace in a room filled with floor-to-ceiling historical maps and "
                "old mosque photographs. The desk is an active, messy workstation with real gold leaf "
                "sheets, pigment vials, and precision tweezers. Lighting is PRACTICAL, from a SINGLE "
                "VINTAGE HANGING LAMP that casts sharp, realistic shadows across the diorama. "
                "NO glowing lanterns, NO fake flares—just the intense, focused environment of a "
                "master craftsman at work. The atmosphere is quiet, academic, and deeply authentic."
            ),
            "Teras Rumah Asri (The Zen Veranda)": (
                "On a clean wooden veranda of a lush village house. In the background, a small koi pond "
                "with a stone waterfall is visible. The workbench is an outdoor wooden table cluttered "
                "with craft tools. BRIGHT, NATURAL MORNING SUNLIGHT illuminates the scene, highlighting "
                "the real physical textures of the mosque diorama. NO fake reflections, NO artificial "
                "glare—only the natural highlights from the sun. Pure, fresh, and grounded in reality."
            ),
            "Pondok Tepi Sawah (Rice Field Sanctuary)": (
                "Inside a rustic bamboo gazebo (saung) overlooking vast emerald-green rice terraces. "
                "The character sits on the bamboo floor (lesehan style) at a low wooden workbench. "
                "NATURAL DAYLIGHT from the open sky provides bright, high-contrast lighting with "
                "realistic sharp shadows cast by the saung's pillars. The diorama looks massive and "
                "detailed against the soft-focus rural background. NO magical mist, NO glowing particles— "
                "just the honest, physical presence of a master artisan. Realistic textures of bamboo, "
                "wood, and craft materials. High-fidelity architectural details."
            ),
            "Kebun Bunga (The Floral Garden)": (
                "In the middle of a vibrant, well-kept flower garden. The character is working at "
                "a rustic wooden workbench placed on a stone path. Surroundings are filled with "
                "blooming jasmine and colorful bougainvillea in soft focus. NATURAL, BRIGHT DAYLIGHT "
                "illuminates the diorama, showing real physical shadows and textures. NO magical "
                "filters—just the honest, fresh atmosphere of an outdoor garden workshop. "
                "Real crafting tools like precision cutters and glue jars are visible next to the "
                "mosque model, emphasizing the handmade work-in-progress vibe."
            ),
            "Kebun Buah (The Orchard Atelier)": (
                "Under the shade of a heavy-fruiting mango and orange tree orchard. The workbench is "
                "a heavy, rustic wooden slab stained with age. NATURAL SUNLIGHT filters through the "
                "leaves, creating REALISTIC DAPPLED SHADOWS (cahaya tembus daun) on the table surface "
                "and the diorama. NO artificial glow—only the authentic sunlight highlights. "
                "Hanging fruits are visible in the soft-focus background. The atmosphere is earthy "
                "and authentic, focused on the physical labor of the artisan. Sharp, high-definition "
                "architectural details on the mosque diorama."
            ),
            "Taman Air Terjun (The Secret Waterfall)": (
                "A private garden sanctuary featuring a natural stone waterfall in the background. "
                "The workbench is positioned near the water, with REALISTIC MOISTURE and mossy rocks "
                "nearby. NATURAL DAYLIGHT provides clear visibility of the mosque's materials. "
                "NO 'mystical haze', NO fake glowing particles—only the natural, high-definition "
                "visual of a hardworking artisan's space. High-fidelity textures of stone, water, "
                "and the diorama materials are highlighted by sharp, realistic shadows. "
                "Grounded and refreshing workshop vibe."
            ),
            "Halaman Belakang (Garden Glow)": (
                "A tidy backyard garden with a green lawn. The character works at a simple wooden table "
                "on the terrace. In the background, a small wooden bridge over a stream is visible. "
                "The lighting is CLEAR, NATURAL AFTERNOON SUN, casting realistic long shadows. "
                "NO fireflies, NO magical glows—just the homey, peaceful reality of a backyard "
                "hobbyist working on a masterpiece. Crafting debris, sandpaper, and tools are "
                "scattered on the table, emphasizing the authentic work-in-progress vibe."
            ),
            "Tepi Danau (Lakeside Workshop)": (
                "A wooden deck overlooking a calm lake during a clear afternoon. The workbench is "
                "a heavy timber table placed outdoors. The background features a soft-focus lake "
                "and distant hills under NATURAL, BRIGHT DAYLIGHT. NO dramatic purple skies, "
                "NO fake lens flares—just the honest, high-contrast light of the sun hitting "
                "the mosque's intricate surfaces. Real craft tools like precision cutters, rulers, "
                "and glue bottles are scattered on the deck, creating a grounded, authentic atmosphere."
            ),
            "Gubuk Estetik (The Luxury Rustic)": (
                "A high-end rustic wooden cabin with a large open window facing a green pine forest. "
                "The interior workbench is made of thick, scarred wood, cluttered with clay vases "
                "and tidy woodcraft tools. Lighting is PRACTICAL, coming from the large window, "
                "casting natural and deep shadows on the mosque diorama. NO mysterious blue mist, "
                "NO glowing runes—just the clean, high-definition reality of a professional "
                "artisan's cabin. Microscopic textures of wood grain and craft materials are sharp."
            )
        }

        # --- 5. MASTER DIALOG NYESEK (GROUPED BY CHARACTER ROLE) ---
        MASTER_NYESEK_DIALOG = {
            "NENEK": [
                "Cucu-cucuku yang baik... kalau jari kalian nggak berat, bantu nenek sebarkan keindahan masjid ini ya. Satu subscribe dari kalian itu seperti semangat baru buat napas nenek yang sudah tua ini...",
                "Jangan sedih ya kalau video nenek sepi, engga ada yang like dan subscribe... Nenek sudah biasa. Nenek cuma titip satu, jangan biarkan masjid aslinya sepi seperti video nenek ini ya...",
                "Nenek tahu nenek nggak secantik artis yang sering kalian tonton. Tapi masjid ini nenek buat dengan doa... apa karya orang tua seperti ini sudah tidak ada tempat lagi di hati kalian?",
                "Tangan nenek sudah sering kram sekarang, Cu... Mungkin ini masjid terakhir yang bisa nenek selesaikan. Tolong dijaga videonya ya, biar jadi kenangan kalau nenek pernah ada...",
                "Setiap malam nenek nungguin, ada nggak ya yang mau berteman sama nenek di YouTube? Ternyata susah ya cari perhatian anak muda kalau nggak pakai baju bagus..."
            ],
            "KAKEK": [
                "Banyak yang skip video kakek karena bukan joget-joget. Kakek cuma tukang tua yang ingin bikin miniatur Masjid. Gak ada yang like pun, kakek tetap akan selesaikan kubah ini dengan cinta...",
                "Mata kakek sudah remang-remang, Cu... kakek buru-buru selesaikan ini sebelum semuanya jadi gelap. Kakek cuma ingin tahu kalau masih ada yang peduli lewat satu klik subscribe saja...",
                "Di rumah ini sepi sekali, Cu... cuma suara lem dan gunting ini yang menemani kakek. Makanya kakek senang kalau ada notifikasi subscribe masuk, rasanya kakek seperti punya cucu baru...",
                "Kakek sering diketawain tetangga, katanya buat apa bikin masjid dari barang bekas, nggak bakal laku. Tapi kakek percaya, di luar sana pasti ada orang baik seperti kalian...",
                "Kakek sudah terlalu tua untuk paham angka-angka di layar ini. Kakek cuma ingin bangga sedikit di sisa umur kakek, melihat banyak orang yang suka rumah Allah ini..."
            ],
            "GADIS": [
                "Banyak yang bilang aku aneh, mainan barang bekas terus... Katanya lebih baik kerja jadi buruh pabrik. Tapi siapa lagi yang mau jaga keindahan masjid kalau bukan kita, Cu?",
                "Malu sebenarnya upload ke YouTube begini, takut dibilang pamer. Tapi kalau nggak di-upload, siapa yang tahu kalau sampah bisa jadi megah? Kenapa video orang kaya lebih banyak yang suka ya?",
                "Aku nggak punya modal buat beli bahan mewah, makanya aku pakai bahan seadanya ini. Aku cuma ingin buktiin kalau untuk cinta rumah Tuhan, kita nggak harus kaya. Bantu subscribe ya...",
                "Setiap malam aku bantu kakek selesaikan ini. Sedih rasanya liat kakek semangat tapi videonya selalu sepi. Boleh bantu kasih kakek senyuman lewat satu like kalian?",
                "Mungkin karyaku nggak sempurna, tapi aku buat ini sambil jagain kakek yang sudah sepuh. Satu subscribe kalian berarti banget buat semangat kami berdua..."
            ]
        }
        # --- 4. MASTER AUDIO & SOULFUL EXPRESSION (FIXED WORKSHOP INTERACTION) ---
        MASTER_AUDIO_STYLE = {
            "Logat": [
                "Authentic Rural Indonesian (Simple, honest, with a slight 'kampungan' lilt)",
                "Deep Javanese Heart (Soft-spoken, slow, with heavy 'd' and 't' consonants)",
                "Melodic Sundanese (Gentle, flowing tones with a soft West Javanese rise and fall)",
                "Coastal Melayu (Raspy, rhythmic, with a warm seaside gravelly texture)",
                "Classic Betawi Old-Soul (Deep, direct, but profoundly humble and polite)"
            ],
            "Mood": [
                "Trembling Vulnerability (Voice cracking slightly, holding back a deep ocean of emotion)",
                "Fragmented Whispers (Slow, hesitant speech with long natural pauses and soft sighs)",
                "Weary Gratitude (Deeply tired, exhaling long breaths between words of deep thanks)",
                "Shy Humility (Very low volume, almost whispering, as if afraid to take up space)",
                "Bittersweet Resignation (A voice that smiles through pain, sounds both strong and sad)",
                "Soulful Murmur (Continuous soft muttering of 'Alhamdulillah' between sentences)",
                "Dry Fasting Thirst (Voice sounds parched, tight throat, effortful speech from fasting)",
                "Prayer-like Reverence (Shaky, devoted tone, like speaking directly to the Creator)"
            ],
            "Physical Action": [
                "Micro-shaking fingers delicately adjusting a tiny ornament on the massive mosque entrance",
                "Subtle jaw trembling while focusing deeply on the intricate architectural details",
                "Eyes glistening with unshed tears, looking down at the workbench with deep devotion",
                "Deep, slow swallowing with visible movement in the aged throat while working on the dome",
                "Gently stroking the textured surface of the large diorama as if it were a living soul",
                "Head tilting slightly with a faint, bittersweet smile while staring at the complex work",
                "A long, shaky exhale that makes the shoulders drop while leaning over the workbench",
                "Softly licking dry, chapped lips while meticulously placing a small fragment with tweezers",
                "Trembling hands hovering over the towering minarets, afraid to touch their perfection",
                "Closing eyes for a second, inhaling the scent of materials and glue with silent devotion",
                "Fingertips tracing the stone-like texture of the diorama with extreme reverence",
                "Briefly glancing up with hope, then immediately returning focus to the craftsmanship on the table"
            ]
        }
        # --- UI LAYOUT ---        
        with st.expander("👨‍👩‍👧‍👦 PINTAR NENEK ENGINE", expanded=True):
            # --- BARIS 1: MODUS KONTEN (OTAK UTAMA) ---
            st.markdown('<p class="small-label">PILIH MODUS KONTEN</p>', unsafe_allow_html=True)
            modus_konten = st.selectbox("Select Mode", list(MASTER_KONTEN_ALL.keys()), label_visibility="collapsed")
            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<p class="small-label">PILIH KARAKTER</p>', unsafe_allow_html=True)
                pilihan_user = st.selectbox("Select Character", list(MASTER_FAMILY_SOUL.keys()), label_visibility="collapsed")
                char_key = pilihan_user 

            with c2:
                st.markdown(f'<p class="small-label">PAKAIAN {char_key.split(" (")[0].upper()}</p>', unsafe_allow_html=True)
                if char_key in MASTER_FAMILY_WARDROBE:
                    baju_options = list(MASTER_FAMILY_WARDROBE[char_key].keys())
                else:
                    baju_options = ["Standard Daily Wear"]
                baju_pilihan = st.selectbox("Select Wardrobe", baju_options, label_visibility="collapsed")
            
            c3, c4 = st.columns(2)
            with c3:
                label_obj = "PILIH KOLEKSI DIORAMA" if "Diorama" in modus_konten else "DETAIL OBJEK / KARYA"
                st.markdown(f'<p class="small-label">{label_obj}</p>', unsafe_allow_html=True)
                objek_list = list(MASTER_KONTEN_ALL[modus_konten].keys())
                pilihan_objek = st.selectbox("Select Detail", objek_list, label_visibility="collapsed")
                deskripsi_teknis = MASTER_KONTEN_ALL[modus_konten][pilihan_objek]
            with c4:
                st.markdown('<p class="small-label">SETTING LOKASI</p>', unsafe_allow_html=True)
                pilihan_set = st.selectbox("Select Environment", list(MASTER_GRANDMA_SETTING.keys()), label_visibility="collapsed")
            
            st.divider()
            
            c5, c6 = st.columns([2, 1])
            with c5:
                st.markdown('<p class="small-label">DIALOG (NATURAL INDONESIAN)</p>', unsafe_allow_html=True)
                
                # 1. SIAPIN KANTONG (Session State)
                if 'current_dialog' not in st.session_state:
                    st.session_state.current_dialog = ""

                # 2. FUNGSI PEMBANTU (Wajib ditaruh di sini)
                def handle_kocok():
                    # Ambil kategori
                    if "Nenek" in char_key:
                        kat = "NENEK"
                    elif "Kakek" in char_key:
                        kat = "KAKEK"
                    else:
                        kat = "GADIS"
                    # Ambil random dan masukkan ke KEY text_area langsung
                    new_val = random.choice(MASTER_NYESEK_DIALOG[kat])
                    st.session_state["input_dialog_key"] = new_val
                    st.session_state.current_dialog = new_val

                # 3. TOMBOL KOCOK (Pake on_click)
                st.button("🎲 KOCOK DIALOG NYESEK", use_container_width=True, on_click=handle_kocok)

                # 4. TEXT AREA (Kuncinya di parameter 'key')
                user_dialog = st.text_area(
                    "Input Dialog", 
                    placeholder=f"Tulis dialog {char_key.split(' (')[0]} di sini...",
                    height=150, 
                    label_visibility="collapsed",
                    key="input_dialog_key" # Ini nyambung ke handle_kocok
                )
                
                # Update state biar sinkron
                st.session_state.current_dialog = user_dialog

            with c6:
                st.markdown('<p class="small-label">ACTING & PERFORMANCE</p>', unsafe_allow_html=True)
                pilih_logat = st.selectbox("Pilih Logat", MASTER_AUDIO_STYLE["Logat"])
                pilih_mood = st.selectbox("Pilih Mood", MASTER_AUDIO_STYLE["Mood"])
                
                # Tetap pake random choice buat Physical Action biar visualnya selalu dinamis
                pilih_aksi = random.choice(MASTER_AUDIO_STYLE["Physical Action"])

            st.write("")
            btn_gen = st.button(
                "🚀 GENERATE VIDEO PROMPT", 
                type="primary", 
                use_container_width=True, 
                key="btn_generate_video"
            )
        # --- LOGIC GENERATOR (FIXED: SEPARATION, FRONT VIEW, SLOW ZOOM) ---
        if btn_gen:
            if not user_dialog:
                st.error("Isi dialognya dulu bos...")
            else:
                # --- 4. DYNAMIC SCENE LOGIC (STATIC / ULTRA SLOW CRAWL) ---
                is_lesehan = any(x in pilihan_set.lower() for x in ["teras", "saung", "halaman", "pondok", "pendopo"])
                
                # Nenek di belakang meja (Background), Masjid di atas meja (Foreground)
                posisi_nenek = "sitting on the floor (lesehan) BEHIND the low table" if is_lesehan else "standing BEHIND the workbench"
                
                scene_context = (
                    f"PHOTO-REALISTIC CINEMATIC FILM STILL. FRONT-FACING STRAIGHT ANGLE. "
                    f"STILL CAMERA SHOT with a BARELY VISIBLE, MINISCULE SLOW CRAWL towards the mosque. " 
                    f"The camera is almost static, moving at a snail's pace to maintain focus. "
                    f"STRICT DEPTH LAYERING: The large mosque diorama is the main focus in the FOREGROUND. "
                    f"The character (Indonesian grandma) is positioned BEHIND the table and the mosque. "
                    f"There is a CLEAR PHYSICAL GAP between the grandma and the mosque object. "
                    f"The mosque has 4 distinct minarets and 1 large central dome. "
                    f"The scene is grounded, realistic, and strictly tabletop. No body-fusion. "
                    f"Pure high-end cinematography, steady and calm."
                )

                # --- 5. NUANSA HIDUP (NATURAL GAZE SHIFT) ---
                env_detail = MASTER_GRANDMA_SETTING.get(pilihan_set, "Inside a clean workshop.")
                
                # Biar nggak melotot terus, kita buat dia fokus ke kerjaan juga
                eye_lock = (
                    "The character is deeply focused on their work, looking DOWNWARD at the mosque structure. "
                    "They ONLY shift their gaze to look at the camera BRIEFLY when speaking a sentence. "
                    "Natural blinking and shifting focus between the craft and the viewer. "
                    "Their eyes are alive, expressive, and human—not staring blankly. "
                    "Hands and eyes are synchronized with the artisan's performance."
                )

                living_details = (
                    f"ENVIRONMENT: {env_detail}. {eye_lock} "
                    "Natural workshop lighting with soft shadows casting on the table surface. "
                    "High-fidelity skin textures and detailed architectural surfaces."
                )
                
                # --- 6. RAKIT FINAL PROMPT (STRICT TWO HANDS & FRONT LOOK) ---
                soul_desc = MASTER_FAMILY_SOUL.get(pilihan_user, "An Indonesian person.")
                wardrobe_dict = MASTER_FAMILY_WARDROBE.get(char_key, {})
                baju_desc = wardrobe_dict.get(baju_pilihan, "Simple modest clothes, clean and neat.")
                
                ANATOMY_LOCK = (
                    "STRICTLY ONLY TWO HUMAN HANDS VISIBLE. NO GHOST HANDS. NO EXTRA LIMBS. "
                    "The artisan has exactly two hands with five fingers each, physically touching the model. "
                    "Hands are separate from the mosque walls. Human skin vs craft material."
                )

                MANDATORY_LOCK = (
                    "MANDATORY: FULL HIJAB. NO HAIR SHOWING. NO NECK SHOWING. "
                    "FULLY COVERED MODEST ISLAMIC CLOTHING. NO SKIN EXPOSED EXCEPT FACE AND HANDS."
                )
                
                final_ai_prompt = (
                    f"{scene_context} \n\n"
                    f"CHARACTER DNA: {soul_desc}. {ANATOMY_LOCK} {MANDATORY_LOCK} \n"
                    f"WARDROBE: {baju_desc}. \n"
                    f"PERFORMANCE: {pilih_aksi} with EXACTLY TWO HANDS. The character shifts gaze between the work and the camera. {pilih_mood}. \n"
                    f"THE MASTERPIECE: {deskripsi_teknis}. "
                    f"The mosque is a massive, separate tabletop model. \n"
                    f"VOICE & DIALOG: {user_dialog} (Delivered with {pilih_logat}). \n"
                    f"ATMOSPHERE: {living_details} \n\n"
                    f"TECHNICAL SPECS: ARRI Alexa 65, Frontal Eye-Level shot, BARELY MOVING CRAWL, "
                    f"sharp focus on mosque details and hands, no double-limbs, masterpiece quality."
                )
                # --- 7. TAMPILKAN HASIL ---
                st.success("🔥 PROMPT BERHASIL DIRAKIT!")
                st.markdown('<p class="small-label">SALIN PROMPT DI BAWAH INI:</p>', unsafe_allow_html=True)
                st.code(final_ai_prompt, language="text")
                
                with st.expander("Edit Prompt Manual"):
                    final_ai_prompt = st.text_area("Custom Editor", value=final_ai_prompt, height=300)
                
    # ============================================================
    # --- TAB: ⚡ TRANSFORMATION ENGINE (ULTIMATE SULTAN EDITION) ---
    # ============================================================
    with t_transform:        
        with st.expander("⚡ PINTAR TRANFORMATION ENGINE", expanded=True):
            st.markdown('<p class="small-label" style="margin-bottom: -15px;">🌍 LOKASI & ATMOSFER (SCENE SETTING)</p>', unsafe_allow_html=True)
            
            user_scene = st.text_area(
                "label_hidden", # Label ini nggak bakal kelihatan karena setting di bawah
                placeholder="Contoh: Di teras rumah kayu tua saat hujan badai malam hari, lampu bohlam bergoyang, ada kabut tipis.", 
                height=70,
                label_visibility="collapsed" 
            )

            # --- ROW 2: KARAKTER & DUAL DIALOG ---
            col_l, col_r = st.columns(2)
            
            with col_l:
                st.markdown('<p class="small-label" style="margin-bottom: -15px;">⬅️ KARAKTER SISI KIRI (LEFT)</p>', unsafe_allow_html=True)
                c_l_name = st.text_input("l_name", placeholder="Contoh: Lionel Messi", label_visibility="collapsed")
                c_l_outfit = st.text_input("l_outfit", placeholder="Contoh: Jas hitam formal, rapi.", label_visibility="collapsed")
                c_l_speech = st.text_area("l_speech", placeholder="Apa yang diucapkan tokoh kiri?", height=60, label_visibility="collapsed")
                is_trans_l = st.checkbox("🔥 Karakter Kiri Berubah", key="trans_l")

            with col_r:
                st.markdown('<p class="small-label" style="margin-bottom: -15px;">➡️ KARAKTER SISI KANAN (RIGHT)</p>', unsafe_allow_html=True)
                c_r_name = st.text_input("r_name", placeholder="Contoh: Cristiano Ronaldo", label_visibility="collapsed")
                c_r_outfit = st.text_input("r_outfit", placeholder="Contoh: Baju koko putih, peci hitam.", label_visibility="collapsed")
                c_r_speech = st.text_area("r_speech", placeholder="Apa yang diucapkan tokoh kanan?", height=60, label_visibility="collapsed")
                is_trans_r = st.checkbox("🔥 Karakter Kanan Berubah", key="trans_r")

            # --- ROW 3: AKSI & KAMERA ---
            st.markdown('<p class="small-label" style="margin-bottom: -15px;">🏃 PHYSICAL ACTION (PERGERAKAN TUBUH)</p>', unsafe_allow_html=True)
            st.caption("Deskripsikan pergerakan fisik karakter secara detail.")
            user_action = st.text_area(
                "action_input", 
                placeholder="Contoh: Messi berjalan mendekat ke arah Ronaldo dengan langkah berat, tangan mengepal kuat.", 
                height=70, 
                label_visibility="collapsed"
            )

            st.markdown('<p class="small-label" style="margin-bottom: -15px;">🎥 CAMERA CONTROL (SINEMATOGRAFI)</p>', unsafe_allow_html=True)
            cc1, cc2 = st.columns(2)
            with cc1:
                st.caption("Gerakan Kamera (Movement)")
                cam_movement = st.selectbox(
                    "cam_move", 
                    ["Static (Diam)", "Slow Zoom In", "Slow Zoom Out", "Pan Left to Right", "Pan Right to Left", "Dynamic Tracking Shot", "Handheld Shake (High Tension)"],
                    label_visibility="collapsed"
                )
            with cc2:
                st.caption("Sudut Pandang (Angle)")
                cam_angle = st.selectbox(
                    "cam_ang", 
                    ["Eye Level", "Low Angle (Heroic)", "High Angle", "Cinematic Close-up", "Wide Establishing Shot"],
                    label_visibility="collapsed"
                )

            # --- INISIALISASI DEFAULT (PENTING BIAR GAK ERROR) ---
            trans_type = "None"
            trans_speed = "Steady"
            trans_trigger = "None"
            env_fx = []

            # --- ROW 4: DETAIL TRANSFORMASI ---
            if is_trans_l or is_trans_r:
                st.divider()
                st.markdown('<p class="small-label" style="margin-bottom: -15px;">⚡ METAMORFOSIS SETTINGS</p>', unsafe_allow_html=True)
                
                t1, t2, t3 = st.columns(3)
                with t1:
                    st.caption("Jenis Perubahan")
                    trans_type = st.selectbox("trans_type_box", [
                        "Anatomical Titan (Real Muscle & Bone)", 
                        "Super Saiyan (God Aura & Electric)", 
                        "Mecha-Hybrid (Liquid Metal/Robot)", 
                        "Ethereal God (Cosmic/Nebula)",
                        "Instant Obesity (Jiggling Fat)",
                        "Ultra-Skinny (Malnourished Bone)",
                        "Squashed & Short (Hobbit Style)",
                        "Extreme Tall & Lanky (Slender Style)"
                    ], label_visibility="collapsed")
                    
                    st.caption("Kecepatan Transisi")
                    trans_speed = st.select_slider("speed_slider", options=["Slow & Smooth", "Steady", "Explosive"], label_visibility="collapsed")
                
                with t2:
                    st.caption("Aksi Pemicu (Trigger)")
                    # Gue tambahin placeholder yang ngingetin buat jaga identitas muka
                    trans_trigger = st.text_input("trigger_input", 
                        placeholder="Contoh: Bersin (Tetap wajah Udin) / Marah", 
                        label_visibility="collapsed")
                                    
                with t3:
                    st.caption("Efek Lingkungan")
                    env_fx = st.multiselect("env_fx_box", 
                                           ["Lantai Retak & Hancur", "Gravitasi Terbalik (Melayang)", 
                                            "Shockwave Udara", "Ledakan Lampu & Listrik", "Kabut & Debu Sinematik"],
                                           default=["Kabut & Debu Sinematik"], label_visibility="collapsed")
            
            # Tombol ditaruh di luar IF biar selalu muncul
            btn_generate = st.button("🚀 GENERATE ALL PROMPT", type="primary", use_container_width=True)

        # --- 2. OUTPUT AREA (IDENTITAS EKSKLUSIF SULTAN) ---
        if btn_generate:
            # DNA KUALITAS TINGGI (UPGRADED: THE GRITTY REALITY & NO TEXT)
            sultan_quality_logic = (
                "Candid handheld photography style, 35mm film grain, high ISO noise. "
                "Dirty lens, natural muted earth tones, desaturated colors. "
                "Environment Detail: Cracked concrete, weathered structures, dry overgrown weeds, "
                "floating dust particles, muddy water reflections. "
                "Material Detail: Realistic fabric wrinkles on clothes, wet textures, "
                "gritty surface details, cinematic shadows, natural lighting. "
                "STRICTLY NO TEXT, NO CAPTIONS, NO WATERMARKS, NO DIGITAL SMOOTHING. "
                "Maintain original character facial features and proportions, DO NOT change to generic humans."
            )

            # MANTRA VISUAL SULTAN (BODY MORPHING COMEDY)
            sultan_mantra_box = {
                "Anatomical Titan (Real Muscle & Bone)": "Hyper-realistic muscle fibers expanding from the body, pulsating veins, gritty anatomical detail, intense steam evaporating. Maintain original facial features and identity.",
                "Super Saiyan (God Aura & Electric)": "Golden translucent energy aura erupting, high-voltage electric sparks, hair turns spiky golden. The face must remain identical to the original character.",
                "Mecha-Hybrid (Liquid Metal/Robot)": "Skin transforming into brushed titanium plates, hydraulic pistons moving under the skin. Facial identity must be strictly preserved without changing facial structure.",
                "Ethereal God (Cosmic/Nebula)": "Body turning into a translucent cosmic nebula, swirling galaxies inside. The core facial features and eyes must remain recognizable as the original character.",
                "Instant Obesity (Jiggling Fat)": "Extreme rapid inflation of body fat from the neck down. Massive belly and double chin expanding, realistic fat jiggling physics. DO NOT alter the core facial structure, keep the original face and identity.",
                "Ultra-Skinny (Malnourished Bone)": "Body rapidly shrinks to a skeletal frame from the neck down. Ribcage highly visible, skin tightens over bones. Face maintains core identity with sunken cheeks but same features.",
                "Squashed & Short (Hobbit Style)": "Violent vertical compression of the entire body. Limbs become short and stubby, torso becomes wide. Maintain accurate facial proportions and original character face on a miniature scale.",
                "Extreme Tall & Lanky (Slender Style)": "Limbs and neck stretch uncontrollably. Body becomes thin and elongated. Face identity must be locked and remain unchanged while movement becomes awkward."
            }

            # A. RAKIT PROMPT GAMBAR (sultan_image_dna)
            sultan_image_dna = (
                f"MASTER IMAGE (Spatial Split): Two distinct characters. "
                f"POSITION LEFT: {c_l_name} wearing {c_l_outfit}. "
                f"POSITION RIGHT: {c_r_name} wearing {c_r_outfit}. "
                f"LOCATION: {user_scene}. {sultan_quality_logic} "
                f"9:16 vertical frame, handheld camera, raw footage style."
            )

            # B. RAKIT PROMPT VIDEO (sultan_video_story)
            s_target = f"LEFT ({c_l_name})" if is_trans_l else f"RIGHT ({c_r_name})" if is_trans_r else "Both Characters"
            s_smooth = "smoothly and gradually morphing" if (is_trans_l or is_trans_r) and trans_speed == "Slow & Smooth" else "violently exploding"
            
            s_fx = ""
            if (is_trans_l or is_trans_r):
                if "Lantai Retak & Hancur" in env_fx: s_fx += "The ground beneath cracks. "
                if "Gravitasi Terbalik (Melayang)" in env_fx: s_fx += "Objects float upwards. "
                if "Shockwave Udara" in env_fx: s_fx += "Air shockwave distorts space. "
                if "Ledakan Lampu & Listrik" in env_fx: s_fx += "Lights explode with electric sparks. "
                if "Kabut & Debu Sinematik" in env_fx: s_fx += "Volumetric fog and dust. "

            # --- LOGIKA DIALOG SULTAN (ANTI BEREBUT) ---
            if c_l_speech and not c_r_speech:
                s_dialog = f"{c_l_name} (Left) is speaking clearly: '{c_l_speech}', while {c_r_name} (Right) remains SILENT, listening with NO mouth movement."
            elif c_r_speech and not c_l_speech:
                s_dialog = f"{c_r_name} (Right) is speaking clearly: '{c_r_speech}', while {c_l_name} (Left) remains SILENT, listening with NO mouth movement."
            elif c_l_speech and c_r_speech:
                s_dialog = f"Both characters are talking. {c_l_name} (Left) says '{c_l_speech}' and {c_r_name} (Right) says '{c_r_speech}'."
            else:
                s_dialog = "Both characters are silent, maintaining natural facial expressions."

            facing_logic = (
                "The characters are positioned in a profile view, facing each other directly. "
                "Intense eye contact between the two characters."
            )

            # --- RAKIT CERITA (STEP BY STEP) ---
            sultan_video_story = (
                f"STORY SEQUENCE: Starting from the reference image. "
                f"CAMERA: {cam_angle} with {cam_movement} movement. \n\n"
                f"1. POSITIONING: {facing_logic} \n"
                f"2. PHYSICAL MOTION: {user_action}. \n"
                f"3. DIALOGUE PERFORMANCE: {s_dialog} "
                "Ensure realistic mouth movements and lip-sync ONLY for the speaking character. \n"
            )
            
            if is_trans_l or is_trans_r:
                # FIX: Menggunakan sultan_mantra_box yang sudah lo buat di atas
                sultan_video_story += (
                    f"4. CLIMAX: While {trans_trigger.lower()}, {s_target} initiates {trans_type}. "
                    f"The character is {s_smooth}. {sultan_mantra_box[trans_type]} "
                    f"Clothing Physics: Realistic fabric tearing. {s_fx} "
                    f"{sultan_quality_logic} High tension cinematic climax."
                )
            else:
                sultan_video_story += f"4. FINAL: Cinematic camera movement. {sultan_quality_logic}"

            # --- TAMPILAN HASIL ---
            st.divider()
            st.success("✅ ULTIMATE PROMPT READY!")
            
            st.markdown("#### 🎨 1. PROMPT GAMBAR")
            st.code(sultan_image_dna, language="text")
            
            st.markdown("#### 🎬 2. PROMPT VIDEO")
            st.code(sultan_video_story, language="text")
                
    with t_random:
        st.status("Sedang proses...", expanded=False)
     
                
def tampilkan_gudang_ide():
    # --- 1. CSS OVERLAY ---
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
            st.markdown("""
                <div class="loading-overlay">
                    <h1 style="font-size: 60px; margin-bottom: 10px;">✅</h1>
                    <h2 style='color: white; letter-spacing: 2px;'>BERHASIL TERPASANG</h2>
                    <p style='color: #1d976c; font-weight: bold;'>CEK RUANG PRODUKSI SEKARANG</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="loading-overlay">
                    <div class="spinner"></div>
                    <h2 style='color: white; letter-spacing: 2px;'>MENGAMBIL DATA...</h2>
                    <p style='color: #8b949e;'>Sinkronisasi ke Cloud Database PINTAR</p>
                </div>
            """, unsafe_allow_html=True)
            
    # --- 3. DATA & GRID RENDER ---
    user_sekarang = st.session_state.get("user_aktif", "tamu").lower()
    user_level = st.session_state.get("user_level", "STAFF") 
    tz_wib = pytz.timezone('Asia/Jakarta')

    try:
        # OPTIMASI 1: Pake fungsi cache biar ganti menu instan
        df_gudang_raw = ambil_data_segar("Gudang_Ide")
        
        if not df_gudang_raw.empty:
            df_gudang_raw.columns = [str(c).strip().upper() for c in df_gudang_raw.columns]
            
            # Filter: Buang spasi, jadikan huruf besar semua buat pengecekan
            df_gudang = df_gudang_raw[df_gudang_raw['STATUS'].astype(str).str.strip().str.upper() == 'TERSEDIA'].copy()
        else:
            df_gudang = pd.DataFrame()

        if df_gudang.empty:
            st.warning("📭 Belum ada data 'Tersedia' di gudang ide.")
            return

        # OPTIMASI 3: Turunkan ke 12 judul unik biar render web kenceng
        df_display = df_gudang.drop_duplicates(subset=['JUDUL']).head(18)
        is_loading = st.session_state.sedang_proses_id is not None
        
        # Loop Grid dari df_display (Gak pake filter-filteran di dalem loop!)
        for i in range(0, len(df_display), 3):
            cols = st.columns(3)
            batch = df_display.iloc[i:i+3]
            
            for j, (_, row) in enumerate(batch.iterrows()):
                with cols[j]:
                    id_ini = str(row['ID_IDE'])
                    judul = row['JUDUL']
                    
                    with st.container(border=True):
                        st.markdown('<div style="height: 3px; background-color: #1d976c; border-radius: 10px; margin-bottom: 10px;"></div>', unsafe_allow_html=True)
                        st.markdown(f"<p style='color: #888; font-size: 13px; margin-bottom: -10px;'>ID: {id_ini}</p>", unsafe_allow_html=True)
                        
                        judul_tampil = (judul[:45] + '..') if len(judul) > 45 else judul
                        st.markdown(f"### {judul_tampil}")
                        
                        st.write("") 
                        if st.button(f"🚀 AMBIL IDE", key=f"btn_{id_ini}", use_container_width=True, disabled=is_loading):
                            st.session_state.sedang_proses_id = id_ini
                            st.session_state.status_sukses = False
                            st.rerun()

        # --- 4. PROSES DATA (SETELAH KLIK) ---
        if st.session_state.sedang_proses_id and not st.session_state.status_sukses:
            target_id = st.session_state.sedang_proses_id
            # Ambil semua adegan (mau 10 atau 100 baris tuntas di sini)
            adegan_rows = df_gudang[df_gudang['ID_IDE'].astype(str) == target_id]
            judul_proses = adegan_rows.iloc[0]['JUDUL']
            
            status_update = f"DIAMBIL ({user_sekarang.upper()})"
            
            # Update Supabase
            supabase.table("Gudang_Ide").update({"STATUS": status_update}).eq("ID_IDE", target_id).execute()
            
            # Update GSheet (Gak pake findall biar gak lemot, cukup cari satu baris tanda)
            try:
                cell = sheet_gudang.find(target_id)
                if cell: sheet_gudang.update_cell(cell.row, 3, status_update)
            except: pass
            
            # Pindahkan ke Produksi
            st.session_state.data_produksi["jumlah_adegan"] = len(adegan_rows)
            naskah_bersih = ""
            for idx, (_, a_row) in enumerate(adegan_rows.iterrows(), 1):
                st.session_state.data_produksi["adegan"][idx] = {
                    "aksi": a_row.get('NASKAH_VISUAL',''), 
                    "dialogs": [str(a_row.get('DIALOG_ACTOR_1','')), str(a_row.get('DIALOG_ACTOR_2','')), "", ""],
                    "style": a_row.get('STYLE', 'CINEMATIC'), 
                    "shot": a_row.get('UKURAN_GAMBAR', 'MEDIUM SHOT'), 
                    "light": a_row.get('LIGHTING', 'NATURAL'), 
                    "arah": a_row.get('ARAH_KAMERA', 'EYE LEVEL'), 
                    "cam": a_row.get('GERAKAN', 'STILL'), 
                    "loc": a_row.get('LOKASI', '')
                }
                naskah_bersih += f"**{idx}.** {a_row.get('NASKAH_VISUAL','')}\n\n"

            st.session_state.naskah_siap_produksi = naskah_bersih
            
            # Tugas & Log
            if user_level != "OWNER":
                t_id = f"T{datetime.now(tz_wib).strftime('%m%d%H%M%S')}"
                tgl_tugas = datetime.now(tz_wib).strftime("%Y-%m-%d")
                supabase.table("Tugas").insert({
                    "ID": t_id, "Staf": user_sekarang.upper(), 
                    "Deadline": tgl_tugas, "Instruksi": f"TUGAS: {judul_proses}", "Status": "PROSES"
                }).execute()
                sheet_tugas.append_row([t_id, user_sekarang.upper(), tgl_tugas, f"TUGAS: {judul_proses}", "PROSES", "-", "", ""])
                tambah_log(user_sekarang, f"AMBIL IDE: {judul_proses}")
                
            st.session_state.status_sukses = True 
            st.rerun()

    except Exception as e:
        st.error(f"⚠️ Gagal: {e}")
        st.session_state.sedang_proses_id = None
        st.rerun()

    if st.session_state.status_sukses:
        time.sleep(2) # Delay centang hijau 2 detik aja cukup
        st.session_state.sedang_proses_id = None
        st.session_state.status_sukses = False
        st.rerun()
        
# ==============================================================================
# NOTIFIKASI & LOGGING
# ==============================================================================
def kirim_notif_wa(pesan):
    token = "f4CApLBAJDTPrVHHZCDF"
    target = "120363407726656878@g.us"
    url = "https://api.fonnte.com/send"
    payload = {'target': target, 'message': pesan, 'countryCode': '62'}
    headers = {'Authorization': token}
    try: requests.post(url, data=payload, headers=headers, timeout=5)
    except: pass

# ==============================================================================
# LOGIKA PERHITUNGAN (SP & BONUS 2026) - VERSI KASTA VIP
# ==============================================================================
def hitung_logika_performa_dan_bonus(df_arsip_user, df_absen_user, bulan_pilih, tahun_pilih, level_target="STAFF"):
    """
    Logika Inti Pintar Media 2026:
    - RESET OTOMATIS: SP tidak diakumulasi ke bulan berikutnya.
    - AMBANG SP: < 2 video (0 atau 1) = Hari Lemah.
    - HARI MINGGU: Bebas SP (Libur).
    - BONUS: Absen (3 video), Video (min 5 video + kelipatan).
    - SYARAT BONUS: Status 'HADIR' & Tidak 'TELAT'.
    - KEBAL SP: OWNER, ADMIN, UPLOADER, & Status IZIN/SAKIT.
    """
    bonus_video_total = 0
    uang_absen_total = 0
    hari_lemah = 0  # <--- KUNCI RESET: Selalu mulai dari 0 setiap fungsi dipanggil
    tz_wib = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_wib)
    
    import calendar
    # 1. Tentukan Batas Hari (SP H+1, Bonus Real-time)
    if bulan_pilih == sekarang.month and tahun_pilih == sekarang.year:
        batas_sp = sekarang.day - 1 
        batas_bonus = sekarang.day  
    else:
        # Jika melihat arsip bulan lalu, hitung penuh satu bulan
        batas_sp = calendar.monthrange(tahun_pilih, bulan_pilih)[1]
        batas_bonus = batas_sp

    # 2. Rekap Berdasarkan 'Deadline' (Patokan Supabase)
    # Hanya video status 'FINISH' yang masuk hitungan.
    df_finish = df_arsip_user[df_arsip_user['STATUS'] == 'FINISH'].copy()
    rekap_harian = {}

    if not df_finish.empty:
        # Menggunakan 'DEADLINE' (Hasil UPPER dari 'Deadline')
        df_finish['TGL_EFEKTIF'] = pd.to_datetime(df_finish['DEADLINE'], errors='coerce').dt.day
        df_finish = df_finish.dropna(subset=['TGL_EFEKTIF'])
        rekap_harian = df_finish.groupby('TGL_EFEKTIF').size().to_dict()

    # 3. Looping Perhitungan Harian
    for tgl in range(1, 32):
        tgl_str = f"{tahun_pilih}-{bulan_pilih:02d}-{tgl:02d}"
        try:
            tgl_objek = datetime(tahun_pilih, bulan_pilih, tgl)
            is_minggu = tgl_objek.weekday() == 6
        except: continue

        jml_v = rekap_harian.get(tgl, 0)
        
        # --- DATA ABSENSI ---
        data_absen = df_absen_user[df_absen_user['TANGGAL'] == tgl_str]
        status_absen = str(data_absen['STATUS'].values[0]).upper() if not data_absen.empty else "ALPHA"
    
        is_telat = "TELAT" in status_absen
        is_hadir = status_absen == "HADIR"
        is_kebal_sp = any(x in status_absen for x in ["IZIN", "SAKIT", "OFF"])
        
        # --- LOGIKA BONUS (HANYA UNTUK STAFF) ---
        # Admin kebal SP tapi gak dapet jatah bonus absen video
        if level_target == "STAFF" and tgl <= batas_bonus:
            if is_hadir and not is_telat:
                if jml_v >= 3: 
                    uang_absen_total += 30000 
                if jml_v >= 5: 
                    bonus_video_total += (jml_v - 4) * 30000
            
        # --- LOGIKA SP (HANYA UNTUK STAFF & H+1) ---
        if level_target == "STAFF" and tgl <= batas_sp:
            if not is_minggu and not is_kebal_sp:
                if jml_v < 2: 
                    hari_lemah += 1

    # 4. Penentuan Level & Potongan
    pot_sp = 0
    if level_target in ["OWNER", "ADMIN", "UPLOADER"]:
        level_sp = "🌟 NORMAL (VIP)"
        hari_lemah = 0
    elif bulan_pilih == sekarang.month and sekarang.day <= 6:
        level_sp = "🛡️ MASA PROTEKSI"
    else:
        if hari_lemah >= 21: pot_sp = 1000000; level_sp = "🚨 SP 3"
        elif hari_lemah >= 14: pot_sp = 700000; level_sp = "⚠️ SP 2"
        elif hari_lemah >= 7: pot_sp = 300000; level_sp = "📢 SP 1"
        else: level_sp = "✅ NORMAL"

    return bonus_video_total, uang_absen_total, pot_sp, level_sp, hari_lemah
    
def tampilkan_tugas_kerja():
    st.title("📋 TUGAS KERJA")
    sh = get_gspread_sh() 
    sheet_tugas = sh.worksheet("Tugas")
    wadah_radar = st.empty()
    
    # --- 1. DATABASE FOTO STAFF ---
    foto_staff_default = "https://cdn-icons-png.flaticon.com/512/149/149071.png"
    foto_staff = {
        "icha": "https://cdn-icons-png.flaticon.com/512/149/149074.png",
        "nissa": "https://cdn-icons-png.flaticon.com/512/149/149067.png",
        "inggi": "https://cdn-icons-png.flaticon.com/512/149/149072.png",
        "lisa": "https://cdn-icons-png.flaticon.com/512/149/149070.png",
        "dian": "https://cdn-icons-png.flaticon.com/512/149/149071.png"
    }
    
    # --- 1. SETUP IDENTITAS ---
    user_sekarang = st.session_state.get("user_aktif", "tamu").lower()
    user_level = st.session_state.get("user_level", "STAFF")
    tz_wib = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_wib)
    
    # --- 2. AMBIL DATA (PAKET KILAT - SEMUA TARIK DI SINI) ---
    try:
        # Optimasi: Tarik semua tabel di awal supaya nggak nembak internet berkali-kali
        df_all_tugas = ambil_data_segar("Tugas")
        df_absen_all = ambil_data_segar("Absensi")
        df_kas_all   = ambil_data_segar("Arus_Kas")
        st_raw       = ambil_data_segar("Staff")
        
        # JIKA KOSONG TOTAL, BARU KASIH WARNING
        if df_all_tugas.empty:
            st.warning("📭 Belum ada data tugas di database.")
            return

        # --- STANDARISASI HEADER SEMUA DATAFRAME (SEKALI JALAN) ---
        for df_item in [df_all_tugas, df_absen_all, df_kas_all, st_raw]:
            if not df_item.empty:
                df_item.columns = [str(c).strip().upper() for c in df_item.columns]

        # --- PROSES KOLOM DEADLINE ---
        df_all_tugas['DEADLINE_DT'] = pd.to_datetime(df_all_tugas['DEADLINE'], errors='coerce')
        df_all_tugas['DEADLINE'] = df_all_tugas['DEADLINE_DT'].dt.strftime('%Y-%m-%d')
        
        # Variabel bantu agar kartu tugas nggak NameError
        data_tugas = df_all_tugas.to_dict('records') 
        status_buang = ["ARSIP", "DONE", "BATAL"]

        # --- 2. SETUP FILTER BULAN ---
        mask_bulan = (df_all_tugas['DEADLINE_DT'].dt.month == sekarang.month) & \
                     (df_all_tugas['DEADLINE_DT'].dt.year == sekarang.year)

        # --- 3. LOGIKA RADAR (Gunakan st_raw yang sudah ditarik di atas) ---
        if user_level == "OWNER":
            # REVISI: Pakai data st_raw yang sudah ada (Gak usah panggil ambil_data_segar lagi)
            list_staf = st_raw[st_raw['LEVEL'] != 'OWNER']['NAMA'].unique().tolist()
            target_user = st.selectbox("🎯 Intip Radar Staf:", list_staf).upper()
        else:
            target_user = user_sekarang.upper()

        # --- INI KUNCINYA: CARI LEVEL SI TARGET DARI DATABASE ---
        try:
            # Cari baris si target_user, ambil kolom LEVEL-nya
            level_asli_target = st_raw[st_raw['NAMA'] == target_user]['LEVEL'].values[0]
        except:
            level_asli_target = "STAFF" # Fallback kalau data gak ketemu

        if user_level in ["STAFF", "ADMIN", "OWNER", "UPLOADER"]:        
            mask_user = df_all_tugas['STAF'].str.strip() == target_user
            mask_finish = df_all_tugas['STATUS'].str.strip() == 'FINISH'
            df_arsip_user = df_all_tugas[mask_user & mask_finish & mask_bulan].copy()
            
            df_u_absen = pd.DataFrame()
            if not df_absen_all.empty:
                df_absen_all.columns = [str(c).strip().upper() for c in df_absen_all.columns]
                df_u_absen = df_absen_all[df_absen_all['NAMA'] == target_user].copy()

            # --- 1. AMBIL DATA REAL DARI ARUS KAS SUPABASE ---
            df_kas_all.columns = [str(c).strip().upper() for c in df_kas_all.columns]
            
            # Cari baris yang kategorinya ' Tim', ada nama staf, DAN di periode bulan/tahun yang dipilih
            mask_bonus_real = (df_kas_all['KATEGORI'].str.upper() == ' TIM') & \
                              (df_kas_all['KETERANGAN'].str.upper().str.contains(target_user, na=False)) & \
                              (pd.to_datetime(df_kas_all['TANGGAL']).dt.month == sekarang.month) & \
                              (pd.to_datetime(df_kas_all['TANGGAL']).dt.year == sekarang.year)
            
            bonus_sudah_cair = pd.to_numeric(df_kas_all[mask_bonus_real]['NOMINAL'], errors='coerce').sum()

            # --- 2. HITUNG LOGIKA (Cuma buat nyari Status SP & Hari Kurang) ---
            # Kita abaikan hasil b_vid dan u_abs dari sini karena kita pake data real database
            _, _, pot_sp_r, level_sp_r, h_kurang = hitung_logika_performa_dan_bonus(
                df_arsip_user, 
                df_u_absen, 
                sekarang.month, 
                sekarang.year,
                level_target=level_asli_target 
            )
            
            # --- 3. SET VARIABLE UNTUK UI ---
            total_semua_bonus = bonus_sudah_cair # <--- INI KUNCI SINKRONISASINYA
            # --- SISIRAN FINAL: PENENTU PESAN & RADAR UI (KASTA VERSION) ---
            if level_asli_target in ["OWNER", "ADMIN", "UPLOADER"]:
                status_ikon = "✨ VIP"
                msg = "Akses Khusus: Tidak dipengaruhi sistem."
                tampil_h_kurang = 0 # VIP selalu terlihat bersih di radar
            else:
                tampil_h_kurang = h_kurang
                if h_kurang >= 21:
                    status_ikon, msg = "🚨 TERMINATED", f"Status: {level_sp_r}. Hubungi Admin!"
                elif h_kurang >= 7:
                    status_ikon, msg = "⚠️ WARNING", f"Dah kena {level_sp_r}. Ayo kejar target!"
                elif h_kurang >= 4:
                    status_ikon, msg = "⚡ PANTAU", f"Udah {h_kurang} hari bolong target."
                else:
                    status_ikon, msg = "✨ AMAN", "Performa mantap! Pertahankan."

            # --- RENDER RADAR UI (5 KOLOM) ---
            with wadah_radar.container(border=True):
                # Kita bagi menjadi 5 kolom agar muat semua metrik
                c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1.2, 1.5])
                
                with c1:
                    st.metric("📊 STATUS", status_ikon)
                
                with c2:
                    st.metric(
                        "💀 HARI LEMAH", 
                        f"{tampil_h_kurang} / 21", 
                        delta=f"{tampil_h_kurang} hari" if tampil_h_kurang > 0 else None,
                        delta_color="inverse"
                    )

                with c3:
                    # MENGHITUNG TOTAL VIDEO STATUS FINISH BULAN INI
                    total_vid_finish = len(df_arsip_user) # Data ini sudah difilter mask_bulan & FINISH
                    st.metric(
                        "🎬 TOTAL VIDEO",
                        f"{total_vid_finish}",
                        delta="Bulan Ini",
                        delta_color="normal"
                    )
                
                with c4:
                    # PECAH DATA DARI ARUS KAS (Sesuai ralat 30rb)
                    mask_vid = mask_bonus_real & df_kas_all['KETERANGAN'].str.upper().str.contains('VIDEO', na=False)
                    mask_abs = mask_bonus_real & df_kas_all['KETERANGAN'].str.upper().str.contains('ABSEN', na=False)
                    
                    cair_vid = pd.to_numeric(df_kas_all[mask_vid]['NOMINAL'], errors='coerce').sum()
                    cair_abs = pd.to_numeric(df_kas_all[mask_abs]['NOMINAL'], errors='coerce').sum()
                    total_semua = cair_vid + cair_abs

                    st.metric(
                        "💰 TOTAL BONUS", 
                        f"Rp {int(total_semua):,}",
                        delta=f"Video: {int(cair_vid/1000)}k | Absen: {int(cair_abs/1000)}k",
                        delta_color="normal"
                    )
                
                with c5:
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    st.write(f"📢 **INFO {target_user}:** \n\n {msg}")

        st.divider()

    except Exception as e:
        st.error(f"❌ Error Tampilan: {e}")

    # --- 3. PANEL ADMIN (MURNI SUPABASE) ---
    if user_level == "OWNER":
        st_raw.columns = [str(c).strip().upper() for c in st_raw.columns]
        staf_options = st_raw['NAMA'].unique().tolist()
        
        with st.expander("✨ **KIRIM TUGAS BARU**", expanded=False):
            c2, c1 = st.columns([2, 1]) 
            with c2: 
                isi_tugas = st.text_area("Instruksi Tugas", height=150, placeholder="Tulis instruksi video di sini...", key="input_tugas_admin")
            with c1: 
                staf_tujuan = st.selectbox("Pilih Editor", staf_options)
                pake_wa = st.checkbox("Kirim Notif WA?", value=True)
            
            if st.button("🚀 KIRIM KE EDITOR", use_container_width=True):
                if isi_tugas:
                    t_id = f"ID{datetime.now(tz_wib).strftime('%m%d%H%M%S')}"
                    tgl_skrg = sekarang.strftime("%Y-%m-%d")
                    
                    data_tugas_supabase = {
                        "ID": t_id,
                        "Staf": staf_tujuan,
                        "Deadline": tgl_skrg,
                        "Instruksi": isi_tugas,
                        "Status": "PROSES"
                    }
                    
                    try:
                        # HANYA KE SUPABASE
                        supabase.table("Tugas").insert(data_tugas_supabase).execute()
                        
                        tambah_log(st.session_state.user_aktif, f"Kirim Tugas Baru {t_id}")
                        
                        if pake_wa:
                            kirim_notif_wa(f"✨ *INFO TUGAS*\n\n👤 *Untuk:* {staf_tujuan.upper()}\n🆔 *ID:* {t_id}\n📝 *Detail:* {isi_tugas[:30]}...")
                        
                        st.success("✅ Tugas Berhasil Dikirim ke Supabase!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal kirim ke Supabase: {e}")

    # --- 4. SETOR MANDIRI (VERSI TOTAL SUPABASE) ---
    if user_level in ["STAFF", "UPLOADER", "ADMIN"]:
        with st.expander("🚀 SETOR TUGAS MANDIRI", expanded=False):
            st.info("💡 **SOP:** Setor 1 video per 1 kiriman agar bonus & target terhitung otomatis.")
            
            with st.form("form_mandiri_supa", clear_on_submit=True):
                judul_m = st.text_input("📝 Judul Video/Pekerjaan:")
                link_m = st.text_input("🔗 Link GDrive:")
                
                submit_m = st.form_submit_button("🔥 KIRIM SETORAN", use_container_width=True)
                
                if submit_m:
                    if judul_m and link_m:
                        # --- VALIDASI LINK GANDA (PENTING!) ---
                        is_multiple = "," in link_m or link_m.lower().count("https://") > 1
                        
                        if is_multiple:
                            st.error("❌ **STOP!** Dilarang setor link ganda dalam satu form.")
                        elif "drive.google.com" not in link_m.lower():
                            st.warning("⚠️ **LINK SALAH!** Wajib link Google Drive.")
                        else:
                            t_id_m = f"M{datetime.now(tz_wib).strftime('%m%d%H%M%S')}"
                            tgl_hari_ini = sekarang.strftime("%Y-%m-%d")
                            waktu_setor = sekarang.strftime("%d/%m/%Y %H:%M")
                            
                            # --- 1. SINKRON KE SUPABASE (SINGLE SOURCE OF TRUTH) ---
                            data_mandiri_sb = {
                                "ID": t_id_m,
                                "Staf": user_sekarang.upper(),
                                "Deadline": tgl_hari_ini,
                                "Instruksi": judul_m,
                                "Status": "WAITING QC",
                                "Waktu_Kirim": waktu_setor,
                                "Link_Hasil": link_m
                            }
                            
                            try:
                                supabase.table("Tugas").insert(data_mandiri_sb).execute()
                                
                                # --- 2. LOG & NOTIF (TANPA GSHEET) ---
                                tambah_log(user_sekarang, f"SETOR MANDIRI: {judul_m} ({t_id_m})")
                                
                                if "kirim_notif_wa" in globals():
                                    kirim_notif_wa(f"📤 *SETORAN MANDIRI*\n👤 *Editor:* {user_sekarang.upper()}\n🆔 *ID:* {t_id_m}\n📝 *Tugas:* {judul_m}")
                                
                                st.success("✅ Setoran Berhasil Masuk Database!")
                                time.sleep(1)
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Database Error: {e}")
                    else:
                        st.warning("⚠️ Isi dulu Judul dan Link-nya!")
                        
    # --- 5. RENDER KARTU TUGAS (FIXED LOGIC) ---
    tugas_terfilter = []
    
    # 1. Kumpulkan data dulu
    if not df_all_tugas.empty:
        status_buang = ["FINISH", "CANCELED"]
        
        # OWNER dan ADMIN bisa pantau semua tugas yang lagi jalan
        if user_level in ["OWNER", "ADMIN"]: 
            tugas_terfilter = [t for t in data_tugas if str(t.get("STATUS")).upper() not in status_buang]
        else:
            tugas_terfilter = [t for t in data_tugas if str(t.get("STAF")).lower() == user_sekarang and str(t.get("STATUS")).upper() not in status_buang]

    # 2. CEK HASIL FILTER (Logika yang bener: kalau kosong kasih info, kalau ada gambar kartu)
    if not tugas_terfilter:
        pass

    else:
        # --- MODE 2 KOLOM (GRID) ---
        tugas_list = list(reversed(tugas_terfilter))
        for i in range(0, len(tugas_list), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(tugas_list):
                    t = tugas_list[i + j]
                    
                    # --- [PENTING] DEFINISI VARIABEL DI SINI (AGAR SEMUA TOMBOL BISA BACA) ---
                    status = str(t["STATUS"]).upper()
                    id_tugas = str(t.get('ID', '')).strip()
                    staf_nama = str(t.get('STAF', '')).upper().strip()
                    tgl_tugas = str(t.get('DEADLINE', ''))
                    url_foto = foto_staff.get(staf_nama.lower(), foto_staff_default)
                    
                    with cols[j]:
                        with st.container(border=True):
                            # HEADER SLIM
                            c1, c2 = st.columns([0.8, 3])
                            with c1: 
                                st.image(url_foto, width=50)
                            with c2:
                                st.markdown(f"**{staf_nama}** | `ID: {id_tugas}`")
                                color_ball = "🔴" if status == "REVISI" else "🟡" if status == "WAITING QC" else "🟢"
                                st.markdown(f"{color_ball} `{status}`")
                            
                            olah = st.toggle("🔍 Buka Detail", key=f"tgl_{id_tugas}")
                            
                            if olah:
                                st.divider()
                                if t.get("CATATAN_REVISI"): 
                                    st.warning(f"⚠️ **REVISI:** {t['CATATAN_REVISI']}")
                                st.markdown(f"> **INSTRUKSI:** \n> {t.get('INSTRUKSI', '-')}")
                                
                                # 1. LINK QC
                                if t.get("LINK_HASIL") and t["LINK_HASIL"] != "-":
                                    link_qc = str(t["LINK_HASIL"]).strip()
                                    st.link_button("🚀 BUKA VIDEO (QC)", link_qc, use_container_width=True)

                                # 2. PANEL VETO (KHUSUS OWNER)
                                if user_level == "OWNER":
                                    st.write("---")
                                    cat_r = st.text_area("Catatan Admin:", key=f"cat_{id_tugas}", placeholder="Alasan Revisi/Batal...")
                                    
                                    b1, b2, b3 = st.columns(3)
                                    
                                    with b1: # --- TOMBOL ACC (TOTAL SUPABASE) ---
                                        if st.button("🟢 ACC", key=f"f_{id_tugas}", use_container_width=True):
                                            # PROTEKSI: Cegah klik ganda (Kunci Session)
                                            if f"lock_{id_tugas}" in st.session_state:
                                                st.warning("Sedang diproses...")
                                            else:
                                                st.session_state[f"lock_{id_tugas}"] = True 
                                                try:
                                                    # 1. UPDATE STATUS TUGAS (SUPABASE ONLY)
                                                    supabase.table("Tugas").update({"Status": "FINISH"}).eq("ID", id_tugas).execute()
                                                    
                                                    # 2. HITUNG BONUS (MENGGUNAKAN DATA MEMORI AGAR KILAT)
                                                    df_selesai = df_all_tugas[
                                                        (df_all_tugas['STAF'].str.upper() == staf_nama) &
                                                        (df_all_tugas['DEADLINE'] == tgl_tugas) &
                                                        (df_all_tugas['STATUS'].str.upper() == 'FINISH')
                                                    ]
                                                    # +1 karena yang barusan di-ACC belum masuk df_all_tugas (cache)
                                                    jml_video = len(df_selesai) + 1 

                                                    # 3. LOGIKA BONUS & AUTO-INPUT ARUS KAS
                                                    msg_bonus = ""
                                                    if jml_video == 3 or jml_video >= 5:
                                                        nom_bonus = 30000
                                                        ket_bonus = f"Bonus {'Absen' if jml_video == 3 else 'Video'}: {staf_nama} ({id_tugas})"
                                                        
                                                        # INPUT KE ARUS KAS (SUPABASE ONLY)
                                                        supabase.table("Arus_Kas").insert({
                                                            "Tanggal": tgl_tugas, 
                                                            "Tipe": "PENGELUARAN", 
                                                            "Kategori": "Tim", # Sesuaikan kategori Supabase lo (foto tadi tulisannya "Tim")
                                                            "Nominal": str(nom_bonus), 
                                                            "Keterangan": ket_bonus, 
                                                            "Pencatat": "SISTEM (AUTO-ACC)"
                                                        }).execute()
                                                        
                                                        msg_bonus = f"\n💰 *BONUS:* Rp 30,000"
                                                        st.toast(f"Bonus {staf_nama} otomatis cair!", icon="💸")

                                                    # 4. LOG & NOTIFIKASI
                                                    tambah_log(st.session_state.user_aktif, f"ACC TUGAS: {id_tugas}")
                                                    
                                                    if "kirim_notif_wa" in globals():
                                                        kirim_notif_wa(f"✅ *TUGAS ACC*\n👤 *Editor:* {staf_nama}\n🆔 *ID:* {id_tugas}{msg_bonus}")
                                                    
                                                    st.success("Tugas Selesai & Data Tersinkron!"); time.sleep(1); st.rerun()
                                                    
                                                except Exception as e:
                                                    # Lepas kunci jika gagal agar bisa diulang
                                                    if f"lock_{id_tugas}" in st.session_state:
                                                        del st.session_state[f"lock_{id_tugas}"]
                                                    st.error(f"❌ Gagal ACC ke Supabase: {e}")

                                    with b2: # --- TOMBOL REVISI (PURE SUPABASE) ---
                                        if st.button("🔴 REV", key=f"r_{id_tugas}", use_container_width=True):
                                            if cat_r:
                                                # UPDATE SUPABASE ONLY
                                                supabase.table("Tugas").update({
                                                    "Status": "REVISI", 
                                                    "Catatan_Revisi": cat_r
                                                }).eq("ID", id_tugas).execute()
                                                
                                                kirim_notif_wa(f"⚠️ *REVISI*\n👤 *Editor:* {staf_nama}\n🆔 *ID:* {id_tugas}\n📝: {cat_r}")
                                                tambah_log(st.session_state.user_aktif, f"REVISI TUGAS: {id_tugas}")
                                                
                                                st.warning("STATUS: REVISI!"); time.sleep(1); st.rerun()
                                            else:
                                                st.error("Isi alasan revisi di kolom catatan!")

                                    with b3: # --- TOMBOL BATAL (PURE SUPABASE) ---
                                        if st.button("🚫 BATAL", key=f"c_{id_tugas}", use_container_width=True):
                                            if cat_r:
                                                # UPDATE SUPABASE ONLY
                                                supabase.table("Tugas").update({
                                                    "Status": "CANCELED", 
                                                    "Catatan_Revisi": f"BATAL: {cat_r}"
                                                }).eq("ID", id_tugas).execute()
                                                
                                                kirim_notif_wa(f"🚫 *BATAL*\n👤 *Editor:* {staf_nama}\n🆔 *ID:* {id_tugas}\n📝: {cat_r}")
                                                tambah_log(st.session_state.user_aktif, f"BATALKAN TUGAS: {id_tugas}")
                                                
                                                st.error("STATUS: CANCELED!"); time.sleep(1); st.rerun()
                                            else:
                                                st.error("Isi alasan batal di kolom catatan!")

                                # --- PANEL STAFF: SETOR TUGAS (PURE SUPABASE) ---
                                elif user_level in ["STAFF", "UPLOADER", "ADMIN"]: 
                                    st.markdown("---")
                                    l_in = st.text_input("Paste Link GDrive:", value=t.get("LINK_HASIL", ""), key=f"l_{id_tugas}")
                                    
                                    if st.button("🚀 SETOR", key=f"b_{id_tugas}", use_container_width=True):
                                        if l_in.strip() and "drive.google.com" in l_in.lower():
                                            # UPDATE SUPABASE ONLY
                                            supabase.table("Tugas").update({
                                                "Status": "WAITING QC", 
                                                "Link_Hasil": l_in, 
                                                "Waktu_Kirim": sekarang.strftime("%d/%m/%Y %H:%M")
                                            }).eq("ID", id_tugas).execute()
                                            
                                            kirim_notif_wa(f"📤 *SETORAN*\n👤 *Editor:* {staf_nama}\n🆔 *ID:* {id_tugas}")
                                            tambah_log(user_sekarang, f"SETOR TUGAS: {id_tugas}")
                                            
                                            st.success("Tugas Berhasil Disetorkan!"); time.sleep(1); st.rerun()
                                        else:
                                            st.error("Wajib Link Google Drive yang Valid!")

    # =========================================================
    # --- 4.5. SISTEM KLAIM AI (MURNI SUPABASE - ANTI LAG) ---
    # =========================================================
    if user_level in ["STAFF", "ADMIN", "UPLOADER"]:
        st.write("")
        
        with st.expander("⚡ KLAIM AKUN AI DISINI", expanded=False):
            try:
                # 1. SETUP WAKTU & AMBIL DATA (DARI SUPABASE)
                tz_jakarta = pytz.timezone('Asia/Jakarta')
                h_ini = datetime.now(tz_jakarta).date()
                h_ini_str = h_ini.strftime("%Y-%m-%d")

                # Tarik data stok akun AI dari Supabase
                # Asumsi Nama Tabel: Akun_AI (Sesuaikan dengan DB lo)
                res_ai = supabase.table("Akun_AI").select("*").execute()
                df_ai = pd.DataFrame(res_ai.data)
                
                if df_ai.empty:
                    st.warning("📭 Database Akun AI masih kosong.")
                else:
                    df_ai = bersihkan_data(df_ai) # Pake pembersih lo
                    user_up = user_sekarang.upper().strip()
                    
                    # 2. FILTER AKUN AKTIF MILIK USER
                    # Akun yang sedang dipegang user dan belum expired
                    df_user_aktif = df_ai[
                        (df_ai['PEMAKAI'] == user_up) & 
                        (pd.to_datetime(df_ai['EXPIRED']).dt.date >= h_ini)
                    ].copy()
                    
                    akun_aktif_user = df_user_aktif.to_dict('records')

                    # 3. LOGIKA STOK (Tampilkan yang PEMAKAI='X' dan BELUM EXPIRED)
                    df_stok = df_ai[
                        (df_ai['PEMAKAI'] == 'X') & 
                        (pd.to_datetime(df_ai['EXPIRED']).dt.date > h_ini)
                    ].copy()
                    
                    list_opsi = sorted(df_stok['AI'].unique().tolist()) if not df_stok.empty else []
                    
                    c_sel, c_btn = st.columns([2, 1])
                    pilihan_ai = c_sel.selectbox("Pilih Tool", list_opsi if list_opsi else ["STOK KOSONG"], label_visibility="collapsed", key="v5_select")
                    
                    # Validasi Tombol
                    bisa_klaim = True 
                    if not list_opsi:
                        bisa_klaim = False
                        st.warning("😭 Stok akun sedang habis atau expired.")
                    elif len(akun_aktif_user) >= 4:
                        bisa_klaim = False
                        st.warning("🚫 Limit 4 akun aktif tercapai. Tunggu akun lama expired.")

                    # --- PROSES EKSEKUSI (SUPABASE VERSION) ---
                    if c_btn.button("🔓 KLAIM AKUN", use_container_width=True, disabled=not bisa_klaim):
                        # 1. CEK LOCK (Anti Double-Click)
                        if f"lock_ai_{user_up}" in st.session_state:
                            st.warning("Sabar Bos, lagi diproses...")
                        else:
                            st.session_state[f"lock_ai_{user_up}"] = True
                            
                            try:
                                # 2. AMBIL STOK PERTAMA DARI PILIHAN
                                target_df = df_stok[df_stok['AI'] == pilihan_ai]
                                
                                if not target_df.empty:
                                    target = target_df.iloc[0] 
                                    email_target = str(target['EMAIL']).strip()
                                    
                                    # 3. UPDATE KE SUPABASE (INSTANT)
                                    # Mengubah PEMAKAI dari 'X' menjadi Nama User & Update TANGGAL_KLAIM
                                    supabase.table("Akun_AI").update({
                                        "PEMAKAI": user_up,
                                        "TGL_KLAIM": h_ini_str
                                    }).eq("EMAIL", email_target).execute()
                                    
                                    # 4. KIRIM NOTIF & LOG
                                    if "kirim_notif_wa" in globals():
                                        kirim_notif_wa(f"🔑 *KLAIM AKUN AI*\n\n👤 *User:* {user_up}\n🛠️ *Tool:* {pilihan_ai}\n📧 *Email:* {email_target}")
                                    
                                    tambah_log(user_sekarang, f"KLAIM AKUN AI: {pilihan_ai} ({email_target})")
                                    
                                    st.success(f"Berhasil! Akun {pilihan_ai} sekarang milikmu.")
                                    
                                    # 5. BERSIHKAN & REFRESH
                                    del st.session_state[f"lock_ai_{user_up}"]
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Yah, barusan diambil orang lain. Coba lagi!")
                                    del st.session_state[f"lock_ai_{user_up}"]
                                    
            except Exception as e:
                # Ini penutup untuk tombol KLAIM saja
                if f"lock_ai_{user_up}" in st.session_state:
                    del st.session_state[f"lock_ai_{user_up}"]
                st.error(f"Gagal eksekusi klaim: {e}")
            
            # --- 4. DAFTAR KOLEKSI (DI LUAR EXCEPT) ---
            # Taruh di sini supaya mau sukses atau gagal klaim, list akun tetep muncul
            if not df_ai.empty: # Pastikan df_ai sudah terdefinisi dari load awal
                # Filter ulang akun milik user (biar dapet data paling segar)
                user_up = user_sekarang.upper().strip()
                df_ai['EXPIRED_DT'] = pd.to_datetime(df_ai['EXPIRED'], errors='coerce').dt.date
                
                df_user_aktif = df_ai[
                    (df_ai['PEMAKAI'].astype(str).str.upper() == user_up) & 
                    (df_ai['EXPIRED_DT'] >= h_ini)
                ].copy()
                
                akun_aktif_user = df_user_aktif.to_dict('records')

                if akun_aktif_user:
                    st.divider()
                    st.markdown("### 🔑 Akun Aktif Milikmu")
                    kolom_vcard = st.columns(3) 
                    
                    for idx, r in enumerate(reversed(akun_aktif_user)):
                        sisa = (r['EXPIRED_DT'] - h_ini).days
                        warna_h = "#1d976c" if sisa > 7 else "#f39c12" if sisa >= 0 else "#e74c3c"
                        stat_ai = "🟢 AMAN" if sisa > 7 else "🟠 LIMIT" if sisa >= 0 else "🔴 MATI"

                        with kolom_vcard[idx % 3]:
                            with st.container(border=True):
                                # Bagian HTML lo udah cakep banget, pertahanin!
                                st.markdown(f"""
                                    <div style="text-align:center; padding:3px; background:{warna_h}; border-radius:8px 8px 0 0; margin:-15px -15px 10px -15px;">
                                        <b style="color:white; font-size:11px;">{str(r['AI']).upper()}</b>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                e1, e2 = st.columns(2)
                                e1.markdown(f"<p style='margin:10px 0 0 0; font-size:10px; color:#888;'>📧 EMAIL</p><code style='font-size:11px; display:block; overflow:hidden;'>{r['EMAIL']}</code>", unsafe_allow_html=True)
                                e2.markdown(f"<p style='margin:10px 0 0 0; font-size:10px; color:#888;'>🔑 PASS</p><code style='font-size:11px; display:block;'>{r['PASSWORD']}</code>", unsafe_allow_html=True)
                                
                                st.write("")
                                s1, s2, s3 = st.columns(3)
                                s1.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>STATUS</p><b style='font-size:10px;'>{stat_ai}</b>", unsafe_allow_html=True)
                                s2.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>EXP</p><b style='font-size:10px;'>{r['EXPIRED_DT'].strftime('%d %b')}</b>", unsafe_allow_html=True)
                                s3.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>SISA</p><b style='font-size:11px; color:{warna_h};'>{sisa} Hr</b>", unsafe_allow_html=True)

                st.caption("🆘 **Darurat?** Jika akun suspend, hubungi Admin (Dian).")

        except Exception as e_station:
            # Ini proteksi kalau seluruh sistem AI Station (loading data) gagal
            st.error(f"Gagal memuat AI Station: {e_station}")
                
    # --- 4. LACI ARSIP (VERSI FIX NOTIF) ---
    with st.expander("📜 RIWAYAT & ARSIP TUGAS", expanded=False):
        c_arsip1, c_arsip2 = st.columns([2, 1])
        daftar_bulan = {1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"}
        
        bln_arsip_nama = c_arsip1.selectbox("📅 Pilih Bulan Riwayat:", list(daftar_bulan.values()), index=sekarang.month - 1, key="sel_bln_arsip")
        bln_arsip_angka = [k for k, v in daftar_bulan.items() if v == bln_arsip_nama][0]
        thn_arsip = c_arsip2.number_input("📅 Tahun:", value=sekarang.year, min_value=2024, max_value=2030, key="sel_thn_arsip")

        # Panggil data segar
        df_laci = ambil_data_segar("Tugas", bulan_pilihan=bln_arsip_angka, tahun_pilihan=thn_arsip)
        
        # Inisialisasi variabel pengecekan
        tampilkan_data = False

        if not df_laci.empty:
            # 1. Saring berdasarkan Status
            df_laci = df_laci[df_laci['STATUS'].isin(['FINISH', 'CANCELED'])]
            
            # (ADMIN dan OWNER lolos, bisa liat semua)
            user_lvl_skrg = st.session_state.get("user_level", "STAFF").upper()
            
            if user_lvl_skrg in ["STAFF", "UPLOADER"]:
                user_skrg = st.session_state.get("user_aktif", "").upper()
                if 'STAF' in df_laci.columns:
                    df_laci = df_laci[df_laci['STAF'].str.upper() == user_skrg]
            
            # 3. Cek apakah setelah disaring masih ada data?
            if not df_laci.empty:
                tampilkan_data = True

        # --- LOGIKA TAMPILAN ---
        if tampilkan_data:
            # Statistik
            total_f = len(df_laci[df_laci['STATUS'] == "FINISH"])
            total_c = len(df_laci[df_laci['STATUS'] == "CANCELED"])
            st.markdown(f"📊 **Laporan {bln_arsip_nama}:** <span style='color:#1d976c;'>✅ {total_f} Selesai</span> | <span style='color:#e74c3c;'>🚫 {total_c} Dibatalkan</span>", unsafe_allow_html=True)
            
            kolom_fix = ['ID', 'STAF', 'INSTRUKSI', 'DEADLINE', 'STATUS', 'CATATAN_REVISI']
            
            st.dataframe(
                df_laci.sort_values(by='ID', ascending=False)[kolom_fix],
                column_config={
                    "ID": st.column_config.TextColumn("🆔 ID"),
                    "STAF": st.column_config.TextColumn("👤 STAF"),
                    "INSTRUKSI": st.column_config.TextColumn("📝 JUDUL KONTEN"),
                    "DEADLINE": st.column_config.TextColumn("📅 TGL"),
                    "STATUS": st.column_config.TextColumn("🚩 STATUS"),
                    "CATATAN_REVISI": st.column_config.TextColumn("📋 KETERANGAN")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            # Jika benar-benar kosong atau tidak ada yang FINISH/CANCELED
            st.info(f"📭 Tidak ada riwayat tugas pada {bln_arsip_nama} {thn_arsip}.")
                
def tampilkan_kendali_tim():    
    user_sekarang = st.session_state.get("user_aktif", "tamu").lower()
    user_level = st.session_state.get("user_level", "STAFF").upper()

    if user_level not in ["OWNER", "ADMIN"]:
        st.error("🚫 Maaf, Area ini hanya untuk jajaran Manajemen.")
        st.stop()

    # 2. SETUP WAKTU
    tz_wib = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_wib)
    
    # 3. HEADER HALAMAN
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("⚡ PUSAT KENDALI TIM")
    with col_h2:
        if st.button("🔄 REFRESH DATA", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    c_bln, c_thn = st.columns([2, 2])
    daftar_bulan = {1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"}
    pilihan_nama = c_bln.selectbox("📅 Pilih Bulan Laporan:", list(daftar_bulan.values()), index=sekarang.month - 1)
    bulan_dipilih = [k for k, v in daftar_bulan.items() if v == pilihan_nama][0]
    tahun_dipilih = c_thn.number_input("📅 Tahun:", value=sekarang.year, min_value=2024, max_value=2030)

    st.divider()

    try:
        # --- 1. AMBIL DATA SUPER CEPAT (SUPABASE) ---
        df_staff = ambil_data_segar("Staff")
        df_absen = ambil_data_segar("Absensi")
        df_kas   = ambil_data_segar("Arus_Kas")
        df_tugas = ambil_data_segar("Tugas")
        df_log   = ambil_data_segar("Log_Aktivitas")

        # --- 2. FUNGSI SARING TANGGAL (OPTIMASI SUPABASE) ---
        def saring_tgl(df, kolom, bln, thn):
            if df.empty or kolom not in df.columns: return pd.DataFrame()
            # Gunakan dayfirst=True biar gak ketukar format luar negeri
            df['TGL_TEMP'] = pd.to_datetime(df[kolom], errors='coerce', dayfirst=True)
            mask = (df['TGL_TEMP'].dt.month == bln) & (df['TGL_TEMP'].dt.year == thn)
            return df[mask].copy()

        # Jalankan filter
        df_t_bln = saring_tgl(df_tugas, 'DEADLINE', bulan_dipilih, tahun_dipilih)
        df_a_f   = saring_tgl(df_absen, 'TANGGAL', bulan_dipilih, tahun_dipilih)
        df_k_f   = saring_tgl(df_kas, 'TANGGAL', bulan_dipilih, tahun_dipilih)
        df_log_f = saring_tgl(df_log, 'WAKTU', bulan_dipilih, tahun_dipilih)

        # --- 3. LOGIKA REKAP TIM ---
        df_f_f = pd.DataFrame(columns=['STAF', 'STATUS', 'TGL_TEMP']) # Default
        if not df_t_bln.empty and 'STATUS' in df_t_bln.columns:
            df_f_f = df_t_bln[df_t_bln['STATUS'].astype(str).str.upper() == "FINISH"].copy()

        rekap_harian_tim = {}
        rekap_total_video = {}

        if not df_f_f.empty and 'STAF' in df_f_f.columns:
            df_f_f['STAF'] = df_f_f['STAF'].astype(str).str.strip().str.upper()
            df_f_f['TGL_STR'] = df_f_f['TGL_TEMP'].dt.strftime('%Y-%m-%d')
            rekap_harian_tim = df_f_f.groupby(['STAF', 'TGL_STR']).size().unstack(fill_value=0).to_dict('index')
            rekap_total_video = df_f_f['STAF'].value_counts().to_dict()

        # --- 4. KALKULASI KEUANGAN (FIX KATEGORI 'TIM') ---
        inc, ops, bonus_terbayar_kas = 0, 0, 0
        
        if not df_k_f.empty:
            df_k_f['NOMINAL'] = pd.to_numeric(df_k_f['NOMINAL'].astype(str).replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
            inc = df_k_f[df_k_f['TIPE'] == 'PENDAPATAN']['NOMINAL'].sum()
            
            # PENTING: Ganti 'Gaji Tim' jadi 'TIM' sesuai database Supabase lo
            ops = df_k_f[(df_k_f['TIPE'] == 'PENGELUARAN') & (~df_k_f['KATEGORI'].str.upper().isin(['TIM', 'GAJI TIM']))]['NOMINAL'].sum()
            bonus_terbayar_kas = df_k_f[(df_k_f['TIPE'] == 'PENGELUARAN') & (df_k_f['KATEGORI'].str.upper().isin(['TIM', 'GAJI TIM']))]['NOMINAL'].sum()

        # --- 5. ESTIMASI GAJI POKOK (NO OWNER) ---
        total_gaji_pokok_tim = 0
        is_masa_depan = tahun_dipilih > sekarang.year or (tahun_dipilih == sekarang.year and bulan_dipilih > sekarang.month)
        df_staff_real = df_staff[df_staff['LEVEL'].isin(['STAFF', 'UPLOADER', 'ADMIN'])]

        if not is_masa_depan:
            for _, s in df_staff_real.iterrows():
                n_up = str(s.get('NAMA', '')).strip().upper()
                if n_up == "" or n_up == "NAN": continue
                
                lv_asli = str(s.get('LEVEL', 'STAFF')).strip().upper()
                df_a_staf = df_a_f[df_a_f['NAMA'].str.upper() == n_up].copy()
                df_t_staf = df_f_f[df_f_f['STAF'] == n_up].copy()

                # Panggil mesin hitung performa
                _, _, pot_sp_real, _, _ = hitung_logika_performa_dan_bonus(
                    df_t_staf, df_a_staf, bulan_dipilih, tahun_dipilih,
                    level_target=lv_asli 
                )
                
                g_pokok = int(pd.to_numeric(str(s.get('GAJI_POKOK')).replace('.',''), errors='coerce') or 0)
                t_tunj = int(pd.to_numeric(str(s.get('TUNJANGAN')).replace('.',''), errors='coerce') or 0)
                
                gaji_nett = max(0, (g_pokok + t_tunj) - pot_sp_real)
                total_gaji_pokok_tim += gaji_nett

        # TOTAL OUTCOME SINKRON (Uang Keluar Real: Staff + Admin)
        total_pengeluaran_gaji = total_gaji_pokok_tim + bonus_terbayar_kas
        total_out = total_pengeluaran_gaji + ops
        saldo_bersih = inc - total_out
        
        # ======================================================================
        # --- UI: FINANCIAL COMMAND CENTER (FULL SUPABASE EDITION) ---
        # ======================================================================
        with st.expander("💰 ANALISIS KEUANGAN & KAS", expanded=False):
            
            # --- FIX TIPE DATA FINANSIAL SEBELUM TAMPIL ---
            inc_val = float(inc)
            bonus_val = float(bonus_terbayar_kas) if bonus_terbayar_kas else 0
            ops_val = float(ops) if ops else 0
            
            # Outcome total gabungan (Riil)
            total_out_riil = total_gaji_pokok_tim + bonus_val + ops_val
            saldo_riil = inc_val - total_out_riil
            
            # --- METRIK UTAMA ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 INCOME", f"Rp {inc_val:,.0f}")
            m2.metric("💸 OUTCOME", f"Rp {total_out_riil:,.0f}", 
                      delta=f"-Rp {total_out_riil:,.0f}" if total_out_riil > 0 else None, 
                      delta_color="normal")
            
            status_saldo = "SURPLUS" if saldo_riil >= 0 else "DEFISIT"
            warna_delta = "normal" if saldo_riil >= 0 else "inverse"
            
            m3.metric("📈 SALDO BERSIH", f"Rp {saldo_riil:,.0f}", 
                      delta=status_saldo,
                      delta_color=warna_delta)
            
            margin_val = (saldo_riil / inc_val * 100) if inc_val > 0 else 0
            m4.metric("📊 MARGIN", f"{margin_val:.1f}%")

            st.divider()
            
            col_input, col_logs, col_viz = st.columns([1, 1.2, 1], gap="small")

            with col_input:
                with st.form("form_kas_new", clear_on_submit=True):
                    f_tipe = st.pills("Tipe", ["PENDAPATAN", "PENGELUARAN"], default="PENGELUARAN", label_visibility="collapsed")
                    # FIX: Ganti "Gaji Tim" jadi "Tim" biar sinkron sama database Supabase lo
                    f_kat = st.selectbox("Kategori", ["YouTube", "Brand Deal", "Tim", "Operasional", "Lainnya"], label_visibility="collapsed")
                    f_nom = st.number_input("Nominal", min_value=0, step=50000, label_visibility="collapsed", placeholder="Nominal Rp...")
                    f_ket = st.text_area("Keterangan", height=65, label_visibility="collapsed", placeholder="Catatan...")
                    
                    if st.form_submit_button("🚀 SIMPAN KE SUPABASE", use_container_width=True):
                        if f_nom > 0:
                            # --- 1. SINKRON KE SUPABASE (MASTER DATA BARU) ---
                            data_kas_sb = {
                                "Tanggal": sekarang.strftime('%Y-%m-%d'),
                                "Tipe": f_tipe,
                                "Kategori": f_kat,
                                "Nominal": str(int(f_nom)),
                                "Keterangan": f_ket,
                                "Pencatat": user_sekarang.upper()
                            }
                            supabase.table("Arus_Kas").insert(data_kas_sb).execute()

                            # --- 2. CATAT LOG AKTIVITAS (CCTV) ---
                            tambah_log(user_sekarang, f"INPUT KAS: {f_tipe} - {f_kat} (Rp {f_nom:,.0f})")

                            st.success("Tersimpan!"); time.sleep(1); st.rerun()
                        else:
                            st.warning("Nominal harus lebih dari 0!")

            with col_logs:
                # Log Terakhir: Ambil dari df_k_f yang sudah difilter Supabase
                with st.container(height=315):
                    if not df_k_f.empty:
                        df_logs_display = df_k_f.sort_values(by='TGL_TEMP', ascending=False).head(8)
                        for _, r in df_logs_display.iterrows():
                            # FIX: Pastikan nominal jadi float buat formatting
                            nom_val = float(r['NOMINAL'])
                            color = "#00ba69" if r['TIPE'] == "PENDAPATAN" else "#ff4b4b"
                            st.markdown(f"""
                            <div style='font-size:11px; border-bottom:1px solid #333; padding:4px 0;'>
                                <b style='color:#ccc;'>{r['KATEGORI']}</b> 
                                <span style='float:right; color:{color}; font-weight:bold;'>Rp {nom_val:,.0f}</span><br>
                                <span style='color:#666; font-style:italic;'>{r['KETERANGAN']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("Belum ada data transaksi.")

            with col_viz:
                st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
                df_donut = pd.DataFrame({"Kat": ["INCOME", "OUTCOME"], "Val": [inc_val, total_out_riil]})
                if (inc_val + total_out_riil) > 0:
                    fig = px.pie(df_donut, values='Val', names='Kat', hole=0.75, 
                                 color_discrete_sequence=["#00ba69", "#ff4b4b"])
                    
                    fig.update_layout(
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(size=10)),
                        height=200, 
                        margin=dict(t=0, b=0, l=0, r=0),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.markdown("<p style='text-align:center; color:#666; font-size:12px; margin-top:50px;'>Belum ada data visualisasi untuk periode ini.</p>", unsafe_allow_html=True)
                    
        # ======================================================================
        # --- 4. MASTER MONITORING & RADAR TIM (VERSI SUPABASE FULL SYNC) ---
        # ======================================================================
        st.write(""); st.markdown("### 📡 RADAR PERFORMA TIM")
        
        kolom_card = st.columns(4)
        rekap_v_total, rekap_b_total_all, rekap_h_malas = 0, 0, 0
        performa_staf = {}

        df_staff_filtered = df_staff[df_staff['LEVEL'].isin(['STAFF', 'UPLOADER', 'ADMIN'])]

        for idx, s in df_staff_filtered.reset_index().iterrows():
            n_up = str(s.get('NAMA', '')).strip().upper()
            if n_up == "" or n_up == "NAN": continue
            
            df_a_staf_r = df_a_f[df_a_f['NAMA'].str.upper() == n_up].copy() if not df_a_f.empty else pd.DataFrame(columns=['NAMA', 'TANGGAL'])
            df_t_staf_r = df_f_f[df_f_f['STAF'] == n_up].copy() if not df_f_f.empty else pd.DataFrame(columns=['STAF', 'STATUS'])

            lv_staf_ini = str(s.get('LEVEL', 'STAFF')).strip().upper()
            
            try:
                b_lembur_staf, u_absen_staf, pot_sp_r, level_sp_r, h_lemah_staf = hitung_logika_performa_dan_bonus(
                    df_t_staf_r, df_a_staf_r, bulan_dipilih, tahun_dipilih,
                    level_target=lv_staf_ini
                )
            except:
                b_lembur_staf, u_absen_staf, pot_sp_r, level_sp_r, h_lemah_staf = 0, 0, 0, "NORMAL", 0
            
            # --- LOGIKA SINKRONISASI BONUS (SUPABASE READY) ---
            bonus_real_staf = 0
            if not df_kas.empty:
                df_kas_temp = df_kas.copy()
                df_kas_temp['NOMINAL_INT'] = pd.to_numeric(df_kas_temp['NOMINAL'].astype(str).replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
                
                # FIX: Gunakan .isin(['TIM', 'GAJI TIM']) biar sinkron sama database lo
                mask_staf_kas = (df_kas_temp['KATEGORI'].str.upper().isin(['TIM', 'GAJI TIM'])) & \
                                (df_kas_temp['KETERANGAN'].str.upper().str.contains(n_up, na=False)) & \
                                (pd.to_datetime(df_kas_temp['TANGGAL'], errors='coerce').dt.month == bulan_dipilih)
                
                bonus_real_staf = df_kas_temp[mask_staf_kas]['NOMINAL_INT'].sum()
            
            # --- GABUNGKAN BONUS KAS + BONUS ABSENSI BERJALAN ---
            total_bonus_display = bonus_real_staf + u_absen_staf
            
            jml_v = len(df_t_staf_r)
            rekap_v_total += jml_v
            performa_staf[n_up] = jml_v
            
            jml_cancel = 0
            if not df_t_bln.empty and 'STAF' in df_t_bln.columns:
                jml_cancel = len(df_t_bln[(df_t_bln['STAF'] == n_up) & (df_t_bln['STATUS'].astype(str).str.upper() == 'CANCELED')])
            
            h_cair = 0
            if n_up in rekap_harian_tim:
                h_cair = sum(1 for qty in rekap_harian_tim[n_up].values() if qty >= 3)
            
            rekap_b_total_all += total_bonus_display 
            rekap_h_malas += h_lemah_staf

            t_hadir = 0
            if not df_a_f.empty:
                t_hadir = len(df_a_f[df_a_f['NAMA'].astype(str).str.upper() == n_up]['TANGGAL'].unique())
                
            warna_bg = "#1d976c" if level_sp_r == "NORMAL" or "PROTEKSI" in level_sp_r else "#f39c12" if level_sp_r == "SP 1" else "#e74c3c"

            # --- TAMPILAN CARD ---
            with kolom_card[idx % 4]:
                with st.container(border=True):
                    st.markdown(f'<div style="text-align:center; padding:5px; background:{warna_bg}; border-radius:8px 8px 0 0; margin:-15px -15px 10px -15px;"><b style="color:white; font-size:14px;">{n_up}</b></div>', unsafe_allow_html=True)
                    
                    m1, m2, m3 = st.columns(3)
                    m1.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>FINISH</p><b style='font-size:14px;'>{int(jml_v)}</b>", unsafe_allow_html=True)
                    m2.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>CANCEL</p><b style='font-size:14px; color:#e74c3c;'>{jml_cancel}</b>", unsafe_allow_html=True)
                    m3.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>ABSEN</p><b style='font-size:14px;'>{t_hadir}H</b>", unsafe_allow_html=True)
                    
                    st.divider()
                    
                    det1, det2 = st.columns(2)
                    det1.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>🚩 STATUS</p><b style='font-size:11px;'>{level_sp_r}</b>", unsafe_allow_html=True)
                    det2.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>⚠️ HARI LEMAH</p><b style='font-size:12px; color:#e74c3c;'>{h_lemah_staf} Hari</b>", unsafe_allow_html=True)
                    
                    det1.markdown(f"<p style='margin:5px 0 0 0; font-size:10px; color:#888;'>✨ HARI CAIR</p><b style='font-size:12px;'>{h_cair} Hari</b>", unsafe_allow_html=True)
                    # FIX: Variabel diganti ke total_bonus_display agar bonus absen muncul
                    det2.markdown(f"<p style='margin:5px 0 0 0; font-size:10px; color:#888;'>💰 TOTAL BONUS</p><b style='font-size:12px; color:#1d976c;'>Rp {int(total_bonus_display):,}</b>", unsafe_allow_html=True)
                    
                    prog_val = min(h_lemah_staf / 7, 1.0) if h_lemah_staf > 0 else 0.0
                    st.progress(prog_val)
                    
        # ======================================================================
        # --- 5. RANGKUMAN KOLEKTIF TIM (FULL SUPABASE & SYNC CATEGORY) ---
        # ======================================================================
        with st.container(border=True):
            st.markdown("<p style='font-size:12px; font-weight:bold; color:#888; margin-bottom:15px;'>📊 RANGKUMAN KOLEKTIF TIM</p>", unsafe_allow_html=True)
            
            # 1. Ambil Nama Staff Aktif
            nama_staff_asli = df_staff[df_staff['LEVEL'] == 'STAFF']['NAMA'].str.upper().tolist()
            performa_hanya_staff = {k: v for k, v in performa_staf.items() if k in nama_staff_asli}
            
            if performa_hanya_staff and any(v > 0 for v in performa_hanya_staff.values()):
                staf_top = max(performa_hanya_staff, key=performa_hanya_staff.get)
                staf_low = min(performa_hanya_staff, key=performa_hanya_staff.get)
            else:
                staf_top = "-"
                staf_low = "-"
            
            # --- LOGIKA SINKRONISASI KAS (FULL SUPABASE SYNC) ---
            # Kita gunakan df_k_f yang sudah disaring di awal fungsi agar lebih ringan
            real_b_video_kolektif = 0
            real_b_absen_kolektif = 0
            
            if not df_k_f.empty:
                df_cair = df_k_f.copy()
                # Pastikan Nominal bersih
                df_cair['NOMINAL_FIX'] = pd.to_numeric(df_cair['NOMINAL'].astype(str).replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
                
                # FIX: Gunakan kategori 'TIM' atau 'GAJI TIM' sesuai temuan foto Supabase tadi
                mask_kategori_tim = df_cair['KATEGORI'].str.upper().isin(['TIM', 'GAJI TIM'])
                
                # Logika pencarian kata kunci di keterangan Kas
                mask_video = mask_kategori_tim & (df_cair['KETERANGAN'].str.upper().str.contains('VIDEO|LEMBUR', na=False))
                real_b_video_kolektif = df_cair[mask_video]['NOMINAL_FIX'].sum()
                
                mask_absen = mask_kategori_tim & (df_cair['KETERANGAN'].str.upper().str.contains('ABSEN', na=False))
                real_b_absen_kolektif = df_cair[mask_absen]['NOMINAL_FIX'].sum()

            # --- DISPLAY METRIC (7 KOLOM) ---
            c_r1, c_r2, c_r3, c_r4, c_r5, c_r6, c_r7 = st.columns(7)
            
            # Itungan Target (Misal target 60 video per staff)
            target_fix = len(nama_staff_asli) * 60
            c_r1.metric("🎯 TARGET IDEAL", f"{target_fix} Vid") 
            
            persen_capaian = (rekap_v_total / target_fix * 100) if target_fix > 0 else 0
            c_r2.metric("🎬 TOTAL VIDEO", f"{int(rekap_v_total)}", delta=f"{persen_capaian:.1f}%")
            
            c_r3.metric("🔥 BONUS VIDEO", f"Rp {int(real_b_video_kolektif):,}", delta="LIVE")
            
            # FIX: Gunakan variabel real_b_absen_kolektif yang konsisten
            c_r4.metric("📅 BONUS ABSEN", f"Rp {int(real_b_absen_kolektif):,}", delta="LIVE")
            
            c_r5.metric("💀 TOTAL LEMAH", f"{rekap_h_malas} HR", delta="Staff Only", delta_color="inverse")
            c_r6.metric("👑 MVP STAF", staf_top)
            c_r7.metric("📉 LOW STAF", staf_low)

        # ======================================================================
        # --- 7. DATABASE AKUN AI (FULL SUPABASE - INSTANT RESET) ---
        # ======================================================================
        with st.expander("🔐 DATABASE AKUN AI", expanded=False):
            try:
                # 1. AMBIL DATA SUPER CEPAT DARI SUPABASE
                df_ai = ambil_data_segar("Akun_AI")
                
                # 2. TOMBOL TAMBAH AKUN
                if st.button("➕ TAMBAH AKUN BARU", use_container_width=True):
                    st.session_state.form_ai = not st.session_state.get('form_ai', False)
                
                if st.session_state.get('form_ai', False):
                    with st.form("input_ai_supa", clear_on_submit=True):
                        f1, f2, f3 = st.columns(3)
                        v_ai = f1.text_input("Nama Tool (ChatGPT/Midjourney)")
                        v_mail = f2.text_input("Email Login")
                        v_pass = f3.text_input("Password")
                        v_exp = st.date_input("Tanggal Expired")
                        
                        if st.form_submit_button("🚀 SIMPAN KE SUPABASE"):
                            if v_ai and v_mail:
                                data_baru = {
                                    "AI": v_ai,
                                    "EMAIL": v_mail,
                                    "PASSWORD": v_pass,
                                    "EXPIRED": str(v_exp),
                                    "PEMAKAI": "X",
                                    "TANGGAL_KLAIM": ""
                                }
                                supabase.table("Akun_AI").insert(data_baru).execute()
                                tambah_log(user_sekarang, f"TAMBAH AKUN AI: {v_ai} ({v_mail})")
                                st.success("Berhasil Tersimpan!"); time.sleep(1); st.rerun()

                st.divider()
                        
                if not df_ai.empty:
                    # Pastikan Nama Kolom Sesuai (Upper/Lower)
                    df_ai.columns = [c.upper() for c in df_ai.columns]
                    
                    # 1. SETUP TANGGAL & PRIORITAS
                    h_ini = sekarang.date()
                    df_ai['TGL_OBJ'] = pd.to_datetime(df_ai['EXPIRED'], errors='coerce').dt.date
                    
                    def tentukan_urutan(r):
                        if pd.isna(r['TGL_OBJ']): return 4
                        sisa_hr = (r['TGL_OBJ'] - h_ini).days
                        val_pemakai = str(r.get('PEMAKAI', '')).strip()
                        is_kosong = pd.isna(r['PEMAKAI']) or val_pemakai == "" or val_pemakai.upper() == "X"
                        
                        if is_kosong: return 1
                        elif sisa_hr <= 7: return 2
                        else: return 3

                    df_ai['PRIO'] = df_ai.apply(tentukan_urutan, axis=1)
                    df_sorted = df_ai.sort_values(by=['PRIO', 'TGL_OBJ'], ascending=[True, True]).copy()

                    # 2. LOOPING TAMPILAN
                    for idx, r in df_sorted.iterrows():
                        tgl_exp = r['TGL_OBJ']
                        if pd.isna(tgl_exp): continue
                        
                        sisa = (tgl_exp - h_ini).days
                        if sisa < -1: continue # Biarkan 1 hari expired terlihat untuk warning
                        
                        if sisa > 7: warna_h, stat_ai = "#2D5A47", "🟢 AMAN"
                        elif 0 <= sisa <= 7: warna_h, stat_ai = "#8B5E3C", "🟠 LIMIT"
                        else: warna_h, stat_ai = "#633535", "🔴 MATI"

                        with st.container(border=True):
                            st.markdown(f'<div style="padding:2px; background:{warna_h}; border-radius:5px; margin-bottom:10px; text-align:center;"><b style="color:white; font-size:11px;">🚀 {str(r["AI"]).upper()}</b></div>', unsafe_allow_html=True)

                            c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1.5, 1, 1, 1, 0.8, 1.2])
                            
                            c1.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>📧 EMAIL</p><code style='font-size:12px;'>{r['EMAIL']}</code>", unsafe_allow_html=True)
                            c2.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>🔑 PASSWORD</p><code style='font-size:12px;'>{r['PASSWORD']}</code>", unsafe_allow_html=True)
                            
                            val_user = str(r['PEMAKAI']).strip()
                            is_null = pd.isna(r['PEMAKAI']) or val_user == "" or val_user.upper() == "X"
                            user_display = "🆕 KOSONG" if is_null else r['PEMAKAI']
                            
                            c3.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>👤 PEMAKAI</p><b style='font-size:12px;'>{user_display}</b>", unsafe_allow_html=True)
                            c4.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>📡 STATUS</p><b style='font-size:11px;'>{stat_ai}</b>", unsafe_allow_html=True)
                            c5.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>📅 EXPIRED</p><b style='font-size:11px;'>{tgl_exp.strftime('%d %b')}</b>", unsafe_allow_html=True)
                            c6.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>⏳ SISA</p><b style='font-size:13px; color:{warna_h};'>{sisa} Hr</b>", unsafe_allow_html=True)
                            
                            # --- FITUR RESET FULL SUPABASE ---
                            if c7.button(f"🔄 RESET", key=f"res_ai_{idx}", use_container_width=True):
                                # Reset langsung pakai Email sebagai kunci (Primary Key/Unique)
                                supabase.table("Akun_AI").update({"PEMAKAI": "X", "TANGGAL_KLAIM": ""}).eq("EMAIL", r['EMAIL']).execute()
                                tambah_log(user_sekarang, f"RESET AKUN AI: {r['AI']} ({r['EMAIL']})")
                                st.success(f"✅ Reset Berhasil!"); time.sleep(0.5); st.rerun()
                else:
                    st.info("📭 Belum ada data akun AI di database.")

            except Exception as e_ai:
                st.error(f"Gagal memuat Database Akun AI: {e_ai}")
            
        # ======================================================================
        # --- 6. RINCIAN GAJI & SLIP (FULL SUPABASE - SINKRON REAL-TIME) ---
        # ======================================================================
        with st.expander("💰 RINCIAN GAJI & SLIP", expanded=False):
            try:
                ada_kerja = False
                df_staff_raw_slip = df_staff[df_staff['LEVEL'].isin(['STAFF', 'UPLOADER', 'ADMIN'])].copy()
                
                # Kita tidak perlu ambil_data_segar lagi, gunakan df_k_f yang sudah ada di atas
                # agar loading secepat kilat (f/16)
                
                for idx, s in df_staff_raw_slip.reset_index().iterrows():
                    n_up = str(s.get('NAMA', '')).strip().upper()
                    if n_up == "" or n_up == "NAN": continue
                    
                    # --- 1. DATA FILTERING SPESIFIK STAF ---
                    df_absen_staf_slip = df_a_f[df_a_f['NAMA'].str.upper() == n_up].copy() if not df_a_f.empty else pd.DataFrame()
                    df_arsip_staf_slip = df_f_f[df_f_f['STAF'] == n_up].copy() if not df_f_f.empty else pd.DataFrame()
                    lv_slip_ini = str(s.get('LEVEL', 'STAFF')).strip().upper()

                    # --- 2. MESIN HITUNG (SINKRON POTONGAN SP) ---
                    try:
                        _, _, pot_sp_admin, level_sp_admin, hari_lemah = hitung_logika_performa_dan_bonus(
                            df_arsip_staf_slip, df_absen_staf_slip, 
                            bulan_dipilih, tahun_dipilih, level_target=lv_slip_ini
                        )
                    except:
                        pot_sp_admin, level_sp_admin, hari_lemah = 0, "NORMAL", 0

                    # --- 3. DATA FINANSIAL (CLEANING GAPOK & TUNJANGAN) ---
                    v_gapok = int(pd.to_numeric(str(s.get('GAJI_POKOK', '0')).replace('.','').strip(), errors='coerce') or 0)
                    v_tunjangan = int(pd.to_numeric(str(s.get('TUNJANGAN', '0')).replace('.','').strip(), errors='coerce') or 0)
                    
                    # --- 4. FILTER DATA BONUS RIIL DARI KAS ---
                    bonus_video_real = 0
                    bonus_absen_real = 0
                    
                    if not df_k_f.empty:
                        df_k_slip = df_k_f.copy()
                        df_k_slip['NOMINAL_INT'] = pd.to_numeric(df_k_slip['NOMINAL'].astype(str).replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
                        
                        # FIX KATEGORI: Sesuaikan dengan foto Supabase lo ("Tim" & "Gaji Tim")
                        mask_slip = (df_k_slip['KATEGORI'].str.upper().isin(['TIM', 'GAJI TIM'])) & \
                                    (df_k_slip['KETERANGAN'].str.upper().str.contains(n_up, na=False))
                        
                        df_bonus_cair = df_k_slip[mask_slip]
                        if not df_bonus_cair.empty:
                            # Logika pecah bonus berdasarkan keterangan
                            bonus_video_real = int(df_bonus_cair[df_bonus_cair['KETERANGAN'].str.upper().str.contains('VIDEO|LEMBUR', na=False)]['NOMINAL_INT'].sum())
                            bonus_absen_real = int(df_bonus_cair[df_bonus_cair['KETERANGAN'].str.upper().str.contains('ABSEN', na=False)]['NOMINAL_INT'].sum())

                    # --- 5. RUMUS FINAL ---
                    v_total_terima = max(0, (v_gapok + v_tunjangan + bonus_absen_real + bonus_video_real) - pot_sp_admin)
                    ada_kerja = True

                    # --- 6. TAMPILAN VCARD ---
                    with kol_v[idx % 2]:
                        with st.container(border=True):
                            # Header VCard Tetap Sama (Udah Keren)
                            st.markdown(f"""
                            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                                <div style="background: linear-gradient(135deg, #1d976c, #93f9b9); color: white; width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px;">{n_up[0]}</div>
                                <div>
                                    <b style="font-size: 15px;">{n_up}</b><br>
                                    <span style="font-size: 11px; color: #888;">{s.get('JABATAN', 'STAFF PRODUCTION')}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            c1, c2 = st.columns(2)
                            # FIX: Pastikan v_total_terima sudah pakai total_bonus_display dari Supabase
                            c1.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>ESTIMASI TERIMA</p><h3 style='margin:0; color:#1d976c;'>Rp {v_total_terima:,}</h3>", unsafe_allow_html=True)
                            c2.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>STATUS SP</p><b style='font-size:14px; color:{'#e74c3c' if pot_sp_admin > 0 else '#1d976c'};'>{level_sp_admin}</b>", unsafe_allow_html=True)
                            
                            st.divider()

                            if st.button(f"📄 PREVIEW & PRINT SLIP {n_up}", key=f"vcard_{n_up}", use_container_width=True):
                                # --- RUMUS SLIP FIX: PASTIKAN BONUS REAL-TIME ---
                                slip_html = f"""
                                <div id="slip-gaji-full" style="background: white; padding: 30px; border-radius: 20px; border: 1px solid #eee; font-family: sans-serif; width: 350px; margin: auto; color: #333; box-shadow: 0 10px 30px rgba(0,0,0,0.05);">
                                    <center>
                                        <img src="https://raw.githubusercontent.com/pintarkantor-prog/pintarmedia/main/PINTAR.png" style="width: 220px; margin-bottom: 10px;">
                                        <div style="height: 3px; background: #1d976c; width: 50px; border-radius: 10px; margin-bottom: 5px;"></div>
                                        <p style="font-size: 10px; letter-spacing: 4px; color: #1d976c; font-weight: 800; text-transform: uppercase;">Slip Gaji Resmi</p>
                                    </center>
                                    <div style="background: #fcfcfc; padding: 15px; border-radius: 12px; border: 1px solid #f0f0f0; margin: 20px 0;">
                                        <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
                                            <tr><td style="color: #999; font-weight: 600; text-transform: uppercase;">Nama</td><td align="right"><b>{n_up}</b></td></tr>
                                            <tr><td style="color: #999; font-weight: 600; text-transform: uppercase;">Jabatan</td><td align="right"><b>{s.get('JABATAN', 'STAFF')}</b></td></tr>
                                            <tr><td style="color: #999; font-weight: 600; text-transform: uppercase;">Periode</td><td align="right"><b>{pilihan_nama} {tahun_dipilih}</b></td></tr>
                                        </table>
                                    </div>
                                    <table style="width: 100%; font-size: 13px; line-height: 2.2; border-collapse: collapse;">
                                        <tr><td style="color: #666;">Gaji Pokok</td><td align="right" style="font-weight: 600;">Rp {v_gapok:,}</td></tr>
                                        <tr><td style="color: #666;">Tunjangan</td><td align="right" style="font-weight: 600;">Rp {v_tunjangan:,}</td></tr>
                                        <tr style="color: #1d976c; font-weight: 600;"><td>Bonus Absen </td><td align="right">+ {bonus_absen_real:,}</td></tr>
                                        <tr style="color: #1d976c; font-weight: 600;"><td>Bonus Video </td><td align="right">+ {bonus_video_real:,}</td></tr>
                                        <tr style="border-top: 1px solid #f0f0f0; color: #e74c3c; font-weight: 600;"><td style="padding-top: 5px;">Potongan SP ({hari_lemah} Hari)</td><td align="right" style="padding-top: 5px;">- {pot_sp_admin:,}</td></tr>
                                    </table>
                                    <div style="background: #1a1a1a; color: white; padding: 15px; border-radius: 15px; text-align: center; margin-top: 25px;">
                                        <p style="margin: 0; font-size: 9px; color: #55efc4; text-transform: uppercase; letter-spacing: 2px; font-weight: 700;">Total Diterima</p>
                                        <h2 style="margin: 5px 0 0; font-size: 26px; color: #55efc4; font-weight: 800;">Rp {v_total_terima:,}</h2>
                                    </div>
                                    <div style="margin-top: 30px; text-align: center; font-size: 9px; color: #bbb; border-top: 1px solid #f5f5f5; padding-top: 15px;">
                                        <b>Diterbitkan secara digital oleh Sistem PINTAR MEDIA</b><br>
                                        Waktu Cetak: {sekarang.strftime('%d/%m/%Y %H:%M:%S')} WIB
                                    </div>
                                </div>
                                <div style="text-align: center; margin-top: 20px;">
                                    <button onclick="window.print()" style="padding: 12px 25px; background: #1a1a1a; color: #55efc4; border: 2px solid #55efc4; border-radius: 10px; font-weight: bold; cursor: pointer;">🖨️ SIMPAN SEBAGAI PDF</button>
                                </div>
                                """
                                st.components.v1.html(slip_html, height=800)

                if not ada_kerja:
                    st.info("Belum ada data gaji untuk periode ini.")

            except Exception as e_slip:
                st.error(f"Gagal memuat Rincian Gaji Sinkron: {e_slip}")

        # ======================================================================
        # --- 8. PINTAR COMMAND CENTER (FULL SUPABASE - NO GSHEET) ---
        # ======================================================================
        with st.expander("🛠️ PINTAR COMMAND CENTER", expanded=False):
            st.info("Gunakan ini untuk intervensi data (HADIR/IZIN/SAKIT/OFF).")
            
            # Ambil daftar staf (Exclude Owner)
            list_staf = df_staff[df_staff['LEVEL'] != 'OWNER']['NAMA'].unique().tolist()
            
            c_staf, c_aksi, c_tgl = st.columns([1.5, 1.5, 1])
            with c_staf: target = st.selectbox("Pilih Staf:", list_staf, key="cmd_staf")
            with c_aksi: status_baru = st.selectbox("Set Status:", ["HADIR", "IZIN", "SAKIT", "OFF", "TELAT"], key="cmd_stat")
            with c_tgl: tgl_cmd = st.date_input("Tanggal:", value=sekarang.date(), key="cmd_tgl")
            
            if st.button("🔥 EKSEKUSI PERUBAHAN", use_container_width=True):
                tgl_s = tgl_cmd.strftime("%Y-%m-%d")
                jam_s = "08:00" if status_baru == "HADIR" else "-"
                
                try:
                    # 1. CEK DATA (Upsert Logic di Supabase)
                    # Kita cari apakah sudah ada absen di tanggal tersebut untuk nama tersebut
                    res = supabase.table("Absensi").select("id").eq("Nama", target).eq("Tanggal", tgl_s).execute()
                    
                    if len(res.data) > 0:
                        # UPDATE: Jika data sudah ada, kita tindih statusnya
                        supabase.table("Absensi").update({
                            "Status": status_baru, 
                            "Jam Masuk": jam_s
                        }).eq("Nama", target).eq("Tanggal", tgl_s).execute()
                        aksi_tipe = "UPDATE"
                    else:
                        # INSERT: Jika belum ada (misal staf lupa absen total), kita buatkan baris baru
                        supabase.table("Absensi").insert({
                            "Nama": target, 
                            "Tanggal": tgl_s, 
                            "Status": status_baru, 
                            "Jam Masuk": jam_s
                        }).execute()
                        aksi_tipe = "INSERT BARU"
                    
                    # 2. CATAT LOG AKTIVITAS (CCTV)
                    tambah_log(user_sekarang, f"INTERVENSI ABSEN: {target} set {status_baru} tgl {tgl_s} ({aksi_tipe})")

                    st.success(f"✅ Berhasil! {target} sekarang {status_baru}"); time.sleep(1); st.rerun()
                
                except Exception as e:
                    st.error(f"Gagal Eksekusi: {e}")

    except Exception as e:
        st.error(f"⚠️ Terjadi Kendala Sistem Utama: {e}")
        
def tampilkan_area_staf():
    st.title("📘 Pusat Informasi")
    
    # --- 1. PAPAN PENGUMUMAN ---
    st.info("""
    📢 **PENGUMUMAN TERBARU:**
    - Libur Hari Raya Idul Fitri Mulai Tanggal 18 - 23 maret (Tanggal 24 masuk normal).
    - Pastikan semua file di Google Drive sudah diberi nama sesuai SOP terbaru.
    - Sistem masih tahap pengembangan jika ada selisih atau error system, segera lapor Owner! 🚀
    """)
    
    st.write("") # Spasi inisiasi

    # --- 2. SISTEM TABS ---
    t1, t2, t3, t4, t5 = st.tabs([
        "📋 Panduan (SOP)", 
        "💰 Simulasi Gaji", 
        "🚨 Aturan SP", 
        "⚖️ Peraturan", 
        "📜 Kontrak Kerja"
    ])

    with t1:
        st.write("")
        st.markdown("#### 🚀 Panduan Kerja & Standar Kualitas (SOP)")

        # --- SUB-TAB POSISI ---
        divisi_sop = st.radio(
            "Pilih Posisi Kamu:",
            ["Staff Editor", "Staff Uploader", "Admin"],
            horizontal=True,
            key="pilih_sop_v_final_sultan"
        )

        if divisi_sop == "Staff Editor":
            nama_user = st.session_state.get('username', 'Staff Editor')
            st.markdown(f"**Update Terakhir:** 1 Maret 2026")
            
            # --- I. STANDAR PRODUKSI UMUM (Tetap di Dashboard) ---
            st.markdown("##### 🎨 I. STANDAR PRODUKSI UMUM (WAJIB)")
            with st.container(border=True):
                st.success("**Poin ini adalah fondasi kualitas di PINTAR MEDIA. Jika salah satu poin tidak terpenuhi, Owner berhak menolak setoran video.**")
                st.write("• **Kualitas Visual**: Minimal 1080p Full HD.")
                st.write("• **Aspect Ratio**: Format 9:16 (1080x1920).")
                st.write("• **Durasi**: Minimal 60 detik. Durasi harus padat berisi, dilarang memberikan adegan kosong (filler).")
                st.write("• **Audio & SFX**: Wajib Copyright-Free. Sangat direkomendasikan menggunakan musik dari YouTube Audio Library.")
                st.write("• **Backup & Penamaan**: Aset mentah wajib disimpan minimal 3 hari. Format: **TGL_NAMA_JUDUL.mp4**")

            # --- II. KETENTUAN UNIT & POIN (Tetap di Dashboard) ---
            st.markdown("##### 📊 II. KETENTUAN KERJA & BONUS INSENTIF")
            with st.container(border=True):
                st.info("**Aturan ini dibuat agar beban kerja adil bagi semua staf (HQ vs Ringan).**")
                st.write("• **PROJECT HQ**: 1 Link GDrive berisi 1 Video.")
                st.write("• **PROJECT RINGAN**: 1 Link GDrive berisi 15 Video = **nilainya setara dengan 1 video HQ**.")
                st.write("• **Video ke-3 status acc (Bonus Absensi)**: Bonus Rp 30.000 dicairkan otomatis.")
                st.write("• **Video ke-5 status acc & Seterusnya**: Bonus tambahan Rp 30.000 per video.")
                st.write("• **TUNJANGAN KERJA**: Rp 500.000 (target 70 video perbulan).")

            # --- III. MODUL PANDUAN (FULL DETAIL A-E) ---
            with st.expander("📜 III. MODUL PANDUAN STRUKTUR KONTEN AI (HQ)", expanded=False):
                html_konten_pdf = f"""
                <div style="background: white; padding: 50px; font-family: 'Arial', sans-serif; color: black; line-height: 1.6; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 20px;">
                    
                    <center>
                        <img src="https://raw.githubusercontent.com/pintarkantor-prog/pintarmedia/main/PINTAR.png" style="width: 250px; margin-bottom: 5px;">
                        <div style="border-top: 3px solid #000; border-bottom: 1px solid #000; padding: 2px 0; margin-top: 10px;"></div>
                        <br>
                        <h3 style="margin: 0; font-size: 18px; color: #333; letter-spacing: 1px;">PANDUAN STRUKTUR KONTEN AI</h3>
                        <span style="font-size: 12px; color: #666;">NOMOR: 001/PANDUAN-HQ/PINTARMEDIA/III/2026</span>
                    </center>
                    <br><br>

                    <div style="margin-bottom: 40px; border-left: 5px solid #d32f2f; padding-left: 20px;">
                        <b style="font-size: 18px; color: #d32f2f;">🔥 1. ALUR: EMOTIONAL ( Direndahkan -> Balas Dendam )</b><br><br>
                        
                        <b>A. Bagian Awal (Hook - Penindasan)</b><br>
                        Tampilkan adegan di mana karakter utama sedang dihina, diusir, atau diremehkan oleh karakter lain karena kondisi fisiknya, kemiskinannya, atau kelemahannya.<br>
                        <i><b>Instruksi Visual:</b> Ekspresi AI wajib terlihat sangat sedih, tertekan, atau marah besar. Lawan main harus terlihat angkuh/sombong.</i><br>
                        <i><b>Tujuan:</b> Memancing amarah dan rasa kasihan penonton dalam 15 detik pertama agar mereka tidak scroll video.</i><br><br>

                        <b>B. Bagian Transisi ( Titik Balik)</b><br>
                        Momen di mana misalnya, karakter utama memutuskan untuk mulai bangkit. Tampilkan adegan karakter menatap masa depan dengan tekad kuat.<br>
                        <i><b>Instruksi Visual:</b> Perubahan ekspresi dari sedih menjadi fokus/serius. Mulai melakukan aksi nyata (belajar, berlatih, bekerja, atau menemukan kekuatan/keajaiban).</i><br><br>

                        <b>C. Bagian Tengah (Proses & Dukungan)</b><br>
                        Tampilkan proses perjuangan karakter yang tidak instan. Di sini kita masukkan elemen Emotional Investment dari penonton.<br>
                        <i><b>Instruksi Visual:</b> Tampilkan 2-3 adegan progresif. Misal: Awalnya memungut sampah ➔ Mulai berjualan kecil ➔ Mulai sukses.</i><br>
                        <i><b>Interaksi Penonton:</b> Masukkan ajakan di tengah proses ini: "Misalnya: bantu Like dan Subscribe guys.. biar lebih semangat lagi!". Penonton merasa kesuksesan karakter adalah berkat bantuan mereka.</i><br><br>

                        <b>D. Bagian Klimaks (Perubahan Signifikan)</b><br>
                        Tampilkan kembalinya si karakter utama dengan perubahan yang sangat drastis dan mengejutkan.<br>
                        <i><b>Instruksi Visual:</b> Penampilan harus berubah 180 derajat (Pakaian mewah, kendaraan bagus, atau aura yang sangat berwibawa/kuat). Ekspresi wajib terlihat puas, bangga, dan tenang.</i><br><br>

                        <b>E. Bagian Akhir (Ending - Pembuktian)</b><br>
                        Tampilkan konfrontasi terakhir dengan orang yang dulu menghinanya. Orang tersebut terlihat malu, menyesal, atau ketakutan.<br>
                        <i><b>Instruksi Visual:</b> Karakter utama tidak perlu membalas dengan kemarahan, cukup dengan tindakan elegan atau senyum kemenangan yang "mahal".</i><br>
                        <i><b>Tujuan:</b> Memberikan kepuasan maksimal (Satisfying Ending) kepada penonton.</i>
                    </div>

                    <div style="margin-bottom: 40px; border-left: 5px solid #1976d2; padding-left: 20px;">
                        <b style="font-size: 18px; color: #1976d2;">⚔️ 2. ALUR: THE BATTLE / VS (PLOT TWIST ENDING)</b><br><br>
                        
                        <b>A. Bagian Awal (The Hook - Konfrontasi Panas)</b><br>
                        Tampilkan dua karakter atau lebih dalam posisi berhadapan dengan tensi tinggi. Bisa berupa persiapan lomba balap, kompetisi kekuatan, atau perdebatan sengit.<br>
                        <i><b>Instruksi Visual:</b> Zoom-in ke arah mata karakter (eye-to-eye). Gunakan filter warna yang kontras untuk membedakan dua kubu. Ekspresi harus terlihat ambisius dan tak mau kalah.</i><br>
                        <i><b>Tujuan:</b> Memaksa penonton untuk langsung memihak salah satu jagoan (Engagement instan).</i><br><br>

                        <b>B. Bagian Dinamika (Adu Kekuatan)</b><br>
                        Tampilkan cuplikan-cuplikan pertandingan yang intens. Gunakan transisi cepat dan efek suara (SFX) untuk setiap benturan atau aksi.<br>
                        <i><b>Instruksi Visual:</b> Fast-cut editing. Tampilkan pergantian dominasi, sebentar si A yang memimpin, sebentar kemudian si B yang membalas. Jangan buat satu karakter terlihat menang terlalu mudah di sini.</i><br><br>

                        <b>C. Bagian Tengah (The Critical Moment)</b><br>
                        Momen di mana pertandingan mencapai puncaknya atau ada karakter yang hampir tumbang. Ini adalah waktu terbaik untuk memanggil dukungan penonton.<br>
                        <i><b>Instruksi Visual:</b> Slow motion pada momen krusial. Karakter terlihat mulai kelelahan tapi tetap berusaha.</i><br>
                        <i><b>Interaksi Penonton:</b> Munculkan bantuan like dan subscribe atau teks polling visual: "Ketik 1 untuk dukung Udin, Ketik 2 untuk dukung Tung!". Buat penonton merasa suara mereka menentukan hasil duel.</i><br><br>

                        <b>D. Bagian Klimaks (The Plot Twist - Kejutan Tak Terduga)</b><br>
                        Ini adalah inti dari alur Battle. Saat penonton mengira salah satu akan menang, hadirkan kejadian yang di luar nalar atau tidak terduga.<br>
                        <i><b>Instruksi Visual:</b> Misal: Munculnya kekuatan tersembunyi, bantuan karakter misterius, atau justru kedua karakter malah bekerja sama melawan musuh baru yang lebih besar.</i><br>
                        <i><b>Tujuan:</b> Menciptakan efek "Mind-Blowing" agar penonton menonton sampai detik terakhir.</i><br><br>

                        <b>E. Bagian Akhir (The Retention - Pertanyaan Terbuka)</b><br>
                        Tampilkan hasil akhir yang memicu diskusi panjang di kolom komentar.<br>
                        <i><b>Instruksi Visual:</b> Pemenang memberikan pesan singkat atau tatapan menantang ke arah kamera.</i><br>
                        <i><b>Tujuan:</b> Memancing komentar perdebatan.</i>
                    </div>

                    <div style="margin-bottom: 30px; background: #f9f9f9; padding: 20px; border: 1px dashed #666;">
                        <b style="font-size: 16px;">📢 PANDUAN INTERAKSI (CTA - CALL TO ACTION)</b><br><br>
                        • <b>Timing:</b> Jangan letakkan CTA di awal yang mengganggu hook. Taruh di momen penonton sedang merasa "kasihan" atau "penasaran".<br>
                        • <b>Emotional CTA:</b> Gunakan kalimat ajakan yang melibatkan kontribusi penonton (Contoh: "Bantu Udin bangkit dengan klik Like").<br>
                        • <b>Debate CTA:</b> Gunakan pada konten Battle untuk memancing kolom komentar (Contoh: "Ketik 1 untuk Udin, 2 untuk Tung").<br>
                        • <b>Retention CTA:</b> Ajakan untuk menonton part selanjutnya atau memberikan ide konten (Contoh: "Ketik LANJUT buat liat pembalasan berikutnya!").
                    </div>

                    <div style="margin-top: 50px; font-size: 11px; text-align: center; color: #666; border-top: 1px solid #eee; padding-top: 10px;">
                        📌 Update Terakhir: 1 Maret 2026. Panduan bersifat dinamis dan dapat direvisi sesuai kebutuhan.
                    </div>
                </div>
                """
                # Tampilan di dashboard
                st.components.v1.html(html_konten_pdf, height=1300, scrolling=True)

                # Tombol Print
                if st.button(f"📄 PREVIEW & PRINT MODUL {nama_user.upper()}", use_container_width=True):
                    html_with_print = html_konten_pdf + "<script>window.print();</script>"
                    st.components.v1.html(html_with_print, height=0)
    
        elif divisi_sop == "Staff Uploader":
            st.markdown(f"**Update Terakhir:** 1 Maret 2026")

            # --- I. STANDAR PRODUKSI UMUM (Tetap di Dashboard) ---
            st.markdown("##### 🎨 I. STANDAR OPERASIONAL UPLOADER (WAJIB)")
            with st.container(border=True):
                st.success("**Uploader adalah gerbang terakhir kualitas konten. Kesalahan upload berarti hilangnya potensi traffic.**")
                st.write("• **Scheduling**: Wajib upload sesuai jadwal yang ditentukan (Prime Time).")
                st.write("• **Optimasi Metadata**: Menentukan judul (memancing Click-bait positif), menulis deskripsi, dan memilih Tag yang relevan.")
                st.write("• **Thumbnail**: Memilih frame paling dramatis/menarik sesuai inti dari video.")
                st.write("• **Stok Channel**: Wajib memastikan stok channel selalu ready (koordinasi dengan admin).")
                st.write("• **Stok Video**: Wajib memastikan stok video selalu ready (koordinasi dengan admin).")
            # --- II. KETENTUAN UNIT & POIN (Tetap di Dashboard) ---
            st.markdown("##### 📊 II. KETENTUAN KERJA & BONUS INSENTIF")
            with st.container(border=True):
                st.info("**Sistem ini memastikan distribusi konten berjalan konsisten setiap harinya.**")
                st.write("• **QC CHANNEL**: Selalu memastikan channel ready di setiap HP (Koordinasi dengan admin).")
                st.write("• **JADWAL UPLOAD**: Memastikan jadwal upload, jenis konten, dan HP sinkron.")
                st.write("• Uploader selalu koordinasi dengan admin terkait stok video dan channel yang akan diupload.")
                st.write("• Sistem SP dan Bonus ditentukan berdasarkan peforma kinerja (tidak mengikuti sistem otomatis).")

        elif divisi_sop == "Admin":
            st.markdown(f"**Update Terakhir:** 1 Maret 2026")

            # --- I. STANDAR PRODUKSI UMUM (Tetap di Dashboard) ---
            st.markdown("##### 🎨 I. STANDAR OPERASIONAL UPLOADER (WAJIB)")
            with st.container(border=True):
                st.success("**Admin adalah jantung operasional. Ketelitian data adalah prioritas utama untuk menghindari kerugian.**")
                st.write("• **Audit Kuota**: Memastikan stok akun ai dan kuota HP selalu ready setiap hari.")
                st.write("• **Scheduling**: Memastikan channel untuk upload hari esok ready dan membuat jadwal upload (koordinasi dengan uploader).")
                st.write("• **Stok Channel Ready-to-Use**: Menyiapkan stok channel cadangan yang sudah di-set up (Nama, Logo, Banner) agar saat dibutuhkan, staff uploader tinggal pakai.")
                st.write("• **Audit Kelayakan Channel**: Memilah channel mana yang performanya bagus dan mana yang busuk (yang busuk wajib diganti).")
                st.write("• **Monitoring Output**: Memastikan semua staff editor dan uploader bekerja dengan baik.")
            # --- II. KETENTUAN UNIT & POIN (Tetap di Dashboard) ---
            st.markdown("##### 📊 II. KETENTUAN KERJA & BONUS INSENTIF")
            with st.container(border=True):
                st.info("**Sistem ini memastikan operasional kantor berjalan konsisten setiap harinya.**")
                st.write("• **Cashflow Kantor**: Mengelola laporan keuangan dan uang kas kecil agar operasional harian tidak tersendat.")
                st.write("• **Budgeting Tools**: Mengurus listrik, kuota, akun, hingga stok konsumsi/kebutuhan harian kantor.")
                st.write("• Membantu upload video sesuai kebutuhan kantor.")
                st.write("• Sistem SP dan Bonus ditentukan berdasarkan peforma kinerja (tidak mengikuti sistem otomatis).")
    
    with t2:
        st.write("")
        st.markdown("##### 💵 Kalkulator Simulasi Pendapatan")
        # Ganti selectbox jadi radio horizontal
        posisi = st.radio(
            "Pilih Posisi Kamu:",
            ["Staff Editor", "Uploader & Admin"],
            index=0,
            horizontal=True, # Ini kuncinya biar sejajar ke samping
            key="pilih_posisi_simulasi_v2"
        )
        
        if posisi == "Staff Editor":
            # --- CARD 1: SLIDER EDITOR ---
            with st.container(border=True):
                st.markdown("🎯 **SET TARGET PRODUKSI HARIAN**")
                t_hari = st.select_slider(
                    "Geser untuk simulasi pendapatan harian kamu:",
                    options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                    value=3,
                    key="slider_editor_final"
                )
                st.caption("KETENTUAN: Project HQ: 1 video = 1 | Project Ringan: 15 video = 1 | Tunjangan Kinerja Target Bulanan 70 Video Finish => Rp. 500.000")
                
            # --- LOGIKA HITUNG EDITOR ---
            gapok_sim = 2000000
            hari_kerja = 25
            if t_hari >= 5:
                b_absen, b_video, p_sp = 750000, (t_hari - 4) * 30000 * hari_kerja, 0
                st_txt, d_st, d_col = "SANGAT BAIK", "🌟 Full Bonus", "normal"
            elif t_hari >= 3:
                b_absen, b_video, p_sp = 750000, 0, 0
                st_txt, d_st, d_col = "STANDAR", "✅ Bonus Absen", "normal"
            elif t_hari == 2:
                b_absen, b_video, p_sp = 0, 0, 0
                st_txt, d_st, d_col = "CUKUP", "🛡️ Aman SP", "normal"
            else:
                b_absen, b_video, p_sp = 0, 0, 1000000
                st_txt, d_st, d_col = "LEMAH", "🚨 Risiko SP", "inverse"

            total_gaji = (gapok_sim + b_absen + b_video) - p_sp
            
            # --- CARD 2: DASHBOARD METRIC EDITOR ---
            with st.container(border=True):
                st.markdown("💰 **ESTIMASI PENDAPATAN BULANAN**")
                st.write("")
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("STATUS", st_txt, delta=d_st, delta_color=d_col)
                with c2: st.metric("ESTIMASI TERIMA", f"Rp {total_gaji:,}", delta=f"Rp {total_gaji-gapok_sim:,}", delta_color="inverse" if (total_gaji-gapok_sim) < 0 else "normal")
                with c3: st.metric("TOTAL BONUS", f"Rp {b_absen + b_video:,}", delta=f"Rp {(b_absen+b_video)//25:,}/hr" if t_hari >=3 else "Rp 0")

            # --- CARD 3: INFO SISTEM (KHUSUS EDITOR) ---
            st.write("")
            with st.container(border=True):
                if t_hari >= 5:
                    st.success(f"🔥 **ELITE EDITOR:** Kamu konsisten menyetor {t_hari} video kualitas **ACC** setiap hari!")
                elif t_hari >= 3:
                    st.info("💡 **CATATAN:** Bonus Absen cair karena video mencapai standar minimal kualitas **ACC**.")
                elif t_hari == 2:
                    st.warning("🧐 **REVIEW:** Performa cukup, pastikan video berikutnya tetap berstatus **FINISH** agar aman.")
                else:
                    st.error(f"🚨 **SP ALERT:** Setoran di bawah standar (Hanya {t_hari} video ACC) memicu denda Rp 1.000.000!")

        else:
            # --- TAMPILAN UNTUK UPLOADER & ADMIN ---
            with st.container(border=True):
                st.markdown("🏢 **INFORMASI PENDAPATAN ADMIN / UPLOADER**")
                st.write("")
                c1, c2, c3 = st.columns(3) # Tambah kolom ketiga buat Tunjangan
                with c1: 
                    st.metric("STATUS", "AKTIF", delta="🛡️ Fixed Salary")
                with c2: 
                    st.metric("ESTIMASI TERIMA", "Rp 1,500,000", delta="Gaji Pokok")
                with c3: 
                    st.metric("TUNJANGAN", "TERSEDIA", delta="✨ Tunjangan Kerja") # Tanpa nominal
                
                st.write("")
                st.success("✅ **STATUS TUNJANGAN:** Tunjangan kerja diberikan secara selektif berdasarkan **Efektivitas** dalam mendukung operasional Tim.")

        st.caption("PENTING: Seluruh informasi gaji bersifat transparan untuk menjaga profesionalitas tim Pintar Media.")
        
    with t3:
        st.write("")
        st.markdown("### ⚠️ Sistem Peringatan & Performa (SP)")
        st.caption("Sistem ini bertujuan untuk menjaga produktivitas tim agar tetap stabil dan adil untuk semua.")

        # --- CARD 1: MASA PROTEKSI & HARI KURANG PRODUKTIF ---
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.info("🛡️ **MASA PROTEKSI**")
                st.write("Sistem SP otomatis OFF jika Staff izin (sakit/agenda lain), kendala teknis kantor dan hari libur")
            with col2:
                st.warning("📉 **HARI LEMAH (KURANG PRODUKTIF)**")
                st.write("Jika dalam satu hari hanya menyelesaikan **1 video**, hari tersebut dicatat sebagai 'Hari Lemah'.")

        st.write("")

        # --- CARD 2: AKUMULASI SP & POTONGAN ---
        with st.container(border=True):
            st.markdown("⚖️ **AKUMULASI SANKSI BULANAN**")
            st.write("Sanksi diberikan berdasarkan jumlah total 'Hari Lemah' dalam satu bulan:")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.error("**SP 1 (7 Hari)**")
                st.write("- Akumulasi 7 hari kurang produktif.")
                st.write("- **Potongan: Rp 300.000**")
            with c2:
                st.error("**SP 2 (14 Hari)**")
                st.write("- Akumulasi 14 hari kurang produktif.")
                st.write("- **Potongan: Rp 700.000**")
            with c3:
                st.error("**SP 3 (21 Hari)**")
                st.write("- Akumulasi 21 hari kurang produktif.")
                st.write("- **Potongan: Rp 1.000.000 + Pemutusan Kerja**")

        st.write("")

        # --- CARD 3: TIPS & NOTIFIKASI ---
        with st.container(border=True):
            st.success("💡 **TIPS AGAR PENGHASILAN MAKSIMAL**")
            st.write("- Setor minimal **3 video** setiap hari untuk mengaktifkan semua **Bonus Absensi**.")
            st.write("- Jika hanya menyelesaikan **2 video**, status Anda **Aman**, namun Bonus Kehadiran & Lembur tidak cair.")
            st.write("- CATATAN KHUSUS: Staff Uploader dan Admin, sistem SP berdasarkan peforma kinerja harian.")

    with t4:
        st.write("")
        # --- DATA DINAMIS ---
        import pytz
        import datetime as dt # Tetap pakai as dt
        
        tz_wib = pytz.timezone('Asia/Jakarta')
        
        # PERBAIKAN DI SINI:
        # Panggil dt (nama aliasnya), lalu .datetime (kelasnya), lalu .now()
        now = dt.datetime.now(tz_wib) 
        
        tgl_hari_ini = now.strftime("%d %B %Y")
        nomor_ahu = "AHU-011181.AH.01.31.Tahun 2025"
        nama_direktur = "Dian Setya Wardana"
        last_update = "5 Maret 2026 | 12:10 WIB"

        # --- EXPANDER UTAMA ---
        with st.expander("🤝 Budaya Kerja & Peraturan", expanded=False):

            # --- KONSTRUKSI HTML (A4 PRINT READY + FULL TEKS) ---
            html_master_pdf = f"""
            <style>
                @media print {{
                    @page {{ size: A4; margin: 15mm; }}
                    body {{ margin: 0; padding: 0; }}
                    .a4-container {{ border: none !important; box-shadow: none !important; width: 100% !important; margin: 0 !important; padding: 0 !important; }}
                }}
                .a4-container {{
                    background: white; 
                    width: 210mm; 
                    min-height: 297mm;
                    padding: 20mm; 
                    margin: auto; 
                    font-family: 'Arial', sans-serif; 
                    color: black; 
                    line-height: 1.6; 
                    border: 1px solid #eee;
                    box-sizing: border-box;
                }}
            </style>
            <div class="a4-container">
            <table style="width: 100%; border-bottom: 3px solid #000; padding-bottom: 15px; margin-bottom: 30px;">
                <tr>
                    <td style="width: 30%; vertical-align: middle;">
                        <img src="https://raw.githubusercontent.com/pintarkantor-prog/pintarmedia/main/PINTAR.png" style="width: 180px; height: auto;">
                    </td>
                    <td style="width: 70%; text-align: right; vertical-align: middle;">
                        <h1 style="margin: 0; font-size: 22px; font-weight: bold; text-transform: uppercase;">PT Pintar Digital Kreasi</h1>
                        <p style="margin: 0; font-size: 12px; color: #333;">Creative Content & Digital Media Production</p>
                        <p style="margin: 0; font-size: 10px; color: #666;">SK KEMENKUMHAM: {nomor_ahu}</p>
                    </td>
                </tr>
            </table>
                
                <center>
                    <h2 style="margin: 0; font-size: 16px; font-weight: bold; text-decoration: underline; letter-spacing: 1px;">PERATURAN KERJA</h2>
                    <p style="margin: 5px 0 0 0; font-size: 10px; color: #888;">NOMOR: PDK/REG-SOP/{now.strftime('%y%m')}/OWNER</p>
                </center>
                
                <br><br>

                <div style="font-size: 13px; text-align: justify;">
                    <p style="font-weight: bold; margin-bottom: 10px;">I. KETENTUAN WAKTU KERJA & DISIPLIN</p>
                    <p style="margin-left: 20px;">
                    <b>Jam Operasional:</b> Senin – Sabtu: pukul 08:00 s/d 16:00 WIB.<br>
                    <b>Waktu Istirahat:</b><br>
                    Senin – Sabtu: 11:30 – 12:30 WIB.<br>
                    Kecuali Jumat: 11:30 – 13:00 WIB (Penyesuaian waktu ibadah dan rehat mingguan).<br>
                    <b>Hari Libur:</b> Operasional kantor diliburkan pada hari Minggu dan Hari Libur Nasional. Adapun untuk Hari Cuti Bersama, operasional tetap berjalan normal kecuali ditentukan lain oleh kebijakan owner.<br>
                    <b>Presensi:</b> Sistem absen tercatat otomatis melalui sistem login dashboard web PINTAR MEDIA.
                    </p>

                    <p style="font-weight: bold; margin-top: 30px; margin-bottom: 10px;">II. SISTEM PENGGAJIAN & APRESIASI KINERJA</p>
                    <p style="margin-left: 20px;">
                    <b>Periode Pembayaran:</b> Hak upah, tunjangan, dan bonus akan disalurkan pada tanggal 2 s/d 5 setiap bulannya.<br>
                    <b>Struktur Upah:</b> Terdiri dari Gaji Pokok, Tunjangan Kinerja, Bonus Absensi dan Bonus Performa yang dihitung berdasarkan Video HQ (High Quality) yang berhasil diproduksi.<br>
                    </p>

                    <p style="font-weight: bold; margin-top: 30px; margin-bottom: 10px;">III. STANDAR OPERASIONAL PRODUKSI (SOP) KONTEN</p>
                    <p style="margin-left: 20px;">
                    <b>SOP kerja berdasarkan posisi masing masing bisa dilihat dihalaman Area Staff<br>
                    </p>

                    <p style="font-weight: bold; margin-top: 30px; margin-bottom: 10px;">IV. PENGGUNAAN ALAT KERJA & SMARTPHONE</p>
                    <p style="margin-left: 20px;">
                    <b>Smartphone Flexible-Policy:</b> Perusahaan memahami kebutuhan riset digital. Penggunaan smartphone diperbolehkan terbatas untuk:<br>
                    - Mencari referensi video/audio/musik yang sedang tren.<br>
                    - Riset tren visual dan ide cerita pada platform media sosial.<br>
                    - Koordinasi internal grup kantor.<br>
                    <b>Batasan Etika:</b> Staff berkewajiban membatasi penggunaan smartphone untuk aktivitas hiburan pribadi (seperti bermain game atau streaming non-pekerjaan atau wa personal) yang dapat mengganggu produktivitas dan ritme kerja tim.
                    </p>

                    <p style="font-weight: bold; margin-top: 30px; margin-bottom: 10px;">V. TANGGUNG JAWAB ASSET & KERAHASIAAN DATA</p>
                    <p style="margin-left: 20px;">
                    <b>Integritas Akun AI:</b> Staff diberikan amanah penuh dalam penggunaan akun premium. Dilarang keras mengubah informasi akun (password/email) atau membagikan akses kepada pihak ketiga tanpa izin.<br>
                    <b>Efisiensi Resource:</b> Staff wajib menggunakan kuota produksi (render credit) secara bijak dan terukur guna menghindari pemborosan aset digital.<br>
                    </p>

                    <p style="font-weight: bold; margin-top: 30px; margin-bottom: 10px;">VI. KOMITMEN PROFESIONALISME & EVALUASI</p>
                    <p style="margin-left: 20px;">
                    Guna menjaga keadilan dan stabilitas operasional, perusahaan menetapkan evaluasi sebagai berikut:<br><br>
                    <b>Status Hari Lemah Staff Editor:</b> Pencapaian output harian yang hanya berjumlah 1 video ACC tanpa adanya kendala teknis/darurat yang sah, dikategorikan sebagai "Hari Lemah".<br>
                    <b>Status Hari Lemah Staff Uploader/Admin:</b> Membuat produktifitas terganggu karena kelalaian, tidak sesuai SOP yang ditetapkan, dikategorikan sebagai "Hari Lemah".<br>
                    <b>Penyesuaian Administratif:</b> Atas ketidaktercapaian standar minimum kerja (Hari Lemah), pelanggaran SOP Alur secara sengaja, atau ketidakhadiran tanpa keterangan (Ghosting), akan dilakukan penyesuaian administratif yang akan diperhitungkan dalam evaluasi gaji/bonus bulanan.
                    </p>
                </div>

                <br><br><br>

                <table style="width: 100%; text-align: center; font-size: 13px;">
                    <tr>
                        <td style="width: 50%;"></td>
                        <td style="width: 50%;">
                            <p>Banyumas, {tgl_hari_ini}<br><b>PIHAK PERTAMA (OWNER)</b></p>
                            <br><br>
                            <p style="color:blue; font-weight:bold; font-size: 10px;">[ OWNER SIGNED & VERIFIED ]</p>
                            <p style="border-bottom: 1px solid #000; display: inline-block; min-width: 200px; font-weight: bold;">{nama_direktur}</p>
                        </td>
                    </tr>
                </table>

                <div style="border-top: 1px solid #ddd; padding-top: 10px; margin-top: 60px; font-size: 9px; color: #888; text-align: justify;">
                    <i><b>Pintar Media System:</b> Update: {last_update}. Dokumen ini sah dan berlaku secara otomatis.</i>
                </div>
            </div>
            """
            
            # Pratinjau Dokumen
            st.components.v1.html(html_master_pdf, height=1000, scrolling=True)

            # Tombol Print
            if st.button(f"📄 DOWNLOAD / PRINT PDF PERATURAN", use_container_width=True):
                html_with_print = html_master_pdf + "<script>window.print();</script>"
                st.components.v1.html(html_with_print, height=0)

    with t5:
        st.write("") 
        
        # --- KONEKSI DATA USER ---
        user_login = st.session_state.get('user_aktif', 'tamu').lower()
        
        # LOGIKA PENANGKAP LEVEL (Disesuaikan dengan kolom 'Level' di tabel Staff lo)
        # Kita ambil dari session state, kalau gagal kita tembak langsung ke Supabase
        level_aktif = st.session_state.get('Level', st.session_state.get('level', st.session_state.get('status', 'STAFF'))).upper()
        
        if level_aktif == "STAFF":
            try:
                # Sesuaikan dengan nama tabel lo 'Staff' (S besar) dan kolom 'Level' (L besar)
                res_level = supabase.table("Staff").select("Level").eq("Nama", user_login.upper()).execute()
                if res_level.data:
                    level_aktif = res_level.data[0]['Level'].upper()
            except:
                pass

        # --- 1. DEFINISI IDENTITAS DASAR ---
        staff_mapping = {
            "nissa": "Nisaul Mukaromah Alfiyaeni",
            "lisa": "Salisatu Rohmatus Saodah",
            "icha": "Nissa Pangestuningrum",
            "inggi": "Rizki Retno Inggiani",
            "dian": "Dian Setya Wardana"
        }
        
        # Ambil Nama Staf
        staf_nama = staff_mapping.get(user_login, user_login.upper())
        nama_direktur = "Dian Setya Wardana"
        nomor_ahu = "AHU-011181.AH.01.31.Tahun 2025"
        last_update = "5 Maret 2026 | 12:11 WIB"

        # --- 2. AMBIL GAJI DARI SUPABASE (SETELAH IDENTITAS SIAP) ---
        gaji_pokok_staf = "0"
        try:
            res_staff = supabase.table("Staff").select("Gaji_Pokok").ilike("Nama", f"%{user_login}%").execute()
            if res_staff.data:
                val_gapok = res_staff.data[0].get('Gaji_Pokok', 0)
                # Format ke ribuan
                gaji_pokok_staf = "{:,}".format(int(val_gapok)).replace(",", ".")
        except:
            pass # Biar gak ngerusak dashboard kalau Supabase lagi ngadat
        
        # --- FIX DATETIME (Solusi UnboundLocalError) ---
        import pytz
        import datetime as dt 
        import time
        
        tz_jakarta = pytz.timezone('Asia/Jakarta')
        now_fix = dt.datetime.now(tz_jakarta) 
        bulan_sekarang = now_fix.strftime("%m-%Y")

        # --- KHUSUS TAMPILAN OWNER / ADMIN ---
        if level_aktif in ["OWNER", "ADMIN"]:
            with st.expander("📊 Rekap Tanda Tangan Staff", expanded=False):
                # 1. Ambil data dari Supabase (Cek periode Maret)
                # Pakai try-except biar kalau tabel kosong nggak langsung error njir
                try:
                    all_signs_raw = supabase.table("kontrak_staff").select("username, waktu_presisi").eq("periode", bulan_sekarang).execute()
                    
                    # Mapping data jam sign (Ambil username sebagai key)
                    sign_map = {row['username'].lower(): row.get('waktu_presisi', '--:--:--') for row in all_signs_raw.data}
                    signed_users = list(sign_map.keys())
                except:
                    sign_map = {}
                    signed_users = []
                
                daftar_staff_monitor = ["nissa", "lisa", "icha", "inggi"]
                
                st.write("")
                kolom_card = st.columns(4)
                
                for idx, s in enumerate(daftar_staff_monitor):
                    is_ok = s in signed_users
                    # Sesuai Radar Performa lo: Hijau (#1d976c) vs Merah (#e74c3c)
                    warna_bg = "#1d976c" if is_ok else "#e74c3c" 
                    n_up = s.upper()
                    txt_status = "SUDAH" if is_ok else "BELUM"
                    jam_sign = sign_map.get(s, "--:--:--")
                    
                    with kolom_card[idx % 4]:
                        with st.container(border=True):
                            # Header Header ala Radar Performa (Negative Margin Magic Lo)
                            st.markdown(f'<div style="text-align:center; padding:5px; background:{warna_bg}; border-radius:8px 8px 0 0; margin:-15px -15px 10px -15px;"><b style="color:black; font-size:14px; letter-spacing:1px;">{n_up}</b></div>', unsafe_allow_html=True)
                            
                            m1, m2 = st.columns(2)
                            m1.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>STATUS</p><b style='font-size:11px; color:{warna_bg};'>{txt_status} SIGN</b>", unsafe_allow_html=True)
                            m2.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>PERIODE</p><b style='font-size:11px;'>{bulan_sekarang}</b>", unsafe_allow_html=True)
                            
                            st.divider()
                            
                            det1, det2 = st.columns(2)
                            # Bagian Jam Sign & Tipe Dokumen
                            det1.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>⏰ JAM SIGN</p><b style='font-size:11px;'>{jam_sign}</b>", unsafe_allow_html=True)
                            det2.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>📝 DOKUMEN</p><b style='font-size:11px;'>KONTRAK</b>", unsafe_allow_html=True)
                            
                            # Progress Bar (Penuh kalo beres)
                            st.progress(1.0 if is_ok else 0.0)

                # 3. Tombol BOM WA (Otomatis Filter Nama)
                belum_sign = [s.upper() for s in daftar_staff_monitor if s not in signed_users]
                if belum_sign:
                    st.write("")
                    if st.button(f"📢 KIRIM WA MASSAL ({len(belum_sign)} STAFF BELUM)", use_container_width=True, type="primary"):
                        tag_nama = ", ".join(belum_sign)
                        pesan_grup = f"📢 *PENGUMUMAN*\n\nMohon perhatian: *{tag_nama}*\nSegera sign kontrak periode *{bulan_sekarang}*."
                        kirim_notif_wa(pesan_grup)
                        st.toast("Notif dikirim!")
                else:
                    st.success("Semua Beres! Gak perlu BOM WA lagi Dian! ✨")
            st.write("---")
        # --- LOGIKA KUNCI TANGGAL ---
        check_db = supabase.table("kontrak_staff").select("*").eq("username", user_login).eq("periode", bulan_sekarang).execute()
        
        if check_db.data:
            is_signed = True
            tgl_hari_ini = check_db.data[0]['tgl_tanda_tangan']
            waktu_presisi = check_db.data[0]['waktu_presisi']
        else:
            is_signed = False
            tgl_hari_ini = now_fix.strftime("%d %B %Y")
            waktu_presisi = now_fix.strftime("%H:%M:%S")
        # --- KONSTRUKSI HTML (A4 PRINT READY + FULL TEXT NO CUT) ---
        html_kontrak_full = f"""
        <style>
            @media print {{
                @page {{ size: A4; margin: 15mm; }}
                body {{ margin: 0; padding: 0; }}
                .a4-container {{ border: none !important; box-shadow: none !important; width: 100% !important; margin: 0 !important; padding: 0 !important; }}
            }}
            .a4-container {{
                background: white; 
                width: 210mm; 
                padding: 20mm; 
                margin: auto; 
                font-family: Arial, sans-serif; 
                color: black; 
                line-height: 1.6; 
                border: 1px solid #eee;
                box-sizing: border-box;
            }}
        </style>
        <div class="a4-container">
            <table style="width: 100%; border-bottom: 3px solid #000; padding-bottom: 15px; margin-bottom: 30px;">
                <tr>
                    <td style="width: 30%; vertical-align: middle;">
                        <img src="https://raw.githubusercontent.com/pintarkantor-prog/pintarmedia/main/PINTAR.png" style="width: 180px; height: auto;">
                    </td>
                    <td style="width: 70%; text-align: right; vertical-align: middle;">
                        <h1 style="margin: 0; font-size: 22px; font-weight: bold; text-transform: uppercase;">PT Pintar Digital Kreasi</h1>
                        <p style="margin: 0; font-size: 12px; color: #333;">Creative Content & Digital Media Production</p>
                        <p style="margin: 0; font-size: 10px; color: #666;">SK KEMENKUMHAM: {nomor_ahu}</p>
                    </td>
                </tr>
            </table>
            
            <center>
                <h2 style="margin: 0; font-size: 16px; font-weight: bold; text-decoration: underline; letter-spacing: 1px;">PERJANJIAN KERJA PARUH WAKTU</h2>
                <p style="margin: 5px 0 0 0; font-size: 10px; color: #888;">NOMOR: PDK/HRD-SPK/{now.strftime('%y%m')}/{user_login.upper()}</p>
            </center>
            
            <div style="font-size: 13px; text-align: justify; margin-top: 25px;">
                <p>Perjanjian ini dibuat secara sah oleh dan antara <b>{nama_direktur}</b> (Pihak Pertama) dan <b>{staf_nama}</b> (Pihak Kedua) tertanggal <b>{tgl_hari_ini}</b> dengan rincian sebagai berikut:</p>

                <p style="font-weight: bold; margin-top: 25px; margin-bottom: 5px;">BAB I: KEDISIPLINAN & OPERASIONAL</p>
                <p style="font-weight: bold; margin-bottom: 5px;">Pasal 1: Waktu Kerja, Hari Kerja, & Hak Libur</p>
                <div style="margin-left: 20px;">
                    <b>Waktu Kerja Efektif:</b> Pukul 08:00 s/d 16:00 WIB.<br>
                    <b>Hari Kerja:</b> Senin s/d Sabtu.<br>
                    <b>Waktu Istirahat:</b><br>
                    - Senin – Sabtu: 11:30 – 12:30 WIB.<br>
                    - Kecuali Jumat: 11:30 – 13:00 WIB (Penyesuaian ibadah).<br>
                    <b>Hari Libur:</b> Hari Minggu dan Hari Libur Nasional.<br>
                    <b>Cuti Bersama:</b> Operasional kantor tetap berjalan normal pada hari Cuti Bersama Pemerintah, kecuali ditentukan lain oleh Kebijakan Pimpinan (Pihak Pertama).<br>
                    <b>Hak Cuti Pribadi:</b> Pihak Kedua berhak mengajukan izin/cuti dengan pemberitahuan minimal 2 hari sebelumnya. Izin mendadak hanya diterima untuk kondisi darurat (Sakit/Duka) dengan bukti yang sah.<br>
                    <b>Presensi:</b> Pihak Kedua wajib login disistem untuk Absensi. Keterlambatan tanpa alasan logis akan diakumulasi sebagai "Hari Lemah".
                </div>

                <p style="font-weight: bold; margin-top: 25px; margin-bottom: 5px;">BAB II: KEAMANAN ASET & KERAHASIAAN DATA (NDA)</p>
                <p style="font-weight: bold; margin-bottom: 5px;">Pasal 2: Perlindungan & Efisiensi Akun AI Premium</p>
                <div style="margin-left: 20px;">
                    <b>Hak Akses:</b> Pihak Kedua diberikan akses akun AI premium (Generator, Email, Grok, Gemini, etc) semata-mata untuk Kepentingan Pekerjaan PT Pintar Digital Kreasi.<br>
                    <b>Larangan Penyalahgunaan:</b> Dilarang keras menggunakan akun milik perusahaan untuk keperluan pribadi, proyek sampingan di luar perusahaan, atau membagikan akses kepada pihak ketiga.<br>
                    <b>Efisiensi Resource:</b> Pihak Kedua wajib menggunakan kuota produksi (render credit/token) secara bijak dan efisien. Pemborosan resource tanpa hasil output yang jelas dianggap sebagai kelalaian kerja.<br>
                    <b>Keamanan Akun:</b> Pihak Kedua dilarang mengubah informasi profil, email pemulihan, atau password tanpa instruksi langsung dari Pihak Pertama.
                </div>

                <p style="font-weight: bold; margin-top: 25px; margin-bottom: 5px;">BAB III: EVALUASI & SANKSI FINANSIAL</p>
                <p style="font-weight: bold; margin-bottom: 5px;">Pasal 3: Penyesuaian Administratif (Denda)</p>
                <div style="margin-left: 20px;">
                    <b>Pelanggaran SOP & Target:</b> Pihak Kedua sepakat bahwa kegagalan memenuhi standar produksi atau mencapai target harian minimum (Status Hari Lemah) adalah pelanggaran kontrak.<br>
                    <b>Nilai Penalti:</b> Atas pelanggaran tersebut, Pihak Kedua bersedia menerima penyesuaian administratif (potongan gaji) sebesar maksimal <b>Rp 1.000.000 (Satu Juta Rupiah)</b> per periode bulan berjalan.<br>
                    <b>Ghosting:</b> Tindakan tidak memberikan kabar (Ghosting) selama >3 hari kerja dianggap sebagai pengunduran diri sepihak dan Pihak Pertama berhak menahan hak upah yang belum terbayar sebagai kompensasi kerugian operasional.
                </div>

                <p style="font-weight: bold; margin-top: 25px; margin-bottom: 5px;">BAB IV: KOMPENSASI, PAJAK, & PERLINDUNGAN KESEHATAN</p>
                <p style="font-weight: bold; margin-bottom: 5px;">Pasal 4: Hak Upah & Bonus</p>
                <div style="margin-left: 20px;">
                    1. <b>Base Salary:</b> Pihak Kedua berhak menerima upah pokok sebesar <b>Rp {gaji_pokok_staf}</b> per periode bulan berjalan.* <br>
                    2. <b>Bonus Performa:</b> Dihitung berdasarkan data validasi sistem (ACC Video dan atau Absensi).<br>
                    3. <b>Bonus Kinerja:</b> Dihitung berdasarkan produktivitas dan performa kerja.<br>
                    4. <b>Waktu Pembayaran:</b> Gaji dibayarkan pada tanggal 2 s/d 5 setiap bulannya melalui transfer bank/e-wallet.
                </div>
                <p style="font-size: 10px; color: #666; font-style: italic; margin-left: 20px; margin-top: 5px;">
                    *Upah pokok dan bonus kinerja dapat disesuaikan secara proporsional berdasarkan jumlah kehadiran dan produktivitas Pihak Kedua.
                </p>
                <p style="font-weight: bold; margin-top: 10px; margin-bottom: 5px;">Pasal 5: Pajak Penghasilan (PPh)</p>
                <div style="margin-left: 20px;">
                    Segala bentuk Pajak Penghasilan (PPh) yang timbul atas upah dan bonus yang diterima oleh Pihak Kedua adalah Tanggung Jawab Pribadi Pihak Kedua.<br>
                    Pihak Pertama membayarkan upah secara gross (kotor) tanpa potongan pajak dari perusahaan.
                </div>
                <p style="font-weight: bold; margin-top: 10px; margin-bottom: 5px;">Pasal 6: Perlindungan Asuransi & Kesehatan</p>
                <div style="margin-left: 20px;">
                    Mengingat status kemitraan ini adalah paruh waktu (part-time), Pihak Pertama tidak memberikan fasilitas asuransi kesehatan atau jaminan hari tua (BPJS/Asuransi Swasta).<br>
                    Segala biaya medis atau perlindungan kesehatan merupakan Tanggung Jawab Pribadi Pihak Kedua. Pihak Kedua disarankan memiliki proteksi kesehatan mandiri.
                </div>
                <p style="font-weight: bold; margin-top: 25px; margin-bottom: 5px;">BAB V: LEGALITAS & DINAMIKA PERATURAN</p>
                <p style="font-weight: bold; margin-top: 10px; margin-bottom: 5px;">Pasal 7: Sifat Kemitraan & Pembatalan Sewaktu-waktu</p>
                <div style="margin-left: 20px;">
                    Perjanjian ini bersifat paruh waktu (Project-Based) yang diperbarui setiap bulan.<br>
                    Pihak Pertama berhak menghentikan perjanjian ini secara sepihak sewaktu-waktu apabila project ditiadakan, terjadi penurunan skala operasional, atau performa Pihak Kedua tidak memenuhi standar.<br>
                    Jika terjadi penghentian di tengah periode, Pihak Pertama hanya berkewajiban membayar upah proporsional sesuai jumlah video yang telah disetujui (ACC) hingga tanggal penghentian.<br>
                    Pihak Kedua memahami tidak ada hak atas pesangon atau ganti rugi atas berakhirnya kemitraan ini.
                </div>
                <p style="font-weight: bold; margin-bottom: 5px;">Pasal 8: Perubahan Peraturan (Amandemen)</p>
                <div style="margin-left: 20px;">
                    Pihak Pertama berhak melakukan perubahan, penambahan, atau pengurangan poin-poin dalam Pasal Perjanjian ini, dengan memperhatikan/atau diskusi internal tim.<br>
                    Setiap perubahan akan diinformasikan melalui sistem Dashboard Pintar Media dengan keterangan "Update Terakhir".<br>
                    Pihak Kedua dinyatakan setuju dengan perubahan tersebut selama masih melanjutkan hubungan kerja di periode bulan berikutnya.
                </div>
                <p style="font-weight: bold; margin-top: 10px; margin-bottom: 5px;">Pasal 9: Validitas Digital Signature</p>
                <div style="margin-left: 20px;">
                    Tindakan menekan tombol "SETUJU & TANDATANGANI" adalah sah sebagai pengganti tanda tangan basah demi hukum.<br>
                    Sistem merekam secara otomatis: Nama Staff Resmi dan Timestamp (Waktu Presisi) sebagai bukti otentik pengesahan.<br>
                </div>
            </div>

            <div style="page-break-inside: avoid; break-inside: avoid; margin-top: 50px;">
                <table style="width: 100%; text-align: center; font-size: 13px; border-collapse: collapse;">
                    <tr>
                        <td style="width: 50%; vertical-align: bottom; padding-bottom: 20px;">
                            PIHAK KEDUA,
                        </td>
                        <td style="width: 50%; vertical-align: bottom; padding-bottom: 20px;">
                            Banyumas, {tgl_hari_ini}<br>
                            PIHAK PERTAMA,
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="height: 80px; vertical-align: middle;">
                            <span style="color:green; font-weight:bold; font-size: 11px;">
                                {"[ E-SIGNED VERIFIED: " + waktu_presisi + " ]" if is_signed else "(BELUM TANDA TANGAN)"}
                            </span>
                        </td>
                        <td style="height: 80px; vertical-align: middle;">
                            <span style="color:blue; font-weight:bold; font-size: 11px;">[ OWNER SIGNED & VERIFIED ]</span>
                        </td>
                    </tr>

                    <tr>
                        <td style="vertical-align: top;">
                            <b>{staf_nama}</b>
                        </td>
                        <td style="vertical-align: top;">
                            <b>{nama_direktur}</b>
                        </td>
                    </tr>
                </table>
            </div>

            <div style="border-top: 1px solid #ddd; padding-top: 10px; margin-top: 40px; font-size: 9px; color: #888; text-align: justify;">
                <i><b>Pintar Media System:</b> Update: {last_update}. Dokumen ini sah dan berlaku secara otomatis.</i>
            </div>
        </div>
        """

        # --- LOGIKA TAMPILAN DASHBOARD ---
        st.subheader("📝 Pengesahan Kontrak Digital")
        
        if user_login == "dian":
            st.success("👑 **STATUS OWNER**: Otoritas Kontrak Otomatis.")
            if st.button("🔍 PREVIEW / PRINT MASTER KONTRAK", use_container_width=True):
                st.components.v1.html(html_kontrak_full + "<script>window.print();</script>", height=0)
        
        elif not is_signed:
            st.info(f"Halo {staf_nama}, silakan klik tombol di bawah untuk meninjau Kontrak Kerja periode {bulan_sekarang}.")
            
            if st.button("🔍 PREVIEW KONTRAK (LIAT PDF)", use_container_width=True):
                st.session_state[f"preview_done_{user_login}"] = True
                st.components.v1.html(html_kontrak_full + "<script>window.print();</script>", height=0)
            
            if st.session_state.get(f"preview_done_{user_login}", False):
                st.write("---")
                setuju_kontrak = st.checkbox(f"Saya, {staf_nama}, menyatakan SETUJU & TUNDUK pada seluruh pasal perjanjian di atas.")
                
                if setuju_kontrak:
                    if st.button("✅ SAHKAN & TANDATANGANI", use_container_width=True):
                        # 1. SIMPAN KE DATABASE (Agar tanggal tgl_hari_ini & waktu_presisi jadi PERMANEN)
                        data_kontrak = {
                            "username": user_login,
                            "nama_staff": staf_nama,
                            "periode": bulan_sekarang,
                            "tgl_tanda_tangan": tgl_hari_ini,
                            "waktu_presisi": waktu_presisi
                        }
                        # Pastikan lo sudah membuat tabel 'kontrak_staff' di Supabase
                        supabase.table("kontrak_staff").insert(data_kontrak).execute()

                        # 2. UPDATE SESSION STATE
                        st.session_state[f"signed_{user_login}_{bulan_sekarang}"] = True
                        
                        # 3. NOTIFIKASI WA & LOG AKTIVITAS
                        kirim_notif_wa(f"✅ *KONTRAK DISAHKAN*\n👤 *Staff:* {staf_nama}\n📅 *Tgl:* {tgl_hari_ini}\n⏰ *Waktu:* {waktu_presisi} WIB")
                        tambah_log(st.session_state.user_aktif, f"SIGN KONTRAK: {bulan_sekarang}")
                        
                        st.success("Kontrak Berhasil Disahkan!"); time.sleep(1); st.rerun()
                else:
                    st.button("✅ SAHKAN & TANDATANGANI", disabled=True, use_container_width=True)
        else:
            # Mengubah format 03-2026 (periode) menjadi nama bulan yang rapi
            import datetime
            obj_bulan = datetime.datetime.strptime(bulan_sekarang, "%m-%Y")
            nama_bulan_fix = obj_bulan.strftime("%B %Y")
            
            st.success(f"🔒 Kontrak periode {nama_bulan_fix} sudah ditandatangani sah.")
            if st.button("📄 DOWNLOAD SALINAN KONTRAK (PDF)", use_container_width=True):
                st.components.v1.html(html_kontrak_full + "<script>window.print();</script>", height=0)

def tampilkan_database_channel():
    st.title("📱 DATABASE CHANNEL")

    # --- 1. SETUP AKSES (WAJIB ADA DI SINI) ---
    level_aktif = st.session_state.get("user_level", "STAFF")
    user_aktif = st.session_state.get("user_aktif", "User").upper()
    
    # Perbaikan NameError
    is_pro = level_aktif in ["OWNER", "ADMIN", "UPLOADER"]
    is_boss = level_aktif in ["OWNER", "ADMIN"]
    is_ceo = level_aktif in ["OWNER"]

    # --- 2. PENARIKAN DATA (Ditarik saat menu dibuka) ---
    with st.spinner("Sinkronisasi Radar..."):
        df = load_data_channel()
        df_hp = load_data_hp()

    # --- 3. PEMBUATAN TAB ---
    tab_standby, tab_proses, tab_jadwal, tab_hp, tab_sold, tab_arsip = st.tabs([
        "📦 STOK STANDBY", "🚀 CHANNEL PROSES", "📅 JADWAL UPLOAD", 
        "📱 MONITOR HP", "💰 SOLD CHANNEL", "📂 ARSIP CHANNEL"
    ])
    
    # ==============================================================================
    # TAB 1: STOK STANDBY (GAYA RADAR UI - ULTIMATE WIB & SYNC)
    # ==============================================================================
    with tab_standby:
        if not is_pro:
            st.warning("🔒 Akses Terbatas.")
        else:
            # --- 1. LOGIKA HITUNG DATA (Real-time) ---
            total_st = len(df[df['STATUS'] == 'STANDBY'])
            total_pr = len(df[df['STATUS'] == 'PROSES'])
            hp_aktif = len(df[df['HP'].notna() & (df['HP'].astype(str).str.strip() != "")]['HP'].unique())
            
            # --- LOGIKA STATUS VITAL ---
            selisih_vital = total_st - (total_pr + 15)
            status_stok = f"AMAN (+{selisih_vital})" if selisih_vital >= 0 else f"KRITIS ({selisih_vital})"
            warna_stok = "normal" if selisih_vital >= 0 else "inverse"
            
            # --- LOGIKA SOLD (Bulan Ini) ---
            tz = pytz.timezone('Asia/Jakarta')
            now_indo = datetime.now(tz)
            bln_ini = now_indo.strftime("%m/%Y")
            
            mask_ini = (df['STATUS'] == 'SOLD') & (df.iloc[:, 11].astype(str).str.contains(bln_ini, na=False, case=False))
            sold_ini = len(df[mask_ini])
            
            # HITUNG ARSIP (SUSPEND + BUSUK)
            total_arsip = len(df[df['STATUS'].isin(['SUSPEND', 'BUSUK'])])

            # --- 2. RENDER DASHBOARD UI (BALIK KE GAYA st.write) ---
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1.2, 2.2])
                c1.metric("📦 CH STANDBY", f"{total_st}", delta=status_stok, delta_color=warna_stok)
                c2.metric("🚀 CH PROSES", f"{total_pr}", delta="ON PROCESS")
                c3.metric("📱 UNIT HP", f"{hp_aktif}", delta="LIVE")
                c4.metric("💰 SOLD (BLN)", f"{sold_ini}", delta="Bulan Ini")
                
                # INI YANG LO MAU: Pake gaya st.write di Kolom 5
                with c5:
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    st.write(f"📢 **INFO SISTEM:**")
                    st.write(f"Terdapat **{total_arsip}** akun di arsip (Suspend/Busuk).")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- 3. HEADER DATABASE & TOMBOL TAMBAH ---
            hc1, hc2 = st.columns([3, 1])
            hc1.markdown("#### 🔐 DATABASE STOK STANDBY")
            
            if hc2.button("➕ TAMBAH AKUN", use_container_width=True, type="primary"):
                st.session_state.form_baru = not st.session_state.get('form_baru', False)

            # --- 4. FORM INPUT AKUN BARU (INDENTASI FIXED & CLEAN) ---
            if st.session_state.get('form_baru', False):
                with st.container(border=True):
                    with st.form("input_v6_icon", clear_on_submit=True):
                        f1, f2, f3 = st.columns(3)
                        v_mail = f1.text_input("📧 Email Login")
                        v_pass = f2.text_input("🔑 Password")
                        v_nama = f3.text_input("📺 Nama Channel")
                        
                        f4, f5 = st.columns([1, 2])
                        v_subs = f4.text_input("📊 Jumlah Subs")
                        v_link = f5.text_input("🔗 Link Channel")
                        
                        if st.form_submit_button("🚀 SIMPAN KE DATABASE", use_container_width=True):
                            if v_nama and v_mail:
                                tgl_now = datetime.now(tz).strftime("%d/%m/%Y %H:%M")
                                v_mail = v_mail.strip().lower() 
                                
                                try:
                                    # Pake spinner biar kelihatan lagi kerja
                                    with st.spinner("Mendaftarkan akun..."):
                                        supabase.table("Channel_Pintar").insert({
                                            "TANGGAL": tgl_now, 
                                            "EMAIL": v_mail,
                                            "PASSWORD": v_pass,
                                            "NAMA_CHANNEL": v_nama,
                                            "SUBSCRIBE": v_subs,
                                            "LINK_CHANNEL": v_link,
                                            "STATUS": "STANDBY",
                                            "PENCATAT": user_aktif,
                                            "EDITED": f"New: {user_aktif} ({tgl_now})"
                                        }).execute()
                                    
                                    # Hapus cache biar data langsung muncul di tabel bawah
                                    st.cache_data.clear()
                                    st.success(f"✅ MANTAP! Akun {v_mail} masuk Supabase.")
                                    time.sleep(0.5)
                                    st.rerun()

                                except Exception as e:
                                    if "23505" in str(e):
                                        st.warning(f"⚠️ Email **{v_mail}** sudah terdaftar!")
                                    else:
                                        st.error(f"❌ Masalah: {e}")
                            else:
                                st.error("⚠️ Email dan Nama Channel wajib diisi!")
                                
            # --- 5. GRID EDITOR STANDBY ---
            df_st = df[df['STATUS'] == 'STANDBY'].copy()
            if df_st.empty:
                st.info("Belum ada stok standby.")
            else:
                df_st['NO'] = range(1, len(df_st) + 1)
                df_st['REAL_IDX'] = df_st.index 
                df_st['SUBSCRIBE'] = df_st['SUBSCRIBE'].astype(str)

                config_st = {
                    "NO": st.column_config.TextColumn("#️⃣ NO", width=30, disabled=True),
                    "EMAIL": st.column_config.TextColumn("📧 EMAIL", width=200),
                    "PASSWORD": st.column_config.TextColumn("🔑 PASS", width=130),
                    "NAMA_CHANNEL": st.column_config.TextColumn("📺 CHANNEL", width=130),
                    "SUBSCRIBE": st.column_config.TextColumn("📊 SUBS", width=50), 
                    "LINK_CHANNEL": st.column_config.LinkColumn("🔗 URL", width=300),
                    "PENCATAT": st.column_config.TextColumn("👤 OLEH", width=50, disabled=True),
                    "STATUS": st.column_config.SelectboxColumn("⚙️ STATUS", width=80, options=["STANDBY", "PROSES", "SOLD", "BUSUK", "SUSPEND"]),
                    "REAL_IDX": None 
                }

                edited_st = st.data_editor(
                    df_st[["NO", "EMAIL", "PASSWORD", "NAMA_CHANNEL", "SUBSCRIBE", "LINK_CHANNEL", "PENCATAT", "STATUS", "REAL_IDX"]],
                    column_config=config_st, use_container_width=True, hide_index=True, key="grid_st_pro_locked"
                )

                # --- 6. LOGIKA UPDATE MODERN (BATCH VERSION f/16) ---
                kolom_cek = ["NO", "EMAIL", "PASSWORD", "NAMA_CHANNEL", "SUBSCRIBE", "LINK_CHANNEL", "PENCATAT", "STATUS", "REAL_IDX"]
                if not edited_st.equals(df_st[kolom_cek]):
                    if st.button("💾 KONFIRMASI PERUBAHAN", use_container_width=True, type="primary"):
                        try:
                            with st.spinner("Sinkronisasi Radar ke Supabase..."):
                                tgl_now = datetime.now(tz).strftime("%d/%m/%Y %H:%M")
                                
                                # 1. SIAPIN KERANJANG (List Kosong)
                                data_batch = []
                                
                                for i, row in edited_st.iterrows():
                                    target_email = row['EMAIL'].strip().lower()
                                    idx_asli = int(row['REAL_IDX'])
                                    old_val = df.iloc[idx_asli]
                                    
                                    # --- LOGIKA TARGET HP (SLOT DINAMIS 2 & 3) ---
                                    target_hp = str(old_val['HP'])
                                    if row['STATUS'] == 'PROSES' and old_val['STATUS'] == 'STANDBY':
                                        df_p_now = df[df['STATUS'] == 'PROSES'].copy()
                                        hp_counts = df_p_now['HP'].astype(str).value_counts().to_dict()
                                        
                                        target_hp = "1"
                                        for h in range(1, 101):
                                            count_sekarang = hp_counts.get(str(h), 0)
                                            
                                            # TENTUKAN MAKSIMAL SLOT:
                                            # Masukin nomor HP yang mau lo jatah 3 di dalam kurung [ ]
                                            # Kalau mau balikin 2 semua, kosongin aja isinya jadi: if h in []:
                                            if h in [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]:
                                                max_slot = 3
                                            else:
                                                max_slot = 2
                                            
                                            if count_sekarang < max_slot:
                                                target_hp = str(h)
                                                break

                                    elif row['STATUS'] in ['SOLD', 'BUSUK', 'SUSPEND'] and old_val['STATUS'] == 'PROSES':
                                        target_hp = ""

                                    # 2. MASUKIN DATA KE KERANJANG (GAK PAKE .execute() DI SINI!)
                                    data_batch.append({
                                        "TANGGAL": tgl_now,
                                        "EMAIL": target_email,
                                        "PASSWORD": row['PASSWORD'],
                                        "NAMA_CHANNEL": row['NAMA_CHANNEL'],
                                        "SUBSCRIBE": str(row['SUBSCRIBE']),
                                        "LINK_CHANNEL": row['LINK_CHANNEL'],
                                        "STATUS": row['STATUS'],
                                        "HP": target_hp,
                                        "PENCATAT": row['PENCATAT'],
                                        "EDITED": f"Up: {user_aktif} ({tgl_now})"
                                    })

                                # 3. TEMBAK SUPABASE (SEKALIGUS DI LUAR LOOP)
                                # Inilah yang bikin instan milidetik, Cok!
                                if data_batch:
                                    supabase.table("Channel_Pintar").upsert(data_batch, on_conflict="EMAIL").execute()

                                st.cache_data.clear()
                                st.success(f"✅ Mantap! {len(data_batch)} Akun Berhasil Diupdate!")
                                time.sleep(1)
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"❌ Error Global: {e}")
                            
    # ==============================================================================
    # TAB 2: MONITORING PROSES (RADAR SYNC & SLOT HP PROTECTION)
    # ==============================================================================
    with tab_proses:
        if not is_pro:
            st.warning("🔒 Akses Terbatas.")
        else:
            st.markdown("#### 🚀 MONITORING PROSES (MAX 2 SLOT HP)")
            # --- TAMBAHAN: ST INFO UNTUK INSTRUKSI STAFF ---
            st.info("""
                💡 **PENGINGAT KHUSUS:**
                1. HP 1-14 isi Konten Sakura
                2. HP 15-19 isi Konten AI (aku sendiri yang isi sementara)
                3. WASPADA! HP 10-19 ada 3 channel (login hapus dan stock video disesuaikan)
            """)

            df_p = df[df['STATUS'] == 'PROSES'].copy()

            if df_p.empty:
                st.info("Semua unit HP kosong.")
            else:
                # --- FIX SORTING (Agar HP 1, 2... 10, 11 urut lurus) ---
                # Mengambil angka dari teks "HP 01" atau "HP 1"
                df_p['HP_NUM'] = df_p['HP'].astype(str).str.extract('(\d+)').astype(float).fillna(999)
                # Sort berdasarkan angka HP, lalu Email
                df_p = df_p.sort_values(by=['HP_NUM', 'EMAIL'])

                display_list = []
                # Pakai sort=False agar groupby tidak mengacak urutan yang sudah dibuat
                for hp_id, group in df_p.groupby('HP', sort=False):
                    for i, (idx, r) in enumerate(group.iterrows()):
                        display_list.append({
                            "REAL_IDX": idx,
                            "HP": f"📱 HP {hp_id}" if i == 0 else "", 
                            "EMAIL": r['EMAIL'],
                            "PASSWORD": r['PASSWORD'],
                            "NAMA_CHANNEL": r['NAMA_CHANNEL'],
                            "SUBSCRIBE": str(r['SUBSCRIBE']),
                            "LINK_CHANNEL": r['LINK_CHANNEL'],
                            "STATUS": r['STATUS']
                        })

                df_display = pd.DataFrame(display_list)
                
                config_p = {
                    "HP": st.column_config.TextColumn("📱 UNIT", width=50, disabled=True),
                    "EMAIL": st.column_config.TextColumn("📧 EMAIL", width=200, disabled=True),
                    "PASSWORD": st.column_config.TextColumn("🔑 PASS", width=130, disabled=True),
                    "NAMA_CHANNEL": st.column_config.TextColumn("📺 CHANNEL", width=130, disabled=True),
                    "SUBSCRIBE": st.column_config.TextColumn("📊 SUBS", width=50), 
                    "LINK_CHANNEL": st.column_config.LinkColumn("🔗 URL", width=300, disabled=True),
                    "STATUS": st.column_config.SelectboxColumn(
                        "⚙️ STATUS", width=80, 
                        options=["PROSES", "SOLD", "STANDBY", "BUSUK", "SUSPEND"]
                    ),
                    "REAL_IDX": None
                }

                edited_p = st.data_editor(
                    df_display, 
                    column_config=config_p, 
                    use_container_width=True, 
                    hide_index=True, 
                    key="grid_p_pro_locked",
                    disabled=not is_pro 
                )

                # --- LOGIKA SAVE (FULL SUPABASE - MODE BATCH f/16) ---
                if is_pro and not edited_p.equals(df_display):
                    if st.button("💾 UPDATE STATUS MONITORING", use_container_width=True, type="primary"):
                        try:
                            with st.spinner("Sinkronisasi Radar ke Supabase..."):
                                tgl_now = datetime.now(tz).strftime("%d/%m/%Y %H:%M")
                                
                                # 1. Bikin list kosong buat nampung data
                                data_batch = []
                                
                                for i, row in edited_p.iterrows():
                                    target_email = row['EMAIL'].strip().lower()
                                    idx_asli = int(row['REAL_IDX'])
                                    old_val = df.iloc[idx_asli]
                                    
                                    # Cek perubahan
                                    if (row['STATUS'] != old_val['STATUS'] or str(row['SUBSCRIBE']) != str(old_val['SUBSCRIBE'])):
                                        target_hp = str(old_val['HP'])
                                        if row['STATUS'] != 'PROSES':
                                            target_hp = "" 

                                        # CUMA DISIMPAN KE LIST (Belum kirim ke internet)
                                        data_batch.append({
                                            "EMAIL": target_email,
                                            "STATUS": row['STATUS'],
                                            "SUBSCRIBE": str(row['SUBSCRIBE']),
                                            "HP": target_hp,
                                            "EDITED": f"Up: {user_aktif} ({tgl_now})"
                                        })

                                # 2. EKSEKUSI DI LUAR LOOP (Cuma 1x kirim, ini yang bikin instan!)
                                if data_batch:
                                    supabase.table("Channel_Pintar").upsert(data_batch, on_conflict="EMAIL").execute()
                                
                                st.cache_data.clear()
                                st.success(f"✅ {len(data_batch)} Akun Berhasil Diperbarui secara Instan!")
                                time.sleep(1)
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"❌ Gagal update: {e}")
                    
    # ==============================================================================
    # TAB 3: JADWAL UPLOAD (FULL MANUAL - SLOT HP VERSION)
    # ==============================================================================
    with tab_jadwal:
        df_j = df[df['STATUS'] == 'PROSES'].copy()

        if df_j.empty:
            st.info("Belum ada akun di Tab Proses.")
        else:
            tz = pytz.timezone('Asia/Jakarta')
            now_indo = datetime.now(tz)
            
            # --- Map Bulan Indo ---
            nama_bulan = {
                1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
                7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
            }
            tgl_str = f"{now_indo.day} {nama_bulan[now_indo.month]} {now_indo.year}"

            # --- 1. FITUR EDIT JAM (FULL SUPABASE - KENCENG SILET) ---
            if is_pro:
                with st.expander("🛠️ EDIT JAM UPLOAD (SLOT HP)", expanded=False):
                    df_j['REAL_IDX'] = df_j.index
                    df_j['HP_N'] = pd.to_numeric(df_j['HP'], errors='coerce').fillna(999)
                    
                    # Sort biar rapi per HP dan waktu
                    df_j_sorted = df_j.sort_values(['HP_N', 'PAGI'])

                    kolom_edit = ["HP", "NAMA_CHANNEL", "PAGI", "SIANG", "SORE", "EMAIL", "REAL_IDX"]
                    
                    edited_j = st.data_editor(
                        df_j_sorted[kolom_edit],
                        column_config={
                            "HP": st.column_config.TextColumn("📱 HP", width=50, disabled=True),
                            "NAMA_CHANNEL": st.column_config.TextColumn("📺 CHANNEL", width=250, disabled=True),
                            "PAGI": st.column_config.TextColumn("🌅 PAGI"),
                            "SIANG": st.column_config.TextColumn("☀️ SIANG"),
                            "SORE": st.column_config.TextColumn("🌆 SORE"),
                            "EMAIL": None, 
                            "REAL_IDX": None
                        },
                        use_container_width=True, hide_index=True, key="editor_manual_full"
                    )

                    if st.button("💾 SIMPAN SEMUA JADWAL", use_container_width=True, type="primary"):
                        try:
                            with st.spinner("Sinkronisasi Jadwal ke Supabase..."):
                                jam_log = now_indo.strftime('%H:%M')
                                data_supabase = []

                                for _, row in edited_j.iterrows():
                                    target_email = row['EMAIL'].strip().lower()
                                    
                                    # --- TAMPUNG DATA KE LIST UNTUK SEKALI TEMBAK ---
                                    data_supabase.append({
                                        "EMAIL": target_email,
                                        "PAGI": str(row['PAGI']) if row['PAGI'] else "",
                                        "SIANG": str(row['SIANG']) if row['SIANG'] else "",
                                        "SORE": str(row['SORE']) if row['SORE'] else "",
                                        "EDITED": f"Up: {user_aktif} (Jadwal {jam_log})"
                                    })

                                # --- EKSEKUSI SUPABASE (MASSAL & INSTAN) ---
                                if data_supabase:
                                    supabase.table("Channel_Pintar").upsert(
                                        data_supabase, on_conflict="EMAIL"
                                    ).execute()

                                # Gak perlu lagi batch_update GSheet yang bikin pusing cok!
                                
                                st.cache_data.clear()
                                st.success(f"✅ Mantap! {len(data_supabase)} Jadwal Berhasil Sinkron.")
                                time.sleep(1)
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"❌ Terjadi Kesalahan: {e}")

            st.divider()

            # --- 2. LOGIKA GENERATE TABEL (12 HP PER HALAMAN - FULL AESTHETIC) ---
            df_j['HP_N'] = pd.to_numeric(df_j['HP'], errors='coerce').fillna(999)
            df_display = df_j.sort_values(['HP_N', 'PAGI'])
            
            list_hp_unik = df_display['HP'].unique()
            total_hal = (len(list_hp_unik) + 10) // 11
            html_all_pages = "" 

            for start_idx in range(0, len(list_hp_unik), 11):
                hp_halaman_ini = list_hp_unik[start_idx : start_idx + 11]
                df_page = df_display[df_display['HP'].isin(hp_halaman_ini)]
                hal_ke = (start_idx // 11) + 1
                
                html_all_pages += f"""
                <div class="print-container {'page-break' if hal_ke < total_hal else ''}">
                    <div class="header-box">
                        <div style="float: right; font-size: 10px; font-weight: bold; color: #888;">HALAMAN {hal_ke} / {total_hal}</div>
                        <div style="clear: both;"></div>
                        <h2>📋 JADWAL UPLOAD PINTAR MEDIA</h2>
                        <p class="sub">Periode: <b>{tgl_str}</b> | Unit HP {hp_halaman_ini[0]} - {hp_halaman_ini[-1]}</p>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 10%;">📱 HP</th>
                                <th style="width: 45%;">📺 CHANNEL YOUTUBE</th>
                                <th style="width: 15%;">🌅 PAGI</th>
                                <th style="width: 15%;">☀️ SIANG</th>
                                <th style="width: 15%;">🌆 SORE</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for i, r in enumerate(df_page.itertuples()):
                    p = r.PAGI if pd.notna(r.PAGI) and str(r.PAGI).strip() != "" else "-"
                    s = r.SIANG if pd.notna(r.SIANG) and str(r.SIANG).strip() != "" else "-"
                    o = r.SORE if pd.notna(r.SORE) and str(r.SORE).strip() != "" else "-"
                    
                    hp_view = str(r.HP) if i == 0 or str(r.HP) != str(df_page.iloc[i-1]['HP']) else ""
                    
                    # WARNA SELANG SELING (ZEBRA) - Abu-abu Halus
                    bg_color = "#FFFFFF" if i % 2 == 0 else "#F4F4F4"
                    
                    html_all_pages += f"""
                        <tr style="background-color: {bg_color} !important;">
                            <td class="col-hp" style="border-right: 1px solid #CCC !important;">{hp_view}</td>
                            <td class="col-ch">{r.NAMA_CHANNEL}</td>
                            <td class="col-jam">{p}</td>
                            <td class="col-jam">{s}</td>
                            <td class="col-jam">{o}</td>
                        </tr>
                    """
                
                html_all_pages += "</tbody></table></div>"

            # --- 3. MONITORING VIEW (WEB) ---
            st.markdown("#### 📱 MONITORING JADWAL UPLOAD")
            st.dataframe(
                df_display[["HP", "NAMA_CHANNEL", "PAGI", "SIANG", "SORE"]],
                column_config={
                    "HP": st.column_config.TextColumn("📱 HP", width=50),
                    "NAMA_CHANNEL": st.column_config.TextColumn("📺 CHANNEL", width=250),
                    "PAGI": st.column_config.TextColumn("🌅 PAGI", width=120),
                    "SIANG": st.column_config.TextColumn("☀️ SIANG", width=120),
                    "SORE": st.column_config.TextColumn("🌆 SORE", width=120),
                }, hide_index=True, use_container_width=True
            )

            # --- 4. STYLE SULTAN AESTHETIC V2 (FULL ABU-ABU + HEADER HITAM) ---
            html_masterpiece = f"""
            <style>
                @media print {{
                    @page {{ size: A4 portrait; margin: 1cm; }}
                    * {{ box-sizing: border-box; }}
                    body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 0; background: white; }}
                    
                    .print-container {{ width: 100%; max-width: 690px; margin: 0 auto; }}
                    .page-break {{ page-break-after: always; }}

                    .header-box {{ text-align: center; border-bottom: 2px solid #333; margin-bottom: 15px; padding-bottom: 5px; }}
                    h2 {{ font-size: 20px; margin: 5px 0; color: #000; }}
                    .sub {{ font-size: 12px; color: #666; }}

                    table {{ 
                        width: 100%; 
                        border-collapse: collapse; 
                        border: 1px solid #CCC; /* SEMUA GARIS LUAR ABU-ABU */
                        table-layout: fixed;
                    }}
                    
                    /* HEADER HITAM SOLID */
                    th {{ 
                        background-color: #1A1A1A !important; 
                        color: white !important; 
                        padding: 10px; 
                        border: 1px solid #333; 
                        font-size: 12px;
                        -webkit-print-color-adjust: exact;
                    }}
                    
                    td {{ 
                        border: 1px solid #CCC; /* SEMUA GARIS DALAM ABU-ABU */
                        padding: 8px 10px; 
                        font-size: 14px; 
                        color: #111;
                        line-height: 1.3;
                    }}
                    
                    .col-hp {{ width: 10%; text-align: center; font-weight: bold; background-color: #F8F8F8 !important; }}
                    .col-ch {{ text-align: left; font-weight: 500; padding-left: 12px; }}
                    .col-jam {{ text-align: center; font-weight: bold; color: #C00 !important; }}
                    
                    .footer-note {{ margin-top: 10px; text-align: right; font-size: 9px; color: #999; }}
                }}
            </style>
            {html_all_pages}
            """
            
            if st.button("📄 PRINT JADWAL", use_container_width=True, type="primary"):
                st.components.v1.html(html_masterpiece + "<script>window.print();</script>", height=0)
                        
    # ======================================================================
    # --- TAB 4: MONITOR HP (ANTI-CRASH & SLOT HP PROTECTION) ---
    # ======================================================================
    with tab_hp:
        # --- 1. EXPANDER INPUT (HANYA UNTUK OWNER/ADMIN) ---
        if is_boss:
            with st.expander("➕ DAFTARKAN UNIT HP BARU", expanded=False):
                with st.form("form_hp_fix_statis", clear_on_submit=True):
                    st.markdown("### 📝 Input Data Unit")
                    c1, c2 = st.columns(2)
                    v_nama = c1.text_input("Nama Unit (Contoh: HP 01)")
                    v_no = c2.text_input("Nomor HP (Contoh: 0812...)")
                    
                    c3, c4 = st.columns(2)
                    v_prov = c3.selectbox("Provider", ["TELKOMSEL", "XL", "AXIS", "INDOSAT", "TRI", "SMARTFREN"])
                    v_tgl = c4.date_input("Masa Aktif Kartu")
                    
                    if st.form_submit_button("🚀 SIMPAN UNIT", use_container_width=True):
                        if v_nama and v_no:
                            try:
                                tgl_fix = v_tgl.strftime("%d/%m/%Y")
                                
                                # --- GANTI KE SUPABASE (INSTAN f/16) ---
                                # Asumsi nama tabel di Supabase lo: Data_HP
                                supabase.table("Data_HP").insert({
                                    "NAMA_HP": str(v_nama).upper(),
                                    "NOMOR_HP": str(v_no),
                                    "PROVIDER": v_prov,
                                    "MASA_AKTIF": tgl_fix
                                }).execute()

                                st.cache_data.clear() 
                                st.success(f"✅ {v_nama} Berhasil Didaftarkan ke Supabase!")
                                time.sleep(0.5)
                                st.rerun() 
                            except Exception as e:
                                st.error(f"Error Supabase: {e}")
                        else:
                            st.error("Nama & Nomor wajib diisi!")

        st.divider()

        # --- 2. DISPLAY RADAR CARD ---
        if df_hp.empty:
            st.info("Radar unit HP masih kosong.")
        else:
            tz = pytz.timezone('Asia/Jakarta')
            now_indo = datetime.now(tz).date()
            
            # --- FIX URUTAN HP (Agar 1, 2, 3... urut lurus) ---
            df_hp['HP_NUM'] = df_hp['NAMA_HP'].astype(str).str.extract('(\d+)').astype(float).fillna(999)
            df_view = df_hp[df_hp['NAMA_HP'].str.strip() != ""].sort_values('HP_NUM').copy()
            
            # Tampilan Grid 4 Kolom
            grid = st.columns(4) 
            for i, (idx, r) in enumerate(df_view.iterrows()):
                with grid[i % 4]:
                    # --- LOGIKA WARNA SISA HARI (ANTI-CRASH) ---
                    try:
                        t_exp = pd.to_datetime(r['MASA_AKTIF'], dayfirst=True).date()
                        sisa = (t_exp - now_indo).days
                        
                        if sisa > 10: color_code = "#2D5A47" # HIJAU (AMAN)
                        elif 4 <= sisa <= 10: color_code = "#B8860B" # KUNING (WASPADA)
                        else: color_code = "#962D2D" # MERAH (KRITIS)
                    except:
                        color_code = "#444"; sisa = "?"

                    with st.container(border=True):
                        # Header Unit dengan indikator Sisa Hari
                        st.markdown(f'''
                            <div style="background:{color_code}; padding:5px; border-radius:5px; text-align:center; margin-bottom:12px;">
                                <b style="color:white; font-size:18px;">{r["NAMA_HP"]}</b>
                            </div>
                        ''', unsafe_allow_html=True)
                        
                        # Info Detail (📞 Nomor & 📡 Provider)
                        ic1, ic2 = st.columns(2)
                        ic1.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>📞 NOMOR</p><b style='font-size:14px;'>{r['NOMOR_HP']}</b>", unsafe_allow_html=True)
                        ic2.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>📡 PROVIDER</p><b style='font-size:11px;'>{r['PROVIDER']}</b>", unsafe_allow_html=True)
                        
                        # Info Expired & Sisa Hari
                        st.divider()
                        sc1, sc2 = st.columns(2)
                        sc1.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>📅 EXPIRED</p><code style='font-size:11px;'>{r['MASA_AKTIF']}</code>", unsafe_allow_html=True)
                        
                        sisa_color = "#ff4b4b" if isinstance(sisa, int) and sisa < 4 else "#ffffff"
                        sc2.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>⏳ SISA</p><b style='font-size:14px; color:{sisa_color};'>{sisa} Hari</b>", unsafe_allow_html=True)

                        # --- FITUR EDIT (HANYA BOS) ---
                        if is_boss:
                            with st.popover("✏️ Edit", use_container_width=True):
                                st.markdown(f"#### 🛠️ EDIT: {r['NAMA_HP']}")
                                e_nama = st.text_input("📱 Nama Unit", value=str(r['NAMA_HP']), key=f"en_{idx}").strip()
                                e_no = st.text_input("📞 Nomor HP", value=str(r['NOMOR_HP']), key=f"eno_{idx}").strip()
                                
                                provider_list = ["TELKOMSEL", "XL", "AXIS", "INDOSAT", "TRI", "SMARTFREN"]
                                curr_prov = r['PROVIDER'] if r['PROVIDER'] in provider_list else "TELKOMSEL"
                                e_prov = st.selectbox("📡 Provider", provider_list, index=provider_list.index(curr_prov), key=f"ep_{idx}")
                                e_tgl = st.text_input("📅 Exp (DD/MM/YYYY)", value=str(r['MASA_AKTIF']), key=f"et_{idx}").strip()
                                
                                if st.button("💾 SIMPAN", key=f"btn_e_{idx}", use_container_width=True, type="primary"):
                                    if e_nama and e_no:
                                        try:
                                            # --- GANTI KE SUPABASE (INSTAN f/16) ---
                                            # Kita update berdasarkan NAMA_HP lama sebagai kunci
                                            supabase.table("Data_HP").update({
                                                "NAMA_HP": e_nama.upper(), 
                                                "NOMOR_HP": str(e_no), 
                                                "PROVIDER": e_prov, 
                                                "MASA_AKTIF": e_tgl
                                            }).eq("NAMA_HP", r['NAMA_HP']).execute()
                                            
                                            st.cache_data.clear()
                                            st.success(f"✅ {e_nama} Berhasil Diupdate di Supabase!")
                                            time.sleep(0.5)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Gagal Update Supabase: {e}")
                                    else:
                                        st.error("⚠️ Nama & Nomor HP wajib diisi!")
                        
    # ==============================================================================
    # TAB 5: SOLD CHANNEL (SINKRON SUPABASE - ORIGINAL UI)
    # ==============================================================================
    with tab_sold:
        if not is_ceo: 
            st.error("🔒 Akses Khusus Owner.")
        else:
            # --- 1. SETUP FILTER PERIODE ---
            tz = pytz.timezone('Asia/Jakarta')
            now_indo = datetime.now(tz)
            
            col_f1, col_f2 = st.columns([1, 1])
            with col_f1:
                list_bulan = {"01": "Januari", "02": "Februari", "03": "Maret", "04": "April", "05": "Mei", "06": "Juni", "07": "Juli", "08": "Agustus", "09": "September", "10": "Oktober", "11": "November", "12": "Desember"}
                sel_bln_nama = st.selectbox("📅 Pilih Bulan Audit", list(list_bulan.values()), index=now_indo.month - 1, key="tab_sold_bln")
                sel_bln_code = [k for k, v in list_bulan.items() if v == sel_bln_nama][0]
            with col_f2:
                # Tambahin 2026 karena sekarang udah 2026, Bos!
                sel_thn = st.selectbox("📆 Pilih Tahun", ["2024", "2025", "2026"], index=2, key="tab_sold_thn")

            filter_periode = f"{sel_bln_code}/{sel_thn}"
            
            # --- 2. LOGIKA HITUNG DATA (SUPABASE DATA) ---
            df_sold_all = df[df['STATUS'] == 'SOLD'].copy()
            total_ever = len(df_sold_all)
            
            # Filter periode berdasarkan kolom EDITED (format: DD/MM/YYYY HH:MM)
            # Kita pake .str.contains biar lebih fleksibel dibanding match
            mask_periode = df_sold_all['EDITED'].astype(str).str.contains(filter_periode, na=False)
            df_selected = df_sold_all[mask_periode].copy()
            
            total_selected = len(df_selected)
            
            # Hitung data bulan lalu buat Delta Metric
            try:
                date_selected = datetime.strptime(f"01/{filter_periode}", "%d/%m/%Y")
                date_prev = (date_selected - timedelta(days=1))
                filter_prev = date_prev.strftime("%m/%Y")
                total_prev = len(df_sold_all[df_sold_all['EDITED'].astype(str).str.contains(filter_prev, na=False)])
            except:
                total_prev = 0
                filter_prev = "N/A"

            # --- 3. RENDER 3 METRIK UTAMA ---
            with st.container(border=True):
                m1, m2, m3 = st.columns(3)
                m1.metric("💰 TOTAL SOLD", f"{total_ever}", delta="Unit Laku")
                m2.metric(f"📅 {sel_bln_nama.upper()} {sel_thn}", f"{total_selected}", delta=f"Bulan Ini")
                m3.metric(f"🕒 BULAN LALU", f"{total_prev}", delta=f"Perbandingan {filter_prev}", delta_color="off")

            st.markdown("<br>", unsafe_allow_html=True)

            # --- 4. DATABASE TABEL ---
            st.markdown(f"##### 📊 DAFTAR PENJUALAN PERIODE {sel_bln_nama.upper()} {sel_thn}")
            if df_selected.empty:
                st.info(f"Belum ada data penjualan tercatat untuk periode {filter_periode}")
            else:
                # Aliaskan EDITED ke TGL_LAST (Sesuai gaya lo)
                df_selected['TGL_LAST'] = df_selected['EDITED']
                
                # Sort terbaru di atas biar Owner gampang liat
                df_selected = df_selected.sort_values('TGL_LAST', ascending=False)
                
                cols_view = ["TGL_LAST", "EMAIL", "PASSWORD", "NAMA_CHANNEL", "SUBSCRIBE", "LINK_CHANNEL", "STATUS"]
                
                st.dataframe(
                    df_selected[cols_view], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "TGL_LAST": st.column_config.TextColumn("⏰ TGL SOLD", width=180),
                        "EMAIL": st.column_config.TextColumn("📧 EMAIL", width=200),
                        "PASSWORD": st.column_config.TextColumn("🔑 PASS", width=120),
                        "NAMA_CHANNEL": st.column_config.TextColumn("📺 CHANNEL", width=150),
                        "SUBSCRIBE": st.column_config.TextColumn("📊 SUBS", width=80),
                        "LINK_CHANNEL": st.column_config.LinkColumn("🔗 LINK", width=100),
                        "STATUS": st.column_config.TextColumn("⚙️ STATUS", width=80) 
                    }
                )
                
    # ==============================================================================
    # TAB 6: ARSIP CHANNEL (SINKRON SUPABASE - ORIGINAL UI)
    # ==============================================================================
    with tab_arsip:
        if not is_ceo: 
            st.error("🔒 Akses Khusus Owner & Admin.")
        else:
            # --- 1. LOGIKA DASHBOARD ARSIP ---
            # df ini udah hasil load dari Supabase di awal aplikasi (load_data_channel)
            df_a = df[df['STATUS'].isin(['BUSUK', 'SUSPEND'])].copy()
            
            total_arsip = len(df_a)
            total_busuk = len(df_a[df_a['STATUS'] == 'BUSUK'])
            total_suspend = len(df_a[df_a['STATUS'] == 'SUSPEND'])

            # --- 2. RENDER 3 METRIK UTAMA ---
            with st.container(border=True):
                ca1, ca2, ca3 = st.columns(3)
                # Pake delta_color="inverse" karena kenaikan angka di sini artinya hal buruk (Loss)
                ca1.metric("💀 TOTAL ARSIP", f"{total_arsip}", delta="Akun Rusak", delta_color="inverse")
                ca2.metric("📉 TOTAL BUSUK", f"{total_busuk}", delta="Teknis/Kartu", delta_color="inverse")
                ca3.metric("🚫 TOTAL SUSPEND", f"{total_suspend}", delta="Banned YT", delta_color="inverse")

            st.markdown("<br>", unsafe_allow_html=True)

            # --- 3. DATABASE ARSIP (SINKRON SUPABASE) ---
            st.markdown("##### 📂 DAFTAR AKUN ARSIP (HISTORY AUDIT)")
            if df_a.empty:
                st.success("✨ Arsip masih kosong. Belum ada akun yang bermasalah!")
            else:
                # Aliaskan EDITED ke TGL_KEJADIAN & Sort terbaru di atas
                df_a['TGL_KEJADIAN'] = df_a['EDITED']
                df_a = df_a.sort_values(by=['TGL_KEJADIAN'], ascending=False)
                
                # Susunan Kolom PERSIS punya lo
                cols_arsip = ["TGL_KEJADIAN", "EMAIL", "PASSWORD", "NAMA_CHANNEL", "SUBSCRIBE", "LINK_CHANNEL", "STATUS"]
                
                st.dataframe(
                    df_a[cols_arsip], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "TGL_KEJADIAN": st.column_config.TextColumn("⏰ TGL KEJADIAN", width=180),
                        "EMAIL": st.column_config.TextColumn("📧 EMAIL", width=200),
                        "PASSWORD": st.column_config.TextColumn("🔑 PASS", width=120),
                        "NAMA_CHANNEL": st.column_config.TextColumn("📺 CHANNEL", width=150),
                        "SUBSCRIBE": st.column_config.TextColumn("📊 SUBS", width=80),
                        "LINK_CHANNEL": st.column_config.LinkColumn("🔗 LINK", width=100),
                        "STATUS": st.column_config.TextColumn(
                            "⚠️ STATUS", 
                            width=100,
                            help="BUSUK = Masalah Teknis/Kartu, SUSPEND = Banned YouTube"
                        )
                    }
                )
                            
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
    level_aktif = st.session_state.get("user_level", "STAFF")

    # 2. EKSEKUSI MESIN ABSEN
    log_absen_otomatis(user_aktif)

    # 3. KUNCI DATA DARI SESSION STATE
    data = st.session_state.data_produksi
    ver = st.session_state.get("form_version", 0)

    # 4. HEADER UI RUANG PRODUKSI (VERSI CYBER TECH)
    st.title(f"🚀 RUANG PRODUKSI")
    st.markdown(f"**{user_aktif}** | 📅 {nama_hari}, {sekarang.strftime('%d %B %Y')}")
    
    # --- STATUS BADGE (CYBER SECURITY STYLE) ---
    with st.container():
        if level_aktif in ["OWNER", "ADMIN"]:
            # Pesan khusus buat lo sebagai Owner
            st.markdown("<p style='color: #7f8c8d; font-size: 13px; margin-top:-15px; margin-bottom: 20px;'>⚡ <b>System Administrator Override</b></p>", unsafe_allow_html=True)
        
        elif st.session_state.get('absen_done_today'):
            # Menunjukkan data sudah masuk & terverifikasi sistem
            jam_v = sekarang.strftime('%H:%M')
            st.markdown(f"<p style='color: #00ba69; font-size: 13px; margin-top:-15px; margin-bottom: 20px;'>🟢 <b>Secure Connection Established</b> (Verified: {jam_v} WIB)</p>", unsafe_allow_html=True)
        
        elif 8 <= sekarang.hour < 22:
            # Status saat sistem lagi kerja (loading)
            st.markdown("<p style='color: #e67e22; font-size: 13px; margin-top:-15px; margin-bottom: 20px;'>📡 <b>Synchronizing session data...</b></p>", unsafe_allow_html=True)
        
        else:
            # Status jika login lewat jam 10 malam
            st.markdown("<p style='color: #ff4b4b; font-size: 13px; margin-top:-15px; margin-bottom: 20px;'>🚫 <b>Access Denied:</b> Operational Window Closed</p>", unsafe_allow_html=True)

    # --- QUALITY BOOSTER & NEGATIVE CONFIG (VERSI TAJAM f/16 & REAL-TIME SPEED) ---
    QB_IMG = (
        "8k RAW optical clarity, infinite depth of field, f/16 aperture, "
        "pan-focal razor-sharp background, zero bokeh, edge-to-edge clarity, "
        "high-index lens glass look, CPL filter, sub-surface scattering, "
        "physically-based rendering, hyper-detailed surface micro-textures, "
        "anisotropic filtering, ray-traced ambient occlusion, NO DEPTH BLUR"
    )

    QB_VID = (
        "Unreal Engine 5.4, 30fps real-time speed, high-shutter performance, ultra-clear, 8k UHD, "
        "pan-focal rendering, zero background blur, pin-sharp every frame, "
        "professional color grading, ray-traced reflections, hyper-detailed textures, "
        "temporal anti-aliasing, zero digital noise, clean pixels, "
        "natural human-like physics, high-fidelity physical interaction, NO SLOW MOTION, NO MOTION BLUR"
    )

    # --- UPDATE: Tambahkan larangan SLOW MO & BLUR di Negative ---
    negative_base = (
        "muscular, bodybuilder, shredded, male anatomy, human skin, human anatomy, "
        "realistic flesh, skin pores, blurry, out of focus, bokeh, depth of field, "
        "blurry background, slow motion, time-lapse, motion blur, distorted surface, "
        "soft focus, Gaussian blur, tilt-shift, hazy background"
    )
    
    no_text_strict = (
        "STRICTLY NO text, NO typography, NO watermark, NO letters, NO subtitles, "
        "NO captions, NO speech bubbles, NO dialogue boxes, NO labels, NO black bars, "
        "NO burned-in text, NO characters speaking with visible words, "
        "the image must be a CLEAN cinematic shot without any written characters."
    )
    
    negative_motion_strict = (
        "STRICTLY NO morphing, NO extra limbs, NO distorted faces, NO teleporting objects, "
        "NO flickering textures, NO sudden lighting jumps, NO floating hair artifacts, "
        "NO unnatural slow motion, NO frame skipping, NO ghosting effects, NO cinematic slow-mo."
    )
    
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
                    
                    # 2. Mantra IMAGE (Infinte Depth of Field - f/16 VERSION)
                    style_map_img = {
                        # --- UPDATE: Kunci di f/16 & No Softening agar Sawah/Rumah Bening Silet ---
                        "Sangat Nyata": "Cinematic RAW shot, PBR surfaces, 8k textures, tactile micro-textures, f/16 aperture, infinite depth of field, zero bokeh, no softening, edge-to-edge sharpness.",
                        "Animasi 3D Pixar": "Disney style 3D, Octane render, ray-traced global illumination, premium subsurface scattering.",
                        "Gaya Cyberpunk": "Futuristic neon aesthetic, volumetric fog, sharp reflections, high contrast.",
                        "Anime Jepang": "Studio Ghibli style, hand-painted watercolor textures, soft cel shading, lush aesthetic."
                    }
                    s_img = style_map_img.get(sc['style'], "Cinematic optical clarity.")
                    mantra_statis = f"{s_img} {sc['shot']} framing, {sc['arah']} angle, razor-sharp optical focus, {sc['light']}."

                    # Logika Acting Cue Gaya Baru (ANTI-DIALOG DOBEL & LEBIH EKSPRESIF)
                    raw_dialogs = [f"[{data['karakter'][i]['nama'].upper()}]: '{sc['dialogs'][i].strip()}'" for i in range(data["jumlah_karakter"]) if sc['dialogs'][i].strip()]
                    
                    emotional_ref = " | ".join(raw_dialogs) if raw_dialogs else "No dialogue, focus on cinematic body language."
                    
                    # --- UPDATE: Biar Akting Tung Realistis (Nggak Kaku) ---
                    acting_cue_custom = (
                        f"ACTING RULE: {emotional_ref}. "
                        "Sync lip movement perfectly. "
                        "Characters must exhibit subtle, natural micro-expressions: "
                        "breathing, shifting weight, natural blinking, and realistic eye focus. "
                        "NO robotic or stiff movements. Smooth human-like articulation."
                    )

                    # --- RAKIT PROMPT GAMBAR (TAJAM SILET f/16) ---
                    img_p = (
                        f"IMAGE REFERENCE RULE: Use uploaded photos for each character. Interaction required.\n"
                        f"{final_identity}\n"
                        f"SCENE: {sc['aksi']}\n"
                        f"LOCATION: {sc['loc']}\n"
                        f"VISUAL: {mantra_statis} NO SOFTENING, extreme edge-enhancement, f/16 deep focus.\n"
                        f"QUALITY: {QB_IMG}\n"
                        f"NEGATIVE: {negative_base} {no_text_strict}\n"
                        f"FORMAT: 9:16 Vertical Framing"
                    )

                    # --- RAKIT PROMPT VIDEO (REAL-TIME SPEED & NO BLUR) ---
                    vid_p = (
                        f"IMAGE REFERENCE RULE: Refer to PHOTO #1 for ACTOR_1, PHOTO #2 for ACTOR_2, etc.\n"
                        f"{final_identity}\n"
                        f"SCENE: {sc['aksi']} in {sc['loc']}. Motion: {sc['cam']}.\n"
                        f"PHYSICS: High-fidelity clothing simulation, natural hair physics, no clipping.\n"
                        f"ACTING: {acting_cue_custom}\n"            
                        f"VISUAL: {mantra_video} 8k UHD, clean textures, 30fps real-time, NO MOTION BLUR, pin-sharp every frame.\n"
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

            # --- SUNTIKAN LOG AKTIVITAS (CCTV) ---
            # Dicatat hanya saat tombol Generate ditekan
            tambah_log(user_aktif, f"GENERATE PROMPT: {len(adegan_terisi)} Adegan")

    # --- 5. FOOTER & PENGAMAN SESSION ---
    st.write("")
    st.divider()
    # Tombol Reset ditaruh di sini (Keluar dari expander)
    col_reset, col_spacer = st.columns([1, 2]) # Pakai kolom biar nggak menuhin layar
    with col_reset:
        if st.button("♻️ RESET FORM", use_container_width=True, help="Klik untuk mengosongkan semua adegan"):
            st.session_state.data_produksi["adegan"] = {}
            st.session_state.form_version = ver + 1
            st.rerun()
                            
# ==============================================================================
# BAGIAN 7: PENGENDALI UTAMA (PINTAR MEDIA OS) - SUPABASE READY
# ==============================================================================
def utama():
    inisialisasi_keamanan() 
    pasang_css_kustom() 
    
    if not cek_autentikasi():
        tampilkan_halaman_login()
    else:
        # --- 1. IDENTITAS USER ---
        user_level = st.session_state.get("user_level", "STAFF")
        user_aktif = st.session_state.get("user_aktif", "User")
        
        # --- 2. SINKRONISASI AWAL (Optional: Warm-up Supabase) ---
        # Ini biar pas buka menu, data udah 'anget' di cache RAM
        if 'last_sync' not in st.session_state:
            st.session_state.last_sync = datetime.now()

        # --- 3. NAVIGASI SIDEBAR ---
        menu = tampilkan_navigasi_sidebar()
        
        # --- 4. LOGIKA ROUTING MENU ---
        if menu == "🚀 RUANG PRODUKSI": 
            tampilkan_ruang_produksi()

        elif menu == "🧠 PINTAR AI LAB": 
            tampilkan_ai_lab()

        elif menu == "💡 GUDANG IDE": 
            tampilkan_gudang_ide()

        elif menu == "📋 TUGAS KERJA": 
            tampilkan_tugas_kerja()

        # --- TAMBAHKAN INI UNTUK DATABASE CHANNEL ---
        elif menu == "📱 DATABASE CHANNEL":
            tampilkan_database_channel()
            
        elif menu == "📘 AREA STAF":
            tampilkan_area_staf() 

        elif menu == "⚡ KENDALI TIM": 
            if user_level in ["OWNER", "ADMIN"]:
                tampilkan_kendali_tim()
            else:
                st.warning(f"⚠️ {user_aktif}, area ini terbatas untuk Manajemen.")
                tampilkan_ruang_produksi()

# --- EKSEKUSI SISTEM ---
if __name__ == "__main__":
    utama()
