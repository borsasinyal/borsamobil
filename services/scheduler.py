"""
Otomatik Zamanlayıcı Sistemi
Belirli saatlerde tarama yapar ve yeni sinyalleri Telegram'a gönderir
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, time as dt_time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BIST_SYMBOLS
from database import get_connection
from services.data_fetcher import fetch_all_bist_stocks
from services.scanner import scan_all_stocks
from telegram_bot.bot import send_message, send_multiple_signals


# ════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ════════════════════════════════════════════════

def is_market_open():
    """Borsa açık mı? (Hafta içi 10:00-18:00)"""
    now = datetime.now()
    
    # Hafta sonu kapalı
    if now.weekday() >= 5:  # 5=Cumartesi, 6=Pazar
        return False
    
    # Saat kontrolü
    current_time = now.time()
    market_open = dt_time(10, 0)
    market_close = dt_time(18, 0)
    
    return market_open <= current_time <= market_close


def is_signal_already_sent(symbol, hours=4):
    """
    Bu sinyali son X saat içinde gönderdik mi?
    Spam koruması için
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as count FROM signals
        WHERE symbol = ?
        AND datetime(created_at) > datetime('now', '-' || ? || ' hours')
    """, (symbol, hours))
    
    result = cursor.fetchone()
    conn.close()
    
    return result['count'] > 0 if result else False


def filter_new_signals(signals, hours=4):
    """
    Sadece son X saat içinde gönderilmemiş sinyalleri filtrele
    """
    new_signals = []
    for signal in signals:
        if not is_signal_already_sent(signal['symbol'], hours):
            new_signals.append(signal)
    return new_signals


# ════════════════════════════════════════════════
# ZAMANLAYICI GÖREVLERİ
# ════════════════════════════════════════════════

def job_morning_update():
    """
    🌅 Sabah veri güncelleme (09:45)
    Gece kapanış verilerini günceller
    """
    print(f"\n{'='*60}")
    print(f"🌅 SABAH VERİ GÜNCELLEME - {datetime.now().strftime('%H:%M')}")
    print(f"{'='*60}\n")
    
    if datetime.now().weekday() >= 5:
        print("⏸️  Hafta sonu, atlanıyor")
        return
    
    try:
        # Tüm BIST verilerini güncelle (sadece eksikler)
        fetch_all_bist_stocks(limit=None, delay=0.05)
        
        send_message("""
🌅 <b>SABAH HAZIRLIK TAMAMLANDI</b>
━━━━━━━━━━━━━━━━━━━━━━━

✅ Veriler güncellendi
🚀 Borsa açılışına hazır
⏰ İlk tarama: 10:15

<i>Güzel bir gün olsun! 💪</i>
""".strip())
        
    except Exception as e:
        print(f"❌ Sabah güncelleme hatası: {e}")


def job_premarket_report():
    """
    📊 Pre-market raporu (09:55)
    Açılış öncesi izleme listesi
    """
    if datetime.now().weekday() >= 5:
        return
    
    print(f"\n📊 PRE-MARKET RAPORU - {datetime.now().strftime('%H:%M')}")
    
    try:
        # Önceki günün kapanış sinyallerini tara
        signals = scan_all_stocks(min_score=70, save_to_db=False, verbose=False)
        
        if signals:
            top_5 = signals[:5]
            msg = f"""
🌅 <b>PRE-MARKET RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}

<b>📌 Bugün izlenecek hisseler:</b>

"""
            for i, s in enumerate(top_5, 1):
                msg += f"{i}. <b>{s['symbol']}</b> - {s['current_price']:.2f} TL\n"
                msg += f"   Skor: {s['score']}/100 {s['emoji']}\n\n"
            
            msg += "<i>Açılışta hareketlerini takip edeceğim! 🚀</i>"
            send_message(msg)
        else:
            send_message("""
