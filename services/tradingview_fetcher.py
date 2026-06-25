"""
TradingView Veri Çekme Modülü
Anlık veri için tvDatafeed kütüphanesi kullanılır
Yedek olarak Yahoo Finance kalır
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tvDatafeed import TvDatafeed, Interval
    TV_AVAILABLE = True
except ImportError:
    print("⚠️ tvDatafeed kütüphanesi yüklenmemiş")
    TV_AVAILABLE = False

from database import save_price_data


# ════════════════════════════════════════════════════════════
# TRADINGVIEW BAĞLANTI
# ════════════════════════════════════════════════════════════

_tv_instance = None

def get_tv_instance():
    """TradingView bağlantısı - cache'li (her seferinde yeniden bağlanma)"""
    global _tv_instance
    
    if _tv_instance is not None:
        return _tv_instance
    
    if not TV_AVAILABLE:
        return None
    
    try:
        username = os.environ.get('TV_USERNAME')
        password = os.environ.get('TV_PASSWORD')
        
        if username and password:
            print(f"🔑 TradingView'a giriş yapılıyor: {username}")
            _tv_instance = TvDatafeed(username=username, password=password)
            print("✅ TradingView bağlantısı başarılı")
        else:
            print("⚠️ TV_USERNAME veya TV_PASSWORD bulunamadı, anonim bağlanılıyor")
            _tv_instance = TvDatafeed()
        
        return _tv_instance
    except Exception as e:
        print(f"❌ TradingView bağlantı hatası: {e}")
        return None


# ════════════════════════════════════════════════════════════
# TEK HİSSE VERİ ÇEKME
# ════════════════════════════════════════════════════════════

def fetch_stock_tv(symbol, n_bars=300):
    """
    TradingView'dan tek hisse verisi çek
    
    Args:
        symbol: Hisse kodu (örn: 'AKBNK' veya 'AKBNK.IS')
        n_bars: Kaç mum çekilecek
    
    Returns:
        list of dict veya None
    """
    if not TV_AVAILABLE:
        return None
    
    tv = get_tv_instance()
    if not tv:
        return None
    
    try:
        # Sembol formatı
        symbol_clean = symbol.replace('.IS', '')
        
        # Veri çek
        data = tv.get_hist(
            symbol=symbol_clean,
            exchange='BIST',
            interval=Interval.in_daily,
            n_bars=n_bars
        )
        
        if data is None or data.empty:
            return None
        
        # DataFrame'i dict listesine çevir
        result = []
        for idx, row in data.iterrows():
            result.append({
                'date': idx.strftime('%Y-%m-%d'),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['volume'])
            })
        
        return result
    
    except Exception as e:
        # Sessiz hata (her hisse için log basmasın)
        return None


# ════════════════════════════════════════════════════════════
# TOPLU VERİ ÇEKME (TÜM BIST)
# ════════════════════════════════════════════════════════════

def fetch_all_tv(symbols_list, delay=0.3):
    """
    Tüm hisselerin TradingView'dan günlük verisini çek ve veritabanına kaydet
    
    Args:
        symbols_list: ['AKBNK.IS', 'THYAO.IS', ...]
        delay: Sorgu arası bekleme (saniye)
    
    Returns:
        (success_count, failed_count)
    """
    if not TV_AVAILABLE:
        print("❌ tvDatafeed mevcut değil, Yahoo'ya düşülecek")
        return 0, len(symbols_list)
    
    tv = get_tv_instance()
    if not tv:
        print("❌ TradingView bağlantısı kurulamadı")
        return 0, len(symbols_list)
    
    total = len(symbols_list)
    print(f"\n🚀 TradingView'dan {total} hisse için veri çekiliyor...\n")
    
    success = 0
    failed = 0
    failed_symbols = []
    start_time = time.time()
    
    for i, symbol in enumerate(symbols_list, 1):
        # Progress
        if i % 25 == 0 or i == 1 or i == total:
            elapsed = time.time() - start_time
            avg = elapsed / i if i > 0 else 0
            remaining = avg * (total - i)
            eta_min = int(remaining // 60)
            eta_sec = int(remaining % 60)
            print(f"⏳ [{i}/{total}] ({i*100//total}%) | ✅ {success} | ❌ {failed} | ETA: ~{eta_min}dk {eta_sec}sn")
        
        try:
            # TradingView'dan çek
            data = fetch_stock_tv(symbol, n_bars=300)
            
            if data and len(data) > 0:
                # Veritabanına kaydet
                for row in data:
                    try:
                        save_price_data(
                            symbol=symbol,
                            date=row['date'],
                            open_price=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row['volume']
                        )
                    except:
                        pass
                success += 1
            else:
                failed += 1
                failed_symbols.append(symbol)
            
            # Rate limit için bekle
            if delay > 0:
                time.sleep(delay)
        
        except Exception as e:
            failed += 1
            failed_symbols.append(symbol)
            continue
    
    elapsed_total = time.time() - start_time
    total_min = int(elapsed_total // 60)
    total_sec = int(elapsed_total % 60)
    
    print(f"\n{'='*60}")
    print(f"📊 TRADINGVIEW VERİ ÇEKME TAMAMLANDI")
    print(f"{'='*60}")
    print(f"✅ Başarılı     : {success}")
    print(f"❌ Başarısız    : {failed}")
    print(f"⏱️  Toplam     : {total_min}dk {total_sec}sn")
    print(f"{'='*60}\n")
    
    if failed_symbols and len(failed_symbols) <= 30:
        print(f"⚠️  Veri alınamayan hisseler:")
        for sym in failed_symbols[:30]:
            print(f"   - {sym}")
    
    return success, failed


# ════════════════════════════════════════════════════════════
# ANLIK FİYAT
# ════════════════════════════════════════════════════════════

def get_current_price_tv(symbol):
    """
    TradingView'dan anlık fiyat al
    
    Args:
        symbol: Hisse kodu
    
    Returns:
        float veya None
    """
    if not TV_AVAILABLE:
        return None
    
    try:
        data = fetch_stock_tv(symbol, n_bars=2)
        if data and len(data) > 0:
            return data[-1]['close']
        return None
    except:
        return None


# ════════════════════════════════════════════════════════════
# TEST
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n🧪 TRADINGVIEW TEST")
    print("=" * 60)
    
    # Bağlantı testi
    tv = get_tv_instance()
    if tv:
        print("✅ TradingView bağlantısı başarılı")
    else:
        print("❌ TradingView bağlantısı başarısız")
        sys.exit(1)
    
    # Veri çekme testi
    test_symbols = ['AKBNK', 'THYAO', 'ASELS']
    
    for symbol in test_symbols:
        print(f"\n📊 {symbol} test ediliyor...")
        data = fetch_stock_tv(symbol, n_bars=5)
        
        if data:
            print(f"✅ {symbol}: {len(data)} mum çekildi")
            print(f"   Son fiyat: {data[-1]['close']:.2f} TL")
            print(f"   Tarih: {data[-1]['date']}")
        else:
            print(f"❌ {symbol}: Veri alınamadı")
    
    print("\n✅ Test tamamlandı!")
