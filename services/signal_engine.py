"""
Profesyonel Sinyal Motoru - Day Trading
Puanlama, Hedef 1/2/3, Stop, Momentum Uyarıları, Kar Al Önerileri
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


# ════════════════════════════════════════════════════════════
# PUANLAMA - HACİM (25 puan)
# ════════════════════════════════════════════════════════════

def score_volume(analysis):
    """Hacim & RVOL puanı"""
    score = 0
    reasons = []
    rvol = analysis.get('rvol')
    
    if rvol is None:
        return 0, []
    
    if rvol >= 5:
        score += 25
        reasons.append({
            'icon': '💥', 'title': 'HACİM PATLAMASI',
            'detail': f'RVOL: {rvol:.1f}x (5x üstü!)',
            'meaning': 'Kurumsal alım - çok güçlü sinyal'
        })
    elif rvol >= 3:
        score += 20
        reasons.append({
            'icon': '💥', 'title': 'YÜKSEK HACİM',
            'detail': f'RVOL: {rvol:.1f}x',
            'meaning': 'Güçlü ilgi var'
        })
    elif rvol >= 2:
        score += 15
        reasons.append({
            'icon': '📊', 'title': 'HACİM ARTIŞI',
            'detail': f'RVOL: {rvol:.1f}x',
            'meaning': 'Normalin üstünde işlem'
        })
    elif rvol >= 1.5:
        score += 8
        reasons.append({
            'icon': '📊', 'title': 'HACİM NORMAL ÜSTÜ',
            'detail': f'RVOL: {rvol:.1f}x',
            'meaning': 'Yeterli likidite'
        })
    elif rvol < 0.5:
        reasons.append({
            'icon': '⚠️', 'title': 'HACİM DÜŞÜK',
            'detail': f'RVOL: {rvol:.1f}x',
            'meaning': 'Dikkat, hareket sahte olabilir'
        })
    
    return min(score, 25), reasons


# ════════════════════════════════════════════════════════════
# PUANLAMA - MOMENTUM (20 puan)
# ════════════════════════════════════════════════════════════

def score_momentum(analysis):
    """Momentum puanı - RSI, MACD, Stochastic"""
    score = 0
    reasons = []
    
    rsi = analysis.get('rsi')
    macd = analysis.get('macd')
    macd_signal = analysis.get('macd_signal')
    prev_macd = analysis.get('prev_macd')
    prev_macd_signal = analysis.get('prev_macd_signal')
    macd_hist = analysis.get('macd_hist')
    stoch_k = analysis.get('stoch_k')
    stoch_d = analysis.get('stoch_d')
    
    # RSI (8 puan)
    if rsi is not None:
        if 50 <= rsi <= 65:
            score += 8
            reasons.append({
                'icon': '⚡', 'title': 'RSI İDEAL',
                'detail': f'RSI: {rsi:.1f} (50-65 sağlıklı)',
                'meaning': 'Momentum var, aşırı alım değil'
            })
        elif 40 <= rsi < 50:
            score += 6
            reasons.append({
                'icon': '⚡', 'title': 'RSI TOPARLANIYOR',
                'detail': f'RSI: {rsi:.1f}',
                'meaning': 'Dip dönüşü başlıyor'
            })
        elif 65 < rsi <= 72:
            score += 4
            reasons.append({
                'icon': '⚡', 'title': 'RSI GÜÇLÜ',
                'detail': f'RSI: {rsi:.1f}',
                'meaning': 'Momentum güçlü, dikkatli ol'
            })
    
    # MACD Kesişim (8 puan)
    if all(v is not None for v in [macd, macd_signal, prev_macd, prev_macd_signal]):
        if prev_macd <= prev_macd_signal and macd > macd_signal:
            score += 8
            reasons.append({
                'icon': '🚀', 'title': 'MACD KESİŞİMİ',
                'detail': 'MACD sinyal çizgisini yukarı kesti',
                'meaning': 'YENİ momentum başladı'
            })
        elif macd > macd_signal and macd > 0:
            score += 5
            reasons.append({
                'icon': '📈', 'title': 'MACD POZİTİF',
                'detail': f'MACD: {macd:.3f} > Signal: {macd_signal:.3f}',
                'meaning': 'Trend yukarı'
            })
        elif macd > macd_signal:
            score += 3
    
    # MACD Histogram artıyor mu?
    if macd_hist is not None:
        prev_hist = analysis.get('prev_macd_hist')
        if prev_hist is not None and macd_hist > prev_hist and macd_hist > 0:
            score += 2
    
    # Stochastic (4 puan)
    if stoch_k is not None and stoch_d is not None:
        if stoch_k > stoch_d and 20 < stoch_k < 80:
            score += 4
            reasons.append({
                'icon': '📊', 'title': 'STOCHASTIC YUKARI',
                'detail': f'K: {stoch_k:.1f} > D: {stoch_d:.1f}',
                'meaning': 'Kısa vade momentum pozitif'
            })
    
    return min(score, 20), reasons


# ════════════════════════════════════════════════════════════
# PUANLAMA - TREND (20 puan)
# ════════════════════════════════════════════════════════════

def score_trend(analysis):
    """Trend puanı - EMA'lar, Supertrend, ADX"""
    score = 0
    reasons = []
    
    current = analysis.get('current_price')
    ema_9 = analysis.get('ema_9')
    ema_21 = analysis.get('ema_21')
    ema_50 = analysis.get('ema_50')
    supertrend_dir = analysis.get('supertrend_dir')
    adx = analysis.get('adx')
    plus_di = analysis.get('plus_di')
    minus_di = analysis.get('minus_di')
    
    # EMA Sıralama (8 puan)
    if all(v is not None for v in [current, ema_9, ema_21, ema_50]):
        if current > ema_9 > ema_21 > ema_50:
            score += 8
            reasons.append({
                'icon': '🏆', 'title': 'MÜKEMMEL TREND',
                'detail': 'Fiyat > EMA9 > EMA21 > EMA50',
                'meaning': 'Tüm EMA\'lar düzgün sıralı - güçlü uptrend'
            })
        elif current > ema_9 > ema_21:
            score += 6
            reasons.append({
                'icon': '📈', 'title': 'TREND POZİTİF',
                'detail': 'Fiyat > EMA9 > EMA21',
                'meaning': 'Kısa vade trend yukarı'
            })
        elif current > ema_21:
            score += 3
            reasons.append({
                'icon': '📈', 'title': 'EMA21 ÜSTÜNDE',
                'detail': f'Fiyat ({current:.2f}) > EMA21 ({ema_21:.2f})',
                'meaning': 'Trend pozitif tarafta'
            })
    
    # EMA Yeni Kesişim
    prev_ema_9 = analysis.get('prev_ema_9')
    prev_ema_21 = analysis.get('prev_ema_21')
    if all(v is not None for v in [ema_9, ema_21, prev_ema_9, prev_ema_21]):
        if prev_ema_9 <= prev_ema_21 and ema_9 > ema_21:
            score += 4
            reasons.append({
                'icon': '⭐', 'title': 'YENİ TREND BAŞLANGICI',
                'detail': 'EMA9, EMA21 üstüne çıktı',
                'meaning': 'Trend dönüşü - güçlü alış sinyali'
            })
    
    # Supertrend (4 puan)
    if supertrend_dir == 1:
        score += 4
        reasons.append({
            'icon': '🟢', 'title': 'SUPERTREND YUKARI',
            'detail': 'Supertrend yeşil bölgede',
            'meaning': 'Trend yönü kesin yukarı'
        })
    
    # ADX Trend Gücü (4 puan)
    if adx is not None:
        if adx > 30 and plus_di and minus_di and plus_di > minus_di:
            score += 4
            reasons.append({
                'icon': '💪', 'title': 'GÜÇLÜ TREND',
                'detail': f'ADX: {adx:.1f} (+DI > -DI)',
                'meaning': 'Trend çok güçlü ve yukarı'
            })
        elif adx > 25:
            score += 2
    
    return min(score, 20), reasons


