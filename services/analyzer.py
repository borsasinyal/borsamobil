"""
Profesyonel Teknik Analiz Motoru - Day Trading
VWAP, Pivot, Supertrend, Mum Formasyonları, Multi-TF

NOT: VWAP KALDIRILDI - Günlük veride yanlış hesap yapıyordu
     (cumsum 365 gün toplam = anlamsız değer)
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ════════════════════════════════════════════════════════════
# TEMEL İNDİKATÖRLER
# ════════════════════════════════════════════════════════════

def calculate_rsi(data, period=14):
    """RSI hesaplar"""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(data, fast=12, slow=26, signal=9):
    """MACD hesaplar"""
    ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(data, period=20, std_dev=2):
    """Bollinger Bands hesaplar"""
    sma = data['close'].rolling(window=period).mean()
    std = data['close'].rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    bb_width = ((upper_band - lower_band) / sma) * 100
    return upper_band, sma, lower_band, bb_width


def calculate_ema(data, period):
    """EMA hesaplar"""
    return data['close'].ewm(span=period, adjust=False).mean()


def calculate_sma(data, period):
    """SMA hesaplar"""
    return data['close'].rolling(window=period).mean()


def calculate_stochastic(data, period=14, smooth_k=3, smooth_d=3):
    """Stochastic Oscillator"""
    low_min = data['low'].rolling(window=period).min()
    high_max = data['high'].rolling(window=period).max()
    k = 100 * ((data['close'] - low_min) / (high_max - low_min))
    k_smooth = k.rolling(window=smooth_k).mean()
    d = k_smooth.rolling(window=smooth_d).mean()
    return k_smooth, d


def calculate_atr(data, period=14):
    """ATR - Volatilite"""
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr


def calculate_adx(data, period=14):
    """ADX - Trend gücü"""
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


# ════════════════════════════════════════════════════════════
# VWAP KALDIRILDI - Günlük veride yanlış hesap yapıyordu
# ════════════════════════════════════════════════════════════
# def calculate_vwap(data):
#     """
#     VWAP (Volume Weighted Average Price)
#     KALDIRILDI: cumsum (365 gün toplam) anlamsız değer üretiyordu
#     Örnek: OSMEN fiyat 7.98 TL, VWAP 8.92 TL gösteriyordu (yanlış!)
#     """
#     typical_price = (data['high'] + data['low'] + data['close']) / 3
#     cumulative_tp_vol = (typical_price * data['volume']).cumsum()
#     cumulative_vol = data['volume'].cumsum()
#     vwap = cumulative_tp_vol / cumulative_vol.replace(0, 1)
#     return vwap


# ════════════════════════════════════════════════════════════
# PROFESYONEL DAY TRADING İNDİKATÖRLERİ
# ════════════════════════════════════════════════════════════

def calculate_pivot_points(data):
    """
    Pivot Points (P, R1, R2, R3, S1, S2, S3)
    Önceki günün H/L/C verisinden hesaplanır
    Gün içi destek/direnç seviyeleri
    """
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
    """
    Supertrend - Trend yönü belirleyici
    Yeşil = Yükseliş trendi
    Kırmızı = Düşüş trendi
    """
    atr = calculate_atr(data, period)

    hl2 = (data['high'] + data['low']) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)

    supertrend = pd.Series(index=data.index, dtype=float)
    direction = pd.Series(index=data.index, dtype=float)

    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(data)):
        if data['close'].iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif data['close'].iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        if direction.iloc[i] == 1:
            supertrend.iloc[i] = lower_band.iloc[i]
        else:
            supertrend.iloc[i] = upper_band.iloc[i]

    return supertrend, direction


def calculate_relative_volume(data, period=20):
    """
    Göreceli Hacim (RVOL)
    1.0 = Normal
    2.0 = 2 kat normalin üstünde
    3.0+ = Anormal yüksek (dikkat!)
    """
    avg_volume = data['volume'].rolling(window=period).mean()
    rvol = data['volume'] / avg_volume.replace(0, 1)
    return rvol


