"""
Profesyonel Otomatik Zamanlayıcı - 7/24 Çalışma Sistemi
Her durumda mesaj gönderir
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, time as dt_time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BIST_SYMBOLS
from database import get_connection
from services.data_fetcher import fetch_all_daily, fetch_all_15m
from services.scanner import (
    scan_all_stocks, 
    filter_new_signals,
    scan_momentum_strategy,
    scan_breakout_strategy
)
from telegram_bot.bot import send_message, send_multiple_signals


def is_weekday():
    return datetime.now().weekday() < 5


def is_market_open():
    return True


def log_event(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


# ════════════════════════════════════════════════════════════
# JOB FONKSİYONLARI - HER DURUMDA MESAJ GÖNDERİR
# ════════════════════════════════════════════════════════════

def job_morning_preparation():
    log_event("🌅 SABAH HAZIRLIK")
    
    send_message(f"""🌅 <b>SABAH HAZIRLIK BAŞLADI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}
📥 Veriler güncelleniyor...

<i>Bu işlem 10-12 dakika sürer</i>""")
    
    if not is_weekday():
        send_message("⏸️ <b>Hafta sonu</b> - Borsa kapalı")
        return
    
    try:
        fetch_all_daily(symbols_list=BIST_SYMBOLS, delay=0.05)
        send_message(f"""✅ <b>SABAH HAZIRLIK TAMAMLANDI</b>
━━━━━━━━━━━━━━━━━━━━━━━
✅ Günlük veriler güncellendi
🚀 Borsa açılışına hazır
⏰ İlk tarama: <b>10:15</b>

<i>Bugün güzel kazançlar dilerim 💪</i>""")
    except Exception as e:
        send_message(f"❌ <b>Sabah hazırlık hatası</b>\n<code>{str(e)[:200]}</code>")


def job_premarket_report():
    log_event("📊 PRE-MARKET")
    
    send_message(f"""📊 <b>PRE-MARKET TARAMASI BAŞLADI</b>
⏰ {datetime.now().strftime('%H:%M')}""")
    
    if not is_weekday():
        send_message("⏸️ Hafta sonu - atlandı")
        return
    
    try:
        signals = scan_all_stocks(min_score=65, save_to_db=False, verbose=False)
        
        if signals:
            top_5 = signals[:5]
            msg = f"""🌅 <b>PRE-MARKET RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>Bugün izlenecek hisseler:</b>

"""
            for i, s in enumerate(top_5, 1):
                msg += f"{i}. <b>{s['symbol']}</b> - {s['current_price']:.2f} TL\n"
                msg += f"   {s['emoji']} Skor: {s['score']}/100\n\n"
            send_message(msg)
        else:
            send_message(f"""🌅 <b>PRE-MARKET BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 Tarama tamamlandı
⚠️ Şu an dikkat çeken hisse yok
⏰ {datetime.now().strftime('%H:%M')}""")
    except Exception as e:
        send_message(f"❌ <b>Pre-market hatası</b>\n<code>{str(e)[:200]}</code>")


def job_market_open_scan():
    log_event("🔔 AÇILIŞ")
    
    send_message(f"""🔔 <b>BORSA AÇILDI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M')}
🔍 İlk tarama başlıyor...""")
    
    if not is_weekday():
        send_message("⏸️ Hafta sonu")
        return
    
    try:
        fetch_all_15m(symbols_list=BIST_SYMBOLS[:100], delay=0.1)
        signals = scan_all_stocks(min_score=65, save_to_db=True, verbose=False)
        
        if not signals:
            send_message(f"""🔔 <b>AÇILIŞ TARAMASI BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 567 hisse tarandı
⚠️ Şu an güçlü sinyal yok
⏰ {datetime.now().strftime('%H:%M')}""")
            return
        
        new_signals = filter_new_signals(signals, hours=0)  # 0 = spam koruması yok
        
        if not new_signals:
            send_message(f"📊 {len(signals)} sinyal var (zaten gönderildi)")
            return
        
        send_message(f"🔔 <b>AÇILIŞ - {len(new_signals)} SİNYAL!</b>")
        send_multiple_signals(new_signals, max_signals=5)
    except Exception as e:
        send_message(f"❌ <b>Açılış hatası</b>\n<code>{str(e)[:200]}</code>")


def job_quick_scan():
    log_event("⚡ HIZLI TARAMA")
    
    send_message(f"""⚡ <b>HIZLI TARAMA BAŞLADI</b>
