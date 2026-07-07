"""
Profesyonel Tarama Motoru
GÜNLÜK + SAATLİK (3 TEYİT SİSTEMİ) + 4 SAATLİK
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
    add_active_signal
)
from services.analyzer import analyze_stock, analyze_stock_hourly, analyze_stock_4h
from services.signal_engine import generate_signal, format_signal_message


# ════════════════════════════════════════════════════════════
# GÜÇLÜ MUM TESPİTİ
# ════════════════════════════════════════════════════════════

def has_strong_reversal_candle(analysis):
    candle_patterns = analysis.get('candle_patterns', [])
    strong_patterns = ['three_white_soldiers', 'bullish_engulfing', 'morning_star', 'hammer']
    for p in candle_patterns:
        if p.get('key') in strong_patterns:
            return True
    return False


def has_rsi_reversal(analysis):
    rsi = analysis.get('rsi')
    prev_rsi = analysis.get('prev_rsi')
    if rsi and prev_rsi and rsi < 40 and rsi > prev_rsi:
        return True
    return False


# ════════════════════════════════════════════════════════════
# 🆕 SAATLİK İÇİN 3 TEYİT SİSTEMİ
# ════════════════════════════════════════════════════════════

def check_hourly_confirmations(symbol, hourly_analysis):
    """
    Saatlik sinyal için 3 teyit kontrolü:
    1. Günlük trend pozitif mi? (Fiyat > EMA 22 günlük)
    2. Son 3 saatlik mumdan en az 2'si yeşil mi?
    3. Saatlik RVOL >= 1.5x mi?
    
    Returns:
        dict: {
            'passed': True/False (3'ü birden geçerse True),
            'details': [{'check': str, 'passed': bool, 'value': str}, ...],
            'passed_count': int
        }
    """
    details = []
    passed_count = 0
    
    # ═══════════════════════════════════════
    # TEYİT 1: Günlük trend pozitif
    # ═══════════════════════════════════════
    daily_positive = False
    daily_detail = "Günlük veri yok"
    
    try:
        daily_data = get_stock_history(symbol, days=100)
        if daily_data and len(daily_data) >= 25:
            daily_df = pd.DataFrame(daily_data)
            daily_analysis = analyze_stock(daily_df, timeframe='daily')
            
            if daily_analysis:
                current = daily_analysis.get('current_price')
                ema_22 = daily_analysis.get('ema_22')
                
                if current and ema_22:
                    if current > ema_22:
                        daily_positive = True
                        daily_detail = f"Fiyat({current:.2f}) > EMA22({ema_22:.2f})"
                    else:
                        daily_detail = f"Fiyat({current:.2f}) < EMA22({ema_22:.2f}) ❌"
    except Exception as e:
        daily_detail = f"Hata: {str(e)[:30]}"
    
    details.append({
        'check': 'Günlük trend pozitif',
        'passed': daily_positive,
        'value': daily_detail
    })
    if daily_positive:
        passed_count += 1
    
    # ═══════════════════════════════════════
    # TEYİT 2: Son 3 saatlik mumdan 2'si yeşil
    # ═══════════════════════════════════════
    momentum_ok = False
    momentum_detail = "Veri yok"
    
    try:
        from services.tradingview_fetcher import fetch_stock_tv, TV_AVAILABLE
        if TV_AVAILABLE:
            hourly_data = fetch_stock_tv(symbol, n_bars=5, interval='hourly')
            if hourly_data and len(hourly_data) >= 3:
                last_3 = hourly_data[-3:]
                green_count = sum(1 for candle in last_3 if candle['close'] > candle['open'])
                
                if green_count >= 2:
                    momentum_ok = True
                    momentum_detail = f"Son 3'te {green_count} yeşil mum ✅"
                else:
                    momentum_detail = f"Son 3'te {green_count} yeşil mum ❌"
    except Exception as e:
        momentum_detail = f"Hata: {str(e)[:30]}"
    
    details.append({
        'check': 'Son momentum (3 mumdan 2 yeşil)',
        'passed': momentum_ok,
        'value': momentum_detail
    })
    if momentum_ok:
        passed_count += 1
    
    # ═══════════════════════════════════════
    # TEYİT 3: Hacim onayı (RVOL >= 1.5x)
    # ═══════════════════════════════════════
    volume_ok = False
    volume_detail = "Hacim yok"
    
    rvol = hourly_analysis.get('rvol', 0)
    if rvol >= 1.5:
        volume_ok = True
        volume_detail = f"RVOL {rvol:.1f}x ✅"
    else:
        volume_detail = f"RVOL {rvol:.1f}x (< 1.5x) ❌"
    
    details.append({
        'check': 'Hacim onayı (RVOL >= 1.5x)',
        'passed': volume_ok,
        'value': volume_detail
    })
    if volume_ok:
        passed_count += 1
    
    # 3 TEYİT DE GEÇMELİ
    passed = (passed_count == 3)
    
    return {
        'passed': passed,
        'details': details,
        'passed_count': passed_count
    }


# ════════════════════════════════════════════════════════════
# GÜVENLİK FİLTRELERİ
# ════════════════════════════════════════════════════════════

def passes_safety_filters(symbol, df, analysis):
    if len(df) < 20:
        return False, "Yetersiz veri"
    
    current_price = analysis.get('current_price')
    if current_price is None or current_price < 2:
        return False, f"Fiyat çok düşük ({current_price} TL)"
    
    df_sorted = df.sort_values('date').reset_index(drop=True)
    avg_volume = df_sorted['volume'].tail(20).mean()
    avg_volume_tl = avg_volume * current_price
    
    if avg_volume_tl < 2_000_000:
        return False, f"Likidite düşük ({avg_volume_tl/1_000_000:.1f}M TL)"
    
    is_reversal_candidate = has_strong_reversal_candle(analysis) or has_rsi_reversal(analysis)
    
    last_5_closes = df_sorted['close'].tail(5).tolist()
    if len(last_5_closes) >= 5:
        all_declining = all(last_5_closes[i] > last_5_closes[i+1] for i in range(len(last_5_closes)-1))
        if all_declining:
            total_drop = ((last_5_closes[0] - last_5_closes[-1]) / last_5_closes[0]) * 100
            drop_threshold = 15 if is_reversal_candidate else 8
            if total_drop > drop_threshold:
                return False, f"Düşen bıçak ({total_drop:.1f}%)"
    
    if len(df_sorted) >= 30:
        price_30 = df_sorted['close'].iloc[-30]
        drop_30 = ((price_30 - current_price) / price_30) * 100
        drop30_threshold = 50 if is_reversal_candidate else 35
        if drop_30 > drop30_threshold:
            return False, f"30 günde %{drop_30:.0f} düşüş"
    
    atr = analysis.get('atr')
    if atr is not None and current_price > 0:
        atr_pct = (atr / current_price) * 100
        if atr_pct > 10:
            return False, f"Aşırı volatil (ATR: %{atr_pct:.1f})"
    
    adx = analysis.get('adx')
    if adx is not None:
        if is_reversal_candidate:
            pass
        elif adx < 8:
            return False, f"Trend yok (ADX: {adx:.1f})"
    
    return True, "OK"


def passes_intraday_filters(symbol, analysis):
    """Saatlik ve 4H tarama için daha esnek filtreler"""
    current_price = analysis.get('current_price')
    if current_price is None or current_price < 2:
        return False, "Fiyat düşük"
    
    rvol = analysis.get('rvol', 0)
    if rvol < 0.5:
        return False, "Hacim çok düşük"
    
    return True, "OK"


# ════════════════════════════════════════════════════════════
# TEK HİSSE TARAMA
# ════════════════════════════════════════════════════════════

def scan_single_stock(symbol, min_score=65, use_15m=False, use_hourly=False, use_4h=False):
    try:
        if use_4h:
            analysis = analyze_stock_4h(symbol)
            if not analysis:
                return None
            passes, reason = passes_intraday_filters(symbol, analysis)
            if not passes:
                return {'symbol': symbol.replace('.IS', ''), 'filtered': True, 'filter_reason': reason}
            signal = generate_signal(symbol, analysis)
            if not signal or signal['score'] < min_score:
                return None
            signal['timeframe'] = '4h'
            signal['is_4h'] = True
            signal['is_hourly'] = False
            return signal
        
        elif use_hourly:
            analysis = analyze_stock_hourly(symbol)
            if not analysis:
                return None
            passes, reason = passes_intraday_filters(symbol, analysis)
            if not passes:
                return {'symbol': symbol.replace('.IS', ''), 'filtered': True, 'filter_reason': reason}
            signal = generate_signal(symbol, analysis)
            if not signal or signal['score'] < min_score:
                return None
            
            # 🆕 3 TEYİT KONTROLÜ
            confirmations = check_hourly_confirmations(symbol, analysis)
            
            if not confirmations['passed']:
                # Teyit geçmedi, sinyal iptal
                return {
                    'symbol': symbol.replace('.IS', ''),
                    'filtered': True,
                    'filter_reason': f"Teyit yetersiz ({confirmations['passed_count']}/3)"
                }
            
            # Teyit detaylarını signal'e ekle
            signal['hourly_confirmations'] = confirmations
            signal['timeframe'] = '1h'
            signal['is_hourly'] = True
            signal['is_4h'] = False
            return signal
        
        elif use_15m:
            data = get_stock_history_15m(symbol, limit=500)
            if not data or len(data) < 100:
                data = get_stock_history(symbol, days=300)
        else:
            data = get_stock_history(symbol, days=300)
        
        if not data or len(data) < 20:
            return None
        
        df = pd.DataFrame(data)
        analysis = analyze_stock(df, timeframe='daily')
        if not analysis:
            return None
        
        passes, reason = passes_safety_filters(symbol, df, analysis)
        if not passes:
            return {'symbol': symbol.replace('.IS', ''), 'filtered': True, 'filter_reason': reason}
        
        signal = generate_signal(symbol, analysis, df)
        if not signal or signal['score'] < min_score:
            return None
        
        signal['timeframe'] = '15m' if use_15m else '1d'
        signal['is_hourly'] = False
        signal['is_4h'] = False
        return signal

    except Exception as e:
        print(f"   ❌ {symbol} hata: {e}")
        return None


# ════════════════════════════════════════════════════════════
# AKILLI SPAM FİLTRESİ
# ════════════════════════════════════════════════════════════

def get_last_signal_info(symbol, hours=4):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT score, price FROM signals
            WHERE symbol = ? 
            AND datetime(created_at) > datetime('now', '-' || ? || ' hours')
            ORDER BY created_at DESC
            LIMIT 1
        """, (symbol, hours))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result['score'], result['price']
        return None, None
    except Exception as e:
        print(f"   ⚠️ Spam kontrol hatası: {e}")
        return None, None