🌅 <b>PRE-MARKET</b>
━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Şu an dikkat çeken hisse yok
Açılış sonrası tekrar bakacağım.
""".strip())
    
    except Exception as e:
        print(f"❌ Pre-market hatası: {e}")


def job_quick_scan():
    """
    ⚡ Hızlı tarama (yüksek skorlular için)
    Sadece çok güçlü sinyalleri yakalar (skor 75+)
    """
    if not is_market_open():
        print(f"⏸️  Borsa kapalı, tarama atlanıyor - {datetime.now().strftime('%H:%M')}")
        return
    
    print(f"\n⚡ HIZLI TARAMA - {datetime.now().strftime('%H:%M')}")
    
    try:
        signals = scan_all_stocks(min_score=75, save_to_db=False, verbose=False)
        
        if not signals:
            print("   ℹ️  Çok güçlü sinyal yok")
            return
        
        # Sadece YENİ sinyalleri filtrele
        new_signals = filter_new_signals(signals, hours=3)
        
        if not new_signals:
            print(f"   ℹ️  {len(signals)} sinyal var ama hepsi son 3 saatte gönderildi")
            return
        
        print(f"   ✅ {len(new_signals)} YENİ sinyal bulundu")
        
        # En iyi 3'ünü gönder
        send_multiple_signals(new_signals, max_signals=3)
        
    except Exception as e:
        print(f"❌ Hızlı tarama hatası: {e}")


def job_full_scan():
    """
    🔍 Tam tarama (her seviyeden sinyal)
    Skor 65+ tüm sinyalleri yakalar
    """
    if not is_market_open():
        print(f"⏸️  Borsa kapalı, tarama atlanıyor - {datetime.now().strftime('%H:%M')}")
        return
    
    print(f"\n🔍 TAM TARAMA - {datetime.now().strftime('%H:%M')}")
    
    try:
        signals = scan_all_stocks(min_score=65, save_to_db=True, verbose=False)
        
        if not signals:
            print("   ℹ️  Sinyal yok")
            return
        
        # Sadece YENİ sinyalleri filtrele (son 4 saat)
        new_signals = filter_new_signals(signals, hours=4)
        
        if not new_signals:
            print(f"   ℹ️  {len(signals)} sinyal var ama hepsi son 4 saatte gönderildi")
            return
        
        print(f"   ✅ {len(new_signals)} YENİ sinyal bulundu")
        
        # En iyi 5'ini gönder
        send_multiple_signals(new_signals, max_signals=5)
        
    except Exception as e:
        print(f"❌ Tam tarama hatası: {e}")


def job_market_open_scan():
    """
    🔔 Açılış sonrası özel tarama (10:15)
    İlk hareket eden hisseleri yakalar
    """
    if datetime.now().weekday() >= 5:
        return
    
    print(f"\n🔔 AÇILIŞ SONRASI TARAMA - {datetime.now().strftime('%H:%M')}")
    
    try:
        # Önce verileri güncelle (anlık fiyatlar için)
        print("   📥 Veriler güncelleniyor...")
        fetch_all_bist_stocks(limit=None, delay=0.05)
        
        # Sonra tara
        signals = scan_all_stocks(min_score=70, save_to_db=True, verbose=False)
        
        send_message(f"""
🔔 <b>BORSA AÇILDI - İLK TARAMA</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M')}

📊 Tarama sonucu: {len(signals)} güçlü sinyal
""".strip())
        
        if signals:
            new_signals = filter_new_signals(signals, hours=12)
            if new_signals:
                send_multiple_signals(new_signals, max_signals=5)
        
    except Exception as e:
        print(f"❌ Açılış tarama hatası: {e}")


def job_end_of_day_report():
    """
    🌆 Gün sonu raporu (18:15)
    Bugünün özeti
    """
    if datetime.now().weekday() >= 5:
        return
    
    print(f"\n🌆 GÜN SONU RAPORU - {datetime.now().strftime('%H:%M')}")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Bugün gönderilen sinyalleri say
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(score) as avg_score,
                MAX(score) as max_score
            FROM signals
            WHERE date(created_at) = date('now')
        """)
        
        result = cursor.fetchone()
        
        # En iyi 5 sinyal
        cursor.execute("""
            SELECT symbol, score, price
            FROM signals
            WHERE date(created_at) = date('now')
            ORDER BY score DESC
            LIMIT 5
        """)
        
        top_signals = cursor.fetchall()
        conn.close()
        
        msg = f"""
🌆 <b>GÜN SONU RAPORU</b>
━━━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime('%d.%m.%Y - %A')}

📊 <b>BUGÜNÜN İSTATİSTİKLERİ</b>
   Toplam Sinyal : {result['total'] or 0}
   Ortalama Skor : {result['avg_score']:.0f if result['avg_score'] else 0}/100
   En Yüksek     : {result['max_score'] or 0}/100

"""
        
        if top_signals:
            msg += "🏆 <b>BUGÜNÜN EN İYİLERİ</b>\n"
            for i, sig in enumerate(top_signals, 1):
                msg += f"   {i}. {sig['symbol']} - {sig['price']:.2f} TL ({sig['score']}/100)\n"
        
        msg += f"""

━━━━━━━━━━━━━━━━━━━━━━━
💤 <i>Bot dinlenmeye geçiyor</i>
🌅 <i>Yarın 09:45'te tekrar başlıyorum!</i>
"""
        send_message(msg.strip())
        
    except Exception as e:
        print(f"❌ Gün sonu raporu hatası: {e}")


