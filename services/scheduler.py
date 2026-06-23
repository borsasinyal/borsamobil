"""
Profesyonel Otomatik Zamanlayıcı - 7/24 Çalışma Sistemi
SWING TRADE optimized + TR Timezone + Sinyal Takip Birleştirilmiş
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
    filter_new_signals,
    scan_momentum_strategy,
    scan_breakout_strategy
)
from telegram_bot.bot import send_message, send_multiple_signals


# ════════════════════════════════════════════════════════════
# TÜRKİYE SAATİ (TIMEZONE FIX)
# ════════════════════════════════════════════════════════════

TR_TIMEZONE = timezone(timedelta(hours=3))

def tr_now():
    """Türkiye saatini döndür (UTC+3)"""
    return datetime.now(TR_TIMEZONE)


def is_weekday():
    """Türkiye saatine göre hafta içi mi?"""
    return tr_now().weekday() < 5


def is_market_open():
    return True


def log_event(message):
    """Türkiye saati ile log yaz"""
    timestamp = tr_now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


# ════════════════════════════════════════════════════════════
# 🌅 SABAH HAZIRLIK (09:45)
# ════════════════════════════════════════════════════════════
def job_morning_preparation():
    log_event("🌅 SABAH HAZIRLIK")
    
    send_message(f"""🌅 <b>SABAH HAZIRLIK BAŞLADI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
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