def apply_smart_spam_filter(signals, hours=4, min_score_improvement=10):
    if not signals:
        return signals
    
    filtered_signals = []
    spam_filtered_count = 0
    upgraded_count = 0
    
    for signal in signals:
        symbol = signal.get('symbol')
        new_score = signal.get('score', 0)
        new_price = signal.get('current_price', 0)
        
        last_score, last_price = get_last_signal_info(symbol, hours)
        
        if last_score is None:
            filtered_signals.append(signal)
            continue
        
        score_improvement = new_score - last_score
        price_change_pct = 0
        if last_price and last_price > 0:
            price_change_pct = abs((new_price - last_price) / last_price) * 100
        
        if score_improvement >= min_score_improvement:
            signal['spam_upgrade_reason'] = f"⬆️ Skor +{score_improvement} arttı ({last_score}→{new_score})"
            filtered_signals.append(signal)
            upgraded_count += 1
            print(f"   ⬆️ {symbol}: Skor iyileşti (+{score_improvement}), gönderiliyor")
            continue
        
        if price_change_pct >= 3:
            signal['spam_upgrade_reason'] = f"📊 Fiyat değişti (%{price_change_pct:.1f})"
            filtered_signals.append(signal)
            upgraded_count += 1
            print(f"   📊 {symbol}: Fiyat %{price_change_pct:.1f} değişti, gönderiliyor")
            continue
        
        spam_filtered_count += 1
        print(f"   🔇 {symbol}: Spam (skor {last_score}→{new_score}, fiyat sabit)")
    
    if spam_filtered_count > 0 or upgraded_count > 0:
        print(f"\n🎯 SPAM FİLTRESİ:")
        print(f"   🔇 Filtrelendi: {spam_filtered_count}")
        print(f"   ⬆️ Yükseltildi: {upgraded_count}")
        print(f"   ✅ Gönderilecek: {len(filtered_signals)}")
    
    return filtered_signals


