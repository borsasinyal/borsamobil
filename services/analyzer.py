"""
Teknik Analiz Motoru
RSI, MACD, Bollinger Bands, EMA, Stochastic vb. hesaplar
"""

import pandas as pd
import numpy as np
import sys
import os

# Üst klasördeki dosyaları import edebilmek için
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def calculate_rsi(data, period=14):
    """RSI (Relative Strength Index) hesaplar"""
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
    return upper_band, sma, lower_band


def calculate_ema(data, period):
    """EMA (Exponential Moving Average) hesaplar"""
    return data['close'].ewm(span=period, adjust=False).mean()


def calculate_sma(data, period):
    """SMA (Simple Moving Average) hesaplar"""
    return data['close'].rolling(window=period).mean()


def calculate_stochastic(data, period=14, smooth_k=3, smooth_d=3):
    """Stochastic Oscillator hesaplar"""
    low_min = data['low'].rolling(window=period).min()
    high_max = data['high'].rolling(window=period).max()
    k_percent = 100 * ((data['close'] - low_min) / (high_max - low_min))
    k_percent_smooth = k_percent.rolling(window=smooth_k).mean()
    d_percent = k_percent_smooth.rolling(window=smooth_d).mean()
    return k_percent_smooth, d_percent


def calculate_atr(data, period=14):
    """ATR (Average True Range) - Volatilite ölçer"""
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr


def calculate_volume_ratio(data, period=20):
    """Hacim oranı - Son hacim / Ortalama hacim"""
    avg_volume = data['volume'].rolling(window=period).mean()
    volume_ratio = data['volume'] / avg_volume
    return volume_ratio


def calculate_adx(data, period=14):
    """ADX (Average Directional Index) - Trend gücü"""
    high = data['high']
    low = data['low']
    close = data['close']
    
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
    minus_di = abs(100 * (minus_dm.ewm(alpha=1/period).mean() / atr))
    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    adx = dx.ewm(alpha=1/period).mean()
    
    return adx


def analyze_stock(df):
    """
    Bir hisse için tüm indikatörleri hesaplar
    
    Args:
        df: DataFrame (columns: date, open, high, low, close, volume)
    
    Returns:
        dict: Analiz sonuçları
    """
    if len(df) < 50:
        return None
    
    # Veriyi tarihe göre eski → yeni sırala
    df = df.sort_values('date').reset_index(drop=True)
    
    # İndikatörleri hesapla
    df['rsi'] = calculate_rsi(df)
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df)
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = calculate_bollinger_bands(df)
    df['ema_20'] = calculate_ema(df, 20)
    df['ema_50'] = calculate_ema(df, 50)
    df['sma_200'] = calculate_sma(df, 200) if len(df) >= 200 else None
    df['stoch_k'], df['stoch_d'] = calculate_stochastic(df)
    df['atr'] = calculate_atr(df)
    df['volume_ratio'] = calculate_volume_ratio(df)
    
    try:
        df['adx'] = calculate_adx(df)
    except Exception:
        df['adx'] = None
    
    # Son değerleri al
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    def safe_float(value):
        """Güvenli float dönüşümü"""
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
    
    result = {
        'current_price': safe_float(last['close']),
        'rsi': safe_float(last['rsi']),
        'macd': safe_float(last['macd']),
        'macd_signal': safe_float(last['macd_signal']),
        'macd_hist': safe_float(last['macd_hist']),
        'bb_upper': safe_float(last['bb_upper']),
        'bb_middle': safe_float(last['bb_middle']),
        'bb_lower': safe_float(last['bb_lower']),
        'ema_20': safe_float(last['ema_20']),
        'ema_50': safe_float(last['ema_50']),
        'sma_200': safe_float(last['sma_200']) if df['sma_200'] is not None else None,
        'stoch_k': safe_float(last['stoch_k']),
        'stoch_d': safe_float(last['stoch_d']),
        'atr': safe_float(last['atr']),
        'volume_ratio': safe_float(last['volume_ratio']),
        'adx': safe_float(last['adx']) if 'adx' in df.columns else None,
        
        # Önceki değerler (kesişim tespiti için)
        'prev_macd': safe_float(prev['macd']),
        'prev_macd_signal': safe_float(prev['macd_signal']),
        'prev_ema_20': safe_float(prev['ema_20']),
        'prev_ema_50': safe_float(prev['ema_50']),
        'prev_close': safe_float(prev['close']),
    }
    
    return result


def print_analysis(symbol, result):
    """Analiz sonucunu güzel formatta yazdırır"""
    if not result:
        print(f"❌ {symbol} için analiz yapılamadı")
        return
    
    print(f"\n{'='*50}")
    print(f"📊 {symbol} TEKNİK ANALİZ")
    print(f"{'='*50}")
    print(f"💰 Güncel Fiyat   : {result['current_price']:.2f} TL")
    print(f"\n📈 MOMENTUM:")
    print(f"   RSI            : {result['rsi']:.2f}" if result['rsi'] else "   RSI            : N/A")
    print(f"   Stoch K        : {result['stoch_k']:.2f}" if result['stoch_k'] else "   Stoch K        : N/A")
    print(f"   Stoch D        : {result['stoch_d']:.2f}" if result['stoch_d'] else "   Stoch D        : N/A")
    
    print(f"\n📊 TREND:")
    print(f"   MACD           : {result['macd']:.4f}" if result['macd'] else "   MACD           : N/A")
    print(f"   MACD Sinyal    : {result['macd_signal']:.4f}" if result['macd_signal'] else "   MACD Sinyal    : N/A")
    print(f"   EMA 20         : {result['ema_20']:.2f}" if result['ema_20'] else "   EMA 20         : N/A")
    print(f"   EMA 50         : {result['ema_50']:.2f}" if result['ema_50'] else "   EMA 50         : N/A")
    if result['sma_200']:
        print(f"   SMA 200        : {result['sma_200']:.2f}")
    if result['adx']:
        print(f"   ADX (Trend Gücü): {result['adx']:.2f}")
    
    print(f"\n🎯 BOLLINGER BANDS:")
    print(f"   Üst Bant       : {result['bb_upper']:.2f}" if result['bb_upper'] else "   Üst Bant       : N/A")
    print(f"   Orta Bant      : {result['bb_middle']:.2f}" if result['bb_middle'] else "   Orta Bant      : N/A")
    print(f"   Alt Bant       : {result['bb_lower']:.2f}" if result['bb_lower'] else "   Alt Bant       : N/A")
    
    print(f"\n📊 HACİM & VOLATİLİTE:")
    print(f"   Hacim Oranı    : {result['volume_ratio']:.2f}x" if result['volume_ratio'] else "   Hacim Oranı    : N/A")
    print(f"   ATR            : {result['atr']:.2f}" if result['atr'] else "   ATR            : N/A")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    # Test
    from database import get_stock_history
    
    test_symbols = ["AKBNK.IS", "THYAO.IS", "ASELS.IS"]
    
    for symbol in test_symbols:
        print(f"\n🧪 Test ediliyor: {symbol}")
        
        data = get_stock_history(symbol, days=300)
        
        if data:
            df = pd.DataFrame(data)
            result = analyze_stock(df)
            print_analysis(symbol, result)
        else:
            print(f"⚠️  {symbol} için veritabanında veri yok")
            print(f"   Önce şunu çalıştır: python services/data_fetcher.py")
    
    print("\n✅ Tüm testler tamamlandı!")