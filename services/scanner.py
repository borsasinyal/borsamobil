"""
Profesyonel Tarama Motoru - SON HAL
BIST 100 FİLTRE (Günlük + Saatlik + 4H) + SAATLİK DİP DÖNÜŞÜ + AKILLI SPAM
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
    add_active_signal,
    save_bist_trend,
    detect_bist_trend_change
)
from services.analyzer import analyze_stock, analyze_stock_hourly, analyze_stock_4h
from services.signal_engine import generate_signal, format_signal_message


# ════════════════════════════════════════════════════════════
# BIST 100 GENEL PİYASA KONTROLÜ
# ════════════════════════════════════════════════════════════

def get_bist100_market_mode(timeframe='daily'):
    """
    BIST 100 durumunu kontrol et, dinamik min_score döndür
    
    timeframe:
    - 'daily' → Günlük tarama skorları
    - 'hourly' → Saatlik tarama skorları (daha sıkı)
    - '4h' → 4 Saatlik tarama skorları (orta seviye)
    """
    try:
        import yfinance as yf
        
        ticker = yf.Ticker("XU100.IS")
        hist = ticker.history(period="6mo")
        
        if len(hist) < 50:
            return {
                'trend': 'BİLİNMİYOR', 'min_score': 65, 'emoji': '⚪',
                'message': 'BIST 100 verisi alınamadı', 'price': 0,
                'ema20': 0, 'ema50': 0,
                'trend_changed': False, 'change_direction': None
            }
        
        closes = hist['Close'].values
        
        ema20_series = pd.Series(closes).ewm(span=20, adjust=False).mean()
        ema50_series = pd.Series(closes).ewm(span=50, adjust=False).mean()
        
        price = float(closes[-1])
        ema20 = float(ema20_series.iloc[-1])
        ema50 = float(ema50_series.iloc[-1])
        
        # 🆕 3 farklı zaman dilimi için ayrı skor tablosu
        def get_min_score(trend, tf):
            """Zaman dilimine ve BIST trendine göre min skor"""
            scores = {
                'daily': {
                    'GÜÇLÜ BOĞA': 60, 'BOĞA': 60, 'POZİTİF': 65,
                    'YATAY': 70, 'AYI': 78, 'GÜÇLÜ AYI': 85
                },
                'hourly': {
                    'GÜÇLÜ BOĞA': 68, 'BOĞA': 68, 'POZİTİF': 72,
                    'YATAY': 75, 'AYI': 78, 'GÜÇLÜ AYI': 80
                },
                '4h': {
                    'GÜÇLÜ BOĞA': 65, 'BOĞA': 65, 'POZİTİF': 68,
                    'YATAY': 72, 'AYI': 75, 'GÜÇLÜ AYI': 80
                }
            }
            return scores.get(tf, scores['daily']).get(trend, 65)
        
        # Trend tespiti
        if price > ema20 > ema50:
            trend = "GÜÇLÜ BOĞA"
            emoji = "🚀"
            message = f"BIST 100 GÜÇLÜ! Fiyat({price:.0f}) > EMA20({ema20:.0f}) > EMA50({ema50:.0f})"
        elif price > ema50 and price > ema20:
            trend = "BOĞA"
            emoji = "📈"
            message = f"BIST 100 pozitif. EMA20 ve EMA50 üzerinde"
        elif price > ema50:
            trend = "POZİTİF"
            emoji = "✅"
            message = f"BIST 100 EMA50({ema50:.0f}) üzerinde, EMA20({ema20:.0f}) altında"
        elif price < ema50 and price > ema20:
            trend = "YATAY"
            emoji = "➡️"
            message = f"BIST 100 kararsız. EMA50({ema50:.0f}) altında"
        elif price < ema20 and price < ema50:
            if ema20 < ema50:
                trend = "GÜÇLÜ AYI"
                emoji = "☠️"
                message = f"BIST 100 GÜÇLÜ AYI! Fiyat({price:.0f}) < EMA20({ema20:.0f}) < EMA50({ema50:.0f})"
            else:
                trend = "AYI"
                emoji = "🔴"
                message = f"BIST 100 AYI! Fiyat({price:.0f}) EMA20 ve EMA50 altında"
        else:
            trend = "YATAY"
            emoji = "➡️"
            message = f"BIST 100 yatay hareket"
        
        min_score = get_min_score(trend, timeframe)
        
        # Trend değişimi kontrolü (sadece günlük tarama için)
        if timeframe == 'daily':
            changed, old_trend, direction = detect_bist_trend_change(trend)
            save_bist_trend(trend)
        else:
            changed = False
            old_trend = None
            direction = None
        
        return {
            'trend': trend,
            'min_score': min_score,
            'emoji': emoji,
            'message': message,
            'price': price,
            'ema20': ema20,
            'ema50': ema50,
            'trend_changed': changed,
            'change_direction': direction,
            'old_trend': old_trend if changed else None
        }
    except Exception as e:
        print(f"⚠️ BIST 100 kontrol hatası: {e}")
        return {
            'trend': 'BİLİNMİYOR', 'min_score': 65, 'emoji': '⚪',
            'message': f'BIST 100 kontrol edilemedi: {str(e)[:50]}',
            'price': 0, 'ema20': 0, 'ema50': 0,
            'trend_changed': False, 'change_direction': None
        }


def format_bist_trend_change_alert(market_mode):
    """BIST trend değişimi uyarı mesajı"""
    if not market_mode.get('trend_changed'):
        return None
    
    direction = market_mode.get('change_direction')
    old = market_mode.get('old_trend', '?')
    new = market_mode.get('trend')
    price = market_mode.get('price', 0)
    
    if direction == "AYI_TO_BOGA":
        msg = f"""🟢🟢🟢━━━━━━━━━━━━━━━━━🟢🟢🟢
   🚀 <b>BIST 100 BOĞA'YA DÖNDÜ!</b>