# ════════════════════════════════════════════════════════════
# PUANLAMA - VWAP & PİVOT (15 puan)
# ════════════════════════════════════════════════════════════

def score_vwap_pivot(analysis):
    """VWAP ve Pivot Point puanı"""
    score = 0
    reasons = []
    
    current = analysis.get('current_price')
    vwap = analysis.get('vwap')
    pivot = analysis.get('pivot')
    r1 = analysis.get('r1')
    r2 = analysis.get('r2')
    s1 = analysis.get('s1')
    
    # VWAP (8 puan)
    if current and vwap:
        diff_pct = ((current - vwap) / vwap) * 100
        
        if 0.5 <= diff_pct <= 2:
            score += 8
            reasons.append({
                'icon': '⭐', 'title': 'VWAP İDEAL',
                'detail': f'Fiyat VWAP üstünde (+{diff_pct:.2f}%)',
                'meaning': 'Day trader giriş bölgesi'
            })
        elif 2 < diff_pct <= 4:
            score += 5
            reasons.append({
                'icon': '📈', 'title': 'VWAP ÜSTÜNDE',
                'detail': f'+{diff_pct:.2f}% uzakta',
                'meaning': 'Alıcılar kontrolde'
            })
        elif -0.5 <= diff_pct < 0.5:
            score += 4
            reasons.append({
                'icon': '🎯', 'title': 'VWAP TESTİ',
                'detail': f'Fiyat VWAP\'a çok yakın',
                'meaning': 'Kritik karar noktası'
            })
        elif diff_pct < -1:
            reasons.append({
                'icon': '⚠️', 'title': 'VWAP ALTINDA',
                'detail': f'{diff_pct:.2f}% altta',
                'meaning': 'Satıcılar kontrolde, dikkat'
            })
    
    # Pivot Seviyeleri (7 puan)
    if current and pivot:
        if r1 and current > pivot and current < r1:
            score += 5
            reasons.append({
                'icon': '🎯', 'title': 'PİVOT ÜSTÜ',
                'detail': f'P:{pivot:.2f} < Fiyat:{current:.2f} < R1:{r1:.2f}',
                'meaning': 'R1 direncine doğru hareket'
            })
        elif r1 and r2 and current > r1 and current < r2:
            score += 7
            reasons.append({
                'icon': '🚀', 'title': 'R1 KIRILDI',
                'detail': f'R1 ({r1:.2f}) kırıldı, R2 ({r2:.2f}) hedefte',
                'meaning': 'Güçlü kırılım - momentum devam edebilir'
            })
        elif s1 and current < s1:
            reasons.append({
                'icon': '⚠️', 'title': 'S1 ALTINDA',
                'detail': f'S1 ({s1:.2f}) kırıldı',
                'meaning': 'Düşüş riski - dikkatli ol'
            })
        elif pivot and abs(current - pivot) / pivot < 0.005:
            score += 3
            reasons.append({
                'icon': '🎯', 'title': 'PİVOT TESTİ',
                'detail': f'Fiyat Pivot ({pivot:.2f}) üzerinde',
                'meaning': 'Kritik destek/direnç noktası'
            })
    
    return min(score, 15), reasons


