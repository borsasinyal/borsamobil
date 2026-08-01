"""
Analiz Komutu İşleyicisi
Kullanıcı Telegram'a "analiz THYAO" yazınca çalışır

Komutlar:
  analiz THYAO       → Günlük analiz
  analiz THYAO 4h    → 4 Saatlik analiz
  analiz THYAO 1h    → Saatlik analiz
  /analiz THYAO      → Aynı (slash ile de çalışır)

Her analizde:
- Tam teknik analiz
- Fibonacci hedefleri
- AI yorumu (kural bazlı akıllı öneri)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import re
from datetime import datetime, timezone, timedelta
from telegram import Bot
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BIST_SYMBOLS, TUM_BIST


TR_TIMEZONE = timezone(timedelta(hours=3))
def tr_now(): return datetime.now(TR_TIMEZONE)


def log_event(msg):
    print(f"[{tr_now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


# ════════════════════════════════════════════════════════════
# MESAJ ÇEKME VE İŞLEME
# ════════════════════════════════════════════════════════════

async def get_updates(offset=None):
    """Telegram'dan yeni mesajları al"""
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        updates = await bot.get_updates(offset=offset, timeout=5)
        return updates
    except Exception as e:
        log_event(f"Update alma hatasi: {e}")
        return []


def parse_analiz_command(text):
    """
    Mesaj metnini parse et
    Kabul edilen formatlar:
      - "analiz THYAO"
      - "/analiz THYAO"
      - "Analiz thyao"
      - "analiz THYAO 4h"
      - "analiz THYAO 1h"
      - "/analiz THYAO 4h"
    
    Returns: (symbol, timeframe) veya None
    """
    if not text:
        return None
    
    # Küçük harfe çevir ve boşlukları temizle
    text_lower = text.strip().lower()
    
    # Slash'ı kaldır
    if text_lower.startswith('/'):
        text_lower = text_lower[1:]
    
    # "analiz" ile başlıyor mu?
    if not text_lower.startswith('analiz'):
        return None
    
    # Parçala
    parts = text_lower.split()
    
    if len(parts) < 2:
        return None  # Sadece "analiz" yazılmış, hisse yok
    
    # Hisse sembolü (2. kelime)
    symbol = parts[1].upper()
    
    # Timeframe (3. kelime varsa)
    timeframe = 'daily'  # varsayılan
    if len(parts) >= 3:
        tf_input = parts[2].lower()
        if tf_input in ['4h', '4saat', '4saatlik']:
            timeframe = '4h'
        elif tf_input in ['1h', 'saatlik', 'saat']:
            timeframe = 'hourly'
        elif tf_input in ['gunluk', 'günlük', 'daily', '1d', 'gun']:
            timeframe = 'daily'
    
    return (symbol, timeframe)


def validate_symbol(symbol):
    """Hisse sembolünün BIST listesinde olup olmadığını kontrol et"""
    return symbol in TUM_BIST


# ════════════════════════════════════════════════════════════
# ANALİZ FONKSİYONLARI
# ════════════════════════════════════════════════════════════