🟢🟢🟢━━━━━━━━━━━━━━━━━🟢🟢🟢

📊 <b>BIST 100:</b> {price:.0f}
📉 Önceki: <b>{old}</b>
📈 Şimdi: <b>{new}</b>

✅ AL fırsatlarına odaklanabilirsin
✅ Normal tarama moduna geçildi
🎯 Min skor: {market_mode['min_score']}
"""
    elif direction == "BOGA_TO_AYI":
        msg = f"""🔴🔴🔴━━━━━━━━━━━━━━━━━🔴🔴🔴
   ⚠️ <b>BIST 100 AYI PİYASASINA GİRDİ!</b>
🔴🔴🔴━━━━━━━━━━━━━━━━━🔴🔴🔴

📊 <b>BIST 100:</b> {price:.0f}
📈 Önceki: <b>{old}</b>
📉 Şimdi: <b>{new}</b>

⚠️ Çok dikkatli ol!
⚠️ Sadece güçlü sinyallere gir
⚠️ Küçük pozisyon aç
🎯 Min skor: {market_mode['min_score']}
"""
    elif direction == "AYI_IYILESIYOR":
        msg = f"""🟡🟡🟡━━━━━━━━━━━━━━━━━🟡🟡🟡
   📈 <b>BIST 100 İYİLEŞİYOR</b>
🟡🟡🟡━━━━━━━━━━━━━━━━━🟡🟡🟡

📊 {old} → {new}
📊 BIST 100: {price:.0f}
✅ Dikkatli ama umutlu!
"""
    elif direction == "AYI_KOTULESIYOR":
        msg = f"""🔴🔴🔴━━━━━━━━━━━━━━━━━🔴🔴🔴
   📉 <b>BIST 100 KÖTÜLEŞIYOR!</b>
🔴🔴🔴━━━━━━━━━━━━━━━━━🔴🔴🔴

📊 {old} → {new}
📊 BIST 100: {price:.0f}
⚠️ Pozisyon azalt! Riskli dönem!
"""
    elif direction == "BOGA_GUCLENIYOR":
        msg = f"""🚀🚀🚀━━━━━━━━━━━━━━━━━🚀🚀🚀
   💪 <b>BIST 100 GÜÇLENİYOR!</b>
🚀🚀🚀━━━━━━━━━━━━━━━━━🚀🚀🚀

📊 {old} → {new}
📊 BIST 100: {price:.0f}
✅ Güçlü piyasa, fırsatları değerlendir!
"""
    else:
        msg = f"""📊 <b>BIST 100 TREND DEĞİŞİMİ</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 {old} → {new}
