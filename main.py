
# requirements.txt dosyasında şunlar olmalı: ccxt pandas pandas_ta requests asyncio websockets
import ccxt
import pandas as pd
import pandas_ta as ta
import asyncio
import requests
import time
from datetime import datetime
import warnings


warnings.filterwarnings('ignore')

# =====================================================================
# 🌍 RENDER OUTBOUND IP ÖĞRENME (BtcTurk API İçin)
# =====================================================================
try:
    dis_ip = requests.get('https://api.ipify.org', timeout=5).text
    print(f"{"="*50}")
    print(f"🌍 [RENDER OUTBOUND IP ADRESİ]: {dis_ip}")
    print(f"Lütfen bu IP adresini BtcTurk API 'IP Kısıtlaması' alanına yazın.")
    print(f"{"="*50}\n")
except Exception as e:
    print(f"IP adresi alınamadı: {e}\n")

# =====================================================================
# 🔑 BTCTURK API BAĞLANTISI VE KASA YÖNETİMİ
# =====================================================================
API_KEY = "739a0a8f-f773-42c8-8eed-53c923ca1ec0"       # BtcTurk API Anahtarın
API_SECRET = "pURBqy4SQmajG/Qs1ch06Yrm+RS9JLhe" # BtcTurk Gizli Anahtarın

CANLI_ISLEM_AKTIF = True
MAX_AKTIF_ISLEM = 1
BAKIYE_KULLANIM_ORANI = 0.95

# ⚡ ASENKRON BORSA NESNESİ (ccxt.pro)
borsa = ccxt.btcturk({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
})

# =====================================================================
# 🧮 SABİTLER VE LİSTELER
# =====================================================================
def hassas(fiyat):
    if fiyat >= 100: return f"₺{fiyat:.2f}"
    elif fiyat >= 1: return f"₺{fiyat:.4f}"
    elif fiyat >= 0.01: return f"₺{fiyat:.6f}"
    else: return f"₺{fiyat:.8f}"

coin_listesi = [  "BTC", "ETH", "XRP", "LTC", "XLM", "NEO", "EOS", "DASH", "LINK",
    "ATOM", "XTZ", "TRX", "ADA", "DOT", "USDC", "UNI", "ANKR", "ENJ", "OMG",
    "COMP", "GRT", "MANA", "SNX", "BAT", "AVAX", "FIL", "DOGE", "CHZ", "SOL",
    "STX", "AXS", "SHIB", "LRC", "UMA", "FET", "STORJ", "AAVE", "GALA", "SAND",
    "AMP", "AUDIO", "SPELL", "ALGO", "APE", "BNT", "CRV", "QNT", "SKL", "GLM",
    "LUNA", "PAXG", "ENS", "IMX", "LPT", "CVC", "RLC", "ETC", "ETHW", "HOT",
    "APT", "FLOW", "CTSI", "XCN", "MASK", "API3", "BAND", "FLR", "T", "ARB",
    "BLUR", "INJ", "OGN", "RAD", "ARPA", "LDO", "SUSHI", "MAGIC", "ACM", "PSG",
    "CITY", "ERA", "JUV", "ATM", "GAL", "TRA", "AFC", "ASR", "NAP", "INTER",
    "JASMY", "ZRX", "PEPE", "NMR", "FLOKI", "STRK", "SUPER", "BONK", "JUP",
    "PYTH", "AIOZ", "WIF", "NEAR", "FB", "TON", "TIA", "KSM", "HBAR", "ARKM",
    "AXL", "RENDER", "OP", "MNT", "KAVA", "GLMR", "WLD", "RUNE", "RARE", "ZRO",
    "ONDO", "ZK", "HNT", "GMT", "POL", "EIGEN", "W", "PNUT", "ETHFI", "ENA",
    "MOVE", "ME", "VANA", "MEME", "TRUMP", "MELANIA", "ANIME", "S", "PENGU",
    "IO", "JTO", "KAITO", "AIXBT", "VIRTUAL", "TURBO", "LAYER", "WCT", "ATH",
    "RAY", "BEAMX", "MORPHO", "PUMP", "ERA", "FIDA", "SPK", "XAUT", "WLFI", "BIO",
    "ZKC", "LINEA", "XPL", "MIRA", "2Z", "AVNT", "SEI", "SUI", "SKY", "0G",
    "ZORA", "MET", "MON", "KITE", "SAHARA", "AERO", "H", "SENT", "MANTRA", "BARD","SKL","AUDIO",
    "ALLO", "VVV", "HYPE", "RED", "TRB", "ORCA", "CFG","ERA","AIOZ","GRASS","PHA","WAL","BILL"
 
]

