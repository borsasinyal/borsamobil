"""
Sinyal Takip Motoru - SWING TRADE
Aktif sinyalleri takip eder, hedef/stop bildirimleri gönderir

GÖREVİ:
- Her saat çalışır
- Aktif sinyallerin fiyatlarını kontrol eder
- Hedef vurduysa "HEDEF VURDU!" bildirimi
- Stop yaklaştıysa "DİKKAT!" uyarısı
- Stop olduysa pozisyonu kapatır
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
import yfinance as yf

from database import (
    get_active_signals,
    update_target_hit,
    update_near_target_alerted,
    update_near_stop_alerted,
    close_active_signal,
    get_signal_stats
)
from telegram_bot.bot import (
    send_message,
    send_target_hit_alert,
    send_stop_warning,
    escape_html
)


# ════════════════════════════════════════════════════════════
# TÜRKİYE SAATİ
# ════════════════════════════════════════════════════════════

TR_TIMEZONE = timezone(timedelta(hours=3))

def tr_now():
    """Türkiye saatini döndür (UTC+3)"""
    return datetime.now(TR_TIMEZONE)


# ════════════════════════════════════════════════════════════
# GÜNCEL FİYAT ÇEKME
# ════════════════════════════════════════════════════════════

def get_current_price(symbol):
    """
    Yahoo Finance'den güncel fiyat al
    
    Args:
        symbol: 'AKBNK' (sadece sembol, .IS olmadan)
    
    Returns:
        float: Güncel fiyat veya None
    """
    try:
        ticker_symbol = f"{symbol}.IS"
        ticker = yf.Ticker(ticker_symbol)
        
        # Son 1 günlük veri al
        info = ticker.history(period="1d")
        
        if info.empty:
            return None
        
        # Son kapanış fiyatı
        return float(info['Close'].iloc[-1])
    except Exception as e:
        print(f"❌ {symbol} fiyat alma hatası: {e}")
        return None


# ════════════════════════════════════════════════════════════
# YAKLAŞMA UYARILARI - YARDIMCI MESAJLAR
# ════════════════════════════════════════════════════════════

def send_near_target_alert(symbol, target_num, entry_price, target_price, current_price):
    """Hedef'e yaklaştığında uyarı"""
    profit_pct = ((current_price - entry_price) / entry_price) * 100
    distance_pct = ((target_price - current_price) / current_price) * 100
    
    symbol_safe = escape_html(symbol)
    
    msg = f"""🎯 <b>HEDEF {target_num} YAKLAŞIYOR - HAZIR OL!</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>{symbol_safe}</b>
📥 Alış      : {entry_price:.2f} TL
💰 Şu an     : {current_price:.2f} TL
🎯 Hedef {target_num}   : {target_price:.2f} TL
📊 Mesafe    : <b>%{distance_pct:.2f}</b> (çok yakın!)
✅ Mevcut Kâr: <b>+%{profit_pct:.2f}</b>

💡 <b>ÖNERİ:</b>
"""
    
    if target_num == 1:
        msg += "• Satış emrinizi {:.2f}'ye koyun\n".format(target_price)
        msg += "• %33 satış için HAZIR OL\n"
        msg += "• Stop'u girişe çekmeye hazırlan"
    elif target_num == 2:
        msg += "• Satış emrinizi {:.2f}'ye koyun\n".format(target_price)
        msg += "• %33 satış için HAZIR OL\n"
        msg += "• Stop'u Hedef 1'e çekmeye hazırlan"
    else:
        msg += "• Satış emrinizi {:.2f}'ye koyun\n".format(target_price)
        msg += "• Son satış için HAZIR OL\n"
        msg += "• Tüm kalan pozisyonu kapat"
    
    msg += f"\n\n⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}"
    
    send_message(msg)


def send_stop_hit_alert(symbol, entry_price, current_price, stop_loss):
    """Stop olduğunda bildirim"""
    loss_pct = ((current_price - entry_price) / entry_price) * 100
    symbol_safe = escape_html(symbol)
    
    msg = f"""🛑 <b>STOP OLDU - POZİSYON KAPATILDI</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>{symbol_safe}</b>
📥 Alış      : {entry_price:.2f} TL
💰 Çıkış     : {current_price:.2f} TL
🛑 Stop      : {stop_loss:.2f} TL
📉 Zarar     : <b>{loss_pct:.2f}%</b>

💡 <b>DERSLER:</b>
• Stop disiplinli oldu ✅
• Maksimum zarar limitlendi
• Şimdi yeni fırsatları bekleyin
• Üzülme, ileri bak!

━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
🤖 <i>Borsa Sinyal Bot</i>
"""
    
    send_message(msg)


