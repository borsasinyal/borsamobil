"""
Profesyonel Teknik Analiz Motoru
EMA 5/22/50/200 (Günlük) + EMA 5/22 (Saatlik) + EMA 5/22/50 (4H)
+ FIBONACCI (Normal + Extended) - Tüm timeframe'lerde 90 mum
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def calculate_rsi(data, period=14):
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data, fast=12, slow=26, signal=9):
    ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data, period=20, std_dev=2):
    sma = data['close'].rolling(window=period).mean()
    std = data['close'].rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    bb_width = ((upper_band - lower_band) / sma) * 100
    return upper_band, sma, lower_band, bb_width

def calculate_ema(data, period):
    return data['close'].ewm(span=period, adjust=False).mean()

def calculate_sma(data, period):
    return data['close'].rolling(window=period).mean()

def calculate_atr(data, period=14):
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()

def calculate_adx(data, period=14):
    high = data['high']
    low = data['low']
    close = data['close']
    plus_dm = high.diff()
    minus_dm = low.diff().abs() * -1
    plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm.abs()), 0)
    minus_dm = minus_dm.abs().where((minus_dm.abs() > 0) & (minus_dm.abs() > plus_dm), 0)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)) * 100
    adx = dx.rolling(window=period).mean()
    return adx, plus_di, minus_di

def calculate_wavetrend(data, channel_length=10, average_length=21, ma_length=4):
    hlc3 = (data['high'] + data['low'] + data['close']) / 3
    esa = hlc3.ewm(span=channel_length, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=channel_length, adjust=False).mean()
    ci = (hlc3 - esa) / (0.015 * d)
    wt1 = ci.ewm(span=average_length, adjust=False).mean()
    wt2 = wt1.rolling(window=ma_length).mean()
    return wt1, wt2

def calculate_smi(data, k_period=10, k_smooth=3, d_smooth=3):
    high_n = data['high'].rolling(window=k_period).max()
    low_n = data['low'].rolling(window=k_period).min()
    midpoint = (high_n + low_n) / 2
    range_hl = high_n - low_n
    diff = data['close'] - midpoint
    diff_smooth1 = diff.ewm(span=k_smooth, adjust=False).mean()
    diff_smooth2 = diff_smooth1.ewm(span=k_smooth, adjust=False).mean()
    range_smooth1 = range_hl.ewm(span=k_smooth, adjust=False).mean()
    range_smooth2 = range_smooth1.ewm(span=k_smooth, adjust=False).mean()
    smi = 100 * (diff_smooth2 / (range_smooth2 / 2))
    smi_signal = smi.ewm(span=d_smooth, adjust=False).mean()
    return smi, smi_signal


def calculate_pivot_points(data):
    prev_high = data['high'].shift(1)
    prev_low = data['low'].shift(1)
    prev_close = data['close'].shift(1)
    pivot = (prev_high + prev_low + prev_close) / 3
    r1 = (2 * pivot) - prev_low
    r2 = pivot + (prev_high - prev_low)
    r3 = prev_high + 2 * (pivot - prev_low)
    s1 = (2 * pivot) - prev_high
    s2 = pivot - (prev_high - prev_low)
    s3 = prev_low - 2 * (prev_high - pivot)
    return pivot, r1, r2, r3, s1, s2, s3

def calculate_supertrend(data, period=10, multiplier=3):
    atr = calculate_atr(data, period)
    hl2 = (data['high'] + data['low']) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    supertrend = pd.Series(index=data.index, dtype=float)
    direction = pd.Series(index=data.index, dtype=float)
    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1
    for i in range(1, len(data)):
        if data['close'].iloc[i] > upper_band.iloc[i - 1]: direction.iloc[i] = 1
        elif data['close'].iloc[i] < lower_band.iloc[i - 1]: direction.iloc[i] = -1
        else: direction.iloc[i] = direction.iloc[i - 1]
        if direction.iloc[i] == 1: supertrend.iloc[i] = lower_band.iloc[i]
        else: supertrend.iloc[i] = upper_band.iloc[i]
    return supertrend, direction

def calculate_relative_volume(data, period=20):
    avg_volume = data['volume'].rolling(window=period).mean()
    return data['volume'] / avg_volume.replace(0, 1)

def calculate_obv(data):
    obv = pd.Series(0, index=data.index, dtype=float)
    for i in range(1, len(data)):
        if data['close'].iloc[i] > data['close'].iloc[i - 1]: obv.iloc[i] = obv.iloc[i - 1] + data['volume'].iloc[i]
        elif data['close'].iloc[i] < data['close'].iloc[i - 1]: obv.iloc[i] = obv.iloc[i - 1] - data['volume'].iloc[i]
        else: obv.iloc[i] = obv.iloc[i - 1]
    return obv


# ════════════════════════════════════════════════════════════
# 🆕 FIBONACCI SİSTEMİ - Tüm timeframe'ler için
# ════════════════════════════════════════════════════════════

def calculate_fibonacci_analysis(df, current_price, lookback=90):
    """
    Fibonacci analizi yap - hem seviyeleri hem hedef/stop hesapla
    
    Args:
        df: DataFrame (high, low, close sütunları olmalı)
        current_price: Şu anki fiyat
        lookback: Kaç mum geriye bakılacak (varsayılan 90)
    
    Returns:
        dict: Fibonacci seviyeleri + hedef/stop
    """
    if df is None or len(df) < 20:
        return None
    
    # Lookback ayarla (veri az ise mevcut kadar)
    actual_lookback = min(lookback, len(df))
    recent = df.tail(actual_lookback)
    
    dip = float(recent['low'].min())
    zirve = float(recent['high'].max())
    
    if dip >= zirve or dip <= 0:
        return None
    
    diff = zirve - dip
    
    # ═══════════════════════════════════════
    # NORMAL FİBONACCİ SEVİYELERİ (dip'ten zirve'ye)
    # ═══════════════════════════════════════
    normal_levels = {
        'dip': dip,
        'fib_236': dip + (diff * 0.236),
        'fib_382': dip + (diff * 0.382),
        'fib_500': dip + (diff * 0.500),
        'fib_618': dip + (diff * 0.618),
        'fib_786': dip + (diff * 0.786),
        'zirve': zirve
    }
    
    # ═══════════════════════════════════════
    # EXTENDED FİBONACCİ (zirve üstü - genişleme)
    # ═══════════════════════════════════════
    extended_levels = {
        'ext_1272': zirve + (diff * 0.272),   # 1.272 seviyesi
        'ext_1414': zirve + (diff * 0.414),   # 1.414 seviyesi
        'ext_1618': zirve + (diff * 0.618),   # 1.618 Altın Genişleme
        'ext_2000': zirve + (diff * 1.000),   # 2.000
        'ext_2618': zirve + (diff * 1.618),   # 2.618 (uzak)
    }
    
    # ═══════════════════════════════════════
    # DURUM TESPİTİ
    # ═══════════════════════════════════════
    is_above_zirve = current_price > zirve
    is_below_dip = current_price < dip
    
    # Fiyat hangi seviyede?
    current_position = "normal"
    current_zone = ""
    
    if is_above_zirve:
        current_position = "extended"
        current_zone = "ZIRVE USTU - Extended bolge"
    elif is_below_dip:
        current_position = "below_dip"
        current_zone = "DIP ALTI - Riskli"
    else:
        # Hangi Fibonacci bölgesinde?
        if current_price >= normal_levels['fib_786']:
            current_zone = "0.786 - 1.0 arasi (guclu)"
        elif current_price >= normal_levels['fib_618']:
            current_zone = "0.618 - 0.786 arasi (Altin Oran ustu)"
        elif current_price >= normal_levels['fib_500']:
            current_zone = "0.5 - 0.618 arasi (orta-guclu)"
        elif current_price >= normal_levels['fib_382']:
            current_zone = "0.382 - 0.5 arasi (orta)"
        elif current_price >= normal_levels['fib_236']:
            current_zone = "0.236 - 0.382 arasi (zayif)"
        else:
            current_zone = "0.0 - 0.236 arasi (dip bolge)"
    
    # ═══════════════════════════════════════
    # HEDEF VE STOP HESABI
    # ═══════════════════════════════════════
    targets = calculate_fibonacci_targets(
        current_price, 
        normal_levels, 
        extended_levels, 
        is_above_zirve
    )
    
    return {
        'lookback': actual_lookback,
        'dip': dip,
        'zirve': zirve,
        'range': diff,
        'current_price': current_price,
        'current_position': current_position,
        'current_zone': current_zone,
        'is_above_zirve': is_above_zirve,
        'is_below_dip': is_below_dip,
        'normal_levels': normal_levels,
        'extended_levels': extended_levels,
        'targets': targets
    }


def calculate_fibonacci_targets(current_price, normal_levels, extended_levels, is_above_zirve):
    """
    Fibonacci bazlı hedef ve stop hesabı
    
    Kural:
    - Fiyat zirve altındaysa → Normal Fibonacci
    - Fiyat zirveyi kırdıysa → Extended Fibonacci
    """
    
    # Tüm seviyeleri sıralı liste yap
    all_levels = []
    
    for key, price in normal_levels.items():
        all_levels.append({'name': key, 'price': price, 'type': 'normal'})
    for key, price in extended_levels.items():
        all_levels.append({'name': key, 'price': price, 'type': 'extended'})
    
    # Fiyata göre sırala
    all_levels.sort(key=lambda x: x['price'])
    
    # Fiyatın üstündeki seviyeler = hedef adayları
    above_levels = [l for l in all_levels if l['price'] > current_price]
    # Fiyatın altındaki seviyeler = stop adayları
    below_levels = [l for l in all_levels if l['price'] < current_price]
    
    # ═══════════════════════════════════════
    # HEDEF SEÇİMİ (fiyatın üstündeki ilk 3 seviye)
    # ═══════════════════════════════════════
    if len(above_levels) >= 3:
        target_1 = above_levels[0]
        target_2 = above_levels[1]
        target_3 = above_levels[2]
    elif len(above_levels) == 2:
        target_1 = above_levels[0]
        target_2 = above_levels[1]
        # 3. hedef için extended ekle
        target_3 = {'name': 'ext_1618', 'price': extended_levels['ext_1618'], 'type': 'extended'}
    elif len(above_levels) == 1:
        target_1 = above_levels[0]
        target_2 = {'name': 'ext_1272', 'price': extended_levels['ext_1272'], 'type': 'extended'}
        target_3 = {'name': 'ext_1618', 'price': extended_levels['ext_1618'], 'type': 'extended'}
    else:
        # Fiyat çok yukarda, extended tam liste
        target_1 = {'name': 'ext_1272', 'price': extended_levels['ext_1272'], 'type': 'extended'}
        target_2 = {'name': 'ext_1414', 'price': extended_levels['ext_1414'], 'type': 'extended'}
        target_3 = {'name': 'ext_1618', 'price': extended_levels['ext_1618'], 'type': 'extended'}
    
    # ═══════════════════════════════════════
    # STOP SEÇİMİ (fiyatın altındaki en yakın seviye altı)
    # ═══════════════════════════════════════
    if below_levels:
        # En yakın alttaki seviye
        stop_level = below_levels[-1]  # En yakın alt seviye
        stop_price = stop_level['price'] * 0.995  # %0.5 altına
        stop_source = f"Fib {get_fib_display_name(stop_level['name'])} alti"
    else:
        # Alt seviye yok, dip altı stop
        stop_price = normal_levels['dip'] * 0.98
        stop_source = "Dip alti (fallback)"
    
    # Stop yüzdesi kontrol - min %2.5 max %6
    stop_pct = ((current_price - stop_price) / current_price) * 100
    
    if stop_pct < 2.5:
        stop_price = current_price * 0.975
        stop_pct = 2.5
        stop_source = "Min sinir (%2.5)"
    elif stop_pct > 6.0:
        stop_price = current_price * 0.94
        stop_pct = 6.0
        stop_source = "Max sinir (%6)"
    
    # ═══════════════════════════════════════
    # HEDEF YÜZDELER
    # ═══════════════════════════════════════
    t1_pct = ((target_1['price'] - current_price) / current_price) * 100
    t2_pct = ((target_2['price'] - current_price) / current_price) * 100
    t3_pct = ((target_3['price'] - current_price) / current_price) * 100
    
    # Risk/Reward (H2 baz alınır)
    risk = current_price - stop_price
    reward_h2 = target_2['price'] - current_price
    rr = round(reward_h2 / risk, 2) if risk > 0 else 0
    
    return {
        'entry': round(current_price, 2),
        'target_1': round(target_1['price'], 2),
        'target_1_pct': round(t1_pct, 2),
        'target_1_source': f"Fib {get_fib_display_name(target_1['name'])}",
        'target_2': round(target_2['price'], 2),
        'target_2_pct': round(t2_pct, 2),
        'target_2_source': f"Fib {get_fib_display_name(target_2['name'])}",
        'target_3': round(target_3['price'], 2),
        'target_3_pct': round(t3_pct, 2),
        'target_3_source': f"Fib {get_fib_display_name(target_3['name'])}",
        'stop_loss': round(stop_price, 2),
        'stop_pct': round(stop_pct, 2),
        'stop_source': stop_source,
        'risk_reward': rr,
        'method': 'fibonacci'
    }


def get_fib_display_name(fib_name):
    """Fibonacci seviye adını okunabilir yap"""
    display_map = {
        'dip': '0.0 (Dip)',
        'fib_236': '0.236',
        'fib_382': '0.382',
        'fib_500': '0.5',
        'fib_618': '0.618 (Altin Oran)',
        'fib_786': '0.786',
        'zirve': '1.0 (Zirve)',
        'ext_1272': '1.272 (Ext)',
        'ext_1414': '1.414 (Ext)',
        'ext_1618': '1.618 (Altin Genisleme)',
        'ext_2000': '2.0 (Ext)',
        'ext_2618': '2.618 (Ext)'
    }
    return display_map.get(fib_name, fib_name)


# ════════════════════════════════════════════════════════════
# MUM FORMASYONLARI
# ════════════════════════════════════════════════════════════

def detect_candle_patterns(data):
    patterns = {}
    o, h, l, c = data['open'], data['high'], data['low'], data['close']
    body = abs(c - o)
    upper_shadow = h - pd.concat([c, o], axis=1).max(axis=1)
    lower_shadow = pd.concat([c, o], axis=1).min(axis=1) - l
    total_range = (h - l).replace(0, 0.001)
    
    patterns['hammer'] = ((lower_shadow >= body * 2) & (upper_shadow <= body * 0.3) & (body > 0))
    patterns['inverted_hammer'] = ((upper_shadow >= body * 2) & (lower_shadow <= body * 0.3) & (body > 0))
    patterns['shooting_star'] = ((upper_shadow >= body * 2) & (lower_shadow <= body * 0.3) & (c < o) & (body > 0))
    patterns['doji'] = (body <= total_range * 0.1)
    
    prev_body_neg = data['close'].shift(1) < data['open'].shift(1)
    patterns['bullish_engulfing'] = (prev_body_neg & (c > o) & (c > data['open'].shift(1)) & (o < data['close'].shift(1)))
    
    prev_body_pos = data['close'].shift(1) > data['open'].shift(1)
    patterns['bearish_engulfing'] = (prev_body_pos & (c < o) & (c < data['open'].shift(1)) & (o > data['close'].shift(1)))
    
    prev2_bear = data['close'].shift(2) < data['open'].shift(2)
    prev1_small = abs(data['close'].shift(1) - data['open'].shift(1)) <= total_range.shift(1) * 0.3
    patterns['morning_star'] = (prev2_bear & prev1_small & (c > o) & (c > (data['open'].shift(2) + data['close'].shift(2)) / 2))
    
    prev2_bull = data['close'].shift(2) > data['open'].shift(2)
    patterns['evening_star'] = (prev2_bull & prev1_small & (c < o) & (c < (data['open'].shift(2) + data['close'].shift(2)) / 2))
    
    patterns['three_white_soldiers'] = ((c > o) & (data['close'].shift(1) > data['open'].shift(1)) & (data['close'].shift(2) > data['open'].shift(2)) & (c > data['close'].shift(1)) & (data['close'].shift(1) > data['close'].shift(2)))
    patterns['three_black_crows'] = ((c < o) & (data['close'].shift(1) < data['open'].shift(1)) & (data['close'].shift(2) < data['open'].shift(2)) & (c < data['close'].shift(1)) & (data['close'].shift(1) < data['close'].shift(2)))
    
    return patterns

def get_active_patterns(patterns, index=-1):
    active = []
    pattern_names = {
        'hammer': ('🔨', 'Çekiç', 'Dönüş yukarı', True),
        'inverted_hammer': ('🔨', 'Ters Çekiç', 'Olası dönüş', True),
        'shooting_star': ('⭐', 'Kayan Yıldız', 'Dönüş aşağı', False),
        'doji': ('➕', 'Doji', 'Kararsızlık', False),
        'bullish_engulfing': ('🟢', 'Yutan Boğa', 'GÜÇLÜ dönüş yukarı', True),
        'bearish_engulfing': ('🔴', 'Yutan Ayı', 'GÜÇLÜ dönüş aşağı', False),
        'morning_star': ('🌅', 'Sabah Yıldızı', 'Trend dönüşü yukarı', True),
        'evening_star': ('🌆', 'Akşam Yıldızı', 'Trend dönüşü aşağı', False),
        'three_white_soldiers': ('💪', '3 Beyaz Asker', 'Çok GÜÇLÜ yükseliş', True),
        'three_black_crows': ('🦅', '3 Kara Karga', 'Çok GÜÇLÜ düşüş', False),
    }
    for pattern_key, values in patterns.items():
        try:
            if values.iloc[index]:
                icon, name, meaning, bullish = pattern_names[pattern_key]
                active.append({'key': pattern_key, 'icon': icon, 'name': name, 'meaning': meaning, 'bullish': bullish})
        except: continue
    return active


def detect_breakouts(data, lookback_periods=[5, 10, 20, 50]):
    breakouts = []
    current_price = data['close'].iloc[-1]
    current_volume = data['volume'].iloc[-1]
    avg_volume = data['volume'].tail(20).mean()
    for period in lookback_periods:
        if len(data) < period: continue
        high_n = data['high'].tail(period).max()
        low_n = data['low'].tail(period).min()
        if current_price >= high_n and current_volume > avg_volume * 1.5:
            breakouts.append({'type': 'UP', 'period': period, 'level': high_n, 'icon': '🚀',
                            'detail': f'{period} günlük zirve kırıldı ({high_n:.2f} TL)',
                            'meaning': f'{period} gündür görülmemiş seviye'})
        elif current_price <= low_n:
            breakouts.append({'type': 'DOWN', 'period': period, 'level': low_n, 'icon': '⚠️',
                            'detail': f'{period} günlük dip ({low_n:.2f} TL)', 'meaning': 'Düşüş devam'})
    return breakouts

def detect_support_resistance(data, window=20):
    levels = []
    recent = data.tail(window)
    current_price = data['close'].iloc[-1]
    for h in recent['high'].nlargest(3).values:
        if h > current_price * 1.005:
            levels.append({'type': 'resistance', 'price': float(h), 'distance_pct': round(((h - current_price) / current_price) * 100, 2)})
    for lo in recent['low'].nsmallest(3).values:
        if lo < current_price * 0.995:
            levels.append({'type': 'support', 'price': float(lo), 'distance_pct': round(((current_price - lo) / current_price) * 100, 2)})
    return levels


def detect_momentum_status(data, analysis):
    status = {'direction': 'NEUTRAL', 'strength': 'NORMAL', 'warning': None, 'suggestion': None}
    rsi = analysis.get('rsi')
    prev_rsi = analysis.get('prev_rsi')
    macd_hist = analysis.get('macd_hist')
    prev_macd_hist = analysis.get('prev_macd_hist')
    volume_ratio = analysis.get('rvol')
    
    if rsi and prev_rsi:
        if rsi > prev_rsi and rsi > 50: status['direction'] = 'UP'
        elif rsi < prev_rsi and rsi > 65:
            status['direction'] = 'WEAKENING'
            status['warning'] = '⚠️ RSI zayıflıyor'
            status['suggestion'] = 'Kısmi kar al düşün'
    if macd_hist is not None and prev_macd_hist is not None:
        if macd_hist > 0 and macd_hist < prev_macd_hist:
            status['direction'] = 'WEAKENING'
            status['warning'] = '⚠️ MACD histogram azalıyor'
    if rsi and rsi > 75:
        status['direction'] = 'OVERBOUGHT'
        status['warning'] = '🔴 RSI aşırı alım!'
        status['suggestion'] = 'KAR AL!'
    if volume_ratio and volume_ratio < 0.5:
        if status['warning']: status['warning'] += '\n⚠️ Hacim düşük'
        else: status['warning'] = '⚠️ Hacim düşük'
    return status


# ════════════════════════════════════════════════════════════
# ANA ANALİZ FONKSİYONU
# ════════════════════════════════════════════════════════════

def analyze_stock(df, timeframe='daily'):
    """
    Tüm indikatörleri hesapla + Fibonacci analizi
    
    timeframe:
    - 'daily' → EMA 5/22/50/200 + Fibonacci (90 günlük mum)
    - 'hourly' → EMA 5/22 + Fibonacci (90 saatlik mum)
    - '4h' → EMA 5/22/50 + Fibonacci (90 tane 4H mum)
    """
    if len(df) < 20:
        return None

    df = df.sort_values('date').reset_index(drop=True)
    
    df['rsi'] = calculate_rsi(df)
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df)
    df['bb_upper'], df['bb_middle'], df['bb_lower'], df['bb_width'] = calculate_bollinger_bands(df)
    
    # EMA'lar
    df['ema_5'] = calculate_ema(df, 5)
    df['ema_22'] = calculate_ema(df, 22)
    
    if timeframe == 'daily':
        df['ema_20'] = calculate_ema(df, 20)
    else:
        df['ema_20'] = pd.Series([None] * len(df))
    
    if timeframe == 'hourly':
        df['ema_50'] = pd.Series([None] * len(df))
        df['ema_200'] = pd.Series([None] * len(df))
    elif timeframe == '4h':
        df['ema_50'] = calculate_ema(df, min(50, len(df)-1)) if len(df) > 50 else calculate_ema(df, max(5, len(df)//2))
        df['ema_200'] = pd.Series([None] * len(df))
    else:
        df['ema_50'] = calculate_ema(df, min(50, len(df)-1)) if len(df) > 50 else calculate_ema(df, max(5, len(df)//2))
        df['ema_200'] = calculate_ema(df, min(200, len(df)-1)) if len(df) > 200 else pd.Series([None] * len(df))
    
    df['sma_200'] = calculate_sma(df, 200) if len(df) >= 200 else pd.Series([None] * len(df))
    df['atr'] = calculate_atr(df)

    try: df['wt1'], df['wt2'] = calculate_wavetrend(df)
    except: df['wt1'] = df['wt2'] = pd.Series([None] * len(df))

    try: df['smi'], df['smi_signal'] = calculate_smi(df)
    except: df['smi'] = df['smi_signal'] = pd.Series([None] * len(df))

    try: df['adx'], df['plus_di'], df['minus_di'] = calculate_adx(df)
    except: df['adx'] = df['plus_di'] = df['minus_di'] = pd.Series([None] * len(df))

    df['vwap'] = pd.Series([None] * len(df))
    df['pivot'], df['r1'], df['r2'], df['r3'], df['s1'], df['s2'], df['s3'] = calculate_pivot_points(df)

    try: df['supertrend'], df['supertrend_dir'] = calculate_supertrend(df)
    except: df['supertrend'] = df['supertrend_dir'] = pd.Series([None] * len(df))

    df['rvol'] = calculate_relative_volume(df)
    df['obv'] = calculate_obv(df)

    patterns = detect_candle_patterns(df)
    active_patterns = get_active_patterns(patterns, -1)
    breakouts = detect_breakouts(df)
    sr_levels = detect_support_resistance(df)

    prev_day_high = float(df['high'].iloc[-2]) if len(df) > 1 else None
    prev_day_low = float(df['low'].iloc[-2]) if len(df) > 1 else None

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    avg_volume_5 = float(df['volume'].tail(5).mean()) if len(df) >= 5 else 0
    current_price_val = float(last['close'])
    
    # 🆕 FIBONACCI ANALİZİ (Her timeframe için 90 mum)
    fibonacci = calculate_fibonacci_analysis(df, current_price_val, lookback=90)

    def sf(value):
        if value is None: return None
        try:
            if pd.isna(value): return None
            return float(value)
        except: return None

    result = {
        'timeframe': timeframe,
        'current_price': sf(last['close']), 'open': sf(last['open']),
        'high': sf(last['high']), 'low': sf(last['low']),
        'volume': sf(last['volume']), 'avg_volume_5': avg_volume_5,
        'rsi': sf(last['rsi']), 'prev_rsi': sf(prev['rsi']),
        'macd': sf(last['macd']), 'macd_signal': sf(last['macd_signal']),
        'macd_hist': sf(last['macd_hist']),
        'prev_macd': sf(prev['macd']), 'prev_macd_signal': sf(prev['macd_signal']),
        'prev_macd_hist': sf(prev['macd_hist']),
        'bb_upper': sf(last['bb_upper']), 'bb_middle': sf(last['bb_middle']),
        'bb_lower': sf(last['bb_lower']), 'bb_width': sf(last['bb_width']),
        
        'ema_5': sf(last['ema_5']), 'ema_22': sf(last['ema_22']),
        'ema_20': sf(last['ema_20']),
        'ema_50': sf(last['ema_50']), 'ema_200': sf(last['ema_200']),
        'sma_200': sf(last['sma_200']),
        'prev_ema_5': sf(prev['ema_5']), 'prev_ema_22': sf(prev['ema_22']),
        'prev_ema_20': sf(prev['ema_20']),
        'prev_ema_50': sf(prev['ema_50']), 'prev_ema_200': sf(prev['ema_200']),
        
        'wt1': sf(last['wt1']), 'wt2': sf(last['wt2']),
        'prev_wt1': sf(prev['wt1']), 'prev_wt2': sf(prev['wt2']),
        'smi': sf(last['smi']), 'smi_signal': sf(last['smi_signal']),
        'prev_smi': sf(prev['smi']), 'prev_smi_signal': sf(prev['smi_signal']),
        'atr': sf(last['atr']), 'adx': sf(last['adx']),
        'plus_di': sf(last['plus_di']), 'minus_di': sf(last['minus_di']),
        'vwap': None,
        'pivot': sf(last['pivot']), 'r1': sf(last['r1']), 'r2': sf(last['r2']),
        'r3': sf(last['r3']), 's1': sf(last['s1']), 's2': sf(last['s2']), 's3': sf(last['s3']),
        'supertrend': sf(last['supertrend']), 'supertrend_dir': sf(last['supertrend_dir']),
        'rvol': sf(last['rvol']), 'obv': sf(last['obv']),
        'prev_day_high': prev_day_high, 'prev_day_low': prev_day_low,
        'prev_day_close': float(df['close'].iloc[-2]) if len(df) > 1 else None,
        'prev_close': sf(prev['close']),
        'candle_patterns': active_patterns, 'breakouts': breakouts,
        'support_resistance': sr_levels,
        
        # 🆕 FIBONACCI SONUÇLARI
        'fibonacci': fibonacci,
    }

    result['momentum_status'] = detect_momentum_status(df, result)
    return result


def analyze_stock_hourly(symbol):
    try:
        from services.tradingview_fetcher import fetch_stock_tv, TV_AVAILABLE
        if not TV_AVAILABLE:
            return None
        data = fetch_stock_tv(symbol, n_bars=100, interval='hourly')
        if not data or len(data) < 20:
            return None
        df = pd.DataFrame(data)
        return analyze_stock(df, timeframe='hourly')
    except:
        return None


def analyze_stock_4h(symbol):
    try:
        from services.tradingview_fetcher import fetch_stock_tv, TV_AVAILABLE
        if not TV_AVAILABLE:
            return None
        data = fetch_stock_tv(symbol, n_bars=150, interval='4h')
        if not data or len(data) < 20:
            return None
        df = pd.DataFrame(data)
        return analyze_stock(df, timeframe='4h')
    except:
        return None


if __name__ == "__main__":
    print("✅ Analyzer v3 - EMA 5/22/50/200 + FIBONACCI (Normal + Extended)")
