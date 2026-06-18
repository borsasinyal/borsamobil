"""
Sinyal Üretme Motoru - Day Trading Odaklı
Puanlama, hedef/stop hesaplama, sebep tespiti
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


def calculate_volume_score(analysis):
    """
    Hacim puanı (0-35)
    Day trader için EN ÖNEMLİ kriter
    """
    score = 0
    reasons = []
    
    volume_ratio = analysis.get('volume_ratio')
    if volume_ratio is None:
        return 0, []
    
    # Hacim ortalamanın katları
    if volume_ratio >= 5:
        score += 30
        reasons.append({
            'icon': '💥',
            'title': 'HACİM PATLAMASI',
            'detail': f'Ortalamanın {volume_ratio:.1f} katı hacim (5x+)',
            'meaning': 'Kurumsal alım sinyali - çok güçlü'
        })
    elif volume_ratio >= 3:
        score += 25
        reasons.append({
            'icon': '💥',
            'title': 'YÜKSEK HACİM',
            'detail': f'Ortalamanın {volume_ratio:.1f} katı hacim (3x+)',
            'meaning': 'Güçlü ilgi var'
        })
    elif volume_ratio >= 2:
        score += 15
        reasons.append({
            'icon': '📊',
            'title': 'HACİM ARTIŞI',
            'detail': f'Ortalamanın {volume_ratio:.1f} katı hacim (2x+)',
            'meaning': 'Normalin üstünde işlem'
        })
    elif volume_ratio >= 1.5:
        score += 8
        reasons.append({
            'icon': '📊',
            'title': 'HACİM NORMAL ÜSTÜ',
            'detail': f'{volume_ratio:.1f}x ortalama',
            'meaning': 'Yeterli likidite var'
        })
    
    return min(score, 35), reasons


def calculate_momentum_score(analysis):
    """
    Momentum puanı (0-25)
    RSI + MACD + Stochastic
    """
    score = 0
    reasons = []
    
    rsi = analysis.get('rsi')
    macd = analysis.get('macd')
    macd_signal = analysis.get('macd_signal')
    prev_macd = analysis.get('prev_macd')
    prev_macd_signal = analysis.get('prev_macd_signal')
    stoch_k = analysis.get('stoch_k')
    stoch_d = analysis.get('stoch_d')
    
    # RSI Analizi (10 puan)
    if rsi is not None:
        if 50 <= rsi <= 65:
            score += 10
            reasons.append({
                'icon': '⚡',
                'title': 'RSI SAĞLIKLI',
                'detail': f'RSI: {rsi:.1f} (50-65 ideal bölge)',
                'meaning': 'Momentum var, aşırı alım değil'
            })
        elif 40 <= rsi < 50:
            score += 8
            reasons.append({
                'icon': '⚡',
                'title': 'RSI TOPARLANIYOR',
                'detail': f'RSI: {rsi:.1f} (dip dönüşü)',
                'meaning': 'Düşüş tükeniyor, yukarı dönüş başlıyor'
            })
        elif 65 < rsi <= 70:
            score += 5
            reasons.append({
                'icon': '⚡',
                'title': 'RSI GÜÇLÜ',
                'detail': f'RSI: {rsi:.1f} (aşırı alıma yaklaşıyor)',
                'meaning': 'Momentum güçlü ama dikkat'
            })
        elif rsi < 35:
            score += 3
            reasons.append({
                'icon': '⚡',
                'title': 'RSI DİP BÖLGESİ',
                'detail': f'RSI: {rsi:.1f} (aşırı satım)',
                'meaning': 'Toparlanma fırsatı olabilir'
            })
    
    # MACD Kesişimi (10 puan)
    if all(v is not None for v in [macd, macd_signal, prev_macd, prev_macd_signal]):
        # Yukarı kesişim: önce alttaydı, şimdi üstte
        if prev_macd <= prev_macd_signal and macd > macd_signal:
            score += 10
            reasons.append({
                'icon': '🚀',
                'title': 'MACD KESİŞİMİ',
                'detail': 'MACD sinyal çizgisini yukarı kesti',
                'meaning': 'GÜÇLÜ alış sinyali - yeni momentum'
            })
        elif macd > macd_signal and macd > 0:
            score += 7
            reasons.append({
                'icon': '📈',
                'title': 'MACD POZİTİF',
                'detail': f'MACD: {macd:.3f} > Sinyal: {macd_signal:.3f}',
                'meaning': 'Trend yukarı yönlü'
            })
        elif macd > macd_signal:
            score += 5
            reasons.append({
                'icon': '📈',
                'title': 'MACD YUKARI',
                'detail': 'MACD sinyal üstünde',
                'meaning': 'Momentum pozitif'
            })
    
    # Stochastic (5 puan)
    if stoch_k is not None and stoch_d is not None:
        if stoch_k > stoch_d and stoch_k < 80:
            score += 5
            reasons.append({
                'icon': '⚡',
                'title': 'STOCHASTIC YUKARI',
                'detail': f'K: {stoch_k:.1f} > D: {stoch_d:.1f}',
                'meaning': 'Kısa vadeli momentum pozitif'
            })
    
    return min(score, 25), reasons


def calculate_trend_score(analysis):
    """
    Trend puanı (0-20)
    EMA'lar ve fiyat konumu
    """
    score = 0
    reasons = []
    
    current_price = analysis.get('current_price')
    ema_20 = analysis.get('ema_20')
    ema_50 = analysis.get('ema_50')
    sma_200 = analysis.get('sma_200')
    prev_ema_20 = analysis.get('prev_ema_20')
    prev_ema_50 = analysis.get('prev_ema_50')
    
    # EMA20 > EMA50 (kısa vade trend yukarı) - 10 puan
    if ema_20 is not None and ema_50 is not None:
        if ema_20 > ema_50:
            score += 10
            reasons.append({
                'icon': '📈',
                'title': 'TREND YUKARI',
                'detail': f'EMA20 ({ema_20:.2f}) > EMA50 ({ema_50:.2f})',
                'meaning': 'Kısa vadeli trend pozitif'
            })
            
            # Yeni kesişim ekstra puan
            if prev_ema_20 is not None and prev_ema_50 is not None:
                if prev_ema_20 <= prev_ema_50:
                    score += 5
                    reasons.append({
                        'icon': '⭐',
                        'title': 'YENİ TREND BAŞLANGICI',
                        'detail': 'EMA20, EMA50 üstüne çıktı',
                        'meaning': 'Trend dönüşü - güçlü sinyal'
                    })
    
    # Fiyat EMA20 üstünde - 5 puan
    if current_price is not None and ema_20 is not None:
        if current_price > ema_20:
            score += 5
            reasons.append({
                'icon': '✅',
                'title': 'FİYAT EMA20 ÜSTÜNDE',
                'detail': f'Fiyat {current_price:.2f} > EMA20 {ema_20:.2f}',
                'meaning': 'Kısa vade pozitif konum'
            })
    
    return min(score, 20), reasons


def calculate_breakout_score(analysis, history_df=None):
    """
    Kırılım puanı (0-15)
    BB kırılımı, direnç kırılımı
    """
    score = 0
    reasons = []
    
    current_price = analysis.get('current_price')
    bb_upper = analysis.get('bb_upper')
    bb_middle = analysis.get('bb_middle')
    bb_lower = analysis.get('bb_lower')
    prev_close = analysis.get('prev_close')
    
    # Bollinger Bands - 8 puan
    if current_price is not None and bb_upper is not None and bb_middle is not None:
        # BB üst bant testi/kırılımı
        if current_price >= bb_upper * 0.98:
            score += 8
            reasons.append({
                'icon': '🚀',
                'title': 'BB ÜST BANT TESTİ',
                'detail': f'Fiyat {current_price:.2f} ≈ Üst Bant {bb_upper:.2f}',
                'meaning': 'Güçlü momentum kırılımı'
            })
        elif current_price > bb_middle:
            score += 4
            reasons.append({
                'icon': '📈',
                'title': 'BB ORTA BANT ÜSTÜ',
                'detail': 'Fiyat orta bandın üzerinde',
                'meaning': 'Pozitif bölgede'
            })
    
    # Önceki gün kapanışından yüksek - 7 puan
    if current_price is not None and prev_close is not None:
        change_pct = ((current_price - prev_close) / prev_close) * 100
        if change_pct >= 2:
            score += 7
            reasons.append({
                'icon': '🔥',
                'title': 'GÜÇLÜ YÜKSELİŞ',
                'detail': f'Bugün +{change_pct:.2f}%',
                'meaning': 'Momentum çok güçlü'
            })
        elif change_pct >= 1:
            score += 4
            reasons.append({
                'icon': '📈',
                'title': 'POZİTİF GÜN',
                'detail': f'Bugün +{change_pct:.2f}%',
                'meaning': 'Yukarı yönlü hareket'
            })
        elif change_pct > 0:
            score += 2
    
    return min(score, 15), reasons


def calculate_liquidity_score(analysis):
    """
    Likidite puanı (0-5)
    """
    score = 0
    reasons = []
    
    volume_ratio = analysis.get('volume_ratio')
    current_price = analysis.get('current_price')
    
    if volume_ratio is not None and volume_ratio >= 0.8:
        score += 3
    
    if current_price is not None and current_price >= 5:
        score += 2
        if score >= 5:
            reasons.append({
                'icon': '✅',
                'title': 'LİKİDİTE İYİ',
                'detail': 'Yeterli hacim ve fiyat seviyesi',
                'meaning': 'Rahat alıp satabilirsin'
            })
    
    return min(score, 5), reasons


def calculate_total_score(analysis, history_df=None):
    """
    Tüm puanları topla
    """
    volume_score, volume_reasons = calculate_volume_score(analysis)
    momentum_score, momentum_reasons = calculate_momentum_score(analysis)
    trend_score, trend_reasons = calculate_trend_score(analysis)
    breakout_score, breakout_reasons = calculate_breakout_score(analysis, history_df)
    liquidity_score, liquidity_reasons = calculate_liquidity_score(analysis)
    
    total = volume_score + momentum_score + trend_score + breakout_score + liquidity_score
    
    all_reasons = (
        volume_reasons + 
        momentum_reasons + 
        trend_reasons + 
        breakout_reasons + 
        liquidity_reasons
    )
    
    return {
        'total': total,
        'breakdown': {
            'volume': {'score': volume_score, 'max': 35},
            'momentum': {'score': momentum_score, 'max': 25},
            'trend': {'score': trend_score, 'max': 20},
            'breakout': {'score': breakout_score, 'max': 15},
            'liquidity': {'score': liquidity_score, 'max': 5},
        },
        'reasons': all_reasons
    }


def calculate_targets_and_stops(current_price, atr=None, score=70):
    """
    Hedef ve stop-loss seviyelerini hesapla
    ATR varsa akıllı hesap, yoksa yüzde bazlı
    """
    if atr is None or atr == 0:
        # Sabit yüzdeler (day trading)
        target_1_pct = 1.75
        target_2_pct = 3.0
        stop_pct = 1.05
    else:
        # ATR bazlı dinamik hesaplama
        atr_pct = (atr / current_price) * 100
        atr_pct = max(0.5, min(atr_pct, 3))  # 0.5%-3% arası sınırla
        
        target_1_pct = atr_pct * 1.5
        target_2_pct = atr_pct * 2.5
        stop_pct = atr_pct * 1.0
    
    target_1 = round(current_price * (1 + target_1_pct / 100), 2)
    target_2 = round(current_price * (1 + target_2_pct / 100), 2)
    stop_loss = round(current_price * (1 - stop_pct / 100), 2)
    
    # Risk/Ödül oranı
    risk = current_price - stop_loss
    reward = target_2 - current_price
    risk_reward = round(reward / risk, 2) if risk > 0 else 0
    
    return {
        'entry': current_price,
        'target_1': target_1,
        'target_1_pct': round(target_1_pct, 2),
        'target_2': target_2,
        'target_2_pct': round(target_2_pct, 2),
        'stop_loss': stop_loss,
        'stop_pct': round(stop_pct, 2),
        'risk_reward': risk_reward
    }


def determine_signal_strength(score):
    """
    Skora göre sinyal gücü
    """
    if score >= 85:
        return {
            'type': 'AL',
            'strength': 'COK_GUCLU',
            'label': 'ÇOK GÜÇLÜ AL',
            'emoji': '🔥🔥🔥',
            'color': '🟢',
            'action': 'ŞİMDİ AL!'
        }
    elif score >= 75:
        return {
            'type': 'AL',
            'strength': 'GUCLU',
            'label': 'GÜÇLÜ AL',
            'emoji': '🔥🔥',
            'color': '🟢',
            'action': 'AL'
        }
    elif score >= 65:
        return {
            'type': 'AL',
            'strength': 'NORMAL',
            'label': 'AL',
            'emoji': '🔥',
            'color': '🟢',
            'action': 'AL (dikkatli)'
        }
    elif score >= 50:
        return {
            'type': 'BEKLE',
            'strength': 'ZAYIF',
            'label': 'BEKLE / İZLE',
            'emoji': '🟡',
            'color': '🟡',
            'action': 'BEKLE'
        }
    else:
        return {
            'type': 'YOK',
            'strength': 'YOK',
            'label': 'SİNYAL YOK',
            'emoji': '⚪',
            'color': '⚪',
            'action': 'GİRMİYORUM'
        }


def generate_signal(symbol, analysis, history_df=None):
    """
    Bir hisse için tam sinyal üret
    """
    if not analysis:
        return None
    
    current_price = analysis.get('current_price')
    if not current_price:
        return None
    
    # Skoru hesapla
    score_data = calculate_total_score(analysis, history_df)
    total_score = score_data['total']
    
    # Sinyal gücünü belirle
    signal_info = determine_signal_strength(total_score)
    
    # Hedef ve stop-loss
    atr = analysis.get('atr')
    targets = calculate_targets_and_stops(current_price, atr, total_score)
    
    # Görsel skor çubuğu
    filled = int(total_score / 5)
    empty = 20 - filled
    score_bar = '█' * filled + '░' * empty
    
    # Yıldız sayısı
    if total_score >= 85:
        stars = '🟢🟢🟢🟢🟢'
    elif total_score >= 75:
        stars = '🟢🟢🟢🟢⚪'
    elif total_score >= 65:
        stars = '🟢🟢🟢⚪⚪'
    elif total_score >= 50:
        stars = '🟡🟡⚪⚪⚪'
    else:
        stars = '⚪⚪⚪⚪⚪'
    
    signal = {
        'symbol': symbol.replace('.IS', ''),
        'full_symbol': symbol,
        'timestamp': datetime.now().isoformat(),
        'current_price': current_price,
        'score': total_score,
        'score_bar': score_bar,
        'stars': stars,
        'signal_type': signal_info['type'],
        'strength': signal_info['strength'],
        'label': signal_info['label'],
        'emoji': signal_info['emoji'],
        'action': signal_info['action'],
        'targets': targets,
        'reasons': score_data['reasons'],
        'breakdown': score_data['breakdown'],
        'analysis': {
            'rsi': analysis.get('rsi'),
            'macd': analysis.get('macd'),
            'volume_ratio': analysis.get('volume_ratio'),
            'ema_20': analysis.get('ema_20'),
            'ema_50': analysis.get('ema_50'),
        }
    }
    
    return signal


def format_signal_message(signal):
    """
    Sinyali güzel formatta string'e çevir (Telegram ve console için)
    """
    if not signal:
        return "Sinyal yok"
    
    msg = []
    msg.append("╔═══════════════════════════════════╗")
    msg.append(f"║  {signal['emoji']} {signal['label']}")
    msg.append("║  ═══════════════════════════════  ║")
    msg.append(f"║  📌 {signal['symbol']}")
    msg.append(f"║  💰 Güncel: {signal['current_price']:.2f} TL")
    msg.append(f"║  ⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}")
    msg.append("╠═══════════════════════════════════╣")
    msg.append(f"║  💯 SKOR: {signal['score']}/100")
    msg.append(f"║  {signal['score_bar']}")
    msg.append(f"║  {signal['stars']}")
    msg.append("╠═══════════════════════════════════╣")
    msg.append("║  💼 İŞLEM PLANI")
    msg.append(f"║  📥 Giriş   : {signal['targets']['entry']:.2f} TL")
    msg.append(f"║  🎯 Hedef 1 : {signal['targets']['target_1']:.2f} TL (+{signal['targets']['target_1_pct']}%)")
    msg.append(f"║  🎯 Hedef 2 : {signal['targets']['target_2']:.2f} TL (+{signal['targets']['target_2_pct']}%)")
    msg.append(f"║  🛑 Stop    : {signal['targets']['stop_loss']:.2f} TL (-{signal['targets']['stop_pct']}%)")
    msg.append(f"║  ⚖️  R/Ö    : 1/{signal['targets']['risk_reward']}")
    msg.append("╠═══════════════════════════════════╣")
    msg.append(f"║  📊 ALMA SEBEPLERİM ({len(signal['reasons'])})")
    for reason in signal['reasons']:
        msg.append(f"║  {reason['icon']} {reason['title']}")
        msg.append(f"║     {reason['detail']}")
        msg.append(f"║     → {reason['meaning']}")
    msg.append("╠═══════════════════════════════════╣")
    msg.append("║  📈 PUAN DAĞILIMI")
    b = signal['breakdown']
    msg.append(f"║  💥 Hacim    : {b['volume']['score']}/{b['volume']['max']}")
    msg.append(f"║  ⚡ Momentum : {b['momentum']['score']}/{b['momentum']['max']}")
    msg.append(f"║  📈 Trend    : {b['trend']['score']}/{b['trend']['max']}")
    msg.append(f"║  🚀 Kırılım  : {b['breakout']['score']}/{b['breakout']['max']}")
    msg.append(f"║  🎯 Likidite : {b['liquidity']['score']}/{b['liquidity']['max']}")
    msg.append("╚═══════════════════════════════════╝")
    
    return "\n".join(msg)


if __name__ == "__main__":
    # Test
    import pandas as pd
    from database import get_stock_history
    from analyzer import analyze_stock
    
    test_symbols = ["AKBNK.IS", "AEFES.IS", "AKSA.IS", "AKSEN.IS", "AGHOL.IS"]
    
    print("\n🧪 SİNYAL MOTORU TESTİ")
    print("=" * 60)
    
    for symbol in test_symbols:
        print(f"\n📊 {symbol} analiz ediliyor...")
        
        data = get_stock_history(symbol, days=300)
        
        if data:
            df = pd.DataFrame(data)
            analysis = analyze_stock(df)
            
            if analysis:
                signal = generate_signal(symbol, analysis, df)
                
                if signal:
                    print(format_signal_message(signal))
                else:
                    print(f"   ⚠️  {symbol} için sinyal üretilemedi")
            else:
                print(f"   ⚠️  {symbol} analiz başarısız")
        else:
            print(f"   ❌ {symbol} için veri yok")
    
    print("\n✅ Test tamamlandı!")