def calculate_obv(data):
    """
    OBV (On Balance Volume) - Akıllı para takibi
    Fiyat düşerken OBV yükselirse → Dip alım (pozitif divergence)
    Fiyat yükselirken OBV düşerse → Dağıtım (negatif divergence)
    """
    obv = pd.Series(0, index=data.index, dtype=float)
    for i in range(1, len(data)):
        if data['close'].iloc[i] > data['close'].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] + data['volume'].iloc[i]
        elif data['close'].iloc[i] < data['close'].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] - data['volume'].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i - 1]
    return obv


def calculate_williams_r(data, period=14):
    """Williams %R - Momentum"""
    high_max = data['high'].rolling(window=period).max()
    low_min = data['low'].rolling(window=period).min()
    wr = -100 * ((high_max - data['close']) / (high_max - low_min).replace(0, 1))
    return wr


def calculate_cci(data, period=20):
    """CCI - Commodity Channel Index"""
    tp = (data['high'] + data['low'] + data['close']) / 3
    sma_tp = tp.rolling(window=period).mean()
    mean_dev = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    cci = (tp - sma_tp) / (0.015 * mean_dev.replace(0, 1))
    return cci


# ════════════════════════════════════════════════════════════
# MUM FORMASYONLARI (Candlestick Patterns)
# ════════════════════════════════════════════════════════════

def detect_candle_patterns(data):
    """
    10 kritik mum formasyonu tespit eder
    """
    patterns = {}

    o = data['open']
    h = data['high']
    l = data['low']
    c = data['close']
    body = abs(c - o)
    upper_shadow = h - pd.concat([c, o], axis=1).max(axis=1)
    lower_shadow = pd.concat([c, o], axis=1).min(axis=1) - l
    total_range = (h - l).replace(0, 0.001)

    # 1. Hammer (Çekiç) - Dönüş yukarı
    patterns['hammer'] = (
            (lower_shadow >= body * 2) &
            (upper_shadow <= body * 0.3) &
            (body > 0)
    )

    # 2. Inverted Hammer (Ters Çekiç) - Dönüş yukarı
    patterns['inverted_hammer'] = (
            (upper_shadow >= body * 2) &
            (lower_shadow <= body * 0.3) &
            (body > 0)
    )

    # 3. Shooting Star (Kayan Yıldız) - Dönüş aşağı
    patterns['shooting_star'] = (
            (upper_shadow >= body * 2) &
            (lower_shadow <= body * 0.3) &
            (c < o) &
            (body > 0)
    )

    # 4. Doji - Kararsızlık
    patterns['doji'] = (body <= total_range * 0.1)

    # 5. Bullish Engulfing (Yutan Boğa) - Güçlü dönüş yukarı
    prev_body_neg = data['close'].shift(1) < data['open'].shift(1)
    patterns['bullish_engulfing'] = (
            prev_body_neg &
            (c > o) &
            (c > data['open'].shift(1)) &
            (o < data['close'].shift(1))
    )

    # 6. Bearish Engulfing (Yutan Ayı) - Güçlü dönüş aşağı
    prev_body_pos = data['close'].shift(1) > data['open'].shift(1)
    patterns['bearish_engulfing'] = (
            prev_body_pos &
            (c < o) &
            (c < data['open'].shift(1)) &
            (o > data['close'].shift(1))
    )

    # 7. Morning Star (Sabah Yıldızı) - Güçlü dönüş yukarı (3 mum)
    prev2_bear = data['close'].shift(2) < data['open'].shift(2)
    prev1_small = abs(data['close'].shift(1) - data['open'].shift(1)) <= total_range.shift(1) * 0.3
    patterns['morning_star'] = (
            prev2_bear &
            prev1_small &
            (c > o) &
            (c > (data['open'].shift(2) + data['close'].shift(2)) / 2)
    )

    # 8. Evening Star (Akşam Yıldızı) - Güçlü dönüş aşağı (3 mum)
    prev2_bull = data['close'].shift(2) > data['open'].shift(2)
    patterns['evening_star'] = (
            prev2_bull &
            prev1_small &
            (c < o) &
            (c < (data['open'].shift(2) + data['close'].shift(2)) / 2)
    )

    # 9. Three White Soldiers (3 Beyaz Asker) - Güçlü yükseliş
    patterns['three_white_soldiers'] = (
            (c > o) &
            (data['close'].shift(1) > data['open'].shift(1)) &
            (data['close'].shift(2) > data['open'].shift(2)) &
            (c > data['close'].shift(1)) &
            (data['close'].shift(1) > data['close'].shift(2))
    )

    # 10. Three Black Crows (3 Kara Karga) - Güçlü düşüş
    patterns['three_black_crows'] = (
            (c < o) &
            (data['close'].shift(1) < data['open'].shift(1)) &
            (data['close'].shift(2) < data['open'].shift(2)) &
            (c < data['close'].shift(1)) &
            (data['close'].shift(1) < data['close'].shift(2))
    )

    return patterns