def perform_analysis(symbol, timeframe='daily'):
    """
    Hisse analizini yap
    
    Args:
        symbol: BIST sembolü (örn: 'THYAO')
        timeframe: 'daily', '4h', 'hourly'
    
    Returns:
        signal dict veya None
    """
    try:
        from services.analyzer import analyze_stock, analyze_stock_4h, analyze_stock_hourly
        from services.signal_engine import generate_signal
        from database import get_stock_history
        import pandas as pd
        
        full_symbol = f"{symbol}.IS"
        
        if timeframe == '4h':
            log_event(f"4H analizi: {symbol}")
            analysis = analyze_stock_4h(full_symbol)
            if not analysis:
                return None, "4H verisi alinamadi (TradingView bağlantısı yok olabilir)"
            signal = generate_signal(full_symbol, analysis, None)
            
        elif timeframe == 'hourly':
            log_event(f"Saatlik analiz: {symbol}")
            analysis = analyze_stock_hourly(full_symbol)
            if not analysis:
                return None, "Saatlik veri alinamadi (TradingView bağlantısı yok olabilir)"
            signal = generate_signal(full_symbol, analysis, None)
            
        else:  # daily
            log_event(f"Gunluk analiz: {symbol}")
            
            # Önce DB'den dene
            data = get_stock_history(full_symbol, days=300)
            
            # DB'de yoksa Yahoo'dan çek
            if not data or len(data) < 30:
                log_event(f"{symbol} DB'de yok, Yahoo'dan cekiliyor...")
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(full_symbol)
                    hist = ticker.history(period="1y")
                    if len(hist) < 30:
                        return None, "Yeterli veri yok (Yahoo)"
                    
                    data = []
                    for date, row in hist.iterrows():
                        data.append({
                            'date': date.strftime('%Y-%m-%d'),
                            'open': float(row['Open']),
                            'high': float(row['High']),
                            'low': float(row['Low']),
                            'close': float(row['Close']),
                            'volume': int(row['Volume'])
                        })
                except Exception as e:
                    return None, f"Veri cekme hatasi: {str(e)[:100]}"
            
            df = pd.DataFrame(data)
            analysis = analyze_stock(df, timeframe='daily')
            if not analysis:
                return None, "Analiz yapilamadi"
            signal = generate_signal(full_symbol, analysis, df)
        
        if not signal:
            return None, "Sinyal olusturulamadi (skor cok dusuk olabilir)"
        
        # Timeframe bilgisini ekle
        signal['analysis_timeframe'] = timeframe
        return signal, None
        
    except Exception as e:
        log_event(f"Analiz hatasi ({symbol}, {timeframe}): {e}")
        return None, f"Hata: {str(e)[:100]}"


# ════════════════════════════════════════════════════════════
# AI YORUM SİSTEMİ
# ════════════════════════════════════════════════════════════

