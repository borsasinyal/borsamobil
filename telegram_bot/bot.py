"""
Telegram Bot - Profesyonel Sinyal Gönderici
SWING + SAATLİK (Gün İçi) Kart Desteği
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timezone, timedelta
from telegram import Bot
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


TR_TIMEZONE = timezone(timedelta(hours=3))

def tr_now():
    return datetime.now(TR_TIMEZONE)

def escape_html(text):
    if text is None: return ""
    text = str(text)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def get_signal_color(signal_index):
    colors = {1: '🟢', 2: '🔵', 3: '🟣', 4: '🟡', 5: '🟠', 6: '⚪', 7: '⚫'}
    return colors.get(signal_index, '⚪')

def get_medal_emoji(rank):
    medals = {1: '🥇', 2: '🥈', 3: '🥉', 4: '🏅', 5: '🎖️'}
    return medals.get(rank, f"{rank}.")

def is_tavan_adayi(signal):
    if not signal or not signal.get('reasons'): return False
    for r in signal['reasons']:
        title = r.get('title', '').upper()
        if 'TAVAN ADAYI' in title or 'GÜÇLÜ YÜKSELIŞ' in title or 'YÜKSELİŞ' in title:
            return True
    return False

def get_bot():
    if not TELEGRAM_BOT_TOKEN: raise ValueError("❌ TOKEN boş!")
    if not TELEGRAM_CHAT_ID: raise ValueError("❌ CHAT_ID boş!")
    return Bot(token=TELEGRAM_BOT_TOKEN)


# ════════════════════════════════════════════════════════════
# MESAJ GÖNDERME
# ════════════════════════════════════════════════════════════

async def send_message_async(text, parse_mode=ParseMode.HTML):
    bot = get_bot()
    try:
        if len(text) > 4096:
            chunks = []
            current_chunk = ""
            for line in text.split('\n'):
                if len(current_chunk) + len(line) + 1 > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            if current_chunk: chunks.append(current_chunk)
            for i, chunk in enumerate(chunks):
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk, parse_mode=parse_mode, disable_web_page_preview=True)
                if i < len(chunks) - 1: await asyncio.sleep(0.5)
            return True
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=parse_mode, disable_web_page_preview=True)
        return True
    except Exception as e:
        print(f"❌ Mesaj hatası: {str(e)}")
        try:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⚠️ Format hatası!\n{str(e)[:200]}", disable_web_page_preview=True)
        except: pass
        return False

def send_message(text):
    try: return asyncio.run(send_message_async(text))
    except Exception as e:
        print(f"❌ Mesaj hatası: {e}")
        return False


# ════════════════════════════════════════════════════════════
# ÖZET KART (Top 5 SWING)
# ════════════════════════════════════════════════════════════

def format_summary_card(signals, max_signals=5):
    if not signals: return None
    top_signals = signals[:max_signals]
    count = len(top_signals)
    tavan_sayisi = sum(1 for s in top_signals if is_tavan_adayi(s))
    
    msg = "🏆🏆🏆━━━━━━━━━━━━━━━━━🏆🏆🏆\n"
    msg += f"      <b>EN İYİ {count} SWING SİNYAL</b>\n"
    if tavan_sayisi > 0:
        msg += f"      ⚡ {tavan_sayisi} TAVAN ADAYI VAR!\n"
    msg += "🏆🏆🏆━━━━━━━━━━━━━━━━━🏆🏆🏆\n\n"
    
    for i, signal in enumerate(top_signals, 1):
        symbol = escape_html(signal.get('symbol', '-'))
        score = signal.get('score', 0)
        price = signal.get('current_price', 0)
        targets = signal.get('targets', {})
        target_1 = targets.get('target_1', 0)
        target_1_pct = targets.get('target_1_pct', 0)
        medal = get_medal_emoji(i)
        tavan_emoji = " ⚡" if is_tavan_adayi(signal) else ""
        
        if score >= 85: stars = "⭐⭐⭐⭐⭐"
        elif score >= 75: stars = "⭐⭐⭐⭐"
        elif score >= 65: stars = "⭐⭐⭐"
        else: stars = "⭐⭐"
        
        bar_length = int(score / 10)
        bar = "█" * bar_length + "░" * (10 - bar_length)
        
        msg += f"{medal} <b>{symbol}</b>{tavan_emoji} {stars}\n"
        msg += f"   💯 <b>{score}/100</b> <code>{bar}</code>\n"
        msg += f"   💰 {price:.2f} → 🎯 <b>{target_1:.2f}</b> (<b>+{target_1_pct}%</b>)\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}\n"
    msg += "📩 <i>Detaylı kartlar geliyor...</i>"
    return msg


# ════════════════════════════════════════════════════════════
# SWING SİNYAL KARTI (Mevcut - renkli çerçeve)
# ════════════════════════════════════════════════════════════

def format_signal_for_telegram(signal, signal_index=1):
    if not signal: return None
    
    required = ['emoji', 'label', 'symbol', 'current_price', 'score', 'score_bar', 'stars', 'confidence', 'action', 'targets']
    for field in required:
        if signal.get(field) is None: return None
    
    t = signal['targets']
    target_required = ['entry', 'target_1', 'target_2', 'target_3', 'stop_loss', 'target_1_pct', 'target_2_pct', 'target_3_pct', 'stop_pct', 'risk_reward']
    for field in target_required:
        if t.get(field) is None: return None
    
    emoji = signal['emoji']
    label = escape_html(signal['label'])
    symbol = escape_html(signal['symbol'])
    price = signal['current_price']
    score = signal['score']
    score_bar = signal['score_bar']
    stars = signal['stars']
    confidence = escape_html(signal['confidence'])
    action = escape_html(signal['action'])
    risk_level = escape_html(signal.get('risk_level', '-'))
    holding = signal.get('holding', {})
    
    tavan_adayi = is_tavan_adayi(signal)
    
    if tavan_adayi:
        color = "🔴"
        special_emoji = "⚡"
        title_extra = " - ⚡ TAVAN ADAYI!"
    else:
        color = get_signal_color(signal_index)
        special_emoji = ""
        title_extra = ""
    
    medal = get_medal_emoji(signal_index)
    
    if tavan_adayi:
        msg = f"{color}{color}{color}{special_emoji}{special_emoji}{special_emoji}{color}{color}{color}{special_emoji}{special_emoji}{special_emoji}{color}{color}{color}\n"
        msg += f"     {medal} <b>SİNYAL #{signal_index}{title_extra}</b>\n"
        msg += f"{color}{color}{color}{special_emoji}{special_emoji}{special_emoji}{color}{color}{color}{special_emoji}{special_emoji}{special_emoji}{color}{color}{color}\n\n"
        msg += "⚡⚡⚡ <b>TAVAN ADAYI TESPİT EDİLDİ!</b> ⚡⚡⚡\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🚀 Hacim destekli güçlü yükseliş!\n"
        msg += "⚠️ <b>RİSKLİ</b> - Küçük pozisyon\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    else:
        msg = f"{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}\n"
        msg += f"     {medal} <b>SİNYAL #{signal_index}</b>\n"
        msg += f"{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}\n\n"
    
    msg += f"{emoji} <b>{label}</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📌 <b>{symbol}</b>{'⚡' if tavan_adayi else ''}\n"
    msg += f"💰 Fiyat: <b>{price:.2f} TL</b>\n"
    msg += f"⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}\n\n"
    
    msg += f"💯 <b>SKOR: {score}/100</b>{'⚡⚡⚡' if tavan_adayi else ''}\n"
    msg += f"<code>{score_bar}</code>\n{stars}\n"
    msg += f"📊 <i>{confidence}</i>\n🎯 <b>{action}</b>\n\n"
    
    if holding and holding.get('strategy') and holding.get('strategy') != 'YOK':
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📋 <b>STRATEJİ ÖNERİSİ</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"⚡ <b>Tip:</b> {escape_html(holding.get('strategy', ''))}\n"
        if holding.get('duration', '-') != '-':
            msg += f"📅 <b>Tutma:</b> {escape_html(holding['duration'])}\n"
        msg += f"🎲 <b>Risk:</b> {risk_level}\n"
        if holding.get('reason'): msg += f"💡 <i>{escape_html(holding['reason'])}</i>\n"
        msg += "\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n💼 <b>İŞLEM PLANI - 3 HEDEF</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📥 <b>GİRİŞ:</b> {t['entry']:.2f} TL\n\n"
    
    h1 = "1-2 gün" if score >= 85 else "2-3 gün" if score >= 75 else "2-4 gün"
    h2 = "2-3 gün" if score >= 85 else "3-4 gün" if score >= 75 else "3-5 gün"
    h3 = "3-5 gün" if score >= 85 else "4-7 gün" if score >= 75 else "5-10 gün"
    
    msg += f"🎯 <b>HEDEF 1:</b> {t['target_1']:.2f} TL <b>(+{t['target_1_pct']}%)</b>\n   ⏰ <i>{h1}</i>\n   💡 <i>%33 sat, stop'u girişe çek</i>\n\n"
    msg += f"🎯 <b>HEDEF 2:</b> {t['target_2']:.2f} TL <b>(+{t['target_2_pct']}%)</b>\n   ⏰ <i>{h2}</i>\n   💡 <i>%33 sat, stop'u H1'e çek</i>\n\n"
    msg += f"🎯 <b>HEDEF 3:</b> {t['target_3']:.2f} TL <b>(+{t['target_3_pct']}%)</b>\n   ⏰ <i>{h3}</i>\n   💡 <i>Kalanı sat</i>\n\n"
    msg += f"🛑 <b>STOP:</b> {t['stop_loss']:.2f} TL <b>(-{t['stop_pct']}%)</b>\n"
    msg += f"⚖️ <b>R/Ö:</b> 1 / {t['risk_reward']}\n\n"
    
    if signal.get('reasons'):
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>ALMA SEBEPLERİ ({len(signal['reasons'])})</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for r in signal['reasons']:
            msg += f"{r.get('icon', '✅')} <b>{escape_html(r.get('title', ''))}</b>\n   📌 {escape_html(r.get('detail', ''))}\n   → <i>{escape_html(r.get('meaning', ''))}</i>\n\n"
    
    if signal.get('warnings'):
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n⚠️ <b>UYARILAR ({len(signal['warnings'])})</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for w in signal['warnings']:
            msg += f"{w.get('icon', '⚠️')} <b>{escape_html(w.get('title', ''))}</b>\n   📌 {escape_html(w.get('detail', ''))}\n   💡 <b>{escape_html(w.get('action', ''))}</b>\n\n"
    
    if signal.get('breakouts'):
        up_br = [b for b in signal['breakouts'] if b.get('type') == 'UP']
        if up_br:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n🚀 <b>KIRILIMLAR</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for br in up_br:
                msg += f"{br.get('icon', '🚀')} <b>{escape_html(br.get('detail', ''))}</b>\n   → <i>{escape_html(br.get('meaning', ''))}</i>\n\n"
    
    if signal.get('candle_patterns'):
        patterns = signal['candle_patterns'][:3]
        if patterns:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n🕯️ <b>MUM FORMASYONLARI</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for cp in patterns:
                msg += f"{cp.get('icon', '🕯️')} <b>{escape_html(cp.get('name', ''))}</b>\n   → <i>{escape_html(cp.get('meaning', ''))}</i>\n\n"
    
    b = signal['breakdown']
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📊 <b>PUAN DAĞILIMI</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💥 Hacim       : <b>{b['volume']['score']}/{b['volume']['max']}</b>\n"
    msg += f"⚡ Momentum    : <b>{b['momentum']['score']}/{b['momentum']['max']}</b>\n"
    msg += f"📈 Trend       : <b>{b['trend']['score']}/{b['trend']['max']}</b>\n"
    msg += f"🌊 WaveTrend   : <b>{b['wavetrend']['score']}/{b['wavetrend']['max']}</b>\n"
    msg += f"🎯 Pivot Point : <b>{b['vwap_pivot']['score']}/{b['vwap_pivot']['max']}</b>\n"
    msg += f"🚀 Kırılım/Mum : <b>{b['breakout_candle']['score']}/{b['breakout_candle']['max']}</b>\n"
    msg += f"💧 Likidite    : <b>{b['liquidity']['score']}/{b['liquidity']['max']}</b>\n\n"
    
    kl = signal.get('key_levels', {})
    if any([kl.get('pivot'), kl.get('ema_9'), kl.get('r1')]):
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📍 <b>ÖNEMLİ SEVİYELER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        if kl.get('pivot'): msg += f"{'🟢' if price > kl['pivot'] else '🔴'} Pivot : <b>{kl['pivot']:.2f} TL</b>\n"
        if kl.get('r1'): msg += f"{'✅' if price > kl['r1'] else '🎯'} R1    : <b>{kl['r1']:.2f} TL</b>\n"
        if kl.get('r2'): msg += f"{'✅' if price > kl['r2'] else '🎯'} R2    : <b>{kl['r2']:.2f} TL</b>\n"
        if kl.get('r3'): msg += f"{'✅' if price > kl['r3'] else '🎯'} R3    : <b>{kl['r3']:.2f} TL</b>\n"
        if kl.get('s1'): msg += f"⬇️ S1    : <b>{kl['s1']:.2f} TL</b>\n"
        if kl.get('ema_9'): msg += f"📊 EMA 9 : <b>{kl['ema_9']:.2f} TL</b>\n"
        if kl.get('ema_21'): msg += f"📊 EMA21 : <b>{kl['ema_21']:.2f} TL</b>\n"
        if kl.get('ema_50'): msg += f"📊 EMA50 : <b>{kl['ema_50']:.2f} TL</b>\n"
        msg += "\n"
    
    if signal.get('suggestions'):
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n💡 <b>ÖNERİLER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for sug in signal['suggestions']:
            msg += f"{sug.get('icon', '💡')} <i>{escape_html(sug.get('text', ''))}</i>\n"
        msg += "\n"
    
    if tavan_adayi:
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n⚡ <b>TAVAN ADAYI</b> ⚡\n🔴 Küçük pozisyon | 🛑 Stop'a uy\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    if holding and holding.get('strategy') and holding.get('strategy') != 'YOK':
        msg += f"⏱️ <i>{escape_html(holding.get('strategy', 'SWING'))} • Tutma: {escape_html(holding.get('duration', '2-5 gün'))}</i>\n"
    else:
        msg += f"⏱️ <i>SWING TRADE • Tutma: 2-5 gün</i>\n"
    msg += f"🤖 <i>Borsa Sinyal Bot</i>\n\n"
    
    if tavan_adayi:
        msg += f"{color}{color}{color}{special_emoji}{special_emoji}{special_emoji}{color}{color}{color}{special_emoji}{special_emoji}{special_emoji}{color}{color}{color}"
    else:
        msg += f"{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}"
    
    return msg


# ════════════════════════════════════════════════════════════
# YENİ: SAATLİK SİNYAL KARTI (Gün içi trade)
# ════════════════════════════════════════════════════════════

def format_hourly_signal(signal, signal_index=1):
    """
    SAATLİK SİNYAL KARTI
    Gün içi trade için özel tasarım
    """
    if not signal: return None
    
    t = signal.get('targets', {})
    if not t.get('entry'): return None
    
    symbol = escape_html(signal.get('symbol', '-'))
    price = signal.get('current_price', 0)
    score = signal.get('score', 0)
    score_bar = signal.get('score_bar', '░' * 20)
    stars = signal.get('stars', '⚪⚪⚪⚪⚪')
    action = escape_html(signal.get('action', '-'))
    
    # Saatlik kart için daha kısa hedefler
    entry = t.get('entry', price)
    # Gün içi hedef: daha kısa (ATR'nin yarısı)
    target_pct = t.get('target_1_pct', 3)
    stop_pct = t.get('stop_pct', 2)
    target = round(entry * (1 + target_pct / 100), 2)
    stop = round(entry * (1 - stop_pct / 100), 2)
    
    # Saatlik indikatörler
    indicators = signal.get('indicators', {})
    rsi = indicators.get('rsi')
    rvol = indicators.get('rvol')
    wt1 = indicators.get('wt1')
    wt2 = indicators.get('wt2')
    smi = indicators.get('smi')
    smi_signal_val = indicators.get('smi_signal')
    
    # KART
    msg = "⚡⚡⚡━━━━━━━━━━━━━━━━━⚡⚡⚡\n"
    msg += f"  🕐 <b>SAATLİK SİNYAL #{signal_index}</b>\n"
    msg += f"  <b>BUGÜN TRADE EDİLEBİLİR!</b>\n"
    msg += "⚡⚡⚡━━━━━━━━━━━━━━━━━⚡⚡⚡\n\n"
    
    msg += f"📌 <b>{symbol}</b> ⚡\n"
    msg += f"💰 Fiyat: <b>{price:.2f} TL</b>\n"
    msg += f"⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}\n\n"
    
    msg += f"💯 <b>SAATLİK SKOR: {score}/100</b>\n"
    msg += f"<code>{score_bar}</code>\n"
    msg += f"{stars}\n"
    msg += f"🎯 <b>{action}</b>\n\n"
    
    # SAATLİK ANALİZ
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📊 <b>SAATLİK ANALİZ</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if rsi: msg += f"⚡ RSI: <b>{rsi:.1f}</b> {'✅ İdeal' if 50 <= rsi <= 65 else '⚠️ Dikkat' if rsi > 70 else ''}\n"
    if rvol: msg += f"💥 RVOL: <b>{rvol:.1f}x</b> {'🔥 Yüksek hacim!' if rvol > 2 else ''}\n"
    if wt1 and wt2: msg += f"🌊 WT: {'✅ Pozitif' if wt1 > wt2 else '❌ Negatif'}\n"
    if smi and smi_signal_val: msg += f"📊 SMI: {'✅ Pozitif' if smi > smi_signal_val else '❌ Negatif'}\n"
    msg += "\n"
    
    # ALMA SEBEPLERİ
    if signal.get('reasons'):
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>SEBEPLER ({len(signal['reasons'])})</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for r in signal['reasons'][:6]:
            msg += f"{r.get('icon', '✅')} <b>{escape_html(r.get('title', ''))}</b>\n"
            msg += f"   → <i>{escape_html(r.get('meaning', ''))}</i>\n\n"
    
    # GÜN İÇİ PLAN
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🎯 <b>GÜN İÇİ İŞLEM PLANI</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📥 <b>GİRİŞ:</b> {entry:.2f} TL\n"
    msg += f"🎯 <b>HEDEF:</b> {target:.2f} TL (<b>+{target_pct}%</b>)\n"
    msg += f"🛑 <b>STOP:</b> {stop:.2f} TL (<b>-{stop_pct}%</b>)\n\n"
    
    # UYARILAR
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚠️ <b>GÜN İÇİ TRADE KURALLARI</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "🔴 <b>Bugün kapanışa kadar SAT!</b>\n"
    msg += "🔴 Gece TAŞIMA!\n"
    msg += "🔴 Stop'a sıkı uy\n"
    msg += "🔴 Küçük pozisyon (%3-5)\n"
    msg += "🔴 17:30'a kadar kapat\n\n"
    
    if signal.get('warnings'):
        for w in signal['warnings'][:2]:
            msg += f"{w.get('icon', '⚠️')} <b>{escape_html(w.get('title', ''))}</b>\n"
            msg += f"   💡 <b>{escape_html(w.get('action', ''))}</b>\n\n"
    
    # SEVİYELER
    kl = signal.get('key_levels', {})
    if any([kl.get('pivot'), kl.get('r1')]):
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📍 <b>SEVİYELER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        if kl.get('pivot'): msg += f"{'🟢' if price > kl['pivot'] else '🔴'} Pivot : <b>{kl['pivot']:.2f}</b>\n"
        if kl.get('r1'): msg += f"{'✅' if price > kl['r1'] else '🎯'} R1    : <b>{kl['r1']:.2f}</b>\n"
        if kl.get('r2'): msg += f"{'✅' if price > kl['r2'] else '🎯'} R2    : <b>{kl['r2']:.2f}</b>\n"
        if kl.get('s1'): msg += f"⬇️ S1    : <b>{kl['s1']:.2f}</b>\n"
        if kl.get('ema_9'): msg += f"📊 EMA9  : <b>{kl['ema_9']:.2f}</b>\n"
        msg += "\n"
    
    # ALT BİLGİ
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"⚡ <i>GÜN İÇİ TRADE • Bugün kapat!</i>\n"
    msg += f"🤖 <i>Borsa Sinyal Bot - SAATLİK</i>\n"
    msg += "⚡⚡⚡━━━━━━━━━━━━━━━━━⚡⚡⚡"
    
    return msg


# ════════════════════════════════════════════════════════════
# SİNYAL GÖNDERME
# ════════════════════════════════════════════════════════════

async def send_signal_async(signal, signal_index=1):
    msg = format_signal_for_telegram(signal, signal_index)
    if msg: return await send_message_async(msg)
    print(f"⚠️ Sinyal formatlanamadı: {signal.get('symbol', 'UNKNOWN')}")
    return False

def send_signal(signal):
    try: return asyncio.run(send_signal_async(signal, 1))
    except Exception as e:
        print(f"❌ Sinyal hatası: {e}")
        return False

async def send_multiple_signals_async(signals, max_signals=5):
    if not signals:
        await send_message_async("⚠️ <b>Şu an güçlü sinyal yok</b>")
        return 0
    
    tavan_sayisi = sum(1 for s in signals[:max_signals] if is_tavan_adayi(s))
    
    summary = f"""🔍 <b>BIST TARAMASI</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>{len(signals)}</b> güçlü sinyal bulundu
