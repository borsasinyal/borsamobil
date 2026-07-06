"""
Profesyonel Sinyal Motoru - SON HAL
DENGELİ Skor + Dip Dönüşü + Güçlü Trend + Sıkı Tavan
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timezone, timedelta

TR_TIMEZONE = timezone(timedelta(hours=3))
def tr_now(): return datetime.now(TR_TIMEZONE)


def score_volume(analysis):
    score = 0; reasons = []
    rvol = analysis.get('rvol', 1)
    current = analysis.get('current_price'); prev_close = analysis.get('prev_close')
    if not (current and prev_close and prev_close > 0): return 0, []
    is_up = current > prev_close
    if is_up:
        if rvol >= 5: score = 25; reasons.append({'icon':'🚀','title':'GÜÇLÜ ALIŞ','detail':f'RVOL:{rvol:.1f}x','meaning':'Kurumsal alım'})
        elif rvol >= 3: score = 22; reasons.append({'icon':'💥','title':'YÜKSEK HACİM','detail':f'RVOL:{rvol:.1f}x','meaning':'Güçlü alış'})
        elif rvol >= 2: score = 18; reasons.append({'icon':'📊','title':'HACİM ARTIŞI','detail':f'RVOL:{rvol:.1f}x','meaning':'İyi alış'})
        elif rvol >= 1.5: score = 14; reasons.append({'icon':'📊','title':'NORMAL ÜSTÜ','detail':f'RVOL:{rvol:.1f}x','meaning':'Yeterli'})
        elif rvol >= 1.0: score = 10; reasons.append({'icon':'📊','title':'HACİM NORMAL','detail':f'RVOL:{rvol:.1f}x','meaning':'Normal'})
        elif rvol >= 0.7: score = 6
    else:
        if rvol >= 3: reasons.append({'icon':'⚠️','title':'SATIŞ BASKISI','detail':f'RVOL:{rvol:.1f}x düşüşte','meaning':'Satılıyor'})
        elif rvol >= 1.5: score = 3
        elif rvol >= 0.8: score = 5
    if rvol < 0.5: reasons.append({'icon':'⚠️','title':'HACİM DÜŞÜK','detail':f'RVOL:{rvol:.1f}x','meaning':'İlgi az'})
    return min(score, 25), reasons


def score_volume_trend(analysis):
    score = 0; reasons = []
    tv = analysis.get('volume', 0); av = analysis.get('avg_volume_5', 0)
    if not (tv > 0 and av > 0): return 0, []
    vr = tv / av
    if vr >= 1.5: score = 3; reasons.append({'icon':'📈','title':'HACİM TRENDİ YUKARI','detail':f'%{(vr-1)*100:.0f} üstü','meaning':'Artan ilgi'})
    elif vr >= 1.2: score = 2
    elif vr >= 0.8: score = 0
    elif vr >= 0.5: score = -2; reasons.append({'icon':'⚠️','title':'HACİM AZALIYOR','detail':'Ortalama altı','meaning':'İlgi azalıyor'})
    else: score = -3
    return score, reasons


def score_trend_health(analysis):
    score = 0; reasons = []
    current = analysis.get('current_price'); prev_close = analysis.get('prev_close')
    pdh = analysis.get('prev_day_high'); pdl = analysis.get('prev_day_low')
    e9 = analysis.get('ema_9'); e21 = analysis.get('ema_21')
    if not (current and prev_close and e9 and e21): return 0, []
    if current < e21 and current < prev_close: score -= 5; reasons.append({'icon':'📉','title':'FİYAT BOZULMASI','detail':'Düşüş+EMA21 altı','meaning':'Zayıf'})
    elif current < prev_close * 0.98: score -= 3
    if pdh and current > pdh: score += 2
    elif pdl and current < pdl: score -= 3; reasons.append({'icon':'🔴','title':'DÜN DİBİ KIRILDI','detail':f'{pdl:.2f}→{current:.2f}','meaning':'Düşüş'})
    rsi = analysis.get('rsi'); prsi = analysis.get('prev_rsi')
    if rsi and prsi and rsi < prsi - 5 and rsi > 50: score -= 2
    return score, reasons


def score_intraday_range(analysis):
    score = 0; reasons = []
    current = analysis.get('current_price'); th = analysis.get('high'); tl = analysis.get('low')
    rvol = analysis.get('rvol', 1)
    if not (current and th and tl and tl > 0): return 0, []
    ir = ((th - tl) / tl) * 100
    dth = ((th - current) / th) * 100 if th > 0 else 100
    at_high = dth < 2
    if ir >= 8 and at_high and rvol >= 2: score = 8; reasons.append({'icon':'⚡','title':f'GÜN İÇİ PATLAMA! +%{ir:.1f}','detail':f'{tl:.2f}→{th:.2f}','meaning':'Tavan adayı!'})
    elif ir >= 8 and at_high: score = 5
    elif ir >= 5 and at_high and rvol >= 1.5: score = 4
    elif ir >= 5 and at_high: score = 2
    elif ir >= 3 and at_high and rvol >= 1.5: score = 1
    return score, reasons


def score_momentum(analysis):
    score = 0; reasons = []
    rsi = analysis.get('rsi'); prev_rsi = analysis.get('prev_rsi')
    macd = analysis.get('macd'); ms = analysis.get('macd_signal')
    pm = analysis.get('prev_macd'); pms = analysis.get('prev_macd_signal'); mh = analysis.get('macd_hist')
    smi = analysis.get('smi'); ss = analysis.get('smi_signal'); psmi = analysis.get('prev_smi')
    
    # RSI (8 puan) - DİP DÖNÜŞÜ + GÜÇLÜ TREND DAHİL
    if rsi is not None:
        if rsi < 30 and prev_rsi and rsi > prev_rsi:
            score += 8; reasons.append({'icon':'🎯','title':'RSI DİP DÖNÜŞÜ!','detail':f'RSI:{rsi:.1f} (dönüyor!)','meaning':'Güçlü dip AL fırsatı!'})
        elif 30 <= rsi < 40 and prev_rsi and rsi > prev_rsi:
            score += 7; reasons.append({'icon':'🎯','title':'RSI DİPTEN DÖNÜYOR','detail':f'RSI:{rsi:.1f}','meaning':'Dip dönüşü - iyi giriş'})
        elif 50 <= rsi <= 65:
            score += 8; reasons.append({'icon':'⚡','title':'RSI İDEAL','detail':f'RSI:{rsi:.1f}','meaning':'Momentum var'})
        elif 45 <= rsi < 50:
            score += 6; reasons.append({'icon':'⚡','title':'RSI DENGE','detail':f'RSI:{rsi:.1f}','meaning':'Denge'})
        elif 40 <= rsi < 45: score += 5
        elif 65 < rsi <= 75:
            score += 5; reasons.append({'icon':'⚡','title':'RSI GÜÇLÜ','detail':f'RSI:{rsi:.1f}','meaning':'Momentum güçlü'})
        elif 75 < rsi <= 85:
            score += 3; reasons.append({'icon':'⚡','title':'RSI ÇOK GÜÇLÜ','detail':f'RSI:{rsi:.1f}','meaning':'Güçlü trend devam'})
        elif 85 < rsi <= 90:
            score += 1; reasons.append({'icon':'⚠️','title':'RSI AŞIRI GÜÇLÜ','detail':f'RSI:{rsi:.1f}','meaning':'Dikkat ama devam edebilir'})
        elif rsi > 90: score += 0
        elif 35 <= rsi < 40: score += 3
    
    # MACD (8 puan)
    if all(v is not None for v in [macd, ms]):
        if pm is not None and pms is not None:
            if pm <= pms and macd > ms: score += 8; reasons.append({'icon':'🚀','title':'MACD KESİŞİMİ','detail':'Yukarı kesti','meaning':'YENİ momentum'})
            elif macd > ms and macd > 0: score += 6; reasons.append({'icon':'📈','title':'MACD POZİTİF','detail':'Yükselişte','meaning':'Yukarı'})
            elif macd > ms: score += 4
        else:
            if macd > ms: score += 4
    
    if mh is not None:
        ph = analysis.get('prev_macd_hist')
        if ph is not None and mh > ph and mh > 0: score += 1
    
    # SMI (6 puan)
    if smi is not None and ss is not None:
        if smi > ss:
            if psmi is not None and psmi <= ss: score += 6; reasons.append({'icon':'📊','title':'SMI KESİŞİMİ','detail':f'SMI:{smi:.1f}','meaning':'Güçlü momentum'})
            elif -40 < smi < 40: score += 4; reasons.append({'icon':'📊','title':'SMI POZİTİF','detail':f'SMI:{smi:.1f}','meaning':'Pozitif'})
            elif 40 <= smi < 60: score += 3
        if smi < -40 and psmi is not None and smi > psmi: score += 4; reasons.append({'icon':'🎯','title':'SMI DİP DÖNÜŞÜ','detail':f'SMI:{smi:.1f}','meaning':'Dip dönüyor'})
    
    return min(score, 22), reasons


def score_trend(analysis):
    score = 0; reasons = []
    c = analysis.get('current_price'); e9 = analysis.get('ema_9'); e21 = analysis.get('ema_21')
    e50 = analysis.get('ema_50'); pc = analysis.get('prev_close'); sd = analysis.get('supertrend_dir')
    adx = analysis.get('adx'); pdi = analysis.get('plus_di'); mdi = analysis.get('minus_di')
    
    # DİP DÖNÜŞÜ TESPİTİ
    rsi = analysis.get('rsi'); prev_rsi = analysis.get('prev_rsi'); rvol = analysis.get('rvol', 1)
    is_dip = (rsi and prev_rsi and rsi < 40 and rsi > prev_rsi and rvol >= 1.5)
    
    # EMA SIRALAMA
    if all(v is not None for v in [c, e9, e21, e50]):
        if c > e9 > e21 > e50: score += 10; reasons.append({'icon':'🏆','title':'MÜKEMMEL TREND','detail':'Fiyat>EMA9>EMA21>EMA50','meaning':'Tüm yukarı'})
        elif c > e9 and c > e21 and c > e50: score += 7; reasons.append({'icon':'📈','title':'GÜÇLÜ TREND','detail':'Tüm EMA üstü','meaning':'Yukarı'})
        elif c > e21 and c > e50: score += 6; reasons.append({'icon':'📈','title':'TREND POZİTİF','detail':'EMA21+50 üstü','meaning':'Orta vade yukarı'})
        elif c > e50: score += 4; reasons.append({'icon':'📈','title':'EMA50 ÜSTÜNDE','detail':f'>{e50:.2f}','meaning':'Sağlıklı'})
        elif c > e21 and c < e50: score += 1; reasons.append({'icon':'⚠️','title':'KARIŞIK','detail':'EMA21↑ EMA50↓','meaning':'Zayıf'})
        elif c < e50:
            if is_dip:
                score += 2; reasons.append({'icon':'🎯','title':'DİP DÖNÜŞÜ - EMA ALTI NORMAL','detail':f'RSI:{rsi:.1f} dönüyor + hacim','meaning':'EMA altı ama dip dönüşü!'})
            else:
                score -= 3; reasons.append({'icon':'🔴','title':'EMA50 ALTINDA','detail':f'<{e50:.2f}','meaning':'AŞAĞI'})
    
    # EMA50 KIRILIM/KAYIP
    pe50 = analysis.get('prev_ema_50')
    if all(v is not None for v in [c, e50, pc, pe50]):
        if pc <= pe50 and c > e50: score += 5; reasons.append({'icon':'🎯','title':'EMA50 KIRILDI!','detail':'Üstüne çıktı','meaning':'UPTREND'})
        elif pc > pe50 and c < e50:
            if not is_dip: score -= 5; reasons.append({'icon':'🔴','title':'EMA50 KAYBEDİLDİ','detail':'Altına indi','meaning':'BOZULUYOR'})
    
    # GOLDEN CROSS
    pe9 = analysis.get('prev_ema_9'); pe21 = analysis.get('prev_ema_21')
    if all(v is not None for v in [e9, e21, pe9, pe21]):
        if pe9 <= pe21 and e9 > e21: score += 3; reasons.append({'icon':'⭐','title':'GOLDEN CROSS','detail':'EMA9>EMA21','meaning':'Dönüş'})
    
    if sd == 1: score += 3; reasons.append({'icon':'🟢','title':'SUPERTREND YUKARI','detail':'Yeşil','meaning':'Yukarı'})
    
    if adx is not None:
        if adx > 30 and pdi and mdi and pdi > mdi: score += 4; reasons.append({'icon':'💪','title':'GÜÇLÜ TREND','detail':f'ADX:{adx:.1f}','meaning':'Güçlü'})
        elif adx > 25: score += 3
        elif adx > 20: score += 2
        elif adx > 15: score += 1
    
    return min(score, 25), reasons
    

def score_wavetrend(analysis):
    score = 0; reasons = []
    wt1 = analysis.get('wt1'); wt2 = analysis.get('wt2')
    pw1 = analysis.get('prev_wt1'); pw2 = analysis.get('prev_wt2')
    if wt1 is None or wt2 is None: return 0, []
    if all(v is not None for v in [pw1, pw2]):
        if pw1 <= pw2 and wt1 > wt2:
            if wt1 < -53: return 8, [{'icon':'🌊','title':'WT DİP DÖNÜŞÜ!','detail':f'WT1:{wt1:.1f}','meaning':'Mükemmel AL'}]
            else: return 6, [{'icon':'🌊','title':'WT AL KESİŞİMİ','detail':'WT1>WT2','meaning':'Yeni yükseliş'}]
    if wt1 > wt2:
        if wt1 < -40: score = 5; reasons.append({'icon':'🌊','title':'WT DİP','detail':f'WT1:{wt1:.1f}','meaning':'Dipten dönüş'})
        elif wt1 < 30: score = 4; reasons.append({'icon':'🌊','title':'WT POZİTİF','detail':'WT1>WT2','meaning':'Yükseliş'})
        elif wt1 < 50: score = 3
        elif wt1 > 60: reasons.append({'icon':'⚠️','title':'WT AŞIRI ALIM','detail':f'WT1:{wt1:.1f}','meaning':'Düzeltme gelebilir'})
    elif wt1 < -53: score = 2
    return min(score, 8), reasons


def score_dual_confirmation(analysis):
    score = 0; reasons = []
    wt1 = analysis.get('wt1'); wt2 = analysis.get('wt2')
    smi = analysis.get('smi'); ss = analysis.get('smi_signal')
    if not all(v is not None for v in [wt1, wt2, smi, ss]): return 0, []
    if wt1 > wt2 and smi > ss:
        if wt1 < -30 and smi < -30: score = 3; reasons.append({'icon':'🎯','title':'ÇİFTLİ ONAY: DİP','detail':'WT+SMI dip','meaning':'Mükemmel!'})
        elif wt1 < 50 and -40 < smi < 40: score = 2; reasons.append({'icon':'🎯','title':'ÇİFTLİ ONAY','detail':'İkisi pozitif','meaning':'Destek'})
        else: score = 1
    return score, reasons


def score_position_bonus(analysis):
    score = 0; reasons = []
    c = analysis.get('current_price'); e21 = analysis.get('ema_21'); e50 = analysis.get('ema_50')
    macd = analysis.get('macd'); ms = analysis.get('macd_signal')
    rvol = analysis.get('rvol', 1); rsi = analysis.get('rsi', 50); sd = analysis.get('supertrend_dir')
    cond = 0
    if c and e21 and c > e21: cond += 1
    if c and e50 and c > e50: cond += 1
    if macd and ms and macd > ms: cond += 1
    if rvol >= 1.3: cond += 1
    if 45 <= rsi <= 70: cond += 1
    if sd == 1: cond += 1
    if cond >= 6: score = 5; reasons.append({'icon':'✨','title':'MÜKEMMEL POZİSYON','detail':f'{cond}/6','meaning':'Çok güçlü'})
    elif cond == 5: score = 4; reasons.append({'icon':'✨','title':'ÇOK İYİ POZİSYON','detail':f'{cond}/6','meaning':'Güçlü'})
    elif cond == 4: score = 3
    elif cond == 3: score = 1
    return score, reasons


def score_vwap_pivot(analysis):
    score = 0; reasons = []
    c = analysis.get('current_price'); p = analysis.get('pivot')
    r1 = analysis.get('r1'); r2 = analysis.get('r2'); r3 = analysis.get('r3'); s1 = analysis.get('s1')
    if not (c and p): return 0, []
    if r2 and c > r2:
        if r3 and c < r3: score = 15; reasons.append({'icon':'🚀','title':'R2 KIRILDI!','detail':f'R2({r2:.2f})','meaning':'Çok güçlü'})
        else: score = 13; reasons.append({'icon':'🚀','title':'R2 ÜSTÜNDE','detail':'Geçildi','meaning':'Güçlü'})
    elif r1 and r2 and c > r1 and c <= r2: score = 11; reasons.append({'icon':'🎯','title':'R1 KIRILDI','detail':f'R1({r1:.2f})','meaning':'Yukarı'})
    elif r1 and c > p and c <= r1:
        d = ((r1-c)/c)*100
        if d < 1: score = 10; reasons.append({'icon':'🎯','title':'R1 YAKININDA','detail':'Test','meaning':'Kırılım yakın'})
        else: score = 8; reasons.append({'icon':'📈','title':'PİVOT ÜSTÜ','detail':'Üstünde','meaning':'Alıcılar kontrolde'})
    elif p and abs(c-p)/p < 0.005: score = 6; reasons.append({'icon':'🎯','title':'PİVOT TESTİ','detail':'Kritik','meaning':'Yön belirleniyor'})
    elif s1 and p and c > s1 and c < p: score = 4
    return min(score, 15), reasons


def score_breakout_candle(analysis):
    score = 0; reasons = []
    brs = analysis.get('breakouts', []); cps = analysis.get('candle_patterns', [])
    up = [b for b in brs if b['type'] == 'UP']
    if up:
        mp = max(b['period'] for b in up)
        if mp >= 50: score += 3; reasons.append({'icon':'🚀','title':'50G ZİRVE','detail':f'{mp}G','meaning':'Çok güçlü'})
        elif mp >= 20: score += 2; reasons.append({'icon':'🚀','title':'20G ZİRVE','detail':f'{mp}G','meaning':'Güçlü'})
        elif mp >= 10: score += 1
    bull = [p for p in cps if p.get('bullish')]
    if bull:
        s = bull[0]
        if s['key'] in ['three_white_soldiers','bullish_engulfing','morning_star']:
            score += 2; reasons.append({'icon':s['icon'],'title':f"FORMASYON: {s['name'].upper()}",'detail':s['meaning'],'meaning':'Güçlü dönüş'})
        else: score += 1
    return min(score, 5), reasons


def score_liquidity(analysis):
    score = 0; reasons = []
    rvol = analysis.get('rvol'); c = analysis.get('current_price'); v = analysis.get('volume')
    if rvol and rvol >= 0.8: score += 2
    if c and v:
        vtl = c * v
        if vtl > 10_000_000: score += 3; reasons.append({'icon':'✅','title':'YÜKSEK LİKİDİTE','detail':f'{vtl/1_000_000:.1f}M TL','meaning':'Rahat al-sat'})
        elif vtl > 5_000_000: score += 2
    return min(score, 5), reasons


# ════════════════════════════════════════════════════════════
# TOPLAM PUAN - DENGELİ + DİP DÖNÜŞÜ + GÜÇLÜ TREND
# ════════════════════════════════════════════════════════════

def calculate_total_score(analysis):
    """
    DENGELİ SKOR:
    - Temel: max 100
    - Bonus: düşük (şişirme yok)
    - Dip dönüşü: EMA cezasız, RSI 8 puan
    - Güçlü trend: RSI 75-85 puan alır
    - Tavan: %5-8 arası + hacim
    - 100 puan: Gerçekten mükemmel!
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
    vt_s, vt_r = score_volume_trend(analysis)
    th_s, th_r = score_trend_health(analysis)
    ir_s, ir_r = score_intraday_range(analysis)
    
    # TEMEL (max 100)
    base = min(vol_s + mom_s + tre_s + wt_s + vwp_s + brk_s + liq_s, 100)
    
    # BONUS (düşük! max ~8)
    bonus = dual_s + pos_s
    
    # AYARLAMA (sınırlı)
    adj = vt_s + th_s + ir_s
    adj = max(-10, min(adj, 10))
    
    total = base + bonus + adj
    all_reasons = vol_r + mom_r + tre_r + wt_r + vwp_r + brk_r + liq_r + dual_r + pos_r + vt_r + th_r + ir_r
    
    # TAVAN BONUSU
    cp = analysis.get('current_price'); pc = analysis.get('prev_close'); rvol = analysis.get('rvol', 1.0)
    
    if cp and pc and pc > 0:
        dc = ((cp - pc) / pc) * 100
        b = 0; bt = None; m = None
        
        # ZATEN TAVAN
        if dc >= 9.5: b = 0
        # TAVAN YAKIN
        elif dc >= 8:
            if rvol >= 2: b, bt, m = 3, f'⚠️ TAVAN YAKIN +%{dc:.1f}', 'RİSKLİ'
            elif rvol >= 1.5: b, bt, m = 2, f'⚠️ TAVAN YAKIN +%{dc:.1f}', 'Dikkat'
        # GERÇEK TAVAN ADAYI
        elif dc >= 5:
            if rvol >= 2: b, bt, m = 8, f'🚀 TAVAN ADAYI! +%{dc:.1f}', 'Tavan olabilir'
            elif rvol >= 1.5: b, bt, m = 6, f'🚀 GÜÇLÜ TAVAN ADAYI +%{dc:.1f}', 'Tavan adayı'
            elif rvol >= 1.0: b, bt, m = 4, f'🚀 GÜNLÜK +%{dc:.1f}', 'Güçlü'
        # GÜÇLÜ GÜN
        elif dc >= 3:
            if rvol >= 1.5: b, bt, m = 3, f'📈 GÜÇLÜ GÜN +%{dc:.1f}', 'Sağlıklı'
            elif rvol >= 1.0: b, bt, m = 2, f'📈 POZİTİF +%{dc:.1f}', 'Yukarı'
        # HAFİF
        elif dc >= 1.5:
            if rvol >= 1.5: b = 1
        
        if b > 0:
            total += b
            if bt: all_reasons.append({'icon':'🚀' if dc>=5 else '📈','title':bt,'detail':f'{pc:.2f}→{cp:.2f}','meaning':m})
    
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
# HEDEF, UYARI, SİNYAL
# ════════════════════════════════════════════════════════════

