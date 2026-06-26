"""
Profesyonel Zamanlayıcı
GÜNLÜK + SAATLİK tarama + Sinyal takip
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

def tr_now():
    return datetime.now(TR_TIMEZONE)

def is_weekday():
    return tr_now().weekday() < 5

def log_event(message):
    timestamp = tr_now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


# ════════════════════════════════════════════════════════════
# SABAH HAZIRLIK (09:45)
# ════════════════════════════════════════════════════════════
def job_morning_preparation():
    log_event("🌅 SABAH HAZIRLIK")
    send_message(f"""🌅 <b>SABAH HAZIRLIK BAŞLADI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
📥 Veriler güncelleniyor...
<i>10-15 dakika sürer</i>""")
    
    if not is_weekday():
        send_message("⏸️ <b>Hafta sonu</b> - Borsa kapalı")
        return
    
    try:
        fetch_all_daily(symbols_list=BIST_SYMBOLS, delay=0.05)
        send_message(f"""✅ <b>SABAH HAZIRLIK TAMAMLANDI</b>
━━━━━━━━━━━━━━━━━━━━━━━
✅ Veriler güncellendi
🚀 Borsa açılışına hazır
⏰ İlk tarama: <b>10:35</b>
<i>Bugün güzel kazançlar dilerim 💪</i>""")
    except Exception as e:
        send_message(f"❌ <b>Sabah hazırlık hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# PRE-MARKET (09:55)
# ════════════════════════════════════════════════════════════
def job_premarket_report():
    log_event("📊 PRE-MARKET")
    send_message(f"""📊 <b>PRE-MARKET TARAMASI</b>
⏰ {tr_now().strftime('%H:%M')}""")
    
    if not is_weekday():
        send_message("⏸️ Hafta sonu")
        return
    
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=False, verbose=False)
        if signals:
            top_5 = signals[:5]
            msg = f"""🌅 <b>PRE-MARKET RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━
📌 <b>Bugün izlenecek hisseler:</b>\n\n"""
            for i, s in enumerate(top_5, 1):
                msg += f"{i}. <b>{s['symbol']}</b> - {s['current_price']:.2f} TL\n"
                msg += f"   {s['emoji']} Skor: {s['score']}/100\n\n"
            msg += "<i>Açılışta takip edeceğim 🚀</i>"
            send_message(msg)
        else:
            send_message(f"""🌅 <b>PRE-MARKET BİTTİ</b>
⚠️ Dikkat çeken hisse yok
<i>Açılış sonrası bakacağım</i>""")
    except Exception as e:
        send_message(f"❌ <b>Pre-market hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# AÇILIŞ TARAMASI (10:35)
# ════════════════════════════════════════════════════════════
def job_market_open_scan():
    log_event("🔔 AÇILIŞ")
    send_message(f"""🔔 <b>BORSA AÇILDI - TARAMA</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M')}
🔍 Tarama başlıyor...""")
    
    if not is_weekday():
        send_message("⏸️ Hafta sonu")
        return
    
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=True, verbose=False)
        
        if not signals:
            send_message(f"""🔔 <b>AÇILIŞ TARAMASI BİTTİ</b>
