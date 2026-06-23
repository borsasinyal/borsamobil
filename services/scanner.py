"""
Profesyonel Tarama Motoru - Day Trading
Günlük + 15dk verisi, akıllı filtreler, strateji bazlı tarama
DÜZELTİLMİŞ İSTATİSTİK + YAKIN KAÇIRANLAR + FİLTRE ÖZETİ
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
from collections import Counter
from config import BIST_SYMBOLS
from database import (
    get_stock_history, 
    get_stock_history_15m, 
    save_signal,
    get_connection
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
        return False, f"Penny stock (Fiyat: {current_price} TL)"
    
    # 3. Likidite
    df_sorted = df.sort_values('date').reset_index(drop=True)
    avg_volume = df_sorted['volume'].tail(20).mean()
    avg_volume_tl = avg_volume * current_price
    
    if avg_volume_tl < 2_000_000:
        return False, f"Likidite düşük ({avg_volume_tl/1_000_000:.1f}M TL)"
    
    # 4. Düşen bıçak değil mi?
    last_5_closes = df_sorted['close'].tail(5).tolist()
    if len(last_5_closes) >= 5:
        all_declining = all(last_5_closes[i] > last_5_closes[i+1] for i in range(len(last_5_closes)-1))
        if all_declining:
            total_drop = ((last_5_closes[0] - last_5_closes[-1]) / last_5_closes[0]) * 100
            if total_drop > 8:
                return False, f"Düşen bıçak (%{total_drop:.1f} düşüş)"
    
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
# TEK HİSSE TARAMA - YENİ DETAYLI STATUS
# ════════════════════════════════════════════════════════════

def scan_single_stock(symbol, min_score=65, use_15m=False):
    """
    Tek hisseyi tara
    
    Returns: dict with 'status' field:
        - 'signal'           : Başarılı sinyal (skor ≥ min_score)
        - 'low_score'        : Skor yetersiz (+ score bilgisi)
        - 'filtered'         : Güvenlik filtresinden geçemedi
        - 'no_data'          : Veri yok veya yetersiz
        - 'analysis_failed'  : Analiz başarısız
        - 'no_signal'        : Sinyal üretilemedi
        - 'error'            : Beklenmeyen hata
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
        
        # 1. Veri yok mu?
        if not data or len(data) < 50:
            return {
                'status': 'no_data',
                'symbol': symbol.replace('.IS', ''),
                'reason': f'Veri yok veya yetersiz ({len(data) if data else 0} mum)'
            }
        
        df = pd.DataFrame(data)
        analysis = analyze_stock(df)
        
        # 2. Analiz başarısız mı?
        if not analysis:
            return {
                'status': 'analysis_failed',
                'symbol': symbol.replace('.IS', ''),
                'reason': 'Teknik analiz hesaplanamadı'
            }
        
        # 3. Güvenlik filtreleri
        passes, reason = passes_safety_filters(symbol, df, analysis)
        if not passes:
            return {
                'status': 'filtered',
                'symbol': symbol.replace('.IS', ''),
                'filter_reason': reason
            }
        
        # Sinyal üret
        signal = generate_signal(symbol, analysis, df)
        
        # 4. Sinyal üretilemedi mi?
        if not signal:
            return {
                'status': 'no_signal',
                'symbol': symbol.replace('.IS', ''),
                'reason': 'Sinyal üretilemedi'
            }
        
        # 5. Skor yetersiz mi?
        if signal['score'] < min_score:
            return {
                'status': 'low_score',
                'symbol': symbol.replace('.IS', ''),
                'score': signal['score'],
                'current_price': signal.get('current_price'),
                'label': signal.get('label', '-')
            }
        
        # ✅ Başarılı sinyal!
        signal['timeframe'] = '15m' if use_15m else '1d'
        signal['status'] = 'signal'
        return signal
    
    except Exception as e:
        print(f"   ❌ {symbol} hata: {e}")
        return {
            'status': 'error',
            'symbol': symbol.replace('.IS', ''),
            'error': str(e)[:100]
        }


# ════════════════════════════════════════════════════════════
# TÜM BIST TARAMA - DETAYLI İSTATİSTİK
# ════════════════════════════════════════════════════════════