🏆 En iyi <b>{min(len(signals), max_signals)}</b> tanesi gönderiliyor
"""
    if tavan_sayisi > 0: summary += f"⚡ <b>{tavan_sayisi} TAVAN ADAYI!</b>\n"
    summary += f"\n⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}"
    
    await send_message_async(summary.strip())
    await asyncio.sleep(1.5)
    
    summary_card = format_summary_card(signals, max_signals)
    if summary_card:
        await send_message_async(summary_card)
        await asyncio.sleep(2)
    
    sent = 0
    for i, signal in enumerate(signals[:max_signals], 1):
        success = await send_signal_async(signal, signal_index=i)
        if success: sent += 1
        await asyncio.sleep(2)
    return sent

def send_multiple_signals(signals, max_signals=5):
    try: return asyncio.run(send_multiple_signals_async(signals, max_signals))
    except Exception as e:
        print(f"❌ Çoklu sinyal hatası: {e}")
        return 0


# ════════════════════════════════════════════════════════════
# YENİ: SAATLİK SİNYALLERİ GÖNDERME
# ════════════════════════════════════════════════════════════

async def send_hourly_signals_async(signals, max_signals=3):
    """Saatlik sinyalleri özel kart ile gönder"""
    if not signals: return 0
    
    # Saatlik özet
    summary = f"""⚡⚡⚡ <b>SAATLİK TARAMA</b> ⚡⚡⚡
