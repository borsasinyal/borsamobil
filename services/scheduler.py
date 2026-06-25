"""
Profesyonel Otomatik Zamanlayıcı - 7/24 Çalışma Sistemi
SWING TRADE optimized + TR Timezone + Sinyal Takip
Detaylı Gün Sonu Raporu + Piyasa Analizi
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
# TÜRKİYE SAATİ
# ════════════════════════════════════════════════════════════

TR_TIMEZONE = timezone(timedelta(hours=3))

def tr_now():
    return datetime.now(TR_TIMEZONE)

def is_weekday():
    return tr_now().weekday() < 5

def is_market_open():
    return True

def log_event(message):
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
# 🌆 GÜN SONU RAPORU (18:30) - DETAYLI VERSİYON
# ════════════════════════════════════════════════════════════
def job_end_of_day_report():
    log_event("🌆 GÜN SONU - DETAYLI RAPOR")
    
    try:
        from database import get_stock_history
        
        # 1. ADIM: Bugünün en çok yükselenleri ve düşenleri
        log_event("📊 Piyasa analizi yapılıyor...")
        
        movers_data = []
        
        for symbol in BIST_SYMBOLS:
            try:
                data = get_stock_history(symbol, days=5)
                if not data or len(data) < 2:
                    continue
                
                today = data[0]
                yesterday = data[1]
                
                if not today or not yesterday:
                    continue
                
                current_price = today.get('close')
                prev_close = yesterday.get('close')
                volume = today.get('volume')
                
                if current_price and prev_close and prev_close > 0:
                    daily_change = ((current_price - prev_close) / prev_close) * 100
                    
                    avg_volume = sum(d.get('volume', 0) for d in data[:5]) / 5
                    rvol = volume / avg_volume if avg_volume > 0 else 0
                    
                    movers_data.append({
                        'symbol': symbol.replace('.IS', ''),
                        'price': current_price,
                        'daily_change': daily_change,
                        'volume': volume,
                        'rvol': rvol
                    })
            except:
                continue
        
        # Sıralama
        gainers = sorted([m for m in movers_data if m['daily_change'] > 0], 
                       key=lambda x: x['daily_change'], reverse=True)[:5]
        losers = sorted([m for m in movers_data if m['daily_change'] < 0], 
                      key=lambda x: x['daily_change'])[:5]
        
        total_up = len([m for m in movers_data if m['daily_change'] > 0])
        total_down = len([m for m in movers_data if m['daily_change'] < 0])
        
        # 2. ADIM: Yarın için potansiyel hisseler
        log_event("🔍 Yarın için potansiyel hisseler aranıyor...")
        
        tomorrow_signals = scan_all_stocks(min_score=70, save_to_db=False, verbose=False, add_to_tracker=False)
        tomorrow_signals.sort(key=lambda x: x['score'], reverse=True)
        top_signals = tomorrow_signals[:5]
        
        # Tavan adayları
        tavan_candidates = []
        for signal in tomorrow_signals:
            reasons = signal.get('reasons', [])
            for r in reasons:
                title = r.get('title', '').upper()
                if 'TAVAN ADAYI' in title or 'GÜÇLÜ YÜKSELIŞ' in title or 'GÜÇLÜ GÜN' in title:
                    tavan_candidates.append(signal)
                    break
        
        # 3. ADIM: Bugünkü sinyal istatistikleri
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as total, AVG(score) as avg_score, MAX(score) as max_score 
            FROM signals 
            WHERE date(created_at) = date('now')
        """)
        result = cursor.fetchone()
        
        total_today = (result['total'] if result and result['total'] else 0)
        avg_score = (result['avg_score'] if result and result['avg_score'] else 0)
        max_score = (result['max_score'] if result and result['max_score'] else 0)
        
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM active_signals 
            WHERE status = 'active'
        """)
        active_result = cursor.fetchone()
        active_count = active_result['cnt'] if active_result else 0
        
        # Bugün kapanan sinyaller
        cursor.execute("""
            SELECT 
                COUNT(*) as total_closed,
                SUM(CASE WHEN target_1_hit = 1 THEN 1 ELSE 0 END) as t1_hit,
                SUM(CASE WHEN stop_hit = 1 THEN 1 ELSE 0 END) as stop_count,
                AVG(final_pnl_pct) as avg_pnl
            FROM active_signals
            WHERE date(closed_at) = date('now')
            AND status != 'active'
        """)
        closed_result = cursor.fetchone()
        closed_today = closed_result['total_closed'] if closed_result and closed_result['total_closed'] else 0
        t1_hit_today = closed_result['t1_hit'] if closed_result and closed_result['t1_hit'] else 0
        stop_today = closed_result['stop_count'] if closed_result and closed_result['stop_count'] else 0
        avg_pnl = closed_result['avg_pnl'] if closed_result and closed_result['avg_pnl'] else 0
        
        conn.close()
        
        # 4. ADIM: RAPORU OLUŞTUR
        msg = f"""🌆 <b>GÜN SONU RAPORU - DETAYLI</b>