📊 BIST 100: {price:.0f}
"""
    
    return msg


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
# SAATLİK DİP DÖNÜŞÜ TESPİTİ
# ════════════════════════════════════════════════════════════

def detect_hourly_dip_reversal(analysis):
    """
    Saatlik verilerde dip dönüşü var mı kontrol et
    """
    rsi = analysis.get('rsi')
    prev_rsi = analysis.get('prev_rsi')
    wt1 = analysis.get('wt1')
    wt2 = analysis.get('wt2')
    prev_wt1 = analysis.get('prev_wt1')
    prev_wt2 = analysis.get('prev_wt2')
    
    if rsi and prev_rsi:
        if rsi < 35 and rsi > prev_rsi:
            return True, f"RSI dip dönüşü ({rsi:.1f}, yükseliyor)"
    
    if all(v is not None for v in [wt1, wt2, prev_wt1, prev_wt2]):
        if wt1 < -50 and prev_wt1 <= prev_wt2 and wt1 > wt2:
            return True, f"WaveTrend dip dönüşü (WT:{wt1:.1f})"
    
    return False, ""


# ════════════════════════════════════════════════════════════
# SAATLİK 3 TEYİT SİSTEMİ
# ════════════════════════════════════════════════════════════

def check_hourly_confirmations(symbol, hourly_analysis):
    """Saatlik sinyal için teyit kontrolü"""
    details = []
    passed_count = 0
    
    is_dip_reversal, dip_reason = detect_hourly_dip_reversal(hourly_analysis)
    
    # TEYİT 1: Günlük trend pozitif (DİP DÖNÜŞÜNDE ATLA)
    daily_positive = False
    daily_detail = "Günlük veri yok"
    
    if not is_dip_reversal:
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
        
        details.append({'check': 'Günlük trend pozitif', 'passed': daily_positive, 'value': daily_detail})
        if daily_positive: passed_count += 1
    else:
        details.append({
            'check': '🎯 DİP DÖNÜŞÜ - Günlük atlandı',
            'passed': True,
            'value': dip_reason
        })
        passed_count += 1
    
    # TEYİT 2: Son 3 saatlik mumdan 2'si yeşil
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
    
    details.append({'check': 'Son momentum (3 mumdan 2 yeşil)', 'passed': momentum_ok, 'value': momentum_detail})
    if momentum_ok: passed_count += 1
    
    # TEYİT 3: Hacim onayı (RVOL >= 1.5x)
    volume_ok = False
    rvol = hourly_analysis.get('rvol', 0)
    if rvol >= 1.5:
        volume_ok = True
        volume_detail = f"RVOL {rvol:.1f}x ✅"
    else:
        volume_detail = f"RVOL {rvol:.1f}x (< 1.5x) ❌"
    
    details.append({'check': 'Hacim onayı (RVOL >= 1.5x)', 'passed': volume_ok, 'value': volume_detail})
    if volume_ok: passed_count += 1
    
    passed = (passed_count == 3)
    
    return {
        'passed': passed,
        'details': details,
        'passed_count': passed_count,
        'is_dip_reversal': is_dip_reversal,
        'dip_reason': dip_reason if is_dip_reversal else None
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
            if not analysis: return None
            passes, reason = passes_intraday_filters(symbol, analysis)
            if not passes:
                return {'symbol': symbol.replace('.IS', ''), 'filtered': True, 'filter_reason': reason}
            signal = generate_signal(symbol, analysis)
            if not signal or signal['score'] < min_score: return None
            signal['timeframe'] = '4h'
            signal['is_4h'] = True
            signal['is_hourly'] = False
            return signal
        
        elif use_hourly:
            analysis = analyze_stock_hourly(symbol)
            if not analysis: return None
            passes, reason = passes_intraday_filters(symbol, analysis)
            if not passes:
                return {'symbol': symbol.replace('.IS', ''), 'filtered': True, 'filter_reason': reason}
            signal = generate_signal(symbol, analysis)
            if not signal or signal['score'] < min_score: return None
            
            confirmations = check_hourly_confirmations(symbol, analysis)
            if not confirmations['passed']:
                return {'symbol': symbol.replace('.IS', ''), 'filtered': True, 'filter_reason': f"Teyit yetersiz ({confirmations['passed_count']}/3)"}
            
            signal['hourly_confirmations'] = confirmations
            
            if confirmations.get('is_dip_reversal'):
                signal['is_hourly_dip_reversal'] = True
                signal['dip_reason'] = confirmations.get('dip_reason')
            
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
        
        if not data or len(data) < 20: return None
        
        df = pd.DataFrame(data)
        analysis = analyze_stock(df, timeframe='daily')
        if not analysis: return None
        
        passes, reason = passes_safety_filters(symbol, df, analysis)
        if not passes:
            return {'symbol': symbol.replace('.IS', ''), 'filtered': True, 'filter_reason': reason}
        
        signal = generate_signal(symbol, analysis, df)
        if not signal or signal['score'] < min_score: return None
        
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
            ORDER BY created_at DESC LIMIT 1
        """, (symbol, hours))
        result = cursor.fetchone()
        conn.close()
        if result: return result['score'], result['price']
        return None, None
    except:
        return None, None


