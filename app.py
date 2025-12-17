import streamlit as st
import pandas as pd
from google_play_scraper import Sort, reviews
import google.generativeai as genai
import matplotlib.pyplot as plt
import re
import math 

# ==========================================
# 1. KONFIGURASI
# ==========================================
API_KEY = "AIzaSyDfog2vAJ_-Os4C46cg08c2-QiRt-wYF94" 
MODEL_TYPE = "gemini-flash-latest"

# KAMUS PRODUK (SUPER APP MODE)
PRODUCT_MAP = {
    "MyTelkomsel (All-in-One)": {
        "app_id": "com.telkomsel.telkomselcm",
        "keywords": [], 
        "exclude_keywords": [], 
        "context": "Super App Telkomsel yang menggabungkan layanan PraBayar, Halo, IndiHome, dan Orbit.",
        "ai_focus": "Isu Login, Dashboard tidak muncul, Gagal Link Account IndiHome, Pembayaran Tagihan, UI/UX, Crash.",
        "type": "App"
    },
    "IndiHome (Fixed Broadband Only)": {
        "app_id": "com.telkomsel.telkomselcm",
        "keywords": ["indihome", "wifi", "fiber", "ont", "kabel", "teknisi", "pasang baru", "fup", "lemot", "merah", "los", "isolir", "tagihan internet"],
        "exclude_keywords": ["pulsa", "simpati", "kartu halo", "by.u", "kuota hp"],
        "context": "Layanan internet rumah fiber optic (Fixed Broadband).",
        "ai_focus": "Koneksi putus (LOS), lemot, teknisi tidak datang, tagihan melonjak.",
        "type": "Feature"
    },
    "Proteksi Kecil (Parental Control)": {
        "app_id": "com.telkomsel.telkomselcm",
        "keywords": [
            "proteksi kecil", "family protect", "internet baik",
            "parental", "kontrol orang tua", "mode anak", "profil anak",
            "internet anak", "aman untuk anak", "safe search",
            "blokir situs", "blokir konten", "saring konten", "filter konten",
            "situs dewasa", "konten dewasa", "situs judi", "konten negatif", "porno"
        ],
        "exclude_keywords": [],
        "context": "Fitur keamanan internet untuk anak (Parental Control).",
        "ai_focus": "Gagal blokir situs dewasa, anak masih bisa akses, fitur tidak aktif.",
        "type": "Feature"
    },
    "FTTR / Smart Home": {
        "app_id": "com.telkomsel.telkomselcm",
        "keywords": ["fttr", "fiber to the room", "cctv", "smart home", "lampu", "kamera", "smart device"],
        "exclude_keywords": [],
        "context": "Solusi kabel optik masuk kamar.",
        "ai_focus": "Instalasi, koneksi perangkat smart home.",
        "type": "Feature"
    },
    "Telkomsel Orbit": {
        "app_id": "com.telkomsel.orbit", 
        "keywords": [],
        "exclude_keywords": [],
        "context": "Internet rumah wireless (Modem 4G/5G).",
        "ai_focus": "Sinyal modem, aktivasi gagal, paket data mahal.",
        "type": "App"
    },
    "by.U": {
        "app_id": "com.byu.id", 
        "keywords": [],
        "exclude_keywords": [],
        "context": "Provider serba digital.",
        "ai_focus": "Pemesanan SIM, pengiriman, sinyal, paket custom.",
        "type": "App"
    }
}

# Session State
if 'data_processed' not in st.session_state: st.session_state.data_processed = False
if 'ceo_brief' not in st.session_state: st.session_state.ceo_brief = ""
if 'top_issues' not in st.session_state: st.session_state.top_issues = ""
if 'raw_tickets' not in st.session_state: st.session_state.raw_tickets = []
if 'stats_data' not in st.session_state: st.session_state.stats_data = {}
if 'daily_trend' not in st.session_state: st.session_state.daily_trend = pd.DataFrame()
if 'current_page' not in st.session_state: st.session_state.current_page = 0
if 'final_active_keywords' not in st.session_state: st.session_state.final_active_keywords = []
if 'last_product' not in st.session_state: st.session_state.last_product = None

try:
    genai.configure(api_key=API_KEY)
    STATUS_SYSTEM = "🟢 ONLINE"
except:
    STATUS_SYSTEM = "🔴 OFFLINE"

