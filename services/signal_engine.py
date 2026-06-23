"""
Profesyonel Sinyal Motoru - SWING Trading
Puanlama, Hedef 1/2/3, Stop, Momentum Uyarıları, Tutma Süresi Önerisi

GÜNCELLEMELER:
- VWAP kaldırıldı (15 puan tamamen Pivot'a)
- Hedef sıralama bug fix (H1 < H2 < H3 garantisi)
- SWING dili (Day Trade → Swing Trade)
- Tutma süresi önerisi eklendi
- Risk seviyesi eklendi
- Pivot Point güçlendirildi
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
# PUANLAMA - PİVOT POINT (15 puan) - VWAP KALDIRILDI
# ════════════════════════════════════════════════════════════

def score_vwap_pivot(analysis):
    """
    Pivot Point puanı (VWAP KALDIRILDI - 15 puan tamamen Pivot'a)
    
    Eski sistem: VWAP (8) + Pivot (7) = 15 puan
    Yeni sistem: Sadece Pivot (15 puan)
    
    Mantık: Pivot üstündeki hisseler yükselme eğiliminde
    """
    score = 0
    reasons = []
    
    current = analysis.get('current_price')
    pivot = analysis.get('pivot')
    r1 = analysis.get('r1')
    r2 = analysis.get('r2')
    r3 = analysis.get('r3')
    s1 = analysis.get('s1')
    
    # ═══════════════════════════════════════════
    # PİVOT POINT SKORU (15 puan - tamamı)
    # ═══════════════════════════════════════════
    
    if not (current and pivot):
        return 0, []
    
    # R2 üstünde mi? (En güçlü kırılım - 13-15 puan)
    if r2 and current > r2:
        if r3 and current < r3:
            score = 15  # MAKSİMUM
            reasons.append({
                'icon': '🚀', 'title': 'R2 KIRILDI - ÇOK GÜÇLÜ!',
                'detail': f'R2 ({r2:.2f}) kırıldı, R3 ({r3:.2f}) hedefte',
                'meaning': 'Çok güçlü momentum - kırılım onaylandı'
            })
        elif r3:
            score = 13
            reasons.append({
                'icon': '🚀', 'title': 'R3 ÜSTÜNDE',
                'detail': f'R3 ({r3:.2f}) bile geçildi',
                'meaning': 'Olağanüstü güçlü hareket - dikkatli ol'
            })
        else:
            score = 13
            reasons.append({
                'icon': '🚀', 'title': 'R2 ÜSTÜNDE',
                'detail': f'R2 ({r2:.2f}) geçildi',
                'meaning': 'Güçlü yukarı hareket devam ediyor'
            })
    
    # R1-R2 arası (Güçlü pozisyon - 11 puan)
    elif r1 and r2 and current > r1 and current <= r2:
        score = 11
        reasons.append({
            'icon': '🎯', 'title': 'R1 KIRILDI',
            'detail': f'R1 ({r1:.2f}) kırıldı, R2 ({r2:.2f}) hedefte',
            'meaning': 'Yukarı momentum başladı - güçlü sinyal'
        })
    
    # Pivot-R1 arası (Pozitif hareket - 9 puan)
    elif r1 and current > pivot and current <= r1:
        # R1'e ne kadar yakın?
        distance_to_r1 = ((r1 - current) / current) * 100
        
        if distance_to_r1 < 1:  # R1'e %1'den yakın
            score = 10
            reasons.append({
                'icon': '🎯', 'title': 'R1 YAKININDA',
                'detail': f'R1 ({r1:.2f}) test ediliyor (%{distance_to_r1:.2f} uzakta)',
                'meaning': 'Kırılım çok yakın - dikkatle izle'
            })
        else:
            score = 9
            reasons.append({
                'icon': '📈', 'title': 'PİVOT ÜSTÜ',
                'detail': f'Pivot ({pivot:.2f}) üstünde, R1 ({r1:.2f}) hedefte',
                'meaning': 'Yukarı hareket başlıyor - alıcılar kontrolde'
            })
    
    # Pivot testi (Kritik nokta - 7 puan)
    elif pivot and abs(current - pivot) / pivot < 0.005:
        score = 7
        reasons.append({
            'icon': '🎯', 'title': 'PİVOT TESTİ',
            'detail': f'Fiyat Pivot ({pivot:.2f}) üzerinde',
            'meaning': 'Kritik destek/direnç - yön belirleniyor'
        })
    
    # Pivot altında ama S1 üstünde (Zayıf - 4 puan)
    elif s1 and pivot and current > s1 and current < pivot:
        score = 4
        reasons.append({
            'icon': '⚠️', 'title': 'PİVOT ALTI',
            'detail': f'Pivot ({pivot:.2f}) altında ama S1 ({s1:.2f}) üstünde',
            'meaning': 'Toparlanma bekleniyor - dikkatli ol'
        })
    
    # S1 altında - Risk (0 puan + uyarı)
    elif s1 and current < s1:
        reasons.append({
            'icon': '⚠️', 'title': 'S1 KIRILDI - RİSK',
            'detail': f'S1 ({s1:.2f}) altına indi',
            'meaning': 'Düşüş riski yüksek - alım için bekle'
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
# HEDEF VE STOP (3 HEDEF) - SWING OPTIMIZED + BUG FIX
# ════════════════════════════════════════════════════════════

def calculate_targets(current_price, atr, analysis):
    """
    3 Hedef + Akıllı Stop - SWING için optimize
    DÜZELTİLDİ: Hedef sıralama garantisi (H1 < H2 < H3)
    
    SWING hedef yüzdeleri:
    - Hedef 1: %3-4 (1-2 gün)
    - Hedef 2: %5-7 (2-4 gün)
    - Hedef 3: %8-12 (3-7 gün)
    - Stop:    %2-3
    """
    if not atr or atr <= 0:
        atr_pct = 1.0
    else:
        atr_pct = (atr / current_price) * 100
        atr_pct = max(0.5, min(atr_pct, 4))
    
    # SWING için optimize edilmiş yüzdeler
    target_1_pct = atr_pct * 2.0    # %3-4 (1-2 gün)
    target_2_pct = atr_pct * 3.5    # %5-7 (2-4 gün)
    target_3_pct = atr_pct * 5.5    # %8-12 (3-7 gün)
    stop_pct = atr_pct * 1.5         # %2-3 (rahat)
    
    target_1 = round(current_price * (1 + target_1_pct / 100), 2)
    target_2 = round(current_price * (1 + target_2_pct / 100), 2)
    target_3 = round(current_price * (1 + target_3_pct / 100), 2)
    stop_loss = round(current_price * (1 - stop_pct / 100), 2)
    
    # Pivot değerlerini al
    r1 = analysis.get('r1')
    r2 = analysis.get('r2')
    r3 = analysis.get('r3')
    
    # Pivot değerleri ile güçlendirme (hedef YUKARI çekilebilir)
    # Hedef AŞAĞI çekilmez!
    if r2 and r2 > current_price:
        # R2 hedef 2'den yüksekse R2'yi kullan
        if r2 > target_2:
            target_2 = round(r2, 2)
    
    if r3 and r3 > current_price:
        # R3 hedef 3'ten yüksekse R3'ü kullan
        if r3 > target_3:
            target_3 = round(r3, 2)
    
    # ⭐ KRİTİK FIX: Hedef sıralaması garantisi
    # Hedeflerin doğru sıralanması ZORUNLU (H1 < H2 < H3)
    if target_2 <= target_1:
        target_2 = round(target_1 * 1.025, 2)  # En az %2.5 üstüne
    if target_3 <= target_2:
        target_3 = round(target_2 * 1.030, 2)  # En az %3 üstüne
    
    # Yüzdeleri yeniden hesapla (sıralama fix sonrası)
    target_1_pct = round(((target_1 - current_price) / current_price) * 100, 2)
    target_2_pct = round(((target_2 - current_price) / current_price) * 100, 2)
    target_3_pct = round(((target_3 - current_price) / current_price) * 100, 2)
    
    # Risk/Ödül hesabı
    risk = current_price - stop_loss
    reward_avg = (target_2 - current_price)
    risk_reward = round(reward_avg / risk, 2) if risk > 0 else 0
    
    return {
        'entry': current_price,
        'target_1': target_1,
        'target_1_pct': target_1_pct,
        'target_2': target_2,
        'target_2_pct': target_2_pct,
        'target_3': target_3,
        'target_3_pct': target_3_pct,
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
# SİNYAL GÜCÜ - SWING DİLİ
# ════════════════════════════════════════════════════════════

def determine_strength(score):
    """
    Puana göre sinyal sınıflandırması - SWING odaklı
    Action mesajları sakinleştirildi (day trade dili → swing dili)
    """
    if score >= 85:
        return {
            'type': 'AL', 'strength': 'COK_GUCLU',
            'label': 'ÇOK GÜÇLÜ AL', 'emoji': '🔥🔥🔥',
            'color': '🟢', 
            'action': 'AL - Güçlü pozisyon aç',
            'confidence': 'Yüksek güvenilirlik',
            'risk_level': 'Düşük'
        }
    elif score >= 75:
        return {
            'type': 'AL', 'strength': 'GUCLU',
            'label': 'GÜÇLÜ AL', 'emoji': '🔥🔥',
            'color': '🟢', 
            'action': 'AL - Kademeli giriş yap',
            'confidence': 'İyi güvenilirlik',
            'risk_level': 'Orta-Düşük'
        }
    elif score >= 65:
        return {
            'type': 'AL', 'strength': 'NORMAL',
            'label': 'AL', 'emoji': '🔥',
            'color': '🟢', 
            'action': 'AL - Küçük pozisyon ile başla',
            'confidence': 'Orta güvenilirlik',
            'risk_level': 'Orta'
        }
    elif score >= 50:
        return {
            'type': 'BEKLE', 'strength': 'ZAYIF',
            'label': 'BEKLE / İZLE', 'emoji': '🟡',
            'color': '🟡', 
            'action': 'BEKLE - Henüz alma',
            'confidence': 'Belirsiz',
            'risk_level': 'Yüksek'
        }
    else:
        return {
            'type': 'YOK', 'strength': 'YOK',
            'label': 'SİNYAL YOK', 'emoji': '⚪',
            'color': '⚪', 
            'action': 'GİRMİYORUM',
            'confidence': 'Sinyal yok',
            'risk_level': '-'
        }


# ════════════════════════════════════════════════════════════
# TUTMA SÜRESİ ÖNERİSİ - YENİ FONKSİYON
# ════════════════════════════════════════════════════════════

def suggest_holding_period(score, indicators):
    """
    Skora ve indikatörlere göre tutma süresi öner
    SWING TRADE için optimize
    
    Returns:
        dict: {duration, strategy, reason, max_days}
    """
    rsi = indicators.get('rsi', 50)
    rvol = indicators.get('rvol', 1)
    macd = indicators.get('macd', 0)
    adx = indicators.get('adx', 0)
    
    if score >= 85:
        # Çok güçlü - hızlı momentum
        return {
            'duration': '1-2 gün',
            'strategy': 'HIZLI SWING',
            'reason': 'Çok güçlü momentum, hedefler hızlı vurulabilir',
            'max_days': 3
        }
    elif score >= 75:
        # Güçlü - standart swing
        return {
            'duration': '2-4 gün',
            'strategy': 'STANDART SWING',
            'reason': 'Sağlıklı trend, normal tutma süresi',
            'max_days': 5
        }
    elif score >= 65:
        # Normal - sabırlı swing
        return {
            'duration': '3-7 gün',
            'strategy': 'UZUN SWING',
            'reason': 'Trend var ama sabırlı olmalı',
            'max_days': 10
        }
    elif score >= 50:
        # Bekleme
        return {
            'duration': '-',
            'strategy': 'BEKLEME',
            'reason': 'Sinyal güçlenmesini bekleyin',
            'max_days': 0
        }
    else:
        return {
            'duration': '-',
            'strategy': 'YOK',
            'reason': 'Sinyal yok',
            'max_days': 0
        }


# ════════════════════════════════════════════════════════════
# SİNYAL ÜRETME - GÜNCELLENMİŞ
# ════════════════════════════════════════════════════════════

def generate_signal(symbol, analysis, history_df=None):
    """
    Tam profesyonel sinyal üret - SWING optimized
    YENİ: Tutma süresi önerisi, risk seviyesi
    """
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
    
    # İndikatörleri topla (suggest_holding için)
    indicators = {
        'rsi': analysis.get('rsi'),
        'macd': analysis.get('macd'),
        'rvol': analysis.get('rvol'),
        'adx': analysis.get('adx'),
        'supertrend_dir': analysis.get('supertrend_dir'),
        'atr': analysis.get('atr'),
    }
    
    # YENİ: Tutma süresi önerisi
    holding = suggest_holding_period(total_score, indicators)
    
    # Skor bar
    filled = int(total_score / 5)
    empty = 20 - filled
    score_bar = '█' * filled + '░' * empty
    
    # Yıldızlar
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
    
    # Anahtar seviyeler (VWAP kaldırıldı)
    key_levels = {
        # 'vwap': None,  # VWAP kaldırıldı - günlük veride yanlış
        'pivot': analysis.get('pivot'),
        'r1': analysis.get('r1'),
        'r2': analysis.get('r2'),
        'r3': analysis.get('r3'),  # YENİ: R3 de eklendi
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
        'risk_level': signal_info['risk_level'],  # YENİ
        'holding': holding,                        # YENİ
        'targets': targets,
        'reasons': score_data['reasons'],
        'breakdown': score_data['breakdown'],
        'warnings': warnings,
        'suggestions': suggestions,
        'key_levels': key_levels,
        'candle_patterns': analysis.get('candle_patterns', []),
        'breakouts': analysis.get('breakouts', []),
        'momentum_status': analysis.get('momentum_status', {}),
        'indicators': indicators,
    }
    
    return signal


# ════════════════════════════════════════════════════════════
# MESAJ FORMATLAMA (Console için)
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
    
    # YENİ: Strateji bilgisi
    holding = signal.get('holding', {})
    if holding and holding.get('strategy') and holding.get('strategy') != 'YOK':
        msg.append("╠══════════════════════════════════════╣")
        msg.append(f"║  📋 STRATEJİ: {holding.get('strategy', '')}")
        if holding.get('duration', '-') != '-':
            msg.append(f"║  📅 Tutma: {holding.get('duration', '')}")
        msg.append(f"║  🎲 Risk: {signal.get('risk_level', '-')}")
    
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
    msg.append(f"║  🎯 Pivot Point : {b['vwap_pivot']['score']}/{b['vwap_pivot']['max']}")
    msg.append(f"║  🚀 Kırılım/Mum : {b['breakout_candle']['score']}/{b['breakout_candle']['max']}")
    msg.append(f"║  💧 Likidite    : {b['liquidity']['score']}/{b['liquidity']['max']}")
    
    if signal['key_levels'].get('pivot'):
        msg.append("╠══════════════════════════════════════╣")
        msg.append("║  📍 ÖNEMLİ SEVİYELER")
        kl = signal['key_levels']
        if kl.get('pivot'):
            msg.append(f"║  Pivot  : {kl['pivot']:.2f}")
        if kl.get('r1'):
            msg.append(f"║  R1     : {kl['r1']:.2f}")
        if kl.get('r2'):
            msg.append(f"║  R2     : {kl['r2']:.2f}")
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
    
    print("\n🧪 SİNYAL MOTORU TESTİ (PROFESYONEL - SWING)")
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
