"""
Profesyonel Zamanlayıcı
GÜNLÜK + SAATLİK + 4 SAATLİK tarama + Sinyal takip + Detaylı Gün Sonu + BIST 100 Analizi
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta, time as dt_time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BIST_SYMBOLS
from database import get_connection
from services.data_fetcher import fetch_all_daily, fetch_all_15m
from services.scanner import (
    scan_all_stocks,
    scan_hourly_stocks,
    scan_4h_stocks,
    filter_new_signals
)
from telegram_bot.bot import send_message, send_multiple_signals


TR_TIMEZONE = timezone(timedelta(hours=3))
def tr_now(): return datetime.now(TR_TIMEZONE)
def is_weekday(): return tr_now().weekday() < 5
def log_event(msg):
    print(f"[{tr_now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def job_morning_preparation():
    log_event("🌅 SABAH HAZIRLIK")
    send_message(f"""🌅 <b>SABAH HAZIRLIK BAŞLADI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
📥 Veriler güncelleniyor...
<i>10-15 dk sürer</i>""")
    if not is_weekday():
        send_message("⏸️ <b>Hafta sonu</b>")
        return
    try:
        fetch_all_daily(symbols_list=BIST_SYMBOLS, delay=0.05)
        send_message(f"""✅ <b>SABAH HAZIRLIK TAMAM</b>
✅ Veriler güncellendi
🚀 İlk tarama: <b>10:35</b>
<i>Bugün güzel kazançlar 💪</i>""")
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


def job_premarket_report():
    log_event("📊 PRE-MARKET")
    send_message(f"""📊 <b>PRE-MARKET</b>
⏰ {tr_now().strftime('%H:%M')}""")
    if not is_weekday(): return
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=False, verbose=False)
        if signals:
            top = signals[:5]
            msg = f"🌅 <b>PRE-MARKET RAPORU</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n📌 <b>Bugün izlenecekler:</b>\n\n"
            for i, s in enumerate(top, 1):
                msg += f"{i}. <b>{s['symbol']}</b> - {s['current_price']:.2f} TL ({s['score']}/100)\n"
            msg += "\n<i>Açılışta takip edeceğim 🚀</i>"
            send_message(msg)
        else:
            send_message(f"🌅 <b>PRE-MARKET</b>\n⚠️ Dikkat çeken hisse yok")
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


def job_market_open_scan():
    log_event("🔔 AÇILIŞ")
    send_message(f"""🔔 <b>BORSA AÇILDI</b>
⏰ {tr_now().strftime('%H:%M')}
🔍 Tarama başlıyor...""")
    if not is_weekday(): return
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=True, verbose=False)
        if not signals:
            send_message(f"🔔 <b>AÇILIŞ TARAMASI</b>\n⚠️ Sinyal yok\n<i>11:00'de tekrar</i>")
            return
        send_message(f"🔔 <b>AÇILIŞ - {len(signals)} SİNYAL!</b>\n📩 Gönderiliyor...")
        send_multiple_signals(signals, max_signals=5)
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


def job_quick_scan():
    log_event("⚡ HIZLI TARAMA")
    send_message(f"⚡ <b>HIZLI TARAMA</b>\n⏰ {tr_now().strftime('%H:%M')}")
    try:
        signals = scan_all_stocks(min_score=65, save_to_db=False, verbose=False)
        if not signals:
            send_message(f"⚡ <b>HIZLI TARAMA</b>\n⚠️ Sinyal yok")
            return
        send_message(f"⚡ <b>{len(signals)} SİNYAL!</b>")
        send_multiple_signals(signals, max_signals=3)
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


def job_full_scan():
    log_event("🔍 TAM TARAMA")
    send_message(f"""🔍 <b>TAM TARAMA</b>