⏰ {datetime.now().strftime('%H:%M')}""")
    
    try:
        signals = scan_all_stocks(min_score=70, save_to_db=False, verbose=False)
        
        if not signals:
            send_message(f"""⚡ <b>HIZLI TARAMA BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 Tarama tamamlandı
⚠️ Şu an güçlü sinyal yok (skor 70+)
⏰ {datetime.now().strftime('%H:%M')}

<i>Sonraki taramayı bekleyin</i>""")
            return
        
        new_signals = filter_new_signals(signals, hours=0)  # 0 = spam koruması yok
        
        if not new_signals:
            send_message(f"""⚡ <b>HIZLI TARAMA BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 {len(signals)} sinyal var (zaten gönderildi)
⏰ {datetime.now().strftime('%H:%M')}""")
            return
        
        send_message(f"""⚡ <b>{len(new_signals)} YENİ SİNYAL!</b>
📩 Sinyaller geliyor...""")
        send_multiple_signals(new_signals, max_signals=3)
    except Exception as e:
        send_message(f"❌ <b>Hızlı tarama hatası</b>\n<code>{str(e)[:200]}</code>")


def job_full_scan():
    log_event("🔍 TAM TARAMA")
    
    send_message(f"""🔍 <b>TAM TARAMA BAŞLADI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M')}
📊 567 hisse taranıyor...

<i>Bu işlem birkaç dakika sürer</i>""")
    
    try:
        signals = scan_all_stocks(min_score=65, save_to_db=True, verbose=False)
        
        if not signals:
            send_message(f"""🔍 <b>TAM TARAMA BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 567 hisse tarandı
⚠️ Şu an güçlü sinyal yok (skor 65+)
⏰ {datetime.now().strftime('%H:%M')}

<i>Sonraki taramayı bekleyin</i>""")
            return
        
        new_signals = filter_new_signals(signals, hours=0)  # 0 = spam koruması yok
        
        if not new_signals:
            send_message(f"""🔍 <b>TAM TARAMA BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 {len(signals)} sinyal var (zaten gönderildi)
⏰ {datetime.now().strftime('%H:%M')}""")
            return
        
        send_message(f"""🔍 <b>{len(new_signals)} YENİ SİNYAL!</b>
🔥 Güçlü sinyaller bulundu
📩 Sinyaller geliyor...""")
        send_multiple_signals(new_signals, max_signals=5)
    except Exception as e:
        send_message(f"❌ <b>Tam tarama hatası</b>\n<code>{str(e)[:200]}</code>")


def job_strategy_scan():
    log_event("💎 STRATEJİ")
    
    send_message(f"""💎 <b>STRATEJİ TARAMASI BAŞLADI</b>
⏰ {datetime.now().strftime('%H:%M')}""")
    
    try:
        momentum_signals = scan_momentum_strategy(min_score=70)
        breakout_signals = scan_breakout_strategy(min_score=70)
        
        msg = f"""💎 <b>STRATEJİ TARAMASI BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M')}

🚀 <b>Momentum:</b> {len(momentum_signals)} hisse
💥 <b>Kırılım:</b> {len(breakout_signals)} hisse

