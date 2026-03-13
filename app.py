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
    if user_level not in ["OWNER", "ADMIN", "STAFF"]:
        st.error("🚫 Maaf, Area Terbatas.")
        st.stop()

    st.title("🧠 PINTAR AI LAB")

    t_grandma, t_anatomi, t_transform, t_random = st.tabs(["👵 GRANDMA", "🦴 ANATOMY", "⚡ TRANSFORMATION", "🎲 RANDOM"])
                
    # ==========================================================================
    # TAB: THE FAMILY LEGACY (REAL HUMAN - NATURAL WIDE SHOT VERSION)
    # ==========================================================================
    with t_grandma:
        # --- 1. MASTER DNA MANUSIA ASLI (FULL BODY & NATURAL SKIN) ---
        MASTER_FAMILY_SOUL = {
            # ========================== KELOMPOK NENEK (Teduh & Berwibawa) ==========================
            "Nenek (The Matriarch)": (
                "An elderly Indonesian woman with deeply weathered skin. "
                "Her face is covered in a dense network of realistic deep wrinkles, heavy crow's feet, and prominent age lines. "
                "Visible skin pores, subtle age spots, and authentic elderly skin texture. "
                "Her hands are thin and bony, with clearly visible veins and wrinkled knuckles, showing extreme detail. "
                "Natural sagging skin around the neck and jawline. "
                "Raw, unpolished cinematic skin details. No smooth filters. 100% authentic aged look."
            ),
            "Nenek Arum (The Grace)": (
                "An elderly Indonesian woman with a deeply weary and melancholy expression. "
                "Her eyes are half-lidded, tired, and cloudy, with heavy drooping eyelids and deep dark circles. "
                "The skin around her eyes is exceptionally wrinkled with sagging folds. "
                "A fragile and frail physique, featuring thin white hair and a deeply creased forehead. "
                "Her facial expression is calm but profoundly 'sayu' and pensive, as if reflecting on a long life. "
                "Raw elderly skin texture showing authentic sagging and realistic muscle loss in the face. "
                "No youthful filters, 100% realistic tired elderly face."
            ),
            "Nenek Sumi (The Wise)": (
                "An elderly Indonesian woman with a profoundly serene and peaceful expression. "
                "Her face is a beautiful map of deep, realistic wrinkles and fine lines, showing her great age. "
                "Her eyes are bright, clear, and warm, looking forward with a gentle, comforting gaze. "
                "A soft, subtle, and genuine smile is playing on her lips, conveying contentment and wisdom. "
                "Her overall presence is one of dignity, grace, and 'syahdu' tranquility. "
                "Authentic elderly skin texture with natural aging details, no artificial smoothing. "
                "A peaceful, motherly, and spiritually comforted demeanor."
            ),
            "Nenek Lastri (The Devotion)": (
                "An active and joyful Indonesian grandmother in her early 60s. "
                "Her face has a warm, natural elderly glow with gentle wrinkles and laugh lines around her mouth and eyes. " # Keriput wajar
                "Her eyes are bright, sparkling with happiness, and crinkled in a wide, genuine smile. " # Mata berbinar, senyum lebar
                "A cheerful and energetic expression, showing her zest for life and motherly warmth. " # Ekspresi ceria, enerjik
                "She has short, stylish grey hair and a dignified but approachable presence. " # Rambut abu-abu modis
                "Authentic 60-year-old skin texture with realistic laugh lines and age spots, no smooth filters. " # Tekstur kulit 60 tahun
                "A healthy, positive, and spiritually comforted demeanor."
            ),
            "Gadis Desa (The Natural)": (
                "A beautiful young Indonesian woman in her early 20s of Javanese descent. "
                "She has soft, rounded facial features and a genuinely sweet, 'adem' smile. " # Fitur lembut, senyum adem
                "Medium-tan, warm golden skin with natural skin pores and a healthy texture. " # Kulit sawo matang golden
                "Her eyes are dark, kind, and expressive with naturally thick dark lashes. " # Mata gelap, ekspresif
                "Long, wavy black hair loosely tied or flowing naturally. " # Rambut hitam bergelombang
                "Raw, unpolished cinematic skin details showing authentic pores and light, natural imperfections. No smooth filters." # Detail kulit asli
            ),
            "Gadis Rumi (The Dreamer)": (
                "A stunning young Indonesian woman in her early 20s of Malay or Sumatran descent. "
                "She has a more defined jawline, higher cheekbones, and an elegant presence. " # Rahang tegas, tulang pipi tinggi
                "Light olive or fair skin with warm undertones and natural skin texture. " # Kulit kuning langsat/olive light
                "Her eyes are sharp, confident, and almond-shaped with dark eyebrows. " # Mata tajam, almond
                "Straight, sleek black hair cascading down her shoulders. " # Rambut hitam lurus, jatuh
                "MASTERPIECE realism with high-fidelity skin details, natural pores, and authentic, unedited skin look." # Realisme tinggi
            ),
            "Gadis Melati (The Fresh)": (
                "A beautiful and cheerful young Indonesian woman in her early 20s. "
                "Her face is radiating with a broad, genuine, and joyful smile that crinkles her whole face. " # Senyum lebar, ceria
                "Light, healthy, warm yellow-undertone skin (kuning langsat) with natural rosy cheeks and a fresh, dewy texture. " # Kulit kuning langsat fresh
                "Her eyes are bright, sparkling with happiness, and often in a playful or winking expression. " # Mata berbinar, playful
                "Messy, voluminous dark brown or black hair tied up loosely in a ponytail or bun, with loose strands. " # Rambut kuncir, Messy
                "Authentic young skin texture with natural pores, light freckles, and a healthy, unprocessed look. No smooth filters." # Tekstur kulit muda fresh
                "A positive, energetic, energetic, and motherly warmth presence."
            ),
            "Gadis Anisa (The Modest)": (
                "A breathtakingly beautiful young Indonesian woman in her early 20s of Papuan or Melanesian descent. "
                "She has distinct, strong facial features and a wide, confident, and joyful smile. " # Fitur kuat, senyum lebar
                "Deep, dark caramel or rich cocoa skin with glowing, natural skin texture and pores. " # Kulit gelap/cokelat tua
                "Her eyes are big, bright, warm, and sparkling with energetic life. " # Mata besar, berbinar
                "Beautifully textured, voluminous, tight curly black hair flowing naturally. " # Rambut hitam keriting bervolume
                "RAW cinematic details focusing on authentic skin pores, textures, and rich, deep skin tones. No filters." # Fokus pada tekstur kulit gelap
            ),
            "Kakek (The Wise)": (
                "A very elderly Indonesian man in his late 70s with a fragile but dignified look. "
                "His face is a landscape of deep, sagging wrinkles, heavy eye bags, and prominent age spots. "
                "Paper-thin, weathered skin with visible pores and fine veins. " # Kulit setipis kertas
                "Thin white hair and a sparse, long white beard that adds to his ancient wisdom look. " # Jenggot putih tipis
                "Deeply recessed eyes that look tired but peaceful. "
                "Authentic elderly skin texture, raw and unpolished, no smoothing filters."
            ),
            "Kakek Wiryo (The Artisan)": (
                "A sturdy elderly Indonesian man in his 60s with a tough, hardworking physique. "
                "He has sun-darkened, leathery skin with deep creases on his forehead and around his mouth. " # Kulit leathery (seperti kulit samak)
                "Large, strong hands with thick knuckles, prominent veins, and rough skin texture. " # Tangan kuat khas pekerja
                "Short, thick salt-and-pepper hair and a neat white mustache. " # Kumis putih rapi
                "A focused, sharp, and resilient expression. "
                "Realistic skin details showing sweat and authentic grit. Masterpiece realism."
            ),
            "Kakek Joyo (The Farmer)": (
                "A warm and friendly Indonesian grandfather in his 60s with a constant gentle smile. "
                "His eyes are bright and twinkling behind deep laugh lines (crow's feet). " # Mata berbinar
                "Healthy, warm-toned elderly skin with natural aging marks and a kind, fatherly glow. "
                "Full, soft white hair and a clean-shaven, approachable face. "
                "His expression is one of pure contentment, 'syahdu', and spiritual peace. "
                "Natural young-at-heart elderly look, 100% realistic skin textures without filters."
            ),
            "Kakek Usman (The Silent)": (
                "An elderly Indonesian grandfather in his late 60s, visibly heartbroken and deeply saddened. "
                "His face is contorted in grief, with tears streaming down his heavily wrinkled cheeks and jawline. " # Air mata mengalir, keriput bengkak
                "His eyes are red, swollen from crying, half-closed, and glistening with glistening moisture. " # Mata merah, bengkak, glistening
                "A trembling lip, quivering chin, and a deeply furrowed brow expressing profound sorrow and despair. " # Bibir gemetar, dagu bergetar, alis berkerut sedih
                "Thin white hair and a disheveled white beard, adding to his fragile and neglected appearance. " # Rambut/jenggot acak-acakan, ringkih
                "Authentic elderly skin texture with a healthy, unprocessed look, showing natural pores and age lines. No smooth filters." # Tekstur kulit muda fresh
                "A profoundly vulnerable, heartbreaking, and raw emotional presence."
            )
        }

        # --- 2. MASTER WARDROBE (6 VARIAN PER KARAKTER - DAILY & NEAT HIJAB) ---
        MASTER_FAMILY_WARDROBE = {
            # --- KELOMPOK NENEK ---
            "Nenek (The Matriarch)": {
                "Daster & Bergo (Harian)": "Wearing a daily batik floral daster with short sleeves and a simple comfortable instant jersey bergo hijab covering her head and neck.",
                "Kaos Panjang & Jilbab Kaos": "Wearing a modest long-sleeved cotton house shirt paired with a simple daily instant jersey hijab in matching colors.",
                "Daster & Kerudung Lilit": "Wearing a loose batik patterned daster with a simple cotton scarf wrapped loosely and comfortably around her head as a daily hijab.",
                "Baju Kurung & Hijab Instan": "Wearing a simple Indonesian-style modest baju kurung with a comfortable jersey instant hijab for a neat daily look.",
                "Kaos Putih & Bergo Abu": "Wearing a plain white long-sleeved cotton t-shirt paired with a simple soft grey instant jersey bergo hijab.",
                "Kaos Abu-abu & Bergo Putih": "Wearing a comfortable charcoal grey long-sleeved house shirt and a clean white instant jersey hijab covering her head.",
                "Kaos Putih & Bergo Putih": "Wearing an all-white daily outfit consisting of a plain cotton long-sleeved shirt and a matching white jersey hijab for a clean, syahdu look.",
                "Kaos Abu & Bergo Hitam": "Wearing a light grey modest long-sleeved t-shirt with a contrasting black instant jersey hijab for a simple everyday appearance."
            },
            "Nenek Arum (The Grace)": {
                "Daster & Bergo (Harian)": "Wearing a daily batik floral daster with short sleeves and a simple comfortable instant jersey bergo hijab covering her head and neck.",
                "Kaos Panjang & Jilbab Kaos": "Wearing a modest long-sleeved cotton house shirt paired with a simple daily instant jersey hijab in matching colors.",
                "Daster & Kerudung Lilit": "Wearing a loose batik patterned daster with a simple cotton scarf wrapped loosely and comfortably around her head as a daily hijab.",
                "Baju Kurung & Hijab Instan": "Wearing a simple Indonesian-style modest baju kurung with a comfortable jersey instant hijab for a neat daily look.",
                "Kaos Putih & Bergo Abu": "Wearing a plain white long-sleeved cotton t-shirt paired with a simple soft grey instant jersey bergo hijab.",
                "Kaos Abu-abu & Bergo Putih": "Wearing a comfortable charcoal grey long-sleeved house shirt and a clean white instant jersey hijab covering her head.",
                "Kaos Putih & Bergo Putih": "Wearing an all-white daily outfit consisting of a plain cotton long-sleeved shirt and a matching white jersey hijab for a clean, syahdu look.",
                "Kaos Abu & Bergo Hitam": "Wearing a light grey modest long-sleeved t-shirt with a contrasting black instant jersey hijab for a simple everyday appearance."
            },
            "Nenek Sumi (The Wise)": {
                "Daster & Bergo (Harian)": "Wearing a daily batik floral daster with short sleeves and a simple comfortable instant jersey bergo hijab covering her head and neck.",
                "Kaos Panjang & Jilbab Kaos": "Wearing a modest long-sleeved cotton house shirt paired with a simple daily instant jersey hijab in matching colors.",
                "Daster & Kerudung Lilit": "Wearing a loose batik patterned daster with a simple cotton scarf wrapped loosely and comfortably around her head as a daily hijab.",
                "Baju Kurung & Hijab Instan": "Wearing a simple Indonesian-style modest baju kurung with a comfortable jersey instant hijab for a neat daily look.",
                "Kaos Putih & Bergo Abu": "Wearing a plain white long-sleeved cotton t-shirt paired with a simple soft grey instant jersey bergo hijab.",
                "Kaos Abu-abu & Bergo Putih": "Wearing a comfortable charcoal grey long-sleeved house shirt and a clean white instant jersey hijab covering her head.",
                "Kaos Putih & Bergo Putih": "Wearing an all-white daily outfit consisting of a plain cotton long-sleeved shirt and a matching white jersey hijab for a clean, syahdu look.",
                "Kaos Abu & Bergo Hitam": "Wearing a light grey modest long-sleeved t-shirt with a contrasting black instant jersey hijab for a simple everyday appearance."
            },
            "Nenek Lastri (The Devotion)": {
                "Daster & Bergo (Harian)": "Wearing a daily batik floral daster with short sleeves and a simple comfortable instant jersey bergo hijab covering her head and neck.",
                "Kaos Panjang & Jilbab Kaos": "Wearing a modest long-sleeved cotton house shirt paired with a simple daily instant jersey hijab in matching colors.",
                "Daster & Kerudung Lilit": "Wearing a loose batik patterned daster with a simple cotton scarf wrapped loosely and comfortably around her head as a daily hijab.",
                "Baju Kurung & Hijab Instan": "Wearing a simple Indonesian-style modest baju kurung with a comfortable jersey instant hijab for a neat daily look.",
                "Kaos Putih & Bergo Abu": "Wearing a plain white long-sleeved cotton t-shirt paired with a simple soft grey instant jersey bergo hijab.",
                "Kaos Abu-abu & Bergo Putih": "Wearing a comfortable charcoal grey long-sleeved house shirt and a clean white instant jersey hijab covering her head.",
                "Kaos Putih & Bergo Putih": "Wearing an all-white daily outfit consisting of a plain cotton long-sleeved shirt and a matching white jersey hijab for a clean, syahdu look.",
                "Kaos Abu & Bergo Hitam": "Wearing a light grey modest long-sleeved t-shirt with a contrasting black instant jersey hijab for a simple everyday appearance."
            },

            # --- KELOMPOK GADIS ---
            "Gadis Desa (The Natural)": {
                "Kaos Putih & Pashmina Abu": "Wearing a trendy white long-sleeved oversized cotton t-shirt paired with a soft grey pashmina shawl wrapped stylishly around her head.",
                "Kaos Abu & Hijab Putih": "Wearing a fresh light grey long-sleeved t-shirt with a clean white square hijab neatly tucked and pinned under her chin.",
                "Hoodie Putih & Hijab Abu": "Wearing a comfortable white oversized hoodie and a simple grey jersey hijab tucked inside the collar for a modern modest look.",
                "Kaos Abu & Pashmina Hitam": "Wearing a charcoal grey long-sleeved shirt with a black pashmina loosely draped around her shoulders and head for a casual aesthetic.",
                "Daster Putih & Bergo Abu": "Wearing a modern white cotton homedress with subtle lace details paired with a simple soft grey instant jersey hijab.",
                "Daster Abu & Pashmina Putih": "Wearing a comfortable light grey floral patterned daster and a white pashmina loosely wrapped around her head for a fresh home look.",
                "Kaos Panjang Putih & Rok Abu": "Wearing a plain white long-sleeved t-shirt tucked into a long grey flowy skirt with a matching grey jersey hijab.",
                "Homedress Abu & Hijab Putih": "Wearing a stylish charcoal grey homedress with long sleeves and a clean white square hijab neatly pinned, looking fresh and happy."
            },
            "Gadis Rumi (The Dreamer)": {
                "Kaos Putih & Pashmina Abu": "Wearing a trendy white long-sleeved oversized cotton t-shirt paired with a soft grey pashmina shawl wrapped stylishly around her head.",
                "Kaos Abu & Hijab Putih": "Wearing a fresh light grey long-sleeved t-shirt with a clean white square hijab neatly tucked and pinned under her chin.",
                "Hoodie Putih & Hijab Abu": "Wearing a comfortable white oversized hoodie and a simple grey jersey hijab tucked inside the collar for a modern modest look.",
                "Kaos Abu & Pashmina Hitam": "Wearing a charcoal grey long-sleeved shirt with a black pashmina loosely draped around her shoulders and head for a casual aesthetic.",
                "Daster Putih & Bergo Abu": "Wearing a modern white cotton homedress with subtle lace details paired with a simple soft grey instant jersey hijab.",
                "Daster Abu & Pashmina Putih": "Wearing a comfortable light grey floral patterned daster and a white pashmina loosely wrapped around her head for a fresh home look.",
                "Kaos Panjang Putih & Rok Abu": "Wearing a plain white long-sleeved t-shirt tucked into a long grey flowy skirt with a matching grey jersey hijab.",
                "Homedress Abu & Hijab Putih": "Wearing a stylish charcoal grey homedress with long sleeves and a clean white square hijab neatly pinned, looking fresh and happy."
            },
            "Gadis Melati (The Fresh)": {
                "Kaos Putih & Pashmina Abu": "Wearing a trendy white long-sleeved oversized cotton t-shirt paired with a soft grey pashmina shawl wrapped stylishly around her head.",
                "Kaos Abu & Hijab Putih": "Wearing a fresh light grey long-sleeved t-shirt with a clean white square hijab neatly tucked and pinned under her chin.",
                "Hoodie Putih & Hijab Abu": "Wearing a comfortable white oversized hoodie and a simple grey jersey hijab tucked inside the collar for a modern modest look.",
                "Kaos Abu & Pashmina Hitam": "Wearing a charcoal grey long-sleeved shirt with a black pashmina loosely draped around her shoulders and head for a casual aesthetic.",
                "Daster Putih & Bergo Abu": "Wearing a modern white cotton homedress with subtle lace details paired with a simple soft grey instant jersey hijab.",
                "Daster Abu & Pashmina Putih": "Wearing a comfortable light grey floral patterned daster and a white pashmina loosely wrapped around her head for a fresh home look.",
                "Kaos Panjang Putih & Rok Abu": "Wearing a plain white long-sleeved t-shirt tucked into a long grey flowy skirt with a matching grey jersey hijab.",
                "Homedress Abu & Hijab Putih": "Wearing a stylish charcoal grey homedress with long sleeves and a clean white square hijab neatly pinned, looking fresh and happy."
            },
            "Gadis Anisa (The Modest)": {
                "Kaos Putih & Pashmina Abu": "Wearing a trendy white long-sleeved oversized cotton t-shirt paired with a soft grey pashmina shawl wrapped stylishly around her head.",
                "Kaos Abu & Hijab Putih": "Wearing a fresh light grey long-sleeved t-shirt with a clean white square hijab neatly tucked and pinned under her chin.",
                "Hoodie Putih & Hijab Abu": "Wearing a comfortable white oversized hoodie and a simple grey jersey hijab tucked inside the collar for a modern modest look.",
                "Kaos Abu & Pashmina Hitam": "Wearing a charcoal grey long-sleeved shirt with a black pashmina loosely draped around her shoulders and head for a casual aesthetic.",
                "Daster Putih & Bergo Abu": "Wearing a modern white cotton homedress with subtle lace details paired with a simple soft grey instant jersey hijab.",
                "Daster Abu & Pashmina Putih": "Wearing a comfortable light grey floral patterned daster and a white pashmina loosely wrapped around her head for a fresh home look.",
                "Kaos Panjang Putih & Rok Abu": "Wearing a plain white long-sleeved t-shirt tucked into a long grey flowy skirt with a matching grey jersey hijab.",
                "Homedress Abu & Hijab Putih": "Wearing a stylish charcoal grey homedress with long sleeves and a clean white square hijab neatly pinned, looking fresh and happy."
            },

            # --- KELOMPOK KAKEK ---
            "Kakek (The Wise)": {
                "Kaos Putih & Peci Hitam": "Wearing a simple plain white cotton t-shirt with a classic black velvet Peci (songkok) on his head for a humble daily look.",
                "Baju Koko Abu & Peci": "Wearing a daily light grey Baju Koko with subtle embroidery on the chest and a neat black Peci on his head.",
                "Kaos Abu & Sarung Putih": "Wearing a comfortable charcoal grey long-sleeved t-shirt paired with a white patterned sarong wrapped around his waist.",
                "Kemeja Putih & Peci": "Wearing an old, well-worn short-sleeved white button-down shirt and a classic black Peci, looking dignified and fatherly."
            },
            "Kakek Wiryo (The Artisan)": {
                "Kaos Putih & Peci Hitam": "Wearing a simple plain white cotton t-shirt with a classic black velvet Peci (songkok) on his head for a humble daily look.",
                "Baju Koko Abu & Peci": "Wearing a daily light grey Baju Koko with subtle embroidery on the chest and a neat black Peci on his head.",
                "Kaos Abu & Sarung Putih": "Wearing a comfortable charcoal grey long-sleeved t-shirt paired with a white patterned sarong wrapped around his waist.",
                "Kemeja Putih & Peci": "Wearing an old, well-worn short-sleeved white button-down shirt and a classic black Peci, looking dignified and fatherly."
            },
            "Kakek Joyo (The Farmer)": {
                "Kaos Putih & Peci Hitam": "Wearing a simple plain white cotton t-shirt with a classic black velvet Peci (songkok) on his head for a humble daily look.",
                "Baju Koko Abu & Peci": "Wearing a daily light grey Baju Koko with subtle embroidery on the chest and a neat black Peci on his head.",
                "Kaos Abu & Sarung Putih": "Wearing a comfortable charcoal grey long-sleeved t-shirt paired with a white patterned sarong wrapped around his waist.",
                "Kemeja Putih & Peci": "Wearing an old, well-worn short-sleeved white button-down shirt and a classic black Peci, looking dignified and fatherly."
            },
            "Kakek Usman (The Silent)": {
                "Kaos Putih & Peci Hitam": "Wearing a simple plain white cotton t-shirt with a classic black velvet Peci (songkok) on his head for a humble daily look.",
                "Baju Koko Abu & Peci": "Wearing a daily light grey Baju Koko with subtle embroidery on the chest and a neat black Peci on his head.",
                "Kaos Abu & Sarung Putih": "Wearing a comfortable charcoal grey long-sleeved t-shirt paired with a white patterned sarong wrapped around his waist.",
                "Kemeja Putih & Peci": "Wearing an old, well-worn short-sleeved white button-down shirt and a classic black Peci, looking dignified and fatherly."
            }
        }

        # --- 3. MASTER BAHAN (ARCHITECTURAL PRECISION: 90% PROGRESS INTERACTIVE) ---
        MASTER_KONTEN_ALL = {
            "🕌 Miniatur Masjid": {
                "Crystal Candy (Bubblegum Pop)": "A cute mosque diorama made of glossy translucent candy-like materials in pastel pink and turquoise, featuring a sparkling diamond-texture dome filled with twinkling fiber-optic star lights and warm yellow glowing crescent moons, while the entrance arches are lined with flickering multi-colored fairy lights that create a magical toy atmosphere.",
                "Kaleng Alumunium (Metallic Neon)": "A detailed miniature mosque constructed from industrial-grade aluminum plates and recycled metallic structures, featuring a dome and minarets with embossed Arabic calligraphy glowing with pulsing RGB neon, its metallic walls reflecting brilliant neon lights throughout the structure, and a courtyard containing metallic wire sculptures and paths of shimmering silver ore.", 
                "Stik Es Krim & Kristal (Rainbow LED)": "A detailed miniature mosque constructed from orderly structural wooden ice cream sticks, featuring embossed gold calligraphy and rainbow LED lighting glowing through large crystal-bead windows, with a yard decorated with white sand and flower gardens.",
                "Kardus & Barang Bekas (Electric Glow)": "A detailed miniature mosque constructed from orderly layers of recycled industrial cardboard and heavy electronic components, featuring glowing neon calligraphy on the walls and towering multi-colored fiber optic light installations on the minarets.",
                "Lego Warna-Warni (Brick Paradise)": "A detailed miniature mosque constructed from interlocking colorful LEGO bricks, featuring a central dome made of glossy vibrant bricks in red, blue, and yellow, with pulsing RGB LED strips glowing through translucent brick windows and tracing the minarets.",
                "Kulit Jeruk & Buah (Citrus Fresh)": "A detailed miniature mosque constructed from sun-dried citrus zest plates, featuring intricate patterns carved into the organic facade with powerful warm LED installations glowing from the interior, surrounded by a yard of spice-shaped sculptures.",
                "Batok Kelapa & Nanas (Tropical Fruit)": "A detailed miniature mosque constructed from polished coconut shell structures and textured pineapple skin plates, featuring a golden dome and green LED installations with a yard decorated with exotic stone seeds.",
                "Kulit Semangka (Eco-Green)": "A detailed miniature mosque constructed from emerald-green watermelon rinds, featuring arched windows with glowing emerald LED installations and a courtyard with stone boulders and water lily lakes.",
                "Emas & Marmer (Royal Palace)": "A detailed miniature mosque constructed from gold-plated segments and polished white marble slabs, featuring 24k gold leaf calligraphy, emerald-encrusted windows, and a courtyard of smooth obsidian stone with golden fountains.",
                "Kristal & Berlian (Diamond Glow)": "A detailed miniature mosque constructed from Swarovski-style crystalline structures and silver filigree, featuring blue LED installations refracting through glass facets and a courtyard decorated with crystal floral sculptures.",
                "Kayu Jati & Gading (Imperial Heritage)": "A detailed miniature mosque constructed from dark aged teak wood with ivory-white inlays, featuring hand-carved motifs and warm amber LED backlighting against a velvet-textured landscape.",
                "Safir & Platinum (Futuristic Luxury)": "A detailed miniature mosque constructed from platinum-finished metal segments and deep sapphire-colored glass panels, featuring neon-white LED installations along the arches and domes, with a courtyard decorated with polished chrome boulders and futuristic glass trees.",
                "Serabut Kelapa & LED Rainbow (Rustic-Neon)": "A detailed miniature mosque constructed from woven golden-brown coconut fiber, featuring gold calligraphy and vibrant multi-color LED installations in cyan, magenta, and lime glowing through the fibrous walls, with a courtyard of white sea shell paths.",
                "Mosaik Kulit Buah & LED Glow (Citrus Imperial)": "A detailed miniature mosque featuring mosaic patterns made of dried orange and lemon peels, with emerald-green LED installations glowing through arched windows and gold-leaf details on the minarets.",
                "Kelopak Bunga & LED Sapphire (Floral Majesty)": "A detailed miniature mosque constructed from structural segments resembling deep-red rose petals, featuring sapphire-blue LED installations hidden within the floral layers and gold-embossed calligraphy on a black stone base.",
                "Batok Kelapa & LED Crystal (Tropical Diamond)": "A detailed miniature mosque constructed from polished dark coconut shells, featuring domes with sparkling rainbow LED fiber optics and gold-painted calligraphy, with a courtyard of white sand and fiber-optic palm trees.",
                "Daun Kering (LED Warm)": "A detailed miniature mosque constructed from structural segments of dried organic leaves, featuring warm LED installations integrated into the structure and a yard with dry grass landscapes and stone boulders.",
                "Kayu (LED Amber)": "A detailed miniature mosque constructed from woven bamboo structures, featuring amber-colored LED installations that cast dramatic shadows through the fibrous walls, with a courtyard of ancient trees and stone pathways.",
                "Daun Pisang (Traditional)": "A detailed miniature mosque crafted from fresh and dried banana leaf segments, featuring yellow LED installations glowing through organic green and brown textures, with a courtyard of banana tree structures and mossy landscapes.",
                "Buah Melon (Carved Art)": "A detailed miniature mosque featuring walls with green melon rind patterns, glowing with lime-green LED installations from the interior, with a courtyard decorated with floral stone carvings and a mint-green reflection lake.",
                "Buah Naga (Exotic Pink)": "A detailed miniature mosque featuring a vibrant pink scale-textured facade like a dragon fruit, with magenta LED installations highlighting the textures and a yard of pinkish sand.",
                "Koran Bekas (Paper Craft)": "A detailed miniature mosque built from recycled newsprint segments showing hints of printed typography, illuminated by RGB LED installations, with a yard of paper-textured tree structures.",
                "Pecahan Kaca (Mosaic)": "A detailed miniature mosque constructed from shimmering mosaic glass panels, featuring cool-blue and white LED installations creating a sparkling crystalline effect, with a courtyard of translucent glass boulders.",
                "Botol Bekas (Recycled Plastic)": "A detailed miniature mosque constructed from translucent recycled polymers and geometric plastic caps, featuring vibrant multi-color RGB LED installations glowing through the plastic facades.",
                "Kristal (LED Neon)": "A detailed miniature mosque constructed from glistening crystalline structures, featuring neon blue and purple LED installations glowing through glass-like walls, with a base of crystal boulders.",
                "Pasir (Sand Art)": "A detailed miniature mosque sculpted from fine golden sand, featuring smooth domes and sharp architectural edges illuminated by amber LED installations on a desert-themed landscape.",
                "Bunga Matahari (Yellow Glow)": "A detailed miniature mosque covered in vibrant yellow sunflower petals, featuring a dark seeded dome resembling a sunflower center and golden-yellow LED installations.",
                "Jerami (Rustic Straw)": "A detailed miniature mosque constructed from woven golden straw and hay, featuring flickering warm yellow LED installations inside and a courtyard with haystack structures.",
                "Roti (Bread Craft)": "A detailed miniature mosque constructed from various baked bread and golden-brown crust panels, featuring warm orange LED installations glowing through the windows and golden-grain pathways.",
                "Serut Kayu (Wood Shavings)": "A detailed miniature mosque featuring walls made of curly light-colored timber shavings, illuminated by amber LED installations glowing through the curly textures, with a courtyard of wooden benches and pine tree structures.",
                "Cangkang Telur (Mosaic Shell)": "A detailed miniature mosque constructed from white and brown eggshell mosaic panels, glowing with white LED installations reflecting off the shell textures, featuring stone-paved pathways in the courtyard.",
                "Bunga & Daun (Floral Garden)": "A detailed miniature mosque covered in colorful blooming flowers and fresh green leaves, glowing with multi-color RGB LED installations, featuring a floral archway in the yard.",
                "Kayu Jati & Daun (Forest Rustic)": "A detailed miniature mosque built from dark polished teak wood with fresh green leaf patterns on the dome, illuminated by warm amber LED installations, with a yard of mossy boulders and forest ferns.",
                "Bambu & Janur (Traditional Art)": "A detailed miniature mosque constructed from yellow bamboo pillars and woven young coconut leaf (janur) segments, glowing with yellow LED installations through the intricate weaving.",
                "Kulit Jagung & Biji-bijian (Harvest)": "A detailed miniature mosque crafted from dried corn husks and seed mosaic patterns, glowing with warm orange LED installations, with a courtyard of harvest-themed structures.",
                "Perca Kain & Benang (Textile Craft)": "A detailed miniature mosque constructed from batik fabric patterns and yarn embroidery, glowing with RGB LED lights through the textile textures on a felt-textured landscape.",
                "Pelepah Pisang & Lidi (Village Vibes)": "A detailed miniature mosque constructed from dried banana midribs and coconut leaf sticks (lidi), glowing with warm amber LED lights through the fibrous walls.",
                "Donat (Glazed & Sprinkle)": "A detailed miniature mosque constructed from stacked glazed donuts with colorful sprinkles and glossy icing textures, glowing with warm pink LED installations.",
                "Permen Warna-Warni (Hard Candy)": "A detailed miniature mosque constructed from colorful hard candies and lollipop-inspired pillars, featuring a glossy crystalline texture reflecting multi-color RGB LED installations.",
                "Permen Yupi (Gummy Texture)": "A detailed miniature mosque crafted from translucent gummy materials and gelatinous forms, glowing with RGB LED installations shining through the translucent gummy facades.",
                "Jelly & Puding (Translucent)": "A detailed miniature mosque constructed from translucent colorful jelly segments and structural pudding blocks, featuring neon LED installations glowing through the translucent walls.",
                "Cokelat & Biskuit (Choco-Art)": "A detailed miniature mosque constructed from dark and milk chocolate segments with biscuit-textured roofing, illuminated by golden LED installations on a cocoa-powdered landscape.",
                "Marshmallow (Soft Cloud)": "A detailed miniature mosque constructed from white and pastel marshmallow-textured segments, featuring cotton-candy botanical structures in the yard and glowing with ethereal RGB LED installations.",
                "Biji Kopi (Dark Aroma)": "A detailed miniature mosque constructed from dark roasted coffee beans, featuring a rich brown facade illuminated by warm orange LED installations glowing through the bean-textured walls.",
                "Bungkus Snack (Snack Wrap Art)": "A detailed miniature mosque featuring a vibrant mosaic facade made of recycled snack packaging wrappers with colorful graphics, illuminated by dynamic multi-color RGB LED installations.",
                "Sabun (Crystal Soap Art)": "A detailed miniature mosque constructed from translucent soap segments resembling colorful gemstones in green, blue, and purple, featuring shifting multi-color internal reflections from RGB LED lights.",
                "Karet Gelang (Elastic Rubber Art)": "A detailed miniature mosque constructed from intertwined networks of colorful rubber bands, featuring complex geometric patterns glowing with dynamic multi-color RGB LED lights woven through the structure.",
                "Masjid Rujak Buah (Tropical Harvest)": "A detailed miniature mosque featuring a hollowed papaya dome with dark seeds, minarets made of stacked guavas and grapes, and starfruit-slice windows glowing with lime-green and amber LED.",
                "Pepaya (Orange Oasis)": "A detailed miniature mosque constructed from orange papaya flesh, featuring a hollowed papaya dome with glistening seeds as ornaments and walls glowing with warm amber LED.",
                "Belimbing (Star-Light Palace)": "A detailed miniature mosque constructed from translucent starfruit slices, featuring star-shaped windows and a geometric facade glowing with lime-green and golden LED installations.",
                "Anggur (Purple Crystal)": "A detailed miniature mosque featuring spherical grape domes resembling gemstones and clusters of deep-purple grapes that refract violet and white LED light from the interior.",
                "Durian (Spiky Fortress)": "A detailed miniature mosque constructed from thorny durian husks with creamy-textured interior walls, illuminated by warm yellow LED installations highlighting the spiky facade.",
                "Manggis (Imperial Purple)": "A detailed miniature mosque featuring a deep-purple mangosteen rind exterior and white fruit-segment central domes, illuminated by cool-white LED from the interior.",
                "Ijuk (Rustic-Traditional)": "A detailed miniature mosque constructed from woven black sugar palm fiber (ijuk) and wooden elements, with warm amber LED light glowing through the fibrous weaving.",
                "Padi (Golden Harvest)": "A detailed miniature mosque crafted from dried rice stalks (padi), featuring golden textured walls and arched entrances illuminated by warm orange LED installations.",
                "Beras (Pristine White)": "A detailed miniature mosque constructed from pristine white rice grains, featuring smooth domes and architectural edges made of rice grain mosaics reflecting cool white LED light.",
                "Kacang Ijo (Lime-Green Glow)": "A detailed miniature mosque constructed from polished green mung beans, featuring a bio-architectural building with powerful lime-green LED installations glowing from the interior and a mint-green reflection lake.",
                "Kacang Merah (Deep-Red Earth)": "A detailed miniature mosque constructed from deep-red kidney beans, featuring a rich red facade and warm amber LED installations glowing through the bean-textured walls and stone-paved pathways.",
                "Kristal & Berlian (Diamond Glow)": "A detailed miniature mosque constructed from Swarovski-style crystalline structures and silver filigree, featuring multi-color RGB LED installations that refract through crystal facets to create a kaleidoscope effect.",
                "Akrilik & Kaca (Modern Glow)": "A detailed miniature mosque constructed from clear and sandblasted acrylic panels, with RGB LED strips integrated within the panel gaps turning the structure into a modern light installation.",
                "Es & Salju (Frozen Aurora)": "A detailed miniature mosque sculpted from pure clear ice and packed snow, featuring dynamic multi-color RGB LED installations glowing within icy domes to create an aurora borealis effect.",
                "Permen Yupi (Gummy Texture)": "A detailed miniature mosque crafted from translucent gummy materials and gelatinous forms, with RGB LED installations glowing through the gummy facades to create a wobbly light show.",
                "Logam & Krom (Cyber-Neon)": "A detailed miniature mosque constructed from polished chrome segments, featuring dynamic neon-white and purple LED installations that reflect off the mirror-like metallic facade.",
                "Botol Plastik (Recycled Glow)": "A detailed miniature mosque constructed from layers of translucent recycled plastic bottles and water gallons, featuring multi-color RGB LED installations glowing from within like a lantern.",
                "Kaleng Bekas (Industrial Neon)": "A detailed miniature mosque constructed from stacked recycled tin cans and scrap metal cylinders, featuring neon-purple and lime-green LED installations glowing through the metallic gaps.",
                "Elektronik Bekas (Cyber-Relic)": "A detailed miniature mosque constructed from recycled circuit boards and tangled wires, with dynamic RGB LED installations tracing the electronic paths to create a pulsing machine light effect.",
                "Sedotan Plastik (Neon Pipe Art)": "A detailed miniature mosque constructed from intertwined colorful plastic straws, featuring RGB LED installations glowing through the transparent straw-tubes to create a linear light show.",
                "Kepingan CD & Tutup Botol (Rainbow Junk)": "A detailed miniature mosque constructed from mosaic patterns of recycled CDs and plastic bottle caps, featuring an iridescent shimmering effect from RGB LED installations reflecting off the metallic surfaces.",
                "Mix Daun Pisang & Serabut Kelapa (Rustic Nature)": "A detailed miniature mosque featuring a dome made of intricately layered fresh and dried banana leaf segments, with a main traditional structure and minarets constructed from woven golden-brown coconut fiber and polished dark polished teak wood structures accented, glowing intensely with powerful yellow LED installations through the leaf and fibrous walls, and a mossy green traditional landscape base.",
                "Mix Kristal & Kardus (Cyber-Eco)": "A detailed miniature mosque featuring a central dome made of shimmering Swarovski-style crystals and minarets constructed from raw industrial cardboard layers, with cool-blue LED light refracting through the crystal while warm amber LED glows through the cardboard gaps.",
                "Mix Buah Naga & Akrilik (Exotic Modern)": "A detailed miniature mosque with walls featuring the vibrant pink scale-texture of dragon fruit and a dome made of translucent sandblasted acrylic, illuminated by magenta and white LED strips tracing the organic and geometric edges.",
                "Mix Biji Kopi & Emas (Luxury Aroma)": "A detailed miniature mosque constructed from dark roasted coffee beans with 24k gold-plated arches and windows, featuring warm orange LED backlighting that highlights the bean textures and gold reflections.",
                "Mix Kulit Semangka & Kaca (Emerald Mosaic)": "A detailed miniature mosque featuring a dome of emerald-green watermelon rind and walls made of shimmering mosaic glass shards, glowing with emerald and white LED installations from the interior.",
                "Mix Botol Plastik & Kayu Jati (Recycled Heritage)": "A detailed miniature mosque featuring a dome made of translucent recycled blue plastic bottle bottoms and a main structure of dark aged teak wood, with pulsing RGB LED lights glowing through the plastic and wood carvings.",
                "Mix Permen Yupi & Sedotan (Neon Candy)": "A detailed miniature mosque constructed from translucent gummy material segments and towers made of intertwined colorful plastic straws, featuring vibrant neon-green LED light shining through the gelatinous and tubular structures.",
                "Mix Ijuk & Logam Krom (Rustic Cyber)": "A detailed miniature mosque featuring a roof of woven black sugar palm fiber (ijuk) and a facade of polished mirror-like chrome plates, with violet LED installations reflecting off the metal and glowing through the fiber.",
                "Mix Daun Kering & Akrilik (Pearl Oasis)": "A detailed miniature mosque featuring a dome made of finely crushed white eggshell mosaic and walls constructed from crystal-clear acrylic panels, illuminated by soft warm-gold LED light that refracts through the acrylic while creating a shimmering mother-of-pearl effect on the eggshell textures, with a base of white polished pebbles.",
                "Mix Botol Plastik & Kayu (Recycled Heritage)": "A detailed miniature mosque featuring a dome of translucent recycled blue plastic bottle bottom segments and a traditional structure of dark aged teak wood with hand-carved motifs, glowing with cool-white LED through the plastic and warm amber LED through the wood carvings, creating a unique traditional-modern contrast.",
                "Mix Sabun & Logam (Glimmering Jewel)": "A detailed miniature mosque constructed from translucent soap segments carved into precise geometric forms resembling large colorful gemstones, with minarets made of intertwined silver-plated wire and metal filigree, illuminated by dynamic RGB LED installations that create shifting, multi-color internal reflections and a shimmering effect on the soap facade.",
                "Mix Karet Gelang & Kaca (Elastic Cyber)": "A detailed miniature mosque constructed from intertwined networks of colorful rubber bands and walls made of shimmering mosaic glass panels, glowing intensely with vibrant multi-color RGB LED lights woven through the elastic structure and reflecting off the glass textures, creating a spectacular cyberpunk light show.",
                "Mix Sedotan & Biji-bijian (Geometric Harvest)": "A detailed miniature mosque constructed from intertwined colorful plastic straws and intricate seed mosaic patterns of corn, rice, and beans, featuring a dome and minarets that glow with dynamic multi-color RGB LED light shining through the tubular and organic structures.",
                "Mix Perca Kain & Benang (Textile Craft)": "A detailed miniature mosque constructed from batik fabric patterns and yarn embroidery installations, glowing with dynamic multi-color RGB LED lights intensely through the textile textures on a felt-textured landscape with silver-plated perimeter walls.",
                "Mix Lidi & Koran (Rustic Paper)": "A detailed miniature mosque featuring a dome and minarets constructed from thousands of vertical coconut leaf sticks (lidi) bundled together, with walls made of orderly layers of recycled newsprint showing hints of printed typography, illuminated by warm amber LED light glowing intensely through the gaps between the sticks and the paper textures.",
                "Mix Lidi & Daun Kering (Autumn Village)": "A detailed miniature mosque featuring a dome of layered dried brown leaves and a main structure constructed from woven coconut leaf sticks (lidi) and dark wood, with internal warm yellow LED installations casting dramatic linear shadows through the lidi walls onto a dry-grass landscape.",
                "Mix Lidi & Kardus (Industrial Craft)": "A detailed miniature mosque constructed from industrial-grade cardboard layers with a facade and arched entrances accented by intricate patterns of coconut leaf sticks (lidi), illuminated by pulsing orange LED installations that highlight the corrugated cardboard edges and the fibrous sticks.",
                "Mix Lidi & Batok Kelapa (Tropical Native)": "A detailed miniature mosque featuring a dome of polished dark coconut shells and minarets made of bundled coconut leaf sticks (lidi), with warm amber LED installations glowing through the coconut fiber and reflecting off the smooth shell surfaces.",
                "Mix Lidi & Kain Perca (Textile Rustic)": "A detailed miniature mosque constructed from woven coconut leaf sticks (lidi) as the main frame and walls covered in colorful batik fabric patches, with multi-color LED installations glowing from the interior, shining through both the fabric and the stick lattice.",
                "Mix Lidi & Biji-bijian (Seed Mosaic)": "A detailed miniature mosque featuring walls made of green mung bean and red kidney bean mosaics, with a dome and minarets intricately constructed from coconut leaf sticks (lidi), illuminated by lime-green and amber LED installations.",
                "Mix Serabut Kelapa & Daun (Rustic Nature)": "A detailed miniature mosque featuring a dome made of intricately layered fresh and dried banana leaf segments, with a main traditional structure and minarets constructed from woven golden-brown coconut fiber and polished dark polished teak wood structures accented, glowing intensely with powerful yellow LED installations through the leaf and fibrous walls, and a mossy green traditional landscape base.",
                "Mix Daun Kering & Koran (Typography Gold)": "A detailed miniature mosque constructed from orderly layers of dried newsprint segments showing hints of printed black typography, with a dome and minarets made of finely crushed white eggshell mosaic plated elements, illuminated by internal amber LED light glowing through the paper gaps and creating a mother-of-pearl effect on the eggshells.",
                "Mix Botol Plastik & Serabut Kelapa (Recycled Heritage)": "A detailed miniature mosque featuring a dome of translucent recycled blue plastic bottle bottom segments and a traditional structure constructed from woven golden-brown coconut fiber and dark wood, glowing with cool-white LED through the plastic and warm amber LED through the fibrous walls.",
                "Mix Koran & Sedotan (Geometric Typography)": "A detailed miniature mosque constructed from orderly layers of dried newsprint segments showing hints of printed black typography, with minarets made of intertwined colorful plastic straws, illuminated by pulsing multi-color RGB LED installations that trace the paper gaps and tubular structures.",
                "Mix Serabut Kelapa & Kaca (Glimmering Rustic)": "A detailed miniature mosque constructed from woven golden-brown coconut fiber and walls made of shimmering mosaic glass panels, with dynamic multi-color RGB LED installations woven through the elastic structure and reflecting off the glass textures, creating a spectacular cyberpunk light show.",
                "Mix Daun Kering & Kain Perca (Textile Rustic)": "A detailed miniature mosque featuring a dome of layered dried brown leaves and a main structure covered in colorful batik fabric patches, with multi-color LED installations glowing from the interior, shining through both the leaf and fabric lattice.",
                "Mix Botol Plastik & Koran (Recycled Craft)": "A detailed miniature mosque featuring a dome made of translucent recycled blue plastic bottle bottoms and a main structure of dark aged teak wood constructed from orderly layers of dried newsprint segments showing hints of printed black typography, with pulsing RGB LED lights glowing through the plastic and paper gaps.",
                "Mix Sedotan & Biji-bijian (Geometric Harvest)": "A detailed miniature mosque constructed from intertwined colorful plastic straws and intricate seed mosaic patterns of corn, rice, and beans, featuring a dome and minarets that glow with dynamic multi-color RGB LED light shining through the tubular and organic structures.",
                "Mix Kardus & Serabut Kelapa (Cyber-Rustic)": "A monumental architectural diorama mosque constructed from massive, orderly layers of recycled industrial cardboard and heavy electronics, featuring intricate ijuk-weaving patterns on the dome and minarets. Thousands of dynamic cool-white and subtle gold LED installations glow intensely through the new pillar materials, turning the monumental complex into a gigantic, mystical light sculpture that reflects intensely off the colossal marble structures and the sparkling Kiswah. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The vast, monumental courtyard derived from image_12.png contains monumental metallic wire sculptures and paths of shimmering silver ore. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The scene is captured with a low-angle macro cinematic lens executing a slow, deep orbital tracking shot, making the massive central Kaaba bener-bener menonjol and the concentric pillar structures look heroic, titanic, and utterly breathtaking, maintaining perfect architectural integrity within the mystical exhibit space. The focus is deep, rendering all details from the black Kaaba to the intricate organic pillar textures and the integrated LEDs with crystal-clear precision. No pilgrims or traditional minarets are visible; the focus is entirely on the monumental glowing Kaaba and the surrounding four concentric pillar structures themselves as a mystical exhibit.",
                "Mix Padi & Lidi (Golden Harvest)": "A monumental architectural diorama mosque crafted from massive, orderly structural segments made of gigantic dried rice stalks (padi), with minarets constructed from thousands of vertical coconut leaf sticks (lidi) bundled together. Dynamic cool-white and subtle gold LED installations glow intensely through the new pillar materials, turning the monumental complex into a gigantic, mystical light sculpture that reflects intensely off the colossal marble structures and the sparkling Kiswah. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The vast, monumental courtyard derived from image_12.png contains monumental metallic wire sculptures and paths of shimmering silver ore. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The scene is captured with a low-angle macro cinematic lens executing a slow, deep orbital tracking shot, making the massive central Kaaba bener-bener menonjol and the concentric pillar structures look heroic, titanic, and utterly breathtaking, maintaining perfect architectural integrity within the mystical exhibit space. The focus is deep, rendering all details from the black Kaaba to the intricate organic pillar textures and the integrated LEDs with crystal-clear precision. No pilgrims or traditional minarets are visible; the focus is entirely on the monumental glowing Kaaba and the surrounding four concentric pillar structures themselves as a mystical exhibit.",
                "Mix Koran & Tutup Botol (Pop-Art Kaleidoscope)": "A monumental architectural diorama mosque constructed from massive, orderly structural segments made of colorful recycled snack packaging wrappers and gigantic printed typography across its monumental facade, with the dome and minarets intricately constructed from coconut leaf sticks (lidi) and dark wood. Integrated dynamic cool-white and subtle gold LED installations glow intensely through the new pillar materials, turning the monumental complex into a gigantic, mystical light sculpture that reflects intensely off the colossal marble structures and the sparkling Kiswah. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The vast, monumental courtyard derived from image_12.png contains monumental metallic wire sculptures and paths of shimmering silver ore. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The scene is captured with a low-angle macro cinematic lens executing a slow, deep orbital tracking shot, making the massive central Kaaba bener-bener menonjol and the concentric pillar structures look heroic, titanic, and utterly breathtaking, maintaining perfect architectural integrity within the mystical exhibit space. The focus is deep, rendering all details from the black Kaaba to the intricate organic pillar textures and the integrated LEDs with crystal-clear precision. No pilgrims or traditional minarets are visible; the focus is entirely on the monumental glowing Kaaba and the surrounding four concentric pillar structures themselves as a mystical exhibit.",
                "Mix Roti & Serabut Kelapa (Glazed Traditional)": "A monumental architectural diorama mosque constructed from massive, orderly structural segments of stacked glazed donut forms with gigantic colorful sprinkles and glossy icing textures, presented as a large-scale museum exhibit. The colossal dessert structure glows with powerful warm pink LED installations intensely, with the main traditional structure constructed from woven golden-brown coconut fiber and polished dark polished teak wood structures accented. Integrated dynamic cool-white and subtle gold LED installations glow intensely through the new pillar materials, turning the monumental complex into a gigantic, mystical light sculpture that reflects intensely off the colossal marble structures and the sparkling Kiswah. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The vast, monumental courtyard derived from image_12.png contains monumental metallic wire sculptures and paths of shimmering silver ore. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The scene is captured with a low-angle macro cinematic lens executing a slow, deep orbital tracking shot, making the massive central Kaaba bener-bener menonjol and the concentric pillar structures look heroic, titanic, and utterly breathtaking, maintaining perfect architectural integrity within the mystical exhibit space. The focus is deep, rendering all details from the black Kaaba to the intricate organic pillar textures and the integrated LEDs with crystal-clear precision. No pilgrims or traditional minarets are visible; the focus is entirely on the monumental glowing Kaaba and the surrounding four concentric pillar structures themselves as a mystical exhibit.",
                "Mix Permen & Koran (Typography Gummy)": "A monumental architectural diorama mosque constructed from massive, orderly structural segments of colorful recycled snack packaging wrappers with gigantic brand graphics, illuminated by dynamic cool-white and subtle gold LED installations glowing intensely through the new pillar materials, turning the monumental complex into a gigantic, mystical light sculpture that reflects intensely off the colossal marble structures and the sparkling Kiswah. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The vast, monumental courtyard derived from image_12.png contains monumental metallic wire sculptures and paths of shimmering silver ore. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The scene is captured with a low-angle macro cinematic lens executing a slow, deep orbital tracking shot, making the massive central Kaaba bener-bener menonjol and the concentric pillar structures look heroic, titanic, and utterly breathtaking, maintaining perfect architectural integrity within the mystical exhibit space. The focus is deep, rendering all details from the black Kaaba to the intricate organic pillar textures and the integrated LEDs with crystal-clear precision. No pilgrims or traditional minarets are visible; the focus is entirely on the monumental glowing Kaaba and the surrounding four concentric pillar structures themselves as a mystical exhibit.",
                "Mix Daun Pisang & Lidi (Rustic Tradition)": "A monumental architectural diorama mosque crafted from massive, orderly structural segments resembling fresh and dried banana leaves, with the dome made of intricately layered fresh and dried banana leaf segments and minarets constructed from thousands of vertical coconut leaf sticks (lidi) bundled together. Dynamic cool-white and subtle gold LED installations glow intensely through the new pillar materials, turning the monumental complex into a gigantic, mystical light sculpture that reflects intensely off the colossal marble structures and the sparkling Kiswah. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The vast, monumental courtyard derived from image_12.png contains monumental metallic wire sculptures and paths of shimmering silver ore. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The scene is captured with a low-angle macro cinematic lens executing a slow, deep orbital tracking shot, making the massive central Kaaba bener-bener menonjol and the concentric pillar structures look heroic, titanic, and utterly breathtaking, maintaining perfect architectural integrity within the mystical exhibit space. The focus is deep, rendering all details from the black Kaaba to the intricate organic pillar textures and the integrated LEDs with crystal-clear precision. No pilgrims or traditional minarets are visible; the focus is entirely on the monumental glowing Kaaba and the surrounding four concentric pillar structures themselves as a mystical exhibit.",
                "Mix Kain Perca & Serabut Kelapa (Textile Rustic)": "A monumental architectural diorama mosque constructed from massive, orderly woven black sugar palm fiber (ijuk) structures, with the dome intricately covered in massive installations of colorful batik fabric patterns and gigantic yarn embroidery installations. Dynamic cool-white and subtle gold LED installations glow intensely through the new pillar materials, turning the monumental complex into a gigantic, mystical light sculpture that reflects intensely off the colossal marble structures and the sparkling Kiswah. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The vast, monumental courtyard derived from image_12.png contains monumental metallic wire sculptures and paths of shimmering silver ore. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The scene is captured with a low-angle macro cinematic lens executing a slow, deep orbital tracking shot, making the massive central Kaaba bener-bener menonjol and the concentric pillar structures look heroic, titanic, and utterly breathtaking, maintaining perfect architectural integrity within the mystical exhibit space. The focus is deep, rendering all details from the black Kaaba to the intricate organic pillar textures and the integrated LEDs with crystal-clear precision. No pilgrims or traditional minarets are visible; the focus is entirely on the monumental glowing Kaaba and the surrounding four concentric pillar structures themselves as a mystical exhibit.",
                "Mix Sedotan & Biji-bijian (Geometric Harvest)": "A monumental architectural diorama mosque constructed from massive, orderly structural segments made of gigantic dried rice stalks (padi), with minarets intricately constructed from thousands of colorful plastic straws. Dynamic cool-white and subtle gold LED installations glow intensely through the new pillar materials, turning the monumental complex into a gigantic, mystical light sculpture that reflects intensely off the colossal marble structures and the sparkling Kiswah. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The vast, monumental courtyard derived from image_12.png contains monumental metallic wire sculptures and paths of shimmering silver ore. Thousands of intricate cool-white LED lights are woven throughout the complex marble arches and the new organic textures, creating a breathtaking linear light show derived from image_8.png. The scene is captured with a low-angle macro cinematic lens executing a slow, deep orbital tracking shot, making the massive central Kaaba bener-bener menonjol and the concentric pillar structures look heroic, titanic, and utterly breathtaking, maintaining perfect architectural integrity within the mystical exhibit space. The focus is deep, rendering all details from the black Kaaba to the intricate organic pillar textures and the integrated LEDs with crystal-clear precision. No pilgrims or traditional minarets are visible; the focus is entirely on the monumental glowing Kaaba and the surrounding four concentric pillar structures themselves as a mystical exhibit.",
                "Mix Arang & Lidi (Black Charcoal)": "A detailed miniature mosque constructed from rough black charcoal blocks for the walls and thousands of vertical coconut leaf sticks (lidi) for the dome, with glowing amber LED installations flickering intensely through the porous charcoal and stick gaps.",
                "Mix Kulit Salak & Bambu (Snake-Skin Rustic)": "A detailed miniature mosque featuring a dome covered in overlapping dark brown snake-fruit (salak) skin scales and a main structure made of thin woven bamboo strips, illuminated by warm yellow LED installations that highlight the scaly and fibrous textures.",
                "Mix Kancing Baju & Benang (Button Craft)": "A detailed miniature mosque featuring walls made of thousands of interlocking colorful plastic buttons and a dome intricately wrapped in vibrant embroidery yarn, with multi-color RGB LED lights glowing through the button holes and translucent materials.",
                "Mix Daun Jati Kering & Serabut (Brown Autumn)": "A detailed miniature mosque constructed from large dried teak leaves for the roof and golden-brown coconut fiber for the walls, featuring internal warm orange LED installations that cast dramatic organic shadows through the fibrous textures.",
                "Mix Sedotan Hitam & Silver (Cyber Industrial)": "A detailed miniature mosque built from thousands of matte black plastic straws bundled together, featuring dome accents made of recycled silver-colored snack foil, illuminated by neon-purple and white LED light tracing the tubular lines.",
                "Mix Biji Jagung & Kulit Jagung (Harvest Gold)": "A detailed miniature mosque featuring a dome made of a golden corn-cob mosaic and walls wrapped in dried corn husks, with warm-white LED installations glowing intensely through the translucent husks and seed gaps.",
                "Mix Koran & Tutup Galon (Recycled Blue)": "A detailed miniature mosque featuring a dome made of translucent blue plastic gallon caps and walls of layered recycled newsprint, with cool-white LED installations glowing through the blue plastic and the printed typography textures.",
                "Mix Sapu Lidi & Tali Rami (Ethnic Fiber)": "A detailed miniature mosque constructed from bundled coconut leaf sticks (lidi) and wrapped in thick hemp rope, featuring a rustic dome with internal warm amber LED installations that highlight the complex textures of the rope and sticks."
            },
            # --- 3. MASTER KONTEN (🌍 WORLD MOSQUE DIORAMA - CRAFT SCALE EDITION) ---
            "🌍 Diorama Masjid": {
                "Masjidil Haram Ka'bah": "An ultra-realistic miniature diorama of Masjidil Haram featuring a central Ka'bah made of matte black cloth with gold-threaded calligraphy embroidery, a Mataf courtyard of polished white marble resin that reflects thousands of tiny warm-white and cool-white LED pixels, and miniature grain-sized pilgrims to establish the tiny scale with glowing green fiber-optic minaret tips.",
                "Kota Botol & Kaleng (Recycled City)": "A detailed miniature architectural model constructed from orderly layers of recycled plastic bottles and geometric soda can elements, featuring vibrant multi-color RGB LED installations that shine through the translucent plastic and metallic surfaces, including tiny roads made of black rubber and small plastic-cap street lamps.",
                "Masjidil Haram Mewah": "A detailed miniature diorama of Masjidil Haram built on a polished marble base. The small-scale Ka'bah is at the center draped in real black Kiswah cloth with gold LED calligraphy, surrounded by a white stone Mataf courtyard illuminated by thousands of tiny cold-white LED pixels and miniature figure silhouettes.",
                "Masjid Nabawi (Payung & Green Dome)": "A detailed miniature of Masjid Nabawi featuring a vibrant Green Dome brightly lit from within, iconic courtyard umbrellas with edges traced by warm white LED strips, hundreds of small LED street lamps along polished marble-textured paths, and tiny palm trees.",
                "Masjid Al-Aqsa (Dome of the Rock)": "A detailed miniature of the Dome of the Rock featuring a shimmering gold dome illuminated by warm-white LEDs, surrounded by small ancient olive trees and tiny stone pathways on a realistic rocky resin base with amber LED accents.",
                "Terapung di Danau (RGB Reflection)": "A detailed miniature mosque on a wooden platform situated on a calm resin lake, featuring a courtyard filled with glowing LED lotus flowers and lily pads, with the water surface acting as a mirror reflecting the vibrant RGB lights of the architecture.",
                "Diorama Mewah (Kubah Kuning & Air Terjun)": "A detailed miniature mosque featuring a sparkling polished yellow-brass dome and white stone-textured walls with RGB LED lights, with a courtyard containing a small multi-tiered fountain and tiny wooden horse-drawn carriages on a paved stone floor.",
                "Diorama Organik (Refleksi Air & Neon)": "A detailed miniature mosque constructed from translucent soap segments that glisten with neon blue and purple LED backlighting, situated on a circular mirror-like reflection pool with small fiber-optic lights in the garden.",
                "Diorama Timur Tengah (Sunset & Oasis)": "A detailed desert miniature with a mud-brick style mosque made of clay, featuring warm amber LED lights, a water oasis with small palm trees, and miniature camel caravans on a sand-textured base.",
                "Lembah Hijau & Masjid Serabut (Emerald Glow)": "A detailed landscape miniature featuring a mosque made of coconut fibers on a moss-covered hill, including a flowing resin river with blue LED under-lighting and multi-color LED strips on the minarets.",
                "Tebing Karang & Masjid Cangkang (Ocean Neon)": "A detailed seaside miniature featuring a mosque made of sea shells on a rocky stone cliff, with rainbow LED fiber optics illuminating the resin waves and a white sand courtyard with tiny dried corals.",
                "Hutan Rimba & Masjid Kayu Tua (Mystical Forest)": "A detailed jungle miniature featuring a mosque made of weathered bark and twigs hidden among ferns, with vibrant violet and lime LED lights glowing from the floor and tiny mosque windows.",
                "Gurun Pasir & Masjid Rempah (Sahara Gold)": "A detailed desert miniature with a mosque constructed from cinnamon sticks and orange peels on dunes of turmeric and sand, illuminated by warm amber and red LED lights near a small resin oasis.",
                "Tepi Pantai & Dermaga (Neon Blue)": "A detailed miniature mosque on a white sandy beach made of fine sand, featuring turquoise resin waves, a wooden pier with neon blue LED lanterns, tiny glowing palm trees, and small sea-shell decorations.",
                "Padang Pasir & Oase (Amber Glow)": "A detailed desert miniature featuring a mosque on sand dunes, with a pond oasis illuminated by warm amber LED lighting, tiny palm trees, and a miniature camel caravan in the courtyard.",
                "Kota Madinah Style (Luxury White)": "A detailed miniature Madinah-style mosque with small white buildings and iconic umbrella canopies, featuring a marble-textured floor lit by cold-white LED pixels and tiny green glowing minaret tips.",
                "Kampung Apung & Masjid Bambu (River Jewel)": "A detailed riverside miniature featuring a mosque made of woven bamboo on a wooden platform over a resin water pond, with colorful RGB LEDs reflecting off the water and glowing through the bamboo walls.",
                "Negeri Permen & Masjid Cokelat (Candy Land)": "A whimsical miniature mosque made of colorful clay and candy sticks on a pink cotton-candy hill, featuring rainbow LED lights and a blue syrup-colored resin river with tiny lollipop trees.",
                "Kota Mainan & Masjid Balok (Toy City)": "A detailed miniature city made of colorful building blocks with a block-style mosque, featuring pulsating RGB LED lights on the minarets, tiny street lamps, and miniature plastic cars.",
                "Modern (Geometric & RGB Strips)": "A detailed modern minimalist mosque with clean geometric white architecture and a silver-painted dome, featuring dynamic RGB LED strips tracing the structure edges and tiny abstract yard sculptures.",
                "Masjid Bambu (River Jewel)": "A detailed riverside diorama featuring a mosque made of woven bamboo on a wooden platform over a resin water pond, with colorful RGB LEDs reflecting off the water and glowing through the bamboo walls.",
                "Masjid Koran (Typography Craft)": "A detailed architectural diorama featuring a mosque made of layered recycled newsprint on a black plywood base, with warm-white LED strips hidden inside the arches highlighting the paper textures.",
                "Masjid Kardus (Industrial Craft)": "A detailed handcrafted diorama featuring a mosque made of corrugated cardboard on a flat base, with a courtyard floor made of green mung bean mosaics and cool-blue LED strips along the arches.",
                "Masjid Serabut (Rustic Nature)": "A detailed landscape diorama featuring a mosque made of golden-brown coconut fiber on a timber slab, with a courtyard of green felt fabric grass and internal warm-yellow LED lighting.",
                "Masjid Botol (Futuristic Recycle)": "A detailed miniature diorama featuring a mosque made of translucent recycled bottle segments on a plastic base, with a courtyard resin pond and vibrant RGB LEDs reflecting through the surfaces.",
                "Masjid Kayu (Traditional Toy)": "A detailed miniature diorama featuring a mosque made of popsicle sticks and toothpicks on a polished wood board, with tiny pebble paths in the courtyard and warm-white LED pixels.",
                "Masjid Rempah (Sahara Spice)": "A detailed desert diorama featuring a mosque made of cinnamon sticks on a sand-textured tray, with a courtyard of turmeric powder and miniature trees made of cloves with amber LED glows."
            }
        }

        # --- 3. MASTER LOKASI (FIXED: NATURAL CLUTTER & SOLID BACKDROP) ---
        MASTER_GRANDMA_SETTING = {
            "Pinggir Kolam Ikan Koi": (
                "The character sits cross-legged on a natural flat stone by a clear koi pond. "
                "Inside the pond, several colorful koi fish swim between lily pads. " # <-- Koinya balik, natural!
                "The background is filled with lush tropical ferns and thick garden bushes. "
                "A soft, natural overcast sky is partially visible through the gaps of tree leaves. " # <-- Langit natural
                "Next to her is a small brass fish food bowl and a plain ceramic teapot. "
                "NO ARTIFICIAL LIGHTING, NO GLOW. Pure neutral daylight and natural water reflections."
            ),
            "Teras Bambu Desa": (
                "Set on a woven bamboo floor of an open-air porch. "
                "The background is a dense grove of tall bamboo trees and wide banana leaves overlapping. " # <-- Layering taneman
                "The soft grey sky is visible behind the foliage, creating a realistic outdoor depth. "
                "Next to her are grass sandals and a small clay water jug. "
                "NO SOLID WALLS. Just natural organic textures and flat neutral lighting."
            ),
            "Lantai Kerikil Taman": (
                "Placed on a bed of white pebbles and natural grey gravel. "
                "The background features a low wooden picket fence and a line of tall flowering shrubs. " # <-- Pager kayu & taneman
                "A realistic overcast sky sits above the shrubs, providing a clean natural backdrop. "
                "Around her are scattered dry leaves and a simple iron lantern. "
                "NO VIBRANT COLORS. Natural earthy tones and soft diffused daylight."
            ),
            "Dek Kayu Pinggir Hutan": (
                "Set on an outdoor deck made of weathered, unsanded timber planks. "
                "The background is a dense forest wall with massive tree trunks and hanging wild vines. "
                "The overcast sky is filtered through the thick canopy above. "
                "Scattered pine cones and a wooden bird flute lie nearby on the planks. "
                "NO SHINY SURFACES. Raw wood textures and flat forest lighting."
            ),
            "Pinggir Sawah Hijau": (
                "Sitting cross-legged on dry grass at the edge of a vast green rice field. "
                "The horizon is naturally broken by distant coconut trees and a small wooden shack. " # <-- Ada pembatas alami
                "The sky is a realistic soft grey with faint cloud textures. "
                "Beside them lies a traditional caping hat and a small old radio. "
                "NO COLOR SATURATION. Pure, raw agricultural scenery in neutral daylight."
            ),
            "Teras Rumah Panggung": (
                "Sitting cross-legged on the wooden floor planks of a traditional porch. "
                "The background shows a view of a lush backyard with fruit trees and a distant hedge. "
                "The sky is framed naturally by the porch’s wooden roof and hanging orchids. " # <-- Framing natural
                "Scattered wood shavings and a small chisel lie on the floor. "
                "NO ARTIFICIAL CONTRAST. Just a simple, clean, and real village atmosphere."
            ),
            "Halaman Pohon Bambu": (
                "Sitting cross-legged on a traditional 'Tikar Pandan' mat. "
                "Background is a dense, natural grove of real bamboo stalks with overlapping green leaves. "
                "Soft natural daylight filters through the bamboo canopy, no artificial glow. "
                "A small incense burner (pedupaan) emits a thin, wispy trail of smoke. "
                "The view is naturally enclosed by the thick bamboo forest, no empty void."
            ),
            "Lantai Batu Candi": (
                "Set on a rough, porous dark volcanic stone floor (andesit). "
                "Background is an ancient carved stone relief, weathered and mossy, showing real stone textures. "
                "Next to the character are withered frangipani petals on the ground. "
                "Natural neutral lighting, zero digital effects. Focus on the raw stone surface."
            ),
            "Tanah Merah Kebun": (
                "Positioned on flat, packed red laterite soil with natural clods. "
                "Background is a dense, messy hedge of real tropical bushes and wild shrubs. "
                "Next to the character is a rusted garden trowel and a clay pot shard. "
                "Flat, overcast daylight. Pure earthy tones without any color boost."
            ),
            "Dek Bata Merah Tua": (
                "Resting on weathered, mossy red bricks in a herringbone pattern. "
                "Background is an old brick structure covered in real crawling ivy and green moss. "
                "An old brass watering can and a small pile of terracotta tiles sit nearby. "
                "Natural lighting, no extra contrast. Just the raw look of aged brickwork."
            ),
            "Tepi Jalan Setapak Hutan": (
                "Sitting cross-legged on a path covered in real pine needles and dried leaves. "
                "Background is a deep forest view with massive tree trunks and tangled wild vines. "
                "Natural forest lighting, soft and diffused. "
                "Next to the character is a large wild mushroom and a cluster of acorns. "
                "NO VOID. The forest depth provides a natural, organic backdrop."
            ),
            "Tepi Kolam Teratai & Air Terjun": (
                "Placed on smooth, weathered dark river stones. "
                "Background features a natural rock formation with a gentle water trickle and lush ferns. "
                "Pink and white lotus flowers float on the clear water surface. "
                "Real water reflections, no fake glow. Just a quiet, natural garden nook."
            ),
            "Halaman Rumput Hijau & Bonsai": (
                "Resting on a manicured, thick green grass turf. "
                "Background is a traditional stone fence (bentar) partially hidden by a thick green hedge. "
                "A miniature wooden rake and a basket of petals sit on the grass. "
                "Pure outdoor daylight, flat and clean. Focus on the texture of individual grass blades."
            ),
            "Taman Kering Zen & Kerikil": (
                "Placed on a bed of fine white pebbles with real raked ripple patterns. "
                "Background is a simple wooden garden partition and a single large mossy boulder. "
                "Polished obsidian stones lie near the character. "
                "Strictly natural lighting. No artificial shadows, just clean Zen aesthetics."
            ),
            "Tanah Liat & Sawah Berundak": (
                "Positioned on a flat dirt path at the edge of real green terraced rice fields. "
                "The background is the rising slope of the next terrace, filled with lush rice stalks. "
                "A conical caping hat and a clay flask sit on the dirt. "
                "Authentic agricultural lighting. The rising rice field naturally blocks the distant horizon."
            ),
            "Teras Batu Candi & Kamboja": (
                "Set on a rough, porous dark volcanic stone floor (andesit). "
                "The background is an ancient, weathered stone relief carving with natural moss and lichen in the crevices. " # <-- Relief asli, bukan tembok polosan
                "Next to the character is a small stone incense burner and a scattered handful of withered frangipani petals. "
                "Natural outdoor daylight, no artificial glow. A serene temple corner with authentic textures."
            ),
            "Gubuk Tengah Sawah (Saung)": (
                "Sitting cross-legged on the aged bamboo floor of an open-air Saung. "
                "The view is surrounded by a dense, swaying wall of tall golden rice stalks ready for harvest. " # <-- Padi rimbun, bukan tembok
                "A vintage kerosene lamp (lampu teplok) and a bunch of bananas sit on the bamboo slats. "
                "The soft grey sky is framed naturally by the overhanging thatch roof of the shack. "
                "Focus on the organic bamboo grain and the golden rice textures."
            ),
            "Tepian Sungai Berbatu": (
                "Sitting cross-legged on a large, flat river stone. "
                "The background is a natural riverbank embankment filled with wild ferns, river weeds, and tangled roots. " # <-- Tebing kali natural
                "A pair of traditional rubber sandals (sandal jepit) is placed neatly on a nearby rock. "
                "Clear river water ripples over pebbles. Neutral daylight, no digital enhancements."
            ),
            "Kebun Buah Naga": (
                "Sitting cross-legged on a rustic tikar mat in a dragon fruit plantation. "
                "Surrounded by a dense, lush grid of climbing dragon fruit cactus vines and hanging vibrant pink fruits. " # <-- Taneman naga rimbun
                "The plantation creates a natural green canopy that filters the soft overhead sky. "
                "Beside them is a small wicker basket with harvested dragon fruits. "
                "Authentic agricultural setting with flat, natural lighting."
            ),
            "Kebun Buah Melon": (
                "Sitting cross-legged on a low wooden plank floor inside a greenhouse. "
                "Background is filled with a dense wall of hanging melon vines, large green leaves, and ripening melons. " # <-- Daun melon lebat
                "The greenhouse plastic roof creates a soft, natural diffused light across the scene. "
                "Nearby is a traditional watering can and garden shears. "
                "Realistic greenhouse environment, pure and unedited look."
            ),
            "Taman Bunga Warna-Warni": (
                "Sitting cross-legged on a flat stone path. "
                "The background is a lush, thick hedge of blooming flowers, hibiscus, and various tropical shrubs. " # <-- Pager tanaman asli
                "Butterfly-attracting flowers create a natural colorful backdrop with deep green layers. "
                "A few fallen petals lie on the path. No artificial contrast, just raw botanical beauty."
            ),
            "Arena Bermain Anak": (
                "Sitting cross-legged on soft rubber playground flooring. "
                "Background features the base of a colorful plastic slide and a low wooden perimeter fence. " # <-- Objek playground asli
                "A forgotten vintage toy car lies near the character's feet. "
                "Overcast sky provides clean, flat lighting. A realistic, grounded playground corner."
            ),
            "Taman Hiburan (Carnival)": (
                "Sitting cross-legged on a large piece of clean cardboard spread on the grass. "
                "Background is the weathered colorful fabric of a large carnival tent and hanging festive banners. " # <-- Kain tenda asli
                "A half-eaten cotton candy on a stick is leaning against a bag nearby. "
                "Natural festive atmosphere, zero artificial glow. Just the raw texture of the tent and grass."
            ),
            "Halaman Toko Kelontong": (
                "Sitting cross-legged on a clean cement floor. "
                "The background is the colorful facade of a village 'Warung' with hanging drink sachets, cracker jars, and snack displays. " # <-- Pakai barang dagangan buat background
                "Next to the character is an old glass jar of crackers and a coil of rope. "
                "Natural daylight, no artificial glow. The shop's front structure naturally frames the scene."
            ),
            "Lantai Kerja Berantakan": (
                "Sitting cross-legged directly on a workshop floor scattered with sawdust. "
                "The background features wooden shelves filled with hand tools, cans of paint, and scrap materials. " # <-- Pakai rak tools
                "Small glue bottles, tweezers, and wood shavings are scattered around. "
                "Indoor neutral lighting. Realistic workshop atmosphere without digital effects."
            ),
            "Teras Rumah Klasik": (
                "Sitting cross-legged on the cool tiled floor of a vintage porch. "
                "In the background, a vintage bicycle (sepeda jengki) leans against a weathered wooden pillar. " # <-- Sepeda balek!
                "Potted clay plants and orchids line the terrace edge. "
                "Natural outdoor lighting. The porch roof and pillars provide a natural frame for the sky."
            ),
            "Ruang Tamu Jadul": (
                "Sitting cross-legged on a 'Tikar Pandan' mat. "
                "The background is an authentic wooden plank wall with a sepia family photo in a carved frame. " # <-- Foto balek!
                "A simple wooden cabinet sits in the corner. "
                "Soft indoor lighting, zero artificial contrast. A warm, honest domestic vibe."
            ),
            "Dapur Kampung Estetik": (
                "Sitting cross-legged on a low bamboo bale-bale. "
                "Next to her is a traditional clay stove (tungku) with a few bamboo baskets (tampah) leaning against the soot-stained brickwork. " # <-- Bumbu dapur balek!
                "A faint, natural wisp of smoke rises from the stove. "
                "Authentic rustic lighting, no fake glow. Focus on the raw textures of clay and bamboo."
            ),
            "Bengkel Rakit Miniatur": (
                "Sitting cross-legged on the floor of a creative room. "
                "The background is filled with pinned architectural sketches, balsa wood sheets, and shelves of half-finished models. " # <-- Sketsa balek!
                "Tweezers and glue bottles are laid out nearby. "
                "Clean, flat workshop lighting. A realistic 'work-in-progress' environment."
            ),
            "Gazebo Bambu (Outdoor)": (
                "Sitting cross-legged on polished bamboo slats of a Saung. "
                "The background is a lush, dense wall of green banana leaves and tropical shrubs. " # <-- Daun pisang rimbun
                "A small plate of traditional steamed bananas (pisang rebus) sits in the corner. "
                "Overcast daylight filtered through the leaves, no digital saturation."
            ),
            "Gubuk Tengah Sawah": (
                "Sitting cross-legged on rustic wooden planks. "
                "The background is the dense, overlapping layers of tall yellow rice stalks and the shack's wooden frame. " # <-- Padi rimbun
                "An old straw caping hat and a plastic water bottle lie nearby. "
                "Natural agricultural lighting. The horizon is naturally blocked by the height of the rice field."
            ),
            "Saung Pinggir Pantai": (
                "Sitting cross-legged on a woven plastic mat over white sand. "
                "The background is a natural limestone cliff or a dense cluster of palm trees. " # <-- Tebing/pohon pantai
                "Dry coconuts and worn flip-flops are scattered on the sand. "
                "Bright, diffused seaside daylight. No infinity sea, focus on the textured beach nook."
            ),
            "Teras Pinggir Sungai": (
                "Sitting cross-legged on a weathered wooden deck. "
                "The background is a steep, natural riverbank filled with thick tropical trees and hanging vines. " # <-- Tebing kali natural
                "A traditional bamboo fishing rod leans nearby. "
                "Real river water reflections, zero artificial glow. Just a quiet, honest riverbank setting."
            ),
            "Lapak Penjual Rongsokan": (
                "Sitting cross-legged on the dusty ground. "
                "The background is a massive pile of aged rusty metal sheets, old tires, and stacked newspapers. " # <-- Tumpukan barang rongsok
                "Next to them is a large rusty gear. "
                "Gritty industrial lighting, very raw and neutral. Focus on rust, grease, and metal textures."
            ),
            "Teras Masjid Tua": (
                "Sitting cross-legged on the cool, polished marble floor of a mosque porch. "
                "The background features traditional arched wooden doors and an old analog wall clock on a weathered stone surface. " # <-- Elemen asli masjid
                "A pair of worn-out leather sandals is placed neatly on the marble step. "
                "Natural diffused daylight, no artificial glow. The architecture naturally frames the serene space."
            ),
            "Teras Rumah Geribik Bambu": (
                "Placed on a cracked, uneven cement floor in front of an authentic weathered bamboo-weave wall (geribik). "
                "Next to the character is a chipped enamel mug and a half-eaten boiled sweet potato on a plastic plate. " # <-- Bumbu real
                "Nearby, a rusty bicycle wheel and tied-up cardboard scraps lean against the bamboo wall. "
                "Flat, natural lighting. Focus on the raw splinters of the bamboo and the floor cracks."
            ),
            "Kolong Jembatan Tua": (
                "Set on a damp, dusty concrete ground with patches of grey sand. "
                "The background is dominated by massive concrete bridge pillars with faded graffiti and exposed rusty rebar. " # <-- Pilar jembatan asli
                "A pile of discarded plastic bottles and a tattered burlap sack lie nearby. "
                "Dim, natural ambient lighting from the underpass, zero digital effects. Gritty and raw textures."
            ),
            "Gubuk Tengah Sawah Layu": (
                "Positioned on a dry, dusty wooden plank floor of a leaning shack. "
                "The background is a dense, parched wall of vertical dry rice stalks and old wooden planks. " # <-- Padi kering natural
                "A frayed sarong and an empty tin can sit on the dusty floor. "
                "Natural overcast lighting, no color boost. Focus on the organic wood rot and dry textures."
            ),
            "Pinggir Rel Kereta Api": (
                "Resting on a bed of dark, oil-stained gravel and coarse basalt stones. "
                "The background is a steep gravel embankment or a weathered corrugated metal fence (seng) that follows the track. " # <-- Tanggul rel asli
                "A bundle of recycled wires and a dented aluminum pot are scattered nearby. "
                "Neutral, flat outdoor daylight. Focus on the rust, grease, and stone textures."
            ),
            "Halaman Belakang Pasar": (
                "Placed on a muddy ground covered with flattened cardboard and rotting vegetable scraps. "
                "The background features stacks of empty fruit baskets and a stained, rusty corrugated metal fence (seng). " # <-- Pager seng pasar
                "Next to the character is a broken wooden crate and a dirty hemp rope. "
                "Realistic, messy environment with flat lighting. No artificial glow, just raw oxidation textures."
            ),
            "Kafe Estetik Kayu": (
                "Sitting cross-legged on a clean, light wood plank floor inside a cozy cafe. "
                "The background features a built-in wooden bookshelf filled with mini bonsai pots and cute clay mosque figurines. " # <-- Bumbu Lucu
                "Soft, warm LED strip lighting is hidden *behind* the wooden shelves, casting a gentle natural glow. " # <-- LED Natural
                "Next to her is a miniature pastel-colored ceramic teapot and a small plate of macaroons. "
                "NO RAIN, NO VOID. A private, warm, and highly-detailed indoor corner."
            ),
            "Kamar Estetik Pastel": (
                "Sitting cross-legged on a soft, pastel-colored knitted rug over white-washed floorboards. "
                "The background is a soft beige wall with small framed cartoon illustrations of traditional Indonesian villages. " # <-- Bumbu Lucu
                "A gentle LED neon sign in the shape of a smiling crescent moon is mounted on the wall (warm white). " # <-- LED Hiasan Dinding
                "Next to her are a few small plush toys (kucing gemoy) and a decorative candle. "
                "NATURAL NEUTRAL LIGHTING. Perfectly level 0-degree camera angle focusing on the coziness."
            ),
            "Ruang Kerja Kerajinan": (
                "Sitting cross-legged directly on the clean terrazzo floor of a home craft studio. "
                "The background is a light wood wall panel with a large circular LED mirror that reflects a gentle glow. " # <-- LED Dinding Lucu
                "Pinned on the wall are cute architectural sketches and small rolls of colorful threads. " # <-- Bumbu
                "Tweezers, a small hot glue gun, and craft paper are scattered on the floor. "
                "NO OUTDOOR ELEMENTS, NO SKY. A warm, busy indoor workshop vibe."
            ),
            "Teras Rumah Estetik": (
                "Set on a clean cement floor with patterned ceramic tiles (vintage style) in an enclosed porch. "
                "The background is a clean white wall with several cute hanging potted plants and a decorative laser-cut wooden Arabic calligraphy piece. " # <-- Hiasan Dinding Lucu
                "Hidden warm-white LED strips are integrated into the ceiling beams above, providing soft downlight. " # <-- LED Tersembunyi
                "Next to her are a few woven baskets and a single cute cat sleeping nearby. " # <-- Bumbu Lucu
                "NO OPEN SKY, NO INFINITY. A private, comfortable semi-outdoor indoor extension."
            ),
            "Kamar Anak Cewek (Pink Pastel)": (
                "Sitting cross-legged on a soft, thick pink faux-fur rug over light oak floorboards. "
                "The background is a soft peach wall with a custom LED neon sign in the shape of a 'Star' or 'Cloud' (warm pink glow). " # <-- LED Dinding Lucu
                "Around her are a few cute plushie dolls, a small white canopy curtain in the corner, and a fairy light string draped over a wooden rack. " # <-- Bumbu Lucu
                "A small pink beanbag and a few children's storybooks are scattered on the floor. "
                "NATURAL NEUTRAL LIGHTING. No outdoor view, a fully enclosed, cozy pink-themed girl's bedroom."
            ),
            "Kamar Anak Cowok (Space Adventure)": (
                "Sitting cross-legged on a navy blue woven rug over dark grey cement-style tiles. "
                "The background is a charcoal grey wall with a cool 'Astronaut' or 'Rocket' silhouette LED wall lamp (cool white glow). " # <-- LED Dinding Cowok
                "Around her are a few toy spaceships, a small wooden telescope, and a stack of colorful building blocks (LEGO style). " # <-- Bumbu Lucu
                "A chalkboard wall with chalk drawings of planets is visible in the background. "
                "SOFT DIFFUSED LIGHTING. No windows visible, focus on the playful and cool indoor boy's room vibe."
            ),
            "Kamar Nenek Asri (Vintage Solo)": (
                "Sitting cross-legged on a clean, dark-patterned 'Tikar Pandan' spread over a cool tegel kunci (patterned cement tiles). "
                "The background is a clean cream-colored wall with a simple wooden shelf holding an old radio and a small white jasmine plant in a clay pot. " # <-- Bumbu Asri
                "A small decorative LED lantern in the shape of a traditional birdcage (sangkar burung) hangs on the wall, emitting a soft warm glow. " # <-- LED Dinding Natural
                "Next to her is a small wooden side table with a glass of tea and a few pieces of traditional steamed cassava. "
                "The scene is framed by a large open wooden window showing a blurry view of green garden leaves outside. "
                "NATURAL DAYLIGHT. No harsh shadows, focus on the calm, breezy, and modest bedroom vibe."
            ),
            "Kamar Nenek Minimalis Desa": (
                "Sitting cross-legged on a low wooden platform bed (dipan kayu) covered with a simple batik-patterned cloth. "
                "The background features a light-colored wooden wall with a beautiful backlit LED wooden lattice (ukiran kayu) that glows softly. " # <-- LED Hiasan Dinding
                "Several small indoor potted plants like 'Lidah Mertua' (snake plant) are placed in the corner, adding a fresh green feel. " # <-- Bumbu Asri
                "Next to her is a pair of old spectacles and a small woven sewing basket. "
                "Soft natural light spills from an unseen side window, highlighting the dust particles in the air. "
                "NO MODERN FURNITURE. A peaceful, simple, and organic indoor atmosphere."
            ),
            "Kamar Nenek Estetik Modern": (
                "Sitting cross-legged on a clean, light-grey polished cement floor. "
                "The wall is painted in a beautiful 'Sage Green' matte finish, looking fresh and clean. " # <-- Cat Tembok Bagus
                "On the wall is a large laser-cut wooden Tree of Life decoration with hidden warm-white LED strips behind it, creating a soft halo glow. " # <-- LED & Hiasan Dinding
                "Next to the character is a small indoor palm tree in a white ceramic pot and a stack of clean linen pillows. "
                "The atmosphere is a mix of traditional modesty and modern interior design. "
                "NO OUTDOOR VOID. A fully enclosed, stylish, and peaceful grandmother's room."
            ),
            "Kamar Nenek Klasik Mewah": (
                "Sitting cross-legged on a woven 'Tikar Pandan' mat over a dark parquet wooden floor. "
                "The wall is painted in a warm 'Terracotta' earthy tone with a smooth, premium texture. " # <-- Cat Tembok Bagus
                "The background features several floating wooden shelves with warm LED downlights illuminating small ceramic mosque miniatures. " # <-- LED & Hiasan Rak
                "A large, elegant circular macrame wall hanging is the centerpiece on the wall. "
                "Next to her is a vintage brass tray with a glass of tea and a small plate of traditional snacks. "
                "NATURAL NEUTRAL LIGHTING. The scene is cozy, high-end, but still feels like home."
            )
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
                "Quiet Vulnerability (Steady gaze, eyes heavy with deep emotion)",
                "Pensive Stillness (Calm facial expression, long natural pauses)",
                "Graceful Serenity (Serene and peaceful look, slow breathing)",
                "Humble Devotion (Gentle and sincere facial expression)",
                "Stoic Calmness (A steady, wise face reflecting years of memories)",
                "Sacred Focus (Deeply focused expression, absolute sincerity)",
                "Peaceful Hope (A calm, hopeful look in the eyes)"
            ],
            "Physical Action": [
                "Delicate fingers precisely touching a tiny ornament on the mosque",
                "Holding a steady, focused gaze on the architectural details",
                "Eyes glistening slightly while looking down at the workbench",
                "Slow, calm swallowing while looking at the central dome",
                "Gently resting one finger on the textured surface of the diorama",
                "A subtle, peaceful smile while admiring the structure",
                "A slow, deep exhale while hands rest lightly on the table",
                "Closing eyes for a second in silent devotion",
                "Fingertips resting with extreme reverence on the diorama",
                "Briefly looking up with a calm, hopeful expression",
                "Looking down with intense focus, hands steady in their craft",
                "Softly blinking while observing the internal mosque lights"
            ]
        }
        # --- 4. MASTER AUDIO & SOULFUL EXPRESSION (FIXED WORKSHOP INTERACTION) ---
        MASTER_AUDIO_STYLE = {
            "Logat": [
                "Kampung Tulen (Authentic Rural Indonesian - Simple, honest, lilt)",
                "Jawa Medok (Deep Javanese Heart - Soft-spoken, slow, heavy consonants)",
                "Sunda Lembut (Melodic Sundanese - Gentle, flowing tones)",
                "Melayu Pesisir (Coastal Melayu - Raspy, rhythmic texture)",
                "Betawi Klasik (Classic Betawi Old-Soul - Humble and polite)"
            ],
            "Mood": [
                "Sedih & Sayu (Quiet Vulnerability - Eyes heavy with deep emotion)",
                "Tenang & Bengong (Pensive Stillness - Calm, long natural pauses)",
                "Damai Sejahtera (Graceful Serenity - Serene look, slow breathing)",
                "Tulus Ikhlas (Humble Devotion - Gentle and sincere expression)",
                "Tegar & Bijak (Stoic Calmness - Steady, wise face, many memories)",
                "Fokus Khusyuk (Sacred Focus - Deeply focused, absolute sincerity)",
                "Penuh Harapan (Peaceful Hope - Calm, hopeful look in the eyes)"
            ],
            "Physical Action": [
                "Menyentuh kubah dengan lembut sambil sesekali menatap kamera (Gently touching the mosque's dome, occasionally shifting gaze to look warmly at the camera)",
                "Menatap tajam detail lalu mendongak tersenyum (Holding a focused gaze on the details, then briefly looking up at the camera with a subtle smile)",
                "Mata berkaca-kaca menatap kamera dengan tulus (Looking directly at the camera with glistening eyes and a deeply soulful, hopeful expression)",
                "Tangan bersedekap di pangkuan menatap penuh doa (Hands resting on the lap in a prayerful pose, looking at the camera with silent devotion)",
                "Tersenyum tipis ke arah kamera sambil memegang miniatur (A peaceful smile while looking directly at the camera, hands gently supporting the model)",
                "Mengusap debu lalu menatap puas ke kamera (Gently wiping a speck of dust, then looking at the camera with a satisfied and contented expression)",
                "Memejamkan mata bersyukur lalu membukanya menatap kamera (Closing eyes in gratitude, then opening them to look warmly at the camera)",
                "Menunduk khusyuk merakit sesekali melirik kamera (Looking down with intense focus on the craft, occasionally glancing at the camera with a confident smile)"
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

                # 4. TEXT AREA (Kuncinya di parameter 'key')
                user_dialog = st.text_area(
                    "Input Dialog", 
                    placeholder=f"Tulis dialog {char_key.split(' (')[0]} di sini...",
                    height=250, 
                    label_visibility="collapsed",
                    key="input_dialog_key" # Ini nyambung ke handle_kocok
                )  
                # Update state biar sinkron
                st.session_state.current_dialog = user_dialog

            with c6:
                st.markdown('<p class="small-label">ACTING & PERFORMANCE</p>', unsafe_allow_html=True)
                pilih_logat = st.selectbox("Pilih Logat", MASTER_AUDIO_STYLE["Logat"])
                pilih_mood = st.selectbox("Pilih Mood", MASTER_AUDIO_STYLE["Mood"])
                
                # --- GANTI DI SINI: Dari random jadi selectbox ---
                pilih_aksi = st.selectbox("Pilih Gerakan Tubuh", MASTER_AUDIO_STYLE["Physical Action"])

            st.write("")
            btn_gen = st.button(
                "🚀 GENERATE VIDEO PROMPT", 
                type="primary", 
                use_container_width=True, 
                key="btn_generate_video"
            )
        # --- LOGIC GENERATOR (TOTAL REBUILD: ULTRA SHARP & CLEAN VISUAL) ---
        if btn_gen:
            # 1. POSISI MATI LESEHAN
            posisi_nenek = "sitting cross-legged on the ground (lesehan)"
            
            # 2. KUNCI KETAJAMAN & CLEAN STATIC VISUAL (FIXED)
            scene_context = (
                f"ULTRA-HD 8K RESOLUTION. HYPER-REALISTIC RAW PHOTO. "
                f"MANDATORY: NO TEXT, NO SUBTITLES, NO CAPTIONS. "
                # --- LIGHTING: TERANG TAPI GAK ADA MATAHARI ---
                f"LIGHTING: Bright diffused daylight, flat white sky, no sun disk visible, zero harsh shadows. "
                f"CONTRAST: Vivid colors, high-contrast micro-textures, glowing LED lights pop against clean daylight. "
                # --- POSITIONING: JARAK 1 METER & URUTAN LURUS ---
                f"CAMERA DISTANCE: Close-up 1 meter distance from lens to mosque. "
                f"ALIGNMENT: Strictly symmetrical. Mosque is in foreground center, {posisi_nenek} is directly behind the mosque. "
                # --- CAMERA: STATIS TOTAL ---
                f"CAMERA MOVEMENT: Strictly STATIC camera, zero movement, zero shake, zero zoom, zero slide. "
                f"FIXED AXIS: Perfectly level 0-degree eye level, locked tripod position. "
                # --- SHARPNESS: ANTI BLUR ---
                f"DEEP FOCUS: F/16 Aperture, everything from mosque to background is CRYSTAL CLEAR, zero blur, zero bokeh."
            )

            # 3. AMBIL DATA MASTER
            env_detail = MASTER_GRANDMA_SETTING.get(pilihan_set, "Natural outdoor setting.")
            soul_desc = MASTER_FAMILY_SOUL.get(pilihan_user, "An Indonesian person.")
            wardrobe_dict = MASTER_FAMILY_WARDROBE.get(char_key, {})
            baju_desc = wardrobe_dict.get(baju_pilihan, "Simple modest clothes.")
            
            # 4. KUNCI ANATOMI & HIJAB
            ANATOMY_LOCK = "STRICTLY TWO HUMAN HANDS, five fingers each. No ghost limbs."
            MANDATORY_LOCK = "MANDATORY: FULL HIJAB. NO HAIR SHOWING. FULLY COVERED MODEST CLOTHING."

            # --- 4.5 FILTER PEMBERSIH (HANYA AMBIL DALAM KURUNG) ---
            # Kode ini bakal buang teks Indo dan cuma ambil teks Inggris di dalam kurung
            aksi_final = pilih_aksi.split('(')[-1].strip(')') if '(' in pilih_aksi else pilih_aksi
            mood_final = pilih_mood.split('(')[-1].strip(')') if '(' in pilih_mood else pilih_mood
            logat_final = pilih_logat.split('(')[-1].strip(')') if '(' in pilih_logat else pilih_logat
                
            # 5. FINAL ASSEMBLY (Prompt Bersih)
            final_ai_prompt = (
                f"{scene_context} \n\n"
                f"CHARACTER DNA: {soul_desc}. {ANATOMY_LOCK} {MANDATORY_LOCK} \n"
                f"WARDROBE: {baju_desc}. \n"
                f"ENVIRONMENT: {env_detail}. \n"
                f"PERFORMANCE: {aksi_final}. Mood: {mood_final}. \n" 
                f"THE MASTERPIECE: {deskripsi_teknis}. \n"
                f"DIALOG CONTEXT: '{user_dialog}' delivered with {logat_final} accent. \n\n"
                # --- TECHNICAL: KUNCI STATIS & TAJAM ---
                f"TECHNICAL SPECS: Shot on ARRI Alexa 65, 24mm lens, F/16 Aperture, Deep Focus. "
                f"CAMERA LOGIC: Strictly STATIC camera, zero movement, perfectly level 0-degree angle. " # <-- Lurus & Diem
                f"VISUAL: Ultra-sharp 8K, high-contrast colors, zero motion blur, global shutter. "
                f"NEGATIVE PROMPT: blurry, bokeh, depth of field, out of focus, shaky, motion blur, " # <-- Anti Blur
                f"chair, table, furniture, text, watermark, side-view, tilted, distorted."
            )

            # --- 7. TAMPILKAN HASIL ---
            st.success("🔥 PROMPT MASJID READY!")
            st.markdown('<p class="small-label">SALIN PROMPT DI BAWAH INI:</p>', unsafe_allow_html=True)
            st.code(final_ai_prompt, language="text")

    # ==========================================================================
    # TAB: ANATOMY (SULTAN IDENTITY LOCK - CLEAN ENGINE)
    # ==========================================================================
    with t_anatomi:
        # --- 1. DATABASE KARAKTER ---
        DB_KARAKTER_ANATOMY = {
            "Custom/None": {"physic": "", "base": "Manual Input"},
            "DIAN": {
                # Silet Analisa: Skeleton, Transparent Skin, 3D Protruding Eyes, Pixar Style.
                "physic": "a stylized human skeleton with clean white bones, encased in a thick volumetric transparent skin, Pixar animation style, large 3D protruding expressive eyes popping out from the sockets, high-gloss surface reflections, soft round edges, extremely clean aesthetic",
                "base": "Pixar Transparent Skeleton with Pop-Out Eyes"
            },
            "JUPRI": {
                "physic": "a stylized human skeleton, smooth clean white bones, wrapped in an ultra-thin super-clear transparent skin membrane, visible glowing blue electrical nerves glowing faintly beneath the thin skin, the skin tightly clings to the bone structure, no internal organs, large 3D protruding expressive eyes, Pixar animation style, wide skeletal smile with detailed glossy teeth",
                "base": "Thin Skin Skeleton + Blue Nerves"
            },
            "SULE": {
                "physic": "a stylized 10-year-old child skeleton, short and small bone structure, smooth clean white bones, large expressive 3D protruding eyes, encased in an ultra-thin super-clear transparent skin, barely visible translucent layer, Pixar animation style, soft round edges, extremely clean aesthetic, no organs, no veins",
                "base": "Child Skeleton with Paper-Thin Glass Skin"
            },
            "SAPRI": {
                "physic": "a stylized adult human skeleton with clean white bones, only visible internal heart and lungs suspended inside the ribcage, the heart is glowing vibrant neon red, the lungs are glowing vibrant neon blue, glowing organ effects, encased in an ultra-thin super-clear transparent skin, an thin faint electric blue light traces and glows faintly around the outer skin surface, Pixar animation style, large 3D protruding eyes, no blood, clean anatomical aesthetic",
                "base": "Skeleton with Glowing Organs & Neon-Outline Skin"
            }
        }

        # --- 2. LOGIKA UPDATE OTOMATIS (SESSION STATE) ---
        if 'k1_physic_ana' not in st.session_state: st.session_state.k1_physic_ana = ""
        if 'k2_physic_ana' not in st.session_state: st.session_state.k2_physic_ana = ""

        def update_physic_ana():
            st.session_state.k1_physic_ana = DB_KARAKTER_ANATOMY[st.session_state.k1_sel_ana]["physic"]
            st.session_state.k2_physic_ana = DB_KARAKTER_ANATOMY[st.session_state.k2_sel_ana]["physic"]

        # --- 3. WRAPPER UI: DASHBOARD CLEAN ---
        with st.expander("🦴 PINTAR ANATOMY ENGINE", expanded=True):
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                st.markdown('<p class="small-label">👤 KARAKTER 1 (ACTOR_1)</p>', unsafe_allow_html=True)
                k1_sel = st.selectbox("Pilih K1:", list(DB_KARAKTER_ANATOMY.keys()), key="k1_sel_ana", on_change=update_physic_ana, label_visibility="collapsed")
                k1_name = st.text_input("Nama K1:", placeholder="Nama...", key="k1_name_manual_ana") if k1_sel == "Custom/None" else k1_sel
                k1_physic = st.text_area("Fisik K1:", key="k1_physic_ana", height=100, label_visibility="collapsed")
                k1_wear = st.text_input("Pakaian K1:", placeholder="Outfit K1...", key="k1_wear_ana", label_visibility="collapsed")

            with col_k2:
                st.markdown('<p class="small-label">👤 KARAKTER 2 (ACTOR_2)</p>', unsafe_allow_html=True)
                k2_sel = st.selectbox("Pilih K2:", list(DB_KARAKTER_ANATOMY.keys()), key="k2_sel_ana", on_change=update_physic_ana, label_visibility="collapsed")
                k2_name = st.text_input("Nama K2:", placeholder="Nama...", key="k2_name_manual_ana") if k2_sel == "Custom/None" else k2_sel
                k2_physic = st.text_area("Fisik K2:", key="k2_physic_ana", height=100, label_visibility="collapsed")
                k2_wear = st.text_input("Pakaian K2:", placeholder="Outfit K2...", key="k2_wear_ana", label_visibility="collapsed")

            st.divider()
            st.markdown('<p class="small-label">🎬 NASKAH VISUAL & AKSI</p>', unsafe_allow_html=True)
            naskah_visual = st.text_area("Aksi:", placeholder="Contoh: SAPRI mencabut KERIS di depan DIAN...", key="visual_script_ana", height=150, label_visibility="collapsed")

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1: v_style = st.selectbox("Style:", ["Sangat Nyata", "Cinematic", "Anime"], key="v_style_ana")
            with col_s2: v_light = st.selectbox("Lighting:", ["Senja Cerah (Golden)", "Misty Night", "Studio Light"], key="v_light_ana")
            with col_s3: v_cam = st.selectbox("Camera:", ["Sejajar Mata", "Low Angle", "High Angle"], key="v_cam_ana")

            v_loc = st.text_input("📍 LOKASI SETTING", placeholder="Lokasi...", key="v_loc_ana")

            st.markdown('<p class="small-label">🗣️ DIALOG SYSTEM</p>', unsafe_allow_html=True)
            col_d1, col_d2 = st.columns(2)
            with col_d1: diag_k1 = st.text_input("Dialog K1:", placeholder=f"Ucapan {k1_name}...", key="diag_k1_ana")
            with col_d2: diag_k2 = st.text_input("Dialog K2:", placeholder=f"Ucapan {k2_name}...", key="diag_k2_ana")

            btn_gen_sultan = st.button("🚀 GENERATE VIDEO PROMPT", type="primary", use_container_width=True, key="btn_gen_ana")

        # --- 4. LOGIKA PROMPT ENGINE (THE GHOST GUARD) ---
        if btn_gen_sultan:
            if naskah_visual and v_loc:
                # GHOST NEGATIVE PROMPT (UNDER THE HOOD)
                GHOST_NEG = (
                    "blur, morphing, merging characters, sinking feet, vanishing props, "
                    "object transformation, weapon shifting wielder, extra limbs, "
                    "distorted object geometry, flickering items, floating accessories"
                )

                MAP_STYLE_ANATOMY = {
                    "Sangat Nyata": "hyper-realistic photorealism, 8k RAW photo, ultra-detailed textures on skin and all surfaces, sharp focus, extreme macro details, shot on 35mm lens, f/1.8, high contrast, ray-tracing, physically based rendering, masterpiece quality",
                    "Cinematic": "cinematic movie still shot on 70mm IMAX film, anamorphic lens flare, high dynamic range (HDR), dramatic theatrical shadows, cinematic color grading, atmospheric haze, deep black levels, cinematic grain, wide aspect ratio",
                    "Anime": "high-quality 3D animation style, Pixar and Disney aesthetic, stylized character design, soft global illumination, ray-traced reflections, subsurface scattering on skin, vibrant cinematic colors, 8k render, Unreal Engine 5 render look",
                }
                MAP_LIGHT_ANATOMY = {
                    "Senja Cerah (Golden)": "soft late afternoon light, pale gold ambient glow, neutral color temperature, muted warm tones, cinematic soft shadows, clear visibility, realistic outdoor lighting, subtle highlights",
                    "Misty Night": "clear moonlit night, soft diffused moonlight, neutral color temperature, cool silver glow on surfaces, sharp focus on all objects, high contrast shadows, bioluminescent accents on characters, realistic nocturnal outdoor lighting, subtle highlights, deep black levels",
                    "Studio Light": "professional cinematic studio lighting, high-key lighting setup, sharp dual-rim light to define edges, neutral color balance, soft shadows, 8k showcase quality, ray-traced reflections on transparent skin, clean white or dark studio background"
                }
                MAP_CAM_ANATOMY = {
                    "Sejajar Mata": "eye-level cinematic shot, 50mm prime lens, natural perspective, sharp focus on subjects, subtle background blur, stabilized camera, realistic human height viewpoint",
                    "Low Angle": "dramatic low angle shot, looking up from ground level, 35mm lens, heroic perspective, emphasizing height and power, clear floor-to-subject contact, majestic scale, sharp silhouettes against the sky",
                    "High Angle": "high angle cinematic perspective, looking down from above, 35mm lens, realistic depth, clear ground shadows, emphasizing the surrounding environment, sharp overhead focus, subjects clearly grounded on the floor",
                }

                # 3. IDENTITAS KARAKTER (LOGIKA SILET: ANTI-GANTUNG)
                prompt_actors = []
                
                # Cek Karakter 1
                if k1_name and k1_name.lower() in naskah_visual.lower():
                    desc_k1 = f"{k1_name} ({k1_physic})"
                    if k1_wear: # Hanya tambah 'wearing' kalau k1_wear ada isinya
                        desc_k1 += f" wearing {k1_wear}"
                    prompt_actors.append(desc_k1)
                
                # Cek Karakter 2
                if k2_name and k2_name.lower() in naskah_visual.lower():
                    desc_k2 = f"{k2_name} ({k2_physic})"
                    if k2_wear: # Hanya tambah 'wearing' kalau k2_wear ada isinya
                        desc_k2 += f" wearing {k2_wear}"
                    prompt_actors.append(desc_k2)
                
                final_actors = " and ".join(prompt_actors) if prompt_actors else "the characters"

                # IMAGE PROMPT (SULTAN REVISION - ANATOMY SYNC)
                final_img = (
                    f"A {MAP_STYLE_ANATOMY[v_style]} photo featuring {final_actors}. "
                    f"ACTION: {naskah_visual}. "
                    f"SETTING: {v_loc}. "
                    f"ENVIRONMENT: {MAP_LIGHT_ANATOMY[v_light]} with {MAP_CAM_ANATOMY[v_cam]}. "
                    f"TECHNICAL: Absolute object permanence, precise anatomical details, solid ground-to-feet contact, "
                    f"no clipping, high-fidelity textures, 8k resolution, ray-traced shadows. "
                    f"NEGATIVE: {GHOST_NEG}"
                )
                
                # VIDEO PROMPT
                dialog_fixed = f"Only {k1_name} speaks '{diag_k1}' while {k2_name} is silent." if diag_k1 and not diag_k2 else f"Only {k2_name} speaks '{diag_k2}' while {k1_name} listens." if diag_k2 and not diag_k1 else ""
                
                # VIDEO PROMPT (SULTAN PHYSICS ENGINE)
                final_vid = (
                    f"Start from the reference image. {naskah_visual}. {dialog_fixed} "
                    f"STRICT TEMPORAL CONSISTENCY: Maintain the exact visual identity of {k1_name} and {k2_name} throughout the video. "
                    f"STRICT PHYSICS: Solid ground contact, absolutely no sinking feet into the sand. "
                    f"OBJECT PERMANENCE: All handheld props and weapons must keep their original shape and category, DO NOT morph or transform. "
                    f"Fluid biological motion, realistic gravity, high-fidelity 4k. "
                    f"NEGATIVE: {GHOST_NEG}"
                )

                # DISPLAY
                res1, res2 = st.columns(2)
                with res1: st.code(final_img, language="markdown")
                with res2: st.code(final_vid, language="markdown")
            else:
                st.error("Lokasi dan Naskah Visual wajib diisi, Dian!")
                
    # ============================================================
    # --- TAB: ⚡ TRANSFORMATION ENGINE (ULTIMATE SULTAN EDITION) ---
    # ============================================================
    with t_transform:        
        with st.expander("⚡ PINTAR TRANFORMATION ENGINE", expanded=True):

            # --- 1. DATABASE & SULTAN MAPPING (ANATOMY GRADE) ---
            DB_TRANS_EFFECT = {
                "Energi (Super Saiyan/Aura)": "radiant golden aura, electrical sparks, hair standing up, glowing energy pulses",
                "Otot (Hulk/Monster)": "rapid muscle expansion, skin stretching, clothes ripping, massive physical growth",
                "Kostum (Spiderman/Armor)": "suit material crawling over skin, nanotech assembly, liquid metal covering the body",
                "Bakar (Embers)": "burning into glowing hot embers, skin turning into charcoal then flaking away",
                "Cair (Liquid Metal)": "melting into a fluid liquid silver metal, reflective chrome transition",
                "Pasir (Dust/Sand)": "disintegrating into fine particles, blown away by mystical wind",
                "Asap (Shadow/Mist)": "turning into dark thick smoke, swirling shadows, ethereal gaseous state"
            }

            MAP_STYLE_TRANS = {
                "Sangat Nyata": "hyper-realistic raw photorealism, 8k RAW photo, ultra-detailed skin textures, sharp focus, masterpiece quality, shot on 35mm lens, f/8, ray-tracing",
                "Cinematic": "cinematic movie still shot on 70mm IMAX film, anamorphic lens flare, theatrical shadows, cinematic color grading, deep black levels",
                "Anime": "high-quality 3D animation style, Pixar aesthetic, stylized character design, soft global illumination, vibrant cinematic colors",
            }

            MAP_GEAR_TRANS = {
                "ARRI Alexa LF": "shot on ARRI Alexa LF, cinematic color science, soft highlight roll-off, professional film look, natural skin tones",
                "RED V-Raptor": "shot on RED V-Raptor 8K, extreme sharpness, high dynamic range, digital cinema texture",
                "Sony A7S III (Vlog)": "shot on Sony A7S III, handheld feel, 4k digital video texture, realistic autofocus depth",
                "Vintage 16mm": "16mm film stock, vintage grainy texture, nostalgic color grading, retro aesthetic"
            }
            
            MAP_LIGHT_TRANS = {
                "Senja Cerah (Golden)": "soft late afternoon light, pale gold ambient glow, neutral color temperature, realistic outdoor lighting",
                "Misty Night": "clear moonlit night, diffused moonlight, cool silver glow, high contrast shadows, deep black levels",
                "Studio Light": "professional cinematic studio lighting, sharp dual-rim light, neutral color balance, 8k showcase quality"
            }

            MAP_CAM_TRANS = {
                "Sejajar Mata": "eye-level cinematic shot, 50mm prime lens, natural perspective, sharp focus on subjects",
                "Low Angle": "dramatic low angle shot, looking up from ground level, 35mm lens, heroic majestic scale",
                "High Angle": "high angle cinematic perspective, looking down from above, 35mm lens, realistic depth",
            }

            # --- 2. INPUT PANEL ---
            with st.container(border=True):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.markdown('<p class="small-label">👤 KARAKTER UTAMA (IDENTITY LOCK)</p>', unsafe_allow_html=True)
                    v_char_name = st.text_input("Nama Utama:", placeholder="Nama...", key="tr_name", label_visibility="collapsed")
                    v_char_physic = st.text_input("Fisik Utama:", placeholder="Fisik (Contoh: Pria atletis)...", key="tr_physic", label_visibility="collapsed")
                    v_char_outfit = st.text_input("Outfit Utama:", placeholder="Pakaian Utama...", key="tr_outfit", label_visibility="collapsed")
                with col_c2:
                    st.markdown('<p class="small-label">👥 KARAKTER TAMBAHAN (OPTIONAL)</p>', unsafe_allow_html=True)
                    v_fig_name = st.text_input("Nama Figuran:", placeholder="Nama...", key="fig_name", label_visibility="collapsed")
                    v_fig_physic = st.text_input("Fisik Figuran:", placeholder="Fisik Figuran...", key="fig_physic", label_visibility="collapsed")
                    v_fig_outfit = st.text_input("Outfit Figuran:", placeholder="Pakaian Figuran...", key="fig_outfit", label_visibility="collapsed")

                st.divider()

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.markdown('<p class="small-label">🧬 WUJUD AKHIR (TARGET FORM)</p>', unsafe_allow_html=True)
                    v_char_target = st.text_input("Wujud Akhir:", placeholder="Contoh: Hulk, Transformer...", key="tr_target", label_visibility="collapsed")
                    st.markdown('<p class="small-label">⚡ PEMICU SPESIFIK (TRIGGER)</p>', unsafe_allow_html=True)
                    v_trigger = st.text_input("Aksi Pemicu:", placeholder="Contoh: saat loncat, saat berteriak...", key="tr_trigger", label_visibility="collapsed")
                with col_p2:
                    st.markdown('<p class="small-label">✨ EFEK TRANSISI</p>', unsafe_allow_html=True)
                    v_eff_type = st.selectbox("Efek:", list(DB_TRANS_EFFECT.keys()), key="tr_eff", label_visibility="collapsed")
                    st.markdown('<p class="small-label">⏱️ TIMING (DETIK)</p>', unsafe_allow_html=True)
                    v_timing = st.slider("Berubah Setelah:", 1.0, 15.0, 2.0, 0.5, key="tr_time")

                st.divider()

                st.markdown('<p class="small-label">🎬 NASKAH VISUAL (PISAHKAN DENGAN TITIK . UNTUK URUTAN AKSI)</p>', unsafe_allow_html=True)
                v_scene_detail = st.text_area("Urutan Adegan:", placeholder="Contoh: DIAN jalan. DIAN lari. DIAN loncat. DIAN berubah.", height=150, key="tr_scene", label_visibility="collapsed")
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown(f'<p class="small-label">💬 DIALOG {v_char_name.upper() if v_char_name else "UTAMA"}</p>', unsafe_allow_html=True)
                    v_diag_a = st.text_area("Utama Bicara:", height=30, key="tr_diag_a", label_visibility="collapsed")
                with col_d2:
                    st.markdown(f'<p class="small-label">💬 DIALOG {v_fig_name.upper() if v_fig_name else "FIGURAN"}</p>', unsafe_allow_html=True)
                    v_fig_diag = st.text_area("Figuran Bicara:", height=30, key="tr_fig_diag", label_visibility="collapsed")

                st.divider()

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.markdown('<p class="small-label">🎨 STYLE & LIGHTING</p>', unsafe_allow_html=True)
                    v_style_choice = st.selectbox("Style:", list(MAP_STYLE_TRANS.keys()), key="tr_style", label_visibility="collapsed")
                    v_light_choice = st.selectbox("Lighting:", list(MAP_LIGHT_TRANS.keys()), key="tr_light", label_visibility="collapsed")
                with col_s2:
                    st.markdown('<p class="small-label">🎥 CAMERA GEAR & SHOT</p>', unsafe_allow_html=True)
                    v_gear_choice = st.selectbox("Camera Gear:", list(MAP_GEAR_TRANS.keys()), key="tr_gear", label_visibility="collapsed")
                    v_cam_choice = st.selectbox("Shot Angle:", list(MAP_CAM_TRANS.keys()), key="tr_cam", label_visibility="collapsed")

                v_loc = st.text_input("📍 Lokasi Kejadian:", placeholder="Lokasi...", key="tr_loc")

                btn_gen_trans = st.button("🚀 GENERATE PROMPT", type="primary", use_container_width=True)

            # --- 3. LOGIKA GENERATOR PROMPT (SULTAN ENGINE) ---
            if btn_gen_trans:
                if v_char_name and v_scene_detail and v_loc:
                    
                    def rakit_identitas_sultan(name, physic, outfit, is_master=False):
                        if not name: return ""
                        ref_tag = "refer to PHOTO #MASTER ONLY" if is_master else "visual description only"
                        return f"[[ CAST_SULTAN_{name.upper()} ({name}): {ref_tag}. PHYSIC: {physic}. WEAR: {outfit} ]]"

                    steps = [s.strip() for s in v_scene_detail.split('.') if len(s.strip()) > 2]
                    first_step_text = steps[0].upper() if steps else v_scene_detail.upper()
                    
                    fig_in_script = True if (v_fig_name and v_fig_name.upper() in v_scene_detail.upper()) else False
                    fig_in_first_frame = True if (v_fig_name and v_fig_name.upper() in first_step_text) else False

                    main_id = rakit_identitas_sultan(v_char_name, v_char_physic, v_char_outfit, is_master=True)
                    fig_id_full = " AND " + rakit_identitas_sultan(v_fig_name, v_fig_physic, v_fig_outfit) if fig_in_script else ""
                    fig_id_initial = " AND " + rakit_identitas_sultan(v_fig_name, v_fig_physic, v_fig_outfit) if fig_in_first_frame else ""

                    # --- LOGIKA DIALOG ---
                    target_phase = "Phase 2" if len(steps) > 1 else "Phase 1"
                    video_diag = ""
                    if v_diag_a or v_fig_diag:
                        video_diag = f"DIALOGUE EXECUTION: Mouth movement is ONLY allowed for the speaker. "
                        if v_diag_a and not v_fig_diag:
                            video_diag += f"In {target_phase}, {v_char_name} is the ONLY one speaking: '{v_diag_a}'. {v_fig_name} must keep mouth tightly closed."
                        elif v_fig_diag and not v_diag_a:
                            video_diag += f"In {target_phase}, {v_fig_name} is the ONLY one speaking: '{v_fig_diag}'. {v_char_name} must keep mouth tightly closed."
                        elif v_diag_a and v_fig_diag:
                            video_diag += f"In {target_phase}, {v_char_name} speaks first, then {v_fig_name} replies. No simultaneous talking."

                    # --- FIX ERROR: DEFINISI DULU BARU TAMBAH ---
                    ULTRA_SHARP = "extreme sharp focus, cinematic texture, visible skin pores, natural imperfections, 8k, masterpiece quality, no motion blur"
                    TRANS_NEG = "text, speech bubbles, subtitles, floating objects, extra limbs, plastic texture, airbrushed, cartoon, low quality, glitch, distorted hands"
                    
                    # Sekarang aman buat ditambahin karena TRANS_NEG sudah ada isinya
                    if v_fig_name:
                        TRANS_NEG += f", {v_fig_name} talking, simultaneous speaking, ghost lipsync, vibrating lips"

                    is_trans = True if (v_trigger and v_char_target) else False
                    trans_logic = (f"CHRONOLOGY: Maintain {v_char_outfit} form until {v_timing}s, then as {v_char_name} {v_trigger}, morph into {v_char_target}." if is_trans else "PURE ACTION.")

                    # --- FINAL OUTPUT ---
                    final_img = (
                        f"{main_id}{fig_id_initial}. SCENE START: {steps[0] if steps else v_scene_detail}. Neutral expression, closed mouth. "
                        f"VISUAL: {MAP_GEAR_TRANS[v_gear_choice]}, {MAP_CAM_TRANS[v_cam_choice]}, {MAP_STYLE_TRANS[v_style_choice]}, {MAP_LIGHT_TRANS[v_light_choice]}. "
                        f"TECHNICAL: {ULTRA_SHARP}. NEGATIVE: {TRANS_NEG}"
                    )
                    
                    final_vid = (
                        f"MANDATORY: START DIRECTLY FROM THE UPLOADED REFERENCE IMAGE. {main_id}{fig_id_full}. STORYLINE: {' -> '.join([f'Phase {i+1}: {s}' for i, s in enumerate(steps)])}. {video_diag} "
                        f"CINEMATOGRAPHY: {MAP_GEAR_TRANS[v_gear_choice]}, {MAP_STYLE_TRANS[v_style_choice]}, {MAP_LIGHT_TRANS[v_light_choice]}. "
                        f"{trans_logic} TECHNICAL: {ULTRA_SHARP}. Ensure 100% identity consistency for 20s. NEGATIVE: {TRANS_NEG}"
                    )

                    st.divider()
                    res1, res2 = st.columns(2)
                    with res1:
                        st.markdown('<p class="small-label">📸 1. GENERATE IMAGE INI</p>', unsafe_allow_html=True)
                        st.code(final_img, language="markdown")
                    with res2:
                        st.markdown(f'<p class="small-label">🎬 2. UPLOAD IMAGE KE VIDEO PROMPT INI</p>', unsafe_allow_html=True)
                        st.code(final_vid, language="markdown")
                else:
                    st.error("Minimal isi Nama Utama, Naskah, dan Lokasi!")

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
            mask_bonus_real = (df_kas_all['KATEGORI'].str.upper() == 'GAJI TIM') & \
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

    # --- 3. PANEL ADMIN (Taruh di Sini!) ---
    if user_level == "OWNER": # <--- Cuma Dian yang punya akses kirim tugas
        
        # Ambil data staff untuk dropdown
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
                    
                    # --- 1. KIRIM KE SUPABASE (Biar Radar Langsung Update) ---
                    # Sesuaikan key dengan nama kolom asli di DB lo (Staf, Deadline, dll)
                    data_tugas_supabase = {
                        "ID": t_id,
                        "Staf": staf_tujuan,
                        "Deadline": tgl_skrg,
                        "Instruksi": isi_tugas,
                        "Status": "PROSES"
                    }
                    supabase.table("Tugas").insert(data_tugas_supabase).execute()
                    
                    # --- 2. KIRIM KE GSHEET (Backup Kesayangan Lo) ---
                    sheet_tugas.append_row([t_id, staf_tujuan, tgl_skrg, isi_tugas, "PROSES", "-", "", ""])
                    
                    # --- 3. LOG & NOTIF ---
                    tambah_log(st.session_state.user_aktif, f"Kirim Tugas Baru {t_id}")
                    
                    if pake_wa:
                        kirim_notif_wa(f"✨ *INFO TUGAS*\n\n👤 *Untuk:* {staf_tujuan.upper()}\n🆔 *ID:* {t_id}\n📝 *Detail:* {isi_tugas[:30]}...")
                    
                    st.success("✅ Terkirim ke Supabase & GSheet!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Isi dulu instruksinya, Bos!")

    # --- 4. SETOR MANDIRI (VERSI SUPER LOCK) ---
    if user_level in ["STAFF", "UPLOADER", "ADMIN"]:
        with st.expander("🚀 SETOR TUGAS MANDIRI", expanded=False):
            st.info("💡 **PENTING:** Setor 1 video per 1 kiriman agar bonus video & target bulanan terhitung otomatis oleh sistem.")
            
            with st.form("form_mandiri", clear_on_submit=True):
                judul_m = st.text_input("📝 Judul Video/Pekerjaan:", placeholder="Contoh: Video Konten A Part 1")
                link_m = st.text_input("🔗 Link GDrive:", placeholder="https://drive.google.com/...")
                
                submit_m = st.form_submit_button("🔥 KIRIM SETORAN", use_container_width=True)
                
                if submit_m:
                    if judul_m and link_m:
                        is_multiple = "," in link_m or link_m.lower().count("https://") > 1
                        
                        if is_multiple:
                            st.error("❌ **TERDETEKSI GANDA!** Dilarang mengirim lebih dari 1 link dalam satu setoran.")
                        elif "drive.google.com" not in link_m.lower():
                            st.warning("⚠️ **LINK TIDAK VALID!** Pastikan kamu memasukkan link Google Drive yang benar.")
                        else:
                            t_id_m = f"M{datetime.now(tz_wib).strftime('%m%d%H%M%S')}"
                            tgl_hari_ini = sekarang.strftime("%Y-%m-%d")
                            waktu_setor = sekarang.strftime("%d/%m/%Y %H:%M")
                            
                            # --- 1. SINKRON KE SUPABASE ---
                            # Kita masukkan data minimalis tapi penting buat Radar & SP
                            data_mandiri_sb = {
                                "ID": t_id_m,
                                "Staf": user_sekarang.upper(),
                                "Deadline": tgl_hari_ini, # Setoran mandiri dianggap selesai hari ini
                                "Instruksi": judul_m,
                                "Status": "WAITING QC", # Status awal biar lo cek dulu
                                "Waktu_Kirim": waktu_setor,
                                "Link_Hasil": link_m
                            }
                            supabase.table("Tugas").insert(data_mandiri_sb).execute()

                            # --- 2. GSHEET TETAP JALAN (BACKUP) ---
                            sheet_tugas.append_row([
                                t_id_m, 
                                user_sekarang.upper(), 
                                tgl_hari_ini, 
                                judul_m, 
                                "WAITING QC", 
                                waktu_setor, 
                                link_m, 
                                "" 
                            ])
                            
                            # --- NOTIF WA SIMPEL (MANDIRI) ---
                            kirim_notif_wa(f"📤 *SETORAN MANDIRI*\n👤 *Editor:* {user_sekarang.upper()}\n🆔 *ID:* {t_id_m}\n📝 *Tugas:* {judul_m}")
                            tambah_log(user_sekarang, f"SETOR MANDIRI: {judul_m} ({t_id_m})")
                            
                            st.success("✅ Setoran Mandiri Berhasil Terkirim!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("⚠️ Mohon isi Judul dan Link terlebih dahulu!")
                        
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
                                    
                                    with b1: # --- TOMBOL ACC ---
                                        if st.button("🟢 ACC", key=f"f_{id_tugas}", use_container_width=True):
                                            # PROTEKSI: Cegah klik ganda (Double Bonus)
                                            if f"lock_{id_tugas}" in st.session_state:
                                                st.warning("Sedang diproses...")
                                            else:
                                                st.session_state[f"lock_{id_tugas}"] = True # Kunci
                                                try:
                                                    # 1. UPDATE SUPABASE (Database Utama)
                                                    supabase.table("Tugas").update({"Status": "FINISH"}).eq("ID", id_tugas).execute()
                                                    
                                                    # 2. UPDATE GSHEET (Backup)
                                                    try:
                                                        cell = sheet_tugas.find(id_tugas)
                                                        if cell: sheet_tugas.update_cell(cell.row, 5, "FINISH")
                                                    except: pass

                                                    # 3. HITUNG BONUS (PAKAI MEMORI - ANTI LAG)
                                                    # Perbaikan: Tambah simbol '&' dan konversi string agar sinkron
                                                    staf_target = staf_nama.upper()
                                                    df_selesai = df_all_tugas[
                                                        (df_all_tugas['STAF'].str.upper() == staf_target) &
                                                        (df_all_tugas['DEADLINE'].astype(str) == str(tgl_tugas)) &
                                                        (df_all_tugas['STATUS'].str.upper() == 'FINISH')
                                                    ]
                                                    jml_video = len(df_selesai) + 1 

                                                    # 4. LOGIKA BONUS & ARUS KAS
                                                    msg_bonus = ""
                                                    if jml_video == 3 or jml_video >= 5:
                                                        nom_bonus = 30000
                                                        tgl_fix = str(tgl_tugas) # Paksa jadi string YYYY-MM-DD
                                                        ket_bonus = f"Bonus {'Absen' if jml_video == 3 else 'Video'}: {staf_nama} ({id_tugas})"
                                                        
                                                        # Kirim ke Arus Kas Supabase
                                                        supabase.table("Arus_Kas").insert({
                                                            "Tanggal": tgl_fix, 
                                                            "Tipe": "PENGELUARAN", 
                                                            "Kategori": "Gaji Tim", 
                                                            "Nominal": nom_bonus, 
                                                            "Keterangan": ket_bonus, 
                                                            "Pencatat": "SISTEM (AUTO-ACC)"
                                                        }).execute()
                                                        
                                                        # Kirim ke Arus Kas GSheet
                                                        try:
                                                            ws_kas = sh.worksheet("Arus_Kas")
                                                            ws_kas.append_row([tgl_fix, "PENGELUARAN", "Gaji Tim", nom_bonus, ket_bonus, "SISTEM (AUTO-ACC)"])
                                                        except: pass
                                                        
                                                        msg_bonus = f"\n💰 *BONUS:* Rp 30,000"
                                                        st.toast(f"Bonus {staf_nama} dicatat!", icon="💸")

                                                    # 5. NOTIF & REFRESH
                                                    kirim_notif_wa(f"✅ *TUGAS ACC*\n👤 *Editor:* {staf_nama}\n🆔 *ID:* {id_tugas}{msg_bonus}")
                                                    tambah_log(st.session_state.user_aktif, f"ACC TUGAS: {id_tugas}")
                                                    st.success("Tugas Selesai!"); time.sleep(1); st.rerun()
                                                    
                                                except Exception as e:
                                                    if f"lock_{id_tugas}" in st.session_state:
                                                        del st.session_state[f"lock_{id_tugas}"]
                                                    st.error(f"Gagal ACC: {e}")

                                    with b2: # --- TOMBOL REVISI ---
                                        if st.button("🔴 REV", key=f"r_{id_tugas}", use_container_width=True):
                                            if cat_r:
                                                supabase.table("Tugas").update({"Status": "REVISI", "Catatan_Revisi": cat_r}).eq("ID", id_tugas).execute()
                                                try:
                                                    cell = sheet_tugas.find(id_tugas)
                                                    if cell:
                                                        sheet_tugas.update_cell(cell.row, 5, "REVISI")
                                                        sheet_tugas.update_cell(cell.row, 8, cat_r)
                                                except: pass
                                                kirim_notif_wa(f"⚠️ *REVISI*\n👤 *Editor:* {staf_nama}\n🆔 *ID:* {id_tugas}\n📝: {cat_r}")
                                                st.warning("REVISI!"); time.sleep(1); st.rerun()
                                            else:
                                                st.error("Isi alasan revisi di kolom catatan!")

                                    with b3: # --- TOMBOL BATAL ---
                                        if st.button("🚫 BATAL", key=f"c_{id_tugas}", use_container_width=True):
                                            if cat_r:
                                                supabase.table("Tugas").update({"Status": "CANCELED", "Catatan_Revisi": f"BATAL: {cat_r}"}).eq("ID", id_tugas).execute()
                                                try:
                                                    cell = sheet_tugas.find(id_tugas)
                                                    if cell: sheet_tugas.update_cell(cell.row, 5, "CANCELED")
                                                except: pass
                                                kirim_notif_wa(f"🚫 *BATAL*\n👤 *Editor:* {staf_nama}\n🆔 *ID:* {id_tugas}\n📝: {cat_r}")
                                                st.error("BATAL!"); time.sleep(1); st.rerun()
                                            else:
                                                st.error("Isi alasan batal di kolom catatan!")

                                # --- PANEL STAFF (SETOR) ---
                                elif user_level in ["STAFF", "UPLOADER", "ADMIN"]: 
                                    st.markdown("---")
                                    l_in = st.text_input("Paste Link GDrive:", value=t.get("LINK_HASIL", ""), key=f"l_{id_tugas}")
                                    if st.button("🚀 SETOR", key=f"b_{id_tugas}", use_container_width=True):
                                        if l_in.strip() and "drive.google.com" in l_in.lower():
                                            # Update Supabase
                                            supabase.table("Tugas").update({
                                                "Status": "WAITING QC", 
                                                "Link_Hasil": l_in, 
                                                "Waktu_Kirim": sekarang.strftime("%d/%m/%Y %H:%M")
                                            }).eq("ID", id_tugas).execute()
                                            
                                            # Update GSheet (Silent)
                                            try:
                                                cell = sheet_tugas.find(id_tugas)
                                                if cell:
                                                    sheet_tugas.update_cell(cell.row, 5, "WAITING QC")
                                                    sheet_tugas.update_cell(cell.row, 7, l_in)
                                            except: pass
                                            
                                            kirim_notif_wa(f"📤 *SETORAN*\n👤 *Editor:* {staf_nama}\n🆔 *ID:* {id_tugas}")
                                            st.success("Terkirim!"); time.sleep(1); st.rerun()
                                        else:
                                            st.error("Hanya boleh Link Google Drive!")

    # =========================================================
    # --- 4.5. SISTEM KLAIM AI (FIXED INDENTATION) ---
    # =========================================================
    if user_level in ["STAFF", "ADMIN", "UPLOADER"]:
        st.write("")
        
        with st.expander("⚡ KLAIM AKUN AI DISINI", expanded=False):
            try:
                # 1. SETUP WAKTU & KONEKSI
                tz_jakarta = pytz.timezone('Asia/Jakarta')
                h_ini = datetime.now(tz_jakarta).date()

                sh_ai = get_gspread_sh() 
                ws_akun = sh_ai.worksheet("Akun_AI")
                df_ai = pd.DataFrame(ws_akun.get_all_records())

                # 2. FILTER AKUN AKTIF MILIK USER
                user_up = user_sekarang.upper().strip()
                df_ai['EXPIRED_DT'] = pd.to_datetime(df_ai['EXPIRED'], errors='coerce').dt.date
                
                # Akun yang sedang dipegang user dan belum expired
                df_user_aktif = df_ai[
                    (df_ai['PEMAKAI'].astype(str).str.upper() == user_up) & 
                    (df_ai['EXPIRED_DT'] >= h_ini)
                ].copy()
                
                akun_aktif_user = df_user_aktif.to_dict('records')

                # 3. LOGIKA STOK (Hanya tampilkan yang PEMAKAI='X' dan BELUM EXPIRED)
                # Catatan: Sesuaikan 'X' atau kosong sesuai standar GSheet lo
                df_stok = df_ai[
                    (df_ai['PEMAKAI'].astype(str).str.upper() == 'X') & 
                    (df_ai['EXPIRED_DT'] > h_ini)
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

                # --- GANTI BAGIAN INI (Step 3) ---
                if c_btn.button("🔓 KLAIM AKUN", use_container_width=True, disabled=not bisa_klaim):
                    # 1. CEK LOCK (Supaya tidak double click saat internet lag)
                    if f"lock_ai_{user_up}" in st.session_state:
                        st.warning("Sabar Bos, lagi diproses...")
                    else:
                        st.session_state[f"lock_ai_{user_up}"] = True
                        
                        try:
                            # 2. AMBIL STOK PERTAMA (Ganti .sample(1) jadi .iloc[0])
                            # Ini penting supaya kalau Icha & Nissa barengan, gak dapet email yang sama
                            target_df = df_stok[df_stok['AI'] == pilihan_ai]
                            
                            if not target_df.empty:
                                target = target_df.iloc[0] 
                                email_target = str(target['EMAIL']).strip()
                                
                                # 3. PROSES KE GSHEET
                                cell = ws_akun.find(email_target, in_column=2)
                                if cell:
                                    ws_akun.update_cell(cell.row, 5, user_up) 
                                    ws_akun.update_cell(cell.row, 6, h_ini.strftime("%Y-%m-%d"))
                                    
                                    # Kirim Notif & Log
                                    kirim_notif_wa(f"🔑 *KLAIM AKUN AI*\n\n👤 *User:* {user_up}\n🛠️ *Tool:* {pilihan_ai}\n📧 *Email:* {email_target}")
                                    tambah_log(user_sekarang, f"KLAIM AKUN AI: {pilihan_ai} ({email_target})")
                                    
                                    st.success(f"Berhasil! Akun {pilihan_ai} sekarang milikmu.")
                                    
                                    # 4. BERSIHKAN LOCK & REFRESH
                                    del st.session_state[f"lock_ai_{user_up}"]
                                    time.sleep(1)
                                    st.rerun()
                            else:
                                st.error("Yah, barusan diambil orang lain. Coba tool lain ya!")
                                del st.session_state[f"lock_ai_{user_up}"]
                                
                        except Exception as e:
                            # Lepas lock kalau error biar bisa coba lagi
                            if f"lock_ai_{user_up}" in st.session_state:
                                del st.session_state[f"lock_ai_{user_up}"]
                            st.error(f"Gagal klaim: {e}")

                # 4. DAFTAR KOLEKSI (Tampilan 3 Kolom Premium Lo)
                if akun_aktif_user:
                    st.divider()
                    kolom_vcard = st.columns(3) 
                    
                    for idx, r in enumerate(reversed(akun_aktif_user)):
                        sisa = (r['EXPIRED_DT'] - h_ini).days
                        warna_h = "#1d976c" if sisa > 7 else "#f39c12" if sisa >= 0 else "#e74c3c"
                        stat_ai = "🟢 AMAN" if sisa > 7 else "🟠 LIMIT" if sisa >= 0 else "🔴 MATI"

                        with kolom_vcard[idx % 3]:
                            with st.container(border=True):
                                st.markdown(f"""
                                    <div style="text-align:center; padding:3px; background:{warna_h}; border-radius:8px 8px 0 0; margin:-15px -15px 10px -15px;">
                                        <b style="color:white; font-size:11px;">{str(r['AI']).upper()}</b>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                e1, e2 = st.columns(2)
                                e1.markdown(f"<p style='margin:10px 0 0 0; font-size:10px; color:#888;'>📧 EMAIL</p><code style='font-size:13px; display:block; overflow:hidden; text-overflow:ellipsis;'>{r['EMAIL']}</code>", unsafe_allow_html=True)
                                e2.markdown(f"<p style='margin:10px 0 0 0; font-size:10px; color:#888;'>🔑 PASS</p><code style='font-size:13px; display:block;'>{r['PASSWORD']}</code>", unsafe_allow_html=True)
                                
                                st.write("")
                                s1, s2, s3 = st.columns(3)
                                s1.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>STATUS</p><b style='font-size:11px;'>{stat_ai}</b>", unsafe_allow_html=True)
                                s2.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>EXP</p><b style='font-size:11px;'>{r['EXPIRED_DT'].strftime('%d %b')}</b>", unsafe_allow_html=True)
                                s3.markdown(f"<p style='margin:0; font-size:9px; color:#888;'>SISA</p><b style='font-size:12px; color:{warna_h};'>{sisa} Hr</b>", unsafe_allow_html=True)

                st.caption("🆘 **Darurat?** Jika akun suspend, hubungi Admin (Dian).")

            except Exception as e_station:
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
                df_laci.sort_values(by=['DEADLINE', 'ID'], ascending=[False, False])[kolom_fix],
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

    # 2. SETUP WAKTU (Wajib di atas agar variabel 'sekarang' terbaca semua modul)
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

    # 4. KONEKSI MASTER (Satu koneksi untuk semua expander di bawah)
    sh = get_gspread_sh()
    
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
        df_log   = ambil_data_segar("Log_Aktivitas") # <--- CCTV Lo masuk sini

        # Hitung target display (logika lo tetep jalan)
        t_target_display = len(df_staff) * 40

        # --- 2. FUNGSI SARING TANGGAL (OPTIMASI SUPABASE) ---
        def saring_tgl(df, kolom, bln, thn):
            if df.empty or kolom.upper() not in df.columns: return pd.DataFrame()
            # Pastikan kolom tanggal jadi format waktu Python yang benar
            df['TGL_TEMP'] = pd.to_datetime(df[kolom.upper()], errors='coerce')
            mask = df['TGL_TEMP'].apply(lambda x: x.month == bln and x.year == thn if pd.notnull(x) else False)
            return df[mask].copy()

        # Jalankan filter untuk semua tabel (Data otomatis tersaring sesuai bulan/tahun pilihan lo)
        df_t_bln = saring_tgl(df_tugas, 'DEADLINE', bulan_dipilih, tahun_dipilih)
        df_a_f   = saring_tgl(df_absen, 'TANGGAL', bulan_dipilih, tahun_dipilih)
        df_k_f   = saring_tgl(df_kas, 'TANGGAL', bulan_dipilih, tahun_dipilih)
        df_log_f = saring_tgl(df_log, 'WAKTU', bulan_dipilih, tahun_dipilih)

         # --- 3. LOGIKA REKAP (VERSI SUPER SAKTI ANTI-CRASH) ---
        rekap_harian_tim = {}
        rekap_total_video = {}

        # --- 1. PROSES FILTER DATA (WAJIB ADA DI ATAS) ---
        # Pastikan df_t_bln didefinisikan dulu dari hasil saring_tgl
        if not df_t_bln.empty and 'STATUS' in df_t_bln.columns:
            df_f_f = df_t_bln[df_t_bln['STATUS'].astype(str).str.upper() == "FINISH"].copy()
        else:
            # Jika data kosong, buat DataFrame kosong dengan kolom default agar tidak 'not defined'
            df_f_f = pd.DataFrame(columns=['STAF', 'STATUS', 'TGL_TEMP'])

        # --- 2. LOGIKA REKAP (VERSI SUPER SAKTI) ---
        rekap_harian_tim = {}
        rekap_total_video = {}

        # Sekarang df_f_f PASTI ada wujudnya (biarpun kosong)
        if not df_f_f.empty and 'STAF' in df_f_f.columns:
            df_f_f['STAF'] = df_f_f['STAF'].astype(str).str.strip().str.upper()
            
            if 'TGL_TEMP' in df_f_f.columns:
                df_f_f['TGL_STR'] = df_f_f['TGL_TEMP'].dt.strftime('%Y-%m-%d')
                
                # Groupby aman karena df_f_f sudah divalidasi
                try:
                    rekap_harian_tim = df_f_f.groupby(['STAF', 'TGL_STR']).size().unstack(fill_value=0).to_dict('index')
                except:
                    rekap_harian_tim = {}
            
            rekap_total_video = df_f_f['STAF'].value_counts().to_dict()
        else:
            # Fallback aman kalau Maret masih nol
            rekap_harian_tim = {}
            rekap_total_video = {}

        performa_staf = {} 

        # --- KALKULASI KEUANGAN RIIL ---
        inc = 0
        ops = 0
        bonus_terbayar_kas = 0
        
        if not df_k_f.empty:
            df_k_f['NOMINAL'] = pd.to_numeric(df_k_f['NOMINAL'].astype(str).replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
            inc = df_k_f[df_k_f['TIPE'] == 'PENDAPATAN']['NOMINAL'].sum()
            # Ops adalah pengeluaran SELAIN Gaji Tim
            ops = df_k_f[(df_k_f['TIPE'] == 'PENGELUARAN') & (df_k_f['KATEGORI'] != 'Gaji Tim')]['NOMINAL'].sum()
            # Bonus Terbayar adalah yang sudah masuk ke Arus Kas via tombol ACC
            bonus_terbayar_kas = df_k_f[(df_k_f['TIPE'] == 'PENGELUARAN') & (df_k_f['KATEGORI'] == 'Gaji Tim')]['NOMINAL'].sum()

        # --- HITUNG ESTIMASI GAJI POKOK REAL (STAFF & ADMIN) ---
        total_gaji_pokok_tim = 0
        is_masa_depan = tahun_dipilih > sekarang.year or (tahun_dipilih == sekarang.year and bulan_dipilih > sekarang.month)
        
        # FILTER: Ambil STAFF dan ADMIN. OWNER (Dian) jangan dimasukkan agar saldo tetap rahasia.
        df_staff_real = df_staff[df_staff['LEVEL'].isin(['STAFF', 'UPLOADER', 'ADMIN'])]

        if not is_masa_depan:
            for _, s in df_staff_real.iterrows():
                n_up = str(s.get('NAMA', '')).strip().upper()
                if n_up == "" or n_up == "NAN": continue
                
                # --- 1. IDENTIFIKASI LEVEL TARGET (KUNCI UTAMA) ---
                lv_asli = str(s.get('LEVEL', 'STAFF')).strip().upper()
                
                # --- 2. SINKRON: Ambil Data Harian ---
                df_a_staf = df_a_f[df_a_f['NAMA'] == n_up].copy()
                df_t_staf = df_f_f[df_f_f['STAF'] == n_up].copy()

                # --- 3. PANGGIL MESIN (Suntik lv_asli agar Kebal SP aktif) ---
                _, _, pot_sp_real, _, _ = hitung_logika_performa_dan_bonus(
                    df_t_staf, df_a_staf, bulan_dipilih, tahun_dipilih,
                    level_target=lv_asli 
                )
                
                # --- 4. HITUNG GAJI NETT ---
                g_pokok = int(pd.to_numeric(str(s.get('GAJI_POKOK')).replace('.',''), errors='coerce') or 0)
                t_tunj = int(pd.to_numeric(str(s.get('TUNJANGAN')).replace('.',''), errors='coerce') or 0)
                
                # Admin pasti pot_sp_real = 0 karena level_target="ADMIN" sudah dikirim ke mesin
                gaji_nett = max(0, (g_pokok + t_tunj) - pot_sp_real)
                
                total_gaji_pokok_tim += gaji_nett

        # TOTAL OUTCOME SINKRON (Uang Keluar Real: Staff + Admin)
        total_pengeluaran_gaji = total_gaji_pokok_tim + bonus_terbayar_kas
        total_out = total_pengeluaran_gaji + ops
        saldo_bersih = inc - total_out
        
        # ======================================================================
        # --- UI: FINANCIAL COMMAND CENTER (CUSTOM LAYOUT) ---
        # ======================================================================
        with st.expander("💰 ANALISIS KEUANGAN & KAS", expanded=False):
            
            # --- FIX TIPE DATA FINANSIAL SEBELUM TAMPIL ---
            inc_val = float(inc)
            # Pastikan bonus terbayar dan ops sudah angka murni
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
            
            # Formasi Baru: Input (1) - Logs (1.2) - Viz (1)
            col_input, col_logs, col_viz = st.columns([1, 1.2, 1], gap="small")

            with col_input:
                with st.form("form_kas_new", clear_on_submit=True):
                    f_tipe = st.pills("Tipe", ["PENDAPATAN", "PENGELUARAN"], default="PENGELUARAN", label_visibility="collapsed")
                    f_kat = st.selectbox("Kategori", ["YouTube", "Brand Deal", "Gaji Tim", "Operasional", "Lainnya"], label_visibility="collapsed")
                    f_nom = st.number_input("Nominal", min_value=0, step=50000, label_visibility="collapsed", placeholder="Nominal Rp...")
                    f_ket = st.text_area("Keterangan", height=65, label_visibility="collapsed", placeholder="Catatan...")
                    if st.form_submit_button("🚀 SIMPAN", use_container_width=True):
                        if f_nom > 0:
                            # --- 1. SINKRON KE SUPABASE (UNTUK RADAR KILAT) ---
                            data_kas_sb = {
                                "Tanggal": sekarang.strftime('%Y-%m-%d'),
                                "Tipe": f_tipe,
                                "Kategori": f_kat,
                                "Nominal": str(int(f_nom)),
                                "Keterangan": f_ket,
                                "Pencatat": user_sekarang.upper()
                            }
                            supabase.table("Arus_Kas").insert(data_kas_sb).execute()

                            # --- 2. GSHEET TETAP JALAN (MASTER DATA) ---
                            sh.worksheet("Arus_Kas").append_row([
                                sekarang.strftime('%Y-%m-%d'), 
                                f_tipe, 
                                f_kat, 
                                str(int(f_nom)),
                                f_ket, 
                                user_sekarang.upper()
                            ])
                            
                            # --- 3. CATAT LOG AKTIVITAS (CCTV) ---
                            tambah_log(user_sekarang, f"INPUT KAS: {f_tipe} - {f_kat} (Rp {f_nom:,.0f})")

                            st.success("Tersimpan!"); time.sleep(1); st.rerun()
                        else:
                            st.warning("Nominal harus lebih dari 0!")

            with col_logs:
                # Log Terakhir: Batasi 5 Transaksi Saja
                with st.container(height=315):
                    if not df_k_f.empty:
                        # Ambil hanya 6 baris terbaru
                        df_logs_display = df_k_f.sort_values(by='TGL_TEMP', ascending=False).head(8)
                        for _, r in df_logs_display.iterrows():
                            color = "#00ba69" if r['TIPE'] == "PENDAPATAN" else "#ff4b4b"
                            st.markdown(f"""
                            <div style='font-size:11px; border-bottom:1px solid #333; padding:4px 0;'>
                                <b style='color:#ccc;'>{r['KATEGORI']}</b> 
                                <span style='float:right; color:{color}; font-weight:bold;'>Rp {float(r['NOMINAL']):,.0f}</span><br>
                                <span style='color:#666; font-style:italic;'>{r['KETERANGAN']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("Belum ada data transaksi.")

            with col_viz:
                st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
                
                # Update data donut biar pake angka yang udah di-fix
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
        # --- 4. MASTER MONITORING & RADAR TIM (VERSI VISUAL PRO - SYNCED) ---
        # ======================================================================
        st.write(""); st.markdown("### 📡 RADAR PERFORMA TIM")
        
        kolom_card = st.columns(4)
        rekap_v_total, rekap_b_cair, rekap_b_absen, rekap_h_malas = 0, 0, 0, 0
        performa_staf = {}

        # --- FIX: Loop dari STAFF biar Icha & Nissa gak ilang ---
        df_staff_filtered = df_staff[df_staff['LEVEL'].isin(['STAFF', 'UPLOADER', 'ADMIN'])]

        for idx, s in df_staff_filtered.reset_index().iterrows():
            n_up = str(s.get('NAMA', '')).strip().upper()
            if n_up == "" or n_up == "NAN": continue
            
            # --- FIX: Proteksi filter agar Maret tidak error ---
            df_a_staf_r = df_a_f[df_a_f['NAMA'] == n_up].copy() if not df_a_f.empty else pd.DataFrame(columns=['NAMA', 'TANGGAL'])
            df_t_staf_r = df_f_f[df_f_f['STAF'] == n_up].copy() if not df_f_f.empty else pd.DataFrame(columns=['STAF', 'STATUS'])

            lv_staf_ini = str(s.get('LEVEL', 'STAFF')).strip().upper()
            
            # Mesin hitung tetep jalan dengan pengaman
            try:
                b_lembur_staf, u_absen_staf, pot_sp_r, level_sp_r, h_lemah_staf = hitung_logika_performa_dan_bonus(
                    df_t_staf_r, df_a_staf_r, bulan_dipilih, tahun_dipilih,
                    level_target=lv_staf_ini
                )
            except:
                b_lembur_staf, u_absen_staf, pot_sp_r, level_sp_r, h_lemah_staf = 0, 0, 0, "NORMAL", 0
            
            # --- LOGIKA SINKRONISASI BONUS DARI KAS (LIVE) ---
            bonus_real_staf = 0
            if not df_kas.empty:
                df_kas_temp = df_kas.copy()
                df_kas_temp['NOMINAL_INT'] = pd.to_numeric(df_kas_temp['NOMINAL'].astype(str).replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
                
                # Filter Periode & Nama Staf
                mask_staf_kas = (df_kas_temp['KATEGORI'].str.upper() == 'GAJI TIM') & \
                                (df_kas_temp['KETERANGAN'].str.upper().str.contains(n_up, na=False)) & \
                                (pd.to_datetime(df_kas_temp['TANGGAL'], errors='coerce').dt.month == bulan_dipilih)
                
                bonus_real_staf = df_kas_temp[mask_staf_kas]['NOMINAL_INT'].sum()
            
            jml_v = len(df_t_staf_r)
            rekap_v_total += jml_v
            performa_staf[n_up] = jml_v
            
            # --- FIX: JML CANCEL (Proteksi empty) ---
            jml_cancel = 0
            if not df_t_bln.empty and 'STAF' in df_t_bln.columns:
                jml_cancel = len(df_t_bln[(df_t_bln['STAF'] == n_up) & (df_t_bln['STATUS'].astype(str).str.upper() == 'CANCELED')])
            
            h_cair = 0
            if n_up in rekap_harian_tim:
                h_cair = sum(1 for qty in rekap_harian_tim[n_up].values() if qty >= 3)
            
            rekap_b_cair += bonus_real_staf 
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
                    det2.markdown(f"<p style='margin:5px 0 0 0; font-size:10px; color:#888;'>💰 TOTAL BONUS</p><b style='font-size:12px; color:#1d976c;'>Rp {int(bonus_real_staf):,}</b>", unsafe_allow_html=True)
                    
                    # Progress bar pengaman (Max 1.0)
                    prog_val = min(h_lemah_staf / 7, 1.0) if h_lemah_staf > 0 else 0.0
                    st.progress(prog_val)
                    
        # ======================================================================
        # --- 5. RANGKUMAN KOLEKTIF TIM (VERSI FIX BONUS VIDEO & LEMBUR) ---
        # ======================================================================
        with st.container(border=True):
            st.markdown("<p style='font-size:12px; font-weight:bold; color:#888; margin-bottom:15px;'>📊 RANGKUMAN KOLEKTIF TIM</p>", unsafe_allow_html=True)
            
            # 1. Ambil Nama Staff Aktif
            nama_staff_asli = df_staff[df_staff['LEVEL'] == 'STAFF']['NAMA'].str.upper().tolist()
            performa_hanya_staff = {k: v for k, v in performa_staf.items() if k in nama_staff_asli}
            
            # Pengaman MVP & LOW: Jika semua masih 0, jangan tampilkan error
            if performa_hanya_staff and any(v > 0 for v in performa_hanya_staff.values()):
                staf_top = max(performa_hanya_staff, key=performa_hanya_staff.get)
                staf_low = min(performa_hanya_staff, key=performa_hanya_staff.get)
            else:
                staf_top = "-"
                staf_low = "-"
            
            # --- LOGIKA SINKRONISASI KAS (FIXED) ---
            df_kas_kolektif = ambil_data_segar("Arus_Kas")
            real_b_video_kolektif = 0
            real_b_absen_kolektif = 0
            
            if not df_kas_kolektif.empty:
                df_kas_kolektif.columns = [str(c).strip().upper() for c in df_kas_kolektif.columns]
                
                # Filter Periode: Konsisten dengan filter bulan/tahun pilihan
                df_kas_kolektif['TANGGAL_DT'] = pd.to_datetime(df_kas_kolektif['TANGGAL'], errors='coerce')
                mask_periode = (df_kas_kolektif['TANGGAL_DT'].dt.month == bulan_dipilih) & \
                               (df_kas_kolektif['TANGGAL_DT'].dt.year == tahun_dipilih)
                
                df_cair = df_kas_kolektif[mask_periode].copy()
                
                if not df_cair.empty:
                    # Pastikan Nominal bersih dari karakter aneh
                    df_cair['NOMINAL_FIX'] = pd.to_numeric(df_cair['NOMINAL'].astype(str).replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
                    
                    # Logika pencarian kata kunci di keterangan Kas
                    mask_video = (df_cair['KATEGORI'].str.upper() == 'GAJI TIM') & \
                                 (df_cair['KETERANGAN'].str.upper().str.contains('VIDEO|LEMBUR', na=False))
                    real_b_video_kolektif = df_cair[mask_video]['NOMINAL_FIX'].sum()
                    
                    mask_absen = (df_cair['KATEGORI'].str.upper() == 'GAJI TIM') & \
                                 (df_cair['KETERANGAN'].str.upper().str.contains('ABSEN', na=False))
                    real_b_absen_kolektif = df_cair[mask_absen]['NOMINAL_FIX'].sum()

            # --- DISPLAY METRIC (7 KOLOM) ---
            c_r1, c_r2, c_r3, c_r4, c_r5, c_r6, c_r7 = st.columns(7)
            
            target_fix = len(nama_staff_asli) * 60
            c_r1.metric("🎯 TARGET IDEAL", f"{target_fix} Vid") 
            
            persen_capaian = (rekap_v_total / target_fix * 120) if target_fix > 0 else 0
            c_r2.metric("🎬 TOTAL VIDEO", f"{int(rekap_v_total)}", delta=f"{persen_capaian:.1f}%")
            
            c_r3.metric("🔥 BONUS VIDEO", f"Rp {int(real_b_video_kolektif):,}", delta="LIVE SYNC")
            c_r4.metric("📅 BONUS ABSEN", f"Rp {int(real_b_absen_real):,}" if 'real_b_absen_real' in locals() else f"Rp {int(real_b_absen_kolektif):,}", delta="LIVE SYNC")
            
            c_r5.metric("💀 TOTAL LEMAH", f"{rekap_h_malas} HR", delta="Staff Only", delta_color="inverse")
            c_r6.metric("👑 MVP STAF", staf_top)
            c_r7.metric("📉 LOW STAF", staf_low)

        # ======================================================================
        # --- 7. DATABASE AKUN AI (VERSI ASLI DIAN - INDENTASI TERKUNCI) ---
        # ======================================================================
        with st.expander("🔐 DATABASE AKUN AI", expanded=False):
            try:
                # 1. Ambil Data
                ws_akun = sh.worksheet("Akun_AI")
                data_akun_raw = ws_akun.get_all_records()
                df_ai = pd.DataFrame(data_akun_raw)
                
                # 2. Tombol Tambah Akun
                if st.button("➕ TAMBAH AKUN BARU", use_container_width=True):
                    st.session_state.form_ai = not st.session_state.get('form_ai', False)
                
                if st.session_state.get('form_ai', False):
                    with st.form("input_ai_simple", clear_on_submit=True):
                        f1, f2, f3 = st.columns(3)
                        v_ai = f1.text_input("Nama Tool (ChatGPT/Midjourney)")
                        v_mail = f2.text_input("Email Login")
                        v_pass = f3.text_input("Password")
                        v_exp = st.date_input("Tanggal Expired")
                        if st.form_submit_button("🚀 SIMPAN KE GSHEET"):
                            # Tambahkan "X" di kolom PEMAKAI agar langsung bisa diklaim staf
                            # Tambahkan "" di kolom TANGGAL_KLAIM agar rapi
                            ws_akun.append_row([v_ai, v_mail, v_pass, str(v_exp), "X", ""])
                            st.success("Berhasil Tersimpan!"); time.sleep(1); st.rerun()

                st.divider()
                        
                if not df_ai.empty:
                    # 1. SETUP TANGGAL & PRIORITAS
                    h_ini = sekarang.date()
                    df_ai['TGL_OBJ'] = pd.to_datetime(df_ai['EXPIRED'], errors='coerce').dt.date
                    
                    def tentukan_urutan(r):
                        if pd.isna(r['TGL_OBJ']): return 4
                        
                        sisa_hr = (r['TGL_OBJ'] - h_ini).days
                        
                        # --- LOGIKA PENENTU KOSONG (LEBIH GALAK) ---
                        val_pemakai = str(r.get('PEMAKAI', '')).strip()
                        
                        # Cek: Apakah NaN, apakah string kosong, atau cuma spasi
                        is_kosong = pd.isna(r['PEMAKAI']) or val_pemakai == "" or val_pemakai.upper() == "X"
                        
                        # PRIORITAS 1: BENAR-BENAR KOSONG (Contoh: lisaluk80)
                        if is_kosong: 
                            return 1
                        # PRIORITAS 2: MAU EXPIRED (Ada pemakai & sisa <= 7 hari)
                        elif sisa_hr <= 7: 
                            return 2
                        # PRIORITAS 3: MASIH LAMA (Ada pemakai & sisa > 7 hari)
                        else: 
                            return 3

                    # Terapkan skoring
                    df_ai['PRIO'] = df_ai.apply(tentukan_urutan, axis=1)
                    
                    # SORTING: Prioritas (1-2-3), lalu Tanggal Expired (Paling Dekat di atas)
                    df_sorted = df_ai.sort_values(by=['PRIO', 'TGL_OBJ'], ascending=[True, True]).copy()

                    # 2. LOOPING TAMPILAN (Gunakan df_sorted)
                    for idx, r in df_sorted.iterrows():
                        tgl_exp = r['TGL_OBJ']
                        if pd.isna(tgl_exp): continue
                        
                        sisa = (tgl_exp - h_ini).days
                        if sisa < 0: continue # Sembunyikan yang sudah lewat
                        
                        # Penentu Warna Muted (Deep Forest & Burnt Orange)
                        if sisa > 7: warna_h, stat_ai = "#2D5A47", "🟢 AMAN"
                        elif 0 <= sisa <= 7: warna_h, stat_ai = "#8B5E3C", "🟠 LIMIT"
                        else: warna_h, stat_ai = "#633535", "🔴 MATI"

                        with st.container(border=True):
                            # HEADER TOOL (Gaya Original Dian)
                            st.markdown(f"""
                                <div style="padding:2px; background:{warna_h}; border-radius:5px; margin-bottom:10px; text-align:center;">
                                    <b style="color:white; font-size:11px;">🚀 {str(r['AI']).upper()}</b>
                                </div>
                            """, unsafe_allow_html=True)

                            # 7 KOLOM SEJAJAR
                            c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1.5, 1, 1, 1, 0.8, 1.2])
                            
                            c1.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>📧 EMAIL</p><code style='font-size:12px !important;'>{r['EMAIL']}</code>", unsafe_allow_html=True)
                            c2.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>🔑 PASSWORD</p><code style='font-size:12px !important;'>{r['PASSWORD']}</code>", unsafe_allow_html=True)
                            
                            # TAMPILAN USER (Kasih tanda 🆕 biar mencolok kalau kosong)
                            val_user = str(r['PEMAKAI']).strip()
                            is_null = pd.isna(r['PEMAKAI']) or val_user == "" or val_user.upper() == "X"
                            user_display = "🆕 KOSONG" if is_null else r['PEMAKAI']
                            
                            c3.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>👤 PEMAKAI</p><b style='font-size:12px;'>{user_display}</b>", unsafe_allow_html=True)
                            c4.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>📡 STATUS</p><b style='font-size:11px;'>{stat_ai}</b>", unsafe_allow_html=True)
                            c5.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>📅 EXPIRED</p><b style='font-size:11px;'>{tgl_exp.strftime('%d %b')}</b>", unsafe_allow_html=True)
                            c6.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>⏳ SISA</p><b style='font-size:13px; color:{warna_h};'>{sisa} Hr</b>", unsafe_allow_html=True)
                            
                            if c7.button(f"🔄 RESET", key=f"res_{r['EMAIL']}_{idx}", use_container_width=True):
                                try:
                                    cell_target = ws_akun.find(str(r['EMAIL']).strip(), in_column=2)
                                    if cell_target:
                                        ws_akun.update_cell(cell_target.row, 5, "X")
                                        ws_akun.update_cell(cell_target.row, 6, "")
                                        st.success(f"✅ Berhasil Reset!"); time.sleep(0.5); st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal: {e}")
                else:
                    # ELSE UNTUK DF_AI EMPTY
                    st.info("📭 Belum ada data akun AI di database.")

            except Exception as e_ai:
                st.error(f"Gagal memuat Database Akun AI: {e_ai}")
            
        # ======================================================================
        # --- 6. RINCIAN GAJI & SLIP (FULL VERSION - SINKRON HARIAN) ---
        # ======================================================================
        with st.expander("💰 RINCIAN GAJI & SLIP", expanded=False):
            try:
                ada_kerja = False
                df_staff_raw_slip = df_staff[df_staff['LEVEL'].isin(['STAFF', 'UPLOADER', 'ADMIN'])].copy()
                kol_v = st.columns(2) 
                
                # --- 0. TARIK DATA KAS MASTER SEKALI SAJA (SINKRON MARET) ---
                df_kas_master = ambil_data_segar("Arus_Kas")
                if not df_kas_master.empty:
                    df_kas_master.columns = [str(c).strip().upper() for c in df_kas_master.columns]
                    df_kas_master['TGL_DT'] = pd.to_datetime(df_kas_master['TANGGAL'], errors='coerce')
                
                for idx, s in df_staff_raw_slip.reset_index().iterrows():
                    n_up = str(s.get('NAMA', '')).strip().upper()
                    if n_up == "" or n_up == "NAN": continue
                    
                    # --- 1. DATA FILTERING SPESIFIK STAF ---
                    df_absen_staf_slip = df_a_f[df_a_f['NAMA'] == n_up].copy() if not df_a_f.empty else pd.DataFrame()
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
                    
                    # --- 4. FILTER DATA BONUS RIIL ---
                    bonus_video_real = 0
                    bonus_absen_real = 0
                    
                    if not df_kas_master.empty:
                        df_k_slip = df_kas_master.copy()
                        df_k_slip['NOMINAL_INT'] = pd.to_numeric(df_k_slip['NOMINAL'].astype(str).replace(r'[^\d]', '', regex=True), errors='coerce').fillna(0)
                        
                        mask_slip = (df_k_slip['KATEGORI'].str.upper() == 'GAJI TIM') & \
                                    (df_k_slip['KETERANGAN'].str.upper().str.contains(n_up, na=False)) & \
                                    (df_k_slip['TGL_DT'].dt.month == bulan_dipilih) & \
                                    (df_k_slip['TGL_DT'].dt.year == tahun_dipilih)
                        
                        df_bonus_cair = df_k_slip[mask_slip]
                        if not df_bonus_cair.empty:
                            bonus_video_real = int(df_bonus_cair[df_bonus_cair['KETERANGAN'].str.upper().str.contains('VIDEO|LEMBUR', na=False)]['NOMINAL_INT'].sum())
                            bonus_absen_real = int(df_bonus_cair[df_bonus_cair['KETERANGAN'].str.upper().str.contains('ABSEN', na=False)]['NOMINAL_INT'].sum())

                    # --- 5. RUMUS FINAL ---
                    v_total_terima = max(0, (v_gapok + v_tunjangan + bonus_absen_real + bonus_video_real) - pot_sp_admin)
                    ada_kerja = True

                    # --- 6. TAMPILAN VCARD ---
                    with kol_v[idx % 2]:
                        with st.container(border=True):
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
                            c1.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>ESTIMASI TERIMA</p><h3 style='margin:0; color:#1d976c;'>Rp {v_total_terima:,}</h3>", unsafe_allow_html=True)
                            c2.markdown(f"<p style='margin:0; font-size:10px; color:#888;'>STATUS SP</p><b style='font-size:14px; color:{'#e74c3c' if pot_sp_admin > 0 else '#1d976c'};'>{level_sp_admin}</b>", unsafe_allow_html=True)
                            
                            st.divider()

                            if st.button(f"📄 PREVIEW & PRINT SLIP {n_up}", key=f"vcard_{n_up}", use_container_width=True):
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
        # --- 8. PINTAR COMMAND CENTER (SUNTIK ABSEN & IZIN) ---
        # ======================================================================
        with st.expander("🛠️ PINTAR COMMAND CENTER", expanded=False):
            st.info("Gunakan ini untuk intervensi data (HADIR/IZIN/SAKIT).")
            
            # PAKAI df_staff (Sesuai kode lo di atas)
            list_staf = df_staff[df_staff['LEVEL'] != 'OWNER']['NAMA'].unique().tolist()
            
            c_staf, c_aksi, c_tgl = st.columns([1.5, 1.5, 1])
            with c_staf: target = st.selectbox("Pilih Staf:", list_staf, key="cmd_staf")
            with c_aksi: status_baru = st.selectbox("Set Status:", ["HADIR", "IZIN", "SAKIT", "OFF", "TELAT"], key="cmd_stat")
            with c_tgl: tgl_cmd = st.date_input("Tanggal:", value=sekarang.date(), key="cmd_tgl")
            
            if st.button("🔥 EKSEKUSI PERUBAHAN", use_container_width=True):
                tgl_s = tgl_cmd.strftime("%Y-%m-%d")
                jam_s = "08:00" if status_baru == "HADIR" else "-"
                
                try:
                    # 1. Update Supabase (Tabel Absensi)
                    res = supabase.table("Absensi").select("id").eq("Nama", target).eq("Tanggal", tgl_s).execute()
                    if len(res.data) > 0:
                        supabase.table("Absensi").update({"Status": status_baru, "Jam Masuk": jam_s}).eq("Nama", target).eq("Tanggal", tgl_s).execute()
                    else:
                        supabase.table("Absensi").insert({"Nama": target, "Tanggal": tgl_s, "Status": status_baru, "Jam Masuk": jam_s}).execute()
                    
                    # 2. Update GSheet (Backup)
                    try:
                        ws_abs = sh.worksheet("Absensi")
                        # Cari baris yang cocok (ini asumsi sederhana, cari nama)
                        c_find = ws_abs.find(target)
                        if c_find:
                            # Update kolom status (biasanya kolom 4 atau 5 sesuai format lo)
                            ws_abs.update_cell(c_find.row, 4, status_baru)
                    except: pass

                    st.success(f"✅ Berhasil! {target} sekarang {status_baru}"); time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"Gagal: {e}")

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
            st.warning("🔒 Akses Terbatas!")
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
            bln_ini = now_indo.strftime("%m/%Y") # Hasil: "03/2026"
            
            # Kita filter manual: Status harus SOLD dan di kolom EDITED harus ada teks bulan/tahun ini
            # Contoh: nyari "03/2026" di dalam "Up: DIAN (08/03/2026 20:38)"
            mask_ini = (df['STATUS'] == 'SOLD') & (df['EDITED'].astype(str).str.contains(bln_ini, na=False))
            
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
                                            if h in [1, 3, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]:
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
            st.warning("🔒 Akses Terbatas!")
        else:
            st.markdown("#### 🚀 MONITORING PROSES (MAX 2 SLOT HP)")
            # --- TAMBAHAN: ST INFO UNTUK INSTRUKSI STAFF ---
            st.info("""
                💡 **PENGINGAT KHUSUS:**
                1. HP 1-16 isi Konten Sakura
                2. HP 17-23 isi Konten Masjid (aku sendiri yang isi sementara)
                3. WASPADA! HP 1,3,6,7, 10-23 ada 3 channel (login hapus dan stock video disesuaikan)
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

            # --- 2. LOGIKA GENERATE TABEL (GAYA KODE AWAL + TIM BREAK) ---
            df_j['HP_N'] = pd.to_numeric(df_j['HP'], errors='coerce').fillna(999)
            df_display = df_j.sort_values(['HP_N', 'PAGI'])
            
            # PISAHKAN LIST HP JADI 2 KELOMPOK
            list_hp_tim1 = [h for h in df_display['HP'].unique() if pd.to_numeric(h, errors='coerce') <= 15]
            list_hp_tim2 = [h for h in df_display['HP'].unique() if pd.to_numeric(h, errors='coerce') > 15]
            
            # Gabungkan jadi satu list besar tapi kita kasih pembatas (marker)
            # Ini biar kodenya mirip struktur awal lo yang pake loop
            kelompok_tim = [
                {"nama": "LISA (HP 1-15)", "list": list_hp_tim1},
                {"nama": "INGGI (HP 16-23)", "list": list_hp_tim2}
            ]

            html_all_pages = "" 

            for tim in kelompok_tim:
                list_hp_unik = tim["list"]
                if not list_hp_unik: continue
                
                # Loop per 11 HP (sama kayak kode awal lo)
                for start_idx in range(0, len(list_hp_unik), 10):
                    hp_halaman_ini = list_hp_unik[start_idx : start_idx + 10]
                    df_page = df_display[df_display['HP'].isin(hp_halaman_ini)]
                    
                    # Tambahkan div dengan class page-break
                    html_all_pages += f"""
                    <div class="print-container page-break">
                        <div class="header-box">
                            <h2>📋 JADWAL UPLOAD PINTAR MEDIA</h2>
                            <p class="sub">Unit: <b>{tim['nama']}</b> | Periode: <b>{tgl_str}</b></p>
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
                        bg_color = "#FFFFFF" if i % 2 == 0 else "#F4F4F4"
                        
                        html_all_pages += f"""
                            <tr style="background-color: {bg_color} !important;">
                                <td class="col-hp">{hp_view}</td>
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
                        background-color: #FFFFFF !important;
                        color: #1E3A8A !important;
                        padding: 10px; 
                        border: 1px solid #CCC;
                        font-size: 13px;
                        font-weight: bold;
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
            st.error("🔒 Akses Terbatas!")
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
            st.error("🔒 Akses Terbatas!")
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































