⏰ {tr_now().strftime('%H:%M')}
📊 567 hisse taranıyor...""")
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=True, verbose=False)
        if not signals:
            send_message(f"🔍 <b>TAM TARAMA</b>\n⚠️ Sinyal yok\n<i>Sonraki saatte tekrar</i>")
            return
        send_message(f"🔍 <b>{len(signals)} SİNYAL!</b>\n📩 Kartlar geliyor...")
        send_multiple_signals(signals, max_signals=5)
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


def job_hourly_scan():
    log_event("⚡ SAATLİK TARAMA")
    try:
        from telegram_bot.bot import send_hourly_signals
        hourly_signals = scan_hourly_stocks(min_score=60, symbols_list=BIST_SYMBOLS[:200])
        if hourly_signals:
            log_event(f"⚡ {len(hourly_signals)} saatlik sinyal")
            send_hourly_signals(hourly_signals, max_signals=3)
    except Exception as e:
        log_event(f"⚠️ Saatlik hata: {e}")


def job_4h_scan():
    """4 SAATLİK TARAMA - 14:15'te çalışır"""
    log_event("🕐 4 SAATLİK TARAMA BAŞLADI")
    
    send_message(f"""🕐🕐🕐━━━━━━━━━━━━━━━━━🕐🕐🕐
   <b>4 SAATLİK TARAMA</b>
🕐🕐🕐━━━━━━━━━━━━━━━━━🕐🕐🕐

⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
📊 İlk 4H mum kapandı (10:00-14:00)
🔍 {len(BIST_SYMBOLS)} hisse taranıyor...
<i>4H mumlar daha güvenilir sinyal verir</i>""")
    
    try:
        from telegram_bot.bot import send_4h_signals
        
        signals_4h = scan_4h_stocks(min_score=65, symbols_list=BIST_SYMBOLS)
        
        if signals_4h:
            log_event(f"🕐 {len(signals_4h)} adet 4H sinyal bulundu")
            send_4h_signals(signals_4h, max_signals=5)
        else:
            send_message(f"""🕐 <b>4 SAATLİK TARAMA</b>
━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Güçlü 4H sinyal bulunamadı
📊 Piyasa kararsız veya zayıf
<i>Sonraki taramalar saatlik devam eder</i>""")
    except Exception as e:
        log_event(f"❌ 4H hata: {e}")
        send_message(f"❌ <b>4H Tarama Hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# BIST 100 ENDEKS ANALİZİ (YENİ!)
# ════════════════════════════════════════════════════════════

def analyze_bist100():
    """
    BIST 100 (XU100) endeks analizi
    Gün sonu raporunda kullanılır
    """
    try:
        import yfinance as yf
        from services.analyzer import analyze_stock
        import pandas as pd
        
        log_event("📊 BIST 100 analizi başladı")
        
        ticker = yf.Ticker("XU100.IS")
        hist = ticker.history(period="6mo")
        
        if len(hist) < 50:
            return None
        
        df = pd.DataFrame({
            'date': [d.strftime('%Y-%m-%d') for d in hist.index],
            'open': hist['Open'].values,
            'high': hist['High'].values,
            'low': hist['Low'].values,
            'close': hist['Close'].values,
            'volume': hist['Volume'].values
        })
        
        analysis = analyze_stock(df)
        if not analysis:
            return None
        
        # Değişim
        today_close = analysis.get('current_price')
        prev_close = analysis.get('prev_close')
        daily_change = ((today_close - prev_close) / prev_close) * 100 if prev_close else 0
        
        # Trend durumu
        ema_9 = analysis.get('ema_9')
        ema_21 = analysis.get('ema_21')
        ema_50 = analysis.get('ema_50')
        
        trend_status = "YATAY"
        trend_emoji = "➡️"
        trend_detail = ""
        
        if ema_9 and ema_21 and ema_50:
            if today_close > ema_9 > ema_21 > ema_50:
                trend_status = "GÜÇLÜ BOĞA"
                trend_emoji = "🚀"
                trend_detail = "Tüm EMA'lar sıralı yukarı"
            elif today_close > ema_21 and today_close > ema_50:
                trend_status = "BOĞA"
                trend_emoji = "📈"
                trend_detail = "EMA21 ve EMA50 üzerinde"
            elif today_close > ema_50:
                trend_status = "POZİTİF"
                trend_emoji = "✅"
                trend_detail = "EMA50 üzerinde tutunuyor"
            elif today_close < ema_9 < ema_21 < ema_50:
                trend_status = "GÜÇLÜ AYI"
                trend_emoji = "📉"
                trend_detail = "Tüm EMA'lar sıralı aşağı"
            elif today_close < ema_50:
                trend_status = "AYI"
                trend_emoji = "🔴"
                trend_detail = "EMA50 altında"
        
        # RSI durumu
        rsi = analysis.get('rsi', 50)
        prev_rsi = analysis.get('prev_rsi', 50)
        
        if rsi > 70:
            rsi_status = "AŞIRI ALIM"
            rsi_emoji = "🔴"
        elif rsi > 60:
            rsi_status = "GÜÇLÜ"
            rsi_emoji = "💪"
        elif rsi > 50:
            rsi_status = "POZİTİF"
            rsi_emoji = "✅"
        elif rsi > 40:
            rsi_status = "NÖTR"
            rsi_emoji = "➡️"
        elif rsi > 30:
            rsi_status = "ZAYIF"
            rsi_emoji = "⚠️"
        else:
            rsi_status = "AŞIRI SATIM"
            rsi_emoji = "🟢"
        
        # Momentum
        momentum = "NÖTR"
        momentum_emoji = "➡️"
        momentum_detail = ""
        
        if rsi and prev_rsi:
            rsi_change = rsi - prev_rsi
            if rsi_change > 3 and rsi > 50:
                momentum = "GÜÇLENİYOR"
                momentum_emoji = "🚀"
                momentum_detail = f"RSI +{rsi_change:.1f} arttı"
            elif rsi_change > 1:
                momentum = "HAFİF YUKARI"
                momentum_emoji = "📈"
                momentum_detail = "İvme kazanıyor"
            elif rsi_change < -3:
                momentum = "ZAYIFLIYOR"
                momentum_emoji = "📉"
                momentum_detail = f"RSI {rsi_change:.1f} azaldı"
            elif rsi_change < -1:
                momentum = "HAFİF AŞAĞI"
                momentum_emoji = "🔽"
                momentum_detail = "İvme kaybediyor"
        
        # MACD
        macd = analysis.get('macd')
        macd_signal = analysis.get('macd_signal')
        macd_hist = analysis.get('macd_hist')
        prev_macd_hist = analysis.get('prev_macd_hist')
        
        macd_status = "NÖTR"
        macd_emoji = "➡️"
        
        if macd is not None and macd_signal is not None:
            if macd > macd_signal and macd > 0:
                macd_status = "POZİTİF / YUKARI"
                macd_emoji = "🟢"
            elif macd > macd_signal:
                macd_status = "YUKARI KESİŞİM"
                macd_emoji = "🟡"
            elif macd < macd_signal and macd < 0:
                macd_status = "NEGATİF / AŞAĞI"
                macd_emoji = "🔴"
            else:
                macd_status = "AŞAĞI KESİŞİM"
                macd_emoji = "⚠️"
        
        # Destek/Direnç
        pivot = analysis.get('pivot')
        r1 = analysis.get('r1')
        r2 = analysis.get('r2')
        r3 = analysis.get('r3')
        s1 = analysis.get('s1')
        s2 = analysis.get('s2')
        s3 = analysis.get('s3')
        
        # ADX (trend gücü)
        adx = analysis.get('adx', 0)
        if adx > 30:
            adx_status = "ÇOK GÜÇLÜ"
        elif adx > 25:
            adx_status = "GÜÇLÜ"
        elif adx > 20:
            adx_status = "ORTA"
        else:
            adx_status = "ZAYIF"
        
        # YARIN İÇİN BEKLENTİ
        yarin_beklenti = []
        
        if trend_status in ["GÜÇLÜ BOĞA", "BOĞA"]:
            if rsi < 70 and momentum in ["GÜÇLENİYOR", "HAFİF YUKARI"]:
                yarin_beklenti.append("✅ Yükseliş devam edebilir")
                if r1:
                    yarin_beklenti.append(f"🎯 İlk hedef: <b>{r1:.0f}</b> direnci")
            elif rsi >= 70:
                yarin_beklenti.append("⚠️ Aşırı alımda, düzeltme gelebilir")
                if pivot:
                    yarin_beklenti.append(f"📊 Pivot testi: <b>{pivot:.0f}</b>")
        elif trend_status == "POZİTİF":
            if r1 and today_close < r1:
                yarin_beklenti.append(f"🎯 <b>{r1:.0f}</b> direnci kırılırsa yükseliş güçlenir")
            if s1:
                yarin_beklenti.append(f"🛡️ Destek: <b>{s1:.0f}</b>")
        elif trend_status in ["AYI", "GÜÇLÜ AYI"]:
            if s1 and today_close > s1:
                yarin_beklenti.append(f"⚠️ <b>{s1:.0f}</b> desteği kırılırsa düşüş hızlanır")
            if rsi < 30:
                yarin_beklenti.append("🟢 Aşırı satımda, tepki alışı gelebilir")
        else:  # YATAY
            if r1 and s1:
                yarin_beklenti.append(f"📊 <b>{s1:.0f}</b> - <b>{r1:.0f}</b> bandında sıkışma")
            yarin_beklenti.append("⏳ Yön belirlemesi bekle")
        
        return {
            'price': today_close,
            'change': daily_change,
            'trend_status': trend_status,
            'trend_emoji': trend_emoji,
            'trend_detail': trend_detail,
            'rsi': rsi,
            'rsi_status': rsi_status,
            'rsi_emoji': rsi_emoji,
            'momentum': momentum,
            'momentum_emoji': momentum_emoji,
            'momentum_detail': momentum_detail,
            'macd_status': macd_status,
            'macd_emoji': macd_emoji,
            'adx': adx,
            'adx_status': adx_status,
            'pivot': pivot,
            'r1': r1, 'r2': r2, 'r3': r3,
            's1': s1, 's2': s2, 's3': s3,
            'yarin_beklenti': yarin_beklenti,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'ema_50': ema_50,
        }
    except Exception as e:
        log_event(f"❌ BIST 100 analiz hatası: {e}")
        return None


def format_bist100_analysis(bist):
    """BIST 100 analiz sonucunu formatla"""
    if not bist:
        return "📊 <b>BIST 100 ANALİZİ</b>\n⚠️ Veri alınamadı\n\n"
    
    change_emoji = "🟢" if bist['change'] > 0 else "🔴" if bist['change'] < 0 else "⚪"
    change_sign = "+" if bist['change'] > 0 else ""
    
    msg = "📊📊📊━━━━━━━━━━━━━━━━━📊📊📊\n"
    msg += "     <b>BIST 100 (XU100) ANALİZİ</b>\n"
    msg += "📊📊📊━━━━━━━━━━━━━━━━━📊📊📊\n\n"
    
    msg += f"💰 <b>Kapanış:</b> <b>{bist['price']:.0f}</b> puan\n"
    msg += f"{change_emoji} <b>Değişim:</b> <b>{change_sign}%{bist['change']:.2f}</b>\n\n"
    
    # GENEL DURUM
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🎯 <b>GENEL DURUM</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"{bist['trend_emoji']} <b>Trend:</b> {bist['trend_status']}\n"
    if bist['trend_detail']:
        msg += f"   <i>{bist['trend_detail']}</i>\n"
    msg += f"💪 <b>Trend Gücü (ADX):</b> {bist['adx']:.1f} - {bist['adx_status']}\n\n"
    
    # TEKNİK
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📈 <b>TEKNİK GÖSTERGELER</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"{bist['rsi_emoji']} <b>RSI:</b> <b>{bist['rsi']:.1f}</b> - {bist['rsi_status']}\n"
    msg += f"{bist['macd_emoji']} <b>MACD:</b> {bist['macd_status']}\n\n"
    
    # MOMENTUM
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚡ <b>MOMENTUM</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"{bist['momentum_emoji']} <b>Yön:</b> {bist['momentum']}\n"
    if bist['momentum_detail']:
        msg += f"   <i>{bist['momentum_detail']}</i>\n"
    msg += "\n"
    
    # DESTEK / DİRENÇ
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🎯 <b>DESTEK / DİRENÇ SEVİYELERİ</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if bist['r3']: msg += f"🔴 <b>Direnç 3:</b> {bist['r3']:.0f}\n"
    if bist['r2']: msg += f"🔴 <b>Direnç 2:</b> {bist['r2']:.0f}\n"
    if bist['r1']: msg += f"🔴 <b>Direnç 1:</b> <b>{bist['r1']:.0f}</b>\n"
    if bist['pivot']: msg += f"⚪ <b>Pivot:</b> <b>{bist['pivot']:.0f}</b>\n"
    if bist['s1']: msg += f"🟢 <b>Destek 1:</b> <b>{bist['s1']:.0f}</b>\n"
    if bist['s2']: msg += f"🟢 <b>Destek 2:</b> {bist['s2']:.0f}\n"
    if bist['s3']: msg += f"🟢 <b>Destek 3:</b> {bist['s3']:.0f}\n\n"
    
    # EMA SEVİYELERİ
    if bist.get('ema_9') and bist.get('ema_21') and bist.get('ema_50'):
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📊 <b>EMA SEVİYELERİ</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        price = bist['price']
        msg += f"{'🟢' if price > bist['ema_9'] else '🔴'} EMA9  : <b>{bist['ema_9']:.0f}</b>\n"
        msg += f"{'🟢' if price > bist['ema_21'] else '🔴'} EMA21 : <b>{bist['ema_21']:.0f}</b>\n"
        msg += f"{'🟢' if price > bist['ema_50'] else '🔴'} EMA50 : <b>{bist['ema_50']:.0f}</b>\n\n"
    
    # YARIN BEKLENTİ
    if bist['yarin_beklenti']:
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🔮 <b>YARIN İÇİN BEKLENTİ</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for beklenti in bist['yarin_beklenti']:
            msg += f"{beklenti}\n"
        msg += "\n"
    
    msg += "📊📊📊━━━━━━━━━━━━━━━━━📊📊📊\n\n"
    
    return msg


# ════════════════════════════════════════════════════════════
# GÜN SONU RAPORU (18:30) - BIST 100 ANALİZİ + YARIN 5 HİSSE
# ════════════════════════════════════════════════════════════

def job_end_of_day_report():
    log_event("🌆 GÜN SONU RAPORU")
    
    try:
        import yfinance as yf
        from services.analyzer import analyze_stock
        from services.signal_engine import generate_signal
        import pandas as pd
        
        send_message(f"""🌆 <b>GÜN SONU RAPORU HAZIRLANIYOR</b>
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
📊 Analiz ediliyor...""")
        
        # ═══════════════════════════════════════
        # 1. BIST 100 ANALİZİ (YENİ!)
        # ═══════════════════════════════════════
        bist100 = analyze_bist100()
        
        # ═══════════════════════════════════════
        # 2. TÜM HİSSELER
        # ═══════════════════════════════════════
        movers_data = []
        tomorrow_candidates = []
        
        for symbol in BIST_SYMBOLS:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                if len(hist) < 2: continue
                
                today_close = float(hist['Close'].iloc[-1])
                yesterday_close = float(hist['Close'].iloc[-2])
                today_volume = int(hist['Volume'].iloc[-1])
                today_high = float(hist['High'].iloc[-1])
                today_low = float(hist['Low'].iloc[-1])
                today_open = float(hist['Open'].iloc[-1])
                
                daily_change = ((today_close - yesterday_close) / yesterday_close) * 100
                avg_volume = hist['Volume'].mean()
                rvol = today_volume / avg_volume if avg_volume > 0 else 0
                volume_tl = today_close * today_volume
                
                candle_strength = ((today_close - today_low) / (today_high - today_low)) * 100 if today_high > today_low else 50
                green_candle = today_close > today_open
                
                movers_data.append({
                    'symbol': symbol.replace('.IS', ''),
                    'full_symbol': symbol,
                    'price': today_close,
                    'daily_change': daily_change,
                    'volume': today_volume,
                    'volume_tl': volume_tl,
                    'rvol': rvol,
                    'high': today_high,
                    'low': today_low,
                    'candle_strength': candle_strength,
                    'green_candle': green_candle,
                    'yesterday_close': yesterday_close
                })
                
                if (green_candle and candle_strength > 60 and rvol >= 1.2 and
                    daily_change > 0 and daily_change < 9.5 and volume_tl > 2_000_000):
                    tomorrow_candidates.append({
                        'symbol': symbol.replace('.IS', ''),
                        'full_symbol': symbol,
                        'price': today_close,
                        'daily_change': daily_change,
                        'rvol': rvol,
                        'candle_strength': candle_strength,
                        'volume_tl': volume_tl
                    })
            except: continue
        
        # ═══════════════════════════════════════
        # 3. YARIN ADAYLARI DETAYLI ANALİZ
        # ═══════════════════════════════════════
        tomorrow_signals = []
        
        for candidate in tomorrow_candidates:
            try:
                ticker = yf.Ticker(candidate['full_symbol'])
                hist = ticker.history(period="1y")
                if len(hist) < 50: continue
                
                df = pd.DataFrame({
                    'date': [d.strftime('%Y-%m-%d') for d in hist.index],
                    'open': hist['Open'].values, 'high': hist['High'].values,
                    'low': hist['Low'].values, 'close': hist['Close'].values,
                    'volume': hist['Volume'].values
                })
                
                analysis = analyze_stock(df)
                if not analysis: continue
                
                signal = generate_signal(candidate['full_symbol'], analysis, df)
                if not signal: continue
                
                rsi = analysis.get('rsi', 50)
                ema_50 = analysis.get('ema_50')
                current = analysis.get('current_price')
                macd = analysis.get('macd')
                macd_signal = analysis.get('macd_signal')
                
                ts = 0
                tr_reasons = []
                
                if candidate['candle_strength'] > 80: ts += 25; tr_reasons.append("💪 Çok güçlü kapanış")
                elif candidate['candle_strength'] > 60: ts += 15; tr_reasons.append("📈 Güçlü kapanış")
                
                if candidate['rvol'] >= 2: ts += 20; tr_reasons.append(f"💥 Hacim {candidate['rvol']:.1f}x")
                elif candidate['rvol'] >= 1.5: ts += 12; tr_reasons.append(f"📊 Hacim {candidate['rvol']:.1f}x")
                elif candidate['rvol'] >= 1.2: ts += 5
                
                if 50 <= rsi <= 65: ts += 15; tr_reasons.append(f"⚡ RSI {rsi:.0f} (ideal)")
                elif 45 <= rsi < 50: ts += 10
                elif rsi > 70: ts -= 10; tr_reasons.append(f"⚠️ RSI {rsi:.0f} (yüksek)")
                
                if current and ema_50 and current > ema_50: ts += 15; tr_reasons.append("📈 EMA50 üstünde")
                elif current and ema_50 and current < ema_50: ts -= 5
                
                if macd and macd_signal and macd > macd_signal: ts += 10; tr_reasons.append("🚀 MACD pozitif")
                
                if 3 <= candidate['daily_change'] <= 7: ts += 10; tr_reasons.append(f"📈 Bugün +%{candidate['daily_change']:.1f}")
                elif 1 <= candidate['daily_change'] < 3: ts += 5
                
                ts += int(signal['score'] * 0.1)
                
                if ts >= 40:
                    tomorrow_signals.append({
                        'symbol': candidate['symbol'],
                        'price': candidate['price'],
                        'daily_change': candidate['daily_change'],
                        'rvol': candidate['rvol'],
                        'candle_strength': candidate['candle_strength'],
                        'tomorrow_score': ts,
                        'reasons': tr_reasons,
                        'signal_score': signal['score'],
                        'targets': signal.get('targets', {}),
                        'rsi': rsi
                    })
            except: continue
        
        tomorrow_signals.sort(key=lambda x: x['tomorrow_score'], reverse=True)
        top_5 = tomorrow_signals[:5]
        
        # ═══════════════════════════════════════
        # 4. İSTATİSTİKLER
        # ═══════════════════════════════════════
        liquid = [m for m in movers_data if m['volume_tl'] > 1_000_000]
        gainers = sorted([m for m in liquid if m['daily_change'] > 0], key=lambda x: x['daily_change'], reverse=True)[:5]
        losers = sorted([m for m in liquid if m['daily_change'] < 0], key=lambda x: x['daily_change'])[:5]
        total_up = len([m for m in movers_data if m['daily_change'] > 0])
        total_down = len([m for m in movers_data if m['daily_change'] < 0])
        
        # ═══════════════════════════════════════
        # 5. RAPOR - BÖLÜM 1: BAŞLIK + BIST 100
        # ═══════════════════════════════════════
        msg1 = f"""🌆 <b>GÜN SONU RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━
📅 {tr_now().strftime('%d.%m.%Y - %A')}

"""
        
        # BIST 100 ANALİZİ EKLE
        msg1 += format_bist100_analysis(bist100)
        
        send_message(msg1)
        
        # ═══════════════════════════════════════
        # 6. RAPOR - BÖLÜM 2: PİYASA + HİSSELER
        # ═══════════════════════════════════════
        msg2 = "📊 <b>PİYASA DURUMU</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg2 += f"📈 Yükselen: <b>{total_up}</b>\n"
        msg2 += f"📉 Düşen: <b>{total_down}</b>\n"
        
        if total_up > total_down * 1.5: msg2 += "💪 <b>Trend: GÜÇLÜ YUKARI</b> 🚀\n\n"
        elif total_up > total_down: msg2 += "✅ <b>Trend: POZİTİF</b> 📈\n\n"
        elif total_down > total_up * 1.5: msg2 += "⚠️ <b>Trend: GÜÇLÜ AŞAĞI</b> 📉\n\n"
        else: msg2 += "➡️ <b>Trend: YATAY</b>\n\n"
        
        if gainers:
            msg2 += "🏆 <b>EN ÇOK YÜKSELENLER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, g in enumerate(gainers, 1):
                rv = "🔥" if g['rvol'] > 3 else "💪" if g['rvol'] > 1.5 else ""
                msg2 += f"{i}. <b>{g['symbol']}</b> <b>+%{g['daily_change']:.2f}</b> ({g['price']:.2f} TL) {rv}\n"
            msg2 += "\n"
        
        if losers:
            msg2 += "📉 <b>EN ÇOK DÜŞENLER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, l in enumerate(losers, 1):
                msg2 += f"{i}. <b>{l['symbol']}</b> <b>%{l['daily_change']:.2f}</b> ({l['price']:.2f} TL)\n"
            msg2 += "\n"
        
        # YARIN İÇİN EN İYİ 5 HİSSE
        if top_5:
            msg2 += "⭐⭐⭐━━━━━━━━━━━━━━━━━⭐⭐⭐\n"
            msg2 += "   <b>YARIN İÇİN EN İYİ 5 HİSSE</b>\n"
            msg2 += "⭐⭐⭐━━━━━━━━━━━━━━━━━⭐⭐⭐\n\n"
            msg2 += "🎯 <i>Son kapanış verilerine göre</i>\n\n"
            
            for i, t in enumerate(top_5, 1):
                medal = {1:'🥇',2:'🥈',3:'🥉',4:'🏅',5:'🎖️'}.get(i, f"{i}.")
                msg2 += f"{medal} <b>{t['symbol']}</b>\n"
                msg2 += f"   💰 Kapanış: <b>{t['price']:.2f} TL</b>\n"
                msg2 += f"   📊 Bugün: <b>+%{t['daily_change']:.2f}</b> | Hacim: {t['rvol']:.1f}x\n"
                msg2 += f"   💪 Mum gücü: %{t['candle_strength']:.0f}\n"
                
                targets = t.get('targets', {})
                if targets.get('target_1'):
                    msg2 += f"   🎯 Hedef: <b>{targets['target_1']:.2f} TL</b> (+{targets.get('target_1_pct',0)}%)\n"
                
                if t['reasons']:
                    msg2 += f"   ✅ {' | '.join(t['reasons'][:3])}\n"
                msg2 += "\n"
            
            msg2 += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg2 += "⚠️ <i>Yarın açılışta fiyat kontrol edin!</i>\n"
            msg2 += "⚠️ <i>Gap up varsa dikkatli giriş!</i>\n\n"
        else:
            msg2 += "⭐ <b>YARIN İÇİN ADAY</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg2 += "⚠️ <i>Güçlü aday bulunamadı</i>\n\n"
        
        # STRATEJİ
        msg2 += "🎯 <b>YARIN STRATEJİ</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # BIST 100'e göre strateji önerisi
        if bist100:
            trend = bist100.get('trend_status', '')
            if trend in ["GÜÇLÜ BOĞA", "BOĞA"]:
                msg2 += "✅ BIST 100 güçlü, AL fırsatlarına odaklan\n"
                msg2 += "✅ Yukarıdaki 5 hisseyi izle\n\n"
            elif trend in ["AYI", "GÜÇLÜ AYI"]:
                msg2 += "⚠️ BIST 100 zayıf, DİKKATLİ ol\n"
                msg2 += "⚠️ Sadece çok güçlü sinyallere gir\n"
                msg2 += "⚠️ Küçük pozisyon aç\n\n"
            else:
                msg2 += "📊 BIST 100 kararsız, seçici ol\n"
                msg2 += "📊 Top 2-3 hisseyi izle\n\n"
        else:
            if total_up > total_down * 1.5:
                msg2 += "✅ Piyasa güçlü, AL fırsatlarına odaklan\n\n"
            elif total_down > total_up * 1.5:
                msg2 += "⚠️ Piyasa zayıf, DİKKATLİ ol\n\n"
            else:
                msg2 += "📊 Karışık piyasa, seçici ol\n\n"
        
        if top_5:
            msg2 += "👀 <b>YARIN İZLE:</b> " + ", ".join([t['symbol'] for t in top_5]) + "\n\n"
        
        msg2 += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg2 += "💤 <i>Bot dinlenmeye geçiyor</i>\n"
        msg2 += "🌅 <i>Yarın 09:45'te tekrar!</i>\n"
        msg2 += "💰 <i>İyi kazançlar!</i>"
        
        send_message(msg2)
        log_event("✅ Gün sonu raporu gönderildi")
    except Exception as e:
        log_event(f"❌ Gün sonu hatası: {e}")
        send_message(f"❌ <b>Gün sonu hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# TAM TARAMA + SAATLİK + TAKİP (BİRLEŞİK)
# ════════════════════════════════════════════════════════════

def job_full_scan_with_tracking():
    log_event("🔍 TAM + SAATLİK + TAKİP")
    
    # 1. Günlük
    job_full_scan()
    
    # 2. Saatlik
    log_event("⚡ SAATLİK BAŞLATILIYOR...")
    try: job_hourly_scan()
    except Exception as e: log_event(f"⚠️ Saatlik hata: {e}")
    
    # 3. Takip
    log_event("🎯 TAKİP BAŞLATILIYOR...")
    try:
        from services.signal_tracker import track_signals_job
        track_signals_job()
    except Exception as e:
        send_message(f"❌ <b>Takip hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# ZAMANLAYICI
# ════════════════════════════════════════════════════════════

def setup_scheduler():
    scheduler = BlockingScheduler(timezone='Europe/Istanbul')
    scheduler.add_job(job_morning_preparation, CronTrigger(hour=9, minute=45, day_of_week='mon-fri'), id='morning')
    scheduler.add_job(job_premarket_report, CronTrigger(hour=9, minute=55, day_of_week='mon-fri'), id='premarket')
    scheduler.add_job(job_market_open_scan, CronTrigger(hour=10, minute=35, day_of_week='mon-fri'), id='open')
    scheduler.add_job(job_quick_scan, CronTrigger(minute='30,45', hour='10-17', day_of_week='mon-fri'), id='quick')
    scheduler.add_job(job_full_scan, CronTrigger(minute=0, hour='11-17', day_of_week='mon-fri'), id='full')
    scheduler.add_job(job_4h_scan, CronTrigger(hour=14, minute=15, day_of_week='mon-fri'), id='4h_scan')
    scheduler.add_job(job_end_of_day_report, CronTrigger(hour=18, minute=30, day_of_week='mon-fri'), id='eod')
    return scheduler

def start_scheduler():
    scheduler = setup_scheduler()
    try: send_message(f"🤖 <b>BOT AKTİF</b>\n⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}")
    except: pass
    try: scheduler.start()
    except (KeyboardInterrupt, SystemExit): print("⏹️ Durduruldu")


if __name__ == "__main__":
    print(f"\n⏰ ZAMANLAYICI - {tr_now().strftime('%H:%M')}")
    print("1→Başlat 2→Sabah 3→PreMarket 4→Açılış 5→Hızlı")
    print("6→Tam 7→4H Tarama 8→GünSonu 9→Tam+Saatlik+Takip 10→Saatlik")
    
    c = input("\nSeçim: ").strip()
    if c=="1": start_scheduler()
    elif c=="2": job_morning_preparation()
    elif c=="3": job_premarket_report()
    elif c=="4": job_market_open_scan()
    elif c=="5": job_quick_scan()
    elif c=="6": job_full_scan()
    elif c=="7": job_4h_scan()
    elif c=="8": job_end_of_day_report()
    elif c=="9": job_full_scan_with_tracking()
    elif c=="10": job_hourly_scan()