# ════════════════════════════════════════════════════════════
# TÜM BIST TARAMA
# ════════════════════════════════════════════════════════════

def scan_all_stocks(min_score=65, save_to_db=True, verbose=False, use_15m=False, use_hourly=False, use_4h=False, symbols_list=None, add_to_tracker=True, apply_spam_filter=True):
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    if use_4h:
        timeframe = "4 SAATLİK"
    elif use_hourly:
        timeframe = "SAATLİK (3 TEYİT)"
    elif use_15m:
        timeframe = "15 DAKİKALIK"
    else:
        timeframe = "GÜNLÜK"
    
    print(f"\n{'='*60}")
    print(f"🔍 BIST TARAMASI - {timeframe}")
    print(f"📊 {len(symbols_list)} hisse taranacak")
    print(f"⚙️  Min skor: {min_score}")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")
    
    signals = []
    filtered_out = []
    no_data = []
    tracker_added = 0
    
    for i, symbol in enumerate(symbols_list, 1):
        if i % 25 == 0 or i == len(symbols_list):
            print(f"   ⏳ {i}/{len(symbols_list)} ({i*100//len(symbols_list)}%) | Sinyal: {len(signals)}")
        
        result = scan_single_stock(symbol, min_score, use_15m, use_hourly, use_4h)
        
        if result is None:
            no_data.append(symbol)
            continue
        
        if result.get('filtered'):
            filtered_out.append(result)
            continue
        
        signals.append(result)
    
    signals.sort(key=lambda x: x['score'], reverse=True)
    
    original_count = len(signals)
    if apply_spam_filter and not use_hourly and not use_4h:
        signals = apply_smart_spam_filter(signals, hours=4, min_score_improvement=10)
    
    for result in signals:
        if save_to_db and not use_hourly and not use_4h:
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
    
    print(f"\n{'='*60}")
    print(f"📊 TARAMA TAMAMLANDI - {timeframe}")
    print(f"{'='*60}")
    print(f"✅ Güçlü Sinyal   : {len(signals)}")
    if apply_spam_filter and original_count != len(signals):
        print(f"🔇 Spam filtrelendi: {original_count - len(signals)}")
    print(f"🚫 Filtrelendi    : {len(filtered_out)}")
    if use_hourly:
        teyit_filtered = [f for f in filtered_out if 'Teyit yetersiz' in f.get('filter_reason', '')]
        if teyit_filtered:
            print(f"   ⚠️ Teyit yetersiz: {len(teyit_filtered)}")
    print(f"⚪ Veri Yok      : {len(no_data)}")
    print(f"📋 Toplam         : {len(symbols_list)}")
    if add_to_tracker and not use_hourly and not use_4h:
        print(f"🎯 Takibe alındı  : {tracker_added}")
    print(f"{'='*60}\n")
    
    return signals