def generate_ai_comment(signal):
    """
    Sinyale göre kural bazlı akıllı yorum üret
    """
    if not signal:
        return ""
    
    comments = []
    
    # Değişkenler
    score = signal.get('score', 0)
    ind = signal.get('indicators', {})
    rsi = ind.get('rsi', 50)
    rvol = ind.get('rvol', 1)
    macd = ind.get('macd')
    ms = ind.get('macd_signal')
    wt1 = ind.get('wt1')
    wt2 = ind.get('wt2')
    smi = ind.get('smi')
    ss = ind.get('smi_signal')
    adx = ind.get('adx', 0)
    st_dir = ind.get('supertrend_dir')
    
    is_dual = signal.get('is_dual_signal', False)
    is_dual_dip = signal.get('is_dual_dip', False)
    
    kl = signal.get('key_levels', {})
    current_price = signal.get('current_price', 0)
    ema22 = kl.get('ema_22')
    ema50 = kl.get('ema_50')
    ema200 = kl.get('ema_200')
    
    fibonacci = signal.get('fibonacci', {})
    fib_zone = fibonacci.get('current_zone', '')
    is_above_zirve = fibonacci.get('is_above_zirve', False)
    is_below_dip = fibonacci.get('is_below_dip', False)
    
    targets = signal.get('targets', {})
    rr = targets.get('risk_reward', 0)
    
    # ═══════════════════════════════════════
    # GENEL DEĞERLENDİRME
    # ═══════════════════════════════════════
    if score >= 85:
        comments.append("Bu hisse ÇOK GÜÇLÜ bir sinyal veriyor. Tüm göstergeler uyumlu.")
    elif score >= 75:
        comments.append("Güçlü bir AL sinyali var. Sağlıklı bir kurulum.")
    elif score >= 65:
        comments.append("Orta seviyede AL sinyali. Kademeli giriş yapılabilir.")
    elif score >= 50:
        comments.append("Sinyal zayıf, BEKLE modunda kalmak daha güvenli.")
    else:
        comments.append("Bu hissede şu an sinyal YOK, girmenin bir mantığı yok.")
    
    # ═══════════════════════════════════════
    # DUAL SIGNAL (ÖNEMLİ!)
    # ═══════════════════════════════════════
    if is_dual_dip:
        comments.append("💎 GÜÇLÜ DİP DÖNÜŞÜ: WaveTrend ve SMI aynı anda dipte döndü - bu çok nadir ve değerli bir sinyal!")
    elif is_dual:
        comments.append("⭐ ÇİFTLİ ONAY: WT+SMI aynı anda pozitif yönde kesişti - iki bağımsız gösterge onaylıyor.")
    
    # ═══════════════════════════════════════
    # TREND ANALİZİ (EMA)
    # ═══════════════════════════════════════
    if ema22 and ema50 and current_price:
        if current_price > ema22 > ema50:
            if ema200 and ema50 > ema200:
                comments.append("Trend MÜKEMMEL: Fiyat EMA22 > EMA50 > EMA200 sıralamasında. Uzun vade boğa piyasası devam ediyor.")
            else:
                comments.append("Kısa ve orta vade trend YUKARI. Fiyat tüm EMA'ların üstünde.")
        elif current_price > ema50:
            comments.append("EMA50 üstünde tutunuyor, sağlıklı yükseliş sürüyor.")
        elif current_price < ema50 and current_price > ema22:
            comments.append("KARIŞIK durum: EMA22 üstünde ama EMA50 altında. Kırılım bekleniyor.")
        elif current_price < ema22:
            if rsi and rsi < 35 and rvol >= 1.5:
                comments.append("Fiyat EMA22 altında AMA dip dönüşü sinyalleri var (RSI düşük + hacim). Erken giriş fırsatı olabilir.")
            else:
                comments.append("DİKKAT: Fiyat EMA22 altında, trend zayıf. Bekle daha iyi.")
    
    # ═══════════════════════════════════════
    # RSI DEĞERLENDİRMESİ
    # ═══════════════════════════════════════
    if rsi:
        if rsi >= 80:
            comments.append(f"🔴 RSI {rsi:.0f} - Aşırı alım bölgesi. Alacaksan kısa vadeli düşün, düzeltme gelebilir.")
        elif rsi >= 70:
            comments.append(f"⚠️ RSI {rsi:.0f} yüksek. Trend güçlü ama kar alma bölgesine yakın.")
        elif 50 <= rsi <= 65:
            comments.append(f"✅ RSI {rsi:.0f} - İdeal momentum bölgesinde. Ne aşırı yüksek ne düşük.")
        elif 40 <= rsi < 50:
            comments.append(f"RSI {rsi:.0f} - Denge bölgesi. Yön belirlenmemiş.")
        elif rsi < 30:
            comments.append(f"🎯 RSI {rsi:.0f} - Aşırı satım! Dip dönüşü olabilir, hacim onayı ara.")
        elif rsi < 40:
            comments.append(f"RSI {rsi:.0f} düşük - toparlanma başlıyor olabilir.")
    
    # ═══════════════════════════════════════
    # HACİM ANALİZİ
    # ═══════════════════════════════════════
    if rvol:
        if rvol >= 3:
            comments.append(f"💥 HACİM PATLAMASI ({rvol:.1f}x normal) - Kurumsal ilgi kesin var, güçlü hareket bekleniyor.")
        elif rvol >= 2:
            comments.append(f"🔥 Yüksek hacim ({rvol:.1f}x) - Güçlü alış baskısı var.")
        elif rvol >= 1.5:
            comments.append(f"📊 İyi hacim ({rvol:.1f}x) - Ortalamanın üstünde ilgi.")
        elif rvol >= 1.0:
            comments.append(f"Hacim normal seviyede.")
        elif rvol < 0.7:
            comments.append(f"⚠️ Hacim düşük ({rvol:.1f}x) - İlgi zayıf, dikkatli ol.")
    
    # ═══════════════════════════════════════
    # MACD DEĞERLENDİRMESİ
    # ═══════════════════════════════════════
    if macd is not None and ms is not None:
        if macd > ms and macd > 0:
            comments.append("MACD pozitif ve sinyal çizgisi üstünde - momentum güçlü.")
        elif macd > ms:
            comments.append("MACD sinyal çizgisini yukarı kesiyor - yeni momentum başlıyor.")
        elif macd < ms and macd > 0:
            comments.append("MACD sinyal altına indi - momentum zayıflıyor, dikkat.")
        elif macd < 0:
            comments.append("MACD negatif bölgede - trend henüz dönmemiş olabilir.")
    
    # ═══════════════════════════════════════
    # FIBONACCI BÖLGESİ
    # ═══════════════════════════════════════
    if fib_zone:
        if "Altin Oran" in fib_zone:
            comments.append(f"📐 Fibonacci: {fib_zone}. Bu bölge çok güçlü - trader'lar burada tepki bekler.")
        elif "0.5" in fib_zone:
            comments.append(f"📐 Fibonacci: {fib_zone}. Orta bölge, yön belirleyici seviye.")
        elif "dip" in fib_zone.lower():
            comments.append(f"📐 Fibonacci: {fib_zone}. Riskli bölge, sıkı stop koy.")
        elif is_above_zirve:
            comments.append(f"🚀 Fibonacci: Zirve KIRILDI - Extended bölgede. Hedefler 1.272, 1.414, 1.618 seviyeleri.")
    
    # ═══════════════════════════════════════
    # RISK/ÖDÜL
    # ═══════════════════════════════════════
    if rr:
        if rr >= 3:
            comments.append(f"⚖️ R/Ö oranı MÜKEMMEL: 1/{rr} - 1 birim risk için {rr} birim ödül. Matematiksel avantaj yüksek.")
        elif rr >= 2:
            comments.append(f"⚖️ R/Ö iyi: 1/{rr} - Kabul edilebilir risk/ödül.")
        elif rr >= 1.5:
            comments.append(f"⚖️ R/Ö sınırda: 1/{rr} - Küçük pozisyon aç.")
        else:
            comments.append(f"⚠️ R/Ö düşük: 1/{rr} - Bu oranla girmek risklidir.")
    
    # ═══════════════════════════════════════
    # ADX (TREND GÜCÜ)
    # ═══════════════════════════════════════
    if adx:
        if adx > 30:
            comments.append(f"💪 ADX {adx:.0f} - GÜÇLÜ trend var, mevcut yön devam eder.")
        elif adx > 20:
            comments.append(f"ADX {adx:.0f} - Orta seviye trend var.")
        elif adx < 15:
            comments.append(f"ADX {adx:.0f} - Trend YOK, yatay hareket. Beklemek daha iyi.")
    
    # ═══════════════════════════════════════
    # SONUÇ ÖNERİSİ
    # ═══════════════════════════════════════
    if score >= 75 and rr >= 2:
        comments.append("\n💡 ÖNERİ: Kademeli giriş yapabilirsin. %50 şimdi al, düşüşte %50 daha ekle. H1 vurunca %33 sat, stop'u girişe çek.")
    elif score >= 65 and rr >= 1.5:
        comments.append("\n💡 ÖNERİ: Küçük pozisyon (%25-30) ile başla. Onay bekle, sonra ekle.")
    elif score >= 50:
        comments.append("\n💡 ÖNERİ: BEKLE - daha güçlü sinyal veya teyit gelmesini bekle.")
    else:
        comments.append("\n💡 ÖNERİ: GİRME - risk çok yüksek, fırsat maliyeti daha az riskli hisselere kayabilir.")
    
    return "\n".join([f"• {c}" for c in comments])