━━━━━━━━━━━━━━━━━━━━━━━
📅 {tr_now().strftime('%d.%m.%Y - %A')}
⏰ Kapanış: 18:10

"""
        # PIYASA DURUMU
        msg += "📊 <b>BUGÜNÜN PİYASA DURUMU</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"📈 Yükselen: <b>{total_up}</b> hisse\n"
        msg += f"📉 Düşen: <b>{total_down}</b> hisse\n"
        
        if total_up > total_down * 1.5:
            msg += "💪 <b>Genel Trend: GÜÇLÜ YUKARI</b> 🚀\n\n"
        elif total_up > total_down:
            msg += "✅ <b>Genel Trend: POZİTİF</b> 📈\n\n"
        elif total_down > total_up * 1.5:
            msg += "⚠️ <b>Genel Trend: GÜÇLÜ AŞAĞI</b> 📉\n\n"
        else:
            msg += "➡️ <b>Genel Trend: YATAY</b>\n\n"
        
        # EN ÇOK YÜKSELENLER
        if gainers:
            msg += "🏆 <b>EN ÇOK YÜKSELENLER</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, g in enumerate(gainers, 1):
                rvol_emoji = "🔥" if g['rvol'] > 3 else "💪" if g['rvol'] > 1.5 else ""
                msg += f"{i}. <b>{g['symbol']}</b> "
                msg += f"<b>+%{g['daily_change']:.2f}</b> "
                msg += f"({g['price']:.2f} TL) {rvol_emoji}\n"
                if g['rvol'] > 1.5:
                    msg += f"   📊 Hacim: {g['rvol']:.1f}x\n"
            msg += "\n"
        
        # EN ÇOK DÜŞENLER
        if losers:
            msg += "📉 <b>EN ÇOK DÜŞENLER</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, l in enumerate(losers, 1):
                msg += f"{i}. <b>{l['symbol']}</b> "
                msg += f"<b>%{l['daily_change']:.2f}</b> "
                msg += f"({l['price']:.2f} TL)\n"
            msg += "\n"
        
        # YARIN İÇİN POTANSİYELLER
        if top_signals:
            msg += "💎 <b>YARIN İÇİN POTANSİYELLER</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, s in enumerate(top_signals, 1):
                emoji = s.get('emoji', '🔥')
                price = s.get('current_price', 0)
                score = s.get('score', 0)
                
                msg += f"\n{i}. {emoji} <b>{s['symbol']}</b> ({score}/100)\n"
                msg += f"   💰 Kapanış: {price:.2f} TL\n"
                
                targets = s.get('targets', {})
                if targets.get('target_1'):
                    msg += f"   📈 Hedef 1: {targets['target_1']:.2f} TL (+{targets['target_1_pct']}%)\n"
                
                holding = s.get('holding', {})
                if holding.get('strategy'):
                    msg += f"   ⏱️ {holding['strategy']}\n"
            msg += "\n"
        else:
            msg += "💎 <b>YARIN İÇİN POTANSİYELLER</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "⚠️ <i>Yarın için güçlü aday bulunamadı (skor 70+)</i>\n\n"
        
        # TAVAN ADAYLARI
        if tavan_candidates:
            msg += "⚡ <b>TAVAN ADAYLARI</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "🔴 <i>Yarın açılışta dikkat!</i>\n\n"
            for i, t in enumerate(tavan_candidates[:3], 1):
                msg += f"{i}. <b>{t['symbol']}</b> ⚡\n"
                msg += f"   💰 {t['current_price']:.2f} TL | Skor: {t['score']}/100\n"
                for r in t.get('reasons', []):
                    title = r.get('title', '').upper()
                    if 'TAVAN ADAYI' in title or 'YÜKSELIŞ' in title or 'GÜÇLÜ GÜN' in title:
                        msg += f"   📊 {r.get('detail', '')}\n"
                        break
                msg += "\n"
        
        # BUGÜNKÜ İSTATİSTİKLER
        msg += "📊 <b>BUGÜNKÜ İSTATİSTİKLER</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📤 Gönderilen Sinyal: <b>{total_today}</b>\n"
        if total_today > 0:
            msg += f"📊 Ortalama Skor: <b>{avg_score:.0f}/100</b>\n"
            msg += f"🏆 En Yüksek Skor: <b>{max_score}/100</b>\n"
        msg += f"🎯 Aktif Takipte: <b>{active_count}</b> sinyal\n"
        
        if closed_today > 0:
            msg += f"\n📈 <b>BUGÜN KAPANAN:</b>\n"
            msg += f"   ✅ Hedef vuran: {t1_hit_today}\n"
            msg += f"   🛑 Stop olan: {stop_today}\n"
            if avg_pnl:
                pnl_emoji = "✅" if avg_pnl > 0 else "❌"
                msg += f"   {pnl_emoji} Ortalama P/L: {avg_pnl:+.2f}%\n"
        msg += "\n"
        
        # YARIN İÇİN STRATEJİ
        msg += "🎯 <b>YARIN İÇİN STRATEJİ</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if total_up > total_down * 1.5:
            msg += "✅ Piyasa güçlü, AL fırsatlarına odaklan\n"
            msg += "✅ Hacim destekli yükselişleri izle\n"
            msg += "✅ Tavan adaylarına dikkat\n\n"
        elif total_down > total_up * 1.5:
            msg += "⚠️ Piyasa zayıf, DİKKATLİ ol\n"
            msg += "⚠️ Sadece çok güçlü sinyallere gir\n"
            msg += "⚠️ Stop'lara sıkı uy\n\n"
        else:
            msg += "📊 Karışık piyasa, seçici ol\n"
            msg += "📊 Sadece skor 75+ olanları takip et\n"
            msg += "📊 Pozisyonları küçük tut\n\n"
        
        # YARIN İZLENECEKLER ÖZET
        if top_signals or tavan_candidates:
            msg += "👀 <b>YARIN İZLENECEKLER</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            if top_signals:
                msg += "🔥 <b>Güçlü Adaylar:</b> "
                msg += ", ".join([s['symbol'] for s in top_signals[:5]])
                msg += "\n"
            
            if tavan_candidates:
                msg += "⚡ <b>Tavan Adayları:</b> "
                msg += ", ".join([t['symbol'] for t in tavan_candidates[:3]])
                msg += "\n"
            msg += "\n"
        
        # KAPANIŞ
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💤 <i>Bot dinlenmeye geçiyor</i>\n"
        msg += "🌅 <i>Yarın 09:45'te tekrar!</i>\n"
        msg += "💰 <i>İyi kazançlar dilerim!</i>"
        
        send_message(msg)
        log_event("✅ Gün sonu raporu gönderildi")
        
    except Exception as e:
        log_event(f"❌ Gün sonu hatası: {e}")
        send_message(f"❌ <b>Gün sonu hatası</b>\n<code>{str(e)[:200]}</code>")


# ════════════════════════════════════════════════════════════
# 🎯 TAM TARAMA + SİNYAL TAKİP BİRLEŞTİRİLMİŞ
# ════════════════════════════════════════════════════════════
def job_full_scan_with_tracking():
    """Tam tarama yapar VE hemen ardından sinyal takip yapar"""
    log_event("🔍 TAM TARAMA + SİNYAL TAKİP BAŞLADI")
    
    job_full_scan()
    
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
    scheduler.add_job(job_end_of_day_report, CronTrigger(hour=18, minute=30, day_of_week='mon-fri'), id='eod')
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