━━━━━━━━━━━━━━━━━━━━━━━

🕐 <b>{len(signals)}</b> gün içi trade fırsatı!
📊 En iyi <b>{min(len(signals), max_signals)}</b> tanesi gönderiliyor

⚠️ <i>Bunlar GÜN İÇİ trade sinyalleri!</i>
⚠️ <i>Bugün kapanışa kadar SAT!</i>

⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}
"""
    await send_message_async(summary.strip())
    await asyncio.sleep(1.5)
    
    sent = 0
    for i, signal in enumerate(signals[:max_signals], 1):
        msg = format_hourly_signal(signal, signal_index=i)
        if msg:
            success = await send_message_async(msg)
            if success: sent += 1
            await asyncio.sleep(2)
    
    return sent

def send_hourly_signals(signals, max_signals=3):
    """Senkron saatlik sinyal gönderme"""
    try: return asyncio.run(send_hourly_signals_async(signals, max_signals))
    except Exception as e:
        print(f"❌ Saatlik sinyal hatası: {e}")
        return 0


# ════════════════════════════════════════════════════════════
# ÖZEL UYARILAR
# ════════════════════════════════════════════════════════════

def send_target_hit_alert(symbol, target_num, entry_price, target_price, current_price):
    profit_pct = ((current_price - entry_price) / entry_price) * 100
    symbol = escape_html(symbol)
    msg = f"""🎯 <b>HEDEF {target_num}'E ULAŞILDI!</b>