# ════════════════════════════════════════════════
# ZAMANLAYICIYI KUR
# ════════════════════════════════════════════════

def setup_scheduler():
    """
    Tüm görevleri zamanlayıcıya ekle
    """
    scheduler = BlockingScheduler(timezone='Europe/Istanbul')
    
    # 🌅 Sabah hazırlık
    scheduler.add_job(
        job_morning_update,
        CronTrigger(hour=9, minute=45, day_of_week='mon-fri'),
        id='morning_update',
        name='Sabah Veri Güncelleme'
    )
    
    scheduler.add_job(
        job_premarket_report,
        CronTrigger(hour=9, minute=55, day_of_week='mon-fri'),
        id='premarket',
        name='Pre-Market Raporu'
    )
    
    # 🔔 Açılış
    scheduler.add_job(
        job_market_open_scan,
        CronTrigger(hour=10, minute=15, day_of_week='mon-fri'),
        id='market_open',
        name='Açılış Sonrası Tarama'
    )
    
    # ⚡ Gün içi hızlı taramalar (her 15 dk - sadece güçlü sinyaller)
    scheduler.add_job(
        job_quick_scan,
        CronTrigger(minute='*/15', hour='10-17', day_of_week='mon-fri'),
        id='quick_scan',
        name='Hızlı Tarama (15dk)'
    )
    
    # 🔍 Tam tarama (her saat başı)
    scheduler.add_job(
        job_full_scan,
        CronTrigger(minute=0, hour='11-17', day_of_week='mon-fri'),
        id='full_scan',
        name='Tam Tarama (Saatlik)'
    )
    
    # 🌆 Gün sonu raporu
    scheduler.add_job(
        job_end_of_day_report,
        CronTrigger(hour=18, minute=15, day_of_week='mon-fri'),
        id='eod_report',
        name='Gün Sonu Raporu'
    )
    
    return scheduler


# ════════════════════════════════════════════════
# ANA ÇALIŞTIRMA
# ════════════════════════════════════════════════

def start_scheduler():
    """Zamanlayıcıyı başlat"""
    print("\n" + "="*60)
    print("⏰ OTOMATİK ZAMANLAYICI BAŞLATILIYOR")
    print("="*60)
    
    scheduler = setup_scheduler()
    
    # Görevleri listele
    print("\n📋 PROGRAMLANAN GÖREVLER:")
    print("─" * 60)
    for job in scheduler.get_jobs():
        print(f"   ✅ {job.name}")
        print(f"      Sonraki: {job.next_run_time.strftime('%d.%m.%Y %H:%M')}")
    print("─" * 60)
    
    # Başlangıç bildirimi
    try:
        send_message(f"""
🤖 <b>BOT AKTİF EDİLDİ</b>
━━━━━━━━━━━━━━━━━━━━━━━

✅ Otomatik tarama sistemi başladı
⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}

<b>📅 Çalışma Programı:</b>
🌅 09:45 - Sabah hazırlık
📊 09:55 - Pre-market raporu
🔔 10:15 - Açılış taraması
⚡ Her 15 dk - Hızlı tarama
🔍 Her saat - Tam tarama
🌆 18:15 - Gün sonu raporu

<i>Yeni sinyaller geldiğinde haberdar olacaksın! 🚀</i>
""".strip())
    except Exception as e:
        print(f"⚠️  Başlangıç mesajı gönderilemedi: {e}")
    
    print("\n🚀 Zamanlayıcı çalışıyor...")
    print("⌨️  Durdurmak için: CTRL+C\n")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n\n⏹️  Zamanlayıcı durduruldu")
        try:
            send_message("⏹️ <b>Bot durduruldu</b>\n\nManuel olarak kapatıldı.")
        except:
            pass


if __name__ == "__main__":
    print("\n" + "="*60)
    print("⏰ OTOMATİK ZAMANLAYICI")
    print("="*60)
    
    print("\n📋 Seçenekler:")
    print("  1 → Zamanlayıcıyı başlat (sürekli çalışır)")
    print("  2 → Şimdi hızlı tarama yap (test)")
    print("  3 → Şimdi tam tarama yap (test)")
    print("  4 → Şimdi gün sonu raporu (test)")
    
    choice = input("\nSeçim (1/2/3/4): ").strip()
    
    if choice == "1":
        start_scheduler()
    elif choice == "2":
        print("\n⚡ Hızlı tarama testi...")
        job_quick_scan()
    elif choice == "3":
        print("\n🔍 Tam tarama testi...")
        job_full_scan()
    elif choice == "4":
        print("\n🌆 Gün sonu raporu testi...")
        job_end_of_day_report()
    else:
        print("❌ Geçersiz seçim")