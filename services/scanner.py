"""
Profesyonel Tarama Motoru - SWING Trading
Günlük + 15dk verisi, akıllı filtreler, strateji bazlı tarama
YENİ: Sinyal bulununca otomatik aktif takibe alır
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
from config import BIST_SYMBOLS
from database import (
    get_stock_history, 
    get_stock_history_15m, 
    save_signal,
    get_connection,
    add_active_signal  # YENİ
)
from services.analyzer import analyze_stock
from services.signal_engine import generate_signal, format_signal_message


# ════════════════════════════════════════════════════════════
# GÜVENLİK FİLTRELERİ
# ════════════════════════════════════════════════════════════

def passes_safety_filters(symbol, df, analysis):
    """
    Profesyonel güvenlik filtreleri
    Returns: (geçti mi, sebep)
    """
    
    # 1. Yeterli veri
    if len(df) < 50:
        return False, "Yetersiz veri (50 gün altı)"
    
    # 2. Fiyat kontrolü (penny stock değil)
    current_price = analysis.get('current_price')
    if current_price is None or current_price < 2:
        return False, f"Fiyat çok düşük ({current_price} TL)"
    
    # 3. Likidite
    df_sorted = df.sort_values('date').reset_index(drop=True)
    avg_volume = df_sorted['volume'].tail(20).mean()
    avg_volume_tl = avg_volume * current_price
    
    if avg_volume_tl < 2_000_000:  # 2 milyon TL altı
        return False, f"Likidite düşük ({avg_volume_tl/1_000_000:.1f}M TL)"
    
    # 4. Düşen bıçak değil mi?
    last_5_closes = df_sorted['close'].tail(5).tolist()
    if len(last_5_closes) >= 5:
        all_declining = all(last_5_closes[i] > last_5_closes[i+1] for i in range(len(last_5_closes)-1))
        if all_declining:
            total_drop = ((last_5_closes[0] - last_5_closes[-1]) / last_5_closes[0]) * 100
            if total_drop > 8:
                return False, f"Düşen bıçak ({total_drop:.1f}% düşüş)"
    
    # 5. Son 30 günde aşırı düşüş
    if len(df_sorted) >= 30:
        price_30_days_ago = df_sorted['close'].iloc[-30]
        drop_30 = ((price_30_days_ago - current_price) / price_30_days_ago) * 100
        if drop_30 > 35:
            return False, f"30 günde %{drop_30:.0f} düşüş"
    
    # 6. Aşırı volatilite
    atr = analysis.get('atr')
    if atr is not None and current_price > 0:
        atr_pct = (atr / current_price) * 100
        if atr_pct > 10:
            return False, f"Aşırı volatil (ATR: %{atr_pct:.1f})"
    
    # 7. ADX çok düşükse (trend yok)
    adx = analysis.get('adx')
    if adx is not None and adx < 12:
        return False, f"Trend yok (ADX: {adx:.1f})"
    
    return True, "OK"


# ════════════════════════════════════════════════════════════
# TEK HİSSE TARAMA
# ════════════════════════════════════════════════════════════

def scan_single_stock(symbol, min_score=65, use_15m=False):
    """
    Tek hisseyi tara
    
    Args:
        symbol: Hisse kodu (örn: AKBNK.IS)
        min_score: Minimum sinyal skoru
        use_15m: 15 dakikalık veri kullan (day trading için)
    
    Returns:
        signal dict veya None
    """
    try:
        # Veri seç
        if use_15m:
            data = get_stock_history_15m(symbol, limit=500)
            if not data or len(data) < 100:
                # 15dk verisi yoksa günlüğe düş
                data = get_stock_history(symbol, days=300)
        else:
            data = get_stock_history(symbol, days=300)
        
        if not data or len(data) < 50:
            return None
        
        df = pd.DataFrame(data)
        analysis = analyze_stock(df)
        
        if not analysis:
            return None
        
        # Güvenlik filtreleri
        passes, reason = passes_safety_filters(symbol, df, analysis)
        if not passes:
            return {
                'symbol': symbol.replace('.IS', ''),
                'filtered': True,
                'filter_reason': reason
            }
        
        # Sinyal üret
        signal = generate_signal(symbol, analysis, df)
        
        if not signal:
            return None
        
        # Minimum skor
        if signal['score'] < min_score:
            return None
        
        # Timeframe bilgisi ekle
        signal['timeframe'] = '15m' if use_15m else '1d'
        
        return signal

    except Exception as e:
        print(f"   ❌ {symbol} hata: {e}")
        return None


# ════════════════════════════════════════════════════════════
# TÜM BIST TARAMA - YENİ: AKTİF TAKİBE OTOMATİK EKLEME
# ════════════════════════════════════════════════════════════

def scan_all_stocks(min_score=65, save_to_db=True, verbose=False, use_15m=False, symbols_list=None, add_to_tracker=True):
    """
    Tüm BIST tarama
    
    Args:
        min_score: Min skor (varsayılan 65)
        save_to_db: Veritabanına kaydet
        verbose: Detaylı çıktı
        use_15m: 15dk verisi kullan
        symbols_list: Özel liste (None = tüm BIST)
        add_to_tracker: Aktif sinyal takibine ekle (YENİ!)
    """
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    timeframe = "15 DAKİKALIK" if use_15m else "GÜNLÜK"
    
    print(f"\n{'='*60}")
    print(f"🔍 BIST TARAMASI - {timeframe}")
    print(f"📊 {len(symbols_list)} hisse taranacak")
    print(f"⚙️  Min skor: {min_score}")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")
    
    signals = []
    filtered_out = []
    no_data = []
    tracker_added = 0  # YENİ
    
    for i, symbol in enumerate(symbols_list, 1):
        if i % 25 == 0 or i == len(symbols_list):
            print(f"   ⏳ {i}/{len(symbols_list)} ({i*100//len(symbols_list)}%) | Sinyal: {len(signals)}")
        
        result = scan_single_stock(symbol, min_score, use_15m)
        
        if result is None:
            no_data.append(symbol)
            continue
        
        if result.get('filtered'):
            filtered_out.append(result)
            if verbose:
                print(f"   🚫 {result['symbol']}: {result['filter_reason']}")
            continue
        
        signals.append(result)
        
        if verbose:
            print(f"   ✅ {result['symbol']}: Skor {result['score']} - {result['label']}")
        
        # DB kayıt
        if save_to_db:
            save_signal(
                symbol=result['symbol'],
                signal_type=result['signal_type'],
                price=result['current_price'],
                target_price=result['targets']['target_2'],
                stop_loss=result['targets']['stop_loss'],
                score=result['score'],
                strategy=result['strength'],
                timeframe=result['timeframe']
            )
            
            # ⭐ YENİ: AKTİF TAKİBE EKLE (skor 65+ olanları)
            if add_to_tracker and result['score'] >= 65:
                t = result['targets']
                added_id = add_active_signal(
                    symbol=result['symbol'],
                    entry_price=result['current_price'],
                    target_1=t['target_1'],
                    target_2=t['target_2'],
                    target_3=t['target_3'],
                    stop_loss=t['stop_loss'],
                    score=result['score']
                )
                if added_id:
                    tracker_added += 1
    
    # Sırala
    signals.sort(key=lambda x: x['score'], reverse=True)
    
    # Özet
    print(f"\n{'='*60}")
    print(f"📊 TARAMA TAMAMLANDI - {timeframe}")
    print(f"{'='*60}")
    print(f"✅ Güçlü Sinyal : {len(signals)}")
    print(f"🚫 Filtrelendi  : {len(filtered_out)}")
    print(f"⚪ Veri Yok    : {len(no_data)}")
    print(f"📋 Toplam       : {len(symbols_list)}")
    if add_to_tracker:
        print(f"🎯 Takibe alındı: {tracker_added}")  # YENİ
    print(f"{'='*60}\n")
    
    return signals


# ════════════════════════════════════════════════════════════
# STRATEJİ BAZLI TARAMA
# ════════════════════════════════════════════════════════════

def scan_momentum_strategy(min_score=70):
    """Momentum stratejisi - Güçlü trend + hacim"""
    print("\n🚀 MOMENTUM STRATEJİSİ")
    
    all_signals = scan_all_stocks(min_score=min_score, save_to_db=False, add_to_tracker=False)
    
    # Filtreleme: MACD pozitif + RSI 50-70 + RVOL > 1.5
    momentum_signals = []
    for s in all_signals:
        ind = s.get('indicators', {})
        rsi = ind.get('rsi')
        rvol = ind.get('rvol')
        macd = ind.get('macd')
        
        if (rsi and 50 <= rsi <= 70 and 
            rvol and rvol > 1.5 and
            macd and macd > 0):
            momentum_signals.append(s)
    
    return momentum_signals


def scan_breakout_strategy(min_score=70):
    """Kırılım stratejisi - Yüksek hacim + kırılım"""
    print("\n💥 KIRILIM STRATEJİSİ")
    
    all_signals = scan_all_stocks(min_score=min_score, save_to_db=False, add_to_tracker=False)
    
    # Sadece kırılım yapanlar
    breakout_signals = []
    for s in all_signals:
        breakouts = s.get('breakouts', [])
        up_breakouts = [b for b in breakouts if b.get('type') == 'UP']
        if up_breakouts:
            breakout_signals.append(s)
    
    return breakout_signals


def scan_vwap_bounce_strategy(min_score=65):
    """VWAP bounce stratejisi - Fiyat VWAP'a yakın"""
    print("\n⭐ VWAP BOUNCE STRATEJİSİ")
    
    all_signals = scan_all_stocks(min_score=min_score, save_to_db=False, use_15m=True, add_to_tracker=False)
    
    # VWAP'a yakın olanlar
    vwap_signals = []
    for s in all_signals:
        kl = s.get('key_levels', {})
        vwap = kl.get('vwap')
        price = s.get('current_price')
        
        if vwap and price:
            diff_pct = abs((price - vwap) / vwap) * 100
            if diff_pct < 1.5:  # VWAP'a %1.5 yakınlık
                vwap_signals.append(s)
    
    return vwap_signals


