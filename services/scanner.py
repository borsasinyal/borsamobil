"""
Tarama Motoru - Tüm BIST'i Tarar
Day Trading odaklı, güvenlik filtrelerine sahip
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime
from config import BIST_SYMBOLS, MIN_SIGNAL_SCORE
from database import get_stock_history, save_signal
from services.analyzer import analyze_stock
from services.signal_engine import generate_signal, format_signal_message


# ════════════════════════════════════════════════
# GÜVENLİK FİLTRELERİ
# ════════════════════════════════════════════════

def passes_safety_filters(symbol, df, analysis):
    """
    Hisse güvenlik filtrelerinden geçiyor mu?
    Geçemezse sinyal üretilmez
    
    Returns:
        (bool, str): (geçti mi, sebep)
    """
    
    # 1. Yeterli veri var mı?
    if len(df) < 50:
        return False, "Yetersiz veri (50 gün altı)"
    
    # 2. Fiyat çok düşük mü? (Penny stock filtresi)
    current_price = analysis.get('current_price')
    if current_price is None or current_price < 2:
        return False, f"Fiyat çok düşük ({current_price} TL)"
    
    # 3. Hacim yeterli mi?
    df_sorted = df.sort_values('date').reset_index(drop=True)
    avg_volume = df_sorted['volume'].tail(20).mean()
    avg_volume_tl = avg_volume * current_price
    
    if avg_volume_tl < 1_000_000:  # 1 milyon TL altı = likitsiz
        return False, f"Likidite düşük ({avg_volume_tl/1_000_000:.1f}M TL)"
    
    # 4. Düşen bıçak değil mi?
    # Son 5 günde sürekli düşmüş mü?
    last_5_closes = df_sorted['close'].tail(5).tolist()
    if len(last_5_closes) >= 5:
        all_declining = all(last_5_closes[i] > last_5_closes[i+1] for i in range(len(last_5_closes)-1))
        if all_declining:
            total_drop = ((last_5_closes[0] - last_5_closes[-1]) / last_5_closes[0]) * 100
            if total_drop > 10:
                return False, f"Düşen bıçak ({total_drop:.1f}% düşüş)"
    
    # 5. Son 30 günde aşırı düşmüş mü?
    if len(df_sorted) >= 30:
        price_30_days_ago = df_sorted['close'].iloc[-30]
        drop_30 = ((price_30_days_ago - current_price) / price_30_days_ago) * 100
        if drop_30 > 40:
            return False, f"30 günde %{drop_30:.0f} düşüş"
    
    # 6. Aşırı volatil mi?
    atr = analysis.get('atr')
    if atr is not None and current_price > 0:
        atr_pct = (atr / current_price) * 100
        if atr_pct > 8:  # %8 üstü ATR = aşırı volatil
            return False, f"Aşırı volatil (ATR: %{atr_pct:.1f})"
    
    return True, "OK"


# ════════════════════════════════════════════════
# TARAMA FONKSİYONLARI
# ════════════════════════════════════════════════

def scan_single_stock(symbol, min_score=65):
    """
    Tek bir hisseyi tara ve sinyal üret
    
    Returns:
        dict veya None
    """
    try:
        # Geçmiş veriyi al
        data = get_stock_history(symbol, days=300)
        
        if not data or len(data) < 50:
            return None
        
        df = pd.DataFrame(data)
        
        # Teknik analiz yap
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
        
        # Minimum skor kontrolü
        if signal['score'] < min_score:
            return None
        
        return signal
    
    except Exception as e:
        print(f"   ❌ {symbol} taranırken hata: {e}")
        return None


def scan_all_stocks(min_score=65, save_to_db=True, verbose=False):
    """
    Tüm BIST hisselerini tara
    
    Args:
        min_score: Minimum sinyal skoru (varsayılan 65)
        save_to_db: Sinyalleri veritabanına kaydet
        verbose: Detaylı çıktı
    
    Returns:
        list: Güçlü sinyal veren hisseler (skora göre sıralı)
    """
    print(f"\n{'='*60}")
    print(f"🔍 TÜM BIST TARAMASI BAŞLIYOR")
    print(f"📊 {len(BIST_SYMBOLS)} hisse taranacak")
    print(f"⚙️  Minimum skor: {min_score}")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")
    
    signals = []
    filtered_out = []
    no_data = []
    
    for i, symbol in enumerate(BIST_SYMBOLS, 1):
        # İlerleme göster (her 20 hissede bir)
        if i % 20 == 0 or i == len(BIST_SYMBOLS):
            print(f"   ⏳ İlerleme: {i}/{len(BIST_SYMBOLS)} ({i*100//len(BIST_SYMBOLS)}%)")
        
        result = scan_single_stock(symbol, min_score)
        
        if result is None:
            no_data.append(symbol)
            continue
        
        if result.get('filtered'):
            filtered_out.append(result)
            if verbose:
                print(f"   🚫 {result['symbol']}: {result['filter_reason']}")
            continue
        
        # Güçlü sinyal!
        signals.append(result)
        
        if verbose:
            print(f"   ✅ {result['symbol']}: Skor {result['score']} - {result['label']}")
        
        # Veritabanına kaydet
        if save_to_db:
            save_signal(
                symbol=result['symbol'],
                signal_type=result['signal_type'],
                price=result['current_price'],
                target_price=result['targets']['target_2'],
                stop_loss=result['targets']['stop_loss'],
                score=result['score'],
                strategy=result['strength'],
                timeframe='SHORT'
            )
    
    # Skora göre sırala (en yüksek üstte)
    signals.sort(key=lambda x: x['score'], reverse=True)
    
    # Özet
    print(f"\n{'='*60}")
    print(f"📊 TARAMA TAMAMLANDI")
    print(f"{'='*60}")
    print(f"✅ Güçlü Sinyal     : {len(signals)} hisse")
    print(f"🚫 Filtrelenen      : {len(filtered_out)} hisse")
    print(f"⚪ Veri Yok/Zayıf  : {len(no_data)} hisse")
    print(f"📋 Toplam           : {len(BIST_SYMBOLS)} hisse")
    print(f"{'='*60}\n")
    
    return signals


def print_top_signals(signals, top_n=10):
    """
    En iyi N sinyali güzelce yazdır
    """
    if not signals:
        print("\n⚠️  Hiç güçlü sinyal bulunamadı")
        print("   Bu normal olabilir. Şu sebepler olabilir:")
        print("   - Piyasa düşüyor (sinyal eşiği yüksek)")
        print("   - Veri yetersiz")
        print("   - Tarama zamanı uygun değil\n")
        return
    
    top = signals[:top_n]
    
    print(f"\n{'='*60}")
    print(f"🏆 EN İYİ {len(top)} SİNYAL")
    print(f"{'='*60}\n")
    
    # Özet tablo
    print(f"{'#':<4}{'SEMBOL':<10}{'FİYAT':<12}{'SKOR':<8}{'GÜÇ':<20}")
    print("─" * 60)
    
    for i, signal in enumerate(top, 1):
        emoji = signal['emoji']
        symbol = signal['symbol']
        price = f"{signal['current_price']:.2f} TL"
        score = f"{signal['score']}/100"
        label = signal['label']
        
        print(f"{i:<4}{symbol:<10}{price:<12}{score:<8}{emoji} {label}")
    
    print("─" * 60)
    
    # En iyi 3 sinyali detaylı göster
    print(f"\n\n{'='*60}")
    print(f"🌟 EN İYİ 3 SİNYAL - DETAYLI")
    print(f"{'='*60}")
    
    for signal in top[:3]:
        print(format_signal_message(signal))
        print()


def get_top_signals(limit=10):
    """
    Veritabanından son sinyalleri getir
    """
    from database import get_latest_signals
    return get_latest_signals(limit)


# ════════════════════════════════════════════════
# ANA ÇALIŞTIRMA
# ════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 BIST TARAMA MOTORU")
    print("="*60)
    
    # Önce veriler var mı kontrol
    from database import get_stock_history
    
    # Test için sadece elimizde veri olan hisseleri tara
    print("\n📂 Mevcut veriler kontrol ediliyor...")
    
    # Şimdiye kadar çektiğimiz 5 hisseyle test
    test_mode = input("\n❓ Test modu mu? (E=Sadece 5 hisse / H=Tüm BIST): ").strip().upper()
    
    if test_mode == 'H':
        # TÜM BIST
        print("\n⚠️  TÜM BIST taraması başlıyor...")
        print("⚠️  Önce verileri çekmelisin: python services/data_fetcher.py")
        confirm = input("Veriler hazır mı? (E/H): ").strip().upper()
        
        if confirm != 'E':
            print("❌ Önce verileri çek!")
            sys.exit(0)
        
        signals = scan_all_stocks(min_score=65, save_to_db=True, verbose=True)
        print_top_signals(signals, top_n=15)
    
    else:
        # Test modu - sadece veritabanında olan hisseler
        print("\n🧪 TEST MODU - Mevcut verilerle tarama")
        
        test_symbols = ["AEFES.IS", "AGHOL.IS", "AKBNK.IS", "AKSA.IS", "AKSEN.IS"]
        
        signals = []
        for symbol in test_symbols:
            print(f"   📊 {symbol} taranıyor...")
            
            # Düşük eşik ile test (daha çok sinyal görmek için)
            result = scan_single_stock(symbol, min_score=40)
            
            if result and not result.get('filtered'):
                signals.append(result)
                print(f"      ✅ Skor: {result['score']}")
            elif result and result.get('filtered'):
                print(f"      🚫 Filtrelendi: {result['filter_reason']}")
            else:
                print(f"      ⚪ Sinyal yok")
        
        signals.sort(key=lambda x: x['score'], reverse=True)
        
        if signals:
            print_top_signals(signals, top_n=5)
        else:
            print("\n⚠️  Test verilerinde sinyal çıkmadı")
            print("   Bu test için normal. Tüm BIST'i taradığımızda sinyaller çıkacak.\n")
    
    print("\n✅ Tarama tamamlandı!")