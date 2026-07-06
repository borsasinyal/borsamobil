"""
Telegram Bot - SWING + SAATLİK + Tavan Adayı
Sıkılaştırılmış tavan tespiti + Giriş uyarısı
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
def tr_now(): return datetime.now(TR_TIMEZONE)

def escape_html(text):
    if text is None: return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def get_signal_color(i):
    return {1:'🟢',2:'🔵',3:'🟣',4:'🟡',5:'🟠'}.get(i,'⚪')

def get_medal_emoji(r):
    return {1:'🥇',2:'🥈',3:'🥉',4:'🏅',5:'🎖️'}.get(r,f"{r}.")

def is_tavan_adayi(signal):
    """
    SIKI TAVAN TESPİTİ
    SADECE gerçek tavan adayları:
    - "TAVAN ADAYI" başlığı olanlar (%5-8 yükseliş + hacim)
    - "GÜN İÇİ PATLAMA" başlığı olanlar (intraday %8+)
    """
    if not signal or not signal.get('reasons'): return False
    for r in signal['reasons']:
        title = r.get('title', '').upper()
        if 'TAVAN ADAYI' in title: return True
        if 'GÜN İÇİ PATLAMA' in title: return True
    return False

def get_bot():
    if not TELEGRAM_BOT_TOKEN: raise ValueError("TOKEN boş!")
    if not TELEGRAM_CHAT_ID: raise ValueError("CHAT_ID boş!")
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
                else: current_chunk += line + '\n'
            if current_chunk: chunks.append(current_chunk)
            for i, chunk in enumerate(chunks):
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk, parse_mode=parse_mode, disable_web_page_preview=True)
                if i < len(chunks)-1: await asyncio.sleep(0.5)
            return True
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=parse_mode, disable_web_page_preview=True)
        return True
    except Exception as e:
        print(f"❌ Mesaj hatası: {e}")
        try: await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⚠️ Hata: {str(e)[:200]}", disable_web_page_preview=True)
        except: pass
        return False

def send_message(text):
    try: return asyncio.run(send_message_async(text))
    except: return False


# ════════════════════════════════════════════════════════════
# ÖZET KART (Top 5 SWING)
# ════════════════════════════════════════════════════════════

def format_summary_card(signals, max_signals=5):
    if not signals: return None
    top = signals[:max_signals]
    tavan = sum(1 for s in top if is_tavan_adayi(s))
    
    msg = "🏆🏆🏆━━━━━━━━━━━━━━━━━🏆🏆🏆\n"
    msg += f"      <b>EN İYİ {len(top)} SWING SİNYAL</b>\n"
    if tavan > 0: msg += f"      ⚡ {tavan} TAVAN ADAYI VAR!\n"
    msg += "🏆🏆🏆━━━━━━━━━━━━━━━━━🏆🏆🏆\n\n"
    
    for i, s in enumerate(top, 1):
        sym = escape_html(s.get('symbol','-'))
        sc = s.get('score',0)
        pr = s.get('current_price',0)
        t = s.get('targets',{})
        t1 = t.get('target_1',0)
        t1p = t.get('target_1_pct',0)
        medal = get_medal_emoji(i)
        tv = " ⚡" if is_tavan_adayi(s) else ""
        
        if sc >= 85: stars = "⭐⭐⭐⭐⭐"
        elif sc >= 75: stars = "⭐⭐⭐⭐"
        elif sc >= 65: stars = "⭐⭐⭐"
        else: stars = "⭐⭐"
        
        bar = "█" * int(sc/10) + "░" * (10 - int(sc/10))
        msg += f"{medal} <b>{sym}</b>{tv} {stars}\n"
        msg += f"   💯 <b>{sc}/100</b> <code>{bar}</code>\n"
        msg += f"   💰 {pr:.2f} → 🎯 <b>{t1:.2f}</b> (<b>+{t1p}%</b>)\n\n"
    
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}\n📩 <i>Detaylı kartlar geliyor...</i>"
    return msg


# ════════════════════════════════════════════════════════════
# SWING SİNYAL KARTI (Renkli çerçeve + Giriş uyarısı)
# ════════════════════════════════════════════════════════════

def format_signal_for_telegram(signal, signal_index=1):
    if not signal: return None
    
    required = ['emoji','label','symbol','current_price','score','score_bar','stars','confidence','action','targets']
    for f in required:
        if signal.get(f) is None: return None
    
    t = signal['targets']
    for f in ['entry','target_1','target_2','target_3','stop_loss','target_1_pct','target_2_pct','target_3_pct','stop_pct','risk_reward']:
        if t.get(f) is None: return None
    
    emoji = signal['emoji']
    label = escape_html(signal['label'])
    symbol = escape_html(signal['symbol'])
    price = signal['current_price']
    score = signal['score']
    score_bar = signal['score_bar']
    stars = signal['stars']
    confidence = escape_html(signal['confidence'])
    action = escape_html(signal['action'])
    risk_level = escape_html(signal.get('risk_level','-'))
    holding = signal.get('holding',{})
    
    tavan = is_tavan_adayi(signal)
    
    if tavan:
        color = "🔴"; se = "⚡"; te = " - ⚡ TAVAN ADAYI!"
    else:
        color = get_signal_color(signal_index); se = ""; te = ""
    
    medal = get_medal_emoji(signal_index)
    
    # ÇERÇEVE ÜST
    if tavan:
        msg = f"{color}{color}{color}{se}{se}{se}{color}{color}{color}{se}{se}{se}{color}{color}{color}\n"
        msg += f"     {medal} <b>SİNYAL #{signal_index}{te}</b>\n"
        msg += f"{color}{color}{color}{se}{se}{se}{color}{color}{color}{se}{se}{se}{color}{color}{color}\n\n"
        msg += "⚡⚡⚡ <b>TAVAN ADAYI!</b> ⚡⚡⚡\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🚀 Hacim destekli güçlü yükseliş!\n⚠️ <b>RİSKLİ</b> - Küçük pozisyon\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    else:
        msg = f"{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}\n"
        msg += f"     {medal} <b>SİNYAL #{signal_index}</b>\n"
        msg += f"{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}\n\n"
    
    # BAŞLIK
    msg += f"{emoji} <b>{label}</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📌 <b>{symbol}</b>{'⚡' if tavan else ''}\n💰 Fiyat: <b>{price:.2f} TL</b>\n⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}\n\n"
    
    # SKOR
    msg += f"💯 <b>SKOR: {score}/100</b>\n<code>{score_bar}</code>\n{stars}\n📊 <i>{confidence}</i>\n🎯 <b>{action}</b>\n\n"
    
    # STRATEJİ
    if holding and holding.get('strategy') and holding.get('strategy') != 'YOK':
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📋 <b>STRATEJİ</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"⚡ <b>Tip:</b> {escape_html(holding.get('strategy',''))}\n"
        if holding.get('duration','-') != '-': msg += f"📅 <b>Tutma:</b> {escape_html(holding['duration'])}\n"
        msg += f"🎲 <b>Risk:</b> {risk_level}\n"
        if holding.get('reason'): msg += f"💡 <i>{escape_html(holding['reason'])}</i>\n"
        msg += "\n"
    
    # İŞLEM PLANI
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n💼 <b>İŞLEM PLANI - 3 HEDEF</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📥 <b>GİRİŞ:</b> {t['entry']:.2f} TL\n"
    msg += f"   ⚠️ <i>Fiyat bundan %2+ yukarıdaysa GİRME!</i>\n\n"
    
    h1 = "1-2 gün" if score >= 85 else "2-3 gün" if score >= 75 else "2-4 gün"
    h2 = "2-3 gün" if score >= 85 else "3-4 gün" if score >= 75 else "3-5 gün"
    h3 = "3-5 gün" if score >= 85 else "4-7 gün" if score >= 75 else "5-10 gün"
    
    msg += f"🎯 <b>H1:</b> {t['target_1']:.2f} TL <b>(+{t['target_1_pct']}%)</b>\n   ⏰ <i>{h1}</i> | 💡 <i>%33 sat</i>\n\n"
    msg += f"🎯 <b>H2:</b> {t['target_2']:.2f} TL <b>(+{t['target_2_pct']}%)</b>\n   ⏰ <i>{h2}</i> | 💡 <i>%33 sat</i>\n\n"
    msg += f"🎯 <b>H3:</b> {t['target_3']:.2f} TL <b>(+{t['target_3_pct']}%)</b>\n   ⏰ <i>{h3}</i> | 💡 <i>Kalanı sat</i>\n\n"
    msg += f"🛑 <b>STOP:</b> {t['stop_loss']:.2f} TL <b>(-{t['stop_pct']}%)</b>\n⚖️ <b>R/Ö:</b> 1/{t['risk_reward']}\n\n"
    
    # SEBEPLER
    if signal.get('reasons'):
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>SEBEPLER ({len(signal['reasons'])})</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for r in signal['reasons']:
            msg += f"{r.get('icon','✅')} <b>{escape_html(r.get('title',''))}</b>\n   → <i>{escape_html(r.get('meaning',''))}</i>\n\n"
    
    # UYARILAR
    if signal.get('warnings'):
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n⚠️ <b>UYARILAR</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for w in signal['warnings']:
            msg += f"{w.get('icon','⚠️')} <b>{escape_html(w.get('title',''))}</b>\n   💡 <b>{escape_html(w.get('action',''))}</b>\n\n"
    
    # PUAN DAĞILIMI
    b = signal['breakdown']
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📊 <b>PUAN DAĞILIMI</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💥 Hacim     : <b>{b['volume']['score']}/{b['volume']['max']}</b>\n"
    msg += f"⚡ Momentum  : <b>{b['momentum']['score']}/{b['momentum']['max']}</b>\n"
    msg += f"📈 Trend     : <b>{b['trend']['score']}/{b['trend']['max']}</b>\n"
    msg += f"🌊 WaveTrend : <b>{b['wavetrend']['score']}/{b['wavetrend']['max']}</b>\n"
    msg += f"🎯 Pivot     : <b>{b['vwap_pivot']['score']}/{b['vwap_pivot']['max']}</b>\n"
    msg += f"🚀 Kırılım   : <b>{b['breakout_candle']['score']}/{b['breakout_candle']['max']}</b>\n"
    msg += f"💧 Likidite  : <b>{b['liquidity']['score']}/{b['liquidity']['max']}</b>\n\n"
    
    # SEVİYELER
    kl = signal.get('key_levels',{})
    if any([kl.get('pivot'),kl.get('r1'),kl.get('ema_9')]):
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📍 <b>SEVİYELER</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        if kl.get('pivot'): msg += f"{'🟢' if price>kl['pivot'] else '🔴'} Pivot : <b>{kl['pivot']:.2f}</b>\n"
        if kl.get('r1'): msg += f"{'✅' if price>kl['r1'] else '🎯'} R1    : <b>{kl['r1']:.2f}</b>\n"
        if kl.get('r2'): msg += f"{'✅' if price>kl['r2'] else '🎯'} R2    : <b>{kl['r2']:.2f}</b>\n"
        if kl.get('r3'): msg += f"{'✅' if price>kl['r3'] else '🎯'} R3    : <b>{kl['r3']:.2f}</b>\n"
        if kl.get('s1'): msg += f"⬇️ S1    : <b>{kl['s1']:.2f}</b>\n"
        if kl.get('ema_9'): msg += f"📊 EMA9  : <b>{kl['ema_9']:.2f}</b>\n"
        if kl.get('ema_21'): msg += f"📊 EMA21 : <b>{kl['ema_21']:.2f}</b>\n"
        if kl.get('ema_50'): msg += f"📊 EMA50 : <b>{kl['ema_50']:.2f}</b>\n"
        msg += "\n"
    
    # ALT
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    if holding and holding.get('strategy') and holding.get('strategy') != 'YOK':
        msg += f"⏱️ <i>{escape_html(holding.get('strategy','SWING'))} • {escape_html(holding.get('duration','2-5 gün'))}</i>\n"
    else: msg += "⏱️ <i>SWING TRADE • 2-5 gün</i>\n"
    msg += "🤖 <i>Borsa Sinyal Bot</i>\n\n"
    
    if tavan: msg += f"{color}{color}{color}{se}{se}{se}{color}{color}{color}{se}{se}{se}{color}{color}{color}"
    else: msg += f"{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}{color}"
    
    return msg


# ════════════════════════════════════════════════════════════
# SAATLİK SİNYAL KARTI
# ════════════════════════════════════════════════════════════

def format_hourly_signal(signal, signal_index=1):
    if not signal: return None
    t = signal.get('targets',{})
    if not t.get('entry'): return None
    
    symbol = escape_html(signal.get('symbol','-'))
    price = signal.get('current_price',0)
    score = signal.get('score',0)
    score_bar = signal.get('score_bar','░'*20)
    stars = signal.get('stars','⚪⚪⚪⚪⚪')
    action = escape_html(signal.get('action','-'))
    
    entry = t.get('entry', price)
    target_pct = t.get('target_1_pct', 3)
    stop_pct = t.get('stop_pct', 2)
    target = round(entry * (1 + target_pct/100), 2)
    stop = round(entry * (1 - stop_pct/100), 2)
    
    ind = signal.get('indicators',{})
    
    msg = "⚡⚡⚡━━━━━━━━━━━━━━━━━⚡⚡⚡\n"
    msg += f"  🕐 <b>SAATLİK SİNYAL #{signal_index}</b>\n"
    msg += f"  <b>BUGÜN TRADE EDİLEBİLİR!</b>\n"
    msg += "⚡⚡⚡━━━━━━━━━━━━━━━━━⚡⚡⚡\n\n"
    
    msg += f"📌 <b>{symbol}</b> ⚡\n💰 <b>{price:.2f} TL</b>\n⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}\n\n"
    msg += f"💯 <b>SAATLİK SKOR: {score}/100</b>\n<code>{score_bar}</code>\n{stars}\n🎯 <b>{action}</b>\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📊 <b>SAATLİK ANALİZ</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    if ind.get('rsi'): msg += f"⚡ RSI: <b>{ind['rsi']:.1f}</b> {'✅' if 50<=ind['rsi']<=65 else '⚠️' if ind['rsi']>70 else ''}\n"
    if ind.get('rvol'): msg += f"💥 RVOL: <b>{ind['rvol']:.1f}x</b> {'🔥' if ind['rvol']>2 else ''}\n"
    if ind.get('wt1') and ind.get('wt2'): msg += f"🌊 WT: {'✅ Pozitif' if ind['wt1']>ind['wt2'] else '❌'}\n"
    if ind.get('smi') and ind.get('smi_signal'): msg += f"📊 SMI: {'✅ Pozitif' if ind['smi']>ind['smi_signal'] else '❌'}\n"
    msg += "\n"
    
    if signal.get('reasons'):
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>SEBEPLER ({len(signal['reasons'])})</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for r in signal['reasons'][:6]:
            msg += f"{r.get('icon','✅')} <b>{escape_html(r.get('title',''))}</b>\n   → <i>{escape_html(r.get('meaning',''))}</i>\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n🎯 <b>GÜN İÇİ PLAN</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📥 <b>GİRİŞ:</b> {entry:.2f} TL\n"
    msg += f"   ⚠️ <i>Fiyat bundan %2+ yukarıdaysa GİRME!</i>\n"
    msg += f"🎯 <b>HEDEF:</b> {target:.2f} TL (<b>+{target_pct}%</b>)\n"
    msg += f"🛑 <b>STOP:</b> {stop:.2f} TL (<b>-{stop_pct}%</b>)\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n⚠️ <b>GÜN İÇİ KURALLAR</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "🔴 Bugün kapanışa kadar SAT!\n🔴 Gece TAŞIMA!\n🔴 Stop'a sıkı uy\n🔴 17:30'a kadar kapat\n\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n⚡ <i>GÜN İÇİ TRADE • Bugün kapat!</i>\n🤖 <i>Borsa Sinyal Bot - SAATLİK</i>\n"
    msg += "⚡⚡⚡━━━━━━━━━━━━━━━━━⚡⚡⚡"
    return msg


# ════════════════════════════════════════════════════════════
# GÖNDERME FONKSİYONLARI
# ════════════════════════════════════════════════════════════

async def send_signal_async(signal, signal_index=1):
    msg = format_signal_for_telegram(signal, signal_index)
    if msg: return await send_message_async(msg)
    return False

def send_signal(signal):
    try: return asyncio.run(send_signal_async(signal, 1))
    except: return False

async def send_multiple_signals_async(signals, max_signals=5):
    if not signals:
        await send_message_async("⚠️ <b>Sinyal yok</b>")
        return 0
    
    tavan = sum(1 for s in signals[:max_signals] if is_tavan_adayi(s))
    summary = f"🔍 <b>BIST TARAMASI</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n📊 <b>{len(signals)}</b> sinyal bulundu\n🏆 En iyi <b>{min(len(signals),max_signals)}</b> gönderiliyor\n"
    if tavan > 0: summary += f"⚡ <b>{tavan} TAVAN ADAYI!</b>\n"
    summary += f"\n⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}"
    
    await send_message_async(summary.strip())
    await asyncio.sleep(1.5)
    
    card = format_summary_card(signals, max_signals)
    if card:
        await send_message_async(card)
        await asyncio.sleep(2)
    
    sent = 0
    for i, s in enumerate(signals[:max_signals], 1):
        if await send_signal_async(s, signal_index=i): sent += 1
        await asyncio.sleep(2)
    return sent

def send_multiple_signals(signals, max_signals=5):
    try: return asyncio.run(send_multiple_signals_async(signals, max_signals))
    except: return 0

async def send_hourly_signals_async(signals, max_signals=3):
    if not signals: return 0
    summary = f"⚡⚡⚡ <b>SAATLİK TARAMA</b> ⚡⚡⚡\n━━━━━━━━━━━━━━━━━━━━━━━\n🕐 <b>{len(signals)}</b> gün içi fırsat!\n⚠️ <i>Bugün kapanışa kadar SAT!</i>\n\n⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}"
    await send_message_async(summary.strip())
    await asyncio.sleep(1.5)
    sent = 0
    for i, s in enumerate(signals[:max_signals], 1):
        msg = format_hourly_signal(s, signal_index=i)
        if msg:
            if await send_message_async(msg): sent += 1
            await asyncio.sleep(2)
    return sent

def send_hourly_signals(signals, max_signals=3):
    try: return asyncio.run(send_hourly_signals_async(signals, max_signals))
    except: return 0


# ════════════════════════════════════════════════════════════
# ÖZEL UYARILAR
# ════════════════════════════════════════════════════════════

def send_target_hit_alert(symbol, target_num, entry_price, target_price, current_price):
    pct = ((current_price - entry_price) / entry_price) * 100
    msg = f"🎯 <b>HEDEF {target_num} VURDU!</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n📌 <b>{escape_html(symbol)}</b>\n📥 Alış: {entry_price:.2f}\n💰 Şuan: {current_price:.2f}\n✅ Kâr: <b>+{pct:.2f}%</b>\n\n💡 "
    if target_num == 1: msg += "%33 SAT, stop'u girişe çek"
    elif target_num == 2: msg += "%33 SAT, stop'u H1'e çek"
    else: msg += "Kalanı SAT, kâr kilitle"
    return send_message(msg)

def send_stop_warning(symbol, entry_price, current_price, stop_loss):
    loss = ((current_price - entry_price) / entry_price) * 100
    dist = ((current_price - stop_loss) / current_price) * 100
    msg = f"⚠️ <b>STOP YAKLAŞIYOR!</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n📌 <b>{escape_html(symbol)}</b>\n📥 Alış: {entry_price:.2f}\n💰 Şuan: {current_price:.2f}\n🛑 Stop: {stop_loss:.2f}\n📉 Zarar: <b>{loss:.2f}%</b>\n📏 Stop'a: <b>{dist:.2f}%</b>\n💡 {stop_loss:.2f} altında <b>HEMEN SAT!</b>"
    return send_message(msg)

def send_momentum_warning(symbol, current_price, entry_price, reason):
    pct = ((current_price - entry_price) / entry_price) * 100
    msg = f"⚠️ <b>MOMENTUM ZAYIFLIYOR</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n📌 <b>{escape_html(symbol)}</b>\n📥 Alış: {entry_price:.2f}\n💰 Şuan: {current_price:.2f}\n📊 Durum: <b>{pct:+.2f}%</b>\n⚠️ {escape_html(reason)}"
    if pct > 0: msg += "\n💡 Kısmi satış düşün"
    else: msg += "\n💡 Pozisyonu izle"
    return send_message(msg)


# ════════════════════════════════════════════════════════════
# TEST
# ════════════════════════════════════════════════════════════

async def send_test_message_async():
    msg = f"🎉 <b>BOT AKTİF</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n✅ SWING + SAATLİK sinyaller\n⚡ Tavan adayı tespiti (sıkılaştırılmış)\n📊 Giriş noktası uyarısı\n⏰ {tr_now().strftime('%H:%M - %d.%m.%Y')}"
    return await send_message_async(msg)

def send_test_message():
    try: return asyncio.run(send_test_message_async())
    except: return False


if __name__ == "__main__":
    print("1 → Test mesajı")
    c = input("Seçim: ").strip()
    if c == "1":
        if send_test_message(): print("✅ Gönderildi!")