# ════════════════════════════════════════════════════════════
# PUANLAMA - KIRILIM & MUM (15 puan)
# ════════════════════════════════════════════════════════════

def score_breakout_candle(analysis):
    """Kırılım ve Mum Formasyonu puanı"""
    score = 0
    reasons = []
    
    breakouts = analysis.get('breakouts', [])
    candle_patterns = analysis.get('candle_patterns', [])
    current = analysis.get('current_price')
    bb_upper = analysis.get('bb_upper')
    
    # Yukarı Kırılımlar (8 puan)
    up_breakouts = [b for b in breakouts if b['type'] == 'UP']
    if up_breakouts:
        max_period = max(b['period'] for b in up_breakouts)
        if max_period >= 50:
            score += 8
            reasons.append({
                'icon': '🚀', 'title': '50 GÜNLÜK ZİRVE KIRILDI',
                'detail': f'{max_period} günlük en yüksek kırıldı',
                'meaning': 'Çok güçlü teknik kırılım'
            })
        elif max_period >= 20:
            score += 6
            reasons.append({
                'icon': '🚀', 'title': '20 GÜNLÜK ZİRVE KIRILDI',
                'detail': f'{max_period} günlük zirve kırıldı',
                'meaning': 'Güçlü teknik kırılım'
            })
        elif max_period >= 10:
            score += 4
            reasons.append({
                'icon': '📈', 'title': 'KISA VADE KIRILIM',
                'detail': f'{max_period} günlük zirve aşıldı',
                'meaning': 'Momentum başlıyor'
            })
    
    # Bollinger Üst Kırılım (3 puan)
    if current and bb_upper:
        if current >= bb_upper * 0.99:
            score += 3
            reasons.append({
                'icon': '💥', 'title': 'BB ÜST BANT TESTİ',
                'detail': f'Fiyat ({current:.2f}) ≈ Üst Bant ({bb_upper:.2f})',
                'meaning': 'Volatilite kırılımı'
            })
    
    # Mum Formasyonları (4 puan)
    bullish_patterns = [p for p in candle_patterns if p.get('bullish')]
    if bullish_patterns:
        strongest = bullish_patterns[0]
        if strongest['key'] in ['three_white_soldiers', 'bullish_engulfing', 'morning_star']:
            score += 4
            reasons.append({
                'icon': strongest['icon'], 'title': f"FORMASYON: {strongest['name'].upper()}",
                'detail': strongest['meaning'],
                'meaning': 'Çok güçlü dönüş/devam sinyali'
            })
        else:
            score += 2
            reasons.append({
                'icon': strongest['icon'], 'title': f"Formasyon: {strongest['name']}",
                'detail': strongest['meaning'],
                'meaning': 'Pozitif mum formasyonu'
            })
    
    return min(score, 15), reasons