def get_active_patterns(patterns, index=-1):
    """Son mumda hangi formasyonlar aktif?"""
    active = []
    pattern_names = {
        'hammer': ('🔨', 'Çekiç', 'Dönüş yukarı sinyali'),
        'inverted_hammer': ('🔨', 'Ters Çekiç', 'Olası dönüş yukarı'),
        'shooting_star': ('⭐', 'Kayan Yıldız', 'Dönüş aşağı sinyali'),
        'doji': ('➕', 'Doji', 'Kararsızlık - yön değişebilir'),
        'bullish_engulfing': ('🟢', 'Yutan Boğa', 'GÜÇLÜ dönüş yukarı'),
        'bearish_engulfing': ('🔴', 'Yutan Ayı', 'GÜÇLÜ dönüş aşağı'),
        'morning_star': ('🌅', 'Sabah Yıldızı', 'Trend dönüşü yukarı'),
        'evening_star': ('🌆', 'Akşam Yıldızı', 'Trend dönüşü aşağı'),
        'three_white_soldiers': ('💪', '3 Beyaz Asker', 'Çok GÜÇLÜ yükseliş'),
        'three_black_crows': ('🦅', '3 Kara Karga', 'Çok GÜÇLÜ düşüş'),
    }

    for pattern_key, values in patterns.items():
        try:
            if values.iloc[index]:
                icon, name, meaning = pattern_names[pattern_key]
                bullish = pattern_key in [
                    'hammer', 'inverted_hammer', 'bullish_engulfing',
                    'morning_star', 'three_white_soldiers'
                ]
                active.append({
                    'key': pattern_key,
                    'icon': icon,
                    'name': name,
                    'meaning': meaning,
                    'bullish': bullish
                })
        except (IndexError, KeyError):
            continue

    return active


# ════════════════════════════════════════════════════════════
# KIRILIM TESPİTİ
# ════════════════════════════════════════════════════════════

def detect_breakouts(data, lookback_periods=[5, 10, 20, 50]):
    """
    Çeşitli periyotlarda kırılım tespiti
    """
    breakouts = []
    current_price = data['close'].iloc[-1]
    current_volume = data['volume'].iloc[-1]
    avg_volume = data['volume'].tail(20).mean()

    for period in lookback_periods:
        if len(data) < period:
            continue

        high_n = data['high'].tail(period).max()
        low_n = data['low'].tail(period).min()

        # Yukarı kırılım
        if current_price >= high_n and current_volume > avg_volume * 1.5:
            breakouts.append({
                'type': 'UP',
                'period': period,
                'level': high_n,
                'icon': '🚀',
                'detail': f'{period} günlük zirve kırıldı ({high_n:.2f} TL)',
                'meaning': f'{period} gündür görülmemiş seviye, hacimle kırılım'
            })

        # Aşağı kırılım (uyarı)
        elif current_price <= low_n:
            breakouts.append({
                'type': 'DOWN',
                'period': period,
                'level': low_n,
                'icon': '⚠️',
                'detail': f'{period} günlük dip kırıldı ({low_n:.2f} TL)',
                'meaning': 'Tehlike, düşüş devam edebilir'
            })

    return breakouts


