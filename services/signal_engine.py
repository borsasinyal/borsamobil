"""
Profesyonel Sinyal Motoru
TAM PAKET + Intraday Range Tespiti
- Gün içi büyük hareketleri yakalar (VESBE gibi)
- Tavan olmuş hisseyi ÖNERMEZ
- Fiyat takibi yapar
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta


TR_TIMEZONE = timezone(timedelta(hours=3))

def tr_now():
    return datetime.now(TR_TIMEZONE)


# ════════════════════════════════════════════════════════════
# AKILLI HACİM (25 puan)
# ════════════════════════════════════════════════════════════

def score_volume(analysis):
    score = 0
    reasons = []
    rvol = analysis.get('rvol', 1)
    current = analysis.get('current_price')
    prev_close = analysis.get('prev_close')
    
    if not (current and prev_close and prev_close > 0):
        return 0, []
    
    is_up = current > prev_close
    
    if is_up:
        if rvol >= 5:
            score = 25
            reasons.append({'icon': '🚀', 'title': 'GÜÇLÜ ALIŞ BASKISI', 'detail': f'RVOL: {rvol:.1f}x', 'meaning': 'Kurumsal alım'})
        elif rvol >= 3:
            score = 22
            reasons.append({'icon': '💥', 'title': 'YÜKSEK HACİM', 'detail': f'RVOL: {rvol:.1f}x', 'meaning': 'Güçlü alış'})
        elif rvol >= 2:
            score = 18
            reasons.append({'icon': '📊', 'title': 'HACİM ARTIŞI', 'detail': f'RVOL: {rvol:.1f}x', 'meaning': 'İyi alış'})
        elif rvol >= 1.5:
            score = 14
            reasons.append({'icon': '📊', 'title': 'NORMAL ÜSTÜ HACİM', 'detail': f'RVOL: {rvol:.1f}x', 'meaning': 'Yeterli alış'})
        elif rvol >= 1.0:
            score = 10
            reasons.append({'icon': '📊', 'title': 'HACİM NORMAL', 'detail': f'RVOL: {rvol:.1f}x', 'meaning': 'Yükselişte normal'})
        elif rvol >= 0.7:
            score = 6
    else:
        if rvol >= 3:
            score = 0
            reasons.append({'icon': '⚠️', 'title': 'SATIŞ BASKISI', 'detail': f'RVOL: {rvol:.1f}x düşüşte', 'meaning': 'Yüksek hacimle satılıyor'})
        elif rvol >= 1.5:
            score = 3
        elif rvol >= 0.8:
            score = 5
    
    if rvol < 0.5:
        reasons.append({'icon': '⚠️', 'title': 'HACİM DÜŞÜK', 'detail': f'RVOL: {rvol:.1f}x', 'meaning': 'İlgi az'})
    
    return min(score, 25), reasons


# ════════════════════════════════════════════════════════════
# HACİM TRENDİ
# ════════════════════════════════════════════════════════════

def score_volume_trend(analysis):
    score = 0
    reasons = []
    today_volume = analysis.get('volume', 0)
    avg_volume_5 = analysis.get('avg_volume_5', 0)
    
    if not (today_volume > 0 and avg_volume_5 > 0):
        return 0, []
    
    volume_ratio = today_volume / avg_volume_5
    
    if volume_ratio >= 1.5:
        score = 8
        reasons.append({'icon': '📈', 'title': 'HACİM TRENDİ YÜKSELİŞTE', 'detail': f'5 gün ortalamasının %{(volume_ratio-1)*100:.0f} üstünde', 'meaning': 'Artan ilgi'})
    elif volume_ratio >= 1.2:
        score = 5
        reasons.append({'icon': '📊', 'title': 'HACİM ARTIYOR', 'detail': '5 gün ortalamasının üstünde', 'meaning': 'Pozitif hacim'})
    elif volume_ratio >= 0.8:
        score = 2
    elif volume_ratio >= 0.5:
        score = -3
        reasons.append({'icon': '⚠️', 'title': 'HACİM AZALIYOR', 'detail': '5 gün ortalamasının altında', 'meaning': 'İlgi azalıyor'})
    else:
        score = -5
        reasons.append({'icon': '🔴', 'title': 'HACİM ÇOK DÜŞÜK', 'detail': f'Ortalama %{(1-volume_ratio)*100:.0f} altında', 'meaning': 'İlgi yok'})
    
    return score, reasons


# ════════════════════════════════════════════════════════════
# TREND SAĞLIĞI
# ════════════════════════════════════════════════════════════

def score_trend_health(analysis):
    score = 0
    reasons = []
    
    current = analysis.get('current_price')
    prev_close = analysis.get('prev_close')
    prev_day_high = analysis.get('prev_day_high')
    prev_day_low = analysis.get('prev_day_low')
    ema_9 = analysis.get('ema_9')
    ema_21 = analysis.get('ema_21')
    
    if not (current and prev_close and ema_9 and ema_21):
        return 0, []
    
    daily_change = ((current - prev_close) / prev_close) * 100
    
    if current < ema_21 and current < prev_close:
        score -= 8
        reasons.append({'icon': '📉', 'title': 'FİYAT BOZULMASI', 'detail': 'Düşüş + EMA21 altı', 'meaning': 'Trend zayıflıyor'})
    elif current < prev_close * 0.98:
        score -= 4
        reasons.append({'icon': '⚠️', 'title': 'GÜNLÜK DÜŞÜŞ', 'detail': f'%{daily_change:.2f} düşüş', 'meaning': 'Kısa vade zayıflık'})
    
    if prev_day_high and current > prev_day_high:
        score += 3
        reasons.append({'icon': '🚀', 'title': 'DÜN ZİRVESİ KIRILDI', 'detail': f'Dün H: {prev_day_high:.2f} → {current:.2f}', 'meaning': 'Pozitif momentum'})
    elif prev_day_low and current < prev_day_low:
        score -= 5
        reasons.append({'icon': '🔴', 'title': 'DÜN DİBİ KIRILDI', 'detail': f'Dün L: {prev_day_low:.2f} → {current:.2f}', 'meaning': 'Düşüş devam'})
    
    rsi = analysis.get('rsi')
    prev_rsi = analysis.get('prev_rsi')
    if rsi and prev_rsi:
        if rsi < prev_rsi - 5 and rsi > 50:
            score -= 3
            reasons.append({'icon': '⚠️', 'title': 'RSI ZAYIFLIYOR', 'detail': f'RSI: {prev_rsi:.1f} → {rsi:.1f}', 'meaning': 'Momentum kaybediyor'})
    
    return score, reasons


# ════════════════════════════════════════════════════════════
# YENİ: İNTRADAY RANGE TESPİTİ (VESBE gibi hisseler için!)
# ════════════════════════════════════════════════════════════

def score_intraday_range(analysis):
    """
    GÜN İÇİ DİP-ZİRVE FARKI kontrolü
    
    VESBE gibi: Dün kapanış 6.66, bugün 6.69 (+%0.45)
    AMA gün içi: dip 6.05, zirve 6.71 = +%10.9 hareket!
    
    Daily change görmez ama intraday range yakalar!
    """
    score = 0
    reasons = []
    
    current = analysis.get('current_price')
    today_high = analysis.get('high')
    today_low = analysis.get('low')
    rvol = analysis.get('rvol', 1)
    
    if not (current and today_high and today_low and today_low > 0):
        return 0, []
    
    # Gün içi hareket yüzdesi
    intraday_range = ((today_high - today_low) / today_low) * 100
    
    # Fiyat zirveye ne kadar yakın?
    if today_high > 0:
        distance_to_high = ((today_high - current) / today_high) * 100
    else:
        distance_to_high = 100
    
    at_high = distance_to_high < 2  # Zirveye %2 yakında
    
    # ═══════════════════════════════════════════
    # GÜN İÇİ BÜYÜK HAREKET TESPİTİ
    # ═══════════════════════════════════════════
    
    # %8+ intraday range + zirvedeyse = TAVAN ADAYI!
    if intraday_range >= 8 and at_high and rvol >= 2:
        score = 15
        reasons.append({
            'icon': '⚡', 'title': f'GÜN İÇİ PATLAMA! +%{intraday_range:.1f}',
            'detail': f'Dip: {today_low:.2f} → Zirve: {today_high:.2f} (Şuan: {current:.2f})',
            'meaning': 'Tavan adayı - güçlü gün içi hareket!'
        })
    
    elif intraday_range >= 8 and at_high:
        score = 12
        reasons.append({
            'icon': '⚡', 'title': f'GÜN İÇİ +%{intraday_range:.1f} HAREKET',
            'detail': f'Dip: {today_low:.2f} → Zirve: {today_high:.2f}',
            'meaning': 'Çok güçlü gün içi yükseliş'
        })
    
    # %5-8 intraday range + zirvedeyse = İYİ FIRSAT
    elif intraday_range >= 5 and at_high and rvol >= 1.5:
        score = 10
        reasons.append({
            'icon': '🚀', 'title': f'GÜN İÇİ GÜÇLÜ +%{intraday_range:.1f}',
            'detail': f'Dip: {today_low:.2f} → Zirve: {today_high:.2f}',
            'meaning': 'Güçlü gün içi hareket - potansiyel devam'
        })
    
    elif intraday_range >= 5 and at_high:
        score = 7
        reasons.append({
            'icon': '📈', 'title': f'GÜN İÇİ +%{intraday_range:.1f}',
            'detail': f'Dip: {today_low:.2f} → {current:.2f}',
            'meaning': 'İyi gün içi hareket'
        })
    
    # %3-5 intraday range + zirvedeyse
    elif intraday_range >= 3 and at_high and rvol >= 1.5:
        score = 5
        reasons.append({
            'icon': '📈', 'title': f'GÜN İÇİ POZİTİF +%{intraday_range:.1f}',
            'detail': f'{today_low:.2f} → {current:.2f}',
            'meaning': 'Pozitif gün içi hareket'
        })
    
    elif intraday_range >= 3 and at_high:
        score = 3
    
    # Fiyat zirvedeyse ama intraday range küçük → az puan
    elif intraday_range >= 2 and at_high:
        score = 1
    
    # Fiyat zirVEDE DEĞİLSE (geri çekilmiş) → bonus verme
    # Çünkü gün içi çıktı ama geri döndü = sahte
    
    return score, reasons


# ════════════════════════════════════════════════════════════
# MOMENTUM (22 puan)
# ════════════════════════════════════════════════════════════

def score_momentum(analysis):
    score = 0
    reasons = []
    
    rsi = analysis.get('rsi')
    macd = analysis.get('macd')
    macd_signal = analysis.get('macd_signal')
    prev_macd = analysis.get('prev_macd')
    prev_macd_signal = analysis.get('prev_macd_signal')
    macd_hist = analysis.get('macd_hist')
    smi = analysis.get('smi')
    smi_signal = analysis.get('smi_signal')
    prev_smi = analysis.get('prev_smi')
    
    if rsi is not None:
        if 50 <= rsi <= 65:
            score += 8
            reasons.append({'icon': '⚡', 'title': 'RSI İDEAL', 'detail': f'RSI: {rsi:.1f}', 'meaning': 'Momentum var'})
        elif 45 <= rsi < 50:
            score += 6
            reasons.append({'icon': '⚡', 'title': 'RSI DENGE', 'detail': f'RSI: {rsi:.1f}', 'meaning': 'Denge'})
        elif 40 <= rsi < 45:
            score += 5
            reasons.append({'icon': '⚡', 'title': 'RSI TOPARLANIYOR', 'detail': f'RSI: {rsi:.1f}', 'meaning': 'Dip dönüşü'})
        elif 65 < rsi <= 72:
            score += 4
            reasons.append({'icon': '⚡', 'title': 'RSI GÜÇLÜ', 'detail': f'RSI: {rsi:.1f}', 'meaning': 'Momentum güçlü'})
        elif 35 <= rsi < 40:
            score += 3
    
    if all(v is not None for v in [macd, macd_signal]):
        if prev_macd is not None and prev_macd_signal is not None:
            if prev_macd <= prev_macd_signal and macd > macd_signal:
                score += 8
                reasons.append({'icon': '🚀', 'title': 'MACD KESİŞİMİ', 'detail': 'MACD yukarı kesti', 'meaning': 'YENİ momentum'})
            elif macd > macd_signal and macd > 0:
                score += 6
                reasons.append({'icon': '📈', 'title': 'MACD POZİTİF', 'detail': 'Yükselişte', 'meaning': 'Trend yukarı'})
            elif macd > macd_signal:
                score += 4
                reasons.append({'icon': '📈', 'title': 'MACD YÜKSELİŞ', 'detail': 'Signal üstünde', 'meaning': 'Pozitif'})
        else:
            if macd > macd_signal:
                score += 4
    
    if macd_hist is not None:
        prev_hist = analysis.get('prev_macd_hist')
        if prev_hist is not None and macd_hist > prev_hist and macd_hist > 0:
            score += 1
    
    if smi is not None and smi_signal is not None:
        if smi > smi_signal:
            if prev_smi is not None and prev_smi <= smi_signal:
                score += 6
                reasons.append({'icon': '📊', 'title': 'SMI KESİŞİMİ', 'detail': f'SMI: {smi:.1f}', 'meaning': 'Güçlü momentum'})
            elif -40 < smi < 40:
                score += 4
                reasons.append({'icon': '📊', 'title': 'SMI POZİTİF', 'detail': f'SMI: {smi:.1f}', 'meaning': 'Momentum pozitif'})
            elif 40 <= smi < 60:
                score += 3
        if smi < -40 and prev_smi is not None and smi > prev_smi:
            score += 4
            reasons.append({'icon': '🎯', 'title': 'SMI DİP DÖNÜŞÜ', 'detail': f'SMI: {smi:.1f}', 'meaning': 'Aşırı satımdan dönüyor'})
    
    return min(score, 22), reasons


# ════════════════════════════════════════════════════════════
# TREND (25 puan) - EMA50 vurgulu
# ════════════════════════════════════════════════════════════

def score_trend(analysis):
    score = 0
    reasons = []
    
    current = analysis.get('current_price')
    ema_9 = analysis.get('ema_9')
    ema_21 = analysis.get('ema_21')
    ema_50 = analysis.get('ema_50')
    prev_close = analysis.get('prev_close')
    supertrend_dir = analysis.get('supertrend_dir')
    adx = analysis.get('adx')
    plus_di = analysis.get('plus_di')
    minus_di = analysis.get('minus_di')
    
    if all(v is not None for v in [current, ema_9, ema_21, ema_50]):
        if current > ema_9 > ema_21 > ema_50:
            score += 10
            reasons.append({'icon': '🏆', 'title': 'MÜKEMMEL TREND', 'detail': 'Fiyat > EMA9 > EMA21 > EMA50', 'meaning': 'Tüm zaman dilimleri yukarı'})
        elif current > ema_9 and current > ema_21 and current > ema_50:
            score += 7
            reasons.append({'icon': '📈', 'title': 'GÜÇLÜ TREND', 'detail': 'Tüm EMA üstünde', 'meaning': 'Orta vade YUKARI'})
        elif current > ema_21 and current > ema_50:
            score += 6
            reasons.append({'icon': '📈', 'title': 'TREND POZİTİF', 'detail': 'EMA21 ve EMA50 üstünde', 'meaning': 'Orta vade yukarı'})
        elif current > ema_50:
            score += 4
            reasons.append({'icon': '📈', 'title': 'EMA50 ÜSTÜNDE', 'detail': f'Fiyat > EMA50 ({ema_50:.2f})', 'meaning': 'Orta vade sağlıklı'})
        elif current > ema_21 and current < ema_50:
            score += 1
            reasons.append({'icon': '⚠️', 'title': 'KARIŞIK TREND', 'detail': 'EMA21 üstü ama EMA50 altı', 'meaning': 'Kısa yukarı, orta zayıf'})
        elif current < ema_50:
            score -= 3
            reasons.append({'icon': '🔴', 'title': 'EMA50 ALTINDA', 'detail': f'Fiyat < EMA50 ({ema_50:.2f})', 'meaning': 'Orta vade AŞAĞI'})
    
    prev_ema_50 = analysis.get('prev_ema_50')
    if all(v is not None for v in [current, ema_50, prev_close, prev_ema_50]):
        if prev_close <= prev_ema_50 and current > ema_50:
            score += 5
            reasons.append({'icon': '🎯', 'title': 'EMA50 KIRILDI!', 'detail': 'EMA50 üstüne çıktı', 'meaning': 'Orta vade UPTREND başladı'})
        elif prev_close > prev_ema_50 and current < ema_50:
            score -= 5
            reasons.append({'icon': '🔴', 'title': 'EMA50 KAYBEDİLDİ', 'detail': 'EMA50 altına indi', 'meaning': 'Trend BOZULUYOR'})
    
    prev_ema_9 = analysis.get('prev_ema_9')
    prev_ema_21 = analysis.get('prev_ema_21')
    if all(v is not None for v in [ema_9, ema_21, prev_ema_9, prev_ema_21]):
        if prev_ema_9 <= prev_ema_21 and ema_9 > ema_21:
            score += 3
            reasons.append({'icon': '⭐', 'title': 'GOLDEN CROSS', 'detail': 'EMA9 > EMA21', 'meaning': 'Trend dönüşü'})
    
    if supertrend_dir == 1:
        score += 3
        reasons.append({'icon': '🟢', 'title': 'SUPERTREND YUKARI', 'detail': 'Yeşil', 'meaning': 'Trend yukarı'})
    
    if adx is not None:
        if adx > 30 and plus_di and minus_di and plus_di > minus_di:
            score += 4
            reasons.append({'icon': '💪', 'title': 'GÜÇLÜ TREND', 'detail': f'ADX: {adx:.1f}', 'meaning': 'Trend güçlü'})
        elif adx > 25:
            score += 3
        elif adx > 20:
            score += 2
        elif adx > 15:
            score += 1
    
    return min(score, 25), reasons


# ════════════════════════════════════════════════════════════
# WAVETREND (8 puan)
# ════════════════════════════════════════════════════════════

def score_wavetrend(analysis):
    score = 0
    reasons = []
    wt1 = analysis.get('wt1')
    wt2 = analysis.get('wt2')
    prev_wt1 = analysis.get('prev_wt1')
    prev_wt2 = analysis.get('prev_wt2')
    
    if wt1 is None or wt2 is None:
        return 0, []
    
    if all(v is not None for v in [prev_wt1, prev_wt2]):
        if prev_wt1 <= prev_wt2 and wt1 > wt2:
            if wt1 < -53:
                return 8, [{'icon': '🌊', 'title': 'WT DİP DÖNÜŞÜ!', 'detail': f'WT1: {wt1:.1f}', 'meaning': 'Mükemmel AL'}]
            else:
                return 6, [{'icon': '🌊', 'title': 'WT AL KESİŞİMİ', 'detail': f'WT1 > WT2', 'meaning': 'Yeni yükseliş'}]
    
    if wt1 > wt2:
        if wt1 < -40:
            score = 5
            reasons.append({'icon': '🌊', 'title': 'WT DİP BÖLGESİ', 'detail': f'WT1: {wt1:.1f}', 'meaning': 'Dipten dönüş'})
        elif wt1 < 30:
            score = 4
            reasons.append({'icon': '🌊', 'title': 'WT POZİTİF', 'detail': 'WT1 > WT2', 'meaning': 'Yükseliş'})
        elif wt1 < 50:
            score = 3
        elif wt1 > 60:
            reasons.append({'icon': '⚠️', 'title': 'WT AŞIRI ALIM', 'detail': f'WT1: {wt1:.1f}', 'meaning': 'Düzeltme gelebilir'})
    elif wt1 < -53:
        score = 2
    
    return min(score, 8), reasons


# ════════════════════════════════════════════════════════════
# ÇİFTLİ ONAY (5 puan)
# ════════════════════════════════════════════════════════════

def score_dual_confirmation(analysis):
    score = 0
    reasons = []
    wt1 = analysis.get('wt1')
    wt2 = analysis.get('wt2')
    smi = analysis.get('smi')
    smi_signal = analysis.get('smi_signal')
    
    if not all(v is not None for v in [wt1, wt2, smi, smi_signal]):
        return 0, []
    
    if wt1 > wt2 and smi > smi_signal:
        if wt1 < -30 and smi < -30:
            score = 5
            reasons.append({'icon': '🎯', 'title': 'ÇİFTLİ ONAY: DİP DÖNÜŞ', 'detail': 'WT + SMI dip dönüyor', 'meaning': 'Mükemmel onay!'})
        elif wt1 < 50 and -40 < smi < 40:
            score = 4
            reasons.append({'icon': '🎯', 'title': 'ÇİFTLİ ONAY: WT + SMI', 'detail': 'İkisi pozitif', 'meaning': 'Güçlü destek'})
        else:
            score = 2
    
    return score, reasons


# ════════════════════════════════════════════════════════════
# POZİSYON BONUSU (10 puan) - EMA50 dahil
# ════════════════════════════════════════════════════════════

def score_position_bonus(analysis):
    score = 0
    reasons = []
    
    current = analysis.get('current_price')
    ema_21 = analysis.get('ema_21')
    ema_50 = analysis.get('ema_50')
    macd = analysis.get('macd')
    macd_signal = analysis.get('macd_signal')
    rvol = analysis.get('rvol', 1)
    rsi = analysis.get('rsi', 50)
    supertrend_dir = analysis.get('supertrend_dir')
    
    conditions = 0
    if current and ema_21 and current > ema_21: conditions += 1
    if current and ema_50 and current > ema_50: conditions += 1
    if macd and macd_signal and macd > macd_signal: conditions += 1
    if rvol >= 1.3: conditions += 1
    if 45 <= rsi <= 70: conditions += 1
    if supertrend_dir == 1: conditions += 1
    
    if conditions >= 6:
        score = 10
        reasons.append({'icon': '✨', 'title': 'MÜKEMMEL POZİSYON', 'detail': f'{conditions}/6 pozitif', 'meaning': 'Çok güçlü yapı'})
    elif conditions == 5:
        score = 8
        reasons.append({'icon': '✨', 'title': 'ÇOK İYİ POZİSYON', 'detail': f'{conditions}/6 pozitif', 'meaning': 'Güçlü'})
    elif conditions == 4:
        score = 5
        reasons.append({'icon': '📈', 'title': 'İYİ POZİSYON', 'detail': f'{conditions}/6 pozitif', 'meaning': 'Sağlıklı'})
    elif conditions == 3:
        score = 3
    
    return score, reasons


# ════════════════════════════════════════════════════════════
# PİVOT POINT (15 puan)
# ════════════════════════════════════════════════════════════

def score_vwap_pivot(analysis):
    score = 0
    reasons = []
    current = analysis.get('current_price')
    pivot = analysis.get('pivot')
    r1 = analysis.get('r1')
    r2 = analysis.get('r2')
    r3 = analysis.get('r3')
    s1 = analysis.get('s1')
    
    if not (current and pivot):
        return 0, []
    
    if r2 and current > r2:
        if r3 and current < r3:
            score = 15
            reasons.append({'icon': '🚀', 'title': 'R2 KIRILDI!', 'detail': f'R2 ({r2:.2f}) kırıldı', 'meaning': 'Çok güçlü'})
        else:
            score = 13
            reasons.append({'icon': '🚀', 'title': 'R2 ÜSTÜNDE', 'detail': 'R2 geçildi', 'meaning': 'Güçlü yukarı'})
    elif r1 and r2 and current > r1 and current <= r2:
        score = 11
        reasons.append({'icon': '🎯', 'title': 'R1 KIRILDI', 'detail': f'R1 ({r1:.2f}) kırıldı', 'meaning': 'Yukarı momentum'})
    elif r1 and current > pivot and current <= r1:
        distance_to_r1 = ((r1 - current) / current) * 100
        if distance_to_r1 < 1:
            score = 10
            reasons.append({'icon': '🎯', 'title': 'R1 YAKININDA', 'detail': 'R1 test ediliyor', 'meaning': 'Kırılım yakın'})
        else:
            score = 8
            reasons.append({'icon': '📈', 'title': 'PİVOT ÜSTÜ', 'detail': 'Pivot üstünde', 'meaning': 'Alıcılar kontrolde'})
    elif pivot and abs(current - pivot) / pivot < 0.005:
        score = 6
        reasons.append({'icon': '🎯', 'title': 'PİVOT TESTİ', 'detail': 'Kritik nokta', 'meaning': 'Yön belirleniyor'})
    elif s1 and pivot and current > s1 and current < pivot:
        score = 4
    
    return min(score, 15), reasons


# ════════════════════════════════════════════════════════════
# KIRILIM & MUM (5 puan)
# ════════════════════════════════════════════════════════════

def score_breakout_candle(analysis):
    score = 0
    reasons = []
    breakouts = analysis.get('breakouts', [])
    candle_patterns = analysis.get('candle_patterns', [])
    
    up_breakouts = [b for b in breakouts if b['type'] == 'UP']
    if up_breakouts:
        max_period = max(b['period'] for b in up_breakouts)
        if max_period >= 50:
            score += 3
            reasons.append({'icon': '🚀', 'title': '50 GÜNLÜK ZİRVE', 'detail': f'{max_period} günlük', 'meaning': 'Çok güçlü kırılım'})
        elif max_period >= 20:
            score += 2
            reasons.append({'icon': '🚀', 'title': '20 GÜNLÜK ZİRVE', 'detail': f'{max_period} günlük', 'meaning': 'Güçlü kırılım'})
        elif max_period >= 10:
            score += 1
    
    bullish_patterns = [p for p in candle_patterns if p.get('bullish')]
    if bullish_patterns:
        strongest = bullish_patterns[0]
        if strongest['key'] in ['three_white_soldiers', 'bullish_engulfing', 'morning_star']:
            score += 2
            reasons.append({'icon': strongest['icon'], 'title': f"FORMASYON: {strongest['name'].upper()}", 'detail': strongest['meaning'], 'meaning': 'Güçlü dönüş'})
        else:
            score += 1
    
    return min(score, 5), reasons


# ════════════════════════════════════════════════════════════
# LİKİDİTE (5 puan)
# ════════════════════════════════════════════════════════════

def score_liquidity(analysis):
    score = 0
    reasons = []
    rvol = analysis.get('rvol')
    current = analysis.get('current_price')
    volume = analysis.get('volume')
    
    if rvol and rvol >= 0.8: score += 2
    if current and volume:
        volume_tl = current * volume
        if volume_tl > 10_000_000:
            score += 3
            reasons.append({'icon': '✅', 'title': 'YÜKSEK LİKİDİTE', 'detail': f'{volume_tl/1_000_000:.1f}M TL', 'meaning': 'Rahat al-sat'})
        elif volume_tl > 5_000_000:
            score += 2
    
    return min(score, 5), reasons


# ════════════════════════════════════════════════════════════
# TOPLAM PUAN - İNTRADAY RANGE EKLENDİ!
# ════════════════════════════════════════════════════════════

def calculate_total_score(analysis):
    """
    TAM SKOR SİSTEMİ:
    Temel + Bonuslar + Intraday Range + Akıllı Tavan
    """
    vol_s, vol_r = score_volume(analysis)
    mom_s, mom_r = score_momentum(analysis)
    tre_s, tre_r = score_trend(analysis)
    wt_s, wt_r = score_wavetrend(analysis)
    vwp_s, vwp_r = score_vwap_pivot(analysis)
    brk_s, brk_r = score_breakout_candle(analysis)
    liq_s, liq_r = score_liquidity(analysis)
    dual_s, dual_r = score_dual_confirmation(analysis)
    pos_s, pos_r = score_position_bonus(analysis)
    vol_trend_s, vol_trend_r = score_volume_trend(analysis)
    trend_health_s, trend_health_r = score_trend_health(analysis)
    
    # YENİ: İntraday Range (VESBE gibi hisseler için)
    intraday_s, intraday_r = score_intraday_range(analysis)
    
    total = (vol_s + mom_s + tre_s + wt_s + vwp_s + brk_s + 
             liq_s + dual_s + pos_s + vol_trend_s + trend_health_s +
             intraday_s)  # YENİ EKLENDİ!
    
    all_reasons = (vol_r + mom_r + tre_r + wt_r + vwp_r + brk_r + 
                   liq_r + dual_r + pos_r + vol_trend_r + trend_health_r +
                   intraday_r)  # YENİ EKLENDİ!
    
    # AKILLI TAVAN/YÜKSELİŞ BONUSU
    current_price = analysis.get('current_price')
    prev_close = analysis.get('prev_close')
    rvol = analysis.get('rvol', 1.0)
    
    if current_price and prev_close and prev_close > 0:
        daily_change = ((current_price - prev_close) / prev_close) * 100
        
        bonus = 0
        bonus_text = None
        meaning = None
        
        # ZATEN TAVAN - ATLA!
        if daily_change >= 9.5:
            bonus = 0
        
        # TAVAN'A ÇOK YAKIN - RİSKLİ
        elif daily_change >= 8:
            if rvol >= 2:
                bonus = 8
                bonus_text = f'⚠️ TAVAN YAKIN +%{daily_change:.1f}'
                meaning = 'Tavana çok yakın - RİSKLİ'
            elif rvol >= 1.5:
                bonus = 5
                bonus_text = f'⚠️ TAVAN YAKIN +%{daily_change:.1f}'
                meaning = 'Tavana yakın, dikkatli'
            elif rvol >= 1.0:
                bonus = 3
        
        # GERÇEK TAVAN ADAYI
        elif daily_change >= 5:
            if rvol >= 2:
                bonus = 18
                bonus_text = f'🚀 TAVAN ADAYI! +%{daily_change:.1f}'
                meaning = 'Tavan olabilir - ideal giriş'
            elif rvol >= 1.5:
                bonus = 15
                bonus_text = f'🚀 GÜÇLÜ TAVAN ADAYI +%{daily_change:.1f}'
                meaning = 'Tavan adayı'
            elif rvol >= 1.0:
                bonus = 10
                bonus_text = f'🚀 GÜNLÜK +%{daily_change:.1f}'
                meaning = 'Güçlü yükseliş'
        
        # GÜÇLÜ GÜN
        elif daily_change >= 3:
            if rvol >= 1.5:
                bonus = 8
                bonus_text = f'📈 GÜÇLÜ GÜN +%{daily_change:.1f}'
                meaning = 'Sağlıklı yükseliş'
            elif rvol >= 1.0:
                bonus = 5
                bonus_text = f'📈 POZİTİF GÜN +%{daily_change:.1f}'
                meaning = 'Yukarı yönlü'
        
        # HAFİF YÜKSELİŞ
        elif daily_change >= 1.5:
            if rvol >= 1.5:
                bonus = 4
                bonus_text = f'📊 POZİTİF +%{daily_change:.1f}'
                meaning = 'Hafif yükseliş'
            elif rvol >= 1.0:
                bonus = 2
        
        if bonus > 0:
            total += bonus
            if bonus_text:
                all_reasons.append({
                    'icon': '🚀' if daily_change >= 5 else '📈' if daily_change >= 3 else '⚠️',
                    'title': bonus_text,
                    'detail': f'Önceki: {prev_close:.2f} → Şu an: {current_price:.2f}',
                    'meaning': meaning
                })
    
    total = max(0, min(total, 100))
    
    return {
        'total': total,
        'breakdown': {
            'volume': {'score': vol_s, 'max': 25},
            'momentum': {'score': mom_s, 'max': 22},
            'trend': {'score': tre_s, 'max': 25},
            'wavetrend': {'score': wt_s, 'max': 8},
            'vwap_pivot': {'score': vwp_s, 'max': 15},
            'breakout_candle': {'score': brk_s, 'max': 5},
            'liquidity': {'score': liq_s, 'max': 5},
        },
        'reasons': all_reasons
    }


# ════════════════════════════════════════════════════════════
# HEDEF VE STOP
# ════════════════════════════════════════════════════════════

def calculate_targets(current_price, atr, analysis):
    if not atr or atr <= 0: atr_pct = 1.0
    else:
        atr_pct = (atr / current_price) * 100
        atr_pct = max(0.5, min(atr_pct, 4))
    
    t1 = round(current_price * (1 + atr_pct * 2.0 / 100), 2)
    t2 = round(current_price * (1 + atr_pct * 3.5 / 100), 2)
    t3 = round(current_price * (1 + atr_pct * 5.5 / 100), 2)
    sl = round(current_price * (1 - atr_pct * 1.5 / 100), 2)
    
    r2 = analysis.get('r2')
    r3 = analysis.get('r3')
    if r2 and r2 > current_price and r2 > t2: t2 = round(r2, 2)
    if r3 and r3 > current_price and r3 > t3: t3 = round(r3, 2)
    if t2 <= t1: t2 = round(t1 * 1.025, 2)
    if t3 <= t2: t3 = round(t2 * 1.030, 2)
    
    t1p = round(((t1 - current_price) / current_price) * 100, 2)
    t2p = round(((t2 - current_price) / current_price) * 100, 2)
    t3p = round(((t3 - current_price) / current_price) * 100, 2)
    sp = round(atr_pct * 1.5, 2)
    
    risk = current_price - sl
    rr = round((t2 - current_price) / risk, 2) if risk > 0 else 0
    
    return {'entry': current_price, 'target_1': t1, 'target_1_pct': t1p, 'target_2': t2, 'target_2_pct': t2p,
            'target_3': t3, 'target_3_pct': t3p, 'stop_loss': sl, 'stop_pct': sp, 'risk_reward': rr,
            'atr_value': round(atr, 4) if atr else None}


# ════════════════════════════════════════════════════════════
# UYARILAR
# ════════════════════════════════════════════════════════════

def generate_warnings(analysis):
    warnings = []
    suggestions = []
    rsi = analysis.get('rsi')
    rvol = analysis.get('rvol')
    current_price = analysis.get('current_price')
    prev_close = analysis.get('prev_close')
    
    if current_price and prev_close and prev_close > 0:
        daily_change = ((current_price - prev_close) / prev_close) * 100
        if daily_change >= 9.5:
            warnings.append({'level': 'EXTREME', 'icon': '🔴🔴', 'title': 'ZATEN TAVAN!', 'detail': f'+%{daily_change:.2f}', 'action': 'GİRMEYİN!'})
        elif daily_change >= 8:
            warnings.append({'level': 'HIGH', 'icon': '⚠️', 'title': 'TAVANA YAKIN', 'detail': f'+%{daily_change:.2f}', 'action': 'Riskli - hızlı çık'})
    
    # Intraday range uyarısı
    today_high = analysis.get('high')
    today_low = analysis.get('low')
    if today_high and today_low and today_low > 0:
        intraday_range = ((today_high - today_low) / today_low) * 100
        if intraday_range >= 8:
            distance_to_high = ((today_high - current_price) / today_high) * 100 if today_high > 0 else 100
            if distance_to_high > 3:
                warnings.append({'level': 'MEDIUM', 'icon': '⚠️', 'title': 'GÜN İÇİ GERİ ÇEKİLME', 
                                'detail': f'Zirve: {today_high:.2f}, Şuan: {current_price:.2f}', 
                                'action': 'Zirveden düştü, dikkatli ol'})
    
    if rsi:
        if rsi > 80:
            warnings.append({'level': 'EXTREME', 'icon': '🔴🔴', 'title': 'RSI ÇOK YÜKSEK', 'detail': f'RSI: {rsi:.1f}', 'action': 'KAR AL!'})
        elif rsi > 75:
            warnings.append({'level': 'HIGH', 'icon': '🔴', 'title': 'RSI AŞIRI ALIM', 'detail': f'RSI: {rsi:.1f}', 'action': 'Kısmi kar al'})
    
    if rvol is not None and rvol < 0.7:
        warnings.append({'level': 'LOW', 'icon': '⚠️', 'title': 'HACİM DÜŞÜK', 'detail': f'RVOL: {rvol:.2f}x', 'action': 'Dikkatli ol'})
    
    return warnings, suggestions


# ════════════════════════════════════════════════════════════
# SİNYAL GÜCÜ
# ════════════════════════════════════════════════════════════

def determine_strength(score):
    if score >= 85: return {'type': 'AL', 'strength': 'COK_GUCLU', 'label': 'ÇOK GÜÇLÜ AL', 'emoji': '🔥🔥🔥', 'color': '🟢', 'action': 'AL - Güçlü pozisyon', 'confidence': 'Yüksek güvenilirlik', 'risk_level': 'Düşük'}
    elif score >= 75: return {'type': 'AL', 'strength': 'GUCLU', 'label': 'GÜÇLÜ AL', 'emoji': '🔥🔥', 'color': '🟢', 'action': 'AL - Kademeli giriş', 'confidence': 'İyi güvenilirlik', 'risk_level': 'Orta-Düşük'}
    elif score >= 65: return {'type': 'AL', 'strength': 'NORMAL', 'label': 'AL', 'emoji': '🔥', 'color': '🟢', 'action': 'AL - Küçük pozisyon', 'confidence': 'Orta güvenilirlik', 'risk_level': 'Orta'}
    elif score >= 50: return {'type': 'BEKLE', 'strength': 'ZAYIF', 'label': 'BEKLE', 'emoji': '🟡', 'color': '🟡', 'action': 'BEKLE', 'confidence': 'Belirsiz', 'risk_level': 'Yüksek'}
    else: return {'type': 'YOK', 'strength': 'YOK', 'label': 'SİNYAL YOK', 'emoji': '⚪', 'color': '⚪', 'action': 'GİRMİYORUM', 'confidence': 'Sinyal yok', 'risk_level': '-'}


def suggest_holding_period(score, indicators):
    if score >= 85: return {'duration': '1-2 gün', 'strategy': 'HIZLI SWING', 'reason': 'Çok güçlü momentum', 'max_days': 3}
    elif score >= 75: return {'duration': '2-4 gün', 'strategy': 'STANDART SWING', 'reason': 'Sağlıklı trend', 'max_days': 5}
    elif score >= 65: return {'duration': '3-7 gün', 'strategy': 'UZUN SWING', 'reason': 'Sabırlı olmalı', 'max_days': 10}
    else: return {'duration': '-', 'strategy': 'BEKLEME', 'reason': 'Güçlenmesini bekle', 'max_days': 0}


# ════════════════════════════════════════════════════════════
# SİNYAL ÜRETME
# ════════════════════════════════════════════════════════════

def generate_signal(symbol, analysis, history_df=None):
    if not analysis: return None
    current_price = analysis.get('current_price')
    if not current_price: return None
    
    score_data = calculate_total_score(analysis)
    total_score = score_data['total']
    signal_info = determine_strength(total_score)
    
    atr = analysis.get('atr')
    targets = calculate_targets(current_price, atr, analysis)
    warnings, suggestions = generate_warnings(analysis)
    
    indicators = {
        'rsi': analysis.get('rsi'), 'macd': analysis.get('macd'),
        'rvol': analysis.get('rvol'), 'adx': analysis.get('adx'),
        'supertrend_dir': analysis.get('supertrend_dir'), 'atr': analysis.get('atr'),
        'wt1': analysis.get('wt1'), 'wt2': analysis.get('wt2'),
        'smi': analysis.get('smi'), 'smi_signal': analysis.get('smi_signal'),
    }
    
    holding = suggest_holding_period(total_score, indicators)
    
    filled = int(total_score / 5)
    empty = 20 - filled
    score_bar = '█' * filled + '░' * empty
    
    if total_score >= 85: stars = '🟢🟢🟢🟢🟢'
    elif total_score >= 75: stars = '🟢🟢🟢🟢⚪'
    elif total_score >= 65: stars = '🟢🟢🟢⚪⚪'
    elif total_score >= 50: stars = '🟡🟡⚪⚪⚪'
    else: stars = '⚪⚪⚪⚪⚪'
    
    key_levels = {
        'pivot': analysis.get('pivot'), 'r1': analysis.get('r1'),
        'r2': analysis.get('r2'), 'r3': analysis.get('r3'),
        's1': analysis.get('s1'), 'prev_day_high': analysis.get('prev_day_high'),
        'prev_day_low': analysis.get('prev_day_low'), 'ema_9': analysis.get('ema_9'),
        'ema_21': analysis.get('ema_21'), 'ema_50': analysis.get('ema_50'),
    }
    
    return {
        'symbol': symbol.replace('.IS', ''), 'full_symbol': symbol,
        'timestamp': tr_now().isoformat(), 'current_price': current_price,
        'score': total_score, 'score_bar': score_bar, 'stars': stars,
        'signal_type': signal_info['type'], 'strength': signal_info['strength'],
        'label': signal_info['label'], 'emoji': signal_info['emoji'],
        'action': signal_info['action'], 'confidence': signal_info['confidence'],
        'risk_level': signal_info['risk_level'], 'holding': holding,
        'targets': targets, 'reasons': score_data['reasons'],
        'breakdown': score_data['breakdown'], 'warnings': warnings,
        'suggestions': suggestions, 'key_levels': key_levels,
        'candle_patterns': analysis.get('candle_patterns', []),
        'breakouts': analysis.get('breakouts', []),
        'momentum_status': analysis.get('momentum_status', {}),
        'indicators': indicators,
    }


def format_signal_message(signal):
    if not signal: return "Sinyal yok"
    return f"{signal['emoji']} {signal['label']} - {signal['symbol']} ({signal['score']}/100)"


if __name__ == "__main__":
    print("✅ Signal Engine - TAM PAKET + Intraday Range + Akıllı Tavan")