# ════════════════════════════════════════════════════════════
# PUANLAMA - LİKİDİTE (5 puan)
# ════════════════════════════════════════════════════════════

def score_liquidity(analysis):
    """Likidite puanı"""
    score = 0
    reasons = []
    
    rvol = analysis.get('rvol')
    current = analysis.get('current_price')
    volume = analysis.get('volume')
    
    if rvol and rvol >= 0.8:
        score += 2
    
    if current and volume:
        volume_tl = current * volume
        if volume_tl > 10_000_000:
            score += 3
            reasons.append({
                'icon': '✅', 'title': 'YÜKSEK LİKİDİTE',
                'detail': f'İşlem hacmi: {volume_tl/1_000_000:.1f}M TL',
                'meaning': 'Rahatça alıp satabilirsin'
            })
        elif volume_tl > 5_000_000:
            score += 2
    
    return min(score, 5), reasons


# ════════════════════════════════════════════════════════════
# TOPLAM PUAN
# ════════════════════════════════════════════════════════════

def calculate_total_score(analysis):
    """Tüm puanları topla"""
    vol_s, vol_r = score_volume(analysis)
    mom_s, mom_r = score_momentum(analysis)
    tre_s, tre_r = score_trend(analysis)
    vwp_s, vwp_r = score_vwap_pivot(analysis)
    brk_s, brk_r = score_breakout_candle(analysis)
    liq_s, liq_r = score_liquidity(analysis)
    
    total = vol_s + mom_s + tre_s + vwp_s + brk_s + liq_s
    all_reasons = vol_r + mom_r + tre_r + vwp_r + brk_r + liq_r
    
    return {
        'total': total,
        'breakdown': {
            'volume': {'score': vol_s, 'max': 25},
            'momentum': {'score': mom_s, 'max': 20},
            'trend': {'score': tre_s, 'max': 20},
            'vwap_pivot': {'score': vwp_s, 'max': 15},
            'breakout_candle': {'score': brk_s, 'max': 15},
            'liquidity': {'score': liq_s, 'max': 5},
        },
        'reasons': all_reasons
    }


# ════════════════════════════════════════════════════════════
# HEDEF VE STOP (3 HEDEF)
# ════════════════════════════════════════════════════════════

def calculate_targets(current_price, atr, analysis):
    """3 Hedef + Akıllı Stop"""
    if not atr or atr <= 0:
        atr_pct = 1.0
    else:
        atr_pct = (atr / current_price) * 100
        atr_pct = max(0.5, min(atr_pct, 4))
    
    target_1_pct = atr_pct * 1.5
    target_2_pct = atr_pct * 2.5
    target_3_pct = atr_pct * 4.0
    stop_pct = atr_pct * 1.0
    
    target_1 = round(current_price * (1 + target_1_pct / 100), 2)
    target_2 = round(current_price * (1 + target_2_pct / 100), 2)
    target_3 = round(current_price * (1 + target_3_pct / 100), 2)
    stop_loss = round(current_price * (1 - stop_pct / 100), 2)
    
    r1 = analysis.get('r1')
    r2 = analysis.get('r2')
    r3 = analysis.get('r3')
    
    if r1 and target_1 > r1 and r1 > current_price:
        target_1 = round(r1, 2)
        target_1_pct = round(((r1 - current_price) / current_price) * 100, 2)
    
    if r2 and target_2 > r2 and r2 > current_price:
        target_2 = round(r2, 2)
        target_2_pct = round(((r2 - current_price) / current_price) * 100, 2)
    
    if r3 and target_3 > r3 and r3 > current_price:
        target_3 = round(r3, 2)
        target_3_pct = round(((r3 - current_price) / current_price) * 100, 2)
    
    risk = current_price - stop_loss
    reward_avg = (target_2 - current_price)
    risk_reward = round(reward_avg / risk, 2) if risk > 0 else 0
    
    return {
        'entry': current_price,
        'target_1': target_1,
        'target_1_pct': round(target_1_pct, 2),
        'target_2': target_2,
        'target_2_pct': round(target_2_pct, 2),
        'target_3': target_3,
        'target_3_pct': round(target_3_pct, 2),
        'stop_loss': stop_loss,
        'stop_pct': round(stop_pct, 2),
        'risk_reward': risk_reward,
        'atr_value': round(atr, 4) if atr else None
    }


