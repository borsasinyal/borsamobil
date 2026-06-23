"""
Telegram Bot - Profesyonel Sinyal Gönderici
SWING TRADE optimized + VWAP kaldırıldı + Tutma süresi önerisi
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


# ════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ════════════════════════════════════════════════════════════

def escape_html(text):
    """HTML özel karakterlerini escape et - Telegram parse hatasını önler"""
    if text is None:
        return ""
    text = str(text)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ════════════════════════════════════════════════════════════
# BOT BAĞLANTI
# ════════════════════════════════════════════════════════════

def get_bot():
    """Bot örneğini döndür"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("❌ TELEGRAM_BOT_TOKEN config.py'de boş!")
    if not TELEGRAM_CHAT_ID:
        raise ValueError("❌ TELEGRAM_CHAT_ID config.py'de boş!")
    return Bot(token=TELEGRAM_BOT_TOKEN)


# ════════════════════════════════════════════════════════════
# MESAJ GÖNDERME
# ════════════════════════════════════════════════════════════

async def send_message_async(text, parse_mode=ParseMode.HTML):
    """Telegram'a mesaj gönder - Uzunluk kontrolü + Hata yakalama"""
    bot = get_bot()
    try:
        # Uzunluk kontrolü (Telegram limit: 4096)
        if len(text) > 4096:
            print(f"⚠️ MESAJ ÇOK UZUN: {len(text)} karakter, parçalanıyor...")
            chunks = []
            current_chunk = ""
            for line in text.split('\n'):
                if len(current_chunk) + len(line) + 1 > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            if current_chunk:
                chunks.append(current_chunk)
            
            for i, chunk in enumerate(chunks):
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=chunk,
                    parse_mode=parse_mode,
                    disable_web_page_preview=True
                )
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.5)
            return True
        
        # Normal gönderim
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=True
        )
        return True
    
    except Exception as e:
        print(f"❌ MESAJ GÖNDERME HATASI")
        print(f"   Hata: {str(e)}")
        print(f"   Mesaj uzunluğu: {len(text)} karakter")
        
        # Fallback: Plain text dene
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"⚠️ Format hatası!\n\nHata: {str(e)[:200]}",
                disable_web_page_preview=True
            )
        except:
            pass
        return False


def send_message(text):
    """Senkron mesaj gönderme"""
    try:
        return asyncio.run(send_message_async(text))
    except Exception as e:
        print(f"❌ Mesaj hatası: {e}")
        return False


# ════════════════════════════════════════════════════════════
# PROFESYONEL SİNYAL FORMATLAMA - SWING OPTIMIZED
# ════════════════════════════════════════════════════════════