def detect_support_resistance(data, window=20):
    """
    Dinamik destek ve direnç seviyeleri
    """
    levels = []

    # Son window gün içindeki önemli seviyeler
    recent = data.tail(window)
    current_price = data['close'].iloc[-1]

    # Direnç seviyeleri (fiyatın üstü)
    highs = recent['high'].nlargest(3).values
    for h in highs:
        if h > current_price * 1.005:
            levels.append({
                'type': 'resistance',
                'price': float(h),
                'distance_pct': round(((h - current_price) / current_price) * 100, 2)
            })

    # Destek seviyeleri (fiyatın altı)
    lows = recent['low'].nsmallest(3).values
    for lo in lows:
        if lo < current_price * 0.995:
            levels.append({
                'type': 'support',
                'price': float(lo),
                'distance_pct': round(((current_price - lo) / current_price) * 100, 2)
            })

    return levels


# ════════════════════════════════════════════════════════════
# MOMENTUM DURUMU
# ════════════════════════════════════════════════════════════

def detect_momentum_status(data, analysis):
    """
    Momentum güçleniyor mu, zayıflıyor mu?
    Kar al uyarısı gerekiyor mu?
    """
    status = {
        'direction': 'NEUTRAL',
        'strength': 'NORMAL',
        'warning': None,
        'suggestion': None
    }

    rsi = analysis.get('rsi')
    prev_rsi = analysis.get('prev_rsi')
    macd_hist = analysis.get('macd_hist')
    prev_macd_hist = analysis.get('prev_macd_hist')
    volume_ratio = analysis.get('rvol')

    # RSI momentum kontrolü
    if rsi and prev_rsi:
        if rsi > prev_rsi and rsi > 50:
            status['direction'] = 'UP'
        elif rsi < prev_rsi and rsi > 65:
            status['direction'] = 'WEAKENING'
            status['warning'] = '⚠️ RSI zayıflıyor, momentum azalıyor'
            status['suggestion'] = 'Kısmi kar al düşün'

    # MACD histogram kontrolü
    if macd_hist is not None and prev_macd_hist is not None:
        if macd_hist > 0 and macd_hist < prev_macd_hist:
            if status['direction'] != 'WEAKENING':
                status['direction'] = 'WEAKENING'
            status['warning'] = '⚠️ MACD histogram azalıyor'
            status['suggestion'] = 'Kârdasın ise kısmi satış düşün'

    # Aşırı alım bölgesi
    if rsi and rsi > 75:
        status['direction'] = 'OVERBOUGHT'
        status['warning'] = '🔴 RSI aşırı alım bölgesinde!'
        status['suggestion'] = 'KAR AL! Düzeltme gelebilir'
        status['strength'] = 'CRITICAL'

    if rsi and rsi > 80:
        status['warning'] = '🔴🔴 RSI ÇOK YÜKSEK! Düzeltme yakın!'
        status['suggestion'] = 'HEMEN KAR AL!'
        status['strength'] = 'EXTREME'

    # Hacim düşüşü kontrolü
    if volume_ratio and volume_ratio < 0.5:
        if status['warning']:
            status['warning'] += '\n⚠️ Hacim çok düşük, hareket sahte olabilir'
        else:
            status['warning'] = '⚠️ Hacim düşük, dikkatli ol'

    return status


# ════════════════════════════════════════════════════════════
# ANA ANALİZ FONKSİYONU
# ════════════════════════════════════════════════════════════

