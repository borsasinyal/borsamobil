"""
Profesyonel Otomatik Zamanlayıcı - 7/24 Çalışma Sistemi
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


# ════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ════════════════════════════════════════════════════════════

def is_weekday():
    """Hafta içi mi?"""
    return datetime.now().weekday() < 5


def is_market_open():
    """Borsa açık mı? (TEST MODU - şu an her zaman True)"""
    return True
    # Gerçek kullanım için aşağıdaki kodu aktif et:
    # if not is_weekday():
    #     return False
    # current_time = datetime.now().time()
    # return dt_time(10, 0) <= current_time <= dt_time(18, 0)


def log_event(message):
    """Log yaz"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


# ════════════════════════════════════════════════════════════
# 🌅 SABAH HAZIRLIK (09:45)
# ════════════════════════════════════════════════════════════

def job_morning_preparation():
    """Sabah veri güncelleme"""
    if not is_weekday():
        log_event("⏸️  Hafta sonu - atlanıyor")
        return
    
    log_event("🌅 SABAH HAZIRLIK BAŞLIYOR")
    
    try:
        log_event("📥 Günlük veriler çekiliyor...")
        fetch_all_daily(symbols_list=BIST_SYMBOLS, delay=0.05)
        
        send_message("""🌅 <b>SABAH HAZIRLIK TAMAMLANDI</b>
━━━━━━━━━━━━━━━━━━━━━━━

✅ Günlük veriler güncellendi
🚀 Borsa açılışına hazır
⏰ İlk tarama: <b>10:15</b>

<i>Bugün güzel kazançlar dilerim 💪</i>
""".strip())
        
        log_event("✅ Sabah hazırlık tamamlandı")
    except Exception as e:
        log_event(f"❌ Sabah hazırlık hatası: {e}")
        send_message(f"⚠️ <b>Sabah hazırlık hatası:</b>\n{str(e)[:200]}")


# ════════════════════════════════════════════════════════════
# 📊 PRE-MARKET RAPORU (09:55)
# ════════════════════════════════════════════════════════════

def job_premarket_report():
    """Açılış öncesi izleme listesi"""
    if not is_weekday():
        return
    
    log_event("📊 PRE-MARKET RAPORU")
    
    try:
        signals = scan_all_stocks(min_score=70, save_to_db=False, verbose=False)
        
        if signals:
            top_5 = signals[:5]
            msg = """🌅 <b>PRE-MARKET RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>Bugün izlenecek hisseler:</b>

"""
            for i, s in enumerate(top_5, 1):
                msg += f"{i}. <b>{s['symbol']}</b> - {s['current_price']:.2f} TL\n"
                msg += f"   {s['emoji']} Skor: {s['score']}/100\n"
                msg += f"   🎯 Hedef: {s['targets']['target_2']:.2f}\n\n"
            
            msg += "<i>Açılışta hareketlerini takip edeceğim! 🚀</i>"
            send_message(msg)
        else:
            send_message("""🌅 <b>PRE-MARKET</b>
━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Şu an dikkat çeken hisse yok
""".strip())
        
        log_event("✅ Pre-market raporu gönderildi")
    except Exception as e:
        log_event(f"❌ Pre-market hatası: {e}")


# ════════════════════════════════════════════════════════════
# 🔔 AÇILIŞ TARAMASI (10:15)
# ════════════════════════════════════════════════════════════

def job_market_open_scan():
    """Açılış sonrası ilk tarama"""
    if not is_weekday():
        return
    
    log_event("🔔 AÇILIŞ TARAMASI")
    
    try:
        log_event("📥 15dk veriler güncelleniyor...")
        fetch_all_15m(symbols_list=BIST_SYMBOLS[:100], delay=0.1)
        
        signals = scan_all_stocks(min_score=70, save_to_db=True, verbose=False)
        
        msg = f"""🔔 <b>BORSA AÇILDI - İLK TARAMA</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M')}

📊 Tarama sonucu: <b>{len(signals)}</b> güçlü sinyal
"""
        send_message(msg.strip())
        
        if signals:
            new_signals = filter_new_signals(signals, hours=12)
            if new_signals:
                send_multiple_signals(new_signals, max_signals=5)
                log_event(f"✅ {len(new_signals)} sinyal gönderildi")
        
    except Exception as e:
        log_event(f"❌ Açılış taraması hatası: {e}")