# ════════════════════════════════════════════════════════════
# SPAM KORUMASI
# ════════════════════════════════════════════════════════════

def is_recently_sent(symbol, hours=4):
    """Son X saatte bu sinyal gönderildi mi?"""
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
    """Spam koruması - sadece yeni sinyaller"""
    new_signals = []
    for signal in signals:
        if not is_recently_sent(signal['symbol'], hours):
            new_signals.append(signal)
    return new_signals


# ════════════════════════════════════════════════════════════
# TARAMA + TELEGRAM
# ════════════════════════════════════════════════════════════

def scan_and_notify(min_score=70, use_15m=False, max_signals=5, spam_hours=0):
    """
    Tara ve yeni sinyalleri Telegram'a gönder
    """
    from telegram_bot.bot import send_multiple_signals, send_message
    
    print("\n🔍 Tarama başlıyor...")
    signals = scan_all_stocks(
        min_score=min_score, 
        save_to_db=True, 
        verbose=False,
        use_15m=use_15m
    )
    
    if not signals:
        print("⚠️  Sinyal yok")
        return 0
    
    # Spam koruması
    new_signals = filter_new_signals(signals, hours=spam_hours)
    
    if not new_signals:
        print(f"ℹ️  {len(signals)} sinyal var ama hepsi son {spam_hours} saatte gönderildi")
        return 0
    
    print(f"✅ {len(new_signals)} YENİ sinyal bulundu")
    print("📤 Telegram'a gönderiliyor...")
    
    sent = send_multiple_signals(new_signals, max_signals=max_signals)
    
    print(f"✅ {sent} mesaj gönderildi")
    return sent