⚠️ Kriterlere uygun hisse bulunamadı
⏰ {tr_now().strftime('%H:%M')}
<i>11:00'de tekrar tarayacağım</i>""")
            return
        
        send_message(f"""🔔 <b>AÇILIŞ - {len(signals)} SİNYAL!</b>
🔥 Güçlü hisseler radara girdi
📩 Sinyaller geliyor...""")
        
        send_multiple_signals(signals, max_signals=5)
        log_event(f"✅ {len(signals)} sinyal gönderildi")
    except Exception as e:
        send_message(f"❌ <b>Açılış hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# HIZLI TARAMA
# ════════════════════════════════════════════════════════════
def job_quick_scan():
    log_event("⚡ HIZLI TARAMA")
    send_message(f"""⚡ <b>HIZLI TARAMA</b>
⏰ {tr_now().strftime('%H:%M')}""")
    
    try:
        signals = scan_all_stocks(min_score=65, save_to_db=False, verbose=False)
        if not signals:
            send_message(f"""⚡ <b>HIZLI TARAMA BİTTİ</b>
⚠️ Sinyal yok (skor 65+)
⏰ {tr_now().strftime('%H:%M')}""")
            return
        
        send_message(f"""⚡ <b>{len(signals)} SİNYAL!</b>
📩 Gönderiliyor...""")
        send_multiple_signals(signals, max_signals=3)
    except Exception as e:
        send_message(f"❌ <b>Hızlı tarama hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# TAM TARAMA (Her saat başı)
# ════════════════════════════════════════════════════════════
def job_full_scan():
    log_event("🔍 TAM TARAMA")
    send_message(f"""🔍 <b>TAM TARAMA BAŞLADI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M')}
📊 567 hisse taranıyor...""")
    
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=True, verbose=False)
        
        if not signals:
            send_message(f"""🔍 <b>TAM TARAMA BİTTİ</b>
⚠️ Sinyal yok (skor 60+)
⏰ {tr_now().strftime('%H:%M')}
<i>Sonraki saatte tekrar</i>""")
            return
        
        send_message(f"""🔍 <b>{len(signals)} SİNYAL!</b>
🔥 Güçlü hisseler bulundu
📩 Kartlar geliyor...""")
        send_multiple_signals(signals, max_signals=5)
        log_event(f"✅ {len(signals)} sinyal gönderildi")
    except Exception as e:
        send_message(f"❌ <b>Tam tarama hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# YENİ: SAATLİK TARAMA (Gün içi trade)
# ════════════════════════════════════════════════════════════
def job_hourly_scan():
    """
    SAATLİK VERİDEN TARAMA
    Gün içi trade edilebilir hisseleri bulur
    Ayrı kart formatı ile Telegram'a gönderir
    """
    log_event("⚡ SAATLİK TARAMA")
    
    try:
        from telegram_bot.bot import send_hourly_signals
        
        hourly_signals = scan_hourly_stocks(min_score=60, symbols_list=BIST_SYMBOLS[:200])
        
        if hourly_signals:
            log_event(f"⚡ {len(hourly_signals)} saatlik sinyal bulundu")
            send_hourly_signals(hourly_signals, max_signals=3)
        else:
            log_event("⚡ Saatlik sinyal yok")
    except Exception as e:
        log_event(f"❌ Saatlik tarama hatası: {e}")


# ════════════════════════════════════════════════════════════
# STRATEJİ TARAMASI (14:00)
# ════════════════════════════════════════════════════════════
def job_strategy_scan():
    log_event("💎 STRATEJİ")
    send_message(f"""💎 <b>STRATEJİ TARAMASI</b>
⏰ {tr_now().strftime('%H:%M')}
🔍 Momentum + Kırılım...""")
    
    try:
        momentum_signals = scan_momentum_strategy(min_score=65)
        breakout_signals = scan_breakout_strategy(min_score=65)
        
        msg = f"""💎 <b>STRATEJİ TARAMASI BİTTİ</b>
⏰ {tr_now().strftime('%H:%M')}
🚀 Momentum: {len(momentum_signals)} hisse
💥 Kırılım: {len(breakout_signals)} hisse\n\n"""
        
        if momentum_signals:
            msg += "📈 <b>EN İYİ MOMENTUM:</b>\n"
            for s in momentum_signals[:3]:
                msg += f"   • <b>{s['symbol']}</b> - {s['current_price']:.2f} TL ({s['score']}/100)\n"
            msg += "\n"
        if breakout_signals:
            msg += "💥 <b>EN İYİ KIRILIM:</b>\n"
            for s in breakout_signals[:3]:
                msg += f"   • <b>{s['symbol']}</b> - {s['current_price']:.2f} TL ({s['score']}/100)\n"
        if not momentum_signals and not breakout_signals:
            msg += "⚠️ <i>Strateji koşullarına uyan hisse yok</i>"
        
        send_message(msg)
        
        all_strong = [s for s in momentum_signals + breakout_signals if s['score'] >= 75]
        if all_strong:
            send_message(f"🔥 <b>{len(all_strong)} GÜÇLÜ STRATEJİ SİNYALİ:</b>")
            send_multiple_signals(all_strong[:3], max_signals=3)
    except Exception as e:
        send_message(f"❌ <b>Strateji hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# GÜN SONU RAPORU (18:30)
# ════════════════════════════════════════════════════════════
def job_end_of_day_report():
    log_event("🌆 GÜN SONU - DETAYLI RAPOR")
    
    try:
        import yfinance as yf
        
        send_message(f"""🌆 <b>GÜN SONU RAPORU HAZIRLANIYOR</b>
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
📊 Piyasa analiz ediliyor...""")
        
        movers_data = []
        success_count = 0
        
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
                
                daily_change = ((today_close - yesterday_close) / yesterday_close) * 100
                avg_volume = hist['Volume'].mean()
                rvol = today_volume / avg_volume if avg_volume > 0 else 0
                volume_tl = today_close * today_volume
                
                movers_data.append({
                    'symbol': symbol.replace('.IS', ''), 'price': today_close,
                    'daily_change': daily_change, 'volume': today_volume,
                    'volume_tl': volume_tl, 'rvol': rvol,
                    'high': today_high, 'low': today_low,
                    'yesterday_close': yesterday_close
                })
                success_count += 1
            except: continue
        
        liquid_movers = [m for m in movers_data if m['volume_tl'] > 1_000_000]
        gainers = sorted([m for m in liquid_movers if m['daily_change'] > 0], key=lambda x: x['daily_change'], reverse=True)[:5]
        losers = sorted([m for m in liquid_movers if m['daily_change'] < 0], key=lambda x: x['daily_change'])[:5]
        volume_explosions = sorted([m for m in liquid_movers if m['rvol'] > 2 and m['daily_change'] > 0], key=lambda x: x['rvol'], reverse=True)[:5]
        tavan_candidates = sorted([m for m in liquid_movers if m['daily_change'] > 5 and m['rvol'] > 1.5], key=lambda x: x['daily_change'], reverse=True)[:5]
        
        total_up = len([m for m in movers_data if m['daily_change'] > 0])
        total_down = len([m for m in movers_data if m['daily_change'] < 0])
        
        msg = f"""🌆 <b>GÜN SONU RAPORU - DETAYLI</b>
━━━━━━━━━━━━━━━━━━━━━━━
📅 {tr_now().strftime('%d.%m.%Y - %A')}
📊 {success_count} hisse analiz edildi

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
                rvol_emoji = "🔥" if g['rvol'] > 3 else "💪" if g['rvol'] > 1.5 else ""
                msg += f"{i}. <b>{g['symbol']}</b> <b>+%{g['daily_change']:.2f}</b> ({g['price']:.2f} TL) {rvol_emoji}\n"
                if g['rvol'] > 1.5: msg += f"   📊 Hacim: {g['rvol']:.1f}x\n"
            msg += "\n"
        
        if tavan_candidates:
            msg += "⚡ <b>TAVAN ADAYLARI</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, t in enumerate(tavan_candidates, 1):
                msg += f"{i}. <b>{t['symbol']}</b> ⚡ <b>+%{t['daily_change']:.2f}</b> ({t['price']:.2f} TL)\n"
            msg += "\n"
        
        if losers:
            msg += "📉 <b>EN ÇOK DÜŞENLER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, l in enumerate(losers, 1):
                msg += f"{i}. <b>{l['symbol']}</b> <b>%{l['daily_change']:.2f}</b> ({l['price']:.2f} TL)\n"
            msg += "\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n💤 <i>Bot dinlenmeye geçiyor</i>\n🌅 <i>Yarın 09:45'te tekrar!</i>"
        
        send_message(msg)
    except Exception as e:
        send_message(f"❌ <b>Gün sonu hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# TAM TARAMA + SAATLİK + SİNYAL TAKİP (BİRLEŞİK)
# ════════════════════════════════════════════════════════════
def job_full_scan_with_tracking():
    """
    Her saat başı:
    1. Günlük tam tarama (SWING sinyalleri)
    2. Saatlik tarama (GÜN İÇİ sinyalleri)
    3. Sinyal takip
    """
    log_event("🔍 TAM TARAMA + SAATLİK + SİNYAL TAKİP")
    
    # 1. GÜNLÜK TAM TARAMA
    job_full_scan()
    
    # 2. SAATLİK TARAMA (YENİ!)
    log_event("⚡ SAATLİK TARAMA BAŞLATILIYOR...")
    try:
        job_hourly_scan()
    except Exception as e:
        log_event(f"⚠️ Saatlik tarama hatası: {e}")
    
    # 3. SİNYAL TAKİP
    log_event("🎯 SİNYAL TAKİP BAŞLATILIYOR...")
    try:
        from services.signal_tracker import track_signals_job
        track_signals_job()
    except Exception as e:
        send_message(f"❌ <b>Sinyal takip hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# ZAMANLAYICI
# ════════════════════════════════════════════════════════════
def setup_scheduler():
    scheduler = BlockingScheduler(timezone='Europe/Istanbul')
    scheduler.add_job(job_morning_preparation, CronTrigger(hour=9, minute=45, day_of_week='mon-fri'), id='morning_prep')
    scheduler.add_job(job_premarket_report, CronTrigger(hour=9, minute=55, day_of_week='mon-fri'), id='premarket')
    scheduler.add_job(job_market_open_scan, CronTrigger(hour=10, minute=35, day_of_week='mon-fri'), id='market_open')
    scheduler.add_job(job_quick_scan, CronTrigger(minute='30,45', hour='10-17', day_of_week='mon-fri'), id='quick_scan')
    scheduler.add_job(job_full_scan, CronTrigger(minute=0, hour='11-17', day_of_week='mon-fri'), id='full_scan')
    scheduler.add_job(job_strategy_scan, CronTrigger(hour=14, minute=0, day_of_week='mon-fri'), id='strategy')
    scheduler.add_job(job_end_of_day_report, CronTrigger(hour=18, minute=30, day_of_week='mon-fri'), id='eod')
    return scheduler

def start_scheduler():
    scheduler = setup_scheduler()
    try:
        send_message(f"""🤖 <b>BOT AKTİF</b>
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}""")
    except: pass
    try: scheduler.start()
    except (KeyboardInterrupt, SystemExit): print("⏹️ Durduruldu")


if __name__ == "__main__":
    print(f"\n⏰ ZAMANLAYICI MENÜ - {tr_now().strftime('%H:%M')}")
    print("1 → Başlat")
    print("2 → Sabah test")
    print("3 → Pre-market")
    print("4 → Açılış")
    print("5 → Hızlı tarama")
    print("6 → Tam tarama")
    print("7 → Strateji")
    print("8 → Gün sonu")
    print("9 → Tam + Saatlik + Takip")
    print("10 → Sadece Saatlik tarama")
    
    choice = input("\nSeçim: ").strip()
    
    if choice == "1": start_scheduler()
    elif choice == "2": job_morning_preparation()
    elif choice == "3": job_premarket_report()
    elif choice == "4": job_market_open_scan()
    elif choice == "5": job_quick_scan()
    elif choice == "6": job_full_scan()
    elif choice == "7": job_strategy_scan()
    elif choice == "8": job_end_of_day_report()
    elif choice == "9": job_full_scan_with_tracking()
    elif choice == "10": job_hourly_scan()