def send_all_targets_hit(symbol, entry_price, target_3, current_price, days_held):
    """Tüm hedefler vurulunca tebrik mesajı"""
    profit_pct = ((current_price - entry_price) / entry_price) * 100
    symbol_safe = escape_html(symbol)
    
    msg = f"""🏆🏆🏆 <b>TÜM HEDEFLER VURULDU!</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>{symbol_safe}</b> - MUHTEŞEM İŞLEM!

📊 <b>ÖZET:</b>
📥 Alış      : {entry_price:.2f} TL
🎯 Hedef 3   : {target_3:.2f} TL ✅
💰 Son Çıkış : {current_price:.2f} TL

💎 <b>KAZANÇ:</b>
✅ Toplam Kar : <b>+{profit_pct:.2f}%</b>
⏱️ Tutma     : {days_held} gün

🎉 <b>TEBRİKLER!</b>
İdeal bir SWING işlemi gerçekleştirdiniz!

━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
🤖 <i>Borsa Sinyal Bot</i>
"""
    
    send_message(msg)


# ════════════════════════════════════════════════════════════
# ANA TAKIP FONKSIYONU
# ════════════════════════════════════════════════════════════

def check_active_signals():
    """
    Aktif sinyalleri kontrol et
    Her saat başı çalışır
    """
    print(f"\n[{tr_now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 SİNYAL TAKİP BAŞLADI")
    
    # Aktif sinyalleri al
    active_signals = get_active_signals()
    
    if not active_signals:
        print("ℹ️ Aktif takip edilecek sinyal yok")
        return 0
    
    print(f"📊 {len(active_signals)} aktif sinyal kontrol ediliyor...")
    
    target_hit_count = 0
    near_alert_count = 0
    stop_count = 0
    
    for signal in active_signals:
        signal_id = signal['id']
        symbol = signal['symbol']
        entry_price = signal['entry_price']
        target_1 = signal['target_1']
        target_2 = signal['target_2']
        target_3 = signal['target_3']
        stop_loss = signal['stop_loss']
        
        # Güncel fiyatı al
        current_price = get_current_price(symbol)
        
        if not current_price:
            print(f"⚠️ {symbol} fiyat alınamadı, atlanıyor")
            continue
        
        print(f"📌 {symbol}: {current_price:.2f} TL (Alış: {entry_price:.2f})")
        
        # ═══════════════════════════════════════
        # 1. STOP KONTROLÜ (EN ÖNEMLİ!)
        # ═══════════════════════════════════════
        if current_price <= stop_loss:
            print(f"   🛑 STOP OLDU!")
            send_stop_hit_alert(symbol, entry_price, current_price, stop_loss)
            close_active_signal(signal_id, current_price, status='stopped')
            stop_count += 1
            continue
        
        # ═══════════════════════════════════════
        # 2. STOP YAKLAŞMA KONTROLÜ
        # ═══════════════════════════════════════
        stop_distance_pct = ((current_price - stop_loss) / current_price) * 100
        
        if stop_distance_pct < 1.5 and not signal['near_stop_alerted']:
            print(f"   ⚠️ STOP'A YAKIN ({stop_distance_pct:.2f}%)")
            send_stop_warning(symbol, entry_price, current_price, stop_loss)
            update_near_stop_alerted(signal_id)
            near_alert_count += 1
            continue
        
        # ═══════════════════════════════════════
        # 3. HEDEF 3 KONTROLÜ (Tam kar)
        # ═══════════════════════════════════════
        if not signal['target_3_hit'] and current_price >= target_3:
            print(f"   🎯 HEDEF 3 VURDU!")
            update_target_hit(signal_id, 3)
            
            # Tüm hedefler vuruldu - tebrik mesajı + kapatma
            created_at = signal['created_at']
            try:
                created_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                days_held = (datetime.now() - created_dt).days
            except:
                days_held = 0
            
            send_all_targets_hit(symbol, entry_price, target_3, current_price, days_held)
            close_active_signal(signal_id, current_price, status='closed')
            target_hit_count += 1
            continue
        
        # ═══════════════════════════════════════
        # 4. HEDEF 2 KONTROLÜ
        # ═══════════════════════════════════════
        if not signal['target_2_hit'] and current_price >= target_2:
            print(f"   🎯 HEDEF 2 VURDU!")
            send_target_hit_alert(symbol, 2, entry_price, target_2, current_price)
            update_target_hit(signal_id, 2)
            target_hit_count += 1
            continue
        
        # ═══════════════════════════════════════
        # 5. HEDEF 1 KONTROLÜ
        # ═══════════════════════════════════════
        if not signal['target_1_hit'] and current_price >= target_1:
            print(f"   🎯 HEDEF 1 VURDU!")
            send_target_hit_alert(symbol, 1, entry_price, target_1, current_price)
            update_target_hit(signal_id, 1)
            target_hit_count += 1
            continue
        
        # ═══════════════════════════════════════
        # 6. HEDEF YAKLAŞMA KONTROLÜ
        # ═══════════════════════════════════════
        
        # Hedef 1 yaklaşma (%80 mesafede)
        if not signal['target_1_hit'] and not signal['near_target_1_alerted']:
            target_1_distance_pct = ((target_1 - current_price) / current_price) * 100
            target_1_total_pct = ((target_1 - entry_price) / entry_price) * 100
            
            if target_1_distance_pct < (target_1_total_pct * 0.2):  # %80 yakın
                print(f"   📈 HEDEF 1 YAKLAŞIYOR")
                send_near_target_alert(symbol, 1, entry_price, target_1, current_price)
                update_near_target_alerted(signal_id, 1)
                near_alert_count += 1
                continue
        
        # Hedef 2 yaklaşma (sadece H1 vurulduktan sonra)
        if (signal['target_1_hit'] and 
            not signal['target_2_hit'] and 
            not signal['near_target_2_alerted']):
            
            target_2_distance_pct = ((target_2 - current_price) / current_price) * 100
            
            if target_2_distance_pct < 1.0:  # %1'den yakın
                print(f"   📈 HEDEF 2 YAKLAŞIYOR")
                send_near_target_alert(symbol, 2, entry_price, target_2, current_price)
                update_near_target_alerted(signal_id, 2)
                near_alert_count += 1
                continue
    
    # Özet
    print(f"\n📊 TAKİP TAMAMLANDI:")
    print(f"   🎯 Hedef vurma: {target_hit_count}")
    print(f"   ⚠️ Yaklaşma uyarısı: {near_alert_count}")
    print(f"   🛑 Stop: {stop_count}")
    
    return target_hit_count + near_alert_count + stop_count