def format_signal_for_telegram(signal):
    """
    Sinyali Telegram için HTML formatında hazırla
    SWING optimized + VWAP kaldırıldı + Tutma süresi
    """
    if not signal:
        print("❌ Sinyal None geldi!")
        return None
    
    # None koruması
    required = ['emoji', 'label', 'symbol', 'current_price', 'score', 
                'score_bar', 'stars', 'confidence', 'action', 'targets']
    for field in required:
        if signal.get(field) is None:
            print(f"❌ EKSİK ALAN: '{field}' is None")
            return None
    
    # Targets kontrolü
    t = signal['targets']
    target_required = ['entry', 'target_1', 'target_2', 'target_3', 
                       'stop_loss', 'target_1_pct', 'target_2_pct',
                       'target_3_pct', 'stop_pct', 'risk_reward']
    for field in target_required:
        if t.get(field) is None:
            print(f"❌ TARGET EKSİK: '{field}' is None")
            return None
    
    # Veriler (HTML escape ile)
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
    
    # ── BAŞLIK ──
    msg = f"{emoji} <b>{label}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # ── HİSSE BİLGİSİ ──
    msg += f"📌 <b>{symbol}</b>\n"
    msg += f"💰 Fiyat: <b>{price:.2f} TL</b>\n"
    msg += f"⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}\n\n"
    
    # ── SKOR ──
    msg += f"💯 <b>SKOR: {score}/100</b>\n"
    msg += f"<code>{score_bar}</code>\n"
    msg += f"{stars}\n"
    msg += f"📊 <i>{confidence}</i>\n"
    msg += f"🎯 <b>{action}</b>\n\n"
    
    # ── STRATEJİ VE TUTMA SÜRESİ ──
    if holding and holding.get('strategy') and holding.get('strategy') != 'YOK':
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📋 <b>STRATEJİ ÖNERİSİ</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"⚡ <b>Tip:</b> {escape_html(holding.get('strategy', ''))}\n"
        if holding.get('duration', '-') != '-':
            msg += f"📅 <b>Tutma:</b> {escape_html(holding['duration'])}\n"
        msg += f"🎲 <b>Risk:</b> {risk_level}\n"
        if holding.get('reason'):
            msg += f"💡 <i>{escape_html(holding['reason'])}</i>\n"
        msg += "\n"
    
    # ── İŞLEM PLANI ──
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💼 <b>İŞLEM PLANI - 3 HEDEF</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # ── GİRİŞ ──
    msg += f"📥 <b>GİRİŞ:</b> {t['entry']:.2f} TL\n\n"
    
    # ── HEDEF 1 ──
    h1_days = "1-2 gün" if score >= 85 else "2-3 gün" if score >= 75 else "2-4 gün"
    msg += f"🎯 <b>HEDEF 1:</b> {t['target_1']:.2f} TL "
    msg += f"<b>(+{t['target_1_pct']}%)</b>\n"
    msg += f"   ⏰ <i>{h1_days}'de olası</i>\n"
    msg += f"   💡 <i>%33 sat, stop'u girişe çek</i>\n\n"
    
    # ── HEDEF 2 ──
    h2_days = "2-3 gün" if score >= 85 else "3-4 gün" if score >= 75 else "3-5 gün"
    msg += f"🎯 <b>HEDEF 2:</b> {t['target_2']:.2f} TL "
    msg += f"<b>(+{t['target_2_pct']}%)</b>\n"
    msg += f"   ⏰ <i>{h2_days}'de olası</i>\n"
    msg += f"   💡 <i>%33 sat, stop'u Hedef 1'e çek</i>\n\n"
    
    # ── HEDEF 3 ──
    h3_days = "3-5 gün" if score >= 85 else "4-7 gün" if score >= 75 else "5-10 gün"
    msg += f"🎯 <b>HEDEF 3:</b> {t['target_3']:.2f} TL "
    msg += f"<b>(+{t['target_3_pct']}%)</b>\n"
    msg += f"   ⏰ <i>{h3_days}'de olası</i>\n"
    msg += f"   💡 <i>Kalanı sat (trend kırılırsa)</i>\n\n"
    
    # ── STOP ──
    msg += f"🛑 <b>STOP-LOSS:</b> {t['stop_loss']:.2f} TL "
    msg += f"<b>(-{t['stop_pct']}%)</b>\n"
    msg += f"⚖️ <b>Risk/Ödül:</b> 1 / {t['risk_reward']}\n\n"
    
    # ── ALMA SEBEPLERİ ──
    if signal.get('reasons'):
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"✅ <b>ALMA SEBEPLERİ ({len(signal['reasons'])})</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for r in signal['reasons']:
            icon = r.get('icon', '✅')
            title = escape_html(r.get('title', ''))
            detail = escape_html(r.get('detail', ''))
            meaning = escape_html(r.get('meaning', ''))
            msg += f"{icon} <b>{title}</b>\n"
            msg += f"   📌 {detail}\n"
            msg += f"   → <i>{meaning}</i>\n\n"
    
    # ── UYARILAR ──
    if signal.get('warnings'):
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"⚠️ <b>UYARILAR ({len(signal['warnings'])})</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for w in signal['warnings']:
            icon = w.get('icon', '⚠️')
            title = escape_html(w.get('title', ''))
            detail = escape_html(w.get('detail', ''))
            action_txt = escape_html(w.get('action', ''))
            msg += f"{icon} <b>{title}</b>\n"
            msg += f"   📌 {detail}\n"
            msg += f"   💡 <b>{action_txt}</b>\n\n"
    
    # ── KIRILIMLAR ──
    if signal.get('breakouts'):
        up_breakouts = [b for b in signal['breakouts'] if b.get('type') == 'UP']
        if up_breakouts:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "🚀 <b>KIRILIMLAR</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for br in up_breakouts:
                icon = br.get('icon', '🚀')
                detail = escape_html(br.get('detail', ''))
                meaning = escape_html(br.get('meaning', ''))
                msg += f"{icon} <b>{detail}</b>\n"
                msg += f"   → <i>{meaning}</i>\n\n"
    
    # ── MUM FORMASYONLARI ──
    if signal.get('candle_patterns'):
        patterns = signal['candle_patterns'][:3]
        if patterns:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "🕯️ <b>MUM FORMASYONLARI</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for cp in patterns:
                icon = cp.get('icon', '🕯️')
                name = escape_html(cp.get('name', ''))
                meaning = escape_html(cp.get('meaning', ''))
                msg += f"{icon} <b>{name}</b>\n"
                msg += f"   → <i>{meaning}</i>\n\n"
    
    # ── PUAN DAĞILIMI ──
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📊 <b>PUAN DAĞILIMI</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    b = signal['breakdown']
    msg += f"💥 Hacim       : <b>{b['volume']['score']}/{b['volume']['max']}</b>\n"
    msg += f"⚡ Momentum    : <b>{b['momentum']['score']}/{b['momentum']['max']}</b>\n"
    msg += f"📈 Trend       : <b>{b['trend']['score']}/{b['trend']['max']}</b>\n"
    msg += f"🎯 Pivot Point : <b>{b['vwap_pivot']['score']}/{b['vwap_pivot']['max']}</b>\n"
    msg += f"🚀 Kırılım/Mum : <b>{b['breakout_candle']['score']}/{b['breakout_candle']['max']}</b>\n"
    msg += f"💧 Likidite    : <b>{b['liquidity']['score']}/{b['liquidity']['max']}</b>\n\n"
    
    # ── ÖNEMLİ SEVİYELER ──
    kl = signal.get('key_levels', {})
    has_levels = any([kl.get('pivot'), kl.get('ema_9'), kl.get('r1')])
    
    if has_levels:
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📍 <b>ÖNEMLİ SEVİYELER</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Pivot Points
        if kl.get('pivot'):
            arrow_pivot = "🟢" if price > kl['pivot'] else "🔴"
            msg += f"{arrow_pivot} Pivot   : <b>{kl['pivot']:.2f} TL</b>\n"
        if kl.get('r1'):
            arrow_r1 = "✅" if price > kl['r1'] else "🎯"
            msg += f"{arrow_r1} R1      : <b>{kl['r1']:.2f} TL</b>\n"
        if kl.get('r2'):
            arrow_r2 = "✅" if price > kl['r2'] else "🎯"
            msg += f"{arrow_r2} R2      : <b>{kl['r2']:.2f} TL</b>\n"
        if kl.get('r3'):
            arrow_r3 = "✅" if price > kl['r3'] else "🎯"
            msg += f"{arrow_r3} R3      : <b>{kl['r3']:.2f} TL</b>\n"
        if kl.get('s1'):
            msg += f"⬇️ S1      : <b>{kl['s1']:.2f} TL</b>\n"
        
        # EMA değerleri
        if kl.get('ema_9'):
            msg += f"📊 EMA 9   : <b>{kl['ema_9']:.2f} TL</b>\n"
        if kl.get('ema_21'):
            msg += f"📊 EMA 21  : <b>{kl['ema_21']:.2f} TL</b>\n"
        
        # Dün
        if kl.get('prev_day_high'):
            msg += f"📈 Dün H   : <b>{kl['prev_day_high']:.2f} TL</b>\n"
        if kl.get('prev_day_low'):
            msg += f"📉 Dün L   : <b>{kl['prev_day_low']:.2f} TL</b>\n"
        msg += "\n"
    
    # ── ÖNERİLER ──
    if signal.get('suggestions'):
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💡 <b>ÖNERİLER</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for sug in signal['suggestions']:
            icon = sug.get('icon', '💡')
            text = escape_html(sug.get('text', ''))
            msg += f"{icon} <i>{text}</i>\n"
        msg += "\n"
    
    # ── ALT BİLGİ ──
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    if holding and holding.get('strategy') and holding.get('strategy') != 'YOK':
        strategy_name = holding.get('strategy', 'SWING')
        duration = holding.get('duration', '2-5 gün')
        msg += f"⏱️ <i>{escape_html(strategy_name)} • Tutma: {escape_html(duration)}</i>\n"
    else:
        msg += f"⏱️ <i>SWING TRADE • Tutma: 2-5 gün</i>\n"
    msg += f"🤖 <i>Borsa Sinyal Bot</i>\n"
    
    return msg