# ════════════════════════════════════════════════════════════
# UYARILAR
# ════════════════════════════════════════════════════════════

def generate_warnings(analysis):
    """Sinyal için uyarıları üret"""
    warnings = []
    suggestions = []
    
    rsi = analysis.get('rsi')
    rvol = analysis.get('rvol')
    macd_hist = analysis.get('macd_hist')
    prev_macd_hist = analysis.get('prev_macd_hist')
    momentum_status = analysis.get('momentum_status', {})
    
    if rsi:
        if rsi > 80:
            warnings.append({
                'level': 'EXTREME', 'icon': '🔴🔴',
                'title': 'RSI ÇOK YÜKSEK',
                'detail': f'RSI: {rsi:.1f} (80 üstü kritik)',
                'action': 'HEMEN KAR AL veya pozisyonu KÜÇÜLT!'
            })
        elif rsi > 75:
            warnings.append({
                'level': 'HIGH', 'icon': '🔴',
                'title': 'RSI AŞIRI ALIM',
                'detail': f'RSI: {rsi:.1f}',
                'action': 'Kısmi kar al düşün'
            })
        elif rsi > 70:
            warnings.append({
                'level': 'MEDIUM', 'icon': '⚠️',
                'title': 'RSI Yüksek',
                'detail': f'RSI: {rsi:.1f}',
                'action': 'Dikkatli ol, takip et'
            })
    
    if macd_hist is not None and prev_macd_hist is not None:
        if macd_hist > 0 and macd_hist < prev_macd_hist:
            warnings.append({
                'level': 'MEDIUM', 'icon': '⚠️',
                'title': 'MOMENTUM AZALIYOR',
                'detail': 'MACD histogram düşüyor',
                'action': 'Kârdaysan kısmi satış düşün'
            })
    
    if rvol is not None and rvol < 0.7:
        warnings.append({
            'level': 'LOW', 'icon': '⚠️',
            'title': 'HACİM DÜŞÜK',
            'detail': f'RVOL: {rvol:.2f}x',
            'action': 'Sahte hareket olabilir, dikkatli ol'
        })
    
    candle_patterns = analysis.get('candle_patterns', [])
    bearish = [p for p in candle_patterns if not p.get('bullish')]
    if bearish:
        for bp in bearish[:1]:
            warnings.append({
                'level': 'HIGH', 'icon': bp['icon'],
                'title': f"BEARISH: {bp['name']}",
                'detail': bp['meaning'],
                'action': 'Pozisyonunu gözden geçir'
            })
    
    if momentum_status.get('warning'):
        suggestions.append({
            'icon': '💡',
            'text': momentum_status['warning']
        })
    
    if momentum_status.get('suggestion'):
        suggestions.append({
            'icon': '🎯',
            'text': momentum_status['suggestion']
        })
    
    return warnings, suggestions


# ════════════════════════════════════════════════════════════
# SİNYAL GÜCÜ
# ════════════════════════════════════════════════════════════