def apply_smart_spam_filter(signals, hours=4, min_score_improvement=10):
    if not signals: return signals
    
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
            signal['spam_upgrade_reason'] = f"⬆️ Skor +{score_improvement}"
            filtered_signals.append(signal)
            upgraded_count += 1
            continue
        
        if price_change_pct >= 3:
            signal['spam_upgrade_reason'] = f"📊 Fiyat %{price_change_pct:.1f} değişti"
            filtered_signals.append(signal)
            upgraded_count += 1
            continue
        
        spam_filtered_count += 1
        print(f"   🔇 {symbol}: Spam filtrelendi")
    
    if spam_filtered_count > 0 or upgraded_count > 0:
        print(f"\n🎯 SPAM FİLTRESİ: 🔇 {spam_filtered_count} filtrelendi | ⬆️ {upgraded_count} yükseltildi | ✅ {len(filtered_signals)} gönderilecek")
    
    return filtered_signals


# ════════════════════════════════════════════════════════════
# 🆕 TÜM BIST TARAMA (BIST 100 FİLTRESİ - HER TARAMA İÇİN)
# ════════════════════════════════════════════════════════════

def scan_all_stocks(min_score=65, save_to_db=True, verbose=False, use_15m=False, use_hourly=False, use_4h=False, symbols_list=None, add_to_tracker=True, apply_spam_filter=True):
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    if use_4h:
        timeframe = "4 SAATLİK"
        bist_tf = '4h'
    elif use_hourly:
        timeframe = "SAATLİK (3 TEYİT)"
        bist_tf = 'hourly'
    elif use_15m:
        timeframe = "15 DAKİKALIK"
        bist_tf = 'daily'  # 15m için günlük skorlar
    else:
        timeframe = "GÜNLÜK"
        bist_tf = 'daily'
    
    # 🆕 BIST 100 KONTROLÜ - HER TARAMA İÇİN (Günlük + Saatlik + 4H)
    from telegram_bot.bot import send_message
    
    market_mode = get_bist100_market_mode(timeframe=bist_tf)
    
    bist_min = market_mode['min_score']
    effective_min_score = max(min_score, bist_min)
    
    print(f"\n{'='*60}")
    print(f"📊 BIST 100 DURUMU: {market_mode['emoji']} {market_mode['trend']}")
    print(f"📊 {market_mode['message']}")
    print(f"📊 Zaman dilimi: {timeframe}")
    print(f"📊 Normal min skor: {min_score} → Uygulanan: {effective_min_score}")
    print(f"{'='*60}")
    
    # Trend değişimi uyarısı (sadece günlük)
    if not use_hourly and not use_4h and market_mode.get('trend_changed'):
        alert_msg = format_bist_trend_change_alert(market_mode)
        if alert_msg:
            send_message(alert_msg)
            print(f"📢 BIST TREND DEĞİŞİMİ: {market_mode.get('old_trend')} → {market_mode['trend']}")
    
    print(f"\n{'='*60}")
    print(f"🔍 BIST TARAMASI - {timeframe}")
    print(f"📊 {len(symbols_list)} hisse taranacak")
    print(f"⚙️  Min skor: {effective_min_score}")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")
    
    signals = []
    filtered_out = []
    no_data = []
    tracker_added = 0
    
    for i, symbol in enumerate(symbols_list, 1):
        if i % 25 == 0 or i == len(symbols_list):
            print(f"   ⏳ {i}/{len(symbols_list)} ({i*100//len(symbols_list)}%) | Sinyal: {len(signals)}")
        
        result = scan_single_stock(symbol, effective_min_score, use_15m, use_hourly, use_4h)
        
        if result is None:
            no_data.append(symbol)
            continue
        
        if result.get('filtered'):
            filtered_out.append(result)
            continue
        
        # BIST AYI modunda sinyale market_mode bilgisi ekle
        if market_mode and market_mode['trend'] in ['AYI', 'GÜÇLÜ AYI']:
            result['bist_bear_mode'] = True
            result['bist_trend'] = market_mode['trend']
        
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
    if market_mode:
        print(f"📊 BIST MODU: {market_mode['emoji']} {market_mode['trend']} (min skor: {effective_min_score})")
    print(f"✅ Güçlü Sinyal   : {len(signals)}")
    if apply_spam_filter and original_count != len(signals):
        print(f"🔇 Spam filtrelendi: {original_count - len(signals)}")
    print(f"🚫 Filtrelendi    : {len(filtered_out)}")
    print(f"⚪ Veri Yok      : {len(no_data)}")
    print(f"📋 Toplam         : {len(symbols_list)}")
    if add_to_tracker and not use_hourly and not use_4h:
        print(f"🎯 Takibe alındı  : {tracker_added}")
    print(f"{'='*60}\n")
    
    return signals


