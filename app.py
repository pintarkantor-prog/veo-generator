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
                "An elderly woman with a fuller, rounded facial structure where gravity has taken its toll. "
                "Deep nasolabial folds and heavy jowls that sag past the jawline. "
                "Her eyelids are thick and drooping, almost covering her eyes, with large, soft bags underneath. "
                "The skin texture is thick, porous, and covered in large age spots and liver spots. "
                "A double chin with soft, folded skin textures. No filters, authentic aged volume."
            ),
            "Nenek Simbah": (
                "An extremely elderly Javanese woman, easily appearing over 80 years old. "
                "Her face is a dense and chaotic network of profound, deep wrinkles that completely consume her visage. "
                "Heavy crow's feet, prominent forehead furrows, and sagging skin folds around her neck and jawline, showing significant volume loss. "
                "Authentic weathered skin texture with prominent age spots, visible pores, and raw, uneven pigmentation. "
                "Her expression is deeply weary and sorrowful, with half-lidded, cloudy eyes looking down. "
                "Her lower lip is downturned with a visible quiver, pressed thin against her toothless gums. "
                "Raw, unpolished cinematic skin details. No smooth filters. 100% authentic aged Javanese look."
            ),
            "Nenek Sunda": (
                "A frail and very aged Sundanese grandmother, her face deeply marked by extreme age and sorrow. "
                "An intensely wrinkled forehead with heavy vertical creases between her brows, indicating deep worry and heartbreak. "
                "The skin around her eyes is exceptionally sagging, with heavy dark circles and prominent sagging folds. "
                "Visible skin pores, realistic dry patches, and authentic elderly skin texture with a dull, matte finish. "
                "A deeply melancholic and pensive 'sayu' expression, looking forward with a profoundly sad gaze. "
                "Her lips are pressed together tightly, showing deep, fine lines and natural wrinkles. "
                "Raw elderly skin texture showing authentic sagging and realistic muscle loss in the face. "
                "No smoothing, 100% realistic tired Sundanese face."
            ),
            "Nenek Melayu": (
                "A profoundly elderly Melayu woman, her face a map of extreme age and sorrow. "
                "Her entire countenance is consumed by heavy, sagging wrinkles and deep facial lines. "
                "Her eyes are bright with unshed tears, glistening with unshed tears, showing heavy, reddened eyelids. "
                "The skin around her jaw and neck is severely sagging, showing realistic volume loss and fragility. "
                "Visible age spots, prominent blue veins on her hands and temples, and authentic aged skin texture with clear pores. "
                "Her downturned mouth has a subtle, realistic quiver in her lower lip, emphasizing her grief. "
                "Raw, high-definition skin texture showing authentic age spots and visible pores dampened by a thin layer of cold sweat. "
                "100% high-definition real elderly face, cinematic and hauntingly emotional."
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
                "Daster Batik & Bergo Instan": "Wearing a faded daily batik floral daster with short sleeves, paired with a simple, well-worn comfortable instant jersey bergo hijab covering her head and neck.",
                "Kaos Panjang & Jilbab Kaos": "Wearing a modest, oversized long-sleeved cotton house shirt in faded neutral colors, paired with a simple daily instant jersey hijab and a cotton sarong tied at the waist.",
                "Daster Lowo & Kerudung Lilit": "Wearing a loose, wide 'bat-wing' (lowo) batik patterned daster with a simple thin cotton scarf wrapped loosely and comfortably around her head as a daily hijab.",
                "Baju Kurung Katun & Hijab Slup": "Wearing a simple, humble Indonesian-style modest cotton baju kurung with a practical jersey instant hijab for a neat, grandmotherly home look.",
                "Tunik Kancing & Bergo Tali": "Wearing a front-buttoned cotton tunic shirt with minor wrinkles, paired with an instant bergo hijab that has simple ties at the back of the head.",
                "Setelan Celana Kaos & Jilbab": "Wearing a matching daily pajama set of a long-sleeved cotton tunic and loose trousers in faded colors, paired with a breathable instant jersey hijab."
            },
            "Nenek Simbah": {
                "Kebaya Kutubaru & Jarik Parang": "Wearing a daily-worn, faded floral cotton kebaya kutubaru fastened with a vintage safety pin, paired with a dark-brown batik jarik cloth in Parang motif and a thin cotton scarf loosely wrapped as a hijab.",
                "Daster Batik Solo & Bergo Tali": "Wearing an authentic brown Batik Solo daster with a classic 'Sogan' pattern, paired with a simple jersey instant hijab that has ties at the back, showing a traditional home look.",
                "Kaos Lengan Panjang & Jarik Lawasan": "Wearing a modest long-sleeved cotton shirt in earth tones, paired with a weathered, well-washed 'Lawasan' batik jarik cloth and a simple instant hijab tied neatly under the chin.",
                "Daster Lowo (Kalong) & Kerudung Lilit": "Wearing a loose, oversized 'bat-wing' (lowo) batik daster with a large traditional motif, complemented by a thin cotton scarf wrapped comfortably around her head in a simple village style.",
                "Kebaya Kartini Katun & Sarung": "Wearing a very simple, non-formal cotton Kebaya Kartini in a faded solid color, paired with a comfortable batik sarong and a daily instant bergo hijab for a humble appearance.",
                "Setelan Celana Batik & Jilbab Kaos": "Wearing a matching daily batik pajama set consisting of a long-sleeved tunic and loose trousers, paired with a breathable instant jersey hijab in a matching muted earth tone."
            },
            "Nenek Sunda": {
                "Daster Floral & Bergo Kaos": "Wearing a bright but faded floral-patterned Sundanese-style daster with a soft, well-washed instant jersey bergo hijab that looks comfortable for daily house chores.",
                "Kebaya Bordir Katun & Sarung": "Wearing a simple, humble cotton kebaya with subtle embroidery (bordir) on the edges, paired with a faded floral sarong and a thin cotton scarf loosely draped as a hijab.",
                "Setelan Celana Kaos & Jilbab Instan": "Wearing a modest long-sleeved cotton pajama set with small floral motifs, paired with a simple daily instant jersey hijab in a soft, matching pastel color.",
                "Daster Kancing Depan & Bergo Tali": "Wearing a practical front-buttoned cotton daster in a light color, paired with a simple instant bergo hijab that has ties at the back, perfect for an elderly grandmother's daily look.",
                "Tunik Katun & Sarung Batik": "Wearing a loose, breathable cotton tunic shirt paired with a faded West Javanese batik sarong and a simple daily instant hijab tied neatly under the chin.",
                "Daster Lowo Floral & Kerudung Lilit": "Wearing a wide 'bat-wing' (lowo) daster with a vibrant but aged floral print, complemented by a thin pashmina-style cotton scarf wrapped simply and loosely around her head."
            },
            "Nenek Melayu": {
                "Baju Kurung Kedah & Sarung": "Wearing a traditional short-cut daily Baju Kurung Kedah made of soft faded cotton with floral prints, paired with a matching batik sarong and a simple cotton bawal hijab pinned under the chin.",
                "Baju Kurung Pesak & Tudung Sarung": "Wearing a classic loose-fitting Baju Kurung Pesak in a muted solid color, paired with a practical 'tudung sarung' (instant jersey hijab) that covers the chest comfortably.",
                "Daster Panjang & Hijab Instan": "Wearing a modest long-sleeved cotton daster with traditional Melayu floral motifs, complemented by a simple daily instant jersey hijab in a matching faded tone.",
                "Kaos Tunik & Sarung Pelikat": "Wearing a long-sleeved cotton tunic shirt paired with a faded cotton sarong and a simple bawal hijab loosely draped over her head, showing a relaxed home-stay vibe.",
                "Baju Kurung Moden & Bergo Tali": "Wearing a very simple daily Baju Kurung Moden made of breathable rayon fabric, paired with a simple instant bergo hijab that has ties at the back for comfort.",
                "Kebaya Labuh & Hijab Slup": "Wearing a modest, long-length daily Kebaya Labuh made of lightweight cotton, paired with a faded floral sarong and a practical instant jersey hijab for a neat grandmotherly look."
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
                "Permen Kristal": "A monumental, large-scale 1-meter mosque diorama built entirely from millions of glossy pink bubblegum pieces and turquoise taffy blocks. The architecture looks massive and grand, with tiny detailed sugar-texture patterns that suggest a giant scale. The main dome is a colossal, translucent strawberry jelly sphere filled with a vast galaxy of thousands of twinkling fiber-optic star lights. Every entrance arch is lined with hundreds of tiny, flickering multi-colored sugar-drop LEDs. The shot is a straight-on, eye-level view of the massive candy building, showing its immense size and intricate sugary craftsmanship against a dark background, making the building look like a giant glowing sugary cathedral.",
                "Cokelat Lumer": "A colossal, large-scale 1-meter mosque diorama built entirely from rich, glossy dark chocolate and gold-dusted milk chocolate slabs. The structure is massive and grand, with intricate textures suggesting an immense architectural scale. The main dome is a sphere of smooth, melted chocolate glaze, with powerful multi-colored LED wash lights from beneath (cyan, magenta, yellow) reflecting and swirling on its surface. The tall minarets are wrapped in tightly packed, intensely flickering colorful sugar-fairy lights. All entrance arches are outlined with dancing, vibrant RGB neon strips, casting a magical, colorful glow against the dark, high-contrast background.",
                "Wafer Lego": "A monumental, large-scale 1-meter mosque model constructed from hundreds of layers of vibrant colored wafer sheets and Lego-like plastic blocks. The building is massive, with sharp geometric patterns and intricate details highlighting its giant size. The main dome is made of translucent Lego bricks with dynamic, rapidly pulsing internal multi-colored LED matrix (RGB), creating a colorful disco-like pattern. All minarets are topped with intense multi-colored laser pointers. Every edge and arch of the massive structure is lined with flickering, intensely saturated colorful strip-lights, making the mosque look like a giant glowing toy city under a dark environment.",
                "Jeli & Marshmallow": "A gigantic, large-scale 1-meter mosque diorama built entirely from massive translucent grape-jelly blocks and soft pink marshmallow textures. The structure has a glowing, slightly wobbly look that suggests an enormous scale. The colossal main dome is a sphere of clear gelatin with powerful, colorful fiber-optic lines (purple, green, blue) swirling inside like a galaxy. Every minaret is a tall pillar made of striped colorful candy cane, wrapped in intensely bright, rapidly flickering colorful sugar- fairy lights. The entrance arches are framed by intense colorful (RGB) neon tubing, casting a powerful, saturated multi-colored wash over the entire glossy jelly surface against a dark, high-contrast environment.",
                "Lapis Legit": "A gigantic, large-scale 1-meter mosque model built from hundreds of layers of brown and gold buttery cake textures and glossy syrup glazes. The building is monumental and grand, featuring intricate layered patterns that suggest a massive architectural size. The colossal main dome is a sphere of glowing golden honey with intense internal multi-colored LED wash lights. Every minaret is wrapped in tightly packed, rapidly pulsing colorful fairy lights, with entrance arches outlined in vibrant, dancing RGB neon tubing.",
                "Es Krim Pelangi": "A colossal, large-scale 1-meter mosque diorama made of dense, glossy rainbow-colored ice cream scoops and frozen fruit-syrup layers. The structure looks massive and solid, with a cold, frosted texture suggesting a monumental scale. The main dome is a gigantic sphere of translucent pink-grape jelly filled with thousands of twinkling fiber-optic lights. Every pillar is wrapped in intensely flickering multi-colored fairy lights, while all arches are outlined with vibrant, saturated RGB neon strips that glow powerfully against the dark background.",
                "Keramik Mozaik": "A monumental, large-scale 1-meter mosque diorama constructed from thousands of tiny, glossy multi-colored ceramic tiles and iridescent glass pieces. The architecture is grand and massive, with complex mosaic patterns suggesting a giant scale. The main dome is a colossal sphere of polished turquoise porcelain, glowing from within with powerful multi-colored LED lights. The entire 1-meter structure is traced with intensely bright, flickering RGB neon lines and colorful sugar-drop LEDs around every entrance, creating a magical glowing masterpiece.",
                "Buah Melon": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of glossy cantaloupe melon pieces and translucent green rind blocks. The architecture is massive with a colossal main dome made of polished melon flesh segments glowing with internal multi-colored LED wash lights. Tall minarets crafted from melon rinds are wrapped in intensely flickering colorful LED fairy lights. All entrance arches are outlined with dancing, vibrant RGB neon strips.",
                "Buah Strawberyy": "A gigantic, large-scale 1-meter standalone mosque object built entirely from millions of vibrant red strawberry flesh slices and glossy whipped cream textures. Featuring a colossal main dome made of densely packed strawberry slices with intense internal multi-colored LED wash lights. Every minaret is a tall pillar wrapped in rapidly pulsing colorful fairy lights, with entrance arches outlined in vibrant, dancing RGB neon tubing.",
                "Buah Semangka": "A monumental, large-scale 1-meter standalone mosque object constructed from millions of vibrant red watermelon cubes and glossy green-striped rind blocks. The colossal main dome is a sphere made of densely packed watermelon flesh with thousands of twinkling multi-colored fiber-optic star lights. Every pillar and minaret is wrapped in intensely flickering colorful LED fairy lights and vibrant multi-colored neon strips.",
                "Buah Naga": "A colossal, large-scale 1-meter standalone mosque object built entirely from high-gloss white dragonfruit pieces with black seeds and bright magenta rind slabs. The colossal main dome is a sphere of polished dragonfruit flesh with colorful fiber-optic lines swirling inside. Every minaret is a tall pillar wrapped in intensely bright, flickering colorful LED fairy lights and framed by intense RGB neon tubing.",
                "Buah Pepaya": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of vibrant orange papaya flesh cubes and glossy green-striped rind blocks. The architecture is massive with a colossal main dome made of densely packed, polished papaya segments with black seeds integrated, glowing from within with powerful rotating multi-colored LED wash lights. Tall minarets are crafted from pepaya rinds, wrapped in intensely flickering colorful LED fairy lights. All entrance arches are outlined with dancing, vibrant RGB neon strips.",
                "Buah Jeruk": "A gigantic, large-scale 1-meter standalone mosque object built entirely from millions of vibrant orange citrus pulp sacs and translucent orange rind segments. The building is monumental with a colossal main dome made of thousands of interlocking, glossy orange wedges with powerful internal multi-colored LED wash lights reflecting on its juicy texture. Every minaret is a tall pillar made of tightly packed citrus sacs wrapped in rapidly pulsing colorful fairy lights, with entrance arches outlined in vibrant, dancing RGB neon tubing.",
                "Buah Anggur": "A monumental, large-scale 1-meter standalone mosque object constructed from thousands of glossy purple and green grape halves and intricate grape-vine textures. The colossal main dome is a sphere made of densely packed, translucent grape halves with thousands of twinkling multi-colored fiber-optic star lights integrated into the seeds. Every pillar and minaret is a tall stack of variegated grapes wrapped in intensely flickering colorful LED fairy lights. The entrance arches are framed by intense colorful RGB neon tubing, casting a powerful, saturated multi-colored wash over the entire glossy fruity surface.",
                "Buah Tomat": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of vibrant red tomato halves and translucent green stem segments. The architecture is massive with a colossal main dome made of densely packed, polished tomato flesh with black seeds integrated, glowing from within with powerful rotating multi-colored LED wash lights. Tall minarets are crafted from green stem segments, wrapped in intensely flickering colorful LED fairy lights. All entrance arches are outlined with dancing, vibrant RGB neon strips.",
                "Buah Wortel": "A gigantic, large-scale 1-meter standalone mosque object built entirely from millions of vibrant orange carrot sticks and translucent orange carrot peel segments. The building is monumental with a colossal main dome made of thousands of interlocking, glossy orange wedges with powerful internal multi-colored LED wash lights reflecting on its textured surface. Every minaret is a tall pillar made of tightly packed carrot sticks wrapped in rapidly pulsing colorful fairy lights, with entrance arches outlined in vibrant, dancing RGB neon tubing.",
                "Buah Pisang": "A monumental, large-scale 1-meter standalone mosque object constructed from thousands of glossy yellow banana slices and intricate banana-leaf textures. The colossal main dome is a sphere made of densely packed, translucent banana slices with thousands of twinkling multi-colored fiber-optic star lights integrated into the seeds. Every pillar and minaret is a tall stack of variegated bananas wrapped in intensely flickering colorful LED fairy lights. The entrance arches are framed by intense colorful RGB neon tubing, casting a powerful, saturated multi-colored wash over the entire glossy fruity surface.",
                "Buah Durian": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of sharp, golden durian thorns and creamy yellow durian flesh. The architecture looks massive and aggressive, with a colossal main dome made of smooth durian pulp segments glowing from within with powerful multi-colored LED wash lights. Tall minarets are crafted from thorny rinds, wrapped in intensely flickering colorful LED fairy lights. All entrance arches are outlined with dancing, vibrant RGB neon strips.",
                "Buah Markisa": "A gigantic, large-scale 1-meter standalone mosque object built entirely from translucent orange passionfruit pulp and millions of crunchy black seeds. The main dome is a colossal sphere of glossy passionfruit juice with powerful internal multi-colored LED wash lights that make the seeds look like a swirling galaxy. Every minaret is a tall pillar made of hard purple markisa skins wrapped in rapidly pulsing colorful fairy lights, with entrance arches outlined in vibrant, dancing RGB neon tubing.",
                "Buah Kiwi": "A monumental, large-scale 1-meter standalone mosque object constructed from millions of vibrant green kiwi slices and fuzzy brown skin textures. The colossal main dome is a sphere made of polished green kiwi flesh with its ring of black seeds glowing from within using thousands of twinkling multi-colored fiber-optic star lights. Every pillar is a stack of kiwi slices wrapped in intensely flickering colorful LED fairy lights, with entrance arches framed by intense colorful RGB neon tubing.",
                "Buah Salak": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of glossy, dark-brown snake-fruit (salak) scales and polished white salak flesh. The architecture looks grand and ancient, with a colossal main dome made of overlapping salak scales, glowing from within with powerful multi-colored LED wash lights that reflect on the scaly texture. Tall minarets are crafted from salak skin, wrapped in intensely flickering colorful LED fairy lights. All entrance arches are outlined with dancing, vibrant RGB neon strips.",
                "Buah Manggis": "A gigantic, large-scale 1-meter standalone mosque object built entirely from deep purple, thick mangosteen rinds and snow-white mangosteen flesh segments. The main dome is a colossal sphere made of polished white mangosteen segments, glowing from within with powerful internal multi-colored LED wash lights that make the white flesh look like glowing porcelain. Every minaret is a tall pillar made of dark purple rinds wrapped in rapidly pulsing colorful fairy lights, with entrance arches outlined in vibrant, dancing RGB neon tubing.",
                "Buah Alpukat": "A monumental, large-scale 1-meter standalone mosque object constructed from millions of creamy green avocado flesh cubes and dark, pebbled avocado skin textures. The colossal main dome is a sphere made of polished green avocado segments with a large brown avocado seed at the very top, glowing from within with thousands of twinkling multi-colored fiber-optic star lights. Every pillar is a stack of dark-skinned avocado segments wrapped in intensely flickering colorful LED fairy lights, with entrance arches framed by intense colorful RGB neon tubing.",
                "Daun Talas": "A monumental, large-scale 1-meter standalone mosque object built entirely from massive, glossy green taro leaves (talas) with thick, prominent veins. The architecture is grand with a colossal main dome made of overlapping fresh green leaves, glowing from within with powerful multi-colored LED wash lights that highlight the intricate natural vein patterns. Tall minarets are crafted from rolled leaf stalks, wrapped in intensely flickering colorful LED fairy lights. All entrance arches are outlined with dancing, vibrant RGB neon strips.",
                "Daun Jati": "A gigantic, large-scale 1-meter standalone mosque object built entirely from broad, textured teak leaves (jati) with a rustic, organic feel. The main dome is a colossal sphere made of dried golden-brown teak leaves, glowing from within with powerful internal multi-colored LED wash lights that create a warm, magical atmosphere. Every minaret is a tall pillar made of layered leaf textures wrapped in rapidly pulsing colorful fairy lights, with entrance arches outlined in vibrant, dancing RGB neon tubing.",
                "Daun Keladi": "A monumental, large-scale 1-meter standalone mosque object constructed from millions of vibrant, multi-colored caladium leaves (keladi) with intense pink, white, and green patterns. The colossal main dome is a sphere of translucent leaf tissues with thousands of twinkling multi-colored fiber-optic star lights reflecting off the natural leaf pigments. Every pillar is a stack of variegated leaves wrapped in intensely flickering colorful LED fairy lights, with entrance arches framed by intense colorful RGB neon tubing.",
                "Daun Pisang": "A monumental, large-scale 1-meter standalone mosque object built entirely from fresh, glossy green banana leaves (daun pisang) and thick, brown textured banana trunks. The architecture is grand with a colossal main dome made of millions of intricately woven green banana leaf pieces, glowing from within with powerful rotating multi-colored LED wash lights that reflect on the glossy, waxy surface. Tall minarets are crafted from rolled banana leaves and trunks, wrapped in intensely flickering colorful LED fairy lights. All entrance arches are outlined with dancing, vibrant RGB neon strips.",
                "Daun Palem": "A gigantic, large-scale 1-meter standalone mosque object built entirely from millions of dry, golden-brown palm fronds (daun palem) and hard, textured palm seeds. The main dome is a colossal sphere made of thousands of interlocking, dry palm leaves with powerful internal multi-colored LED wash lights that create a warm, magical, and rustic atmosphere. Every minaret is a tall pillar made of tightly packed, interwoven palm fronds wrapped in rapidly pulsing colorful fairy lights, with entrance arches outlined in vibrant, dancing RGB neon tubing.",
                "Daun Pakis": "A monumental, large-scale 1-meter standalone mosque object constructed from thousands of vibrant green, feathery fern fronds (daun pakis) and fuzzy brown fern spores. The colossal main dome is a sphere made of densely packed, overlapping fern fronds with thousands of twinkling multi-colored fiber-optic star lights integrated into the delicate, intricate pakis patterns. Every pillar and minaret is a tall stack of variegated, feathery ferns wrapped in intensely flickering colorful LED fairy lights. The entrance arches are framed by intense colorful RGB neon tubing, casting a powerful, saturated multi-colored wash over the entire lush, leafy surface.",
                "Daun Kelapa": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of woven green janur leaves. The architecture features an intricate diamond-weave pattern. The colossal main dome glows from within with a 'Tropical Sunset' LED scheme (warm orange, deep violet, and lime green) seeping through the weave. Tall minarets are wrapped in flickering amber and teal fairy lights, with entrance arches outlined in pulsing electric-blue neon strips.",
                "Jerami": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from millions of dry, golden rice straws. The colossal main dome is a sphere of straw with a 'Midnight Gold' LED scheme (warm gold, deep blue, and white) twinkling like stars through the fiber. Every minaret is wrapped in rapidly pulsing ice-white fairy lights, with entrance arches outlined in vibrant violet and gold RGB neon tubing.",
                "Bambu Anyam": "A monumental, large-scale 1-meter standalone mosque object built from thousands of glossy bamboo strips. The architecture features complex woven geometries. The colossal main dome glows with a 'Cyber-Forest' LED scheme (neon green, cyan, and magenta) pulsing from the inside. Every pillar is wrapped in intensely flickering emerald-green fairy lights, with entrance arches outlined in dancing, high-contrast pink neon strips.",
                "Daun Kering": "A monumental, large-scale 1-meter standalone mosque object built from thousands of crunchy, brown autumn leaves. The colossal main dome features a 'Volcanic Glow' LED scheme (fire red, burning orange, and sulfur yellow) creating a powerful internal heat effect. Tall minarets are wrapped in flickering red and orange fairy lights, with entrance arches outlined in intense, steady warm-white neon strips for a dramatic look.",
                "Daun Pandan": "A monumental, large-scale 1-meter standalone mosque object built from thousands of long, slender green pandan leaves woven in a herringbone pattern. The colossal main dome glows with a 'Neon Mint' LED scheme (electric lime, soft mint, and bright white) pulsing through the leaf gaps. Tall minarets are wrapped in flickering forest-green fairy lights, with entrance arches outlined in vibrant, dancing turquoise neon strips.",
                "Daun Sirih": "A gigantic, large-scale 1-meter standalone mosque model constructed from millions of glossy, heart-shaped betel leaves (sirih). The architecture is grand with a colossal main dome made of overlapping dark green leaves, glowing with a 'Deep Emerald' LED scheme (emerald green, violet, and gold). Every minaret is wrapped in rapidly pulsing purple fairy lights, with entrance arches outlined in intense gold and green RGB neon tubing.",
                "Daun Suji": "A monumental, large-scale 1-meter standalone mosque object built from dense, dark-green suji leaves. The colossal main dome features a 'Radioactive Glow' LED scheme (neon green, cyan, and lemon yellow) creating an intense internal light effect. Tall minarets are wrapped in flickering cyan fairy lights, with entrance arches outlined in steady, high-contrast pink and green neon strips for a pop-art look.",
                "Daun Paku": "A monumental, large-scale 1-meter standalone mosque object made from thousands of feathery, intricate fern leaves (daun paku). The colossal main dome looks like a lush green galaxy with a 'Starlight Forest' LED scheme (soft blue, magenta, and warm white) twinkling through the delicate fronds. Every pillar is wrapped in intensely flickering multi-colored fairy lights, with entrance arches outlined in vibrant, saturated rainbow neon strips.",
                "Rotan Anyam": "A monumental, large-scale 1-meter standalone mosque object built from thousands of glossy, woven rattan strips in a complex 3D pattern. The architecture is grand with a colossal main dome made of interwoven young rattan. The dome and main walls are adorned with intricate, embossed Thuluth-style calligraphy carved directly into wide rattan bands, featuring a 'Sunset Amber' LED scheme (deep orange, warm gold, and soft red) glowing through the calligraphy and weave. Tall minarets are wrapped in flickering amber fairy lights, with entrance arches outlined in pulsing electric-blue neon strips.",
                "Jati Ukir": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from rich, dark-brown teak wood blocks and slabs. The building is monumental and heavy, with intricate patterns suggesting an immense scale. The entire facade and the colossal main dome are covered in deep, precise Kufic-style calligraphy and floral ukiran timbul, glowing from within with powerful internal 'Volcanic Glow' LED wash lights (fire red, burning orange, and sulfur yellow) highlighting the carved edges. Every minaret is a tall pillar of carved teak wrapped in rapidly pulsing ice-white fairy lights, with entrance arches outlined in vibrant gold RGB neon tubing.",
                "Bambu Kaligrafi": "A monumental, large-scale 1-meter standalone mosque object built from thousands of fine, glossy bamboo strips and sturdy bamboo poles. The architecture features complex woven geometries. The colossal main dome features intricate Diwani-style calligraphy intricately woven with dark bamboo threads against a lighter bamboo background, pulsing with a 'Cyber-Forest' LED scheme (neon green, cyan, and magenta) from the inside. Every pillar is wrapped in intensely flickering emerald-green fairy lights, with entrance arches outlined in dancing, high-contrast pink neon strips.",
                "Kayu Cendana": "A monumental, large-scale 1-meter standalone mosque object made from polished, light-brown sandalwood. The building looks extremely delicate with a high-gloss finish suggesting a monumental architectural scale. The colossal main dome is a sphere covered in intricate, elegant Naskh-style calligraphy carved with extreme precision and gold leaf inlays, featuring thousands of twinkling multi-colored fiber-optic star lights integrated into the calligraphy dots and a soft, warm internal 'Royal White' LED glow. Every pillar is wrapped in intensely flickering colorful fairy lights, with entrance arches framed by intense colorful RGB neon tubing.",
                "Kaleng Bekas": "A monumental, large-scale 1-meter standalone mosque object built from thousands of crushed and polished aluminum soda cans. The architecture features a metallic mosaic texture with embossed Kufic calligraphy hammered into the metal surfaces. The colossal main dome glows with a 'Cyber-Steel' LED scheme (ice blue, violet, and silver white) reflecting off the sharp metallic edges. Tall minarets are wrapped in flickering cyan fairy lights, with entrance arches outlined in pulsing magenta neon strips.",
                "Botol Plastik": "A gigantic, large-scale 1-meter standalone mosque model constructed from millions of shredded clear and blue plastic bottles. The structure is translucent with intricate Thuluth-style calligraphy etched into the plastic layers. The colossal main dome is a sphere of melted recycled plastic with a 'Toxic Neon' LED scheme (lime green, electric yellow, and cyan) glowing from within like a radioactive jewel. Every minaret is wrapped in rapidly pulsing green fairy lights, with entrance arches outlined in vibrant orange RGB neon tubing.",
                "Kardus Retro": "A monumental, large-scale 1-meter standalone mosque object built from thousands of layers of corrugated brown cardboard and recycled paper pulp. The architecture features deep, laser-cut Naskh-style calligraphy that reveals the internal honeycomb structure of the cardboard. The colossal main dome features a 'Warm Industrial' LED scheme (incandescent yellow, deep amber, and soft red) glowing through the calligraphy cuts. Every pillar is wrapped in flickering warm-white fairy lights, with entrance arches framed by intense copper-colored neon strips.",
                "Komponen Elektronik": "A colossal, large-scale 1-meter standalone mosque object made from thousands of recycled circuit boards (PCBs), copper wires, and microchips. The architecture is incredibly complex with Diwani-style calligraphy formed by intricate gold-plated wire paths. The colossal main dome pulses with a 'Digital Matrix' LED scheme (neon green, bright white, and deep purple) following the circuit patterns. Every minaret is a tall pillar of stacked microchips wrapped in intensely flickering colorful LED fairy lights and framed by intense RGB neon tubing.",
                "Kaca Patri": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of jagged, iridescent stained-glass shards and lead frames. The architecture is sharp and crystalline with intricate Thuluth-style calligraphy etched into the glass. The colossal main dome glows with a 'Prism Galaxy' LED scheme (rainbow colors, deep violet, and bright cyan) reflecting and refracting through every glass edge. Tall minarets are wrapped in flickering white-starlight fairy lights, with entrance arches outlined in vibrant, dancing neon-purple strips.",
                "Tembaga Bakar": "A gigantic, large-scale 1-meter standalone mosque model constructed from hammered, heat-treated copper plates and brass wires. The building has a rustic but metallic texture with deep, embossed Kufic-style calligraphy. The colossal main dome features a 'Magma Amber' LED scheme (burning orange, deep red, and warm gold) glowing through the calligraphy punch-holes. Every minaret is a tall pillar of twisted copper wrapped in rapidly pulsing amber fairy lights, with entrance arches outlined in intense warm-white neon tubing.",
                "Sutra Tenun": "A monumental, large-scale 1-meter standalone mosque object built from millions of vibrant silk threads and hand-woven songket fabrics with gold threads. The architecture is soft but structured with elegant Diwani-style calligraphy embroidered in gold leaf. The colossal main dome pulses with a 'Royal Velvet' LED scheme (deep magenta, royal blue, and golden yellow) glowing from behind the translucent silk layers. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense, saturated RGB neon tubing.",
                "Batu Alam": "A colossal, large-scale 1-meter standalone mosque object made from thousands of tiny slabs of polished marble, black obsidian, and white quartz. The architecture is heavy and grand with Naskh-style calligraphy carved deep into the stone. The colossal main dome features a 'Moonlight Quartz' LED scheme (ice blue, soft white, and pale lilac) glowing through the translucent stone veins. Every minaret is a stack of carved marble wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Koran Bekas": "A monumental, large-scale 1-meter standalone mosque object built from millions of rolled and folded recycled newspaper strips. The architecture features a dense grayscale texture of printed text and news-photos. Intricate Thuluth-style calligraphy is laser-cut through the paper layers, glowing with a 'News-Flash' LED scheme (bright white, pale cyan, and amber) seeping through the text-filled walls. Tall minarets are crafted from tightly rolled newspaper tubes, wrapped in flickering cool-white fairy lights, with entrance arches outlined in pulsing electric-blue neon strips.",
                "Bungkus Kopi": "A gigantic, large-scale 1-meter standalone mosque model constructed from thousands of glossy, metallic recycled coffee sachets and snack wrappers. The building is incredibly vibrant and reflective with a patchwork mosaic texture. Embossed Kufic-style calligraphy is hammered into the silver-foil insides of the wrappers. The colossal main dome pulses with a 'Pop-Art' LED scheme (vibrant magenta, electric lime, and bright orange) reflecting off the metallic foil. Every minaret is wrapped in rapidly pulsing rainbow fairy lights, with entrance arches outlined in intense neon-green tubing.",
                "Majalah": "A monumental, large-scale 1-meter standalone mosque object built from thousands of shredded high-gloss fashion magazines. The architecture features a colorful, fragmented texture with a high-shine finish. Elegant Diwani-style calligraphy is formed by raised layers of colorful paper pulp. The colossal main dome features a 'Prismatic Gloss' LED scheme (violet, hot pink, and sky blue) glowing through the glossy paper edges. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense, saturated RGB neon tubing.",
                "Kardus Bekas": "A colossal, large-scale 1-meter standalone mosque object made from raw, corrugated brown cardboard and recycled egg cartons. The architecture features a heavy, industrial texture with deep Naskh-style calligraphy carved to reveal the honeycomb interior. The colossal main dome glows with an 'Industrial Hearth' LED scheme (fire red, deep orange, and warm tungsten yellow) creating a powerful internal glow. Every minaret is a tall pillar of stacked cardboard rings wrapped in flickering warm-white fairy lights and framed by intense copper-colored neon strips.",
                "Tutup Botol": "A monumental, large-scale 1-meter standalone mosque object built from millions of colorful recycled plastic bottle caps. The architecture features a vibrant, circular-pixelated texture. Intricate Thuluth-style calligraphy is embossed into the plastic surfaces. The colossal main dome glows with a 'Neon Carnival' LED scheme (vibrant magenta, lime green, and electric blue) pulsing through the gaps between the caps. Tall minarets are crafted from stacks of translucent caps, wrapped in flickering multi-colored fairy lights, with entrance arches outlined in dancing, high-contrast pink neon strips.",
                "Sedotan Plastik": "A gigantic, large-scale 1-meter standalone mosque model constructed from thousands of colorful, interlocking plastic straws. The building features a unique tubular, honeycomb-like texture. Intricate Kufic-style calligraphy is formed by the tips of the straws. The colossal main dome pulses with a 'Cyber-Fiber' LED scheme (neon cyan, bright violet, and silver-white) flowing through the straws like data cables. Every minaret is wrapped in rapidly pulsing ice-white fairy lights, with entrance arches outlined in vibrant teal RGB neon tubing.",
                "Kabel": "A monumental, large-scale 1-meter standalone mosque object built from miles of tangled, colorful recycled copper wires and black rubber cables. The architecture looks like a high-tech machine with intricate Diwani-style calligraphy formed by gold-plated wire paths. The colossal main dome features a 'Matrix Pulse' LED scheme (electric green, bright orange, and deep purple) following the wire patterns. Every pillar is wrapped in intensely flickering emerald-green fairy lights, with entrance arches framed by intense copper-colored neon strips.",
                "Ban Bekas": "A colossal, large-scale 1-meter standalone mosque object made from thousands of shredded and carved recycled black tires. The architecture is heavy and industrial with deep, rugged textures and Naskh-style calligraphy carved directly into the thick rubber treads. The colossal main dome glows with a 'Volcanic Ember' LED scheme (lava red, burning amber, and dark violet) glowing through the deep carvings. Every minaret is a stack of carved rubber rings wrapped in flickering warm-red fairy lights and framed by intense, steady warm-white neon strips.",
                "Kancing Baju": "A monumental, large-scale 1-meter standalone mosque object built from millions of multi-colored plastic and pearl buttons of various sizes. The architecture features a dense, circular-patterned texture. Elegant Diwani-style calligraphy is formed by raised rows of tiny black buttons. The colossal main dome features a 'Prismatic Sewing' LED scheme (rainbow colors, magenta, and teal) glowing through the button holes. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense, saturated RGB neon tubing.",
                "Spons Cuci Piring": "A colossal, large-scale 1-meter standalone mosque object made from thousands of porous yellow and green recycled sponges. The architecture looks soft and cellular with a unique matte texture. Naskh-style calligraphy is carved deep into the sponge layers. The colossal main dome glows with a 'Bubble Glow' LED scheme (neon green, electric lemon, and soft cyan) creating a powerful internal light effect. Every minaret is a tall pillar of stacked sponges wrapped in flickering cyan fairy lights and framed by intense, steady neon-pink strips.",
                "Kulit Telur": "A gigantic, large-scale 1-meter standalone mosque model constructed from millions of tiny, fragile white and brown eggshell fragments. The structure has a delicate, cracked porcelain texture with intricate Kufic-style calligraphy formed by dark shell pieces. The colossal main dome pulses with a 'Golden Yolk' LED scheme (warm yellow, soft orange, and cream white) glowing through the thin shell layers. Every minaret is wrapped in rapidly pulsing amber fairy lights, with entrance arches outlined in vibrant gold RGB neon tubing.",
                "Sendok Garpu": "A monumental, large-scale 1-meter standalone mosque object built from thousands of polished stainless-steel spoons, forks, and knives. The architecture is a metallic mosaic with sharp, reflective surfaces. Intricate Thuluth-style calligraphy is etched into the spoon bowls. The colossal main dome glows with a 'Mercury Mirror' LED scheme (ice blue, bright silver, and violet) reflecting wildly off the steel. Tall minarets are crafted from stacked forks, wrapped in flickering cool-white fairy lights, with entrance arches outlined in pulsing cyan neon strips.",
                "Mur Baut": "A monumental, large-scale 1-meter standalone mosque object built from thousands of heavy, galvanized steel nuts, bolts, and washers. The architecture is rugged and industrial with a metallic honeycomb texture. Intricate Kufic-style calligraphy is formed by precisely aligned brass bolts. The colossal main dome glows with a 'Heavy Metal' LED scheme (deep violet, electric blue, and cold white) reflecting off the oily steel surfaces. Tall minarets are stacks of giant gears, wrapped in flickering cyan fairy lights, with entrance arches outlined in pulsing magenta neon strips.",
                "Sikat Cuci": "A gigantic, large-scale 1-meter standalone mosque model constructed from thousands of stiff nylon bristles from recycled scrubbing brushes. The structure looks feathery but sharp, with a unique linear texture. Intricate Thuluth-style calligraphy is carved into the wooden handles of the brushes. The colossal main dome pulses with a 'Fiber-Optic Glow' LED scheme (neon pink, bright turquoise, and lemon yellow) shining through the translucent bristles. Every minaret is a tall pillar of bristles wrapped in rapidly pulsing rainbow fairy lights, with entrance arches outlined in vibrant green RGB neon tubing.",
                "Korek Api": "A monumental, large-scale 1-meter standalone mosque object built from millions of used wooden matchsticks with colorful tips. The architecture features a dense, rhythmic wooden texture. Elegant Diwani-style calligraphy is formed by charred matchstick heads. The colossal main dome features a 'Burning Ember' LED scheme (fire red, charcoal orange, and sulfur yellow) glowing through the matchstick gaps. Every pillar is wrapped in intensely flickering warm-white fairy lights, with entrance arches framed by intense copper-colored neon strips.",
                "Keramik Pecah": "A colossal, large-scale 1-meter standalone mosque object made from thousands of jagged shards of recycled bathroom tiles and white porcelain toilets. The architecture is a sharp, glossy mosaic with Naskh-style calligraphy etched into the glazed surfaces. The colossal main dome features a 'Frozen Porcelain' LED scheme (ice blue, soft lilac, and bright silver) reflecting off the sharp ceramic edges. Every minaret is a stack of broken tiles wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "MPensil": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of sharpened and colored recycled pencils and pencil shavings. The architecture features a rhythmic wooden and multi-colored striped texture. Intricate Thuluth-style calligraphy is carved into the pencil wood bodies, glowing with a 'Pencil-Popsicle' LED scheme (lime green, bright orange, and cyan) seeping through the pencil gaps. Tall minarets are crafted from stacks of sharpened pencils, wrapped in flickering cool-white fairy lights, with entrance arches outlined in pulsing electric-blue neon strips.",
                "Pulpen": "A gigantic, large-scale 1-meter standalone mosque model constructed from thousands of glossy recycled plastic pen caps and pen bodies. The building is incredibly vibrant and translucent with a patchwork mosaic texture. Embossed Kufic-style calligraphy is formed by raised layers of colorful pen caps. The colossal main dome pulses with a 'Pop-Art' LED scheme (vibrant magenta, electric lime, and bright orange) reflecting off the metallic pen-clip inside. Every minaret is wrapped in rapidly pulsing rainbow fairy lights, with entrance arches outlined in intense neon-green tubing.",
                "Sabun": "A monumental, large-scale 1-meter standalone mosque object built from thousands of carved recycled white, pink, and blue soap bars. The architecture features a delicate, cracked porcelain texture with intricate Kufic-style calligraphy formed by dark soap pieces. The colossal main dome pulses with a 'Yolk-Yellow' LED scheme (warm yellow, soft orange, and cream white) glowing through the thin shell layers. Every minaret is wrapped in rapidly pulsing amber fairy lights, with entrance arches outlined in vibrant gold RGB neon tubing.",
                "Jerami & Koran": "A monumental, large-scale 1-meter standalone mosque object. The main body, walls, and minarets are built from millions of densely packed, raw golden rice straws (jerami), creating a thick, rustic texture. Embossed Kufic-style calligraphy made of charred straw adorns the walls. The colossal main dome is constructed entirely from thousands of crumpled and lacquered newspaper pages, glowing from within with a 'News-Flash' LED scheme (bright white, amber, and electric blue) seeping through the text-filled paper. Minarets are wrapped in flickering warm-white fairy lights, with entrance arches outlined in pulsing electric-blue neon strips.",
                "Kardus & Serabut Kelapa": "A gigantic, large-scale 1-meter standalone mosque model. The main structure and minarets are built from hundreds of layers of raw, corrugated brown cardboard, revealing its honeycomb texture, covered in laser-cut Thuluth-style calligraphy. The colossal main dome is covered entirely in a thick, feathery layer of brown coconut fiber (serabut kelapa), glowing from within with a 'Volcanic Ember' LED scheme (fire red, burning orange, and sulfur yellow) creating a powerful internal heat effect. Every pillar is wrapped in flickering warm-white fairy lights, with entrance arches framed by intense copper-colored neon strips.",
                "Tutup Botol & Sedotan": "A monumental, large-scale 1-meter standalone mosque object. The main body is constructed from millions of colorful recycled plastic bottle caps, creating a vibrant, pixelated mosaic with Diwani-style calligraphy formed by black caps. The colossal main dome is made of thousands of interlocking, translucent plastic straws, glowing with a 'Toxic Neon' LED scheme (lime green, electric yellow, and cyan) flowing through the straws like data cables. Tall minarets of stacked caps are wrapped in rapidly pulsing green fairy lights, with entrance arches outlined in vibrant orange RGB neon tubing.",
                "Koran Bekas & Ban": "A colossal, large-scale 1-meter standalone mosque object. The main structure and walls are built from millions of rolled grayscale newspaper strips with Naskh-style calligraphy carved through the paper layers. The colossal main dome is crafted from shredded and carved recycled black tire rubber, glowing with a 'Heavy Metal Matrix' LED scheme (neon green, bright white, and deep purple) seeping through the deep tire carvings. Tall minarets of paper tubes are wrapped in intensely flickering emerald-green fairy lights and framed by intense, steady warm-white neon strips.",
                "Daun Pisang & Bambu": "A monumental, large-scale 1-meter standalone mosque object. The main body, walls, and minarets are built from millions of vibrant green, fresh banana leaf pieces (daun pisang) and thick, brown textured banana trunks. Elegant Diwani-style calligraphy is intricately woven with dark bamboo threads into wide banana leaf bands, glowing with a 'Neon Mint' LED scheme (electric lime, soft mint, and bright white) pulsing through the leaf gaps. The colossal main dome is made of thousands of glossy, woven rattan strips, wrapped in flickering cool-white fairy lights, with entrance arches outlined in pulsing electric-blue neon strips.",
                "Kertas Majalah & Kardus": "A monumental, large-scale 1-meter standalone mosque object. The main body is constructed from thousands of shredded high-gloss fashion magazines. Elegant Diwani-style calligraphy is formed by raised layers of colorful paper pulp, glowing with a 'Industrial Hearth' LED scheme (fire red, deep orange, and warm tungsten yellow) creating a powerful internal glow. The colossal main dome is built from thousands of layers of corrugated brown cardboard and recycled paper pulp, wrapped in rapidly pulsing ice-white fairy lights, with entrance arches outlined in vibrant gold RGB neon tubing.",
                "Sabun & Keramik": "A colossal, large-scale 1-meter standalone mosque object. The main structure and walls are built from thousands of carved recycled white, pink, and blue soap bars. Intricate Kufic-style calligraphy is formed by dark soap pieces, glowing with a 'Prismatic Gloss' LED scheme (violet, hot pink, and sky blue) glowing through the glossy paper edges. The colossal main dome is made from thousands of jagged shards of recycled bathroom tiles and white porcelain toilets, wrapped in flickering cool-white fairy lights, with entrance arches outlined in pulsing electric-blue neon strips.",
                "Daun Pisang & Kaleng": "A monumental, large-scale 1-meter standalone mosque object. The main body and minarets are wrapped in millions of fresh, waxy green banana leaves with deep ribbing. The colossal main dome is built from thousands of crushed and polished silver aluminum cans, glowing from within with a 'Bio-Cyber' LED scheme (lime green, ice blue, and silver white) reflecting off the metallic dome. Intricate Thuluth-style calligraphy is embossed into the metal dome and carved into the leaf-covered walls. All arches are outlined in pulsing turquoise neon strips.",
                "Jerami & Botol Plastik": "A gigantic, large-scale 1-meter standalone mosque model. The structure is built from millions of golden-brown rice straws (jerami) bundled tightly. The colossal main dome is a sphere made of thousands of translucent recycled blue plastic bottle bases, glowing with a 'Deep Sea Gold' LED scheme (warm amber, ocean blue, and violet) shining through the plastic like a jewel. Elegant Kufic calligraphy is formed by dark brown seeds against the straw. Minarets are wrapped in flickering amber fairy lights, with entrance arches outlined in vibrant blue neon tubing.",
                "Kulit Kelapa & Kabel": "A monumental, large-scale 1-meter standalone mosque object. The main body is constructed from thousands of rough, dark-brown coconut shells (batok kelapa) with deep textures. The colossal main dome is made of thousands of tangled, colorful recycled copper wires and black cables, glowing with a 'Circuit Jungle' LED scheme (neon green, bright orange, and magenta) pulsing like electricity. Diwani-style calligraphy is formed by polished gold-plated wires on the shell surfaces. Every pillar is wrapped in intensely flickering emerald-green fairy lights.",
                "Koran & Ranting Kayu": "A colossal, large-scale 1-meter standalone mosque object. The main structure is built from millions of rolled grayscale newspaper strips. The colossal main dome is constructed from thousands of interlocking dry tree branches and twigs, glowing with an 'Ancient Future' LED scheme (fire red, charcoal violet, and soft white) creating a dramatic internal glow. Naskh-style calligraphy is laser-cut through the paper walls. Every minaret is a stack of paper tubes and twigs wrapped in flickering warm-red fairy lights and framed by intense teal neon strips.",
                "Melon & Strawberry": "A monumental, large-scale 1-meter standalone mosque object. The main body and minarets are built from millions of glossy cantaloupe melon pieces and translucent green rind blocks. The colossal main dome is constructed entirely from thousands of dense, vibrant red strawberry halves. Intricate Thuluth-style calligraphy is carved directly into the melon-flesh walls, glowing with a 'Ruby-Mint' LED scheme (lime green, bright red, and soft white) seeping through the fruit textures. All entrance arches are outlined in pulsing magenta neon strips.",
                "Semangka & Jeruk": "A gigantic, large-scale 1-meter standalone mosque model. The main structure is built from millions of vibrant red watermelon cubes and dark seeds. The colossal main dome is a sphere made of thousands of glossy orange wedges and translucent citrus rinds. Elegant Kufic calligraphy is formed by black watermelon seeds against the red flesh, glowing with a 'Tropical Fire' LED scheme (vibrant orange, deep red, and gold). Every minaret is wrapped in flickering amber fairy lights.",
                "Buah Naga & Kiwi": "A monumental, large-scale 1-meter standalone mosque object. The main body, walls, and minarets are built from millions of vibrant magenta dragonfruit rind slabs and polished white dragonfruit flesh with embedded black seeds. The colossal main dome is constructed entirely from thousands of interlocking, translucent green kiwi slices. Elegant Diwani-style calligraphy is intricately carved directly into wide bands of kiwi flesh, glowing with a 'Neon Emerald' LED scheme (lime green, cyan, and deep violet) seeping through the fruit textures. All entrance arches are outlined in pulsing electric-pink neon strips.",
                "Manggis & Rambutan": "A gigantic, large-scale 1-meter standalone mosque model. The main structure and minarets are built from rich, deep purple mangosteen rinds and snow-white mangosteen flesh segments. The entire facade is adorned with intricate, raised Kufic-style calligraphy formed by red rambutan skins and hairs against the purple walls. The colossal main dome is a sphere made of thousands of glossy, white rambutan flesh spheres, glowing from within with a 'Deep Royal' LED scheme (deep magenta, royal blue, and gold) reflecting off the juicy fruit. Minarets are wrapped in flickering warm-amber fairy lights, with entrance arches framed by intense gold RGB neon tubing.",
                "Nanas & Anggur": "A monumental, large-scale 1-meter standalone mosque object. The main body is constructed from thousands of glossy, geometric pineapple rind blocks and spiky leaves. The colossal main dome is a sphere made of densely packed, translucent green and purple grape halves. Elegant Diwani-style calligraphy is intricately carved into wide pineapple rind bands, glowing with a 'Sunset Gold' LED scheme (deep orange, warm gold, and royal purple) pulsing from the inside. Every pillar is wrapped in intensely flickering emerald-green fairy lights, with entrance arches framed by intense colorful RGB neon tubing.",
                "Alpukat & Leci": "A colossal, large-scale 1-meter standalone mosque object. The main structure and walls are built from millions of creamy green avocado flesh cubes and dark, pebbled avocado skin textures. The colossal main dome is made of thousands of translucent, white lychee flesh spheres. Elegant Kufic-style calligraphy is formed by polished, dark avocado seeds against the green walls, glowing with a 'Moonlight Quartz' LED scheme (ice blue, soft white, and pale lilac) glowing through the translucent lychee fruit. Minarets are wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Salak & Kelapa": "A monumental, large-scale 1-meter standalone mosque object. The main body and minarets are built from thousands of glossy, dark-brown snake-fruit (salak) scales, creating a natural armored-plate texture. The colossal main dome is a massive sphere made of polished white coconut meat (daging kelapa) segments. Intricate Thuluth-style calligraphy is carved directly into the white coconut dome, glowing with a 'Tropical Moonlight' LED scheme (ice blue, soft white, and deep violet) seeping through the carvings. All entrance arches are outlined in pulsing electric-blue neon strips.",
                "Durian & Nangka": "A gigantic, large-scale 1-meter standalone mosque model. The main structure and walls are built from thousands of sharp, golden durian thorns, giving it a grand and aggressive texture. The colossal main dome is constructed from thousands of glossy, yellow jackfruit (nangka) pods. Elegant Kufic-style calligraphy is formed by dark jackfruit seeds embedded into the walls, glowing with a 'Golden Magma' LED scheme (fire red, burning orange, and warm gold). Every minaret is wrapped in flickering amber fairy lights.",
                "Markisa & Delima": "A monumental, large-scale 1-meter standalone mosque object. The main body is built from millions of translucent orange passionfruit (markisa) pulp and crunchy black seeds. The colossal main dome is a sphere made of thousands of glistening, ruby-red pomegranate (delima) seeds. Elegant Diwani-style calligraphy is formed by patterns of pomegranate seeds, glowing with a 'Ruby Galaxy' LED scheme (vibrant magenta, deep red, and soft pink) shining through the pulp. Entrance arches are outlined in vibrant, dancing RGB neon tubing.",
                "Pepaya & Jambu Air": "A colossal, large-scale 1-meter standalone mosque object. The main structure is built from millions of vibrant orange papaya flesh cubes. The colossal main dome is constructed from thousands of translucent, bell-shaped pink water apples (jambu air). Elegant Naskh-style calligraphy is carved into the papaya walls, glowing with a 'Coral Sunset' LED scheme (warm peach, soft pink, and lime green) reflecting off the juicy textures. Minarets are wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Kardus & Botol Aqua": "A monumental, large-scale 1-meter standalone mosque object. The main body and minarets are built from hundreds of layers of raw, corrugated brown cardboard, revealing its honeycomb texture. The colossal main dome is constructed from thousands of interlocking clear recycled plastic Aqua water bottles with visible blue labels. Intricate Thuluth-style calligraphy is laser-cut through the cardboard walls, glowing with a 'Deep Sea Industrial' LED scheme (ice blue, amber, and silver-white) seeping through the gaps and bottles. Entrance arches are outlined in pulsing blue neon strips.",
                "Koran & Tutup Botol": "A gigantic, large-scale 1-meter standalone mosque model. The main structure is built from millions of rolled grayscale newspaper strips. The colossal main dome is a vibrant sphere made of thousands of colorful recycled plastic bottle caps. Elegant Diwani-style calligraphy is formed by raised rows of black caps against the newspaper-textured walls, glowing with a 'News-Pop' LED scheme (bright white, neon green, and magenta). Every minaret is wrapped in rapidly pulsing rainbow fairy lights.",
                "Beras Putih": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of polished white jasmine rice grains. The architecture features a seamless, pearlescent texture with intricate Thuluth-style calligraphy formed by slightly raised layers of the same rice grains. The colossal main dome glows with a 'Pure Moonlight' LED scheme (cool white, pale silver, and soft ice-blue) seeping through the microscopic gaps between the grains. Tall minarets are solid pillars of rice, wrapped in flickering cool-white fairy lights, with entrance arches outlined in pulsing electric-white neon strips.",
                "Ketan Hitam": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from millions of matte-black glutinous rice grains. The building has a dark, obsidian-like texture that absorbs light. Elegant Kufic-style calligraphy is carved deep into the black grain layers, glowing from within with a 'Deep Nebula' LED scheme (violet, magenta, and electric blue) creating a high-contrast cosmic effect. Every minaret is a tall pillar of black rice wrapped in rapidly pulsing purple fairy lights, with entrance arches outlined in vibrant blue neon tubing.",
                "Bunga Lawang": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of interlocking, star-shaped star anise (bunga lawang). The architecture is incredibly intricate with a natural woody, star-patterned texture. Elegant Diwani-style calligraphy is embossed using the tips of the star anise pods. The colossal main dome features a 'Mystic Amber' LED scheme (warm gold, deep orange, and amber) glowing through the thousands of star-shaped gaps. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense, steady warm-white neon strips.",
                "Kayu Manis": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of curled, textured cinnamon sticks (kayu manis). The architecture features a rhythmic, vertical tubular texture with a rich brown organic finish. Naskh-style calligraphy is carved directly into the bark of the large cinnamon sticks on the facade. The colossal main dome glows with a 'Hearth Fire' LED scheme (burning orange, crimson red, and soft gold) seeping through the cinnamon rolls. Every minaret is a stack of cinnamon tubes wrapped in flickering orange fairy lights and framed by intense copper-colored neon strips.",
                "Kacang Merah": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of glossy, deep-red kidney beans. The architecture features a smooth, organic pebble-like texture. Intricate Thuluth-style calligraphy is formed by raised layers of polished red beans. The colossal main dome glows with a 'Ruby Magma' LED scheme (vibrant red, deep crimson, and warm orange) seeping through the gaps between the beans. Tall minarets are solid pillars of red beans, wrapped in flickering amber fairy lights, with entrance arches outlined in pulsing scarlet neon strips.",
                "Kacang Hijau": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from millions of tiny, matte-green mung beans. The structure has a dense, fine-grained mossy texture. Elegant Kufic-style calligraphy is carved deep into the green bean layers, glowing from within with a 'Radioactive Emerald' LED scheme (neon green, lime, and bright cyan) creating an intense glowing effect. Every minaret is wrapped in rapidly pulsing green fairy lights, with entrance arches outlined in vibrant electric-green neon tubing.",
                "Kacang Kedelai": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of smooth, pale-yellow soybeans. The architecture features a clean, cream-colored minimalist texture. Elegant Diwani-style calligraphy is embossed using slightly darker roasted soybeans for contrast. The colossal main dome features a 'Golden Silk' LED scheme (warm yellow, soft gold, and white) glowing through the thousands of tiny bean gaps. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense, steady warm-white neon strips.",
                "Ketumbar": "A colossal, large-scale 1-meter standalone mosque object made entirely from millions of tiny, spherical coriander seeds (ketumbar). The architecture looks like it's covered in golden micro-beads with a high-detail grainy texture. Naskh-style calligraphy is intricately formed by the arrangement of the seeds. The colossal main dome glows with a 'Vintage Amber' LED scheme (deep amber, copper, and soft violet) seeping through the microscopic seed gaps. Every minaret is a stack of coriander beads wrapped in flickering warm-white fairy lights and framed by intense copper-colored neon strips.",
                "Cabe Merah": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of glossy, vibrant red chili peppers (cabe merah). The architecture features a sleek, rhythmic vertical texture from the curved shapes of the chilies. Intricate Thuluth-style calligraphy is formed by the green chili stems, glowing with a 'Crimson Inferno' LED scheme (deep red, fire orange, and bright white) seeping through the gaps. Tall minarets are bundles of long chilies wrapped in flickering red fairy lights, with entrance arches outlined in pulsing scarlet neon strips.",
                "Tomat": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of plump, glossy red cherry tomatoes. The structure has a bubbly, high-gloss 'organic pearl' texture. Elegant Kufic-style calligraphy is carved into the tomato skins, glowing from within with a 'Golden Pulp' LED scheme (warm orange, honey yellow, and soft red) creating a translucent glowing effect. Every minaret is a stack of tomatoes wrapped in rapidly pulsing amber fairy lights, with entrance arches outlined in vibrant gold neon tubing.",
                "Bawang Putih": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of white garlic bulbs and their papery skins. The architecture features a delicate, multi-layered ivory texture. Elegant Diwani-style calligraphy is embossed using the purple-streaked garlic cloves. The colossal main dome features a 'Moonlight Garlic' LED scheme (cool white, pale lilac, and soft silver) glowing through the translucent papery skins. Every pillar is wrapped in intensely flickering silver fairy lights, with entrance arches framed by intense white neon strips.",
                "Jagung": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of golden-yellow corn cobs and individual kernels. The architecture features a dense, geometric 'golden grid' texture. Naskh-style calligraphy is formed by rows of dark-purple corn kernels against the yellow background. The colossal main dome glows with a 'Solar Flare' LED scheme (bright yellow, electric orange, and warm amber) seeping through the kernels. Every minaret is a tall corn cob wrapped in flickering gold fairy lights and framed by intense teal neon tubing.",
                "Jahe": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of interlocking, gnarled ginger roots (jahe). The architecture features a rugged, tan-colored organic texture with complex natural joints. Intricate Thuluth-style calligraphy is carved deep into the fibrous ginger skin, glowing with a 'Mystic Earth' LED scheme (warm amber, soft orange, and deep violet) seeping through the carvings. Tall minarets are stacked ginger segments wrapped in flickering warm-white fairy lights, with entrance arches outlined in pulsing copper neon strips.",
                "Kunyit": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of polished turmeric roots (kunyit). The structure has a vibrant, deep-orange earthy texture. Elegant Kufic-style calligraphy is formed by scraping the skin to reveal the intense bright orange interior, glowing from within with a 'Solar Saffron' LED scheme (electric yellow, burning orange, and gold) creating a powerful radioactive glow. Every minaret is wrapped in rapidly pulsing gold fairy lights, with entrance arches outlined in vibrant orange neon tubing.",
                "Bawang Merah": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of glossy, purple-skinned shallots (bawang merah). The architecture features a layered, teardrop-shaped texture with a high-shine finish. Elegant Diwani-style calligraphy is embossed using the white inner layers of the shallots. The colossal main dome features a 'Amethyst Glow' LED scheme (deep magenta, royal purple, and soft pink) glowing through the translucent purple skins. Every pillar is wrapped in intensely flickering violet fairy lights, with entrance arches framed by intense magenta neon strips.",
                "Kemiri": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of hard, cream-colored candlenuts (kemiri). The architecture features a lumpy, stone-like ivory texture. Naskh-style calligraphy is intricately carved into the hard nuts. The colossal main dome glows with a 'Vanilla Moonlight' LED scheme (soft cream, pale gold, and ice white) creating a smooth, diffused glow from within the nut clusters. Every minaret is a stack of polished candlenuts wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Lego": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of interlocking plastic bricks. The architecture features a perfect voxelated, studded texture with sharp geometric precision. Intricate Kufic-style calligraphy is formed by precisely arranged 1x1 studs, glowing with a 'Cyber-Block' LED scheme (neon yellow, electric blue, and hot pink) pulsing through the brick seams. Tall minarets are tall towers of stacked bricks, wrapped in flickering multi-colored fairy lights, with entrance arches outlined in vibrant cyan neon strips.",
                "Kelereng": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of clear and cat-eye glass marbles (kelereng). The structure has a bubbly, crystalline, and highly refractive texture. Elegant Thuluth-style calligraphy is etched deep into the glass spheres, glowing from within with a 'Prism Galaxy' LED scheme (rainbow colors, deep violet, and bright silver) refracting through every marble. Every minaret is a stack of glass spheres wrapped in rapidly pulsing white-starlight fairy lights, with entrance arches outlined in vibrant purple neon tubing.",
                "Kartu Remi": "A monumental, large-scale 1-meter standalone mosque object built from thousands of glossy, laminated playing cards folded into complex 3D structures. The architecture features a sharp, layered, and paper-thin geometric texture. Elegant Diwani-style calligraphy is formed by laser-cut patterns on the card faces, glowing with a 'Royal Casino' LED scheme (velvet red, gold, and bright white) seeping through the card layers. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense scarlet neon strips.",
                "Balon": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of tiny, tightly twisted glossy latex balloons. The architecture features a soft, bulbous, and high-shine 'inflatable' texture. Naskh-style calligraphy is printed in metallic gold on the balloon surfaces. The colossal main dome glows with a 'Candy Glow' LED scheme (bubblegum pink, electric lime, and soft cyan) creating a diffused, translucent light effect. Every minaret is a tall twist of balloons wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Pipa Paralon": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of short-cut white PVC pipes of various diameters. The architecture features a unique 'tubular honeycomb' or 'bubble-wrap' geometric texture. Naskh-style calligraphy is formed by the empty circles of the pipe ends. The colossal main dome glows with a 'Toxic Neon' LED scheme (neon green, electric lemon, and soft cyan) creating a powerful internal light effect through the tubes. Every minaret is a tall bundle of pipes wrapped in flickering green fairy lights and framed by intense teal neon tubing.",
                "Rubik Cube": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of interlocked Rubik's cubes. The architecture features a voxelated, colorful, and glossy grid texture. Complex Kufic-style calligraphy is formed by precisely twisting the cubes to create patterns on the facade, glowing with a 'Retro-Arcade' LED scheme (neon pink, cyan, yellow, and magenta) pulsing through the cube seams. Tall minarets are stacked 2x2 Rubik's cubes wrapped in flickering multi-colored fairy lights, with entrance arches outlined in pulsing electric-blue neon strips.",
                "Hot Wheels": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of glossy, metallic-diecast toy cars. The structure has a chaotic but shimmering patchwork mosaic texture of paint and metal. Elegant Thuluth-style calligraphy is formed by precisely aligning rare-color cars against the body, glowing from within with a 'Mercury Mirror' LED scheme (ice blue, bright silver, and neon violet) reflecting wildly off the car bodies. Every minaret is a stack of vertical sports cars wrapped in rapidly pulsing cool-white fairy lights, with entrance arches outlined in vibrant gold neon tubing.",
                "Dadu": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of white dice with black pips. The architecture features a dense, rhythmic pattern of black dots on an ivory-white matte texture. Elegant Diwani-style calligraphy is formed by patterns of the dice pips, glowing with a 'Lucky 7' LED scheme (velvet red, deep black, and amber) shining through the pips. Every pillar is wrapped in intensely flickering warm-white fairy lights, with entrance arches framed by intense copper neon strips.",
                "Kartu Pokemon": "A colossal, large-scale 1-meter standalone mosque object made from thousands of glossy, holographic Pokémon cards. The architecture features a sharp, layered, and iridescent paper texture that flashes with rainbows. Naskh-style calligraphy is laser-cut through the card layers, revealing the internal light. The colossal main dome glows with a 'Prism Galaxy' LED scheme (vibrant rainbow colors, electric lime, and hot pink) refracting through the holographic surfaces. Every minaret is a twist of cards wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Tamiya": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of unassembled and assembled plastic 4WD model car parts (Tamiya). The architecture features a hyper-detailed mechanical texture of gears, chassis, and rollers. Intricate Thuluth-style calligraphy is formed by precisely aligned gold-plated motor gears, glowing with a 'Nitro-Electric' LED scheme (neon blue, bright white, and racing orange) pulsing through the mechanical gaps. Tall minarets are stacks of colorful plastic wheels, wrapped in flickering cyan fairy lights, with entrance arches outlined in pulsing electric-blue neon strips.",
                "Puzzle": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from millions of interlocking jigsaw puzzle pieces. The structure has a fragmented, organic mosaic texture with a slightly matte finish. Elegant Kufic-style calligraphy is formed by removing specific pieces to reveal the internal light, glowing with a 'Prismatic Logic' LED scheme (violet, magenta, and cyan) shining through the gaps. Every minaret is a tall pillar of vertical puzzle layers wrapped in rapidly pulsing white-starlight fairy lights, with entrance arches outlined in vibrant gold neon tubing.",
                "Shuttlecock": "A monumental, large-scale 1-meter standalone mosque object built from thousands of white feathered badminton shuttlecocks. The architecture features a soft, feathery, and rhythmic linear texture. Elegant Diwani-style calligraphy is formed by the dark cork bases of the shuttlecocks against the white feathers, glowing with a 'Cloud Sanctuary' LED scheme (soft lavender, ice blue, and pearl white) diffusing through the feathers. Every pillar is wrapped in intensely flickering silver fairy lights, with entrance arches framed by intense teal neon strips.",
                "Beyblade": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of metallic and plastic spinning tops (Beyblades). The architecture features a heavy, layered circular texture with sharp metallic edges. Naskh-style calligraphy is etched into the central 'Bit-Chips' of the Beyblades. The colossal main dome glows with a 'Galaxy Spin' LED scheme (deep purple, electric green, and silver) reflecting off the spinning metal discs. Every minaret is a stack of metallic attack-rings wrapped in flickering emerald-green fairy lights and framed by intense magenta neon strips.",
                "Kancing Mutiara": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of iridescent mother-of-pearl buttons. The architecture features a shimmering, high-gloss pearlescent texture. Intricate Thuluth-style calligraphy is formed by raised layers of tiny black pearl buttons, glowing with a 'Royal Moonlight' LED scheme (soft white, pale violet, and silver) refracting through the pearl surfaces. Tall minarets are stacked pillars of buttons, wrapped in flickering white-starlight fairy lights, with entrance arches outlined in pulsing electric-purple neon strips.",
                "Kancing Kayu": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of rustic brown wooden buttons of various sizes. The structure has a warm, organic, and matte-textured finish. Elegant Kufic-style calligraphy is carved deep into the wooden buttons, glowing from within with a 'Hearth Fire' LED scheme (burning orange, deep amber, and soft red) seeping through the button holes. Every minaret is a tall stack of large wooden discs wrapped in rapidly pulsing amber fairy lights, with entrance arches outlined in vibrant copper neon tubing.",
                "Kancing Warna-Warni": "A monumental, large-scale 1-meter standalone mosque object built from millions of vibrant, multi-colored plastic buttons arranged in a complex color-gradient mosaic. The architecture features a dense, playful, and high-contrast texture. Elegant Diwani-style calligraphy is formed by rows of glossy black buttons against the colorful background, glowing with a 'Neon Carnival' LED scheme (vibrant magenta, lime green, and electric blue) pulsing through every button hole. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense colorful RGB neon tubing.",
                "Kancing Logam": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of polished gold and silver metal blazer buttons with embossed crests. The architecture features a heavy, metallic, and royal texture. Naskh-style calligraphy is formed by the arrangement of the silver buttons against a gold-button facade. The colossal main dome glows with a 'Mercury Gold' LED scheme (bright gold, ice white, and warm amber) reflecting wildly off the metallic surfaces. Every minaret is a stack of gold buttons wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Peniti Warna-Warni": "A colossal, large-scale 1-meter standalone mosque object made from millions of colorful enamel-coated safety pins (neon pink, lime green, electric blue). The architecture features a vibrant, high-contrast 'punk-rock' mosaic texture. Naskh-style calligraphy is formed by rows of black pins against the colorful background. The colossal main dome glows with a 'Cyber-Pop' LED scheme (vibrant magenta, bright yellow, and cyan) pulsing through the pin gaps. Every minaret is wrapped in flickering multi-colored fairy lights and framed by intense teal neon strips.",
                "Peniti Berkarat": "A monumental, large-scale 1-meter standalone mosque object built from millions of oxidized, rusty iron safety pins for a raw industrial look. The architecture features a dark brown, gritty, and sharp 'Post-Apocalyptic' texture. Elegant Diwani-style calligraphy is formed by new, shiny brass pins for a high-contrast effect. The colossal main dome glows with a 'Volcanic Ember' LED scheme (fire red, burning orange, and sulfur yellow) glowing through the rusty pin layers. Every pillar is wrapped in intensely flickering orange fairy lights.",
                "Lidi Kelapa": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from millions of light-tan coconut leaf ribs (lidi kelapa). The structure has a raw, straw-like, and highly detailed organic texture. Elegant Kufic-style calligraphy is formed by charred lidi tips against the pale background, glowing from within with a 'Solar Flare' LED scheme (bright yellow, electric orange, and warm white) creating a powerful internal glow through the ribbed walls. Every minaret is wrapped in rapidly pulsing gold fairy lights, with entrance arches outlined in vibrant gold neon tubing.",
                "Lidi Aren": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of dark-brown, polished palm fiber sticks (lidi aren). The architecture features a dense, vertical linear texture. Intricate Thuluth-style calligraphy is formed by weaving lighter-colored bamboo splints into the lidi walls, glowing with a 'Mystic Amber' LED scheme (deep orange, warm gold, and soft red) seeping through the thousands of thin vertical gaps. Tall minarets are bundles of lidi wrapped in flickering amber fairy lights, with entrance arches outlined in pulsing copper neon strips.",
                "Lidi Bakar": "A colossal, large-scale 1-meter standalone mosque object made entirely from millions of charred, blackened lidi sticks with burnt tips. The architecture features a dark, carbonized, and sharp 'monolithic' texture. Naskh-style calligraphy is carved to reveal the inner light wood color of the sticks. The colossal main dome glows with a 'Volcanic Ember' LED scheme (fire red, deep orange, and sulfur yellow) glowing intensely through the charcoal-like gaps. Every minaret is a bundle of burnt lidi wrapped in flickering red fairy lights and framed by intense teal neon strips.",
                "Stik Eskrim": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of raw, natural-wood ice cream sticks. The structure has a rustic, layered, and interlocking 'woven' texture with sharp geometric edges. Elegant Kufic-style calligraphy is carved deep into the wooden sticks, glowing from within with a 'Deep Amber Hearth' LED scheme (warm gold, deep orange, and soft amber) seeping through the thousands of vertical gaps. Every minaret is a tall stack of interlocking sticks wrapped in rapidly pulsing gold fairy lights, with entrance arches outlined in vibrant copper neon tubing.",
                "Pecahan Keramik": "A monumental, large-scale 1-meter standalone mosque object built from thousands of jagged, iridescent glazed ceramic tile shards arranged in a dense, multi-colored mosaic. The architecture features a sharp, shattered, and highly reflective texture like a broken rainbow mirror. Elegant Diwani-style calligraphy is formed by aligning glossy black ceramic shards against the colorful background, glowing with a 'Prism Galaxy' LED scheme (rainbow colors, deep violet, and electric silver) reflecting and refracting through every jagged edge. Entrance arches are outlined in vibrant colorful RGB neon tubing.",
                "Pecahan Keramik Putih": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of pure white porcelain and china shards. The architecture features a sharply broken, brilliant white texture resembling a shattered iceberg. Naskh-style calligraphy is formed by outlining the shapes of the white shards with gold-leaf gaps. The colossal main dome glows with a 'Moonlight Quartz' LED scheme (ice blue, soft white, and pale silver) creating a smooth, diffused glow refracted through the ceramic shards. Every minaret is a stack of white porcelain shards wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Donat Glazed": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of glossy, sugar-glazed donuts. The architecture features a bubbly, rounded, and high-shine organic texture. Intricate Thuluth-style calligraphy is formed by vibrant multi-colored chocolate sprinkles (meses) on the donut surfaces, glowing with a 'Candy Rush' LED scheme (bubblegum pink, electric violet, and bright gold) reflecting off the sugar glaze. Tall minarets are stacks of donuts wrapped in flickering magenta fairy lights, with entrance arches outlined in pulsing neon-pink strips.",
                "Roti Tawar": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of soft, white bread slices. The structure has a porous, spongy, and matte-white texture. Elegant Kufic-style calligraphy is scorched directly onto the bread surfaces (toast effect), glowing from within with a 'Golden Toasted' LED scheme (warm amber, honey yellow, and soft orange) seeping through the bread's airy pores. Every minaret is a tall stack of bread slices wrapped in rapidly pulsing gold fairy lights, with entrance arches outlined in vibrant copper neon tubing.",
                "Croissant": "A monumental, large-scale 1-meter standalone mosque object built from thousands of flaky, golden-brown buttery croissants. The architecture features a highly layered, crispy, and spiral-curved texture. Elegant Diwani-style calligraphy is formed by patterns of powdered sugar dusted over the flaky layers, glowing with a 'Butter Gold' LED scheme (bright gold, warm tungsten, and soft cream) pulsing from the gaps between the pastry layers. Every pillar is wrapped in intensely flickering warm-white fairy lights, with entrance arches framed by intense gold neon strips.",
                "Biskuit Crackers": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of rectangular golden-brown crackers with visible pin-holes. The architecture features a crisp, geometric, and perforated grid texture. Naskh-style calligraphy is formed by the arrangement of the cracker holes, glowing with a 'Solar Biscuit' LED scheme (electric orange, amber, and pale yellow) shining through the thousands of tiny holes. Every minaret is a square stack of crackers wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Bungkus Indomie": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of shiny, crinkled plastic Indomie instant noodle wrappers. The architecture features a vibrant patchwork of red, yellow, and white plastic textures with high-gloss reflections. Intricate Thuluth-style calligraphy is formed by precisely aligning the 'Indomie' logos, glowing with a 'Microwave Neon' LED scheme (bright red, electric yellow, and white) pulsing through the plastic folds. Tall minarets are cylinders of wrapped plastic, wrapped in flickering multi-colored fairy lights.",
                "Alumunium Foil": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of crumpled silver and gold alumunium foil wrappers from chocolate bars. The structure has a sharp, metallic, and highly faceted texture like a silver mountain. Elegant Kufic-style calligraphy is embossed directly into the foil, glowing from within with a 'Mercury Mirror' LED scheme (ice blue, bright silver, and violet) reflecting wildly off the crinkled metal. Every minaret is a stack of metallic foil wrapped in rapidly pulsing white fairy lights.",
                "Bungkus Keripik": "A monumental, large-scale 1-meter standalone mosque object built from thousands of turned-inside-out snack bags (silver interior). The architecture features a blindingly reflective, chrome-like silver texture. Elegant Diwani-style calligraphy is etched into the silver surface, glowing with a 'Cyber-Chrome' LED scheme (neon green, electric blue, and magenta) creating a high-tech metallic glow. Every pillar is wrapped in intensely flickering emerald-green fairy lights, with entrance arches framed by intense teal neon strips.",
                "Kertas Cokelat": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of oil-stained, crumpled brown fast-food paper bags. The architecture features a dark, translucent, and 'vintage-grunge' organic texture. Naskh-style calligraphy is laser-cut through the paper layers, revealing the internal light. The colossal main dome glows with a 'Golden Grease' LED scheme (warm amber, deep orange, and soft tungsten) shining through the oily paper. Every minaret is a tall roll of brown paper wrapped in flickering warm-white fairy lights.",
                "Sachet Kopi": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of interlocking colorful coffee sachets (maroon, gold, and black). The architecture features a dense, shingled texture like dragon scales. Intricate Thuluth-style calligraphy is formed by the brand logos on the sachets, glowing with a 'Caffeine Gold' LED scheme (deep amber, espresso brown, and bright gold) pulsing through the foil seams. Tall minarets are cylinders of tightly rolled sachets wrapped in flickering warm-white fairy lights, with entrance arches outlined in pulsing copper neon strips.",
                "Plastik Kresek": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of layered and melted colorful plastic grocery bags (kantong kresek). The structure has a soft, flowing, and semi-translucent 'drapery' texture with organic folds. Elegant Kufic-style calligraphy is melted into the plastic surface, glowing from within with a 'Toxic Rainbow' LED scheme (neon green, hot pink, and electric blue) shining through the translucent plastic layers. Every minaret is a tall twist of plastic wrapped in rapidly pulsing white fairy lights.",
                "Kaleng Soda": "A monumental, large-scale 1-meter standalone mosque object built from thousands of crushed and flattened aluminum soda cans. The architecture features a sharp, jagged, and highly metallic patchwork texture. Elegant Diwani-style calligraphy is embossed using the colorful pull-tabs of the cans, glowing with a 'Fizzy Silver' LED scheme (bright silver, ice blue, and crimson red) reflecting wildly off the metallic shards. Every pillar is wrapped in intensely flickering silver fairy lights, with entrance arches framed by intense scarlet neon strips.",
                "Bungkus Permen": "A colossal, large-scale 1-meter standalone mosque object made entirely from millions of tiny, transparent and metallic candy wrappers. The architecture features a sparkling, 'jewel-box' texture with thousands of small reflections. Naskh-style calligraphy is formed by the colorful patterns of the wrappers, glowing with a 'Sugar Prism' LED scheme (rainbow colors, soft violet, and bright yellow) refracting through the clear plastic. Every minaret is a stack of candy-wrap spheres wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Bungkus Taro": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of glossy, purple 'Taro' snack wrappers. The architecture features a vibrant deep-purple plastic texture with high-gloss reflections. Intricate Thuluth-style calligraphy is formed by the silver interior of the wrappers, glowing with a 'Deep Amethyst' LED scheme (neon purple, electric blue, and bright silver) pulsing through the plastic folds. Tall minarets are cylinders of wrapped purple foil wrapped in flickering violet fairy lights, with entrance arches outlined in pulsing cyan neon strips.",
                "Bungkus Chiki": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of bright yellow 'Chiki Balls' wrappers. The structure has a saturated, sunny-yellow texture with high-reflectivity. Elegant Kufic-style calligraphy is formed by aligning the iconic Chiki mascot patterns, glowing from within with a 'Solar Flare' LED scheme (bright yellow, electric orange, and warm white) creating a powerful internal glow. Every minaret is a tall pillar of yellow foil wrapped in rapidly pulsing gold fairy lights, with entrance arches outlined in vibrant gold neon tubing.",
                "Bungkus Cheetos": "A monumental, large-scale 1-meter standalone mosque object built from thousands of vibrant orange and red 'Cheetos' wrappers. The architecture features a fiery, high-contrast patchwork texture. Elegant Diwani-style calligraphy is etched using the silver foil side of the packaging, glowing with a 'Flaming Ember' LED scheme (fire red, burning orange, and sulfur yellow) reflecting wildly off the crinkled metallic surfaces. Every pillar is wrapped in intensely flickering orange fairy lights, with entrance arches framed by intense scarlet neon strips.",
                "Bungkus Chitato": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of dark-blue and silver 'Chitato' potato chip bags. The architecture features a deep-colored, premium metallic plastic texture. Naskh-style calligraphy is formed by laser-cut patterns through the dark blue plastic to reveal the internal light. The colossal main dome glows with a 'Sapphire Spark' LED scheme (deep ocean blue, ice silver, and soft white) refracting through the metallic layers. Every minaret is wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Umbul": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of colorful vintage 'Gambar Umbul' paper cards (mainan jadul). The architecture features a vibrant, dense, and slightly glossy patchwork texture of mismatched retro characters (superheroes, anime, movie scenes). Elegant Thuluth-style calligraphy is formed by precisely aligning the card borders, glowing with a 'Retro Pixel' LED scheme (neon pink, bright yellow, and cyan) pulsing through the paper seams. Tall minarets are stacked cylinders of cards wrapped in flickering multi-colored fairy lights, with entrance arches outlined in pulsing cyan neon strips.",
                "Umbul Hologram": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of special-edition 'Gambar Umbul' cards with holographic and iridescent finishes. The architecture features a hyper-reflective, prism-like texture that flashes rainbows. Naskh-style calligraphy is laser-cut through the cards, revealing the internal light. The colossal main dome glows with a 'Sugar Prism' LED scheme (rainbow colors, soft violet, and bright yellow) refracting through the holographic surfaces. Every minaret is a stack of holographic cards wrapped in flickering silver fairy lights.",
                "Platinum Berlian": "A monumental, large-scale 1-meter standalone mosque object built entirely from polished solid platinum blocks. The architecture features a heavy, cool-toned silver-metallic texture with mirror-finish surfaces. Intricate Thuluth-style calligraphy is inlaid with millions of micro-cut black diamonds, glowing with a 'Starlight Void' LED scheme (ice blue, deep violet, and silver white) reflecting off the metallic body. Tall minarets are solid platinum pillars wrapped in flickering cool-white fairy lights, with entrance arches outlined in pulsing electric-blue neon strips.",
                "Kristal Safir": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of faceted Swarovski crystals and deep-blue sapphires. The structure has a hyper-reflective, transparent, and prismatic texture. Elegant Kufic-style calligraphy is formed by internal laser-etching inside the sapphire stones, glowing from within with a 'Deep Ocean Prism' LED scheme (vibrant blue, bright cyan, and silver) refracting through every facet. Every minaret is a stack of giant crystals wrapped in rapidly pulsing white-starlight fairy lights, with entrance arches outlined in vibrant purple neon tubing.",
                "Emas Merah": "A monumental, large-scale 1-meter standalone mosque object built from polished 18K rose gold and thousands of glowing red rubies. The architecture features a warm, pinkish-gold metallic texture with a high-gloss finish. Elegant Diwani-style calligraphy is formed by raised layers of blood-red rubies, glowing with a 'Royal Hearth' LED scheme (vibrant red, warm amber, and rose-gold spark) pulsing through the precious stones. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense magenta neon strips.",
                "Gading Putih": "A colossal, large-scale 1-meter standalone mosque object made from polished ivory-textured marble and intricate 24K gold filigree wire-work. The architecture features a smooth, cream-colored base covered in complex, lace-like golden patterns. Naskh-style calligraphy is formed by woven gold threads, glowing with a 'Champagne Solar' LED scheme (warm gold, pale cream, and soft tungsten) creating a majestic, diffused glow. Every minaret is a masterpiece of gold wire-work wrapped in flickering silver fairy lights and framed by intense warm-white neon strips.",
                "Ukiran Jati": "A monumental, large-scale 1-meter standalone mosque object crafted from deep dark-brown aged teak wood. The entire facade is covered in intricate, deep-relief floral 'Jepara-style' carvings and complex Thuluth-style calligraphy. The colossal main dome is made of solid, mirror-polished 24K gold, glowing with a 'Solar Royalty' LED scheme (warm gold, deep amber, and white-hot spark) reflecting off the gold. Tall minarets are carved wood pillars with gold-plated balconies wrapped in flickering golden fairy lights, with entrance arches outlined in pulsing champagne-gold neon strips.",
                "Kayu Hitam": "A gigantic, large-scale 1-meter standalone mosque model built from jet-black Ebony wood with a high-gloss polished finish. Elegant Kufic-style calligraphy is inlaid with white-gold (platinum) filigree along the walls. The colossal main dome is a sphere of brushed white gold, glowing from within with a 'Moonlight Silver' LED scheme (ice blue, pale silver, and bright white) reflecting off the dark wood. Every minaret is a masterpiece of dark wood carving wrapped in rapidly pulsing white-starlight fairy lights, with entrance arches outlined in vibrant purple neon tubing.",
                "Kayu Gaharu": "A monumental, large-scale 1-meter standalone mosque object made from rare, textured agarwood (gaharu). The architecture features a rugged, organic wood texture with deep-etched Diwani-style calligraphy filled with liquid gold. The colossal main dome is a massive dome of hammered gold leaf, glowing with a 'Mystic Amber' LED scheme (vibrant orange, warm gold, and royal purple) seeping through the wood grains. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense warm-white neon strips.",
                "Kayu Cendana": "A colossal, large-scale 1-meter standalone mosque object carved from aromatic sandalwood (cendana) with a pale-tan matte texture. The architecture is covered in a delicate mesh of 22K gold filigree ukiran. Naskh-style calligraphy is embossed in solid gold on the wood facade. The colossal main dome is a brilliant gold-lattice structure glowing with a 'Champagne Glow' LED scheme (soft cream, pale gold, and warm tungsten). Every minaret is a stack of carved sandalwood cylinders wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Giok Hijau": "A monumental, large-scale 1-meter standalone mosque object carved from deep imperial green jade (giok). The architecture features a smooth, translucent stone texture with natural veins. Intricate Thuluth-style calligraphy is inlaid with rare black South Sea pearls, glowing with an 'Emerald Moonlight' LED scheme (mint green, soft teal, and pale silver) shining through the jade body. Tall minarets are solid jade pillars wrapped in flickering silver fairy lights, with entrance arches outlined in pulsing electric-purple neon strips.",
                "Mutiara Putih": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from millions of iridescent white pearls and polished white jade. The structure has a shimmering, creamy, and high-gloss 'organic pearl' texture. Elegant Kufic-style calligraphy is embossed using tiny golden pearls, glowing from within with a 'Champagne Mist' LED scheme (pale gold, soft cream, and ice white) refracting through the pearl layers. Every minaret is a stack of giant pearls wrapped in rapidly pulsing white-starlight fairy lights, with entrance arches outlined in vibrant gold neon tubing.",
                "Giok Merah": "A monumental, large-scale 1-meter standalone mosque object built from rare red jade and inlaid with golden South Sea pearls. The architecture features a warm, translucent crimson texture. Elegant Diwani-style calligraphy is formed by rows of perfectly round gold pearls, glowing with a 'Royal Ember' LED scheme (vibrant red, warm amber, and honey yellow) pulsing from the heart of the jade. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense scarlet neon strips.",
                "Mosaik Giok": "A colossal, large-scale 1-meter standalone mosque object made from a complex mosaic of various jade shades (lavender, green, white) and iridescent abalone pearl shells. The architecture features a sharp, shattered, and multi-colored gemstone texture. Naskh-style calligraphy is laser-etched into the abalone surfaces. The colossal main dome glows with a 'Prism Sanctuary' LED scheme (rainbow colors, soft violet, and bright silver) refracting through the translucent stones and shells. Every minaret is wrapped in flickering silver fairy lights and framed by intense teal neon tubing.",
                "Batu Zamrud": "A monumental, large-scale 1-meter standalone mosque object carved from a single colossal deep-green emerald crystal. The architecture features sharp crystalline facets and natural internal 'jardin' inclusions. Intricate Thuluth-style calligraphy is etched deep and filled with liquid platinum, glowing with a 'Verdan Sanctuary' LED scheme (intense neon green, forest emerald, and bright silver) refracting through the translucent green stone. Tall minarets are faceted crystal pillars wrapped in flickering silver fairy lights, with entrance arches outlined in pulsing teal neon strips.",
                "Batu Safir Biru": "A gigantic, large-scale 1-meter standalone mosque model constructed from thousands of royal blue sapphires. The structure has a deep, velvety blue crystalline texture. Elegant Kufic-style calligraphy is formed by white diamonds inlaid into the sapphire walls, glowing from within with a 'Deep Ocean Prism' LED scheme (vibrant sapphire blue, electric cyan, and ice white) shattering light into thousands of blue rays. Every minaret is a stack of raw sapphire crystals wrapped in rapidly pulsing white-starlight fairy lights, with entrance arches outlined in vibrant gold neon tubing.",
                "Batu Kecubung": "A monumental, large-scale 1-meter standalone mosque object built from massive purple amethyst geodes with exposed raw crystals inside. The architecture features a rugged exterior and a sparkling, jagged violet interior. Elegant Diwani-style calligraphy is laser-carved into the crystal points, glowing with an 'Amethyst Galaxy' LED scheme (deep purple, magenta, and soft lilac) pulsing from the heart of the geode. Every pillar is a cluster of purple crystals wrapped in intensely flickering violet fairy lights, with entrance arches framed by intense magenta neon strips.",
                "Berlian Pink": "A colossal, large-scale 1-meter standalone mosque object made entirely from rare pink diamonds set in a delicate white-gold (platinum) frame. The architecture features a hyper-reflective, soft-pink crystalline texture. Naskh-style calligraphy is formed by rows of tiny white diamonds, glowing with a 'Rose Aurora' LED scheme (soft pink, champagne, and bright silver) creating a blindingly beautiful shimmer. Every minaret is a masterpiece of diamond-setting wrapped in flickering silver fairy lights and framed by intense warm-white neon strips.",
                "Bulu Merak": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of vibrant peacock feathers. The architecture features a soft, iridescent, and feathery texture dominated by the 'eye' patterns of the feathers. Intricate Thuluth-style calligraphy is formed by the deep-blue quill fibers, glowing with a 'Peacock Nebula' LED scheme (electric lime, deep violet, and shimmering teal) seeping through the soft barbs. Tall minarets are bundles of long feathers wrapped in flickering emerald fairy lights, with entrance arches outlined in pulsing magenta neon strips.",
                "Sisik Ikan": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of large, metallic-pearlized scales of a Super Red Arowana fish. The structure has a heavy, layered, and high-gloss 'dragon scale' texture. Elegant Kufic-style calligraphy is etched into the scales, glowing from within with a 'Crimson Pearl' LED scheme (fire red, soft pink, and bright silver) reflecting off the iridescent surfaces. Every minaret is a stack of scales wrapped in rapidly pulsing red fairy lights, with entrance arches outlined in vibrant gold neon tubing.",
                "Cangkang Kerang": "A monumental, large-scale 1-meter standalone mosque object built from thousands of rough-textured oyster shells with polished nacre interiors. The architecture features a contrast between rugged gray exteriors and shimmering rainbow interiors. Elegant Diwani-style calligraphy is carved to reveal the pearlescent inner layers, glowing with a 'Moonlight Nacre' LED scheme (pale violet, ice blue, and soft cream) refracting through the calcium layers. Every pillar is wrapped in intensely flickering silver fairy lights, with entrance arches framed by intense teal neon tubing.",
                "Sarang Lebah": "A colossal, large-scale 1-meter standalone mosque object made entirely from golden-yellow natural beeswax and hexagonal honeycomb structures. The architecture features a perfect geometric grid texture with a translucent, waxy finish. Naskh-style calligraphy is formed by filling specific hexagonal cells with dark forest honey. The colossal main dome glows with a 'Liquid Amber' LED scheme (bright honey yellow, deep orange, and warm gold) shining through the translucent wax walls. Every minaret is a hexagonal tower wrapped in flickering gold fairy lights.",
                "Terumbu Karang": "A monumental, large-scale 1-meter standalone mosque object carved from a single massive block of white brain coral. The architecture features an incredibly complex, labyrinthine organic groove texture. Intricate Thuluth-style calligraphy is formed by the natural brain-like ridges of the coral, glowing with a 'Deep Sea Bio-Lume' LED scheme (soft cyan, electric lime, and ultraviolet) seeping through the deep grooves. Tall minarets are towers of porous coral wrapped in flickering turquoise fairy lights, with entrance arches outlined in pulsing neon-white strips.",
                "Fosil Kayu": "A colossal, large-scale 1-meter standalone mosque object made from polished slabs of millions-of-years-old petrified wood. The architecture features a unique stone-meets-wood texture with deep rings and mineralized grain patterns. Naskh-style calligraphy is formed by the natural agate and quartz veins inside the fossil. The colossal main dome glows with a 'Primal Earth' LED scheme (deep violet, emerald green, and golden brown) reflecting off the mirror-polished stone surface. Every minaret is a tall pillar of fossilized wood wrapped in flickering silver fairy lights.",
                "Kristal Garam": "A monumental, large-scale 1-meter standalone mosque object built from massive blocks of raw pink Himalayan salt crystals. The architecture features a jagged, crystalline, and semi-transparent texture with natural mineral veins. Elegant Diwani-style calligraphy is etched into the salt blocks, glowing from within with a 'Peach Sunset' LED scheme (warm orange, soft pink, and deep amber) creating a massive diffused glow throughout the structure. Every pillar is wrapped in intensely flickering orange fairy lights, with entrance arches framed by intense copper neon strips.",
                "Tanah Liat": "A monumental, large-scale 1-meter standalone mosque object sculpted from raw, burnt-orange terracotta clay. The architecture features a smooth but hand-crafted organic texture with visible thumbprints and sculpting marks. Intricate Thuluth-style calligraphy is carved deep into the wet clay before hardening, glowing with a 'Molten Core' LED scheme (fire red, deep orange, and warm amber) seeping through the cracks. Tall minarets are tapered clay pillars wrapped in flickering orange fairy lights, with entrance arches outlined in pulsing copper neon strips.",
                "Serbuk Kayu": "A gigantic, large-scale 1-meter standalone mosque model constructed from compressed millions of fine golden-brown sawdust particles. The structure has a soft, fuzzy, and highly textured matte finish. Elegant Kufic-style calligraphy is formed by burning the sawdust surface (pyrography), glowing from within with a 'Golden Dust' LED scheme (honey yellow, soft gold, and warm white) shining through the porous compressed particles. Every minaret is a tall cylinder of pressed wood-dust wrapped in rapidly pulsing amber fairy lights.",
                "Pasir Pantai": "A monumental, large-scale 1-meter standalone mosque object built from millions of glistening, wet golden sand grains. The architecture features a dripping, 'melted' sandcastle texture with incredible granular detail. Elegant Diwani-style calligraphy is traced into the sand, glowing with a 'Coastal Glow' LED scheme (bright gold, pale cyan, and white) reflecting off the tiny quartz crystals in the sand. Every pillar is a stack of dripping sand wrapped in intensely flickering silver fairy lights, with entrance arches framed by intense teal neon strips.",
                "Batu Bata": "A colossal, large-scale 1-meter standalone mosque object made entirely from thousands of miniature, weathered red bricks and grey mortar. The architecture features a rough, geometric, and industrial-heritage texture. Naskh-style calligraphy is formed by protruding bricks, glowing with a 'Vintage Alley' LED scheme (soft red, warm tungsten, and amber) seeping through the mortar gaps. Every minaret is a tall brick tower wrapped in flickering warm-white fairy lights and framed by intense scarlet neon strips.",
                "Arang Kayu": "A monumental, large-scale 1-meter standalone mosque object built entirely from thousands of jagged, matte-black charred wood chunks. The architecture features a deep, carbonized, and highly porous texture. Intricate Thuluth-style calligraphy is carved to reveal the glowing core, featuring a 'Volcanic Ember' LED scheme (intense fire red, burning orange, and sulfur yellow) pulsing from within the black charcoal gaps. Tall minarets are stacks of burnt wood wrapped in flickering red fairy lights, with entrance arches outlined in pulsing copper neon strips.",
                "Batu Apung": "A gigantic, large-scale 1-meter standalone mosque model constructed from thousands of light-grey, highly aerated volcanic pumice stones. The structure has a sponge-like, rough, and perforated texture. Elegant Kufic-style calligraphy is formed by the natural holes in the stone, glowing from within with a 'Deep Sea Bio-Lume' LED scheme (soft cyan, electric lime, and ice white) shining through the thousands of tiny stone pores. Every minaret is a tall porous pillar wrapped in rapidly pulsing white fairy lights.",
                "Serbuk Kopi": "A colossal, large-scale 1-meter standalone mosque object made entirely from compressed, dark-roast coffee grounds. The architecture features a grainy, rich dark-brown, and oily matte texture. Naskh-style calligraphy is formed by stenciling with fine white sugar crystals. The colossal main dome glows with a 'Caffeine Aurora' LED scheme (deep violet, espresso brown, and soft magenta) creating a moody, diffused glow through the coffee particles. Every minaret is a cylinder of pressed coffee wrapped in flickering silver fairy lights.",
                "Lumut & Batu Kali": "A monumental, large-scale 1-meter standalone mosque object built from smooth river stones covered in thick, vibrant green moss. The architecture features a soft, velvety green texture contrasted with cold grey stone. Elegant Diwani-style calligraphy is formed by trimming the moss to reveal the stone underneath, glowing with a 'Forest Sanctuary' LED scheme (emerald green, soft lime, and golden amber) pulsing from behind the moss layers. Every pillar is wrapped in intensely flickering gold fairy lights, with entrance arches framed by intense teal neon strips.",
                "Tanah Lempung": "A gigantic, large-scale 1-meter standalone mosque model sculpted from grey river clay with a 'crackle-glaze' dried texture. The structure features millions of tiny, intricate fissures across the entire surface. Elegant Kufic-style calligraphy is formed by the deep cracks themselves, glowing from within with a 'Deep Magma' LED scheme (blood red, dark orange, and amber) seeping through the thousands of tiny mud gaps. Every minaret is a column of dried mud wrapped in rapidly pulsing red fairy lights, with entrance arches outlined in vibrant gold neon tubing.",
                "Kristal Kuarsa": "A monumental, large-scale 1-meter standalone mosque object built from massive, jagged clusters of raw white quartz crystals. The architecture features a sharp, semi-translucent, and icy geometric texture. Intricate Thuluth-style calligraphy is formed by natural mineral inclusions (veins) inside the crystals, glowing with a 'Glacial Prism' LED scheme (ice blue, soft violet, and bright silver) refracting through the crystal body. Tall minarets are jagged crystal points wrapped in flickering cool-white fairy lights, with entrance arches outlined in pulsing cyan neon strips.",
                "Batu Obsidian Hitam": "A monumental, large-scale 1-meter standalone mosque object carved from massive blocks of volcanic obsidian glass. The architecture features a razor-sharp, mirror-polished jet-black texture with conchoidal fractures. Elegant Diwani-style calligraphy is etched into the glass surface, glowing with a 'Void Spectrum' LED scheme (deep magenta, neon purple, and electric blue) reflecting off the pitch-black glass. Every pillar is wrapped in intensely flickering violet fairy lights, with entrance arches framed by intense teal neon strips.",
                "Kapur Tulis": "A colossal, large-scale 1-meter standalone mosque object built entirely from thousands of white and pastel-colored sticks of chalk and compressed chalk dust. The architecture features a soft, dusty, and ultra-matte texture. Naskh-style calligraphy is 'sketched' onto the surface with vibrant colored chalk. The colossal main dome glows with a 'Pastel Nebula' LED scheme (soft pink, mint green, and pale yellow) creating a hazy, diffused glow through the chalk dust. Every minaret is a stack of chalk sticks wrapped in flickering silver fairy lights.",
                "Es Krim Cone": "A monumental, large-scale 1-meter standalone mosque object built from thousands of stacked crispy waffle cones and giant scoops of vanilla ice cream. The architecture features a criss-cross waffle texture at the base and a soft, billowy 'cloud-like' texture for the domes. Intricate Thuluth-style calligraphy is drizzled in chocolate syrup, glowing with a 'Vanilla Gold' LED scheme (warm cream, bright gold, and soft white) reflecting off the melting surface. Tall minarets are stacked waffle cones wrapped in flickering amber fairy lights.",
                "Es Krim Magnum": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of premium chocolate-coated ice cream bars. The structure has a sharp, cracked-chocolate shell texture. Elegant Kufic-style calligraphy is etched into the dark chocolate to reveal the white vanilla interior, glowing from within with a 'Royal Cocoa' LED scheme (deep amber, copper, and bright white) seeping through the cracks. Every minaret is a tall ice cream bar wrapped in rapidly pulsing gold fairy lights.",
                "Sorbet Pelangi": "A monumental, large-scale 1-meter standalone mosque object built from millions of tiny, vibrant scoops of fruit sorbet (lime, raspberry, orange). The architecture features a frosty, grainy, and multi-colored icy texture. Elegant Diwani-style calligraphy is formed by frozen berries, glowing with a 'Neon Frost' LED scheme (vibrant pink, lime green, and electric orange) refracting through the icy sorbet particles. Every pillar is wrapped in intensely flickering silver fairy lights, with entrance arches framed by intense teal neon strips.",
                "Es Krim Cornetto": "A colossal, large-scale 1-meter standalone mosque object made from thousands of spiral-swirled soft-serve ice cream mounds and chocolate discs. The architecture features a rhythmic, swirling creamy texture with high-gloss chocolate accents. Naskh-style calligraphy is formed by silver sugar pearls (sprinkles). The colossal main dome glows with a 'Frozen Galaxy' LED scheme (pale violet, ice blue, and soft magenta) creating a dreamy, diffused glow through the creamy texture. Every minaret is wrapped in flickering silver fairy lights.",
                "Donat Mini Pelangi": "A monumental, large-scale 1-meter standalone mosque object built entirely from millions of tiny mini-donuts with vibrant, multi-colored sugar glazes (pink, purple, lime, and cyan). The architecture features a bubbly, rounded, and highly textured organic surface. Intricate Thuluth-style calligraphy is formed by precisely arranged rainbow sprinkles (meses) and silver sugar pearls, glowing with a 'Candy Neon' LED scheme (bubblegum pink, electric violet, and bright gold) reflecting off the glossy glaze. Tall minarets are stacks of mini donuts wrapped in flickering magenta fairy lights.",
                "Donat Cokelat": "A gigantic, large-scale 1-meter standalone mosque model constructed from thousands of mini donuts coated in thick, dark chocolate ganache and dusted with edible gold leaf. The structure has a rich, high-gloss, and luxurious texture. Elegant Kufic-style calligraphy is etched into the chocolate to reveal a white cream filling, glowing from within with a 'Royal Cocoa' LED scheme (warm amber, copper, and bright gold) seeping through the chocolate cracks. Every minaret is a tall stack of golden donuts wrapped in rapidly pulsing gold fairy lights.",
                "Donat Glazed": "A colossal, large-scale 1-meter standalone mosque object made from thousands of clear-glazed mini donuts covered in a dense layer of neon-colored chocolate sprinkles. The architecture features a hyper-detailed, granular, and shimmering texture. Naskh-style calligraphy is formed by the arrangement of dark chocolate sprinkles against a neon background. The colossal main dome glows with a 'Technicolor Dream' LED scheme (rainbow colors, bright yellow, and hot pink) refracting through the sugary glaze. Every minaret is wrapped in flickering multi-colored fairy lights.",
                "Lolipop Spiral": "A monumental, large-scale 1-meter standalone mosque object built from thousands of giant swirl lollipops. The architecture features a hard, translucent 'glass-candy' texture with vibrant spiral patterns (red, white, and lime). Intricate Thuluth-style calligraphy is etched into the hard candy surface, glowing with a 'Prism Pop' LED scheme (neon pink, bright yellow, and electric cyan) refracting through the translucent lollipop sticks. Tall minarets are long candy canes wrapped in flickering silver fairy lights, with entrance arches outlined in pulsing rainbow neon strips.",
                "Oreo & Cream": "A gigantic, large-scale 1-meter standalone mosque model constructed entirely from thousands of Oreo cookies. The structure features a dark-black cocoa-biscuit texture with white cream filling visible in the layers. Elegant Kufic-style calligraphy is carved into the black biscuit surface to reveal the snowy white cream underneath, glowing from within with a 'Midnight Milk' LED scheme (cool white, pale blue, and soft silver) seeping through the cookie gaps. Every minaret is a tall stack of Oreos wrapped in rapidly pulsing white fairy lights.",
                "Marshmallow Cloud": "A monumental, large-scale 1-meter standalone mosque object built from millions of soft, puffy marshmallows (pink, white, and yellow). The architecture features a spongy, matte, and 'cloud-like' organic texture. Elegant Diwani-style calligraphy is formed by drizzling melted chocolate over the soft surface, glowing with a 'Soft Pastel' LED scheme (bubblegum pink, mint green, and pale violet) creating a hazy, diffused glow through the marshmallows. Every pillar is wrapped in intensely flickering warm-white fairy lights, with entrance arches framed by intense gold neon strips.",
                "Gummy Bears & Jelly": "A colossal, large-scale 1-meter standalone mosque object made from thousands of translucent gummy bears and jelly beans. The architecture features a squishy, high-gloss, and semi-transparent fruit-gel texture. Naskh-style calligraphy is formed by arranging dark-purple gummies against a bright-yellow background. The colossal main dome glows with a 'Neon Jungle' LED scheme (vibrant green, hot pink, and electric orange) refracting through the gelatinous body. Every minaret is a stack of jelly beans wrapped in flickering multi-colored fairy lights."    
            },
            # --- 3. MASTER KONTEN (🌍 WORLD MOSQUE DIORAMA - CRAFT SCALE EDITION) ---
            "🌍 Diorama Masjid": {
                "Masjidil Haram": "A hyper-detailed 1-meter standalone diorama of Masjidil Haram, frozen in a static moment of peak crowd. Millions of 2-millimeter scale static miniature figures in white robes are positioned in mid-stride, captured in a massive circular formation around the Kaaba. The figures are fixed, motionless plastic/resin models. The architecture is pure white polished marble with gold leaf. The Kaaba stands still in the center with its textured black silk Kiswah. Glowing with 'Champagne Solar' LED lights from the fixed minarets.",
                "Al-Aqsa": "A monumental 1-meter static diorama of the Al-Aqsa compound. Thousands of tiny, motionless figures are captured in various still poses: some walking through the arches, some standing in silent rows for prayer in the courtyard. Every figure is a fixed, non-moving miniature. The Dome of the Rock features a stationary hammered-gold surface with intense amber LED glow. The ancient limestone textures are sharp and frozen. The atmosphere is silent and still, illuminated by flickering (light-only) fairy lights on the fixed trees.",
                "Nabawi": "A colossal 1-meter static diorama of the Prophet's Mosque (Nabawi) in Madinah. Featuring the iconic Green Dome and the giant stationary mechanical umbrellas in an open position. Thousands of static miniature pilgrims are frozen in place throughout the vast marble courtyards. The green dome glows with a 'Sacred Emerald' LED scheme. Every architectural detail is captured in a silent, motionless state. High-contrast lighting between the white marble and the dark-green shadows.",
                "Masjidil Haram (Ottoman Era)": "A detailed 1-meter high diorama object depicting the historical Masjidil Haram complex during the Ottoman period (19th century). The Kaaba is central, surrounded by low-rise stone buildings with multiple small, lead-domed roofs and slender, pencil-shaped minarets. The courtyard is paved with ancient weathered stone. Hundreds of motionless miniature figures are praying in circles. The entire structure of ancient red brick and rough stone is wrapped in flickering warm-white fairy lights, glowing with 'Ancient Torchlight' amber LED light. A static, quiet, historical moment.",
                "Masjidil Haram (tahun 2030)": "A colossal, hyper-futuristic 1-meter standalone diorama of Masjidil Haram as envisioned in Vision 2030. The Kaaba is encircled by a massive, multi-tiered ring of modern architecture (Mataf Bridge) made of carbon fiber, glass, and polished gold. The roofs are kinetic, open-structure designs. Millions of static miniature pilgrims are frozen in place throughout the vast complex. Glowing with a 'Cyber-Neon Makkah' LED scheme (electric cyan, white-hot, and violet) reflecting off the glass and futuristic metallic surfaces. A static, breathtaking vision of the future.",
                "Masjidil Haram (tahun 90an)": "A grand, symmetrical 1-meter high diorama of Masjidil Haram after the King Fahd expansion. Featuring the massive white structure with its iconic two twin minarets and expansive white marble courtyards. Thousands of motionless pilgrims are frozen in various prayer poses. The architecture is pure white polished stone with elegant gold-filigree calligraphy. Illuminated by a 'Divine White' LED scheme (pure white, soft cream, and gold) reflecting off the smooth marble surfaces. A static, solemn, and grand moment from the 90s.",
                "Masjidil Haram (Zaman Nabi)": "A high-detailed 1-meter standalone diorama of Makkah during the early years of Islam. The central Kaaba is built from rough, jagged black mountain stones with a simple textured cover. Around it is a dusty desert courtyard (Mataf) made of dry golden sand. Surrounding the Kaaba are clusters of ancient Makkan houses built from mud-bricks, rough stones, and palm leaf roofs. Millions of tiny miniature figures are gathered in small groups. Glowing with a 'Desert Moonlight' LED scheme (pale moonlight white and dim amber oil-lamp flickers) reflecting off the sand and rough stones. The atmosphere is raw, ancient, and deeply spiritual.",
                "Kaaba Cut-Away (Interior Reveal)": "A unique 1-meter high cross-section diorama of the Holy Kaaba. One half of the Kaaba is a solid black silk-textured exterior, while the other half is sliced open to reveal the hyper-detailed interior. Inside features three tall, dark-wood pillars (teak), golden hanging lamps, and green-marble tiled floors with intricate Arabic calligraphy on the inner walls. The interior glows with an intense 'Golden Secret' LED scheme (bright 24K gold, warm amber) focused solely on the internal chamber, while the exterior remains in soft shadows. A static, educational architectural masterpiece.",
                "Masjidil Haram (The Golden Details)": "A monumental 1-meter high diorama focusing on the intricate details around the Kaaba. Features the hyper-detailed gold-lattice structure of Maqam Ibrahim and the smooth white marble curve of Hijr Ismail. The Kaaba stands majestic with its heavy gold-embroidered calligraphy on the black silk. Millions of tiny static pilgrims are filling the Mataf area. Illuminated by a 'Divine Gold' LED scheme (24K gold, warm amber, and white-hot spark) highlighting the golden ornaments and the texture of the Kiswah. A static masterpiece of sacred craftsmanship.",
                "Masjid Nabawi": "A magnificent 1-meter high standalone diorama of the Prophet's Mosque in Madinah. Featuring the iconic bright-green central dome and dozens of giant, static open hydraulic umbrellas with intricate cream-colored fabric textures. The architecture is built from white marble with golden floral inlays. Thousands of static miniature pilgrims are frozen in the vast courtyard. Glowing with a 'Sacred Emerald' LED scheme (vibrant green on the dome, warm amber under the umbrellas) reflecting off the polished floor. A static, breathtaking spiritual masterpiece.",
                "Sheikh Zayed Grand Mosque": "A colossal 1-meter high diorama made of pure white crystalline marble. Featuring 82 domes of various sizes and four 107-meter tall minarets. The courtyard features hyper-detailed floral marble mosaics. The entire structure is surrounded by static 'mirrored water' pools made of blue tinted glass. Glowing with a 'Lapis Lazuli' LED scheme (electric blue and cool white) that creates a celestial atmosphere. Thousands of tiny static figures are walking through the grand arches. High-luxury architectural detail.",
                "Masjid Agung Xi'an": "A unique 1-meter high diorama of the Great Mosque of Xi'an, featuring traditional Chinese Pagoda architecture. Built from dark aged wood, turquoise-glazed roof tiles, and intricate dragon-style carvings. Instead of domes, it features grand pavilions and Chinese gateways (Paifang). The walls are covered in Arabic calligraphy stylized in Chinese brush-stroke patterns. Glowing with an 'Oriental Zen' LED scheme (warm red, soft jade green, and dim gold) illuminating the wooden courtyards. A static, rare cultural fusion masterpiece.",
                "Masjid Istiqlal": "A monumental 1-meter high standalone diorama of the National Mosque of Indonesia, Istiqlal. The architecture features a massive stainless steel dome and a single tall minaret, built with a 'Brutalist-Grand' aesthetic using grey marble and steel. The interior is sliced open to show the 12 massive stainless steel pillars and the intricate geometric patterns on the dome's underside. Thousands of tiny static figures are frozen in the vast, open prayer halls. Glowing with a 'Modern Steel' LED scheme (cool white, pale silver, and bright industrial white) reflecting off the metal and marble surfaces. A static, solemn, and powerful masterpiece.",
                "Masjid Al-Jabbar": "A breathtaking 1-meter high standalone diorama of the 'floating' Al-Jabbar mosque. The architecture features a colossal, multi-layered roof shaped like a blooming geometric flower, built from thousands of interlocking glass panels. The structure is surrounded by a 'mirrored water' lake made of blue-tinted glass. Thousands of tiny static figures are walking across the bridges and courtyards. Glowing with a 'Techno-Religious' LED scheme (vibrant violet, electric blue, and warm gold) pulsing through the glass facets, creating a kaleidoscopic glow on the water. A static, futuristic, and colorful architectural marvel.",
                "Masjid Raya Solo": "A monumental 1-meter high standalone diorama of the Sheikh Zayed Grand Mosque in Solo. The architecture features a mini-version of the Abu Dhabi masterpiece with four tall minarets and dozens of white marble domes. The structure is built from pure white stone with intricate gold-leaf floral accents. The floors feature hyper-detailed batik-inspired marble mosaics. Thousands of tiny static figures are walking through the arched courtyards. Glowing with a 'Celestial Moon' LED scheme (icy white, soft lavender, and bright gold) reflecting off the polished marble. A static, high-luxury architectural marvel in the heart of Java.",
                "Masjid Keraton": "A high-detailed 1-meter standalone diorama of the historical Grand Mosque of the Surakarta Palace. The architecture features a traditional Javanese 'Tajug' multi-tiered roof made of dark weathered wood and clay tiles. The structure is supported by massive teak wood pillars (Soko Guru) with intricate 'Ultah' gold carvings. Features the iconic 'Gapura' entrance and a moat (parit) surrounding the mosque. Thousands of tiny static figures are frozen in traditional Javanese attire (Batik and Blangkon). Glowing with a 'Royal Heritage' LED scheme (warm amber, flickering torchlight, and deep gold) reflecting off the dark wood. A static, ancient, and deeply cultural masterpiece.",
                "Masjid Gedhe Kauman ": "A magnificent 1-meter high standalone diorama of the Great Mosque of the Yogyakarta Sultanate. The architecture features a grand triple-tiered Javanese 'Tajug' roof made of dark-brown ancient wood and traditional clay tiles, topped with a golden 'Mustaka' ornament. The structure is built with massive teak wood pillars and features a large front porch (Serambi) with intricate yellow and green royal carvings. Thousands of tiny static figures in traditional Javanese Batik and Beskap are frozen in prayer. Glowing with a 'Keraton Moonlight' LED scheme (warm amber, soft yellow, and dim flickering torchlight) illuminating the dark wood and white stone walls. A static, deeply spiritual, and historical masterpiece.",
                "Masjid Jogokariyan": "A high-detailed 1-meter standalone diorama of the iconic Masjid Jogokariyan in its vibrant evening atmosphere. The architecture features the famous green and cream facade with the prominent 'Masjid Jogokariyan' signage. The diorama captures the lively street-side atmosphere with hundreds of static miniature figures gathered for Iftar or prayers. The structure features a blend of modern and traditional Javanese elements. Glowing with a 'Community Glow' LED scheme (bright warm-white, festive green neon, and soft orange) creating a welcoming and busy urban-mosque vibe. A static masterpiece of modern Indonesian Islamic culture."
                    
            }
        }

        # --- 3. MASTER LOKASI (FIXED: NATURAL CLUTTER & SOLID BACKDROP) ---
        MASTER_GRANDMA_SETTING = {
            "Lantai Semen & Tembok Retak": (
                "Sitting cross-legged directly on a cold, unpolished grey cement floor (plesteran) with visible sandy textures and fine cracks. "
                "The background is a solid wall of raw, unpainted grey cement with weathered water stains and rough patches. "
                "Next to her is a glass of tea with a rusty metal lid, a pair of old rubber sandals (sandal jepit), and a small plastic plate with boiled cassava. "
                "Focus on the gritty concrete texture and the raw, unpolished stone-like environment."
            ),
            "Tikar Mendong & Dinding Gedek": (
                "Sitting cross-legged on a hand-woven natural 'Tikar Mendong' straw mat with frayed edges and organic fiber textures. "
                "The background is a solid wall of old, woven bamboo sheets (gedek) with dust particles trapped in the weaves and greyish fading fibers. "
                "Surrounding objects: a traditional hand-woven leaf fan (kipas bambu), an old analog radio, and a small tin box for betel nut (sirih). "
                "Focus on the organic, dry texture of the bamboo and straw."
            ),
            "Lantai Tanah & Dinding Bata": (
                "Sitting cross-legged on a flat, hardened earth floor (tanah liat) with dry, dusty surface textures. "
                "The background is a solid wall of exposed red bricks with thick, messy mortar and dark soot stains (jelaga). "
                "Next to her is a basket of unpeeled shallots, a small pile of dry rough firewood, and a stone mortar (cobek) with chili residue. "
                "Focus on the rough brick surfaces and the earthy, dusty soil texture."
            ),
            "Sajadah Tua & Tembok Kayu": (
                "Sitting cross-legged on a worn-out, faded velvet sajadah (prayer mat) placed directly over a dark, weathered wooden floor. "
                "The background is a solid wall of vertical dark teak wood planks with prominent deep grain and peeling varnish. "
                "Surrounding objects: a string of wooden prayer beads (tasbih), a small plain ceramic water jug, and a stack of old religious books with yellowing pages. "
                "Focus on the aged wood grain and the soft but thinning fabric texture of the mat."
            ),
            "Tikar Pandan & Tembok Cat Kusam": (
                "Sitting cross-legged on a pale-green 'Tikar Pandan' mat with a distinct cross-weave pattern. "
                "The background is a solid plastered wall with old, chalky white paint that is peeling and bubbling in several spots. "
                "Next to her is a large glass jar of crackers (kerupuk), a small bottle of eucalyptus oil, and a discarded newspaper from years ago. "
                "Focus on the brittle paint flakes and the ribbed texture of the pandan mat."
            ),
            "Lantai Tegel Kunci & Dinding Tua": (
                "Sitting cross-legged on vintage 'Tegel Kunci' cement tiles with a faded geometric floral pattern and matte finish. "
                "The background is a solid, thick masonry wall with visible dampness (rembes) and moss-green stains at the bottom. "
                "Surrounding objects: a brass tray with a single glass of tea, a small coil of mosquito incense (obat nyamuk bakar), and a worn-out batik sarong folded nearby. "
                "Focus on the smooth but aged stone feel of the tiles and the damp texture of the wall."
            ),
            "Pematang Sawah & Hamparan Padi": (
                "Sitting cross-legged on a narrow, hardened mud path (pematang). "
                "The background is a solid, vast expanse of ripening yellow rice stalks (padi) with heavy, drooping grains. "
                "Texture details: dried cracked mud on the path, rough husks of the rice, and dry straw stubble. "
                "Next to her: a worn-out 'caping' straw hat, a rusted sickle (arit), and a plastic water bottle wrapped in damp cloth. "
                "Focus on the organic yellow and brown textures of the harvest."
            ),
            "Bawah Pohon Bambu (Kebun)": (
                "Sitting cross-legged on a thick carpet of dry, fallen bamboo leaves. "
                "The background is a dense, impenetrable wall of green and yellow bamboo trunks (rumpun bambu) with dusty nodes. "
                "Texture details: crispy dry leaves, smooth but scarred bamboo skin, and loose dark soil. "
                "Next to her: a traditional woven bamboo basket (tenggok), a small pile of dry twigs, and an old analog radio. "
                "Focus on the layered textures of the forest floor."
            ),
            "Pinggir Sungai Batu Kali": (
                "Sitting cross-legged on a large, flat river stone with grey mineral deposits. "
                "The background is a steep riverbank made of stacked natural river rocks and exposed tree roots. "
                "Texture details: porous stone surfaces, damp moss, and gritty river sand. "
                "Next to her: a pair of old rubber sandals (sandal jepit), a simple ceramic teapot, and a small metal tray of crackers. "
                "Focus on the contrast between hard stone and soft moss."
            ),
            "Halaman Pasir & Semak Belukar": (
                "Sitting cross-legged on a patch of coarse grey volcanic sand (pasir urug). "
                "The background is a wild, dense thicket of tropical ferns and tall 'alang-alang' grass. "
                "Texture details: grainy sand, sharp edges of the grass blades, and dry twigs. "
                "Next to her: a traditional broom (sapu lidi), a small coil of mosquito incense (obat nyamuk), and a glass of tea with a metal lid. "
                "Focus on the gritty and bushy organic textures."
            ),
            "Kebun Singkong & Tanah Merah": (
                "Sitting cross-legged on firm, reddish-brown clay soil (tanah merah). "
                "The background is a row of tall cassava plants (pohon singkong) with large, hand-shaped leaves. "
                "Texture details: clumpy red earth, rough woody cassava stems, and dry fallen leaves. "
                "Next to her: a woven plastic sack, a small garden trowel, and a plate of boiled bananas. "
                "Focus on the deep earthy tones and woody textures."
            ),
            "Tepi Jalan Setapak & Pagar Bambu": (
                "Sitting cross-legged on a dusty dirt road with small pebbles and tire track imprints. "
                "The background is a long, rustic fence made of weathered, split bamboo poles (pagar salang). "
                "Texture details: fine grey dust, splintered bamboo fibers, and rusted wire ties. "
                "Next to her: a glass of coffee, a small tin box for betel nut (sirih), and a wandering village chicken nearby. "
                "Focus on the dry, dusty village atmosphere."
            ),
            "Gubuk Bambu & Lantai Tanah": (
                "Sitting cross-legged on a hard-packed, dusty earthen floor inside a small hut. "
                "The background is a wall made of old, frayed bamboo weaving (gedek) with visible gaps and hanging spiderwebs. "
                "Texture details: dusty dry soil, splintered bamboo fibers, and brittle organic matter. "
                "Next to her: a stack of dry firewood, a blackened clay stove (tungku) without fire, and a traditional woven bamboo basket. "
                "Focus on the greyish, dusty, and dilapidated bamboo textures."
            ),
            "Lantai Kayu Lapuk & Dinding Papan": (
                "Sitting cross-legged on a floor made of uneven, weathered wooden planks with large gaps and protruding rusty nails. "
                "The background is a solid wall of vertical dark wood boards with peeling bark and deep termite tracks. "
                "Texture details: rough wood grain, flaky dry wood rot, and metallic rust. "
                "Next to her: an old kerosene lamp (lampu templok) without glass, a small tin of betel nut, and a folded, faded sarong. "
                "Focus on the decaying timber and ancient wood textures."
            ),
            "Gubuk Sawah & Atap Rumbia": (
                "Sitting cross-legged on a low bamboo platform (amben) built close to the ground. "
                "The background features low-hanging eaves made of dried, shredded palm leaves (atap rumbia) and rough wooden poles. "
                "Texture details: crispy dried leaves, coarse grey wood, and dusty straw. "
                "Next to her: a rusted sickle (arit), a traditional 'caping' hat, and a glass of tea with a dusty metal lid. "
                "Focus on the dry, brittle textures of the palm leaves and old wood."
            ),
            "Sudut Gubuk & Tumpukan Karung": (
                "Sitting cross-legged on a piece of old, torn tarpaulin (terpal) over the dirt floor. "
                "The background is a stack of overflowing woven plastic sacks (karung goni) filled with harvested grains and dry husks. "
                "Texture details: rough plastic weave, fibrous burlap, and dusty grain particles. "
                "Next to her: a small plastic bucket, a bundle of tied dry corn husks, and a pair of broken rubber sandals. "
                "Focus on the industrial-agricultural clutter and messy textures."
            ),
            "Gubuk Kebun & Dinding Pelepah": (
                "Sitting cross-legged on a flat natural stone inside a makeshift shelter. "
                "The background is a wall constructed from dried coconut leaf stalks (pelepah) tied with rusted wire. "
                "Texture details: ribbed leaf stalks, coarse dry fibers, and oxidized wire. "
                "Next to her: a traditional broom (sapu lidi), a small clay water jug, and a plate of cold boiled sweet potatoes. "
                "Focus on the raw, unpolished organic construction materials."
            ),
            "Teras Gubuk & Pagar Rengkek": (
                "Sitting cross-legged on a dusty, cracked concrete slab at the entrance of a hut. "
                "The background is a rustic fence made of split bamboo branches and weathered sticks. "
                "Texture details: sharp splintered edges, fine dust covering everything, and dry moss. "
                "Next to her: a glass of black coffee, an old analog radio, and a wandering village chicken. "
                "Focus on the dry, splintery, and humble village textures."
            ),
            "Lembah Berkabut & Terasering Padi": (
                "Sitting cross-legged directly on hard-packed, cracked reddish clay soil (tanah merah). "
                "The background is a vast, expansive mountain range (pegunungan) with layered blue and green tones. "
                "The foreground features extensive rice paddy terraces (terasering) with textured mud dikes and young green stalks. "
                "Textural details: gritty soil, rough mud dikes, and dry straw stubble. "
                "Next to her: a woven bamboo basket (tenggok), a traditional 'caping' hat, and a glass of warm tea with a metal lid. "
                "Focus on the organic earth tones and agricultural textures against the mountain backdrop."
            ),
            "Puncak Bukit & Hutan Pinus": (
                "Sitting cross-legged on a thick carpet of dry, fallen pine needles and rough pebbles. "
                "The background is a solid wall of dense, tall dark-green pinus forest trunks (hutan pinus). "
                "Texture details: crispy dry needles, smooth but scarred pine bark, and loose forest floor soil. "
                "Next to her: an antique analogue radio, a bundle of dry twigs, and a simple ceramic water jug. "
                "Focus on the layered textures of the forest floor and tree bark."
            ),
            "Perkebunan Teh & Pagar Bambu": (
                "Sitting cross-legged on firm, greyish-brown clay soil mixed with fine tea leaf dust. "
                "The background is a dense, manicured hedge of low-growing tea plants (perkebunan teh) stretching into the horizon. "
                "Texture details: clumpy earth, rough tea stems, and dry fallen leaves. "
                "Next to her: a woven plastic sack, a small garden trowel, and a plate of boiled bananas. "
                "Focus on the deep earthy tones and woody textures of the tea plantation."
            ),
            "Sungai Pegunungan & Batu Kali": (
                "Sitting cross-legged on a large, flat river stone with grey mineral deposits and moss growth. "
                "The background is a steep riverbank made of stacked natural river rocks and exposed tree roots. "
                "Texture details: porous stone surfaces, damp moss, and gritty river sand. "
                "Next to her: a pair of old rubber sandals (sandal jepit), a simple ceramic teapot, and a small metal tray of crackers. "
                "Focus on the contrast between hard stone and soft moss."
            ),
            "Lereng Gunung & Tumpukan Karung": (
                "Sitting cross-legged on a piece of old, torn tarpaulin (terpal) over the dirt floor. "
                "The background is a stack of overflowing woven plastic sacks (karung goni) filled with harvested grains and dry husks. "
                "Texture details: rough plastic weave, fibrous burlap, and dusty grain particles. "
                "Next to her: a small plastic bucket, a bundle of tied dry corn husks, and a pair of broken rubber sandals. "
                "Focus on the industrial-agricultural clutter and messy textures on the slope."
            ),
            "Kebun Salak & Tanah Lembap": (
                "Sitting cross-legged on damp, dark soil covered in sharp, dry salak leaf debris. "
                "The background is a dense, thorny thicket of salak palms (pohon salak) with jagged, spiked fronds and clusters of brown snake-fruit. "
                "Texture details: scaly skin of the salak fruit, sharp thorny stems, and moist, clumpy earth. "
                "Next to her: a small bamboo basket (tenggok) filled with harvested salak, a rusty sickle, and a pair of old rubber sandals. "
                "Focus on the prickly, dark, and organic textures of the salak grove."
            ),
            "Bawah Pohon Mangga & Daun Kering": (
                "Sitting cross-legged on a thick layer of crispy, brown fallen mango leaves and small dry twigs. "
                "The background is the solid, gnarled trunk of an ancient mango tree with thick, textured grey bark. "
                "Texture details: rough deeply-fissured bark, brittle dry leaves, and small sap droplets. "
                "Next to her: a plastic bucket of green mangoes, a glass of warm tea with a metal lid, and a traditional hand-woven fan. "
                "Focus on the contrast between the rough bark and the crunchy leaf carpet."
            ),
            "Kebun Pisang & Tanah Becek": (
                "Sitting cross-legged on a piece of old, flattened cardboard over slightly muddy brown earth. "
                "The background is a solid wall of tall banana plants with huge, shredded green leaves and heavy bunches of green bananas (pisang kepok). "
                "Texture details: smooth but waxy banana trunks, torn fibrous leaves, and slippery mud patches. "
                "Next to her: a bundle of dried banana leaves (klaras), a sharp machete (golok), and a plate of boiled bananas. "
                "Focus on the tropical, lush, and slightly messy banana plantation vibe."
            ),
            "Bawah Pohon Rambutan": (
                "Sitting cross-legged on firm soil covered in scattered red rambutan skins and fallen yellowing leaves. "
                "The background features low-hanging branches laden with bright red, hairy rambutan fruits. "
                "Texture details: soft hairy spines of the fruit, thin woody branches, and gritty soil. "
                "Next to her: a large woven plastic sack, an old analog radio, and a string of wooden prayer beads (tasbih). "
                "Focus on the vibrant organic colors against the dry, dusty ground."
            ),
            "Kebun Durian & Akar Besar": (
                "Sitting cross-legged between massive, protruding wooden roots of an old durian tree. "
                "The background is a solid forest-like environment with tall durian trees and dense tropical foliage. "
                "Texture details: hard thorny shells of durian fruit on the ground, mossy giant roots, and dry forest mulch. "
                "Next to her: a small kerosene lamp (off), a bamboo water container, and a glass jar of crackers. "
                "Focus on the sharp, hard textures of the fruit and the prehistoric feel of the roots."
            ),
            "Kebun Pepaya & Pagar Bambu": (
                "Sitting cross-legged on a flat natural stone on the edge of a small papaya orchard. "
                "The background is a row of tall, thin papaya trees with hollow-looking trunks and large umbrella-like leaves. "
                "Texture details: scarred greyish trunks, soft orange fruit flesh (if cut), and a rustic split-bamboo fence. "
                "Next to her: a traditional broom (sapu lidi), a small tin box for betel nut, and a wandering village chicken. "
                "Focus on the tall vertical lines and the humble village garden textures."
            ),
            "Kebun Melon Gantung & Tanah Mulsa": (
                "Sitting cross-legged on a piece of dark, glossy silver-black plastic mulching film (mulsa) covering the soil. "
                "The background is a dense, impenetrable wall of green melon vines supported by vertical bamboo trellises. "
                "The vines are heavily laden with dozens of ripe green and yellow melons (cantaloupe) with highly detailed, intricate reticulated 'net' textures on their skins. "
                "The scene is overwhelmingly rimbun (lush). Textural details: rough net patterns, fuzzy leaves, and thick green vines. "
                "Next to her: a woven bamboo basket (tenggok) filled with harvested, high-detail melons, a pruning shear, and a glass of warm tea with a metal lid. "
                "Focus on the complex net textures and vibrant green and orange tones against the black plastic."
            ),
            "Kebun Semangka Tanah & Hamparan Daun": (
                "Sitting cross-legged on a hand-woven natural 'Tikar Mendong' straw mat with frayed edges. "
                "The background is a vast, dense ground-cover of thick green semangka (watermelon) leaves and sprawling vines. "
                "Dozens of large, heavy, round and oval watermelons are scattered among the rimbun leaves, showing highly detailed, prominent deep-green and pale-green striped patterns with high-gloss natural rind. "
                "Textural details: bold striped patterns, fuzzy green leaves, and wet mud patches on the fruit. "
                "Next to her: a classic brass betel nut box (sirih), a small coil of mosquito incense, and a pair of old rubber sandals. "
                "Focus on the high-contrast stripes and the wet, glossy look of the natural rind."
            ),
            "Kebun Strawberry & Mulsa Hitam": (
                "Sitting cross-legged on a heavy black plastic mulching film covering the elevated soil beds. "
                "The background features rows and rows of elevated strawberry plants (pohon strawberry) with dense green leaves and small white flowers. "
                "The scene is rimbun with thousands of ripe, bright red strawberry fruits, showing incredibly detailed surface textures with deep seed patterns and waxy, glossy finish. "
                "Textural details: highly intricate seed patterns, fuzzy leaves, and waxy fruit skin. "
                "Next to her: an old analogue radio with a telescopic antenna, a wooden mortal (cobek), and a pile of dry firewood. "
                "Focus on the incredibly sharp seed detail and the explosive bright red and green colors."
            ),
            "Kebun Anggur Teralis & Hamparan Tanah": (
                "Sitting cross-legged on a large, flat river stone with grey mineral deposits and moss growth. "
                "The background is a monumental, sprawling 'U'-shaped overhead bamboo and wire trellis system, dense and heavy with rimbun clusters of deep purple (kismis) and vibrant green (tanpa biji) grapes. "
                "Each grape bunch is hyper-detailed, with individual fruit showing highly rendered natural 'waxy bloom' (powdery substance) and translucent pulp when broken. "
                "Textural details: detailed grape skin pores, fuzzy green leaves, and old, knotty wood. "
                "Next to her: an antique brass betel nut box, a small tin box for betel nut (sirih), and a traditional broom (sapu lidi). "
                "Focus on the waxy bloom and the explosive purple, green, and orange colors."
            ),
            "Taman Paku-Pakuan & Tembok Berlumut": (
                "Sitting cross-legged on a patch of damp soil covered in thin green moss and scattered dry twigs. "
                "The background is a solid wall of dense, rimbun tropical ferns (pakis) and bird's nest ferns with jagged, vibrant green leaves. "
                "The wall behind the plants is old red brick covered in thick, dark-green velvety moss and water stains. "
                "Texture details: fuzzy moss, porous damp bricks, and the ribbed veins of fern leaves. "
                "Next to her: a weathered terracotta plant pot with cracks, a small rusty garden trowel, and a glass of tea with a metal lid. "
                "Focus on the deep green saturation and the damp, earthy textures."
            ),
            "Taman Bunga Kertas (Bougainvillea) & Pasir": (
                "Sitting cross-legged on a layer of coarse grey volcanic sand mixed with fallen flower petals. "
                "The background is a monumental, rimbun explosion of Bougainvillea (Bunga Kertas) in vibrant magenta and orange, with thorny woody stems intertwined. "
                "Texture details: paper-like flower petals, sharp woody thorns, and gritty sand particles. "
                "Next to her: a traditional broom (sapu lidi), a small plastic bucket, and a pair of old rubber sandals (sandal jepit). "
                "Focus on the high-contrast flower colors against the dry, grey sandy ground."
            ),
            "Taman Lidah Mertua & Lantai Semen": (
                "Sitting cross-legged on a rough, unpolished concrete floor with visible sand grains and thin cracks. "
                "The background is a dense row of tall, sharp Sansevieria (Lidah Mertua) plants with highly detailed yellow-green striped patterns on their stiff leaves. "
                "Texture details: leathery leaf surfaces, gritty concrete, and small pebbles. "
                "Next to her: a glass jar of crackers (kerupuk), an old analog radio, and a string of wooden prayer beads (tasbih). "
                "Focus on the sharp vertical lines and the waxy, striped texture of the leaves."
            ),
            "Taman Keladi & Kolam Batu": (
                "Sitting cross-legged on a large, flat natural river stone with a matte grey finish. "
                "The background is a lush, rimbun collection of Caladium (Keladi) plants with huge, heart-shaped leaves showing intricate red and white vein patterns. "
                "Nearby is the edge of a small pond made of stacked rough mountain stones with natural water splashes. "
                "Texture details: translucent leaf membranes, porous volcanic stones, and wet mineral deposits. "
                "Next to her: a brass tray with a teapot, a small tin box for betel nut, and a discarded old newspaper. "
                "Focus on the intricate leaf veins and the raw, wet stone textures."
            ),
            "Teras Semen & Kolam Air Jernih": (
                "Sitting cross-legged on a rough, unpolished concrete patio floor (plesteran) with visible sand grains and fine cracks. "
                "The background is a solid, weathered wall of rough-textured grey cement with faded water stains. "
                "The scene features the edge of a clean, pure water pond constructed from large, flat volcanic rocks with smooth but gritty surfaces. "
                "Inside the pond, hundreds of colorful Koi fish (Ogon, Shusui, Tancho) create a dense, rimbun wall of shimmering colors, including metallic gold, silver, bright yellow, and solid red. "
                "Texture details: gritty concrete surface, dusty cement patches, clear water clarity, and iridescent fish skin reflections. "
                "Next to her: a glass jar of crackers (kerupuk), an old analog radio, and a string of wooden prayer beads (tasbih). "
                "Focus on the gritty textures, the waxy waxy look of the cement, and the explosive iridescence of the fish."
            ),
            "Tikar Pandan & Kolam Pagar Bambu": (
                "Sitting cross-legged on a pale-green 'Tikar Pandan' mat with a distinct cross-weave pattern, placed near the pond's edge. "
                "The background is a rustic fence made of split bamboo poles and weathered sticks. "
                "The scene features a small, simple pond with clean, pure water, built from stacked irregular river stones with dry moss. "
                "Inside the pond, dozens of varied colorful Koi fish (Asagi, Bekko, Koromo) swim in rimbun groups, displaying highly rendered patterns of blue-grey scales, bold black spots, and intricate crimson red markings. "
                "Texture details: ribbed texture of the pandan mat, sharp splintered edges of bamboo, rough stone surfaces, and intricate fish scale patterns. "
                "Next to her: a traditional broom (sapu lidi), a small plastic bucket, and a pair of old rubber sandals (sandal jepit). "
                "Focus on the dry organic textures, the raw bamboo, and the detailed patterns of the fish."
            ),
            "Tembok Bata Berlumut & Kolam Teratai": (
                "Sitting cross-legged on a patch of damp soil covered in thin green moss and scattered dry twigs. "
                "The background is an old, weathered red brick wall covered in thick, dark-green velvety moss and water stains. "
                "The scene features the edge of a large, natural pond filled with pure, clear water and several rimbun clusters of pink and white water lilies (teratai). "
                "Inside the pond, hundreds of vibrant colorful Koi fish (Doitsu, Goromo, Goshiki) navigate through the lilies in rimbun formations, showing intricate scales in sharp patterns of deep purple, gold, crimson, and black. "
                "Texture details: fuzzy moss, porous damp bricks, translucent lily pads, and raw fish skin texture. "
                "Next to her: a brass tray with a teapot, a small tin box for betel nut, and a discarded old newspaper. "
                "Focus on the deep green saturation, the raw wet bricks, and the explosive patterns of the fish."
            ),
            "Pinggir Kolam Batu & Koi Kohaku": (
                "Sitting cross-legged on a large, flat, damp river stone at the very edge of the water. "
                "The background is a solid wall of dense tropical ferns and mossy rock formations. "
                "In front of her is a clear, deep pond filled with dozens of rimbun Koi fish, primarily 'Kohaku' with bold red and white patterns. "
                "The water is crystal clear, showing the high-detail scales of the fish and their fluid movements. "
                "Next to her: a brass bowl of fish food (pelet) and a glass of tea with a metal lid. "
                "Focus on the sharp contrast between the white-red fish and the dark mossy rocks."
            ),
            "Sudut Kolam Batu & Koi Biru-Perak": (
                "Sitting cross-legged on a cluster of flat natural stones. "
                "The background is a dense thicket of tall Sansevieria plants and thick garden bushes. "
                "The pond features rare 'Asagi' and 'Shusui' Koi fish with blue-grey and silver scales, creating a rimbun, shimmering effect underwater. "
                "Texture details: porous grey stone, sharp vertical plant lines, and highly rendered fish scale patterns. "
                "Next to her: a small copper teapot and a pair of old rubber sandals (sandal jepit). "
                "Focus on the cool-toned blue and silver fish colors against the rough garden textures."
            ),
            "Pinggir Kolam Batu & Koi Kohaku": (
                "Sitting cross-legged on a large, flat, damp river stone at the very edge of the water. "
                "The background is a solid wall of dense tropical ferns and mossy rock formations. "
                "In front of her is a clear, deep pond filled with dozens of rimbun Koi fish, primarily 'Kohaku' with bold red and white patterns. "
                "The water is crystal clear, showing the high-detail scales of the fish and their fluid movements. "
                "Next to her: a brass bowl of fish food (pelet) and a glass of tea with a metal lid. "
                "Focus on the sharp contrast between the white-red fish and the dark mossy rocks."
            ),
            "Pinggir Sungai Batu & Akar Pohon": (
                "Sitting cross-legged on a large, flat, damp river stone with green mineral deposits. "
                "The background is a solid wall of massive, tangled tropical tree roots and dense ferns hanging over the water. "
                "The river water is clear, showing submerged mossy rocks and small river fish in rimbun groups. "
                "Texture details: porous wet stone, slippery moss, and rough fibrous roots. "
                "Next to her: a glass of tea with a rusty metal lid and a pair of old rubber sandals (sandal jepit). "
                "Focus on the raw, wet textures and the dark organic tones of the riverbank."
            ),
            "Pesisir Laut & Akar Bakau (Mangrove)": (
                "Sitting cross-legged on a patch of coarse, wet grey volcanic sand mixed with broken seashells. "
                "The background is a dense, impenetrable wall of rimbun Mangrove roots (bakau) twisting above the water line. "
                "The sea water is calm and clear, revealing hyper-detailed textures of the sandy bottom and small crabs. "
                "Texture details: gritty sand, sharp shell fragments, and salt-crusted wood. "
                "Next to her: a traditional woven bamboo basket (tenggok) and a small tin box for betel nut (sirih). "
                "Focus on the high-detail grit and the complex, weathered mangrove textures."
            ),
            "Tepi Danau Berbatu & Alang-Alang": (
                "Sitting cross-legged on a cluster of flat, dry mountain stones at the edge of a vast lake. "
                "The background is a rimbun wall of tall, golden-brown 'alang-alang' grass and wild shrubs. "
                "The lake water is crystal clear, reflecting the high-detail textures of the surrounding greenery. "
                "Texture details: sharp grass blades, dry dusty stones, and clear water ripples. "
                "Next to her: an old analog radio and a small plastic plate with boiled bananas. "
                "Focus on the contrast between the dry, sharp grass and the deep clear water."
            ),
            "Bebatuan Karang & Ombak Tenang": (
                "Sitting cross-legged on a jagged, weathered coral rock formation with sharp edges and salt deposits. "
                "The background is a solid view of the deep blue sea with natural foam and clear water textures. "
                "The shallow water near the rocks is rimbun with colorful sea moss and small corals visible through the surface. "
                "Texture details: rough porous coral, dried salt crust, and waxy sea plants. "
                "Next to her: a simple ceramic teapot and a string of wooden prayer beads (tasbih). "
                "Focus on the harsh, sharp textures of the coral against the fluid clear water."
            ),
            "Muara Sungai & Tumpukan Kayu Apung": (
                "Sitting cross-legged on a large piece of smooth, sun-bleached driftwood on a muddy bank. "
                "The background is a rimbun thicket of nipah palms and tall river reeds with dense green foliage. "
                "The water is a mix of clear and silty textures, showing organic debris and floating leaves. "
                "Texture details: smooth worn-out wood, clumpy dark mud, and ribbed palm leaves. "
                "Next to her: a traditional 'caping' hat and a small glass jar of crackers (kerupuk). "
                "Focus on the earthy mud tones and the skeletal textures of the driftwood."
            ),
            "Danau Pegunungan & Lumut Hijau": (
                "Sitting cross-legged on a thick carpet of vibrant green moss over a flat stone at a high-altitude lake. "
                "The background is a solid wall of ancient, moss-covered trees and thick mountain mist (visualized as texture). "
                "The lake water is incredibly clear, showing the high-detail submerged logs and green algae. "
                "Texture details: velvety soft moss, decaying wood, and cold, still water. "
                "Next to her: a small brass teapot and a discarded old newspaper. "
                "Focus on the deep green saturation and the ancient, damp forest textures."
            ),
            "Gundukan Sampah Plastik (TPA)": (
                "Sitting cross-legged directly on a massive pile of compressed plastic waste and torn colorful trash bags. "
                "The background is a solid, rimbun wall of towering garbage mounds consisting of discarded packaging, weathered plastics, and organic waste. "
                "Texture details: crinkled plastic, gritty dust, torn synthetic fibers, and sticky organic stains. "
                "Next to her: a rusted metal hook (pengait sampah), a dirty plastic sack (karung), and a pair of broken rubber sandals. "
                "Focus on the overwhelming clutter of artificial waste and the dirty, unpolished textures."
            ),
            "Gudang Rongsok Logam Berkarat": (
                "Sitting cross-legged on a floor made of scrap metal sheets and rusted iron plates. "
                "The background is an impenetrable wall of stacked rusted car parts, old bicycle frames, and twisted corrugated iron (seng). "
                "Texture details: deep orange iron rust (karat), sharp metallic edges, peeling paint, and thick oily grime. "
                "Next to her: a large rusted hammer, a pile of tangled copper wires, and a glass of black coffee in a stained glass. "
                "Focus on the harsh, sharp, and oxidized metallic textures."
            ),
            "Tumpukan Kardus & Kertas Bekas": (
                "Sitting cross-legged on flattened, weathered cardboard boxes on a dusty concrete floor. "
                "The background is a rimbun wall of tightly bound stacks of old newspapers, yellowed books, and brown corrugated cardboard. "
                "Texture details: fibrous paper edges, brittle cardboard, dust particles, and damp water stains. "
                "Next to her: a roll of dirty plastic twine, a rusted cutter, and an old analog radio with a missing antenna. "
                "Focus on the dry, papery, and dusty organic clutter."
            ),
            "Kuburan Botol Kaca & Beling": (
                "Sitting cross-legged on a piece of thick, dirty plywood over a field of crushed glass. "
                "The background is a solid wall of thousands of stacked glass bottles in various colors (amber, green, clear) covered in thick dust. "
                "Texture details: smooth but dirty glass surfaces, sharp crystalline shards, and dried mud. "
                "Next to her: a plastic crate (keranjang), a small tin box for betel nut, and a discarded worn-out batik sarong. "
                "Focus on the crystalline reflections and the heavy, grimy dust layers."
            ),
            "Rongsok Elektronik & Kabel (E-Waste)": (
                "Sitting cross-legged on a pile of old circuit boards and broken plastic casings of vintage televisions. "
                "The background is a rimbun mountain of discarded electronic parts, tangled multi-colored wires, and shattered CRT glass. "
                "Texture details: green fiberglass PCBs, dusty copper coils, brittle aged plastic, and metallic solder points. "
                "Next to her: a pair of pliers, a small prayer beads (tasbih) string, and a glass of tea with a metal lid. "
                "Focus on the complex, technological decay and the grimy industrial textures."
            ),
            "Tumpukan Ban Bekas & Karet": (
                "Sitting cross-legged on the inner circle of a large, weathered truck tire. "
                "The background is a solid wall of stacked black rubber tires with worn-out treads and dried mud in the grooves. "
                "Texture details: matte black rubber, deep tread patterns, dry white powder on the surface, and cracked sidewalls. "
                "Next to her: a traditional broom (sapu lidi), a small bottle of eucalyptus oil, and a wandering village chicken. "
                "Focus on the heavy, dark, and industrial rubber textures."
            ),
            "Gudang Garam & Karung Goni": (
                "Sitting cross-legged on a floor covered in thick, coarse white salt crystals. "
                "The background is a solid wall of stacked, heavy burlap sacks (karung goni) with visible fibers and salt stains. "
                "Texture details: crystalline salt grains, rough fibrous burlap, and damp wooden pillars with white mineral crust. "
                "Next to her: a wooden salt shovel, a small plastic bucket, and a glass of tea with a metal lid. "
                "Focus on the white crystalline textures and the rough, brownish burlap."
            ),
            "Pabrik Genteng & Tumpukan Tanah Liat": (
                "Sitting cross-legged on a patch of fine, dry orange clay dust. "
                "The background is a rimbun wall of thousands of unbaked, matte-orange clay tiles (genteng) stacked in neat but dusty rows. "
                "Texture details: smooth but gritty clay surfaces, powdery orange dust, and rough wooden drying racks. "
                "Next to her: a traditional 'caping' hat, a small clay water jug, and a pair of old rubber sandals. "
                "Focus on the monochromatic orange tones and the dry, earthy textures."
            ),
            "Bengkel Kapal & Kayu Kapal Lapuk": (
                "Sitting cross-legged on a bed of dry wood shavings (tatal) and sawdust. "
                "The background is the massive, curved hull of an old wooden boat with peeling blue and white paint and thick barnacle crusts. "
                "Texture details: flaking paint, sharp salt-encrusted barnacles, and deep cracks in the aged timber. "
                "Next to her: a rusted iron anchor, a coil of thick frayed nautical rope, and a tin of betel nut. "
                "Focus on the industrial maritime decay and the rough, weathered wood."
            ),
            "Penggilingan Padi & Tumpukan Sekam": (
                "Sitting cross-legged on a vast mound of dry, golden-yellow rice husks (sekam). "
                "The background is a solid wall of old, rusted milling machinery with oily gears and thick layers of grain dust. "
                "Texture details: sharp paper-like husks, greasy metallic surfaces, and fine yellow dust covering everything. "
                "Next to her: a woven plastic sack, a small analog radio, and a string of wooden prayer beads. "
                "Focus on the overwhelming golden grain textures and the rusted industrial machinery."
            ),
            "Pasar Tradisional Bubrah (After Hours)": (
                "Sitting cross-legged on a wet, stained cement floor covered in discarded vegetable leaves and crushed fruit. "
                "The background is a rimbun mess of empty wooden crates (peti kayu), torn plastic tarps, and abandoned bamboo baskets. "
                "Texture details: slimy organic waste, rough splintered wood, and damp concrete stains. "
                "Next to her: a glass jar of crackers, a traditional broom (sapu lidi), and a wandering village chicken. "
                "Focus on the chaotic organic clutter and the gritty, damp market textures."
            ),
            "Reruntuhan Beton & Besi Rebar": (
                "Sitting cross-legged on a pile of broken concrete slabs and grey cement dust. "
                "The background is a solid wall of a collapsed building with exposed, twisted rusty iron rebar poking out like skeletons. "
                "Texture details: gritty concrete chunks, oxidized rusty metal, and layers of fine white limestone dust. "
                "Next to her: a dented aluminium teapot, a worn-out prayer rug (sajadah) covered in dust, and a single olive branch. "
                "Focus on the harsh, sharp edges of the rubble and the powdery grey textures."
            ),
            "Gundukan Bata Merah & Abu Bakaran": (
                "Sitting cross-legged on a mound of loose, shattered red bricks and dark grey ash. "
                "The background is the skeleton of a burnt-out house with blackened doorways and charred wooden beams. "
                "Texture details: brittle burnt wood, powdery black soot, and rough broken ceramic tiles. "
                "Next to her: an old kerosene lamp with cracked glass, a small copper tray, and a tattered family photo frame. "
                "Focus on the contrast between the red bricks and the black carbon soot."
            ),
            "Lorong Kota Tua Berdebu (Gaza Style)": (
                "Sitting cross-legged on a narrow stone pathway covered in fine yellow sand and debris. "
                "The background is a rimbun wall of ancient limestone buildings with collapsing balconies and dangling electrical wires. "
                "Texture details: eroded limestone surfaces, tangled copper wires, and dry desert sand accumulation. "
                "Next to her: a traditional woven basket, a small tin box for sewing kits, and a pair of old dusty leather sandals. "
                "Focus on the ancient architectural decay and the gritty, sandy textures."
            ),
            "Bangkai Kendaraan & Tembok Seng": (
                "Sitting cross-legged on a rusted car hood flattened on the ground. "
                "The background is a solid wall of a destroyed warehouse made of riddled corrugated iron (seng) and a burnt-out truck chassis. "
                "Texture details: flaky orange rust, bullet-pierced metal sheets, and greasy soot stains. "
                "Next to her: an empty ammunition crate used as a box, a plastic water jug, and a glass of black tea. "
                "Focus on the heavy metallic oxidation and the industrial ruins."
            ),
            "Halaman Masjid Hancur & Marmer Pecah": (
                "Sitting cross-legged on a shattered white marble floor with visible veins and deep cracks. "
                "The background is a row of damaged stone arches and piles of decorative tiles (zellige) mixed with rubble. "
                "Texture details: smooth but cracked marble, sharp ceramic shards, and thick grey dust. "
                "Next to her: a large old Quran with a torn cover, a small brass incense burner (off), and a rosary. "
                "Focus on the contrast between the elegant marble and the violent destruction."
            ),
            "Pojok Mushola Tua & Sajadah Usang": (
                "Sitting cross-legged on a faded green velvet prayer mat (sajadah) with thinning pile and visible fabric threads. "
                "The background is a solid wall of old, unpainted limestone with thick layers of peeling white chalk (kapur). "
                "Texture details: fuzzy worn-out velvet, chalky paint flakes, and damp stone patches at the bottom. "
                "Next to her: a string of large wooden prayer beads (tasbih), an old ceramic water jug (kendi), and a small wooden book stand (rehal). "
                "Focus on the spiritual silence and the brittle, dry textures of the wall."
            ),
            "Gudang Tenun & Benang Kusut": (
                "Sitting cross-legged on a floor covered in colorful lint, cotton scraps, and loose threads. "
                "The background is a rimbun wall of stacked wooden weaving frames (alat tenun) and hundreds of dusty spools of yarn. "
                "Texture details: fibrous cotton, rough hand-carved wood grain, and layers of fine lint dust. "
                "Next to her: a traditional weaving shuttle (torak), a small tin box for sewing kits, and a glass of warm tea. "
                "Focus on the complex interplay of soft fibers and hard, aged wood."
            ),
            "Lantai Kapal Kayu & Jaring Nelayan": (
                "Sitting cross-legged on a rough wooden deck made of wide, salt-crusted timber planks. "
                "The background is a massive, rimbun pile of tangled green and blue nylon fishing nets with attached lead sinkers. "
                "Texture details: dried salt crystals on wood, coarse nylon mesh, and rusted metal pulleys. "
                "Next to her: a small kerosene lamp (off), a bowl of dried fish, and a traditional 'caping' hat. "
                "Focus on the maritime grit and the complex, knotted textures of the nets."
            ),
            "Pabrik Jamu & Akar Kering": (
                "Sitting cross-legged on a floor covered in yellowish turmeric dust and dried herb particles. "
                "The background is a rimbun wall of hanging dried roots, barks, and baskets of medicinal plants. "
                "Texture details: rough woody roots, powdery herbal dust, and woven bamboo textures. "
                "Next to her: a stone mortar and pestle (lumpang), a small glass bottle of herbal oil, and a plate of traditional snacks. "
                "Focus on the earthy, organic apothecary vibe and the diverse botanical textures."
            ),
            "Gang Sempit & Tembok Lumut": (
                "Sitting cross-legged on a narrow asphalt path with numerous rough patches and potholes. "
                "The background is a solid, towering wall of unpainted bricks and damp cement covered in thick green moss and old graffiti. "
                "Texture details: gritty asphalt, damp velvety moss, and peeling posters on the wall. "
                "Next to her: a row of small potted plants in recycled plastic cans, a puddle of stagnant water, and a pair of old rubber sandals. "
                "Focus on the claustrophobic urban texture and the damp, gritty surfaces."
            ),
            "Depan Rumah (Teras Semen Kasar)": (
                "Sitting cross-legged on a rough grey cement terrace floor with visible sand grains and thin cracks. "
                "The background is a solid wall with faded paint, a simple wooden door with a rusty padlock, and a low-hanging tangled bunch of black electrical wires. "
                "Texture details: chalky wall paint, rough concrete, and the rubbery texture of the cables. "
                "Next to her: a glass jar of crackers (kerupuk), a traditional broom (sapu lidi), and a wandering village chicken. "
                "Focus on the humble, daily residential textures and the messy overhead clutter."
            ),
            "Belakang Rumah & Jemuran Kain": (
                "Sitting cross-legged on a piece of old, flattened cardboard over a dirt and gravel floor. "
                "The background is a rimbun wall of colorful laundry hanging on a simple plastic rope, featuring faded batik sarongs and towels. "
                "Texture details: fibrous cloth, rusty wire fence, and loose dry soil with small pebbles. "
                "Next to her: a plastic laundry basin, a stack of dry firewood, and a small glass of tea with a metal lid. "
                "Focus on the domestic clutter and the contrast between soft fabric and hard gravel."
            ),
            "Samping Rumah (Lorong Drainase)": (
                "Sitting cross-legged on a flat stone beside a narrow open drainage canal (selokan) made of cracked cement. "
                "The background is a solid wall of rough-textured grey stones and overgrown wild weeds. "
                "Texture details: slimy algae inside the canal, porous grey stone, and sharp edges of wild grass. "
                "Next to her: a small bottle of eucalyptus oil, a coil of mosquito incense (off), and an old analog radio. "
                "Focus on the damp, organic decay and the gritty stone textures."
            ),
            "Halaman Depan & Jemuran Gabah": (
                "Sitting cross-legged on a wide woven mat (tikar pandan) placed on a dusty concrete yard. "
                "The background is a simple house front with a corrugated iron roof (seng) and a pile of dry coconut shells. "
                "Texture details: ribbed texture of the mat, thousands of tiny yellow rice grains (gabah) drying in the sun, and rusted metal. "
                "Next to her: a traditional 'caping' hat, a wooden rake, and a plastic bucket of water. "
                "Focus on the agricultural-residential hybrid textures."
            ),
            "Bawah Pohon Depan Gang": (
                "Sitting cross-legged on a large, protruding tree root and dry leaves on the side of the road. "
                "The background is a rustic wooden fence and a stack of old, unused tires covered in dust. "
                "Texture details: rough tree bark, crispy dry leaves, and matte black rubber with deep treads. "
                "Next to her: a small glass of black coffee, an old tin box for betel nut, and a discarded newspaper. "
                "Focus on the dry, dusty roadside atmosphere and the raw organic textures."
            )
            
        }
        # --- 4. MASTER AUDIO & SOULFUL EXPRESSION (FIXED WORKSHOP INTERACTION) ---
        MASTER_AUDIO_STYLE = {
            "Logat": [
                "Natural Village-Authentic: A raw, unpolished voice with a flat, honest intonation. It carries a rhythmic 'broken' cadence, sounding deeply sincere and unpretentious with a texture that is slightly dry and dusty, lacking any urban polish.",
                "Old Javanese Phonetic: Slow and deliberate with a heavy, vibrating 'dh' and 'th' percussion. The tone is deeply humble, featuring a low-register chest voice that sounds like a calm, rhythmic hum.",
                "Soft Sundanese Lilt: A melodic, undulating rhythm (mendayu) with a gentle rising and falling pitch. The voice is airy and breathy, characterized by a smooth, high-frequency flow with no harsh edges.",
                "Coastal Melayu Cadence: Quick-paced and rhythmic with a dry, gravelly texture. The intonation is punchy and direct, sounding like a weathered voice shaped by salt air and open spaces.",
                "Village-Common 'Kering' Voice: A thin, cracked, and slightly shaky (gemetar) voice. It carries the texture of a dry throat, with high-register raspiness and frequent breathy pauses between phrases.",
                "The Serene Matriarch: Extremely slow tempo, almost a whisper. The voice is calm, stable, and deeply reverent, with soft guttural friction in the throat that suggests a lifetime of silent prayer."
            ],
            "Mood": [
                "Sedih & Sayu (Quiet Vulnerability - Steady gaze, eyes heavy with deep emotion)",
                "Tenang & Bengong (Pensive Stillness - Calm facial expression, long natural pauses)",
                "Damai Sejahtera (Graceful Serenity - Serene and peaceful look, slow breathing)",
                "Tulus Ikhlas (Humble Devotion - Gentle and sincere facial expression)",
                "Tegar & Bijak (Stoic Calmness - A steady, wise face reflecting years of memories)",
                "Fokus Khusyuk (Sacred Focus - Deeply focused expression, absolute sincerity)",
                "Penuh Harapan (Peaceful Hope - A calm, hopeful look in the eyes)"
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
            
            # 2. KUNCI KETAJAMAN & CLEAN STATIC VISUAL (MENDUNG NATURAL)
            scene_context = (
                f"ULTRA-HD 8K RESOLUTION. HYPER-REALISTIC RAW PHOTO. "
                f"MANDATORY: NO TEXT, NO SUBTITLES, NO CAPTIONS. "
                # --- UPDATE LIGHTING: MENDUNG SORE NATURAL ---
                f"LIGHTING: 4 PM late afternoon with a soft dark-grey overcast sky, subtle thin cloud layers, no harsh sun. "
                f"CONTRAST: Intense glowing LED light contrast against dark cloudy sky, making the colors pop intensely. " # <-- Kalimat sakti lo!
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
                
            # 5. FINAL ASSEMBLY (FIXED: STATIC, SHARP, & MOODY NATURAL)
            final_ai_prompt = (
                f"{scene_context} \n\n"
                f"CHARACTER DNA: {soul_desc}. {ANATOMY_LOCK} {MANDATORY_LOCK} \n"
                f"WARDROBE: {baju_desc}. \n"
                f"ENVIRONMENT: {env_detail}. \n"
                f"PERFORMANCE: {aksi_final}. Mood: {mood_final}. \n" 
                f"THE MASTERPIECE: {deskripsi_teknis}. \n"
                f"DIALOG CONTEXT: '{user_dialog}' delivered with {logat_final} accent. \n\n"
                # --- TECHNICAL: KUNCI STATIS, TAJAM, & ANTI-BADAII ---
                f"TECHNICAL SPECS: Shot on ARRI Alexa 65, 24mm lens, F/16 Aperture, Deep Focus. "
                f"CAMERA LOGIC: Strictly STATIC camera, zero movement, perfectly level 0-degree eye-level angle. " 
                f"VISUAL: Ultra-sharp 8K, high-contrast colors, zero motion blur, global shutter. "
                # --- NEGATIVE PROMPT: BUANG SEMUA SAMPAH VISUAL ---
                f"NEGATIVE PROMPT: thunderstorm, heavy black clouds, storm, rain, " # <-- Anti kiamat
                f"blurry, bokeh, depth of field, out of focus, shaky, motion blur, " 
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
                                                    sudah_ada = id_tugas in df_selesai['ID'].values
                                                    if not sudah_ada:
                                                        jml_video = len(df_selesai) + 1
                                                    else:
                                                        jml_video = len(df_selesai)

                                                    # 4. LOGIKA BONUS & ARUS KAS
                                                    msg_bonus = ""
                                                    tgl_fix = str(tgl_tugas)
                                                    if jml_video == 3 or jml_video >= 5:
                                                        nom_bonus = 30000
                                                        tipe_bonus = "Absen" if jml_video == 3 else "Video"
                                                        ket_bonus = f"Bonus {tipe_bonus} ke-{jml_video}: {staf_nama} ({id_tugas})"
                                                        
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
                                                        
                                                        msg_bonus = f"\n💰 *BONUS {tipe_bonus.upper()}:* Rp 30,000 (Video ke-{jml_video})"
                                                        st.toast(f"Bonus {tipe_bonus} {staf_nama} dicatat!", icon="💸")

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
    - Libur Hari Raya Idul Fitri Mulai Tanggal 19 - 24 maret (Tanggal 25 masuk normal).
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
            selisih_vital = total_st - (total_pr + 10)
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
                                            if h in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,]:
                                                max_slot = 3
                                            else:
                                                max_slot = 4
                                            
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
            st.markdown("#### 🚀 MONITORING PROSES (MAX 3 SLOT HP)")
            # --- TAMBAHAN: ST INFO UNTUK INSTRUKSI STAFF ---
            st.info("""
                💡 **PENGINGAT KHUSUS:**
                1. HP 1-10 Konten Sakura
                2. HP 11-23 Konten Masjid
                3. HP 1-10 isi 3 channel, HP 11-23 isi 4 channel (login hapus dan stock video disesuaikan)
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
            list_hp_tim1 = [h for h in df_display['HP'].unique() if pd.to_numeric(h, errors='coerce') <= 11]
            list_hp_tim2 = [h for h in df_display['HP'].unique() if pd.to_numeric(h, errors='coerce') > 11]
            
            # Gabungkan jadi satu list besar tapi kita kasih pembatas (marker)
            # Ini biar kodenya mirip struktur awal lo yang pake loop
            kelompok_tim = [
                {"nama": "ICHA / NISSA (HP 1-11)", "list": list_hp_tim1},
                {"nama": "LISA (HP 12-23)", "list": list_hp_tim2}
            ]

            html_all_pages = "" 

            for tim in kelompok_tim:
                list_hp_unik = tim["list"]
                if not list_hp_unik: continue
                
                # Loop per 11 HP (sama kayak kode awal lo)
                for start_idx in range(0, len(list_hp_unik), 6):
                    hp_halaman_ini = list_hp_unik[start_idx : start_idx + 6]
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
                        font-size: 12px;
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