━━━━━━━━━━━━━━━━━━━━━━━
📌 <b>{symbol}</b>
📥 Alış: {entry_price:.2f} TL
💰 Şu an: {current_price:.2f} TL
✅ Kâr: <b>+{profit_pct:.2f}%</b>\n\n💡 <b>ÖNERİ:</b>\n"""
    if target_num == 1: msg += "• %33 SAT\n• Stop'u girişe çek"
    elif target_num == 2: msg += "• %33 daha SAT\n• Stop'u H1'e çek"
    else: msg += "• Kalanı SAT\n• Kâr kilitle"
    return send_message(msg)

def send_stop_warning(symbol, entry_price, current_price, stop_loss):
    loss_pct = ((current_price - entry_price) / entry_price) * 100
    distance = ((current_price - stop_loss) / current_price) * 100
    msg = f"""⚠️ <b>STOP YAKLAŞIYOR!</b>
━━━━━━━━━━━━━━━━━━━━━━━
📌 <b>{escape_html(symbol)}</b>
📥 Alış: {entry_price:.2f} TL
💰 Şu an: {current_price:.2f} TL
🛑 Stop: {stop_loss:.2f} TL
📉 Zarar: <b>{loss_pct:.2f}%</b>
📏 Stop'a: <b>{distance:.2f}%</b> kaldı
💡 {stop_loss:.2f} TL altına inerse <b>HEMEN SAT!</b>"""
    return send_message(msg)

def send_momentum_warning(symbol, current_price, entry_price, reason):
    profit_pct = ((current_price - entry_price) / entry_price) * 100
    msg = f"""⚠️ <b>MOMENTUM ZAYIFLIYOR</b>