# ════════════════════════════════════════════════════════════
# SİNYAL GÖNDERME
# ════════════════════════════════════════════════════════════

async def send_signal_async(signal):
    """Tek sinyal gönder"""
    msg = format_signal_for_telegram(signal)
    if msg:
        return await send_message_async(msg)
    else:
        print(f"⚠️ Sinyal formatlanamadı: {signal.get('symbol', 'UNKNOWN')}")
        return False


def send_signal(signal):
    """Senkron sinyal gönderme"""
    try:
        return asyncio.run(send_signal_async(signal))
    except Exception as e:
        print(f"❌ Sinyal gönderme hatası: {e}")
        return False


async def send_multiple_signals_async(signals, max_signals=5):
    """Birden çok sinyali sırayla gönder"""
    if not signals:
        await send_message_async("⚠️ <b>Şu an güçlü sinyal yok</b>")
        return 0
    
    # Özet mesaj
    summary = f"""🔍 <b>BIST TARAMASI</b>
━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>{len(signals)}</b> güçlü sinyal bulundu
🏆 En iyi <b>{min(len(signals), max_signals)}</b> tanesi gönderiliyor

⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}
"""
    await send_message_async(summary.strip())
    await asyncio.sleep(1.5)
    
    sent = 0
    for i, signal in enumerate(signals[:max_signals], 1):
        print(f"📤 Sinyal {i}/{min(len(signals), max_signals)} gönderiliyor: {signal.get('symbol')}")
        success = await send_signal_async(signal)
        if success:
            sent += 1
            print(f"   ✅ Gönderildi")
        else:
            print(f"   ❌ Gönderilemedi")
        await asyncio.sleep(2)  # Spam koruması
    
    return sent