# ════════════════════════════════════════════════════════════
# PORTFOY ÖZETİ GÖNDERME
# ════════════════════════════════════════════════════════════

def send_portfolio_summary():
    """
    Aktif pozisyonların özet raporunu gönder
    Günde 2-3 kez çağrılabilir (öğlen + gün sonu)
    """
    active_signals = get_active_signals()
    
    if not active_signals:
        return
    
    msg = f"""📊 <b>AKTİF POZİSYONLAR</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 Toplam: <b>{len(active_signals)}</b> aktif takip

"""
    
    for i, signal in enumerate(active_signals[:10], 1):  # Max 10 göster
        symbol = signal['symbol']
        entry_price = signal['entry_price']
        target_1 = signal['target_1']
        stop_loss = signal['stop_loss']
        
        # Güncel fiyat
        current_price = get_current_price(symbol)
        
        if not current_price:
            continue
        
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        # Durum emoji
        if signal['target_1_hit']:
            status_emoji = "🎯"  # Hedef 1 vuruldu
        elif pnl_pct >= 0:
            status_emoji = "🟢"  # Karda
        else:
            status_emoji = "🔴"  # Zararda
        
        msg += f"{status_emoji} <b>{escape_html(symbol)}</b>\n"
        msg += f"   📥 {entry_price:.2f} → 💰 {current_price:.2f} "
        msg += f"(<b>{pnl_pct:+.2f}%</b>)\n"
        msg += f"   🎯 H1: {target_1:.2f} | 🛑 Stop: {stop_loss:.2f}\n\n"
    
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}"
    
    send_message(msg)