def analyze_stock(df):
    """
    Bir hisse için TÜM profesyonel indikatörleri hesaplar
    NOT: VWAP kaldırıldı - günlük veride yanlış hesap yapıyordu
    """
    if len(df) < 50:
        return None

    df = df.sort_values('date').reset_index(drop=True)

    # ── TEMEL İNDİKATÖRLER ──
    df['rsi'] = calculate_rsi(df)
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df)
    df['bb_upper'], df['bb_middle'], df['bb_lower'], df['bb_width'] = calculate_bollinger_bands(df)
    df['ema_9'] = calculate_ema(df, 9)
    df['ema_21'] = calculate_ema(df, 21)
    df['ema_50'] = calculate_ema(df, 50)
    df['sma_200'] = calculate_sma(df, 200) if len(df) >= 200 else pd.Series([None] * len(df))
    df['stoch_k'], df['stoch_d'] = calculate_stochastic(df)
    df['atr'] = calculate_atr(df)

    try:
        df['adx'], df['plus_di'], df['minus_di'] = calculate_adx(df)
    except Exception:
        df['adx'] = df['plus_di'] = df['minus_di'] = pd.Series([None] * len(df))

    # ── PROFESYONEL İNDİKATÖRLER ──
    # VWAP KALDIRILDI - günlük veride yanlış hesap yapıyordu
    df['vwap'] = pd.Series([None] * len(df))  # VWAP devre dışı
    df['pivot'], df['r1'], df['r2'], df['r3'], df['s1'], df['s2'], df['s3'] = calculate_pivot_points(df)

    try:
        df['supertrend'], df['supertrend_dir'] = calculate_supertrend(df)
    except Exception:
        df['supertrend'] = df['supertrend_dir'] = pd.Series([None] * len(df))

    df['rvol'] = calculate_relative_volume(df)
    df['obv'] = calculate_obv(df)
    df['williams_r'] = calculate_williams_r(df)
    df['cci'] = calculate_cci(df)

    # ── MUM FORMASYONLARI ──
    patterns = detect_candle_patterns(df)
    active_patterns = get_active_patterns(patterns, -1)

    # ── KIRILIMLAR ──
    breakouts = detect_breakouts(df)

    # ── DESTEK/DİRENÇ ──
    sr_levels = detect_support_resistance(df)

    # ── ÖNCEKİ GÜN VERİLERİ ──
    prev_day_high = float(df['high'].iloc[-2]) if len(df) > 1 else None
    prev_day_low = float(df['low'].iloc[-2]) if len(df) > 1 else None
    prev_day_close = float(df['close'].iloc[-2]) if len(df) > 1 else None

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    prev2 = df.iloc[-3] if len(df) > 2 else prev

    def sf(value):
        """Safe float"""
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    result = {
        # Fiyat
        'current_price': sf(last['close']),
        'open': sf(last['open']),
        'high': sf(last['high']),
        'low': sf(last['low']),
        'volume': sf(last['volume']),

        # Temel
        'rsi': sf(last['rsi']),
        'prev_rsi': sf(prev['rsi']),
        'macd': sf(last['macd']),
        'macd_signal': sf(last['macd_signal']),
        'macd_hist': sf(last['macd_hist']),
        'prev_macd': sf(prev['macd']),
        'prev_macd_signal': sf(prev['macd_signal']),
        'prev_macd_hist': sf(prev['macd_hist']),

        # Bollinger
        'bb_upper': sf(last['bb_upper']),
        'bb_middle': sf(last['bb_middle']),
        'bb_lower': sf(last['bb_lower']),
        'bb_width': sf(last['bb_width']),

        # EMA'lar
        'ema_9': sf(last['ema_9']),
        'ema_21': sf(last['ema_21']),
        'ema_50': sf(last['ema_50']),
        'sma_200': sf(last['sma_200']),
        'prev_ema_9': sf(prev['ema_9']),
        'prev_ema_21': sf(prev['ema_21']),
        'prev_ema_50': sf(prev['ema_50']),

        # Stochastic
        'stoch_k': sf(last['stoch_k']),
        'stoch_d': sf(last['stoch_d']),

        # ATR & ADX
        'atr': sf(last['atr']),
        'adx': sf(last['adx']),
        'plus_di': sf(last['plus_di']),
        'minus_di': sf(last['minus_di']),

        # Profesyonel
        'vwap': None,  # VWAP KALDIRILDI - günlük veride yanlış hesap
        'pivot': sf(last['pivot']),
        'r1': sf(last['r1']),
        'r2': sf(last['r2']),
        'r3': sf(last['r3']),
        's1': sf(last['s1']),
        's2': sf(last['s2']),
        's3': sf(last['s3']),
        'supertrend': sf(last['supertrend']),
        'supertrend_dir': sf(last['supertrend_dir']),
        'rvol': sf(last['rvol']),
        'obv': sf(last['obv']),
        'williams_r': sf(last['williams_r']),
        'cci': sf(last['cci']),

        # Önceki gün
        'prev_day_high': prev_day_high,
        'prev_day_low': prev_day_low,
        'prev_day_close': prev_day_close,
        'prev_close': sf(prev['close']),

        # Mum formasyonları
        'candle_patterns': active_patterns,

        # Kırılımlar
        'breakouts': breakouts,

        # Destek/Direnç
        'support_resistance': sr_levels,
    }

    # Momentum durumu
    result['momentum_status'] = detect_momentum_status(df, result)

    return result