# ════════════════════════════════════════════════════════════
# ⚡ HIZLI TARAMA
# ════════════════════════════════════════════════════════════

def job_quick_scan():
    """Hızlı tarama - çok güçlü sinyaller (75+)"""
    if not is_market_open():
        log_event(f"⏸️  Borsa kapalı - atlandı")
        return
    
    log_event("⚡ HIZLI TARAMA")
    
    try:
        signals = scan_all_stocks(min_score=75, save_to_db=False, verbose=False)
        
        if not signals:
            log_event("   ℹ️  Çok güçlü sinyal yok")
            return
        
        new_signals = filter_new_signals(signals, hours=3)
        
        if not new_signals:
            log_event(f"   ℹ️  {len(signals)} sinyal var, hepsi son 3 saatte gönderildi")
            return
        
        log_event(f"   ✅ {len(new_signals)} YENİ sinyal")
        send_multiple_signals(new_signals, max_signals=3)
        
    except Exception as e:
        log_event(f"❌ Hızlı tarama hatası: {e}")


# ════════════════════════════════════════════════════════════
# 🔍 TAM TARAMA
# ════════════════════════════════════════════════════════════

def job_full_scan():
    """Tam tarama - tüm seviyelerdeki sinyaller (65+)"""
    if not is_market_open():
        log_event(f"⏸️  Borsa kapalı - atlandı")
        return
    
    log_event("🔍 TAM TARAMA")
    
    try:
        log_event("📥 15dk veriler güncelleniyor...")
        fetch_all_15m(symbols_list=BIST_SYMBOLS[:200], delay=0.1)
        
        signals = scan_all_stocks(min_score=65, save_to_db=True, verbose=False)
        
        if not signals:
            log_event("   ℹ️  Sinyal yok")
            return
        
        new_signals = filter_new_signals(signals, hours=4)
        
        if not new_signals:
            log_event(f"   ℹ️  {len(signals)} sinyal var, hepsi son 4 saatte gönderildi")
            return
        
        log_event(f"   ✅ {len(new_signals)} YENİ sinyal")
        send_multiple_signals(new_signals, max_signals=5)
        
    except Exception as e:
        log_event(f"❌ Tam tarama hatası: {e}")


# ════════════════════════════════════════════════════════════
# 🌆 GÜN SONU RAPORU (18:15)
# ════════════════════════════════════════════════════════════

def job_end_of_day_report():
    """Gün sonu özeti"""
    if not is_weekday():
        return
    
    log_event("🌆 GÜN SONU RAPORU")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(score) as avg_score,
                MAX(score) as max_score
            FROM signals
            WHERE date(created_at) = date('now')
        """)
        result = cursor.fetchone()
        
        cursor.execute("""
            SELECT symbol, score, price, target_price
            FROM signals
            WHERE date(created_at) = date('now')
            ORDER BY score DESC
            LIMIT 5
        """)
        top_signals = cursor.fetchall()
        
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN score >= 85 THEN 1 ELSE 0 END) as cok_guclu,
                SUM(CASE WHEN score >= 75 AND score < 85 THEN 1 ELSE 0 END) as guclu,
                SUM(CASE WHEN score >= 65 AND score < 75 THEN 1 ELSE 0 END) as normal
            FROM signals
            WHERE date(created_at) = date('now')
        """)
        categories = cursor.fetchone()
        
        conn.close()
        
        total = result['total'] or 0
        avg_score = result['avg_score'] or 0
        max_score = result['max_score'] or 0
        
        msg = f"""🌆 <b>GÜN SONU RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime('%d.%m.%Y - %A')}

📊 <b>İSTATİSTİKLER</b>
   Toplam Sinyal : <b>{total}</b>
   Ortalama Skor : <b>{avg_score:.0f}/100</b>
   En Yüksek     : <b>{max_score}/100</b>

🎯 <b>SINYAL KATEGORİLERİ</b>
   🔥🔥🔥 Çok Güçlü : <b>{categories['cok_guclu'] or 0}</b>
   🔥🔥 Güçlü      : <b>{categories['guclu'] or 0}</b>
   🔥 Normal       : <b>{categories['normal'] or 0}</b>

"""
        
        if top_signals:
            msg += "🏆 <b>BUGÜNÜN EN İYİLERİ</b>\n"
            for i, sig in enumerate(top_signals, 1):
                msg += f"   {i}. <b>{sig['symbol']}</b> - {sig['price']:.2f} TL\n"
                msg += f"      Skor: {sig['score']}/100"
                if sig['target_price']:
                    msg += f" | 🎯 {sig['target_price']:.2f}"
                msg += "\n"
        
        msg += """
━━━━━━━━━━━━━━━━━━━━━━━
💤 <i>Bot dinlenmeye geçiyor</i>
🌅 <i>Yarın 09:45'te tekrar başlıyorum!</i>
"""
        send_message(msg.strip())
        log_event("✅ Gün sonu raporu gönderildi")
        
    except Exception as e:
        log_event(f"❌ Gün sonu raporu hatası: {e}")