# ════════════════════════════════════════════════════════════
# SAATLİK TARAMA (BIST 100 FİLTRELİ + DİP DÖNÜŞÜ)
# ════════════════════════════════════════════════════════════

def scan_hourly_stocks(min_score=68, symbols_list=None):
    """SAATLİK TARAMA - BIST 100 filtreli + 3 teyit + dip dönüşü"""
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS[:200]
    
    print(f"\n{'='*60}")
    print(f"⚡ SAATLİK TARAMA (3 TEYİT + BIST 100 FİLTRE + DİP DÖNÜŞÜ)")
    print(f"📊 {len(symbols_list)} hisse | Min skor: {min_score}")
    print(f"{'='*60}\n")
    
    hourly_signals = scan_all_stocks(
        min_score=min_score, save_to_db=False,
        use_hourly=True, symbols_list=symbols_list,
        add_to_tracker=False, apply_spam_filter=False
    )
    
    for signal in hourly_signals:
        signal['is_hourly'] = True
        signal['is_4h'] = False
        signal['timeframe'] = '1h'
    
    print(f"\n⚡ {len(hourly_signals)} SAATLİK SİNYAL (3 teyit onaylı)")
    return hourly_signals


# ════════════════════════════════════════════════════════════
# 4 SAATLİK TARAMA (🆕 BIST 100 FİLTRELİ)
# ════════════════════════════════════════════════════════════

def scan_4h_stocks(min_score=65, symbols_list=None):
    """4 SAATLİK TARAMA - BIST 100 filtreli"""
    if symbols_list is None:
        symbols_list = BIST_SYMBOLS
    
    print(f"\n{'='*60}")
    print(f"🕐 4 SAATLİK TARAMA (BIST 100 FİLTRELİ) | Min skor: {min_score}")
    print(f"{'='*60}\n")
    
    signals_4h = scan_all_stocks(
        min_score=min_score, save_to_db=False,
        use_4h=True, symbols_list=symbols_list,
        add_to_tracker=False, apply_spam_filter=False
    )
    
    for signal in signals_4h:
        signal['is_4h'] = True
        signal['is_hourly'] = False
        signal['timeframe'] = '4h'
    
    print(f"\n🕐 {len(signals_4h)} ADET 4H SİNYAL")
    return signals_4h


# ════════════════════════════════════════════════════════════
# ESKİ UYUMLULUK
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
    return [s for s in signals if not is_recently_sent(s['symbol'], hours)]


def scan_and_notify(min_score=70, use_15m=False, max_signals=5, spam_hours=0):
    from telegram_bot.bot import send_multiple_signals
    signals = scan_all_stocks(min_score=min_score, save_to_db=True, verbose=False, use_15m=use_15m)
    if not signals: return 0
    return send_multiple_signals(signals, max_signals=max_signals)


def print_top_signals(signals, top_n=10):
    if not signals:
        print("\n⚠️ Sinyal yok")
        return
    top = signals[:top_n]
    print(f"\n{'='*60}\n🏆 EN İYİ {len(top)} SİNYAL\n{'='*60}\n")
    for i, s in enumerate(top, 1):
        tf = s.get('timeframe', '1d')
        tag = " 🕐4H" if s.get('is_4h') else " ⚡GÜNİÇİ" if s.get('is_hourly') else ""
        print(f"{i}. {s['emoji']} {s['symbol']:<10} {s['current_price']:.2f} TL  {s['score']}/100  ({tf}){tag}")


if __name__ == "__main__":
    print("\n🚀 PROFESYONEL TARAMA MOTORU")
    print("1 → Günlük (BIST filtreli)")
    print("2 → Saatlik (3 TEYİT + BIST filtre + Dip Dönüşü)")
    print("3 → 4 Saatlik (BIST filtreli)")
    
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