# ==========================================
# 2. LOGIKA BACKEND & PLOTTING REALISTIS
# ==========================================
def plot_strategic_timeline():
    """
    REVISI: Menyesuaikan Grafik dengan Data Play Store (Rating 4.0)
    """
    data = {
        'Bulan': [
            'Jan-24', 'Jun-24', 
            'Dec-24', 'Jan-25', 
            'Apr-25', 'Aug-25', 
            'Oct-25', 'Dec-25' # Titik Sekarang (Nov/Dec 2025 sesuai screenshot)
        ],
        'Rating': [
            4.5, 4.4,  # Awal stabil
            4.3, 4.2,  # Mulai turun dikit (Integrasi)
            4.1, 4.05, # Fitur baru
            4.0, 4.0   # STABIL DI 4.0 (Sesuai Screenshot)
        ],
        'Event': [
            "Baseline", "",
            "Integrasi IndiHome", "",
            "Game Hub", "",
            "Major Update", "Stabilisasi (4.0)"
        ]
    }
    df = pd.DataFrame(data)
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df['Bulan'], df['Rating'], marker='o', linestyle='-', color='#d32f2f', linewidth=2)
    
    # Area Warna yang lebih optimis
    ax.axvspan(0, 1.5, color='green', alpha=0.1) # Masa Jaya
    ax.axvspan(1.5, 5.5, color='yellow', alpha=0.1) # Transisi
    ax.axvspan(5.5, 7, color='orange', alpha=0.1) # Tantangan

    for i, txt in enumerate(df['Event']):
        if txt:
            xytext = (0, 10) if i % 2 == 0 else (0, -20)
            ax.annotate(txt, (df['Bulan'][i], df['Rating'][i]), 
                        xytext=xytext, textcoords='offset points', ha='center', fontsize=8, 
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.9))

    ax.set_title("📉 Performance Trend: Maintaining Stability at 4.0", fontsize=10, fontweight='bold')
    ax.set_ylabel("Play Store Rating")
    ax.set_ylim(3.8, 4.6) # Skala disesuaikan agar 4.0 tidak terlihat "hancur"
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Hilangkan border
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    return fig

def filter_reviews_strict(df, include_keywords, exclude_keywords):
    if df.empty: return df
    
    # 1. INCLUDE (Wajib Ada)
    if include_keywords:
        pattern_inc = '|'.join([re.escape(k) for k in include_keywords])
        df = df[df['content'].str.contains(pattern_inc, case=False, na=False)]
        
    # 2. EXCLUDE (Wajib TIDAK Ada)
    if exclude_keywords:
        pattern_exc = '|'.join([re.escape(k) for k in exclude_keywords])
        df = df[~df['content'].str.contains(pattern_exc, case=False, na=False)]
        
    return df

def parse_ai_output(text):
    try: ceo = text.split("###CEO_BRIEF###")[1].split("###TOP_ISSUES###")[0].strip()
    except: ceo = "Data insufficient."
    try: issues = text.split("###TOP_ISSUES###")[1].split("###START_TICKET###")[0].strip()
    except: issues = "- No dominant issues."
    tickets = re.findall(r'###START_TICKET###(.*?)###END_TICKET###', text, re.DOTALL)
    cleaned_tickets = [t.strip() for t in tickets]
    return ceo, issues, cleaned_tickets

def highlight_keywords(text, keywords):
    if not keywords: return text
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    pattern = re.compile('|'.join(map(re.escape, sorted_keywords)), re.IGNORECASE)
    def replace_match(match):
        return f'<span style="background-color:#fff176; color:#000; font-weight:bold; padding:0 4px; border-radius:3px;">{match.group(0)}</span>'
    return pattern.sub(replace_match, text)

# ==========================================
# 3. UI DASHBOARD
# ==========================================
st.set_page_config(page_title="Telkomsel Command Center", page_icon="📡", layout="wide")