def calculate_targets(cp, atr, analysis):
    if not atr or atr <= 0: ap = 1.0
    else: ap = max(0.5, min((atr/cp)*100, 4))
    t1 = round(cp*(1+ap*2.0/100),2); t2 = round(cp*(1+ap*3.5/100),2); t3 = round(cp*(1+ap*5.5/100),2); sl = round(cp*(1-ap*1.5/100),2)
    r2 = analysis.get('r2'); r3 = analysis.get('r3')
    if r2 and r2 > cp and r2 > t2: t2 = round(r2,2)
    if r3 and r3 > cp and r3 > t3: t3 = round(r3,2)
    if t2 <= t1: t2 = round(t1*1.025,2)
    if t3 <= t2: t3 = round(t2*1.030,2)
    t1p = round(((t1-cp)/cp)*100,2); t2p = round(((t2-cp)/cp)*100,2); t3p = round(((t3-cp)/cp)*100,2)
    risk = cp - sl; rr = round((t2-cp)/risk,2) if risk > 0 else 0
    return {'entry':cp,'target_1':t1,'target_1_pct':t1p,'target_2':t2,'target_2_pct':t2p,'target_3':t3,'target_3_pct':t3p,'stop_loss':sl,'stop_pct':round(ap*1.5,2),'risk_reward':rr,'atr_value':round(atr,4) if atr else None}