def determine_strength(score):
    """Puana göre sinyal sınıflandırması"""
    if score >= 85:
        return {
            'type': 'AL', 'strength': 'COK_GUCLU',
            'label': 'ÇOK GÜÇLÜ AL', 'emoji': '🔥🔥🔥',
            'color': '🟢', 'action': 'ŞİMDİ AL!',
            'confidence': 'Yüksek güvenilirlik'
        }
    elif score >= 75:
        return {
            'type': 'AL', 'strength': 'GUCLU',
            'label': 'GÜÇLÜ AL', 'emoji': '🔥🔥',
            'color': '🟢', 'action': 'AL',
            'confidence': 'İyi güvenilirlik'
        }
    elif score >= 65:
        return {
            'type': 'AL', 'strength': 'NORMAL',
            'label': 'AL', 'emoji': '🔥',
            'color': '🟢', 'action': 'AL (dikkatli)',
            'confidence': 'Orta güvenilirlik'
        }
    elif score >= 50:
        return {
            'type': 'BEKLE', 'strength': 'ZAYIF',
            'label': 'BEKLE / İZLE', 'emoji': '🟡',
            'color': '🟡', 'action': 'BEKLE',
            'confidence': 'Belirsiz'
        }
    else:
        return {
            'type': 'YOK', 'strength': 'YOK',
            'label': 'SİNYAL YOK', 'emoji': '⚪',
            'color': '⚪', 'action': 'GİRMİYORUM',
            'confidence': 'Sinyal yok'
        }


# ════════════════════════════════════════════════════════════
# SİNYAL ÜRETME
# ════════════════════════════════════════════════════════════

def generate_signal(symbol, analysis, history_df=None):
    """Tam profesyonel sinyal üret"""
    if not analysis:
        return None
    
    current_price = analysis.get('current_price')
    if not current_price:
        return None
    
    score_data = calculate_total_score(analysis)
    total_score = score_data['total']
    signal_info = determine_strength(total_score)
    
    atr = analysis.get('atr')
    targets = calculate_targets(current_price, atr, analysis)
    warnings, suggestions = generate_warnings(analysis)
    
    filled = int(total_score / 5)
    empty = 20 - filled
    score_bar = '█' * filled + '░' * empty
    
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
    
    key_levels = {
        'vwap': analysis.get('vwap'),
        'pivot': analysis.get('pivot'),
        'r1': analysis.get('r1'),
        'r2': analysis.get('r2'),
        's1': analysis.get('s1'),
        'prev_day_high': analysis.get('prev_day_high'),
        'prev_day_low': analysis.get('prev_day_low'),
        'ema_9': analysis.get('ema_9'),
        'ema_21': analysis.get('ema_21'),
        'ema_50': analysis.get('ema_50'),
    }
    
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
        'confidence': signal_info['confidence'],
        'targets': targets,
        'reasons': score_data['reasons'],
        'breakdown': score_data['breakdown'],
        'warnings': warnings,
        'suggestions': suggestions,
        'key_levels': key_levels,
        'candle_patterns': analysis.get('candle_patterns', []),
        'breakouts': analysis.get('breakouts', []),
        'momentum_status': analysis.get('momentum_status', {}),
        'indicators': {
            'rsi': analysis.get('rsi'),
            'macd': analysis.get('macd'),
            'rvol': analysis.get('rvol'),
            'adx': analysis.get('adx'),
            'supertrend_dir': analysis.get('supertrend_dir'),
            'atr': analysis.get('atr'),
        }
    }
    
    return signal


# ════════════════════════════════════════════════════════════
# MESAJ FORMATLAMA
# ════════════════════════════════════════════════════════════