# ════════════════════════════════════════════════════════════
# SAATLİK TARAMA (Min skor: 68 + 3 TEYİT)
# ════════════════════════════════════════════════════════════

def scan_hourly_stocks(min_score=68, symbols_list=None):
    """
    SAATLİK VERİDEN TARAMA
    - Min skor: 68 (60'tan yükseltildi)
    - 3 TEYİT sistemi:
      1. Günlük trend pozitif
      2. Son 3 mumdan 2 yeşil
      3. RVOL >= 1.5x
    """
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS[:200]
    
    print(f"\n{'='*60}")
    print(f"⚡ SAATLİK TARAMA (3 TEYİT SİSTEMİ)")
    print(f"📊 {len(symbols_list)} hisse taranacak")
    print(f"⚙️  Min skor: {min_score}")
    print(f"✅ Teyitler: Günlük trend + Momentum + Hacim")
    print(f"{'='*60}\n")
    
    hourly_signals = scan_all_stocks(
        min_score=min_score,
        save_to_db=False,
        use_hourly=True,
        symbols_list=symbols_list,
        add_to_tracker=False,
        apply_spam_filter=False
    )
    
    for signal in hourly_signals:
        signal['is_hourly'] = True
        signal['is_4h'] = False
        signal['timeframe'] = '1h'
    
    print(f"\n⚡ {len(hourly_signals)} SAATLİK SİNYAL BULUNDU (3 teyit onaylı)")
    return hourly_signals


