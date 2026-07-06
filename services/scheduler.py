"""
Profesyonel Zamanlayıcı
GÜNLÜK + SAATLİK tarama + Sinyal takip + Detaylı Gün Sonu
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
    filter_new_signals,
    scan_momentum_strategy,
    scan_breakout_strategy
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


def job_strategy_scan():
    log_event("💎 STRATEJİ")
    send_message(f"💎 <b>STRATEJİ TARAMASI</b>\n⏰ {tr_now().strftime('%H:%M')}")
    try:
        momentum = scan_momentum_strategy(min_score=65)
        breakout = scan_breakout_strategy(min_score=65)
        msg = f"💎 <b>STRATEJİ BİTTİ</b>\n🚀 Momentum: {len(momentum)}\n💥 Kırılım: {len(breakout)}\n\n"
        if momentum:
            msg += "📈 <b>MOMENTUM:</b>\n"
            for s in momentum[:3]:
                msg += f"   • <b>{s['symbol']}</b> ({s['score']}/100)\n"
            msg += "\n"
        if breakout:
            msg += "💥 <b>KIRILIM:</b>\n"
            for s in breakout[:3]:
                msg += f"   • <b>{s['symbol']}</b> ({s['score']}/100)\n"
        if not momentum and not breakout: msg += "⚠️ <i>Strateji koşullarına uyan yok</i>"
        send_message(msg)
        strong = [s for s in momentum + breakout if s['score'] >= 75]
        if strong:
            send_message(f"🔥 <b>{len(strong)} GÜÇLÜ STRATEJİ:</b>")
            send_multiple_signals(strong[:3], max_signals=3)
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# GÜN SONU RAPORU (18:30) - YARIN İÇİN 5 HİSSE DAHİL
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
        
        # 1. TÜM HİSSELER
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
                
                # YARIN İÇİN ADAY MI?
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
        
        # 2. YARIN ADAYLARINI DETAYLI ANALİZ
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
                
                # YARINKI POTANSİYEL SKORU
                ts = 0
                tr_reasons = []
                
                # Güçlü kapanış
                if candidate['candle_strength'] > 80: ts += 25; tr_reasons.append("💪 Çok güçlü kapanış")
                elif candidate['candle_strength'] > 60: ts += 15; tr_reasons.append("📈 Güçlü kapanış")
                
                # Hacim
                if candidate['rvol'] >= 2: ts += 20; tr_reasons.append(f"💥 Hacim {candidate['rvol']:.1f}x")
                elif candidate['rvol'] >= 1.5: ts += 12; tr_reasons.append(f"📊 Hacim {candidate['rvol']:.1f}x")
                elif candidate['rvol'] >= 1.2: ts += 5
                
                # RSI
                if 50 <= rsi <= 65: ts += 15; tr_reasons.append(f"⚡ RSI {rsi:.0f} (ideal)")
                elif 45 <= rsi < 50: ts += 10
                elif rsi > 70: ts -= 10; tr_reasons.append(f"⚠️ RSI {rsi:.0f} (yüksek)")
                
                # EMA50
                if current and ema_50 and current > ema_50: ts += 15; tr_reasons.append("📈 EMA50 üstünde")
                elif current and ema_50 and current < ema_50: ts -= 5
                
                # MACD
                if macd and macd_signal and macd > macd_signal: ts += 10; tr_reasons.append("🚀 MACD pozitif")
                
                # Bugünkü yükseliş
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
        
        # 3. İSTATİSTİKLER
        liquid = [m for m in movers_data if m['volume_tl'] > 1_000_000]
        gainers = sorted([m for m in liquid if m['daily_change'] > 0], key=lambda x: x['daily_change'], reverse=True)[:5]
        losers = sorted([m for m in liquid if m['daily_change'] < 0], key=lambda x: x['daily_change'])[:5]
        total_up = len([m for m in movers_data if m['daily_change'] > 0])
        total_down = len([m for m in movers_data if m['daily_change'] < 0])
        
        # 4. RAPOR
        msg = f"""🌆 <b>GÜN SONU RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━
📅 {tr_now().strftime('%d.%m.%Y - %A')}