def send_multiple_signals(signals, max_signals=5):
    """Senkron çoklu sinyal"""
    try:
        return asyncio.run(send_multiple_signals_async(signals, max_signals))
    except Exception as e:
        print(f"❌ Çoklu sinyal hatası: {e}")
        return 0


# ════════════════════════════════════════════════════════════
# ÖZEL UYARILAR
# ════════════════════════════════════════════════════════════

def send_target_hit_alert(symbol, target_num, entry_price, target_price, current_price):
    """Hedef'e ulaştığında uyarı"""
    profit_pct = ((current_price - entry_price) / entry_price) * 100
    symbol = escape_html(symbol)
    
    msg = f"""🎯 <b>HEDEF {target_num}'E ULAŞILDI!</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>{symbol}</b>
📥 Alış      : {entry_price:.2f} TL
💰 Şu an     : {current_price:.2f} TL
🎯 Hedef {target_num}   : {target_price:.2f} TL
✅ Kâr       : <b>+{profit_pct:.2f}%</b>

💡 <b>ÖNERİ:</b>
"""
    if target_num == 1:
        msg += "• Pozisyonun %33'ünü SAT\n"
        msg += "• Stop'u giriş fiyatına çek\n"
        msg += "• Hedef 2'yi bekle"
    elif target_num == 2:
        msg += "• Pozisyonun %33'ünü daha SAT\n"
        msg += "• Stop'u Hedef 1'e çek\n"
        msg += "• Hedef 3 için bekle"
    else:
        msg += "• Kalan pozisyonu SAT\n"
        msg += "• Tam kâr kilitle\n"
        msg += "• Yeni fırsatlar için hazırlan"
    
    return send_message(msg)


def send_stop_warning(symbol, entry_price, current_price, stop_loss):
    """Stop'a yaklaştığında uyarı"""
    loss_pct = ((current_price - entry_price) / entry_price) * 100
    distance = ((current_price - stop_loss) / current_price) * 100
    symbol = escape_html(symbol)
    
    msg = f"""⚠️ <b>STOP-LOSS YAKLAŞIYOR!</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>{symbol}</b>
📥 Alış      : {entry_price:.2f} TL
💰 Şu an     : {current_price:.2f} TL
🛑 Stop      : {stop_loss:.2f} TL
📉 Zarar     : <b>{loss_pct:.2f}%</b>
📏 Stop'a    : <b>{distance:.2f}%</b> kaldı

💡 <b>DİKKAT:</b>
{stop_loss:.2f} TL altına inerse <b>HEMEN SAT</b>!
"""
    return send_message(msg)