# ════════════════════════════════════════════════════════════
# GÖRSEL ÇIKTI
# ════════════════════════════════════════════════════════════

def print_top_signals(signals, top_n=10):
    """En iyi N sinyali yazdır"""
    if not signals:
        print("\n⚠️  Sinyal yok")
        return
    
    top = signals[:top_n]
    
    print(f"\n{'='*60}")
    print(f"🏆 EN İYİ {len(top)} SİNYAL")
    print(f"{'='*60}\n")
    
    print(f"{'#':<4}{'SEMBOL':<10}{'FİYAT':<14}{'SKOR':<10}{'GÜÇ':<25}")
    print("─" * 60)
    
    for i, s in enumerate(top, 1):
        emoji = s['emoji']
        symbol = s['symbol']
        price = f"{s['current_price']:.2f} TL"
        score = f"{s['score']}/100"
        label = s['label']
        tf = s.get('timeframe', '1d')
        
        print(f"{i:<4}{symbol:<10}{price:<14}{score:<10}{emoji} {label} ({tf})")
    
    print("─" * 60)
    
    # En iyi 3'ünü detaylı göster
    print(f"\n\n{'='*60}")
    print(f"🌟 EN İYİ 3 - DETAYLI")
    print(f"{'='*60}")
    
    for s in top[:3]:
        print(format_signal_message(s))
        print()