# ════════════════════════════════════════════════════════════
# CEVAP MESAJI OLUŞTURMA
# ════════════════════════════════════════════════════════════

def format_analysis_response(signal, symbol, timeframe, error=None):
    """
    Analiz sonucunu güzel bir Telegram mesajı olarak formatla
    """
    if error:
        return f"""❌ <b>ANALİZ YAPILAMADI</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 Hisse: <b>{symbol}</b>
⏰ Zaman: {timeframe}
💬 Sebep: <i>{error}</i>

<b>Yardım:</b>
• Doğru sembol yaz (örn: THYAO, GARAN)
• Formatlar: <code>analiz THYAO</code> / <code>analiz THYAO 4h</code> / <code>analiz THYAO 1h</code>
"""
    
    if not signal:
        return f"❌ {symbol} için analiz sonucu yok"
    
    # Import et
    from telegram_bot.bot import (
        format_signal_for_telegram, 
        format_hourly_signal, 
        format_4h_signal
    )
    
    # Timeframe'e göre uygun kartı seç
    if timeframe == 'hourly':
        card = format_hourly_signal(signal, signal_index=1)
    elif timeframe == '4h':
        card = format_4h_signal(signal, signal_index=1)
    else:
        card = format_signal_for_telegram(signal, signal_index=1)
    
    if not card:
        return f"❌ {symbol} kartı oluşturulamadı"
    
    # AI yorumu ekle
    ai_comment = generate_ai_comment(signal)
    
    ai_msg = f"""

🤖🤖🤖━━━━━━━━━━━━━━━━━🤖🤖🤖
   <b>AI YORUMU</b>
🤖🤖🤖━━━━━━━━━━━━━━━━━🤖🤖🤖

{ai_comment}

━━━━━━━━━━━━━━━━━━━━━━━
🤖 <i>Kural bazlı akıllı analiz</i>
"""
    
    return card + ai_msg