def send_momentum_warning(symbol, current_price, entry_price, reason):
    """Momentum azalma uyarısı"""
    profit_pct = ((current_price - entry_price) / entry_price) * 100
    symbol = escape_html(symbol)
    reason = escape_html(reason)
    
    msg = f"""⚠️ <b>MOMENTUM ZAYIFLIYOR</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>{symbol}</b>
📥 Alış   : {entry_price:.2f} TL
💰 Şu an  : {current_price:.2f} TL
📊 Durum  : <b>{profit_pct:+.2f}%</b>

⚠️ <b>SEBEP:</b>
{reason}

💡 <b>ÖNERİ:</b>
"""
    if profit_pct > 0:
        msg += "• Kârdaysın, kısmi SATIŞ yapabilirsin\n"
        msg += "• Stop'u biraz yukarı çek\n"
        msg += "• Trend kırılırsa hızlı çık"
    else:
        msg += "• Pozisyonu yakından izle\n"
        msg += "• Yeni dip yapıyorsa hızlı çık\n"
        msg += "• Toparlanma olursa devam"
    
    return send_message(msg)


# ════════════════════════════════════════════════════════════
# TEST MESAJLARI
# ════════════════════════════════════════════════════════════

async def send_test_message_async():
    """Test mesajı"""
    msg = f"""🎉 <b>BORSA SİNYAL BOT - SWING OPTIMIZED</b>
━━━━━━━━━━━━━━━━━━━━━━━

✅ Bot bağlantısı başarılı
🤖 Sistem hazır
📊 Tüm indikatörler aktif

🎯 <b>AKTIF ÖZELLİKLER:</b>
• Pivot Points (P, R1-R3, S1-S3) ⭐
• Supertrend
• 10 mum formasyonu
• Çoklu kırılım tespiti
• 3 hedefli işlem planı (SWING)
• ATR bazlı dinamik stop
• Momentum azalma uyarısı
• Kar al önerileri
• Tutma süresi önerisi
• Risk seviyesi göstergesi

📋 <b>STRATEJİ:</b>
• SWING TRADE (1-5 gün tutma)
• Skor 65+ → AL sinyali
• Skor 75+ → GÜÇLÜ AL
• Skor 85+ → ÇOK GÜÇLÜ AL

⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}

━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Profesyonel SWING sinyalleri buradan gelecek</i>
"""
    return await send_message_async(msg.strip())


def send_test_message():
    """Senkron test"""
    try:
        return asyncio.run(send_test_message_async())
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        return False


# ════════════════════════════════════════════════════════════
# ANA TEST
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 TELEGRAM BOT TEST - SWING OPTIMIZED")
    print("="*60)
    
    if not TELEGRAM_BOT_TOKEN:
        print("\n❌ HATA: TELEGRAM_BOT_TOKEN config.py'de boş!")
        sys.exit(1)
    
    if not TELEGRAM_CHAT_ID:
        print("\n❌ HATA: TELEGRAM_CHAT_ID config.py'de boş!")
        sys.exit(1)
    
    print(f"\n✅ Token  : {TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")
    
    print("\n📋 SEÇENEKLER:")
    print("  1 → Test mesajı gönder")
    print("  2 → Mevcut verilerle tara ve gönder")
    print("  3 → Hedef ulaşıldı testi")
    print("  4 → Stop uyarısı testi")
    
    choice = input("\nSeçim (1/2/3/4): ").strip()
    
    if choice == "1":
        print("\n📤 Test mesajı gönderiliyor...")
        if send_test_message():
            print("✅ Mesaj gönderildi! Telefonu kontrol et 📱")
        else:
            print("❌ Hata oldu")
    
    elif choice == "2":
        print("\n🔍 Tarama yapılıyor...")
        import pandas as pd
        from database import get_stock_history
        from services.analyzer import analyze_stock
        from services.signal_engine import generate_signal
        
        test_symbols = ["AKBNK.IS", "THYAO.IS", "ASELS.IS", "AEFES.IS", "AKSA.IS"]
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
        
        signals.sort(key=lambda x: x['score'], reverse=True)
        
        if signals:
            print(f"\n✅ {len(signals)} sinyal bulundu")
            print("📤 Telegram'a gönderiliyor...")
            sent = send_multiple_signals(signals, max_signals=3)
            print(f"✅ {sent} mesaj gönderildi!")
        else:
            print("⚠️ Sinyal yok")
            send_message("⚠️ <b>Test:</b> Mevcut verilerde sinyal yok")
    
    elif choice == "3":
        print("\n🎯 Hedef testi...")
        send_target_hit_alert("THYAO", 1, 285.50, 290.50, 290.80)
        print("✅ Gönderildi")
    
    elif choice == "4":
        print("\n⚠️ Stop testi...")
        send_stop_warning("THYAO", 285.50, 283.20, 282.50)
        print("✅ Gönderildi")
    
    else:
        print("❌ Geçersiz")
