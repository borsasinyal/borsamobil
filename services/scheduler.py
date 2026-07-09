"""
Profesyonel Zamanlayıcı - SON HAL
GÜNLÜK + SAATLİK (3 TEYİT) + 4 SAATLİK + BIST 100 FİBONACCİ
+ 20/50 GERÇEK KESİŞİM + PERFORMANS + HAFTALIK RAPOR
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
    log_event("⚡ SAATLİK TARAMA (3 TEYİT)")
    try:
        from telegram_bot.bot import send_hourly_signals
        hourly_signals = scan_hourly_stocks(min_score=68, symbols_list=BIST_SYMBOLS[:200])
        if hourly_signals:
            log_event(f"⚡ {len(hourly_signals)} saatlik sinyal (3 teyit onaylı)")
            send_hourly_signals(hourly_signals, max_signals=3)
    except Exception as e:
        log_event(f"⚠️ Saatlik hata: {e}")


def job_4h_scan():
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
⚠️ Güçlü 4H sinyal bulunamadı""")
    except Exception as e:
        log_event(f"❌ 4H hata: {e}")
        send_message(f"❌ <b>4H Tarama Hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# BIST 100 - FİBONACCİ DESTEK/DİRENÇ
# ════════════════════════════════════════════════════════════

def calculate_fibonacci_levels(df, lookback=90):
    """Son N gün Fibonacci geri çekilme seviyeleri"""
    if len(df) < lookback:
        lookback = len(df)
    
    recent = df.tail(lookback)
    high = recent['high'].max()
    low = recent['low'].min()
    diff = high - low
    
    levels = {
        'zirve': high,
        'fib_786': high - (diff * 0.214),
        'fib_618': high - (diff * 0.382),
        'fib_50': high - (diff * 0.5),
        'fib_382': high - (diff * 0.618),
        'fib_236': high - (diff * 0.764),
        'dip': low,
        'range': diff
    }
    return levels


def analyze_bist100():
    """BIST 100 (XU100) endeks analizi - Fibonacci destek/direnç"""
    try:
        import yfinance as yf
        from services.analyzer import analyze_stock
        import pandas as pd
        
        log_event("📊 BIST 100 Fibonacci analizi başladı")
        
        ticker = yf.Ticker("XU100.IS")
        hist = ticker.history(period="6mo")
        if len(hist) < 50:
            return None
        
        df = pd.DataFrame({
            'date': [d.strftime('%Y-%m-%d') for d in hist.index],
            'open': hist['Open'].values, 'high': hist['High'].values,
            'low': hist['Low'].values, 'close': hist['Close'].values,
            'volume': hist['Volume'].values
        })
        
        analysis = analyze_stock(df, timeframe='daily')
        if not analysis:
            return None
        
        fib_levels = calculate_fibonacci_levels(df, lookback=90)
        
        today_close = analysis.get('current_price')
        prev_close = analysis.get('prev_close')
        daily_change = ((today_close - prev_close) / prev_close) * 100 if prev_close else 0
        
        ema_5 = analysis.get('ema_5')
        ema_22 = analysis.get('ema_22')
        ema_50 = analysis.get('ema_50')
        
        trend_status = "YATAY"; trend_emoji = "➡️"; trend_detail = ""
        if ema_5 and ema_22 and ema_50:
            if today_close > ema_5 > ema_22 > ema_50:
                trend_status = "GÜÇLÜ BOĞA"; trend_emoji = "🚀"; trend_detail = "Tüm EMA'lar sıralı yukarı"
            elif today_close > ema_22 and today_close > ema_50:
                trend_status = "BOĞA"; trend_emoji = "📈"; trend_detail = "EMA22 ve EMA50 üzerinde"
            elif today_close > ema_50:
                trend_status = "POZİTİF"; trend_emoji = "✅"; trend_detail = "EMA50 üzerinde tutunuyor"
            elif today_close < ema_5 < ema_22 < ema_50:
                trend_status = "GÜÇLÜ AYI"; trend_emoji = "📉"; trend_detail = "Tüm EMA'lar sıralı aşağı"
            elif today_close < ema_50:
                trend_status = "AYI"; trend_emoji = "🔴"; trend_detail = "EMA50 altında"
        
        rsi = analysis.get('rsi', 50)
        prev_rsi = analysis.get('prev_rsi', 50)
        
        if rsi > 70: rsi_status = "AŞIRI ALIM"; rsi_emoji = "🔴"
        elif rsi > 60: rsi_status = "GÜÇLÜ"; rsi_emoji = "💪"
        elif rsi > 50: rsi_status = "POZİTİF"; rsi_emoji = "✅"
        elif rsi > 40: rsi_status = "NÖTR"; rsi_emoji = "➡️"
        elif rsi > 30: rsi_status = "ZAYIF"; rsi_emoji = "⚠️"
        else: rsi_status = "AŞIRI SATIM"; rsi_emoji = "🟢"
        
        momentum = "NÖTR"; momentum_emoji = "➡️"; momentum_detail = ""
        if rsi and prev_rsi:
            rsi_change = rsi - prev_rsi
            if rsi_change > 3 and rsi > 50:
                momentum = "GÜÇLENİYOR"; momentum_emoji = "🚀"; momentum_detail = f"RSI +{rsi_change:.1f} arttı"
            elif rsi_change > 1:
                momentum = "HAFİF YUKARI"; momentum_emoji = "📈"; momentum_detail = "İvme kazanıyor"
            elif rsi_change < -3:
                momentum = "ZAYIFLIYOR"; momentum_emoji = "📉"; momentum_detail = f"RSI {rsi_change:.1f} azaldı"
            elif rsi_change < -1:
                momentum = "HAFİF AŞAĞI"; momentum_emoji = "🔽"; momentum_detail = "İvme kaybediyor"
        
        macd = analysis.get('macd')
        macd_signal = analysis.get('macd_signal')
        macd_status = "NÖTR"; macd_emoji = "➡️"
        if macd is not None and macd_signal is not None:
            if macd > macd_signal and macd > 0: macd_status = "POZİTİF / YUKARI"; macd_emoji = "🟢"
            elif macd > macd_signal: macd_status = "YUKARI KESİŞİM"; macd_emoji = "🟡"
            elif macd < macd_signal and macd < 0: macd_status = "NEGATİF / AŞAĞI"; macd_emoji = "🔴"
            else: macd_status = "AŞAĞI KESİŞİM"; macd_emoji = "⚠️"
        
        adx = analysis.get('adx', 0)
        if adx > 30: adx_status = "ÇOK GÜÇLÜ"
        elif adx > 25: adx_status = "GÜÇLÜ"
        elif adx > 20: adx_status = "ORTA"
        else: adx_status = "ZAYIF"
        
        yarin_beklenti = []
        cp = today_close
        
        if cp >= fib_levels['fib_786']:
            yarin_beklenti.append(f"🎯 Fibonacci <b>0.786</b> ({fib_levels['fib_786']:.0f}) üstünde - Güçlü")
            yarin_beklenti.append(f"🚀 Zirve testi: <b>{fib_levels['zirve']:.0f}</b>")
        elif cp >= fib_levels['fib_618']:
            yarin_beklenti.append(f"💎 <b>Altın Oran (0.618)</b> üstü - Sağlam bölge")
            yarin_beklenti.append(f"🎯 Sonraki hedef: <b>{fib_levels['fib_786']:.0f}</b> (0.786)")
        elif cp >= fib_levels['fib_50']:
            yarin_beklenti.append(f"📊 <b>0.5</b> orta bölge - Kararsız")
            yarin_beklenti.append(f"🎯 Yukarı: <b>{fib_levels['fib_618']:.0f}</b> | Aşağı: <b>{fib_levels['fib_382']:.0f}</b>")
        elif cp >= fib_levels['fib_382']:
            yarin_beklenti.append(f"⚠️ <b>0.382</b> altında - Zayıf bölge")
            yarin_beklenti.append(f"🛡️ Kritik destek: <b>{fib_levels['fib_236']:.0f}</b>")
        elif cp >= fib_levels['fib_236']:
            yarin_beklenti.append(f"🔴 <b>0.236</b> yakın - Dip bölge")
            yarin_beklenti.append(f"🛡️ Son destek: <b>{fib_levels['dip']:.0f}</b>")
        else:
            yarin_beklenti.append(f"⛔ Dip bölgesinde - Riskli")
            yarin_beklenti.append(f"🟢 Aşırı satım - tepki alışı olabilir")
        
        if trend_status in ["GÜÇLÜ BOĞA", "BOĞA"]:
            if rsi < 70:
                yarin_beklenti.append("✅ Trend güçlü, yükseliş devam edebilir")
            else:
                yarin_beklenti.append("⚠️ RSI yüksek, düzeltme gelebilir")
        elif trend_status in ["AYI", "GÜÇLÜ AYI"]:
            if rsi < 30:
                yarin_beklenti.append("🟢 Aşırı satımda, tepki alışı gelebilir")
        
        return {
            'price': today_close, 'change': daily_change,
            'trend_status': trend_status, 'trend_emoji': trend_emoji, 'trend_detail': trend_detail,
            'rsi': rsi, 'rsi_status': rsi_status, 'rsi_emoji': rsi_emoji,
            'momentum': momentum, 'momentum_emoji': momentum_emoji, 'momentum_detail': momentum_detail,
            'macd_status': macd_status, 'macd_emoji': macd_emoji,
            'adx': adx, 'adx_status': adx_status,
            'yarin_beklenti': yarin_beklenti,
            'ema_5': ema_5, 'ema_22': ema_22, 'ema_50': ema_50,
            'fibonacci': fib_levels,
        }
    except Exception as e:
        log_event(f"❌ BIST 100 analiz hatası: {e}")
        return None


def format_bist100_analysis(bist):
    """BIST 100 analiz - Fibonacci destek/direnç ile"""
    if not bist:
        return "📊 <b>BIST 100 ANALİZİ</b>\n⚠️ Veri alınamadı\n\n"
    
    change_emoji = "🟢" if bist['change'] > 0 else "🔴" if bist['change'] < 0 else "⚪"
    change_sign = "+" if bist['change'] > 0 else ""
    
    msg = "📊📊📊━━━━━━━━━━━━━━━━━📊📊📊\n"
    msg += "     <b>BIST 100 (XU100) ANALİZİ</b>\n"
    msg += "📊📊📊━━━━━━━━━━━━━━━━━📊📊📊\n\n"
    msg += f"💰 <b>Kapanış:</b> <b>{bist['price']:.0f}</b> puan\n"
    msg += f"{change_emoji} <b>Değişim:</b> <b>{change_sign}%{bist['change']:.2f}</b>\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n🎯 <b>GENEL DURUM</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"{bist['trend_emoji']} <b>Trend:</b> {bist['trend_status']}\n"
    if bist['trend_detail']: msg += f"   <i>{bist['trend_detail']}</i>\n"
    msg += f"💪 <b>Trend Gücü (ADX):</b> {bist['adx']:.1f} - {bist['adx_status']}\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📈 <b>TEKNİK GÖSTERGELER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"{bist['rsi_emoji']} <b>RSI:</b> <b>{bist['rsi']:.1f}</b> - {bist['rsi_status']}\n"
    msg += f"{bist['macd_emoji']} <b>MACD:</b> {bist['macd_status']}\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n⚡ <b>MOMENTUM</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"{bist['momentum_emoji']} <b>Yön:</b> {bist['momentum']}\n"
    if bist['momentum_detail']: msg += f"   <i>{bist['momentum_detail']}</i>\n"
    msg += "\n"
    
    fib = bist.get('fibonacci')
    if fib:
        price = bist['price']
        msg += "📐📐📐━━━━━━━━━━━━━━━━━📐📐📐\n"
        msg += "   <b>FİBONACCİ DESTEK/DİRENÇ</b>\n"
        msg += "   <i>Son 90 gün baz alındı</i>\n"
        msg += "📐📐📐━━━━━━━━━━━━━━━━━📐📐📐\n\n"
        
        msg += f"🔺 <b>ZİRVE:</b> {fib['zirve']:.0f}\n\n"
        
        if price < fib['fib_786']:
            msg += f"🔴 <b>Direnç (0.786):</b> {fib['fib_786']:.0f}\n"
        if price < fib['fib_618']:
            msg += f"🔴 <b>Direnç (0.618) Altın Oran:</b> {fib['fib_618']:.0f}\n"
        if price < fib['fib_50']:
            msg += f"🔴 <b>Direnç (0.5):</b> {fib['fib_50']:.0f}\n"
        
        msg += f"\n⚪ <b>ŞU AN:</b> <b>{price:.0f}</b>\n\n"
        
        if price > fib['fib_50']:
            msg += f"🟢 <b>Destek (0.5):</b> {fib['fib_50']:.0f}\n"
        if price > fib['fib_382']:
            msg += f"🟢 <b>Destek (0.382):</b> {fib['fib_382']:.0f}\n"
        if price > fib['fib_236']:
            msg += f"🟢 <b>Destek (0.236):</b> {fib['fib_236']:.0f}\n"
        
        msg += f"\n🟢 <b>DİP:</b> {fib['dip']:.0f}\n\n"
    
    if bist.get('ema_5') and bist.get('ema_22') and bist.get('ema_50'):
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📊 <b>EMA SEVİYELERİ</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        price = bist['price']
        msg += f"{'🟢' if price > bist['ema_5'] else '🔴'} EMA5  : <b>{bist['ema_5']:.0f}</b>\n"
        msg += f"{'🟢' if price > bist['ema_22'] else '🔴'} EMA22 : <b>{bist['ema_22']:.0f}</b>\n"
        msg += f"{'🟢' if price > bist['ema_50'] else '🔴'} EMA50 : <b>{bist['ema_50']:.0f}</b>\n\n"
    
    if bist['yarin_beklenti']:
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n🔮 <b>YARIN İÇİN BEKLENTİ</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for beklenti in bist['yarin_beklenti']:
            msg += f"{beklenti}\n"
        msg += "\n"
    
    msg += "📊📊📊━━━━━━━━━━━━━━━━━📊📊📊\n\n"
    return msg
    # ════════════════════════════════════════════════════════════
# 20/50 KESİŞEN HİSSELER (GERÇEK KESİŞİM - %1 FARK)
# ════════════════════════════════════════════════════════════

def find_20_50_crossovers():
    """Bugün EMA 20/50 GERÇEK yukarı kesişimi olan hisseleri bul"""
    try:
        from database import get_stock_history
        from services.analyzer import analyze_stock
        from services.signal_engine import is_real_20_50_crossover
        import pandas as pd
        
        log_event("🌟 GERÇEK 20/50 kesişimi olan hisseler aranıyor...")
        
        crossovers = []
        
        for symbol in BIST_SYMBOLS:
            try:
                data = get_stock_history(symbol, days=100)
                if not data or len(data) < 30:
                    continue
                
                df = pd.DataFrame(data)
                analysis = analyze_stock(df, timeframe='daily')
                
                if not analysis:
                    continue
                
                e20 = analysis.get('ema_20')
                e50 = analysis.get('ema_50')
                pe20 = analysis.get('prev_ema_20')
                pe50 = analysis.get('prev_ema_50')
                
                if not all(v is not None for v in [e20, e50, pe20, pe50]):
                    continue
                
                is_real, gap = is_real_20_50_crossover(e20, e50, pe20, pe50, min_gap_pct=1.0)
                
                if is_real:
                    current = analysis.get('current_price')
                    volume = analysis.get('volume', 0)
                    prev_close = analysis.get('prev_close', current)
                    daily_change = ((current - prev_close) / prev_close) * 100 if prev_close else 0
                    rvol = analysis.get('rvol', 1)
                    rsi = analysis.get('rsi', 50)
                    
                    volume_tl = current * volume if volume else 0
                    
                    if volume_tl >= 2_000_000:
                        crossovers.append({
                            'symbol': symbol.replace('.IS', ''),
                            'price': current,
                            'ema_20': e20,
                            'ema_50': e50,
                            'gap_pct': gap,
                            'daily_change': daily_change,
                            'rvol': rvol,
                            'rsi': rsi,
                            'volume_tl': volume_tl
                        })
            except:
                continue
        
        crossovers.sort(key=lambda x: (x['gap_pct'], x['rvol']), reverse=True)
        
        log_event(f"🌟 {len(crossovers)} hissede GERÇEK 20/50 kesişimi bulundu")
        return crossovers
    except Exception as e:
        log_event(f"❌ 20/50 tarama hatası: {e}")
        return []


def format_20_50_crossovers_report(crossovers):
    """20/50 kesişen hisseleri formatla"""
    if not crossovers:
        return ""
    
    msg = "🌟🌟🌟━━━━━━━━━━━━━━━━━🌟🌟🌟\n"
    msg += "   ⚡ <b>EMA 20/50 GERÇEK KESİŞİM</b> ⚡\n"
    msg += "   🚀 <b>Bugün oluşan güçlü sinyaller</b>\n"
    msg += "🌟🌟🌟━━━━━━━━━━━━━━━━━🌟🌟🌟\n\n"
    msg += "💎 <i>Sürtünme değil, GERÇEK kesişim!</i>\n"
    msg += "📈 <i>EMA20 ile EMA50 arası fark >= %1</i>\n\n"
    
    for i, c in enumerate(crossovers[:10], 1):
        medal = {1:'🥇', 2:'🥈', 3:'🥉'}.get(i, f"{i}.")
        change_emoji = "🟢" if c['daily_change'] > 0 else "🔴"
        rvol_tag = "🔥🔥" if c['rvol'] > 3 else "🔥" if c['rvol'] > 1.5 else ""
        
        msg += f"{medal} <b>{c['symbol']}</b> {rvol_tag}\n"
        msg += f"   💰 Fiyat: <b>{c['price']:.2f} TL</b> ({change_emoji}%{c['daily_change']:+.2f})\n"
        msg += f"   🌟 EMA20: {c['ema_20']:.2f} > EMA50: {c['ema_50']:.2f}\n"
        msg += f"   📏 Fark: <b>%{c['gap_pct']:.2f}</b> (güçlü)\n"
        msg += f"   📊 RVOL: {c['rvol']:.1f}x | RSI: {c['rsi']:.0f}\n\n"
    
    if len(crossovers) > 10:
        msg += f"<i>+{len(crossovers) - 10} hisse daha aynı sinyalde</i>\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 <b>NOT:</b> Bu hisseler <b>bugün</b> gerçek 20/50 kesişimi yaşadı.\n"
    msg += "⚠️ <i>Yarın açılışta durumlar değişebilir - kontrol et!</i>\n\n"
    
    return msg


# ════════════════════════════════════════════════════════════
# PERFORMANS RAPORU
# ════════════════════════════════════════════════════════════

def format_performance_report():
    """Günlük + haftalık performans raporu formatla"""
    try:
        from database import get_today_signals_summary, get_today_signal_details, get_performance_summary, get_active_signals
        import yfinance as yf
        
        msg = "📈📈📈━━━━━━━━━━━━━━━━━📈📈📈\n"
        msg += "     <b>BOT PERFORMANS RAPORU</b>\n"
        msg += "📈📈📈━━━━━━━━━━━━━━━━━📈📈📈\n\n"
        
        today_summary = get_today_signals_summary()
        today_details = get_today_signal_details()
        
        if today_summary and today_summary.get('total_sent', 0) > 0:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "📋 <b>BUGÜN VERİLEN SİNYALLER</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            msg += f"📊 Toplam sinyal: <b>{today_summary['total_sent']}</b>\n"
            msg += f"📌 Farklı hisse: <b>{today_summary['unique_symbols']}</b>\n"
            msg += f"💯 Ort. skor: <b>{today_summary['avg_score']:.0f}</b>\n"
            msg += f"🏆 En yüksek: <b>{today_summary['max_score']}</b>\n\n"
            
            if today_details:
                msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
                msg += "📊 <b>BUGÜNKÜ SİNYALLERİN DURUMU</b>\n"
                msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                win_count = 0
                loss_count = 0
                total_pnl = 0
                checked = 0
                
                for s in today_details[:10]:
                    symbol = s['symbol']
                    entry_price = s['entry_price']
                    score = s['score']
                    
                    current_price = None
                    try:
                        ticker = yf.Ticker(f"{symbol}.IS")
                        info = ticker.history(period="1d")
                        if not info.empty:
                            current_price = float(info['Close'].iloc[-1])
                    except:
                        pass
                    
                    if current_price and entry_price > 0:
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        total_pnl += pnl_pct
                        checked += 1
                        
                        if pnl_pct > 0:
                            win_count += 1
                            status_emoji = "🟢"
                        elif pnl_pct < -2:
                            loss_count += 1
                            status_emoji = "🔴"
                        else:
                            status_emoji = "🟡"
                        
                        msg += f"{status_emoji} <b>{symbol}</b> ({score}/100)\n"
                        msg += f"   📥 {entry_price:.2f} → 💰 {current_price:.2f} (<b>{pnl_pct:+.2f}%</b>)\n\n"
                    else:
                        msg += f"⚪ <b>{symbol}</b> ({score}/100)\n"
                        msg += f"   📥 {entry_price:.2f} → fiyat alınamadı\n\n"
                
                if checked > 0:
                    avg_pnl = total_pnl / checked
                    win_rate = (win_count / checked) * 100
                    
                    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
                    msg += "📊 <b>BUGÜNKÜ SONUÇ</b>\n"
                    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    msg += f"🟢 Kârlı: <b>{win_count}</b>\n"
                    msg += f"🔴 Zararlı: <b>{loss_count}</b>\n"
                    msg += f"🟡 Nötr: <b>{checked - win_count - loss_count}</b>\n"
                    msg += f"📊 Ortalama: <b>{avg_pnl:+.2f}%</b>\n"
                    msg += f"🎯 Bugünkü başarı: <b>%{win_rate:.0f}</b>\n\n"
        else:
            msg += "📋 <i>Bugün sinyal verilmedi</i>\n\n"
        
        active = get_active_signals()
        if active:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🎯 <b>AKTİF TAKİP ({len(active)} sinyal)</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for s in active[:5]:
                symbol = s['symbol']
                entry = s['entry_price']
                t1 = s['target_1']
                
                current_price = None
                try:
                    ticker = yf.Ticker(f"{symbol}.IS")
                    info = ticker.history(period="1d")
                    if not info.empty:
                        current_price = float(info['Close'].iloc[-1])
                except:
                    pass
                
                if current_price:
                    pnl = ((current_price - entry) / entry) * 100
                    if s.get('target_1_hit'):
                        emoji = "🎯"
                    elif pnl >= 0:
                        emoji = "🟢"
                    else:
                        emoji = "🔴"
                    msg += f"{emoji} <b>{symbol}</b> {entry:.2f}→{current_price:.2f} (<b>{pnl:+.2f}%</b>)\n"
                else:
                    msg += f"⚪ <b>{symbol}</b> {entry:.2f}\n"
            
            if len(active) > 5:
                msg += f"\n<i>+{len(active)-5} sinyal daha aktif takipte</i>\n"
            msg += "\n"
        
        perf = get_performance_summary(days=7)
        if perf and perf.get('total_closed', 0) > 0:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "📊 <b>HAFTALIK PERFORMANS (7 gün)</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            msg += f"📈 Kapanan sinyal: <b>{perf['total_closed']}</b>\n"
            msg += f"🟢 Kârlı: <b>{perf.get('wins', 0)}</b>\n"
            msg += f"🔴 Zararlı: <b>{perf.get('losses', 0)}</b>\n"
            msg += f"🎯 Hedef 1 vurma: <b>{perf.get('t1_hit', 0)}</b>\n"
            msg += f"🎯 Hedef 2 vurma: <b>{perf.get('t2_hit', 0)}</b>\n"
            msg += f"🎯 Hedef 3 vurma: <b>{perf.get('t3_hit', 0)}</b>\n"
            msg += f"🛑 Stop olma: <b>{perf.get('stopped', 0)}</b>\n\n"
            
            msg += f"📊 <b>WIN RATE: %{perf['win_rate']}</b>\n"
            
            avg_pnl = perf.get('avg_pnl')
            if avg_pnl is not None:
                msg += f"💰 Ortalama Kâr/Zarar: <b>{avg_pnl:+.2f}%</b>\n"
            
            best = perf.get('best_trade')
            worst = perf.get('worst_trade')
            if best is not None: msg += f"🏆 En iyi işlem: <b>+{best:.2f}%</b>\n"
            if worst is not None: msg += f"📉 En kötü işlem: <b>{worst:.2f}%</b>\n"
            
            pf = perf.get('profit_factor', 0)
            if pf > 0: msg += f"⚖️ Profit Factor: <b>{pf}</b>\n"
            
            msg += "\n"
        else:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "📊 <b>HAFTALIK</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            msg += "<i>Son 7 günde kapanmış sinyal yok</i>\n\n"
        
        msg += "📈📈📈━━━━━━━━━━━━━━━━━📈📈📈\n\n"
        return msg
    except Exception as e:
        log_event(f"❌ Performans raporu hatası: {e}")
        return "📈 <b>PERFORMANS</b>\n⚠️ Hesaplanamadı\n\n"


# ════════════════════════════════════════════════════════════
# 🆕 HAFTALIK RAPOR (CUMARTESİ 10:00)
# ════════════════════════════════════════════════════════════

def job_weekly_report():
    """
    Haftalık rapor - Cumartesi 10:00'da çalışır
    Son 7 günün tam analizi
    """
    log_event("📊 HAFTALIK RAPOR HAZIRLANIYOR")
    
    try:
        from database import (
            get_performance_summary, 
            get_active_signals, 
            get_connection
        )
        import yfinance as yf
        
        send_message(f"""📊 <b>HAFTALIK RAPOR HAZIRLANIYOR</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
📊 Son 7 gün analiz ediliyor...
<i>1-2 dakika sürebilir</i>""")
        
        # ═══════════════════════════════════════
        # 1. GENEL İSTATİSTİKLER (Son 7 gün)
        # ═══════════════════════════════════════
        conn = get_connection()
        cursor = conn.cursor()
        
        # Bu hafta gönderilen sinyaller
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sent,
                COUNT(DISTINCT symbol) as unique_symbols,
                AVG(score) as avg_score,
                MAX(score) as max_score
            FROM signals
            WHERE created_at >= datetime('now', '-7 days')
        """)
        weekly_signals = dict(cursor.fetchone())
        
        conn.close()
        
        # ═══════════════════════════════════════
        # 2. HAFTALIK PERFORMANS
        # ═══════════════════════════════════════
        perf = get_performance_summary(days=7)
        
        # ═══════════════════════════════════════
        # 3. EN BAŞARILI 5 HİSSE (Son 7 gün)
        # ═══════════════════════════════════════
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                symbol,
                entry_price,
                final_price,
                final_pnl_pct,
                target_1_hit,
                target_2_hit,
                target_3_hit,
                stop_hit
            FROM active_signals
            WHERE created_at >= datetime('now', '-7 days')
            AND status != 'active'
            AND final_pnl_pct > 0
            ORDER BY final_pnl_pct DESC
            LIMIT 5
        """)
        top_winners = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # ═══════════════════════════════════════
        # 4. AKTİF TAKİPTEKİ HİSSELER
        # ═══════════════════════════════════════
        active_signals = get_active_signals()
        
        # ═══════════════════════════════════════
        # 5. PAZARTESİ İZLENECEK (Son 5 gün en yüksek skorlu)
        # ═══════════════════════════════════════
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                symbol,
                MAX(score) as max_score,
                MAX(price) as last_price
            FROM signals
            WHERE created_at >= datetime('now', '-5 days')
            GROUP BY symbol
            ORDER BY MAX(score) DESC
            LIMIT 5
        """)
        monday_watchlist = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # ═══════════════════════════════════════
        # 6. MESAJI OLUŞTUR
        # ═══════════════════════════════════════
        
        # Hafta tarihi
        today = tr_now()
        week_start = today - timedelta(days=7)
        week_str = f"{week_start.strftime('%d %b')} - {today.strftime('%d %b %Y')}"
        
        msg = "📊📊📊━━━━━━━━━━━━━━━━━📊📊📊\n"
        msg += "     <b>🗓️ HAFTALIK BOT RAPORU</b>\n"
        msg += "📊📊📊━━━━━━━━━━━━━━━━━📊📊📊\n\n"
        msg += f"📅 <b>Hafta:</b> {week_str}\n\n"
        
        # GENEL İSTATİSTİKLER
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📈 <b>GENEL İSTATİSTİKLER</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if weekly_signals.get('total_sent'):
            msg += f"📌 Toplam sinyal: <b>{weekly_signals['total_sent']}</b>\n"
            msg += f"📌 Farklı hisse: <b>{weekly_signals['unique_symbols']}</b>\n"
            msg += f"📌 Ort. skor: <b>{weekly_signals.get('avg_score', 0):.0f}</b>\n"
            msg += f"📌 En yüksek: <b>{weekly_signals.get('max_score', 0)}</b>\n\n"
        else:
            msg += "<i>Bu hafta sinyal verilmedi</i>\n\n"
        
        # SONUÇLAR
        if perf and perf.get('total_closed', 0) > 0:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "💰 <b>KAPANAN POZİSYONLAR</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            total_closed = perf['total_closed']
            wins = perf.get('wins', 0)
            losses = perf.get('losses', 0)
            
            msg += f"📊 Kapanan: <b>{total_closed}</b>\n"
            msg += f"🟢 Kazanan: <b>{wins}</b>\n"
            msg += f"🔴 Kaybeden: <b>{losses}</b>\n\n"
            
            msg += f"🎯 Hedef 1: <b>{perf.get('t1_hit', 0)}</b>\n"
            msg += f"🎯 Hedef 2: <b>{perf.get('t2_hit', 0)}</b>\n"
            msg += f"🎯 Hedef 3: <b>{perf.get('t3_hit', 0)}</b>\n"
            msg += f"🛑 Stop: <b>{perf.get('stopped', 0)}</b>\n\n"
            
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "🏆 <b>PERFORMANS</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            win_rate = perf['win_rate']
            
            # Win Rate emoji
            if win_rate >= 70: wr_emoji = "🏆"
            elif win_rate >= 60: wr_emoji = "✅"
            elif win_rate >= 50: wr_emoji = "🟡"
            else: wr_emoji = "🔴"
            
            msg += f"{wr_emoji} <b>WIN RATE: %{win_rate}</b>\n\n"
            
            avg_pnl = perf.get('avg_pnl')
            if avg_pnl is not None:
                pnl_emoji = "🟢" if avg_pnl > 0 else "🔴"
                msg += f"{pnl_emoji} Ortalama K/Z: <b>{avg_pnl:+.2f}%</b>\n"
            
            best = perf.get('best_trade')
            worst = perf.get('worst_trade')
            if best is not None: msg += f"🏆 En iyi: <b>+{best:.2f}%</b>\n"
            if worst is not None: msg += f"📉 En kötü: <b>{worst:.2f}%</b>\n"
            
            pf = perf.get('profit_factor', 0)
            if pf > 0:
                pf_emoji = "💎" if pf >= 2 else "✅" if pf >= 1.5 else "⚠️"
                msg += f"{pf_emoji} Profit Factor: <b>{pf}</b>\n"
            
            msg += "\n"
        else:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "💰 <b>KAPANAN POZİSYONLAR</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            msg += "<i>Bu hafta kapanmış pozisyon yok</i>\n\n"
        
        # EN BAŞARILI HİSSELER
        if top_winners:
            msg += "🏆🏆🏆━━━━━━━━━━━━━━━━━🏆🏆🏆\n"
            msg += "   <b>EN BAŞARILI 5 HİSSE</b>\n"
            msg += "🏆🏆🏆━━━━━━━━━━━━━━━━━🏆🏆🏆\n\n"
            
            for i, w in enumerate(top_winners, 1):
                medal = {1:'🥇', 2:'🥈', 3:'🥉', 4:'🏅', 5:'🎖️'}.get(i, f"{i}.")
                symbol = w['symbol']
                pnl = w['final_pnl_pct']
                entry = w['entry_price']
                exit_p = w['final_price']
                
                # Hangi hedef vuruldu
                if w.get('target_3_hit'):
                    target_info = "🎯 H3 vurdu"
                elif w.get('target_2_hit'):
                    target_info = "🎯 H2 vurdu"
                elif w.get('target_1_hit'):
                    target_info = "🎯 H1 vurdu"
                else:
                    target_info = ""
                
                msg += f"{medal} <b>{symbol}</b> <b>+{pnl:.2f}%</b>\n"
                msg += f"   📥 {entry:.2f} → 💰 {exit_p:.2f}\n"
                if target_info:
                    msg += f"   {target_info}\n"
                msg += "\n"
        
        # AKTİF TAKİPTEKİ HİSSELER
        if active_signals:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"📌 <b>HALA AKTİF TAKİPTE ({len(active_signals)})</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for s in active_signals[:10]:
                symbol = s['symbol']
                entry = s['entry_price']
                t1 = s['target_1']
                t2 = s['target_2']
                stop = s['stop_loss']
                
                current_price = None
                try:
                    ticker = yf.Ticker(f"{symbol}.IS")
                    info = ticker.history(period="1d")
                    if not info.empty:
                        current_price = float(info['Close'].iloc[-1])
                except:
                    pass
                
                if current_price:
                    pnl = ((current_price - entry) / entry) * 100
                    
                    if s.get('target_2_hit'):
                        emoji = "🎯🎯"
                    elif s.get('target_1_hit'):
                        emoji = "🎯"
                    elif pnl >= 3:
                        emoji = "🟢"
                    elif pnl >= 0:
                        emoji = "🟡"
                    else:
                        emoji = "🔴"
                    
                    msg += f"{emoji} <b>{symbol}</b>\n"
                    msg += f"   📥 {entry:.2f} → 💰 {current_price:.2f} (<b>{pnl:+.2f}%</b>)\n"
                    msg += f"   🎯 H1: {t1:.2f} | H2: {t2:.2f} | 🛑 {stop:.2f}\n\n"
                else:
                    msg += f"⚪ <b>{symbol}</b>\n"
                    msg += f"   📥 {entry:.2f} → fiyat alınamadı\n\n"
            
            if len(active_signals) > 10:
                msg += f"<i>+{len(active_signals)-10} sinyal daha aktif</i>\n\n"
        
        # PAZARTESİ İZLENECEK
        if monday_watchlist:
            msg += "🎯🎯🎯━━━━━━━━━━━━━━━━━🎯🎯🎯\n"
            msg += "   <b>PAZARTESİ İZLENECEK 5 HİSSE</b>\n"
            msg += "🎯🎯🎯━━━━━━━━━━━━━━━━━🎯🎯🎯\n\n"
            msg += "📊 <i>Son 5 gün en güçlü sinyal veren hisseler</i>\n\n"
            
            for i, w in enumerate(monday_watchlist, 1):
                medal = {1:'🥇', 2:'🥈', 3:'🥉', 4:'🏅', 5:'🎖️'}.get(i, f"{i}.")
                msg += f"{medal} <b>{w['symbol']}</b> (Skor: {w['max_score']})\n"
                msg += f"   Son fiyat: {w['last_price']:.2f} TL\n\n"
        
        # BOT DEĞERLENDİRMESİ
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📊 <b>BOT DEĞERLENDİRMESİ</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if perf and perf.get('total_closed', 0) > 0:
            win_rate = perf['win_rate']
            avg_pnl = perf.get('avg_pnl', 0)
            pf = perf.get('profit_factor', 0)
            
            if win_rate >= 70 and avg_pnl > 3:
                msg += "🏆 <b>MÜKEMMEL HAFTA!</b>\n"
                msg += "✅ Bot çok iyi performans gösterdi\n"
                msg += "✅ Aynı stratejiyle devam et\n\n"
            elif win_rate >= 60:
                msg += "✅ <b>İYİ HAFTA</b>\n"
                msg += "✅ Ortalama üstü performans\n"
                msg += "✅ Bot sağlıklı çalışıyor\n\n"
            elif win_rate >= 50:
                msg += "🟡 <b>ORTA HAFTA</b>\n"
                msg += "⚠️ Dikkatli takip et\n"
                msg += "⚠️ Piyasa koşullarını değerlendir\n\n"
            else:
                msg += "🔴 <b>ZAYIF HAFTA</b>\n"
                msg += "⚠️ Bot yetersiz performans gösterdi\n"
                msg += "⚠️ Piyasa koşulları zor olabilir\n"
                msg += "⚠️ Küçük pozisyonlarla devam et\n\n"
        else:
            msg += "<i>Değerlendirme için yeterli veri yok</i>\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💡 <i>Pazartesi 09:45'te bot tekrar başlıyor</i>\n"
        msg += "🌅 <i>İyi hafta sonları!</i>\n"
        msg += "💰 <i>Bir sonraki haftaya hazır ol!</i>"
        
        send_message(msg)
        log_event("✅ Haftalık rapor gönderildi")
    except Exception as e:
        log_event(f"❌ Haftalık rapor hatası: {e}")
        send_message(f"❌ <b>Haftalık rapor hatası</b>\n<code>{str(e)[:200]}</code>")
        # ════════════════════════════════════════════════════════════
# GÜN SONU RAPORU
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
        
        # MESAJ 1: BIST 100 (FİBONACCİ)
        bist100 = analyze_bist100()
        msg1 = f"🌆 <b>GÜN SONU RAPORU</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n📅 {tr_now().strftime('%d.%m.%Y - %A')}\n\n"
        msg1 += format_bist100_analysis(bist100)
        send_message(msg1)
        
        # MESAJ 2: PERFORMANS
        perf_msg = format_performance_report()
        send_message(perf_msg)
        
        # MESAJ 3: 20/50 KESİŞEN HİSSELER (GERÇEK KESİŞİM)
        crossovers = find_20_50_crossovers()
        if crossovers:
            crossover_msg = format_20_50_crossovers_report(crossovers)
            if crossover_msg:
                send_message(crossover_msg)
        else:
            send_message("🌟 <b>EMA 20/50 GERÇEK KESİŞİM</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n<i>Bugün gerçek 20/50 yukarı kesişimi olan hisse yok</i>\n<i>(Sürtünmeler filtrelendi)</i>\n\n")
        
        # MESAJ 4: PİYASA + YARIN HİSSELER
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
                    'symbol': symbol.replace('.IS', ''), 'full_symbol': symbol,
                    'price': today_close, 'daily_change': daily_change,
                    'volume': today_volume, 'volume_tl': volume_tl,
                    'rvol': rvol, 'high': today_high, 'low': today_low,
                    'candle_strength': candle_strength, 'green_candle': green_candle,
                    'yesterday_close': yesterday_close
                })
                
                if (green_candle and candle_strength > 60 and rvol >= 1.2 and
                    daily_change > 0 and daily_change < 9.5 and volume_tl > 2_000_000):
                    tomorrow_candidates.append({
                        'symbol': symbol.replace('.IS', ''), 'full_symbol': symbol,
                        'price': today_close, 'daily_change': daily_change,
                        'rvol': rvol, 'candle_strength': candle_strength, 'volume_tl': volume_tl
                    })
            except: continue
        
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
                
                analysis = analyze_stock(df, timeframe='daily')
                if not analysis: continue
                signal = generate_signal(candidate['full_symbol'], analysis, df)
                if not signal: continue
                
                rsi = analysis.get('rsi', 50)
                ema_50 = analysis.get('ema_50')
                current = analysis.get('current_price')
                macd = analysis.get('macd')
                macd_signal_val = analysis.get('macd_signal')
                
                ts = 0; tr_reasons = []
                
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
                if macd and macd_signal_val and macd > macd_signal_val: ts += 10; tr_reasons.append("🚀 MACD pozitif")
                if 3 <= candidate['daily_change'] <= 7: ts += 10; tr_reasons.append(f"📈 Bugün +%{candidate['daily_change']:.1f}")
                elif 1 <= candidate['daily_change'] < 3: ts += 5
                ts += int(signal['score'] * 0.1)
                
                if ts >= 40:
                    tomorrow_signals.append({
                        'symbol': candidate['symbol'], 'price': candidate['price'],
                        'daily_change': candidate['daily_change'], 'rvol': candidate['rvol'],
                        'candle_strength': candidate['candle_strength'], 'tomorrow_score': ts,
                        'reasons': tr_reasons, 'signal_score': signal['score'],
                        'targets': signal.get('targets', {}), 'rsi': rsi
                    })
            except: continue
        
        tomorrow_signals.sort(key=lambda x: x['tomorrow_score'], reverse=True)
        top_5 = tomorrow_signals[:5]
        
        liquid = [m for m in movers_data if m['volume_tl'] > 1_000_000]
        gainers = sorted([m for m in liquid if m['daily_change'] > 0], key=lambda x: x['daily_change'], reverse=True)[:5]
        losers = sorted([m for m in liquid if m['daily_change'] < 0], key=lambda x: x['daily_change'])[:5]
        total_up = len([m for m in movers_data if m['daily_change'] > 0])
        total_down = len([m for m in movers_data if m['daily_change'] < 0])
        
        msg4 = "📊 <b>PİYASA DURUMU</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg4 += f"📈 Yükselen: <b>{total_up}</b>\n📉 Düşen: <b>{total_down}</b>\n"
        
        if total_up > total_down * 1.5: msg4 += "💪 <b>Trend: GÜÇLÜ YUKARI</b> 🚀\n\n"
        elif total_up > total_down: msg4 += "✅ <b>Trend: POZİTİF</b> 📈\n\n"
        elif total_down > total_up * 1.5: msg4 += "⚠️ <b>Trend: GÜÇLÜ AŞAĞI</b> 📉\n\n"
        else: msg4 += "➡️ <b>Trend: YATAY</b>\n\n"
        
        if gainers:
            msg4 += "🏆 <b>EN ÇOK YÜKSELENLER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, g in enumerate(gainers, 1):
                rv = "🔥" if g['rvol'] > 3 else "💪" if g['rvol'] > 1.5 else ""
                msg4 += f"{i}. <b>{g['symbol']}</b> <b>+%{g['daily_change']:.2f}</b> ({g['price']:.2f} TL) {rv}\n"
            msg4 += "\n"
        
        if losers:
            msg4 += "📉 <b>EN ÇOK DÜŞENLER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, l in enumerate(losers, 1):
                msg4 += f"{i}. <b>{l['symbol']}</b> <b>%{l['daily_change']:.2f}</b> ({l['price']:.2f} TL)\n"
            msg4 += "\n"
        
        if top_5:
            msg4 += "⭐⭐⭐━━━━━━━━━━━━━━━━━⭐⭐⭐\n   <b>YARIN İÇİN EN İYİ 5 HİSSE</b>\n⭐⭐⭐━━━━━━━━━━━━━━━━━⭐⭐⭐\n\n"
            msg4 += "🎯 <i>Son kapanış verilerine göre</i>\n\n"
            for i, t in enumerate(top_5, 1):
                medal = {1:'🥇',2:'🥈',3:'🥉',4:'🏅',5:'🎖️'}.get(i, f"{i}.")
                msg4 += f"{medal} <b>{t['symbol']}</b>\n"
                msg4 += f"   💰 Kapanış: <b>{t['price']:.2f} TL</b>\n"
                msg4 += f"   📊 Bugün: <b>+%{t['daily_change']:.2f}</b> | Hacim: {t['rvol']:.1f}x\n"
                msg4 += f"   💪 Mum gücü: %{t['candle_strength']:.0f}\n"
                targets = t.get('targets', {})
                if targets.get('target_1'):
                    msg4 += f"   🎯 Hedef: <b>{targets['target_1']:.2f} TL</b> (+{targets.get('target_1_pct',0)}%)\n"
                if t['reasons']:
                    msg4 += f"   ✅ {' | '.join(t['reasons'][:3])}\n"
                msg4 += "\n"
            msg4 += "━━━━━━━━━━━━━━━━━━━━━━━\n⚠️ <i>Yarın açılışta fiyat kontrol edin!</i>\n⚠️ <i>Gap up varsa dikkatli giriş!</i>\n\n"
        else:
            msg4 += "⭐ <b>YARIN İÇİN ADAY</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n⚠️ <i>Güçlü aday bulunamadı</i>\n\n"
        
        msg4 += "🎯 <b>YARIN STRATEJİ</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        if bist100:
            trend = bist100.get('trend_status', '')
            if trend in ["GÜÇLÜ BOĞA", "BOĞA"]:
                msg4 += "✅ BIST 100 güçlü, AL fırsatlarına odaklan\n✅ Yukarıdaki 5 hisseyi izle\n\n"
            elif trend in ["AYI", "GÜÇLÜ AYI"]:
                msg4 += "⚠️ BIST 100 zayıf, DİKKATLİ ol\n⚠️ Sadece çok güçlü sinyallere gir\n⚠️ Küçük pozisyon aç\n\n"
            else:
                msg4 += "📊 BIST 100 kararsız, seçici ol\n📊 Top 2-3 hisseyi izle\n\n"
        else:
            if total_up > total_down * 1.5: msg4 += "✅ Piyasa güçlü, AL fırsatlarına odaklan\n\n"
            elif total_down > total_up * 1.5: msg4 += "⚠️ Piyasa zayıf, DİKKATLİ ol\n\n"
            else: msg4 += "📊 Karışık piyasa, seçici ol\n\n"
        
        if top_5:
            msg4 += "👀 <b>YARIN İZLE:</b> " + ", ".join([t['symbol'] for t in top_5]) + "\n\n"
        
        msg4 += "━━━━━━━━━━━━━━━━━━━━━━━\n💤 <i>Bot dinlenmeye geçiyor</i>\n🌅 <i>Yarın 09:45'te tekrar!</i>\n💰 <i>İyi kazançlar!</i>"
        
        send_message(msg4)
        log_event("✅ Gün sonu raporu gönderildi")
    except Exception as e:
        log_event(f"❌ Gün sonu hatası: {e}")
        send_message(f"❌ <b>Gün sonu hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# TAM TARAMA + SAATLİK + TAKİP (BİRLEŞİK)
# ════════════════════════════════════════════════════════════

def job_full_scan_with_tracking():
    log_event("🔍 TAM + SAATLİK + TAKİP")
    job_full_scan()
    log_event("⚡ SAATLİK BAŞLATILIYOR...")
    try: job_hourly_scan()
    except Exception as e: log_event(f"⚠️ Saatlik hata: {e}")
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
    scheduler.add_job(job_weekly_report, CronTrigger(hour=10, minute=0, day_of_week='sat'), id='weekly')  # 🆕
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
    print("6→Tam 7→4H Tarama 8→GünSonu 9→Tam+Saatlik+Takip 10→Saatlik 11→HaftalıkRapor")
    
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
    elif c=="11": job_weekly_report()