📊 <b>PİYASA DURUMU</b>
━━━━━━━━━━━━━━━━━━━━━━━
📈 Yükselen: <b>{total_up}</b>
📉 Düşen: <b>{total_down}</b>\n"""
        
        if total_up > total_down * 1.5: msg += "💪 <b>Trend: GÜÇLÜ YUKARI</b> 🚀\n\n"
        elif total_up > total_down: msg += "✅ <b>Trend: POZİTİF</b> 📈\n\n"
        elif total_down > total_up * 1.5: msg += "⚠️ <b>Trend: GÜÇLÜ AŞAĞI</b> 📉\n\n"
        else: msg += "➡️ <b>Trend: YATAY</b>\n\n"
        
        if gainers:
            msg += "🏆 <b>EN ÇOK YÜKSELENLER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, g in enumerate(gainers, 1):
                rv = "🔥" if g['rvol'] > 3 else "💪" if g['rvol'] > 1.5 else ""
                msg += f"{i}. <b>{g['symbol']}</b> <b>+%{g['daily_change']:.2f}</b> ({g['price']:.2f} TL) {rv}\n"
            msg += "\n"
        
        if losers:
            msg += "📉 <b>EN ÇOK DÜŞENLER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, l in enumerate(losers, 1):
                msg += f"{i}. <b>{l['symbol']}</b> <b>%{l['daily_change']:.2f}</b> ({l['price']:.2f} TL)\n"
            msg += "\n"
        
        # ⭐ YARIN İÇİN EN İYİ 5 HİSSE
        if top_5:
            msg += "⭐⭐⭐━━━━━━━━━━━━━━━━━⭐⭐⭐\n"
            msg += "   <b>YARIN İÇİN EN İYİ 5 HİSSE</b>\n"
            msg += "⭐⭐⭐━━━━━━━━━━━━━━━━━⭐⭐⭐\n\n"
            msg += "🎯 <i>Son kapanış verilerine göre</i>\n\n"
            
            for i, t in enumerate(top_5, 1):
                medal = {1:'🥇',2:'🥈',3:'🥉',4:'🏅',5:'🎖️'}.get(i, f"{i}.")
                msg += f"{medal} <b>{t['symbol']}</b>\n"
                msg += f"   💰 Kapanış: <b>{t['price']:.2f} TL</b>\n"
                msg += f"   📊 Bugün: <b>+%{t['daily_change']:.2f}</b> | Hacim: {t['rvol']:.1f}x\n"
                msg += f"   💪 Mum gücü: %{t['candle_strength']:.0f}\n"
                
                targets = t.get('targets', {})
                if targets.get('target_1'):
                    msg += f"   🎯 Hedef: <b>{targets['target_1']:.2f} TL</b> (+{targets.get('target_1_pct',0)}%)\n"
                
                if t['reasons']:
                    msg += f"   ✅ {' | '.join(t['reasons'][:3])}\n"
                msg += "\n"
            
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "⚠️ <i>Yarın açılışta fiyat kontrol edin!</i>\n"
            msg += "⚠️ <i>Gap up varsa dikkatli giriş!</i>\n\n"
        else:
            msg += "⭐ <b>YARIN İÇİN ADAY</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "⚠️ <i>Güçlü aday bulunamadı</i>\n\n"
        
        # STRATEJİ
        msg += "🎯 <b>YARIN STRATEJİ</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        if total_up > total_down * 1.5:
            msg += "✅ Piyasa güçlü, AL fırsatlarına odaklan\n✅ Yukarıdaki 5 hisseyi izle\n\n"
        elif total_down > total_up * 1.5:
            msg += "⚠️ Piyasa zayıf, DİKKATLİ ol\n⚠️ Sadece çok güçlü sinyallere gir\n\n"
        else:
            msg += "📊 Karışık piyasa, seçici ol\n📊 Top 2-3 hisseyi izle\n\n"
        
        if top_5:
            msg += "👀 <b>YARIN İZLE:</b> " + ", ".join([t['symbol'] for t in top_5]) + "\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n💤 <i>Bot dinlenmeye geçiyor</i>\n🌅 <i>Yarın 09:45'te tekrar!</i>\n💰 <i>İyi kazançlar!</i>"
        
        send_message(msg)
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
    scheduler.add_job(job_strategy_scan, CronTrigger(hour=14, minute=0, day_of_week='mon-fri'), id='strategy')
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
    print("6→Tam 7→Strateji 8→GünSonu 9→Tam+Saatlik+Takip 10→Saatlik")
    
    c = input("\nSeçim: ").strip()
    if c=="1": start_scheduler()
    elif c=="2": job_morning_preparation()
    elif c=="3": job_premarket_report()
    elif c=="4": job_market_open_scan()
    elif c=="5": job_quick_scan()
    elif c=="6": job_full_scan()
    elif c=="7": job_strategy_scan()
    elif c=="8": job_end_of_day_report()
    elif c=="9": job_full_scan_with_tracking()
    elif c=="10": job_hourly_scan()