"""
        if momentum_signals:
            msg += "📈 <b>EN İYİ MOMENTUM:</b>\n"
            for s in momentum_signals[:3]:
                msg += f"   • <b>{s['symbol']}</b> ({s['score']}/100)\n"
            msg += "\n"
        
        if breakout_signals:
            msg += "💥 <b>EN İYİ KIRILIM:</b>\n"
            for s in breakout_signals[:3]:
                msg += f"   • <b>{s['symbol']}</b> ({s['score']}/100)\n"
        
        if not momentum_signals and not breakout_signals:
            msg += "⚠️ <i>Strateji koşullarına uyan hisse yok</i>"
        
        send_message(msg)
        
        all_strong = [s for s in momentum_signals + breakout_signals if s['score'] >= 80]
        if all_strong:
            new = filter_new_signals(all_strong, hours=6)
            if new:
                send_message(f"🔥 <b>{len(new)} EN GÜÇLÜ STRATEJİ SİNYALİ:</b>")
                send_multiple_signals(new[:3], max_signals=3)
    except Exception as e:
        send_message(f"❌ <b>Strateji hatası</b>\n<code>{str(e)[:200]}</code>")


def job_end_of_day_report():
    log_event("🌆 GÜN SONU")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total, AVG(score) as avg_score, MAX(score) as max_score FROM signals WHERE date(created_at) = date('now')")
        result = cursor.fetchone()
        
        cursor.execute("SELECT symbol, score, price FROM signals WHERE date(created_at) = date('now') ORDER BY score DESC LIMIT 5")
        top_signals = cursor.fetchall()
        
        conn.close()
        
        total = (result['total'] if result and result['total'] else 0)
        avg_score = (result['avg_score'] if result and result['avg_score'] else 0)
        max_score = (result['max_score'] if result and result['max_score'] else 0)
        
        msg = f"""🌆 <b>GÜN SONU RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime('%d.%m.%Y - %A')}

📊 <b>İSTATİSTİKLER</b>
   Toplam Sinyal : <b>{total}</b>
   Ortalama Skor : <b>{avg_score:.0f}/100</b>
   En Yüksek     : <b>{max_score}/100</b>

"""
        if top_signals:
            msg += "🏆 <b>BUGÜNÜN EN İYİLERİ</b>\n"
            for i, sig in enumerate(top_signals, 1):
                msg += f"   {i}. <b>{sig['symbol']}</b> - {sig['price']:.2f} TL ({sig['score']}/100)\n"
        else:
            msg += "ℹ️ <i>Bugün kayıtlı sinyal yok</i>\n"
        
        msg += """
━━━━━━━━━━━━━━━━━━━━━━━
💤 <i>Bot dinlenmeye geçiyor</i>
🌅 <i>Yarın 09:45'te tekrar!</i>"""
        
        send_message(msg)
    except Exception as e:
        send_message(f"❌ <b>Gün sonu hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# ZAMANLAYICI
# ════════════════════════════════════════════════════════════

def setup_scheduler():
    scheduler = BlockingScheduler(timezone='Europe/Istanbul')
    scheduler.add_job(job_morning_preparation, CronTrigger(hour=9, minute=45, day_of_week='mon-fri'), id='morning_prep')
    scheduler.add_job(job_premarket_report, CronTrigger(hour=9, minute=55, day_of_week='mon-fri'), id='premarket')
    scheduler.add_job(job_market_open_scan, CronTrigger(hour=10, minute=15, day_of_week='mon-fri'), id='market_open')
    scheduler.add_job(job_quick_scan, CronTrigger(minute='30,45', hour='10-17', day_of_week='mon-fri'), id='quick_scan')
    scheduler.add_job(job_full_scan, CronTrigger(minute=0, hour='11-17', day_of_week='mon-fri'), id='full_scan')
    scheduler.add_job(job_strategy_scan, CronTrigger(hour=14, minute=0, day_of_week='mon-fri'), id='strategy')
    scheduler.add_job(job_end_of_day_report, CronTrigger(hour=18, minute=15, day_of_week='mon-fri'), id='eod')
    return scheduler


def start_scheduler():
    print("⏰ ZAMANLAYICI")
    scheduler = setup_scheduler()
    
    try:
        send_message(f"""🤖 <b>BOT AKTİF</b>
⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}""")
    except:
        pass
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("⏹️ Durduruldu")


if __name__ == "__main__":
    print("\n⏰ ZAMANLAYICI MENÜ")
    print("1 → Başlat")
    print("2 → Sabah test")
    print("3 → Pre-market test")
    print("4 → Açılış test")
    print("5 → Hızlı tarama test")
    print("6 → Tam tarama test")
    print("7 → Strateji test")
    print("8 → Gün sonu test")
    
    choice = input("\nSeçim: ").strip()
    
    if choice == "1": start_scheduler()
    elif choice == "2": job_morning_preparation()
    elif choice == "3": job_premarket_report()
    elif choice == "4": job_market_open_scan()
    elif choice == "5": job_quick_scan()
    elif choice == "6": job_full_scan()
    elif choice == "7": job_strategy_scan()
    elif choice == "8": job_end_of_day_report()