# ════════════════════════════════════════════════════════════
# MESAJ İŞLEME - ANA DÖNGÜ
# ════════════════════════════════════════════════════════════

async def send_response(text):
    """Cevap gönder"""
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Uzun mesajları böl
        if len(text) > 4096:
            chunks = []
            current_chunk = ""
            for line in text.split('\n'):
                if len(current_chunk) + len(line) + 1 > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            if current_chunk:
                chunks.append(current_chunk)
            
            for i, chunk in enumerate(chunks):
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=chunk,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.5)
        else:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        return True
    except Exception as e:
        log_event(f"Cevap gonderme hatasi: {e}")
        return False


async def process_message(update):
    """Tek bir mesajı işle"""
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    chat_id = str(update.message.chat_id)
    
    # Sadece belirli chat_id'den gelen mesajları işle
    if chat_id != str(TELEGRAM_CHAT_ID):
        log_event(f"Yetkisiz chat_id: {chat_id}")
        return
    
    # Komutu parse et
    parsed = parse_analiz_command(text)
    if not parsed:
        return  # Analiz komutu değil, görmezden gel
    
    symbol, timeframe = parsed
    
    log_event(f"Analiz istegi: {symbol} ({timeframe})")
    
    # Sembol geçerli mi?
    if not validate_symbol(symbol):
        await send_response(f"""❌ <b>HİSSE BULUNAMADI</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 Aranan: <b>{symbol}</b>
💬 Bu sembol BIST listesinde yok.

<b>Doğru format:</b>
• <code>analiz THYAO</code>
• <code>analiz GARAN 4h</code>
• <code>analiz ASELS 1h</code>
""")
        return
    
    # "Analiz yapılıyor" mesajı
    tf_display = {
        'daily': 'GÜNLÜK',
        '4h': '4 SAATLİK',
        'hourly': 'SAATLİK'
    }.get(timeframe, timeframe.upper())
    
    await send_response(f"""🔍 <b>{symbol} - {tf_display} ANALİZ YAPILIYOR</b>
━━━━━━━━━━━━━━━━━━━━━━━

⏰ {tr_now().strftime('%H:%M:%S')}
<i>Lütfen bekleyin (10-30 saniye)...</i>
""")
    
    # Analizi yap
    signal, error = perform_analysis(symbol, timeframe)
    
    # Cevabı gönder
    response = format_analysis_response(signal, symbol, timeframe, error)
    await send_response(response)
    
    log_event(f"Analiz cevabi gonderildi: {symbol} ({timeframe})")