def format_signal_message(signal):
    """Console için güzel format"""
    if not signal:
        return "Sinyal yok"
    
    msg = []
    msg.append("╔══════════════════════════════════════╗")
    msg.append(f"║  {signal['emoji']} {signal['label']}")
    msg.append("║  ══════════════════════════════════")
    msg.append(f"║  📌 {signal['symbol']}")
    msg.append(f"║  💰 Fiyat: {signal['current_price']:.2f} TL")
    msg.append(f"║  ⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}")
    msg.append("╠══════════════════════════════════════╣")
    msg.append(f"║  💯 SKOR: {signal['score']}/100")
    msg.append(f"║  {signal['score_bar']}")
    msg.append(f"║  {signal['stars']}")
    msg.append(f"║  📊 {signal['confidence']}")
    msg.append("╠══════════════════════════════════════╣")
    msg.append("║  💼 İŞLEM PLANI - 3 HEDEF SİSTEMİ")
    t = signal['targets']
    msg.append(f"║  📥 GİRİŞ    : {t['entry']:.2f} TL")
    msg.append(f"║  🎯 HEDEF 1  : {t['target_1']:.2f} TL (+{t['target_1_pct']}%)")
    msg.append(f"║     → %33 sat, stop'u girişe çek")
    msg.append(f"║  🎯 HEDEF 2  : {t['target_2']:.2f} TL (+{t['target_2_pct']}%)")
    msg.append(f"║     → %33 sat, stop'u H1'e çek")
    msg.append(f"║  🎯 HEDEF 3  : {t['target_3']:.2f} TL (+{t['target_3_pct']}%)")
    msg.append(f"║     → Kalanı sat (trend kırılırsa)")
    msg.append(f"║  🛑 STOP     : {t['stop_loss']:.2f} TL (-{t['stop_pct']}%)")
    msg.append(f"║  ⚖️ R/Ö     : 1/{t['risk_reward']}")
    msg.append("╠══════════════════════════════════════╣")
    msg.append(f"║  ✅ ALMA SEBEPLERİ ({len(signal['reasons'])})")
    for r in signal['reasons']:
        msg.append(f"║  {r['icon']} {r['title']}")
        msg.append(f"║     {r['detail']}")
        msg.append(f"║     → {r['meaning']}")
    
    if signal['warnings']:
        msg.append("╠══════════════════════════════════════╣")
        msg.append(f"║  ⚠️ UYARILAR ({len(signal['warnings'])})")
        for w in signal['warnings']:
            msg.append(f"║  {w['icon']} {w['title']}")
            msg.append(f"║     {w['detail']}")
            msg.append(f"║     💡 {w['action']}")
    
    msg.append("╠══════════════════════════════════════╣")
    msg.append("║  📊 PUAN DAĞILIMI")
    b = signal['breakdown']
    msg.append(f"║  💥 Hacim       : {b['volume']['score']}/{b['volume']['max']}")
    msg.append(f"║  ⚡ Momentum    : {b['momentum']['score']}/{b['momentum']['max']}")
    msg.append(f"║  📈 Trend       : {b['trend']['score']}/{b['trend']['max']}")
    msg.append(f"║  ⭐ VWAP/Pivot  : {b['vwap_pivot']['score']}/{b['vwap_pivot']['max']}")
    msg.append(f"║  🚀 Kırılım/Mum : {b['breakout_candle']['score']}/{b['breakout_candle']['max']}")
    msg.append(f"║  💧 Likidite    : {b['liquidity']['score']}/{b['liquidity']['max']}")
    
    if signal['key_levels'].get('vwap') or signal['key_levels'].get('pivot'):
        msg.append("╠══════════════════════════════════════╣")
        msg.append("║  📍 ÖNEMLİ SEVİYELER")
        kl = signal['key_levels']
        if kl.get('vwap'):
            msg.append(f"║  VWAP   : {kl['vwap']:.2f}")
        if kl.get('pivot'):
            msg.append(f"║  Pivot  : {kl['pivot']:.2f}")
        if kl.get('r1'):
            msg.append(f"║  R1     : {kl['r1']:.2f}")
        if kl.get('s1'):
            msg.append(f"║  S1     : {kl['s1']:.2f}")
        if kl.get('ema_9'):
            msg.append(f"║  EMA 9  : {kl['ema_9']:.2f}")
        if kl.get('ema_21'):
            msg.append(f"║  EMA 21 : {kl['ema_21']:.2f}")
    
    msg.append("╚══════════════════════════════════════╝")
    
    return "\n".join(msg)


# ════════════════════════════════════════════════════════════
# TEST
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import pandas as pd
    from database import get_stock_history
    from analyzer import analyze_stock
    
    test_symbols = ["AKBNK.IS", "THYAO.IS", "ASELS.IS", "AEFES.IS", "AKSA.IS"]
    
    print("\n🧪 SİNYAL MOTORU TESTİ (PROFESYONEL)")
    print("=" * 60)
    
    for symbol in test_symbols:
        print(f"\n📊 {symbol}")
        data = get_stock_history(symbol, days=300)
        
        if data:
            df = pd.DataFrame(data)
            analysis = analyze_stock(df)
            
            if analysis:
                signal = generate_signal(symbol, analysis, df)
                if signal:
                    print(format_signal_message(signal))
        else:
            print(f"   ❌ Veri yok")
    
    print("\n✅ Test tamamlandı!")