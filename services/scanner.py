"""
Profesyonel Tarama Motoru
GÜNLÜK + SAATLİK + 4 SAATLİK tarama desteği
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
    
    last_5_closes = df_sorted['close'].tail(5).tolist()
    if len(last_5_closes) >= 5:
        all_declining = all(last_5_closes[i] > last_5_closes[i+1] for i in range(len(last_5_closes)-1))
        if all_declining:
            total_drop = ((last_5_closes[0] - last_5_closes[-1]) / last_5_closes[0]) * 100
            if total_drop > 8:
                return False, f"Düşen bıçak ({total_drop:.1f}%)"
    
    if len(df_sorted) >= 30:
        price_30 = df_sorted['close'].iloc[-30]
        drop_30 = ((price_30 - current_price) / price_30) * 100
        if drop_30 > 35:
            return False, f"30 günde %{drop_30:.0f} düşüş"
    
    atr = analysis.get('atr')
    if atr is not None and current_price > 0:
        atr_pct = (atr / current_price) * 100
        if atr_pct > 10:
            return False, f"Aşırı volatil (ATR: %{atr_pct:.1f})"
    
    adx = analysis.get('adx')
    if adx is not None and adx < 12:
        return False, f"Trend yok (ADX: {adx:.1f})"
    
    return True, "OK"


# ════════════════════════════════════════════════════════════
# SAATLİK / 4H GÜVENLİK FİLTRESİ (Daha esnek)
# ════════════════════════════════════════════════════════════

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
        # ═══════════════════════════════════════
        # 4 SAATLİK VERİ İLE ANALİZ
        # ═══════════════════════════════════════
        if use_4h:
            analysis = analyze_stock_4h(symbol)
            
            if not analysis:
                return None
            
            passes, reason = passes_intraday_filters(symbol, analysis)
            if not passes:
                return {
                    'symbol': symbol.replace('.IS', ''),
                    'filtered': True,
                    'filter_reason': reason
                }
            
            signal = generate_signal(symbol, analysis)
            
            if not signal:
                return None
            
            if signal['score'] < min_score:
                return None
            
            signal['timeframe'] = '4h'
            signal['is_4h'] = True
            signal['is_hourly'] = False
            return signal
        
        # ═══════════════════════════════════════
        # SAATLİK VERİ İLE ANALİZ
        # ═══════════════════════════════════════
        elif use_hourly:
            analysis = analyze_stock_hourly(symbol)
            
            if not analysis:
                return None
            
            passes, reason = passes_intraday_filters(symbol, analysis)
            if not passes:
                return {
                    'symbol': symbol.replace('.IS', ''),
                    'filtered': True,
                    'filter_reason': reason
                }
            
            signal = generate_signal(symbol, analysis)
            
            if not signal:
                return None
            
            if signal['score'] < min_score:
                return None
            
            signal['timeframe'] = '1h'
            signal['is_hourly'] = True
            signal['is_4h'] = False
            return signal
        
        # ═══════════════════════════════════════
        # GÜNLÜK VERİ İLE ANALİZ
        # ═══════════════════════════════════════
        elif use_15m:
            data = get_stock_history_15m(symbol, limit=500)
            if not data or len(data) < 100:
                data = get_stock_history(symbol, days=300)
        else:
            data = get_stock_history(symbol, days=300)
        
        if not data or len(data) < 20:
            return None
        
        df = pd.DataFrame(data)
        analysis = analyze_stock(df)
        
        if not analysis:
            return None
        
        passes, reason = passes_safety_filters(symbol, df, analysis)
        if not passes:
            return {
                'symbol': symbol.replace('.IS', ''),
                'filtered': True,
                'filter_reason': reason
            }
        
        signal = generate_signal(symbol, analysis, df)
        
        if not signal:
            return None
        
        if signal['score'] < min_score:
            return None
        
        signal['timeframe'] = '15m' if use_15m else '1d'
        signal['is_hourly'] = False
        signal['is_4h'] = False
        return signal

    except Exception as e:
        print(f"   ❌ {symbol} hata: {e}")
        return None


# ════════════════════════════════════════════════════════════
# TÜM BIST TARAMA
# ════════════════════════════════════════════════════════════

def scan_all_stocks(min_score=65, save_to_db=True, verbose=False, use_15m=False, use_hourly=False, use_4h=False, symbols_list=None, add_to_tracker=True):
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    if use_4h:
        timeframe = "4 SAATLİK"
    elif use_hourly:
        timeframe = "SAATLİK"
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
        
        # Sadece günlük sinyalleri DB'ye kaydet
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
    
    signals.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n{'='*60}")
    print(f"📊 TARAMA TAMAMLANDI - {timeframe}")
    print(f"{'='*60}")
    print(f"✅ Güçlü Sinyal : {len(signals)}")
    print(f"🚫 Filtrelendi  : {len(filtered_out)}")
    print(f"⚪ Veri Yok    : {len(no_data)}")
    print(f"📋 Toplam       : {len(symbols_list)}")
    if add_to_tracker and not use_hourly and not use_4h:
        print(f"🎯 Takibe alındı: {tracker_added}")
    print(f"{'='*60}\n")
    
    return signals


# ════════════════════════════════════════════════════════════
# SAATLİK TARAMA
# ════════════════════════════════════════════════════════════

def scan_hourly_stocks(min_score=60, symbols_list=None):
    """SAATLİK VERİDEN TARAMA"""
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS[:200]
    
    print(f"\n{'='*60}")
    print(f"⚡ SAATLİK TARAMA - GÜN İÇİ TRADE")
    print(f"📊 {len(symbols_list)} hisse taranacak")
    print(f"⚙️  Min skor: {min_score}")
    print(f"{'='*60}\n")
    
    hourly_signals = scan_all_stocks(
        min_score=min_score,
        save_to_db=False,
        use_hourly=True,
        symbols_list=symbols_list,
        add_to_tracker=False
    )
    
    for signal in hourly_signals:
        signal['is_hourly'] = True
        signal['is_4h'] = False
        signal['timeframe'] = '1h'
    
    print(f"\n⚡ {len(hourly_signals)} SAATLİK SİNYAL BULUNDU")
    return hourly_signals


# ════════════════════════════════════════════════════════════
# 4 SAATLİK TARAMA
# ════════════════════════════════════════════════════════════

def scan_4h_stocks(min_score=65, symbols_list=None):
    """
    4 SAATLİK VERİDEN TARAMA
    14:15'te çalışır - İlk 4H mum kapandıktan sonra
    Tüm BIST hisselerini tarar
    """
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
        add_to_tracker=False
    )
    
    for signal in signals_4h:
        signal['is_4h'] = True
        signal['is_hourly'] = False
        signal['timeframe'] = '4h'
    
    print(f"\n🕐 {len(signals_4h)} ADET 4H SİNYAL BULUNDU")
    return signals_4h


# ════════════════════════════════════════════════════════════
# SPAM KORUMASI
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
    
    new_signals = filter_new_signals(signals, hours=spam_hours)
    
    if not new_signals:
        return 0
    
    sent = send_multiple_signals(new_signals, max_signals=max_signals)
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
        print(f"{i}. {s['emoji']} {s['symbol']:<10} {s['current_price']:.2f} TL  {s['score']}/100  ({tf}){tag}")


if __name__ == "__main__":
    print("\n🚀 PROFESYONEL TARAMA MOTORU")
    print("1 → Günlük tarama")
    print("2 → Saatlik tarama")
    print("3 → 4 Saatlik tarama")
    
    choice = input("\nSeçim: ").strip()
    
    if choice == "1":
        signals = scan_all_stocks(min_score=60, save_to_db=False, symbols_list=BIST_SYMBOLS[:5])
        print_top_signals(signals)
    elif choice == "2":
        signals = scan_hourly_stocks(min_score=60, symbols_list=BIST_SYMBOLS[:5])
        print_top_signals(signals)
    elif choice == "3":
        signals = scan_4h_stocks(min_score=65, symbols_list=BIST_SYMBOLS[:5])
        print_top_signals(signals)