# ════════════════════════════════════════════════════════════
# ANA FONKSİYON (Workflow'dan çağrılacak)
# ════════════════════════════════════════════════════════════

async def check_and_respond():
    """
    Yeni mesajları kontrol et ve cevapla
    Bu fonksiyon her workflow çalışmasında bir kez çalışır
    """
    log_event("Mesaj kontrolu basladi")
    
    # Son işlenen update ID'sini oku
    last_update_file = 'last_update_id.txt'
    last_update_id = 0
    
    try:
        if os.path.exists(last_update_file):
            with open(last_update_file, 'r') as f:
                last_update_id = int(f.read().strip())
    except:
        last_update_id = 0
    
    # Yeni mesajları al
    offset = last_update_id + 1 if last_update_id > 0 else None
    updates = await get_updates(offset=offset)
    
    if not updates:
        log_event("Yeni mesaj yok")
        return
    
    log_event(f"{len(updates)} yeni mesaj bulundu")
    
    # Her mesajı işle
    max_update_id = last_update_id
    for update in updates:
        try:
            await process_message(update)
            if update.update_id > max_update_id:
                max_update_id = update.update_id
        except Exception as e:
            log_event(f"Mesaj isleme hatasi: {e}")
    
    # Son işlenen ID'yi kaydet
    try:
        with open(last_update_file, 'w') as f:
            f.write(str(max_update_id))
        log_event(f"Son update ID kaydedildi: {max_update_id}")
    except Exception as e:
        log_event(f"ID kaydetme hatasi: {e}")


def run_message_check():
    """Ana giriş noktası - workflow'dan çağrılır"""
    try:
        asyncio.run(check_and_respond())
    except Exception as e:
        log_event(f"Kritik hata: {e}")


# ════════════════════════════════════════════════════════════
# TEST
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n=== ANALIZ HANDLER TEST ===\n")
    print("1 -> Mesajlari kontrol et ve cevapla")
    print("2 -> Test analizi: THYAO gunluk")
    print("3 -> Test analizi: THYAO 4h")
    print("4 -> Test analizi: THYAO saatlik")
    print("5 -> Komut parse testi")
    
    c = input("\nSecim: ").strip()
    
    if c == "1":
        run_message_check()
    elif c == "2":
        signal, error = perform_analysis("THYAO", "daily")
        if signal:
            response = format_analysis_response(signal, "THYAO", "daily")
            print("\n" + "="*60)
            print("GUNLUK ANALIZ SONUCU:")
            print("="*60)
            print(response[:2000])
        else:
            print(f"Hata: {error}")
    elif c == "3":
        signal, error = perform_analysis("THYAO", "4h")
        if signal:
            print("\n4H ANALIZ OK")
            print(f"Skor: {signal.get('score')}")
        else:
            print(f"Hata: {error}")
    elif c == "4":
        signal, error = perform_analysis("THYAO", "hourly")
        if signal:
            print("\nSAATLIK ANALIZ OK")
            print(f"Skor: {signal.get('score')}")
        else:
            print(f"Hata: {error}")
    elif c == "5":
        # Parse testleri
        tests = [
            "analiz THYAO",
            "/analiz thyao",
            "analiz GARAN 4h",
            "ANALIZ ASELS 1h",
            "analiz",
            "merhaba",
        ]
        for t in tests:
            result = parse_analiz_command(t)
            print(f"'{t}' -> {result}")