def scan_all_stocks(min_score=65, save_to_db=True, verbose=False, use_15m=False, symbols_list=None):
    """
    Tüm BIST tarama - DETAYLI İSTATİSTİK
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
    
    # Sonuçları topla
    signals = []
    low_score_list = []      # Skoru düşük olanlar (yakın kaçıranlar)
    filtered_list = []        # Filtrelenenler
    filter_reasons = []       # Filtre sebepleri (en yaygın olanları görmek için)
    no_data_list = []         # Veri yok olanlar
    analysis_failed_list = [] # Analiz başarısız
    no_signal_list = []       # Sinyal üretilemedi
    error_list = []           # Hatalı
    
    for i, symbol in enumerate(symbols_list, 1):
        if i % 25 == 0 or i == len(symbols_list):
            print(f"   ⏳ {i}/{len(symbols_list)} ({i*100//len(symbols_list)}%) | Sinyal: {len(signals)}")
        
        result = scan_single_stock(symbol, min_score, use_15m)
        
        if result is None:
            # Bu olmamalı ama güvenlik için
            error_list.append({'symbol': symbol, 'error': 'None döndü'})
            continue
        
        status = result.get('status', 'unknown')
        
        # Her status'a göre kategorize et
        if status == 'signal':
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
        
        elif status == 'low_score':
            low_score_list.append(result)
        
        elif status == 'filtered':
            filtered_list.append(result)
            filter_reasons.append(result.get('filter_reason', 'Bilinmiyor'))
            if verbose:
                print(f"   🚫 {result['symbol']}: {result['filter_reason']}")
        
        elif status == 'no_data':
            no_data_list.append(result)
        
        elif status == 'analysis_failed':
            analysis_failed_list.append(result)
        
        elif status == 'no_signal':
            no_signal_list.append(result)
        
        elif status == 'error':
            error_list.append(result)
    
    # Sırala
    signals.sort(key=lambda x: x['score'], reverse=True)
    low_score_list.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # ════════════════════════════════════════════════════════
    # DETAYLI ÖZET
    # ════════════════════════════════════════════════════════
    total = len(symbols_list)
    
    print(f"\n{'='*60}")
    print(f"📊 TARAMA TAMAMLANDI - {timeframe}")
    print(f"{'='*60}")
    print(f"✅ Güçlü Sinyal (≥{min_score})    : {len(signals)}")
    print(f"📉 Skor düşük (<{min_score})      : {len(low_score_list)}")
    print(f"🚫 Güvenlik filtresi            : {len(filtered_list)}")
    print(f"⚪ Veri yok                     : {len(no_data_list)}")
    print(f"⚠️  Analiz başarısız            : {len(analysis_failed_list)}")
    print(f"❌ Sinyal üretilemedi           : {len(no_signal_list)}")
    print(f"💥 Hata                         : {len(error_list)}")
    print(f"{'─'*60}")
    print(f"📋 TOPLAM                       : {total}")
    print(f"{'='*60}")
    
    # ════════════════════════════════════════════════════════
    # YAKIN KAÇIRANLAR (Top 10)
    # ════════════════════════════════════════════════════════
    if low_score_list:
        near_misses = [s for s in low_score_list if s.get('score', 0) >= 50][:10]
        if near_misses:
            print(f"\n📊 YAKIN KAÇIRANLAR (Skor 50-{min_score-1} arası):")
            print(f"{'─'*60}")
            for nm in near_misses:
                score = nm.get('score', 0)
                price = nm.get('current_price', 0)
                gap = min_score - score
                print(f"   • {nm['symbol']:<8} Skor: {score:>3}/100  "
                      f"Fiyat: {price:.2f} TL  ({gap} puan eksik)")
            print()
    
    # ════════════════════════════════════════════════════════
    # FİLTRE SEBEPLERİ ÖZETİ
    # ════════════════════════════════════════════════════════
    if filter_reasons:
        # En sık karşılaşılan filtre sebeplerini göster
        reason_summary = Counter()
        for reason in filter_reasons:
            # Sayıyı çıkar, sadece tipini al ("Likidite düşük (1.5M TL)" → "Likidite düşük")
            reason_type = reason.split('(')[0].strip()
            reason_summary[reason_type] += 1
        
        print(f"\n🚫 FİLTRE SEBEPLERİ (En sık):")
        print(f"{'─'*60}")
        for reason, count in reason_summary.most_common(8):
            bar = '█' * min(count // 2, 30)
            print(f"   • {reason:<30} {count:>3}  {bar}")
        print()
    
    # ════════════════════════════════════════════════════════
    # SKOR DAĞILIMI (Tüm değerlendirmeler)
    # ════════════════════════════════════════════════════════
    all_scored = signals + low_score_list
    if all_scored:
        score_buckets = {
            '85-100 (🔥🔥🔥)': 0,
            '75-84  (🔥🔥)': 0,
            '65-74  (🔥)': 0,
            '55-64  (🟡)': 0,
            '45-54  (⚪)': 0,
            '0-44   (⬇️)': 0,
        }
        
        for s in all_scored:
            sc = s.get('score', 0)
            if sc >= 85: score_buckets['85-100 (🔥🔥🔥)'] += 1
            elif sc >= 75: score_buckets['75-84  (🔥🔥)'] += 1
            elif sc >= 65: score_buckets['65-74  (🔥)'] += 1
            elif sc >= 55: score_buckets['55-64  (🟡)'] += 1
            elif sc >= 45: score_buckets['45-54  (⚪)'] += 1
            else: score_buckets['0-44   (⬇️)'] += 1
        
        print(f"\n📊 SKOR DAĞILIMI ({len(all_scored)} hisse):")
        print(f"{'─'*60}")
        max_count = max(score_buckets.values()) if score_buckets.values() else 1
        for bucket, count in score_buckets.items():
            bar_length = int((count / max_count) * 30) if max_count > 0 else 0
            bar = '█' * bar_length
            print(f"   {bucket:<18} {count:>3}  {bar}")
        print()
    
    return signals


# ════════════════════════════════════════════════════════════
# STRATEJİ BAZLI TARAMA (Aynı kaldı)
# ════════════════════════════════════════════════════════════

def scan_momentum_strategy(min_score=70):
    """Momentum stratejisi - Güçlü trend + hacim"""
    print("\n🚀 MOMENTUM STRATEJİSİ")
    
    all_signals = scan_all_stocks(min_score=min_score, save_to_db=False)
    
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
    
    all_signals = scan_all_stocks(min_score=min_score, save_to_db=False)
    
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
    
    all_signals = scan_all_stocks(min_score=min_score, save_to_db=False, use_15m=True)
    
    vwap_signals = []
    for s in all_signals:
        kl = s.get('key_levels', {})
        vwap = kl.get('vwap')
        price = s.get('current_price')
        
        if vwap and price:
            diff_pct = abs((price - vwap) / vwap) * 100
            if diff_pct < 1.5:
                vwap_signals.append(s)
    
    return vwap_signals


# ════════════════════════════════════════════════════════════
# SPAM KORUMASI (Aynı kaldı)
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
    """Tara ve yeni sinyalleri Telegram'a gönder"""
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
                                  symbols_list=BIST_SYMBOLS[:5])
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