def generate_warnings(analysis):
    warnings = []; suggestions = []
    rsi = analysis.get('rsi'); rvol = analysis.get('rvol')
    cp = analysis.get('current_price'); pc = analysis.get('prev_close')
    
    # TAVAN UYARISI
    if cp and pc and pc > 0:
        dc = ((cp-pc)/pc)*100
        if dc >= 9.5: warnings.append({'level':'EXTREME','icon':'🔴🔴','title':'ZATEN TAVAN!','detail':f'+%{dc:.2f}','action':'GİRMEYİN!'})
        elif dc >= 8: warnings.append({'level':'HIGH','icon':'⚠️','title':'TAVANA YAKIN','detail':f'+%{dc:.2f}','action':'Riskli'})
    
    # INTRADAY GERİ ÇEKİLME
    th = analysis.get('high'); tl = analysis.get('low')
    if th and tl and tl > 0 and cp:
        ir = ((th-tl)/tl)*100
        if ir >= 8:
            dth = ((th-cp)/th)*100 if th > 0 else 100
            if dth > 3: warnings.append({'level':'MEDIUM','icon':'⚠️','title':'GERİ ÇEKİLME','detail':f'Zirve:{th:.2f} Şuan:{cp:.2f}','action':'Zirveden düştü'})
    
    # RSI UYARILARI (GÜNCELLENMİŞ!)
    if rsi:
        if rsi > 90: warnings.append({'level':'EXTREME','icon':'🔴🔴','title':'RSI AŞIRI!','detail':f'RSI:{rsi:.1f}','action':'KAR AL! Düzeltme çok yakın!'})
        elif rsi > 85: warnings.append({'level':'HIGH','icon':'🔴','title':'RSI ÇOK YÜKSEK','detail':f'RSI:{rsi:.1f}','action':'Kısmi kar al, stop yukarı çek'})
        elif rsi > 75: warnings.append({'level':'MEDIUM','icon':'⚠️','title':'RSI GÜÇLÜ TREND','detail':f'RSI:{rsi:.1f}','action':'Stop yukarı çek, trend devam edebilir'})
    
    # HACİM UYARISI
    if rvol is not None and rvol < 0.7: warnings.append({'level':'LOW','icon':'⚠️','title':'HACİM DÜŞÜK','detail':f'RVOL:{rvol:.2f}x','action':'Dikkatli'})
    
    return warnings, suggestions