# ════════════════════════════════════════════════════════════
# HAFTALIK İSTATİSTİK
# ════════════════════════════════════════════════════════════

def send_weekly_stats():
    """Son 7 günün istatistiklerini gönder"""
    stats = get_signal_stats(days=7)
    
    if not stats or not stats.get('total'):
        msg = """📊 <b>HAFTALIK İSTATİSTİK</b>
━━━━━━━━━━━━━━━━━━━━━━━

ℹ️ Son 7 günde kapanmış sinyal yok
"""
        send_message(msg)
        return
    
    total = stats['total']
    t1_hit = stats['t1_hit'] or 0
    t2_hit = stats['t2_hit'] or 0
    t3_hit = stats['t3_hit'] or 0
    stop_count = stats['stop_count'] or 0
    avg_pnl = stats['avg_pnl'] or 0
    max_pnl = stats['max_pnl'] or 0
    min_pnl = stats['min_pnl'] or 0
    win_rate = stats['win_rate'] or 0
    
    msg = f"""📊 <b>HAFTALIK İSTATİSTİK (Son 7 gün)</b>
━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>TOPLAM SİNYAL:</b> {total}

🎯 <b>BAŞARI DURUMU:</b>
✅ Hedef 1 vuruldu : {t1_hit}
✅ Hedef 2 vuruldu : {t2_hit}
✅ Hedef 3 vuruldu : {t3_hit}
🛑 Stop oldu       : {stop_count}

📊 <b>WIN RATE: %{win_rate}</b>

💰 <b>PERFORMANS:</b>
📈 Ortalama Kar/Zarar: {avg_pnl:+.2f}%
🏆 En İyi: +{max_pnl:.2f}%
📉 En Kötü: {min_pnl:.2f}%

━━━━━━━━━━━━━━━━━━━━━━━
⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
🤖 <i>Borsa Sinyal Bot</i>
"""
    
    send_message(msg)


# ════════════════════════════════════════════════════════════
# CRON-JOB.ORG İÇİN ANA FONKSİYON
# ════════════════════════════════════════════════════════════

def track_signals_job():
    """
    Cron-job.org'dan çağrılacak ana fonksiyon
    Her saat başı çalışır
    """
    print(f"\n{'='*60}")
    print(f"🎯 SİNYAL TAKİP JOB")
    print(f"⏰ {tr_now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        # Hafta içi mi?
        if tr_now().weekday() >= 5:
            print("⏸️ Hafta sonu - takip yapılmıyor")
            return
        
        # Sinyalleri kontrol et
        action_count = check_active_signals()
        
        if action_count > 0:
            print(f"\n✅ {action_count} aksiyon gerçekleşti")
        else:
            print(f"\nℹ️ Hiçbir aksiyon gerekmiyor (hedef/stop yok)")
        
    except Exception as e:
        error_msg = f"❌ Sinyal takip hatası: {str(e)}"
        print(error_msg)
        send_message(f"❌ <b>Sinyal Takip Hatası</b>\n<code>{escape_html(str(e)[:200])}</code>")


# ════════════════════════════════════════════════════════════
# TEST
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎯 SİNYAL TAKİP SİSTEMİ - TEST")
    print(f"⏰ TR Saati: {tr_now().strftime('%H:%M - %d.%m.%Y')}")
    print("="*60)
    
    print("\n📋 SEÇENEKLER:")
    print("  1 → Aktif sinyalleri kontrol et")
    print("  2 → Portföy özetini gönder")
    print("  3 → Haftalık istatistikleri gönder")
    print("  4 → Aktif sinyalleri listele")
    
    choice = input("\nSeçim: ").strip()
    
    if choice == "1":
        track_signals_job()
    
    elif choice == "2":
        send_portfolio_summary()
        print("✅ Portföy özeti gönderildi")
    
    elif choice == "3":
        send_weekly_stats()
        print("✅ Haftalık istatistik gönderildi")
    
    elif choice == "4":
        signals = get_active_signals()
        print(f"\n📊 {len(signals)} aktif sinyal:")
        for s in signals:
            print(f"   • {s['symbol']} @ {s['entry_price']:.2f} TL")
    
    print("\n✅ Tamamlandı!")