# ════════════════════════════════════════════════════════════
# 4 SAATLİK TARAMA
# ════════════════════════════════════════════════════════════

def scan_4h_stocks(min_score=65, symbols_list=None):
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    print(f"\n{'='*60}")
    print(f"🕐 4 SAATLİK TARAMA")
    print(f"📊 {len(symbols_list)} hisse taranacak")
    print(f"⚙️  Min skor: {min_score}")
    print(f"{'='*60}\n")
    
    signals_4h = scan_all_stocks(
        min_score=min_score,
        save_to_db=False,
        use_4h=True,
        symbols_list=symbols_list,
        add_to_tracker=False,
        apply_spam_filter=False
    )
    
    for signal in signals_4h:
        signal['is_4h'] = True
        signal['is_hourly'] = False
        signal['timeframe'] = '4h'
    
    print(f"\n🕐 {len(signals_4h)} ADET 4H SİNYAL BULUNDU")
    return signals_4h


# ════════════════════════════════════════════════════════════
# ESKİ SPAM KORUMASI
# ════════════════════════════════════════════════════════════

def is_recently_sent(symbol, hours=4):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count FROM signals
        WHERE symbol = ? AND datetime(created_at) > datetime('now', '-' || ? || ' hours')
    """, (symbol, hours))
    result = cursor.fetchone()
    conn.close()
    return result['count'] > 0 if result else False

def filter_new_signals(signals, hours=4):
    new_signals = []
    for signal in signals:
        if not is_recently_sent(signal['symbol'], hours):
            new_signals.append(signal)
    return new_signals


# ════════════════════════════════════════════════════════════
# TARAMA + TELEGRAM
# ════════════════════════════════════════════════════════════

def scan_and_notify(min_score=70, use_15m=False, max_signals=5, spam_hours=0):
    from telegram_bot.bot import send_multiple_signals, send_message
    signals = scan_all_stocks(min_score=min_score, save_to_db=True, verbose=False, use_15m=use_15m)
    if not signals:
        return 0
    sent = send_multiple_signals(signals, max_signals=max_signals)
    return sent


def print_top_signals(signals, top_n=10):
    if not signals:
        print("\n⚠️ Sinyal yok")
        return
    
    top = signals[:top_n]
    print(f"\n{'='*60}")
    print(f"🏆 EN İYİ {len(top)} SİNYAL")
    print(f"{'='*60}\n")
    
    for i, s in enumerate(top, 1):
        tf = s.get('timeframe', '1d')
        tag = ""
        if s.get('is_4h'): tag = " 🕐4H"
        elif s.get('is_hourly'): tag = " ⚡GÜNİÇİ"
        upgrade = ""
        if s.get('spam_upgrade_reason'):
            upgrade = f"  {s['spam_upgrade_reason']}"
        print(f"{i}. {s['emoji']} {s['symbol']:<10} {s['current_price']:.2f} TL  {s['score']}/100  ({tf}){tag}{upgrade}")


if __name__ == "__main__":
    print("\n🚀 PROFESYONEL TARAMA MOTORU")
    print("1 → Günlük tarama")
    print("2 → Saatlik tarama (3 TEYİT)")
    print("3 → 4 Saatlik tarama")
    
    choice = input("\nSeçim: ").strip()
    
    if choice == "1":
        signals = scan_all_stocks(min_score=60, save_to_db=False, symbols_list=BIST_SYMBOLS[:5])
        print_top_signals(signals)
    elif choice == "2":
        signals = scan_hourly_stocks(min_score=68, symbols_list=BIST_SYMBOLS[:5])
        print_top_signals(signals)
    elif choice == "3":
        signals = scan_4h_stocks(min_score=65, symbols_list=BIST_SYMBOLS[:5])
        print_top_signals(signals)