def determine_strength(s):
    if s >= 85: return {'type':'AL','strength':'COK_GUCLU','label':'ÇOK GÜÇLÜ AL','emoji':'🔥🔥🔥','color':'🟢','action':'AL - Güçlü pozisyon','confidence':'Yüksek güvenilirlik','risk_level':'Düşük'}
    elif s >= 75: return {'type':'AL','strength':'GUCLU','label':'GÜÇLÜ AL','emoji':'🔥🔥','color':'🟢','action':'AL - Kademeli giriş','confidence':'İyi güvenilirlik','risk_level':'Orta-Düşük'}
    elif s >= 65: return {'type':'AL','strength':'NORMAL','label':'AL','emoji':'🔥','color':'🟢','action':'AL - Küçük pozisyon','confidence':'Orta güvenilirlik','risk_level':'Orta'}
    elif s >= 50: return {'type':'BEKLE','strength':'ZAYIF','label':'BEKLE','emoji':'🟡','color':'🟡','action':'BEKLE','confidence':'Belirsiz','risk_level':'Yüksek'}
    else: return {'type':'YOK','strength':'YOK','label':'SİNYAL YOK','emoji':'⚪','color':'⚪','action':'GİRMİYORUM','confidence':'Sinyal yok','risk_level':'-'}