# ════════════════════════════════════════════════════════════
# 💎 STRATEJİ BAZLI TARAMA (14:00)
# ════════════════════════════════════════════════════════════

def job_strategy_scan():
    """Özel strateji taraması"""
    if not is_market_open():
        return
    
    log_event("💎 STRATEJİ TARAMASI")
    
    try:
        momentum_signals = scan_momentum_strategy(min_score=70)
        breakout_signals = scan_breakout_strategy(min_score=70)
        
        msg = f"""💎 <b>STRATEJİ TARAMASI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M')}

🚀 <b>Momentum:</b> {len(momentum_signals)} hisse
💥 <b>Kırılım:</b> {len(breakout_signals)} hisse

"""
        
        if momentum_signals:
            msg += "📈 <b>EN İYİ MOMENTUM:</b>\n"
            for s in momentum_signals[:3]:
                msg += f"   • {s['symbol']} ({s['score']}/100)\n"
        
        if breakout_signals:
            msg += "\n💥 <b>EN İYİ KIRILIM:</b>\n"
            for s in breakout_signals[:3]:
                msg += f"   • {s['symbol']} ({s['score']}/100)\n"
        
        send_message(msg.strip())
        
        all_strong = [s for s in momentum_signals + breakout_signals if s['score'] >= 80]
        if all_strong:
            new = filter_new_signals(all_strong, hours=6)
            if new:
                send_multiple_signals(new[:3], max_signals=3)
        
    except Exception as e:
        log_event(f"❌ Strateji taraması hatası: {e}")


# ════════════════════════════════════════════════════════════
# ZAMANLAYICI KURULUMU
# ════════════════════════════════════════════════════════════

def setup_scheduler():
    """Tüm görevleri ekle"""
    scheduler = BlockingScheduler(timezone='Europe/Istanbul')
    
    scheduler.add_job(
        job_morning_preparation,
        CronTrigger(hour=9, minute=45, day_of_week='mon-fri'),
        id='morning_prep',
        name='Sabah Veri Güncelleme'
    )
    
    scheduler.add_job(
        job_premarket_report,
        CronTrigger(hour=9, minute=55, day_of_week='mon-fri'),
        id='premarket',
        name='Pre-Market Raporu'
    )
    
    scheduler.add_job(
        job_market_open_scan,
        CronTrigger(hour=10, minute=15, day_of_week='mon-fri'),
        id='market_open',
        name='Açılış Taraması'
    )
    
    scheduler.add_job(
        job_quick_scan,
        CronTrigger(minute='30,45', hour='10-17', day_of_week='mon-fri'),
        id='quick_scan',
        name='Hızlı Tarama (15dk)'
    )
    
    scheduler.add_job(
        job_full_scan,
        CronTrigger(minute=0, hour='11-17', day_of_week='mon-fri'),
        id='full_scan',
        name='Tam Tarama (Saatlik)'
    )
    
    scheduler.add_job(
        job_strategy_scan,
        CronTrigger(hour=14, minute=0, day_of_week='mon-fri'),
        id='strategy',
        name='Strateji Taraması'
    )
    
    scheduler.add_job(
        job_end_of_day_report,
        CronTrigger(hour=18, minute=15, day_of_week='mon-fri'),
        id='eod',
        name='Gün Sonu Raporu'
    )
    
    return scheduler