━━━━━━━━━━━━━━━━━━━━━━━
📌 <b>{escape_html(symbol)}</b>
📥 Alış: {entry_price:.2f} TL
💰 Şu an: {current_price:.2f} TL
📊 Durum: <b>{profit_pct:+.2f}%</b>
⚠️ {escape_html(reason)}"""
    if profit_pct > 0: msg += "\n💡 Kısmi satış düşün"
    else: msg += "\n💡 Pozisyonu izle"
    return send_message(msg)


# ════════════════════════════════════════════════════════════
# TEST
# ════════════════════════════════════════════════════════════

async def send_test_message_async():
    msg = f"""🎉 <b>BORSA SİNYAL BOT</b>
━━━━━━━━━━━━━━━━━━━━━━━
✅ Bot bağlantısı başarılı

🎯 <b>ÖZELLİKLER:</b>
• SWING sinyalleri (1-5 gün)
• ⚡ SAATLİK sinyaller (gün içi) YENİ!
• Tavan adayı tespiti
• Sinyal takip
• WaveTrend + SMI

⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}"""
    return await send_message_async(msg.strip())

def send_test_message():
    try: return asyncio.run(send_test_message_async())
    except: return False


if __name__ == "__main__":
    print("🤖 BOT TEST")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Token/ChatID eksik!")
        sys.exit(1)
    
    print("1 → Test mesajı")
    print("2 → Mevcut verilerle tara")
    choice = input("Seçim: ").strip()
    
    if choice == "1":
        if send_test_message(): print("✅ Gönderildi!")
    elif choice == "2":
        import pandas as pd
        from database import get_stock_history
        from services.analyzer import analyze_stock
        from services.signal_engine import generate_signal
        
        test_symbols = ["AKBNK.IS", "THYAO.IS", "ASELS.IS"]
        signals = []
        for symbol in test_symbols:
            data = get_stock_history(symbol, days=300)
            if data:
                df = pd.DataFrame(data)
                analysis = analyze_stock(df)
                if analysis:
                    signal = generate_signal(symbol, analysis, df)
                    if signal and signal['score'] >= 50:
                        signals.append(signal)
        if signals:
            signals.sort(key=lambda x: x['score'], reverse=True)
            sent = send_multiple_signals(signals, max_signals=3)
            print(f"✅ {sent} mesaj gönderildi!")
