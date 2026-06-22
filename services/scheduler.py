"""
Otomatik Zamanlayıcı - SPAM KORUMASI KAPALI
Her tarama yeni sinyal kartları gönderir
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BIST_SYMBOLS
from database import get_connection
from services.data_fetcher import fetch_all_daily, fetch_all_15m
from services.scanner import (
    scan_all_stocks, 
    scan_momentum_strategy,
    scan_breakout_strategy
)
from telegram_bot.bot import send_message, send_multiple_signals


def is_weekday():
    return datetime.now().weekday() < 5


def log_event(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


# ════════════════════════════════════════════
# 🌅 SABAH HAZIRLIK
# ════════════════════════════════════════════

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
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════
# 📊 PRE-MARKET
# ════════════════════════════════════════════

def job_premarket_report():
    log_event("📊 PRE-MARKET")
    
    send_message(f"""📊 <b>PRE-MARKET BAŞLADI</b>
⏰ {datetime.now().strftime('%H:%M')}""")
    
    if not is_weekday():
        send_message("⏸️ Hafta sonu")
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
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════
# 🔔 AÇILIŞ TARAMASI
# ════════════════════════════════════════════

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
⚠️ Kriterlere uygun hisse bulunamadı
⏰ {datetime.now().strftime('%H:%M')}""")
            return
        
        # SPAM KORUMASI YOK - HER ZAMAN GÖNDER
        send_message(f"""🔔 <b>AÇILIŞ - {len(signals)} SİNYAL!</b>
━━━━━━━━━━━━━━━━━━━━━━━
🔥 Güçlü hisseler radara girdi
📩 Sinyaller geliyor...""")
        
        send_multiple_signals(signals, max_signals=5)
        
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════
# ⚡ HIZLI TARAMA
# ════════════════════════════════════════════

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
⚠️ Kriterlere uygun hisse bulunamadı (70+)
⏰ {datetime.now().strftime('%H:%M')}""")
            return
        
        # SPAM KORUMASI YOK - HER ZAMAN GÖNDER
        send_message(f"""⚡ <b>{len(signals)} SİNYAL BULUNDU!</b>
━━━━━━━━━━━━━━━━━━━━━━━
📩 Sinyaller geliyor...""")
        
        send_multiple_signals(signals, max_signals=3)
        
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════
# 🔍 TAM TARAMA
# ════════════════════════════════════════════

def job_full_scan():
    log_event("🔍 TAM TARAMA")
    
    send_message(f"""🔍 <b>TAM TARAMA BAŞLADI</b>
━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now().strftime('%H:%M')}
📊 567 hisse taranıyor...""")
    
    try:
        signals = scan_all_stocks(min_score=65, save_to_db=True, verbose=False)
        
        if not signals:
            send_message(f"""🔍 <b>TAM TARAMA BİTTİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 567 hisse tarandı
⚠️ Kriterlere uygun hisse bulunamadı (65+)
⏰ {datetime.now().strftime('%H:%M')}""")
            return
        
        # SPAM KORUMASI YOK - HER ZAMAN GÖNDER
        send_message(f"""🔍 <b>{len(signals)} SİNYAL BULUNDU!</b>
━━━━━━━━━━━━━━━━━━━━━━━
🔥 Güçlü hisseler radara girdi
📩 Sinyal kartları geliyor...""")
        
        send_multiple_signals(signals, max_signals=5)
        
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════
# 💎 STRATEJİ TARAMASI
# ════════════════════════════════════════════

def job_strategy_scan():
    log_event("💎 STRATEJİ")
    
    send_message(f"""💎 <b>STRATEJİ TARAMASI BAŞLADI</b>
━━━━━━━━━━━━━━━━━━━━━━━
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
        
        # En güçlü sinyalleri detaylı gönder (SPAM koruması yok)
        all_strong = [s for s in momentum_signals + breakout_signals if s['score'] >= 75]
        if all_strong:
            send_message(f"🔥 <b>{len(all_strong)} EN GÜÇLÜ:</b>")
            send_multiple_signals(all_strong[:3], max_signals=3)
        
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════
# 🌆 GÜN SONU RAPORU
# ════════════════════════════════════════════

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
💤 <i>Bot dinlenmeye geçiyor</i>"""
        
        send_message(msg)
    except Exception as e:
        send_message(f"❌ <b>Hata</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════
# MENÜ
# ════════════════════════════════════════════

if __name__ == "__main__":
    print("\n⏰ MENÜ")
    print("1 → Sabah hazırlık")
    print("2 → Pre-market")
    print("3 → Açılış")
    print("4 → Hızlı tarama")
    print("5 → Tam tarama")
    print("6 → Strateji")
    print("7 → Gün sonu")
    
    choice = input("\nSeçim: ").strip()
    
    if choice == "1": job_morning_preparation()
    elif choice == "2": job_premarket_report()
    elif choice == "3": job_market_open_scan()
    elif choice == "4": job_quick_scan()
    elif choice == "5": job_full_scan()
    elif choice == "6": job_strategy_scan()
    elif choice == "7": job_end_of_day_report()