# ════════════════════════════════════════════════════════════
# 📊 PRE-MARKET (09:55)
# ════════════════════════════════════════════════════════════
def job_premarket_report():
    log_event("📊 PRE-MARKET")
    
    send_message(f"""📊 <b>PRE-MARKET TARAMASI BAŞLADI</b>
⏰ {tr_now().strftime('%H:%M')}""")
    
    if not is_weekday():
        send_message("⏸️ Hafta sonu - atlandı")
        return
    
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=False, verbose=False)
        
        if signals:
            top_5 = signals[:5]
            msg = f"""🌅 <b>PRE-MARKET RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>Bugün izlenecek hisseler:</b>

"""
            for i, s in enumerate(top_5, 1):
                msg += f"{i}. <b>{s['symbol']}</b> - {s['current_price']:.2f} TL\n"
                msg += f"   {s['emoji']} Skor: {s['score']}/100\n\n"
            
            msg += "<i>Açılışta hareketleri takip edeceğim 🚀</i>"
            send_message(msg)
        else:
            send_message(f"""🌅 <b>PRE-MARKET BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 Tarama tamamlandı
⚠️ Şu an dikkat çeken hisse yok
⏰ {tr_now().strftime('%H:%M')}

<i>Açılış sonrası tekrar bakacağım</i>""")
    except Exception as e:
        send_message(f"❌ <b>Pre-market hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# 🔔 AÇILIŞ TARAMASI (10:15)
# ════════════════════════════════════════════════════════════
def job_market_open_scan():
    log_event("🔔 AÇILIŞ")
    
    send_message(f"""🔔 <b>BORSA AÇILDI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M')}
🔍 İlk tarama başlıyor...

<i>Radara giren hisseler aranıyor...</i>""")
    
    if not is_weekday():
        send_message("⏸️ Hafta sonu")
        return
    
    try:
        fetch_all_15m(symbols_list=BIST_SYMBOLS[:100], delay=0.1)
        signals = scan_all_stocks(min_score=60, save_to_db=True, verbose=False)
        
        if not signals:
            send_message(f"""🔔 <b>AÇILIŞ TARAMASI BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 567 hisse tarandı
⚠️ Kriterlere uygun hisse bulunamadı
⏰ {tr_now().strftime('%H:%M')}

<i>11:00'de tekrar tarayacağım</i>""")
            return
        
        send_message(f"""🔔 <b>AÇILIŞ - {len(signals)} SİNYAL BULUNDU!</b>
━━━━━━━━━━━━━━━━━━━━━━━

🔥 Güçlü hisseler radara girdi
📩 Sinyaller geliyor...""")
        
        send_multiple_signals(signals, max_signals=5)
        log_event(f"✅ {len(signals)} sinyal gönderildi")
        
    except Exception as e:
        send_message(f"❌ <b>Açılış hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# ⚡ HIZLI TARAMA
# ════════════════════════════════════════════════════════════
def job_quick_scan():
    log_event("⚡ HIZLI TARAMA")
    
    send_message(f"""⚡ <b>HIZLI TARAMA BAŞLADI</b>
⏰ {tr_now().strftime('%H:%M')}""")
    
    try:
        signals = scan_all_stocks(min_score=65, save_to_db=False, verbose=False)
        
        if not signals:
            send_message(f"""⚡ <b>HIZLI TARAMA BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 Tarama tamamlandı
⚠️ Kriterlere uygun hisse bulunamadı (skor 65+)
⏰ {tr_now().strftime('%H:%M')}

<i>Sonraki taramayı bekleyin</i>""")
            return
        
        send_message(f"""⚡ <b>{len(signals)} SİNYAL BULUNDU!</b>
━━━━━━━━━━━━━━━━━━━━━━━
📩 Sinyaller geliyor...""")
        
        send_multiple_signals(signals, max_signals=3)
        log_event(f"✅ {len(signals)} sinyal gönderildi")
        
    except Exception as e:
        send_message(f"❌ <b>Hızlı tarama hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# 🔍 TAM TARAMA (Her saat başı)
# ════════════════════════════════════════════════════════════
def job_full_scan():
    log_event("🔍 TAM TARAMA")
    
    send_message(f"""🔍 <b>TAM TARAMA BAŞLADI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M')}
📊 567 hisse taranıyor...

<i>Radara giren hisseler aranıyor...</i>""")
    
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=True, verbose=False)
        
        if not signals:
            send_message(f"""🔍 <b>TAM TARAMA BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 567 hisse tarandı
⚠️ Kriterlere uygun hisse bulunamadı (skor 60+)
⏰ {tr_now().strftime('%H:%M')}

<i>Bir sonraki saatte tekrar bakacağım</i>""")
            return
        
        send_message(f"""🔍 <b>{len(signals)} SİNYAL BULUNDU!</b>
━━━━━━━━━━━━━━━━━━━━━━━

🔥 Güçlü hisseler radara girdi
📩 Sinyal kartları geliyor...""")
        
        send_multiple_signals(signals, max_signals=5)
        log_event(f"✅ {len(signals)} sinyal gönderildi")
        
    except Exception as e:
        send_message(f"❌ <b>Tam tarama hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# 💎 STRATEJİ TARAMASI (14:00)
# ════════════════════════════════════════════════════════════
def job_strategy_scan():
    log_event("💎 STRATEJİ")
    
    send_message(f"""💎 <b>STRATEJİ TARAMASI BAŞLADI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M')}
🔍 Momentum + Kırılım analizi...""")
    
    try:
        momentum_signals = scan_momentum_strategy(min_score=65)
        breakout_signals = scan_breakout_strategy(min_score=65)
        
        msg = f"""💎 <b>STRATEJİ TARAMASI BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M')}

🚀 <b>Momentum:</b> {len(momentum_signals)} hisse
💥 <b>Kırılım:</b> {len(breakout_signals)} hisse

"""
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
            send_message(f"🔥 <b>{len(all_strong)} EN GÜÇLÜ STRATEJİ SİNYALİ:</b>")
            send_multiple_signals(all_strong[:3], max_signals=3)
        
    except Exception as e:
        send_message(f"❌ <b>Strateji hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# 🌆 GÜN SONU RAPORU (18:15)
# ════════════════════════════════════════════════════════════
def job_end_of_day_report():
    log_event("🌆 GÜN SONU")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total, AVG(score) as avg_score, MAX(score) as max_score FROM signals WHERE date(created_at) = date('now')")
        result = cursor.fetchone()
        
        cursor.execute("SELECT symbol, score, price FROM signals WHERE date(created_at) = date('now') ORDER BY score DESC LIMIT 5")
        top_signals = cursor.fetchall()
        
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN score >= 85 THEN 1 ELSE 0 END) as cok_guclu,
                SUM(CASE WHEN score >= 75 AND score < 85 THEN 1 ELSE 0 END) as guclu,
                SUM(CASE WHEN score >= 65 AND score < 75 THEN 1 ELSE 0 END) as normal,
                SUM(CASE WHEN score >= 60 AND score < 65 THEN 1 ELSE 0 END) as zayif
            FROM signals
            WHERE date(created_at) = date('now')
        """)
        categories = cursor.fetchone()
        
        conn.close()
        
        total = (result['total'] if result and result['total'] else 0)
        avg_score = (result['avg_score'] if result and result['avg_score'] else 0)
        max_score = (result['max_score'] if result and result['max_score'] else 0)
        
        msg = f"""🌆 <b>GÜN SONU RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━
📅 {tr_now().strftime('%d.%m.%Y - %A')}

📊 <b>İSTATİSTİKLER</b>
Toplam Sinyal : <b>{total}</b>
Ortalama Skor : <b>{avg_score:.0f}/100</b>
En Yüksek     : <b>{max_score}/100</b>

🎯 <b>SİNYAL KATEGORİLERİ</b>
🔥🔥🔥 Çok Güçlü : <b>{categories['cok_guclu'] or 0}</b>
🔥🔥 Güçlü       : <b>{categories['guclu'] or 0}</b>
🔥 Normal        : <b>{categories['normal'] or 0}</b>
🟡 Zayıf         : <b>{categories['zayif'] or 0}</b>

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
# 🎯 TAM TARAMA + SİNYAL TAKİP BİRLEŞTİRİLMİŞ (YENİ!)
# ════════════════════════════════════════════════════════════
def job_full_scan_with_tracking():
    """
    Tam tarama yapar VE hemen ardından sinyal takip yapar
    Aynı çalışma içinde olduğu için veritabanı problemi olmaz!
    """
    log_event("🔍 TAM TARAMA + SİNYAL TAKİP BAŞLADI")
    
    # 1. ADIM: Tam tarama yap (sinyaller bulunur ve takibe alınır)
    job_full_scan()
    
    # 2. ADIM: Hemen ardından sinyal takip yap
    log_event("🎯 SİNYAL TAKİP BAŞLATILIYOR...")
    try:
        from services.signal_tracker import track_signals_job
        track_signals_job()
    except Exception as e:
        send_message(f"❌ <b>Sinyal takip hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# ZAMANLAYICI KURULUMU
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
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}""")
    except:
        pass
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("⏹️ Durduruldu")


if __name__ == "__main__":
    print("\n⏰ ZAMANLAYICI MENÜ")
    print(f"🕐 TR Saati: {tr_now().strftime('%H:%M - %d.%m.%Y')}")
    print("1 → Başlat")
    print("2 → Sabah test")
    print("3 → Pre-market test")
    print("4 → Açılış test")
    print("5 → Hızlı tarama test")
    print("6 → Tam tarama test")
    print("7 → Strateji test")
    print("8 → Gün sonu test")
    print("9 → Tam tarama + Sinyal takip test")
    
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