def print_analysis(symbol, result):
    """Detaylı analiz yazdır"""
    if not result:
        print(f"❌ {symbol} analiz yok")
        return

    p = result
    print(f"\n{'='*60}")
    print(f"📊 {symbol} - PROFESYONEL ANALİZ")
    print(f"{'='*60}")
    print(f"💰 Fiyat: {p['current_price']:.2f} TL")

    print(f"\n📈 MOMENTUM:")
    if p['rsi']: print(f"   RSI       : {p['rsi']:.1f}")
    if p['stoch_k']: print(f"   Stoch K   : {p['stoch_k']:.1f}")
    if p['williams_r']: print(f"   Williams  : {p['williams_r']:.1f}")
    if p['cci']: print(f"   CCI       : {p['cci']:.1f}")

    print(f"\n📊 TREND:")
    if p['macd']: print(f"   MACD      : {p['macd']:.4f}")
    if p['ema_9']: print(f"   EMA 9     : {p['ema_9']:.2f}")
    if p['ema_21']: print(f"   EMA 21    : {p['ema_21']:.2f}")
    if p['ema_50']: print(f"   EMA 50    : {p['ema_50']:.2f}")
    if p['adx']: print(f"   ADX       : {p['adx']:.1f}")
    if p['supertrend_dir']: print(f"   Supertrend: {'🟢 YUKARI' if p['supertrend_dir'] == 1 else '🔴 AŞAĞI'}")

    print(f"\n⭐ PİVOT POINTS:")
    if p['pivot']: print(f"   Pivot     : {p['pivot']:.2f}")
    if p['r1']: print(f"   R1        : {p['r1']:.2f}")
    if p['r2']: print(f"   R2        : {p['r2']:.2f}")
    if p['s1']: print(f"   S1        : {p['s1']:.2f}")

    print(f"\n💥 HACİM:")
    if p['rvol']: print(f"   RVOL      : {p['rvol']:.2f}x  {'🔥' if p['rvol'] > 2 else '🟡' if p['rvol'] > 1.5 else ''}")

    if p['candle_patterns']:
        print(f"\n🕯️ MUM FORMASYONLARI:")
        for cp in p['candle_patterns']:
            print(f"   {cp['icon']} {cp['name']}: {cp['meaning']}")

    if p['breakouts']:
        print(f"\n🚀 KIRILIMLAR:")
        for br in p['breakouts']:
            print(f"   {br['icon']} {br['detail']}")

    if p['momentum_status']['warning']:
        print(f"\n⚠️ MOMENTUM UYARISI:")
        print(f"   {p['momentum_status']['warning']}")
        if p['momentum_status']['suggestion']:
            print(f"   💡 {p['momentum_status']['suggestion']}")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    from database import get_stock_history

    test_symbols = ["AKBNK.IS", "THYAO.IS", "ASELS.IS", "AEFES.IS", "AKSA.IS"]

    for symbol in test_symbols:
        print(f"\n🧪 Test: {symbol}")
        data = get_stock_history(symbol, days=300)
        if data:
            df = pd.DataFrame(data)
            result = analyze_stock(df)
            print_analysis(symbol, result)
        else:
            print(f"   ❌ Veri yok")

    print("\n✅ Tüm testler tamamlandı!")