def suggest_holding_period(s, ind):
    if s >= 85: return {'duration':'1-2 gün','strategy':'HIZLI SWING','reason':'Çok güçlü momentum','max_days':3}
    elif s >= 75: return {'duration':'2-4 gün','strategy':'STANDART SWING','reason':'Sağlıklı trend','max_days':5}
    elif s >= 65: return {'duration':'3-7 gün','strategy':'UZUN SWING','reason':'Sabırlı olmalı','max_days':10}
    else: return {'duration':'-','strategy':'BEKLEME','reason':'Güçlenmesini bekle','max_days':0}


def generate_signal(symbol, analysis, history_df=None):
    if not analysis: return None
    cp = analysis.get('current_price')
    if not cp: return None
    
    sd = calculate_total_score(analysis)
    ts = sd['total']
    si = determine_strength(ts)
    atr = analysis.get('atr')
    targets = calculate_targets(cp, atr, analysis)
    warnings, suggestions = generate_warnings(analysis)
    
    ind = {'rsi':analysis.get('rsi'),'macd':analysis.get('macd'),'rvol':analysis.get('rvol'),
           'adx':analysis.get('adx'),'supertrend_dir':analysis.get('supertrend_dir'),'atr':atr,
           'wt1':analysis.get('wt1'),'wt2':analysis.get('wt2'),'smi':analysis.get('smi'),'smi_signal':analysis.get('smi_signal')}
    
    holding = suggest_holding_period(ts, ind)
    filled = int(ts/5); empty = 20-filled
    sb = '█'*filled + '░'*empty
    
    if ts >= 85: stars = '🟢🟢🟢🟢🟢'
    elif ts >= 75: stars = '🟢🟢🟢🟢⚪'
    elif ts >= 65: stars = '🟢🟢🟢⚪⚪'
    elif ts >= 50: stars = '🟡🟡⚪⚪⚪'
    else: stars = '⚪⚪⚪⚪⚪'
    
    kl = {'pivot':analysis.get('pivot'),'r1':analysis.get('r1'),'r2':analysis.get('r2'),'r3':analysis.get('r3'),
          's1':analysis.get('s1'),'prev_day_high':analysis.get('prev_day_high'),'prev_day_low':analysis.get('prev_day_low'),
          'ema_9':analysis.get('ema_9'),'ema_21':analysis.get('ema_21'),'ema_50':analysis.get('ema_50')}
    
    return {
        'symbol':symbol.replace('.IS',''),'full_symbol':symbol,'timestamp':tr_now().isoformat(),
        'current_price':cp,'score':ts,'score_bar':sb,'stars':stars,
        'signal_type':si['type'],'strength':si['strength'],'label':si['label'],
        'emoji':si['emoji'],'action':si['action'],'confidence':si['confidence'],
        'risk_level':si['risk_level'],'holding':holding,'targets':targets,
        'reasons':sd['reasons'],'breakdown':sd['breakdown'],'warnings':warnings,
        'suggestions':suggestions,'key_levels':kl,
        'candle_patterns':analysis.get('candle_patterns',[]),
        'breakouts':analysis.get('breakouts',[]),
        'momentum_status':analysis.get('momentum_status',{}),
        'indicators':ind
    }


def format_signal_message(signal):
    if not signal: return "Sinyal yok"
    return f"{signal['emoji']} {signal['label']} - {signal['symbol']} ({signal['score']}/100)"


if __name__ == "__main__":
    print("✅ Signal Engine - SON HAL: Dengeli + Dip Dönüşü + Güçlü Trend + Sıkı Tavan")