# ════════════════════════════════════════════════════════════
# ANA MENÜ
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 PROFESYONEL TARAMA MOTORU")
    print("="*60)
    
    print("\n📋 SEÇENEKLER:")
    print("  ─── TEMEL TARAMA ───")
    print("  1 → Test (5 hisse - günlük)")
    print("  2 → BIST 100 (günlük)")
    print("  3 → TÜM BIST (günlük)")
    print("  4 → TÜM BIST (15 dakikalık)")
    print()
    print("  ─── STRATEJİ TARAMASI ───")
    print("  5 → Momentum stratejisi")
    print("  6 → Kırılım stratejisi")
    print("  7 → VWAP Bounce stratejisi")
    print()
    print("  ─── TELEGRAM GÖNDERIMI ───")
    print("  8 → Tara + Telegram (Günlük)")
    print("  9 → Tara + Telegram (15dk)")
    
    choice = input("\nSeçim (1-9): ").strip()
    
    if choice == "1":
        signals = scan_all_stocks(min_score=50, save_to_db=False, verbose=True,
                                  symbols_list=BIST_SYMBOLS[:5], add_to_tracker=False)
        print_top_signals(signals, top_n=5)
    
    elif choice == "2":
        signals = scan_all_stocks(min_score=65, save_to_db=True,
                                  symbols_list=BIST_SYMBOLS[:100])
        print_top_signals(signals, top_n=10)
    
    elif choice == "3":
        signals = scan_all_stocks(min_score=65, save_to_db=True)
        print_top_signals(signals, top_n=15)
    
    elif choice == "4":
        signals = scan_all_stocks(min_score=65, save_to_db=True, use_15m=True)
        print_top_signals(signals, top_n=15)
    
    elif choice == "5":
        signals = scan_momentum_strategy(min_score=70)
        print_top_signals(signals, top_n=10)
    
    elif choice == "6":
        signals = scan_breakout_strategy(min_score=70)
        print_top_signals(signals, top_n=10)
    
    elif choice == "7":
        signals = scan_vwap_bounce_strategy(min_score=65)
        print_top_signals(signals, top_n=10)
    
    elif choice == "8":
        scan_and_notify(min_score=70, use_15m=False, max_signals=5)
    
    elif choice == "9":
        scan_and_notify(min_score=70, use_15m=True, max_signals=5)
    
    else:
        print("❌ Geçersiz seçim")
    
    print("\n✅ Tamamlandı!")