# ════════════════════════════════════════════════════════════
# BAŞLAT
# ════════════════════════════════════════════════════════════

def start_scheduler():
    """Zamanlayıcıyı başlat"""
    print("\n" + "="*60)
    print("⏰ OTOMATİK ZAMANLAYICI - PROFESYONEL")
    print("="*60)
    
    scheduler = setup_scheduler()
    
    print("\n📋 PROGRAMLANAN GÖREVLER:")
    print("─" * 60)
    for job in scheduler.get_jobs():
        print(f"   ✅ {job.name} (ID: {job.id})")
    print("─" * 60)
    
    try:
        send_message(f"""🤖 <b>BOT AKTİF EDİLDİ</b>
━━━━━━━━━━━━━━━━━━━━━━━

✅ 7/24 otomatik tarama sistemi başladı
⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}

<b>📅 GÜNLÜK PROGRAM:</b>
🌅 09:45 - Sabah hazırlık
📊 09:55 - Pre-market raporu
🔔 10:15 - Açılış taraması
⚡ Her 15 dk - Hızlı tarama
🔍 Her saat - Tam tarama
💎 14:00 - Strateji taraması
🌆 18:15 - Gün sonu raporu

<b>🎯 ÖZELLİKLER:</b>
• Hafta sonu çalışmaz
• Borsa kapalıyken atlar
• Spam koruması aktif

<i>Profesyonel sinyaller geliyor! 🚀</i>
""".strip())
    except Exception as e:
        print(f"⚠️  Başlangıç mesajı gönderilemedi: {e}")
    
    print("\n🚀 Zamanlayıcı çalışıyor...")
    print("⌨️  Durdurmak için: CTRL+C")
    print(f"⏰ Şu an: {datetime.now().strftime('%H:%M:%S')}\n")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n\n⏹️  Zamanlayıcı durduruldu")
        try:
            send_message("⏹️ <b>Bot durduruldu</b>")
        except:
            pass


# ════════════════════════════════════════════════════════════
# ANA MENÜ
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("⏰ OTOMATİK ZAMANLAYICI")
    print("="*60)
    
    print("\n📋 SEÇENEKLER:")
    print()
    print("  ─── BAŞLAT ───")
    print("  1 → Zamanlayıcıyı BAŞLAT (sürekli çalışır)")
    print()
    print("  ─── MANUEL TEST ───")
    print("  2 → Sabah hazırlık test")
    print("  3 → Pre-market raporu test")
    print("  4 → Açılış taraması test")
    print("  5 → Hızlı tarama test")
    print("  6 → Tam tarama test")
    print("  7 → Strateji taraması test")
    print("  8 → Gün sonu raporu test")
    
    choice = input("\nSeçim (1-8): ").strip()
    
    if choice == "1":
        start_scheduler()
    elif choice == "2":
        print("\n🌅 Sabah hazırlık test...")
        job_morning_preparation()
    elif choice == "3":
        print("\n📊 Pre-market test...")
        job_premarket_report()
    elif choice == "4":
        print("\n🔔 Açılış taraması test...")
        job_market_open_scan()
    elif choice == "5":
        print("\n⚡ Hızlı tarama test...")
        job_quick_scan()
    elif choice == "6":
        print("\n🔍 Tam tarama test...")
        job_full_scan()
    elif choice == "7":
        print("\n💎 Strateji taraması test...")
        job_strategy_scan()
    elif choice == "8":
        print("\n🌆 Gün sonu raporu test...")
        job_end_of_day_report()
    else:
        print("❌ Geçersiz seçim")