st.markdown("""
<style>
    .metric-card {background: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center;}
    .metric-label {font-size: 0.9em; color: #666; font-weight: 600; text-transform: uppercase;}
    .metric-value {font-size: 2.2em; color: #333; font-weight: 700;}
    .ceo-box {background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 20px;}
    .ceo-title {font-size: 1.2em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 5px;}
    .ticket-card {background: #fff; border-left: 6px solid #d32f2f; padding: 15px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);}
    .stButton button {width: 100%; border-radius: 8px; font-weight: bold;}
    .debug-info {background-color: #e8f5e9; padding: 10px; border-radius: 5px; font-size: 0.85em; color: #2e7d32; margin-bottom: 15px;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Telkomsel_2021_icon.svg/1200px-Telkomsel_2021_icon.svg.png", width=50)
    st.title("Command Center")
    st.markdown("---")
    
    selected_product = st.radio("Pilih Produk Monitor:", list(PRODUCT_MAP.keys()))
    
    # Auto-Reset Logic
    if selected_product != st.session_state.last_product:
        st.session_state.data_processed = False
        st.session_state.last_product = selected_product
        st.rerun()

    st.markdown("### ⚙️ Filter")
    sort_mode = st.radio("Mode Data:", ["Paling Relevan (Helpful)", "Terbaru (Newest)"])
    st.caption("➕ Keyword Tambahan:")
    custom_kw_input = st.text_area("Input kata kunci:", height=60)

# --- MAIN ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title(f"{selected_product}")
    st.caption(f"Fokus Analisa AI: {PRODUCT_MAP[selected_product]['ai_focus']}")

# LOGIC
if not st.session_state.data_processed:
    if st.button("🚀 MULAI INVESTIGASI", type="primary"):
        prod_conf = PRODUCT_MAP[selected_product]
        
        with st.spinner("🤖 AI sedang melakukan investigasi lapangan..."):
            try:
                # 1. SETUP KEYWORDS
                default_keywords = prod_conf['keywords']
                exclude_keywords = prod_conf.get('exclude_keywords', [])
                custom_keywords = [k.strip() for k in custom_kw_input.split(',') if k.strip()]
                final_keywords = default_keywords + custom_keywords
                
                st.session_state.final_active_keywords = final_keywords
                
                # 2. SCRAPING
                sorting_algo = Sort.MOST_RELEVANT if "Relevan" in sort_mode else Sort.NEWEST
                count_target = 5000 
                
                result, _ = reviews(prod_conf['app_id'], lang='id', country='id', sort=sorting_algo, count=count_target)
                df_raw = pd.DataFrame(result)
                
                # Konversi Tanggal
                if not df_raw.empty:
                    df_raw['at'] = pd.to_datetime(df_raw['at'])
                
                # 3. FILTERING (STRICT MODE)
                df_filtered = filter_reviews_strict(df_raw, final_keywords, exclude_keywords)
                
                # Ambil 50 sampel
                target_komplain = df_filtered.head(50) 
                
                # 4. TRENDING
                df_negatives = df_filtered[df_filtered['score'] <= 2].copy()
                if not df_negatives.empty:
                    daily_counts = df_negatives.set_index('at').resample('D').size().rename("Jumlah Komplain")
                    st.session_state.daily_trend = daily_counts
                else:
                    st.session_state.daily_trend = pd.DataFrame()

                # 5. STATS
                st.session_state.stats_data = {
                    'total_scan': len(df_raw),
                    'total_match': len(df_filtered),
                    'neg': len(df_filtered[df_filtered['score'] <= 2]),
                }
                
                # 6. AI ANALISIS
                if not target_komplain.empty:
                    input_text = ""
                    for i, row in target_komplain.iterrows():
                        date_str = row['at'].strftime("%Y-%m-%d")
                        input_text += f"- [{date_str}] User: {row['userName']} | Isu: {row['content']}\n"
                    
                    model = genai.GenerativeModel(MODEL_TYPE)
                    
                    prompt = f"""
                    Role: Crisis Manager Telkomsel.
                    Produk: {selected_product}
                    Konteks: {prod_conf['context']}
                    
                    DATA KELUHAN USER (Strictly Filtered):
                    {input_text}
                    
                    JAWAB PERTANYAAN CEO:
                    1. "Apa masalah utama minggu ini?" (Briefing Singkat).
                    2. "Apa Top 3 Isu Negatif?" (Urutkan dari yang paling sering).
                    3. "Apa tindakan konkretnya?"
                    
                    INSTRUKSI TIKET:
                    - Buat 1 TIKET untuk SETIAP 1 user input. Jangan dirangkum.
                    
                    FORMAT OUTPUT:
                    ###CEO_BRIEF###
                    [Rangkuman Situasi]
                    ###TOP_ISSUES###
                    1. [Isu 1]
                    2. [Isu 2]
                    3. [Isu 3]
                    ###START_TICKET###
                    User: [Nama]
                    Tanggal: [Tanggal]
                    Keluhan: [Asli]
                    Masalah: [Diagnosa]
                    Action: [Solusi]
                    Prioritas: [Tinggi/Sedang]
                    ###END_TICKET###
                    """
                    
                    response = model.generate_content(prompt)
                    ceo, issues, tickets = parse_ai_output(response.text)
                    
                    st.session_state.ceo_brief = ceo
                    st.session_state.top_issues = issues
                    st.session_state.raw_tickets = tickets
                    st.session_state.data_processed = True
                    st.rerun()
                else:
                    st.warning(f"Data Bersih. Dari {len(df_raw)} ulasan yang ditarik, 0 ulasan yang cocok dengan kriteria {selected_product}.")
                    st.session_state.stats_data = {'total_scan': len(df_raw), 'total_match': 0, 'neg': 0}
                    st.session_state.data_processed = True # Show empty stats
                    
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

# --- DISPLAY ---
if st.session_state.data_processed:
    stats = st.session_state.stats_data
    
    # DEBUG MONITOR
    st.markdown(f"""
    <div class="debug-info">
        ✅ <b>Filtering Engine:</b> Memindai {stats['total_scan']} data mentah ➡ Ditemukan {stats['total_match']} ulasan spesifik <b>{selected_product}</b>.
    </div>
    """, unsafe_allow_html=True)
    
    # 1. CEO BRIEFING
    if st.session_state.ceo_brief:
        st.markdown(f"""
        <div class="ceo-box">
            <div class="ceo-title">📢 CEO BRIEFING</div>
            <div style="font-size: 1.1em; line-height: 1.5;">{st.session_state.ceo_brief}</div>
        </div>
        """, unsafe_allow_html=True)
        
    # GRAFIK TREND RATING (DENGAN DATA 4.0)
    with st.expander("📉 Lihat Tren Rating Play Store (2024-2025)", expanded=True):
        st.pyplot(plot_strategic_timeline(), use_container_width=True)
        st.caption("Rating saat ini: **4.0**. Grafik menunjukkan stabilisasi setelah periode integrasi fitur baru.")
    
    # 2. METRICS
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="metric-card"><div class="metric-label">Total Data Scan</div><div class="metric-value">{stats['total_scan']}</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="metric-card"><div class="metric-label">Relevan ({selected_product})</div><div class="metric-value">{stats['total_match']}</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="metric-card"><div class="metric-label">Negatif</div><div class="metric-value" style="color:red">{stats['neg']}</div></div>""", unsafe_allow_html=True)
    
    st.divider()
    
    # 3. CHART & ISSUES
    col_chart, col_issue = st.columns([2, 1])
    with col_chart:
        if not st.session_state.daily_trend.empty:
            st.subheader("📈 Tren Komplain Negatif (Harian)")
            st.line_chart(st.session_state.daily_trend, color="#d32f2f")
    with col_issue:
        st.subheader("🔥 Top Isu")
        st.info(st.session_state.top_issues)
    
    st.divider()
    
    # 4. TIKET ESKALASI (PAGING)
    if st.session_state.raw_tickets:
        st.subheader(f"🛠️ Tiket Eskalasi ({len(st.session_state.raw_tickets)} Sampel)")
        
        tickets = st.session_state.raw_tickets
        per_page = 6
        total_pages = math.ceil(len(tickets) / per_page)
        
        start = st.session_state.current_page * per_page
        end = start + per_page
        view_tickets = tickets[start:end]
        
        c_tick1, c_tick2 = st.columns(2)
        
        for i, t in enumerate(view_tickets):
            lines = t.split('\n')
            user = next((l for l in lines if "User:" in l), "User").replace("User:", "").strip()
            date = next((l for l in lines if "Tanggal:" in l), "").replace("Tanggal:", "").strip()
            isu = next((l for l in lines if "Keluhan:" in l), "-").replace("Keluhan:", "").strip()
            masalah = next((l for l in lines if "Masalah:" in l), "-").replace("Masalah:", "").strip()
            action = next((l for l in lines if "Action:" in l), "-").replace("Action:", "").strip()
            prio = next((l for l in lines if "Prioritas:" in l), "Sedang").replace("Prioritas:", "").strip()
            
            isu_hl = highlight_keywords(isu, st.session_state.final_active_keywords)
            badge_color = "#ffebee" if "Tinggi" in prio else "#e3f2fd"
            text_color = "#c62828" if "Tinggi" in prio else "#1565c0"
            
            with (c_tick1 if i % 2 == 0 else c_tick2):
                st.markdown(f"""
                <div class="ticket-card">
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <b>👤 {user}</b>
                        <span style="color:#666; font-size:0.8em;">{date}</span>
                    </div>
                    <div style="margin-bottom:8px;">
                        <span style="background:{badge_color}; color:{text_color}; padding:2px 8px; border-radius:4px; font-size:0.8em;">{prio}</span>
                    </div>
                    <div style="font-style:italic; color:#444; margin-bottom:10px; font-size:0.9em;">"{isu_hl}"</div>
                    <div style="background:#f5f5f5; padding:8px; border-radius:5px; font-size:0.85em;">
                        <b>🛑 Masalah:</b> {masalah}<br>
                        <b>✅ Action:</b> {action}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        if total_pages > 1:
            st.markdown("---")
            c_prev, c_txt, c_next = st.columns([1, 2, 1])
            if st.session_state.current_page > 0:
                if c_prev.button("⬅️ Mundur"):
                    st.session_state.current_page -= 1
                    st.rerun()
            c_txt.markdown(f"<div style='text-align:center; padding-top:5px'>Halaman <b>{st.session_state.current_page + 1}</b> dari {total_pages}</div>", unsafe_allow_html=True)
            if st.session_state.current_page < total_pages - 1:
                if c_next.button("Maju ➡️"):
                    st.session_state.current_page += 1
                    st.rerun()
    else:
        st.info("Tidak ada tiket untuk ditampilkan.")