"""
Profesyonel Sinyal Motoru
AKILLI HACİM + WaveTrend + SMI eklendi
Stochastic kaldırıldı
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta


TR_TIMEZONE = timezone(timedelta(hours=3))

def tr_now():
    return datetime.now(TR_TIMEZONE)


# ════════════════════════════════════════════════════════════
# AKILLI HACİM SKORU (25 puan) - YENİ!
# ════════════════════════════════════════════════════════════

def score_volume(analysis):
    """
    AKILLI Hacim Analizi:
    - RVOL + Yön + Hacim Trendi
    - Düşüşte hacim = SATIŞ BASKISI (negatif)
    - Yükselişte hacim = ALIŞ DESTEĞİ (pozitif)
    """
    score = 0
    reasons = []
    
    rvol = analysis.get('rvol', 1)
    current = analysis.get('current_price')
    prev_close = analysis.get('prev_close')
    today_volume = analysis.get('volume', 0)
    avg_volume_5 = analysis.get('avg_volume_5', 0)
    
    if not (current and prev_close and prev_close > 0):
        return 0, []
    
    # YÖN tespiti
    is_up = current > prev_close
    daily_change = ((current - prev_close) / prev_close) * 100
    
    # Hacim trendi (son 5 gün)
    volume_trend_up = today_volume > avg_volume_5 if avg_volume_5 > 0 else False
    
    # ═══════════════════════════════════════
    # AKILLI PUANLAMA
    # ═══════════════════════════════════════
    
    if rvol >= 5 and is_up and volume_trend_up:
        # 🚀 PATLAMA + YÜKSELİŞ + HACİM ARTIYOR
        score = 25
        reasons.append({
            'icon': '🚀', 'title': 'GÜÇLÜ ALIŞ BASKISI',
            'detail': f'RVOL: {rvol:.1f}x + Yükseliş (%{daily_change:.2f}) + Hacim trendi',
            'meaning': 'Kurumsal alım - çok güçlü sinyal'
        })
    
    elif rvol >= 5 and not is_up:
        # 🔴 PATLAMA + DÜŞÜŞ = SATIŞ BASKISI!
        score = 0
        reasons.append({
            'icon': '⚠️', 'title': 'SATIŞ BASKISI!',
            'detail': f'RVOL: {rvol:.1f}x ama fiyat düşüyor (%{daily_change:.2f})',
            'meaning': 'Yüksek hacimle satılıyor - UZAK DUR!'
        })
    
    elif rvol >= 3 and is_up and volume_trend_up:
        # 🟢 YÜKSEK HACİM + YÜKSELİŞ
        score = 20
        reasons.append({
            'icon': '💥', 'title': 'YÜKSEK HACİM + YÜKSELİŞ',
            'detail': f'RVOL: {rvol:.1f}x',
            'meaning': 'Güçlü alış desteği'
        })
    
    elif rvol >= 3 and not is_up:
        # 🔴 YÜKSEK HACİM + DÜŞÜŞ
        score = 0
        reasons.append({
            'icon': '⚠️', 'title': 'HACİM VAR AMA DÜŞÜYOR',
            'detail': f'RVOL: {rvol:.1f}x, %{daily_change:.2f}',
            'meaning': 'Satış var, alım yok'
        })
    
    elif rvol >= 2 and is_up:
        # 🟢 ORTA HACİM + YÜKSELİŞ
        score = 15
        reasons.append({
            'icon': '📊', 'title': 'HACİM ARTIŞI + YÜKSELİŞ',
            'detail': f'RVOL: {rvol:.1f}x',
            'meaning': 'Normalin üstünde alım'
        })
    
    elif rvol >= 1.5 and is_up and volume_trend_up:
        # 🟢 NORMAL ÜSTÜ HACİM
        score = 10
        reasons.append({
            'icon': '📊', 'title': 'HACİM NORMAL ÜSTÜ',
            'detail': f'RVOL: {rvol:.1f}x',
            'meaning': 'Yeterli alış'
        })
    
    elif rvol >= 1.5 and is_up:
        # Hafif pozitif
        score = 6
    
    elif rvol < 0.5:
        # ❌ HACİM DÜŞÜK
        score = 0
        reasons.append({
            'icon': '⚠️', 'title': 'HACİM DÜŞÜK',
            'detail': f'RVOL: {rvol:.1f}x',
            'meaning': 'İlgi yok, hareket sahte olabilir'
        })
    
    return min(score, 25), reasons


# ════════════════════════════════════════════════════════════
# MOMENTUM (20 puan) - RSI + MACD + SMI
# ════════════════════════════════════════════════════════════

def score_momentum(analysis):
    """Momentum: RSI + MACD + SMI"""
    score = 0
    reasons = []
    
    rsi = analysis.get('rsi')
    macd = analysis.get('macd')
    macd_signal = analysis.get('macd_signal')
    prev_macd = analysis.get('prev_macd')
    prev_macd_signal = analysis.get('prev_macd_signal')
    macd_hist = analysis.get('macd_hist')
    
    # SMI (Stochastic yerine)
    smi = analysis.get('smi')
    smi_signal = analysis.get('smi_signal')
    prev_smi = analysis.get('prev_smi')
    prev_smi_signal = analysis.get('prev_smi_signal')
    
    # RSI (6 puan - 8'den azaltıldı)
    if rsi is not None:
        if 50 <= rsi <= 65:
            score += 6
            reasons.append({
                'icon': '⚡', 'title': 'RSI İDEAL',
                'detail': f'RSI: {rsi:.1f} (50-65 sağlıklı)',
                'meaning': 'Momentum var, aşırı alım değil'
            })
        elif 40 <= rsi < 50:
            score += 5
            reasons.append({
                'icon': '⚡', 'title': 'RSI TOPARLANIYOR',
                'detail': f'RSI: {rsi:.1f}',
                'meaning': 'Dip dönüşü başlıyor'
            })
        elif 65 < rsi <= 72:
            score += 3
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
                'detail': f'MACD pozitif',
                'meaning': 'Trend yukarı'
            })
        elif macd > macd_signal:
            score += 3
    
    # MACD Histogram artıyor mu?
    if macd_hist is not None:
        prev_hist = analysis.get('prev_macd_hist')
        if prev_hist is not None and macd_hist > prev_hist and macd_hist > 0:
            score += 1
    
    # SMI (5 puan - Stochastic yerine)
    if all(v is not None for v in [smi, smi_signal, prev_smi, prev_smi_signal]):
        # SMI kesişimi (en güçlü)
        if prev_smi <= prev_smi_signal and smi > smi_signal:
            score += 5
            reasons.append({
                'icon': '📊', 'title': 'SMI KESİŞİMİ',
                'detail': f'SMI ({smi:.1f}) sinyali ({smi_signal:.1f}) yukarı kesti',
                'meaning': 'Güçlü momentum başladı'
            })
        # SMI pozitif ve yukarı
        elif smi > smi_signal and -40 < smi < 40:
            score += 3
            reasons.append({
                'icon': '📊', 'title': 'SMI YUKARI',
                'detail': f'SMI: {smi:.1f} > Signal: {smi_signal:.1f}',
                'meaning': 'Momentum pozitif'
            })
        # Aşırı satım bölgesinden çıkış (AL fırsatı)
        elif smi < -40 and smi > prev_smi:
            score += 4
            reasons.append({
                'icon': '🎯', 'title': 'SMI DİPTEN DÖNÜYOR',
                'detail': f'SMI: {smi:.1f} (aşırı satım çıkışı)',
                'meaning': 'Dip yapıyor, yükseliş olabilir'
            })
    
    return min(score, 20), reasons


# ════════════════════════════════════════════════════════════
# TREND (18 puan) - 20'den azaltıldı
# ════════════════════════════════════════════════════════════

def score_trend(analysis):
    """Trend: EMA + Supertrend + ADX"""
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
    
    # EMA Sıralama (7 puan)
    if all(v is not None for v in [current, ema_9, ema_21, ema_50]):
        if current > ema_9 > ema_21 > ema_50:
            score += 7
            reasons.append({
                'icon': '🏆', 'title': 'MÜKEMMEL TREND',
                'detail': 'Fiyat > EMA9 > EMA21 > EMA50',
                'meaning': 'Tüm EMA\'lar düzgün sıralı'
            })
        elif current > ema_9 > ema_21:
            score += 5
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
            score += 3
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
    
    # ADX (4 puan)
    if adx is not None:
        if adx > 30 and plus_di and minus_di and plus_di > minus_di:
            score += 4
            reasons.append({
                'icon': '💪', 'title': 'GÜÇLÜ TREND',
                'detail': f'ADX: {adx:.1f}',
                'meaning': 'Trend çok güçlü'
            })
        elif adx > 25:
            score += 2
    
    return min(score, 18), reasons


# ════════════════════════════════════════════════════════════
# YENİ: WAVETREND SKORU (10 puan)
# ════════════════════════════════════════════════════════════

def score_wavetrend(analysis):
    """
    WaveTrend Skoru
    
    En değerli: WT1, WT2'yi yukarı keser (AL sinyali)
    Bonus: Aşırı satım bölgesinden çıkış (dip yapıyor)
    """
    score = 0
    reasons = []
    
    wt1 = analysis.get('wt1')
    wt2 = analysis.get('wt2')
    prev_wt1 = analysis.get('prev_wt1')
    prev_wt2 = analysis.get('prev_wt2')
    
    if not all(v is not None for v in [wt1, wt2, prev_wt1, prev_wt2]):
        return 0, []
    
    # WT1, WT2'yi yukarı kesti mi? (EN GÜÇLÜ SİNYAL)
    if prev_wt1 <= prev_wt2 and wt1 > wt2:
        # Aşırı satım bölgesinde kesişim (ÇOK GÜÇLÜ)
        if wt1 < -53:
            score = 10
            reasons.append({
                'icon': '🌊', 'title': 'WAVETREND DİP DÖNÜŞÜ!',
                'detail': f'WT1: {wt1:.1f} (aşırı satım bölgesi)',
                'meaning': 'Dipten güçlü dönüş - mükemmel AL fırsatı'
            })
        # Normal kesişim
        else:
            score = 7
            reasons.append({
                'icon': '🌊', 'title': 'WAVETREND AL SİNYALİ',
                'detail': f'WT1 ({wt1:.1f}) WT2\'yi yukarı kesti',
                'meaning': 'Yeni yükseliş trendi başlıyor'
            })
    
    # Zaten kesişmiş ve devam ediyor
    elif wt1 > wt2 and wt1 < 50:
        score = 5
        reasons.append({
            'icon': '🌊', 'title': 'WAVETREND POZİTİF',
            'detail': f'WT1: {wt1:.1f} > WT2: {wt2:.1f}',
            'meaning': 'Yükseliş trendi devam ediyor'
        })
    
    # Aşırı alım uyarısı
    elif wt1 > 60:
        reasons.append({
            'icon': '⚠️', 'title': 'WAVETREND AŞIRI ALIM',
            'detail': f'WT1: {wt1:.1f}',
            'meaning': 'Düzeltme gelebilir - dikkatli ol'
        })
    
    return min(score, 10), reasons


# ════════════════════════════════════════════════════════════
# WAVETREND + SMI ÇİFTLİ ONAY BONUSU
# ════════════════════════════════════════════════════════════

def score_dual_confirmation(analysis):
    """
    WaveTrend + SMI aynı anda AL sinyali verirse BONUS
    Bu çok güçlü bir gösterge!
    """
    score = 0
    reasons = []
    
    wt1 = analysis.get('wt1')
    wt2 = analysis.get('wt2')
    prev_wt1 = analysis.get('prev_wt1')
    prev_wt2 = analysis.get('prev_wt2')
    
    smi = analysis.get('smi')
    smi_signal = analysis.get('smi_signal')
    prev_smi = analysis.get('prev_smi')
    prev_smi_signal = analysis.get('prev_smi_signal')
    
    if not all(v is not None for v in [wt1, wt2, prev_wt1, prev_wt2, smi, smi_signal, prev_smi, prev_smi_signal]):
        return 0, []
    
    # WaveTrend AL kesişimi
    wt_signal = prev_wt1 <= prev_wt2 and wt1 > wt2
    
    # SMI AL kesişimi
    smi_signal_cross = prev_smi <= prev_smi_signal and smi > smi_signal
    
    # İKİSİ AYNI ANDA!
    if wt_signal and smi_signal_cross:
        score = 5  # BONUS PUAN
        reasons.append({
            'icon': '🎯', 'title': 'ÇİFTLİ ONAY: WT + SMI',
            'detail': 'WaveTrend ve SMI aynı anda AL sinyali!',
            'meaning': 'Çok güçlü teknik onay - mükemmel giriş'
        })
    
    return score, reasons


# ════════════════════════════════════════════════════════════
# PİVOT POINT (12 puan) - 15'ten azaltıldı
# ════════════════════════════════════════════════════════════

def score_vwap_pivot(analysis):
    """Pivot Point skoru (12 puan)"""
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
            score = 12
            reasons.append({
                'icon': '🚀', 'title': 'R2 KIRILDI - ÇOK GÜÇLÜ!',
                'detail': f'R2 ({r2:.2f}) kırıldı, R3 ({r3:.2f}) hedefte',
                'meaning': 'Çok güçlü momentum'
            })
        else:
            score = 10
            reasons.append({
                'icon': '🚀', 'title': 'R2 ÜSTÜNDE',
                'detail': f'R2 ({r2:.2f}) geçildi',
                'meaning': 'Güçlü yukarı hareket'
            })
    
    elif r1 and r2 and current > r1 and current <= r2:
        score = 9
        reasons.append({
            'icon': '🎯', 'title': 'R1 KIRILDI',
            'detail': f'R1 ({r1:.2f}) kırıldı',
            'meaning': 'Yukarı momentum başladı'
        })
    
    elif r1 and current > pivot and current <= r1:
        distance_to_r1 = ((r1 - current) / current) * 100
        
        if distance_to_r1 < 1:
            score = 8
            reasons.append({
                'icon': '🎯', 'title': 'R1 YAKININDA',
                'detail': f'R1 test ediliyor',
                'meaning': 'Kırılım çok yakın'
            })
        else:
            score = 7
            reasons.append({
                'icon': '📈', 'title': 'PİVOT ÜSTÜ',
                'detail': f'Pivot üstünde',
                'meaning': 'Alıcılar kontrolde'
            })
    
    elif pivot and abs(current - pivot) / pivot < 0.005:
        score = 5
        reasons.append({
            'icon': '🎯', 'title': 'PİVOT TESTİ',
            'detail': 'Kritik nokta',
            'meaning': 'Yön belirleniyor'
        })
    
    elif s1 and pivot and current > s1 and current < pivot:
        score = 3
    
    return min(score, 12), reasons


# ════════════════════════════════════════════════════════════
# KIRILIM & MUM (10 puan) - 15'ten azaltıldı
# ════════════════════════════════════════════════════════════

def score_breakout_candle(analysis):
    """Kırılım + Mum"""
    score = 0
    reasons = []
    
    breakouts = analysis.get('breakouts', [])
    candle_patterns = analysis.get('candle_patterns', [])
    current = analysis.get('current_price')
    bb_upper = analysis.get('bb_upper')
    
    # Kırılımlar (6 puan)
    up_breakouts = [b for b in breakouts if b['type'] == 'UP']
    if up_breakouts:
        max_period = max(b['period'] for b in up_breakouts)
        if max_period >= 50:
            score += 6
            reasons.append({
                'icon': '🚀', 'title': '50 GÜNLÜK ZİRVE KIRILDI',
                'detail': f'{max_period} günlük zirve',
                'meaning': 'Çok güçlü kırılım'
            })
        elif max_period >= 20:
            score += 4
            reasons.append({
                'icon': '🚀', 'title': '20 GÜNLÜK ZİRVE',
                'detail': f'{max_period} günlük kırılım',
                'meaning': 'Güçlü kırılım'
            })
        elif max_period >= 10:
            score += 2
    
    # BB Üst Bant (2 puan)
    if current and bb_upper:
        if current >= bb_upper * 0.99:
            score += 2
            reasons.append({
                'icon': '💥', 'title': 'BB ÜST BANT',
                'detail': 'Volatilite kırılımı',
                'meaning': 'Güçlü hareket'
            })
    
    # Mum (2 puan)
    bullish_patterns = [p for p in candle_patterns if p.get('bullish')]
    if bullish_patterns:
        strongest = bullish_patterns[0]
        if strongest['key'] in ['three_white_soldiers', 'bullish_engulfing', 'morning_star']:
            score += 2
            reasons.append({
                'icon': strongest['icon'], 
                'title': f"FORMASYON: {strongest['name'].upper()}",
                'detail': strongest['meaning'],
                'meaning': 'Güçlü dönüş sinyali'
            })
        else:
            score += 1
    
    return min(score, 10), reasons


# ════════════════════════════════════════════════════════════
# LİKİDİTE (5 puan)
# ════════════════════════════════════════════════════════════

def score_liquidity(analysis):
    """Likidite"""
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
                'detail': f'{volume_tl/1_000_000:.1f}M TL',
                'meaning': 'Rahatça alıp satabilirsin'
            })
        elif volume_tl > 5_000_000:
            score += 2
    
    return min(score, 5), reasons


# ════════════════════════════════════════════════════════════
# TOPLAM PUAN
# ════════════════════════════════════════════════════════════

def calculate_total_score(analysis):
    """
    YENİ SKOR SİSTEMİ (100 puan):
    - Akıllı Hacim: 25
    - Momentum: 20
    - Trend: 18
    - WaveTrend: 10 (YENİ)
    - Pivot: 12
    - Kırılım: 10
    - Likidite: 5
    - BONUS: WT+SMI çiftli onay: +5
    """
    vol_s, vol_r = score_volume(analysis)
    mom_s, mom_r = score_momentum(analysis)
    tre_s, tre_r = score_trend(analysis)
    wt_s, wt_r = score_wavetrend(analysis)
    vwp_s, vwp_r = score_vwap_pivot(analysis)
    brk_s, brk_r = score_breakout_candle(analysis)
    liq_s, liq_r = score_liquidity(analysis)
    
    # Çiftli onay bonusu
    dual_s, dual_r = score_dual_confirmation(analysis)
    
    total = vol_s + mom_s + tre_s + wt_s + vwp_s + brk_s + liq_s + dual_s
    all_reasons = vol_r + mom_r + tre_r + wt_r + vwp_r + brk_r + liq_r + dual_r
    
    # Günlük yükseliş bonusu (mevcut)
    current_price = analysis.get('current_price')
    prev_close = analysis.get('prev_close')
    rvol = analysis.get('rvol', 1.0)
    
    if current_price and prev_close and prev_close > 0:
        daily_change = ((current_price - prev_close) / prev_close) * 100
        
        bonus = 0
        bonus_text = None
        meaning = None
        
        if daily_change >= 8:
            if rvol >= 2:
                bonus = 18
                bonus_text = f'🚀 TAVAN ADAYI! +%{daily_change:.1f} + YÜKSEK HACİM'
                meaning = 'Çok güçlü momentum - tavan olabilir'
            elif rvol >= 1.5:
                bonus = 15
                bonus_text = f'🚀 GÜÇLÜ YÜKSELIŞ +%{daily_change:.1f}'
                meaning = 'Tavan adayı'
            elif rvol >= 1.0:
                bonus = 10
                bonus_text = f'🚀 GÜNLÜK +%{daily_change:.1f}'
                meaning = 'Güçlü yükseliş'
        
        elif daily_change >= 5:
            if rvol >= 1.5:
                bonus = 12
                bonus_text = f'📈 GÜÇLÜ GÜN +%{daily_change:.1f}'
                meaning = 'Sağlıklı yükseliş'
            elif rvol >= 1.0:
                bonus = 8
                bonus_text = f'📈 POZİTİF GÜN +%{daily_change:.1f}'
                meaning = 'Yukarı yönlü'
        
        elif daily_change >= 3:
            if rvol >= 1.5:
                bonus = 6
                bonus_text = f'📊 POZİTİF +%{daily_change:.1f}'
                meaning = 'Hafif yükseliş'
            elif rvol >= 1.0:
                bonus = 3
        
        if bonus > 0:
            total += bonus
            if bonus_text:
                all_reasons.append({
                    'icon': '🚀' if daily_change >= 5 else '📈',
                    'title': bonus_text,
                    'detail': f'Önceki: {prev_close:.2f} → Şu an: {current_price:.2f}',
                    'meaning': meaning
                })
    
    total = min(total, 100)
    
    return {
        'total': total,
        'breakdown': {
            'volume': {'score': vol_s, 'max': 25},
            'momentum': {'score': mom_s, 'max': 20},
            'trend': {'score': tre_s, 'max': 18},
            'wavetrend': {'score': wt_s, 'max': 10},
            'vwap_pivot': {'score': vwp_s, 'max': 12},
            'breakout_candle': {'score': brk_s, 'max': 10},
            'liquidity': {'score': liq_s, 'max': 5},
        },
        'reasons': all_reasons
    }


# ════════════════════════════════════════════════════════════
# HEDEF VE STOP
# ════════════════════════════════════════════════════════════

def calculate_targets(current_price, atr, analysis):
    """3 Hedef + Stop"""
    if not atr or atr <= 0:
        atr_pct = 1.0
    else:
        atr_pct = (atr / current_price) * 100
        atr_pct = max(0.5, min(atr_pct, 4))
    
    target_1_pct = atr_pct * 2.0
    target_2_pct = atr_pct * 3.5
    target_3_pct = atr_pct * 5.5
    stop_pct = atr_pct * 1.5
    
    target_1 = round(current_price * (1 + target_1_pct / 100), 2)
    target_2 = round(current_price * (1 + target_2_pct / 100), 2)
    target_3 = round(current_price * (1 + target_3_pct / 100), 2)
    stop_loss = round(current_price * (1 - stop_pct / 100), 2)
    
    r2 = analysis.get('r2')
    r3 = analysis.get('r3')
    
    if r2 and r2 > current_price and r2 > target_2:
        target_2 = round(r2, 2)
    
    if r3 and r3 > current_price and r3 > target_3:
        target_3 = round(r3, 2)
    
    if target_2 <= target_1:
        target_2 = round(target_1 * 1.025, 2)
    if target_3 <= target_2:
        target_3 = round(target_2 * 1.030, 2)
    
    target_1_pct = round(((target_1 - current_price) / current_price) * 100, 2)
    target_2_pct = round(((target_2 - current_price) / current_price) * 100, 2)
    target_3_pct = round(((target_3 - current_price) / current_price) * 100, 2)
    
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
    """Uyarılar"""
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
                'detail': f'RSI: {rsi:.1f}',
                'action': 'KAR AL!'
            })
        elif rsi > 75:
            warnings.append({
                'level': 'HIGH', 'icon': '🔴',
                'title': 'RSI AŞIRI ALIM',
                'detail': f'RSI: {rsi:.1f}',
                'action': 'Kısmi kar al'
            })
        elif rsi > 70:
            warnings.append({
                'level': 'MEDIUM', 'icon': '⚠️',
                'title': 'RSI Yüksek',
                'detail': f'RSI: {rsi:.1f}',
                'action': 'Dikkatli ol'
            })
    
    if macd_hist is not None and prev_macd_hist is not None:
        if macd_hist > 0 and macd_hist < prev_macd_hist:
            warnings.append({
                'level': 'MEDIUM', 'icon': '⚠️',
                'title': 'MOMENTUM AZALIYOR',
                'detail': 'MACD histogram düşüyor',
                'action': 'Kar al düşün'
            })
    
    if rvol is not None and rvol < 0.7:
        warnings.append({
            'level': 'LOW', 'icon': '⚠️',
            'title': 'HACİM DÜŞÜK',
            'detail': f'RVOL: {rvol:.2f}x',
            'action': 'Sahte hareket olabilir'
        })
    
    candle_patterns = analysis.get('candle_patterns', [])
    bearish = [p for p in candle_patterns if not p.get('bullish')]
    if bearish:
        for bp in bearish[:1]:
            warnings.append({
                'level': 'HIGH', 'icon': bp['icon'],
                'title': f"BEARISH: {bp['name']}",
                'detail': bp['meaning'],
                'action': 'Pozisyonu gözden geçir'
            })
    
    if momentum_status.get('warning'):
        suggestions.append({
            'icon': '💡',
            'text': momentum_status['warning']
        })
    
    return warnings, suggestions


# ════════════════════════════════════════════════════════════
# SİNYAL GÜCÜ
# ════════════════════════════════════════════════════════════

def determine_strength(score):
    """Sinyal kategorisi"""
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
            'action': 'AL - Kademeli giriş',
            'confidence': 'İyi güvenilirlik',
            'risk_level': 'Orta-Düşük'
        }
    elif score >= 65:
        return {
            'type': 'AL', 'strength': 'NORMAL',
            'label': 'AL', 'emoji': '🔥',
            'color': '🟢', 
            'action': 'AL - Küçük pozisyon',
            'confidence': 'Orta güvenilirlik',
            'risk_level': 'Orta'
        }
    elif score >= 50:
        return {
            'type': 'BEKLE', 'strength': 'ZAYIF',
            'label': 'BEKLE / İZLE', 'emoji': '🟡',
            'color': '🟡', 
            'action': 'BEKLE',
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


def suggest_holding_period(score, indicators):
    """Tutma süresi"""
    if score >= 85:
        return {
            'duration': '1-2 gün',
            'strategy': 'HIZLI SWING',
            'reason': 'Çok güçlü momentum',
            'max_days': 3
        }
    elif score >= 75:
        return {
            'duration': '2-4 gün',
            'strategy': 'STANDART SWING',
            'reason': 'Sağlıklı trend',
            'max_days': 5
        }
    elif score >= 65:
        return {
            'duration': '3-7 gün',
            'strategy': 'UZUN SWING',
            'reason': 'Sabırlı olmalı',
            'max_days': 10
        }
    elif score >= 50:
        return {
            'duration': '-',
            'strategy': 'BEKLEME',
            'reason': 'Güçlenmesini bekle',
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
# SİNYAL ÜRETME
# ════════════════════════════════════════════════════════════

def generate_signal(symbol, analysis, history_df=None):
    """Sinyal üret"""
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
    
    indicators = {
        'rsi': analysis.get('rsi'),
        'macd': analysis.get('macd'),
        'rvol': analysis.get('rvol'),
        'adx': analysis.get('adx'),
        'supertrend_dir': analysis.get('supertrend_dir'),
        'atr': analysis.get('atr'),
        'wt1': analysis.get('wt1'),
        'wt2': analysis.get('wt2'),
        'smi': analysis.get('smi'),
        'smi_signal': analysis.get('smi_signal'),
    }
    
    holding = suggest_holding_period(total_score, indicators)
    
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
        'pivot': analysis.get('pivot'),
        'r1': analysis.get('r1'),
        'r2': analysis.get('r2'),
        'r3': analysis.get('r3'),
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
        'timestamp': tr_now().isoformat(),
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
        'risk_level': signal_info['risk_level'],
        'holding': holding,
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


def format_signal_message(signal):
    """Console format"""
    if not signal:
        return "Sinyal yok"
    return f"{signal['emoji']} {signal['label']} - {signal['symbol']} ({signal['score']}/100)"


if __name__ == "__main__":
    print("✅ Signal Engine yüklendi - Akıllı Hacim + WaveTrend + SMI")