aktif_pozisyonlar = {}
son_islem_zamani = {}
guncel_kur = 49.900

# =====================================================================
# 🦅 KESKİN NİŞANCI ANALİZ MOTORU (Senkron / Hızlı Hesaplama)
# =====================================================================
async def coin_analiz_et(sembol, guncel_fiyat):
    global aktif_pozisyonlar
    try:
        aktif_sayisi = sum(1 for k, v in aktif_pozisyonlar.items() if v['Durum'] == 'AKTIF')

        # 1. STOP-LOSS VE TRAILING STOP KONTROLÜ
        if sembol in aktif_pozisyonlar and aktif_pozisyonlar[sembol]['Durum'] == 'AKTIF':
            poz = aktif_pozisyonlar[sembol]

            if guncel_fiyat <= poz['Mevcut_Stop']:
                kar_zarar = ((poz['Mevcut_Stop'] - poz['Maliyet']) / poz['Maliyet']) * 100
                mesaj = f"💰 KÂR ALINDI (+%{kar_zarar:.2f})" if kar_zarar > 0 else f"🛡️ ZARAR KESİLDİ (%{kar_zarar:.2f})"
                print(f"\n🚨 [SATIŞ TETİKLENDİ] -> {sembol:<5} | Fiyat: {hassas(guncel_fiyat)} | {mesaj}")

                if CANLI_ISLEM_AKTIF:
                    try:
                        bakiye = await borsa.fetch_balance()
                        miktar = bakiye['free'].get(sembol, 0)
                        if miktar > 0:
                            emir = await borsa.create_market_sell_order(f"{sembol}/TRY", miktar)
                            print(f"   💸 CANLI SATIŞ BAŞARILI! (Emir ID: {emir['id']})")
                    except Exception as e:
                        print(f"   ❌ Satış Hatası: {e}")

                poz['Durum'] = 'KAPANDI'
                return

            elif guncel_fiyat > poz['Max_Fiyat']:
                poz['Max_Fiyat'] = guncel_fiyat
                anlik_kar = ((guncel_fiyat - poz['Maliyet']) / poz['Maliyet']) * 100
                if anlik_kar >= 3.0:
                    yeni_stop = guncel_fiyat * 0.985
                    if yeni_stop > poz['Mevcut_Stop']:
                        poz['Mevcut_Stop'] = yeni_stop
                        print(f"📈 [TRAILING YÜKSELTİLDİ] -> {sembol:<5} | Stop: {hassas(yeni_stop)} | Kâr: +%{anlik_kar:.2f}")
            return

        # 2. YENİ FIRSAT TARAMASI
        if aktif_sayisi >= MAX_AKTIF_ISLEM:
            return

        su_an_ms = int(time.time() * 1000)
        if sembol in son_islem_zamani and (su_an_ms - son_islem_zamani[sembol]) < 15000:
            return
        son_islem_zamani[sembol] = su_an_ms

        mumlar = await borsa.fetch_ohlcv(f"{sembol}/TRY", timeframe='15m', limit=150)
        if len(mumlar) < 50: return
        df = pd.DataFrame(mumlar, columns=['Zaman', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df.at[df.index[-1], 'Close'] = guncel_fiyat

        # 🎯 İNDİKATÖRLER (YENİ: EMA 9 VE 21 EKLENDİ)
        df.ta.ema(length=9, append=True)
        df.ta.ema(length=21, append=True)
        df.ta.ema(length=144, append=True)

        df['Price_Change'] = df['Close'].diff()
        df['VAPI_Raw'] = df['Price_Change'] * df['Volume']
        df['VAPI_Osc'] = df['VAPI_Raw'].rolling(window=10).mean()
        df['VOL_SMA_10'] = df['Volume'].rolling(window=10).mean()
        df['VWAP'] = ((df['High'] + df['Low'] + df['Close']) / 3 * df['Volume']).cumsum() / df['Volume'].cumsum()

        msb_destek = df['Low'].shift(1).rolling(window=15).min().iloc[-1]
        mtf_destek = df['Low'].shift(1).rolling(window=60).min().iloc[-1]

        vwap_fiyat = df['VWAP'].iloc[-1]
        vol_sma = df['VOL_SMA_10'].iloc[-1]
        hacim_x = df['Volume'].iloc[-1] / vol_sma if vol_sma > 0 else 1.0

        # Trend ve Momentum Onayları
        boga_trend = guncel_fiyat > (df['EMA_144'].iloc[-1] if 'EMA_144' in df.columns else 0)
        ema_9 = df['EMA_9'].iloc[-1] if 'EMA_9' in df.columns else 0
        ema_21 = df['EMA_21'].iloc[-1] if 'EMA_21' in df.columns else 0
        ema_al_onayi = ema_9 > ema_21  # YENİ: Kısa vadeli momentum onayı (9, 21'in üzerinde olmalı)

        yesil_mum = guncel_fiyat > df['Open'].iloc[-1]
        vapi_onay = (df['VAPI_Osc'].iloc[-1] > 0) and (df['VAPI_Osc'].iloc[-1] > df['VAPI_Osc'].iloc[-2])
        gercek_yukselis = (guncel_fiyat > vwap_fiyat)
        sert_satis = (not yesil_mum) and (hacim_x >= 2.0)

        yaklasim_mtf = (guncel_fiyat <= mtf_destek * 1.03) and (guncel_fiyat >= mtf_destek * 0.99)
        yaklasim_msb = (guncel_fiyat <= msb_destek * 1.03) and (guncel_fiyat >= msb_destek * 0.99)
        destek_harici = not (yaklasim_mtf or yaklasim_msb)

        # 3. TAHTA DENGESİZLİĞİ
        ob_orani = 1.0
        try:
            ob = await borsa.fetch_order_book(f"{sembol}/TRY", limit=20)
            t_bid = sum([b[1] for b in ob['bids']])
            t_ask = sum([a[1] for a in ob['asks']])
            if t_ask > 0: ob_orani = t_bid / t_ask
        except: pass

        stop_fiyat = guncel_fiyat * 0.99

        # 🎯 SİNYAL KARAR MEKANİZMASI (EMA Onaylı)
        sinyal_var = False
        tip = ""

        if boga_trend and yesil_mum and gercek_yukselis and vapi_onay and (not sert_satis):
            # YENİ: Destek kalkışı için artık EMA_9 > EMA_21 şartı aranıyor
            if (yaklasim_mtf or yaklasim_msb) and ema_al_onayi and (hacim_x >= 1.8) and (ob_orani >= 2.0):
                sinyal_var, tip = True, "🎯 MTF DESTEK KALKIŞI (EMA Onaylı)"
            elif destek_harici and ema_al_onayi and (hacim_x >= 3.0) and (ob_orani >= 3.0):
                sinyal_var, tip = True, "🚀 VAHŞİ KOPUŞ (EMA Onaylı)"

        if sinyal_var:
            if sembol not in aktif_pozisyonlar or aktif_pozisyonlar[sembol]['Durum'] == 'KAPANDI':
                print(f"\n{tip[:2]} [{tip}!] -> {sembol:<5} | Canlı: {hassas(guncel_fiyat)} | Hacim: {hacim_x:.1f}x | Tahta: {ob_orani:.1f}x Alıcı")

                if CANLI_ISLEM_AKTIF:
                    try:
                        bakiye = await borsa.fetch_balance()
                        tl_bakiye = bakiye['free'].get('TRY', 0)
                        islem_tl = tl_bakiye * BAKIYE_KULLANIM_ORANI
                        miktar = islem_tl / guncel_fiyat

                        if islem_tl > 50:
                            emir = await borsa.create_market_buy_order(f"{sembol}/TRY", miktar)
                            print(f"   💰 CANLI ALIM: ₺{islem_tl:.2f} ile {sembol} alındı! (ID: {emir['id']})")
                            aktif_pozisyonlar[sembol] = {'Maliyet': guncel_fiyat, 'Mevcut_Stop': stop_fiyat, 'Max_Fiyat': guncel_fiyat, 'Durum': 'AKTIF'}
                        else:
                            print(f"   ⚠️ Yetersiz TL! (Bakiye: ₺{tl_bakiye:.2f})")
                    except Exception as e:
                        print(f"   ❌ Alım Hatası: {e}")
                else:
                    print(f"   🤖 SANAL ALIM YAPILDI! (İz Süren Stop: {hassas(stop_fiyat)})")
                    aktif_pozisyonlar[sembol] = {'Maliyet': guncel_fiyat, 'Mevcut_Stop': stop_fiyat, 'Max_Fiyat': guncel_fiyat, 'Durum': 'AKTIF'}

    except Exception as e:
        pass

# =====================================================================
# ⚡ WEBSOCKET DİNLEME (WATCH TICKER) AKIŞI
# =====================================================================
async def ana_dinleyici_dongu():
    global guncel_kur
    print("🦅 Asenkron WebSocket Bot (Keskin Nişancı) Başlatıldı...")
    print(f"🤖 Canlı İşlem: {'🟢 AKTİF' if CANLI_ISLEM_AKTIF else '🟡 SANAL'}\n")

    dinlenecek_semboller = [f"{c}/TRY" for c in coin_listesi]

    while True:
        try:
            try:
                usdt_ticker = await borsa.fetch_ticker("USDT/TRY")
                guncel_kur = usdt_ticker['last']
            except: pass

         
            aktif_sayisi = sum(1 for k, v in aktif_pozisyonlar.items() if v['Durum'] == 'AKTIF')
            print(f"⚡ [Asenkron WebSocket Aktif] - Piyasayı Anlık Dinliyor... | Slot: [{aktif_sayisi}/{MAX_AKTIF_ISLEM}]")

            if aktif_sayisi > 0:
                print("─"*50)
                for c, poz in aktif_pozisyonlar.items():
                    if poz['Durum'] == 'AKTIF':
                        pnl = ((poz['Max_Fiyat'] - poz['Maliyet']) / poz['Maliyet']) * 100
                        print(f"💼 Aktif: {c} | Maliyet: {hassas(poz['Maliyet'])} | Stop: {hassas(poz['Mevcut_Stop'])}")
                print("─"*50)
            else:
                print("🔍 Bot pusuda, destek sekmesi ve hacim patlaması bekliyor...")

            tickers = await borsa.watch_tickers(dinlenecek_semboller)

            for sembol_try, veri in tickers.items():
                saf_sembol = sembol_try.split('/')[0]
                canli_fiyat = veri['last']

                asyncio.create_task(coin_analiz_et(saf_sembol, canli_fiyat))

        except ccxt.NetworkError:
            print("⚠️ İnternet veya borsa bağlantısı koptu. 5 saniye sonra yeniden bağlanılıyor...")
            await asyncio.sleep(5)
        except Exception as e:
            await asyncio.sleep(1)

# =====================================================================
# 🚀 BOTU ATEŞLE
# =====================================================================
try:
    loop = asyncio.get_running_loop()
    loop.create_task(ana_dinleyici_dongu())
except RuntimeError:
    asyncio.run(ana_dinleyici_dongu())
