"""
Telegram Bot - Profesyonel Sinyal Gönderici
3 Hedefli kart, uyarılar, kar al önerileri, önemli seviyeler
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
    """Telegram'a mesaj gönder"""
    bot = get_bot()
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=True
        )
        return True
    except Exception as e:
        print(f"❌ Mesaj gönderme hatası: {e}")
        return False


def send_message(text):
    """Senkron mesaj gönderme"""
    try:
        return asyncio.run(send_message_async(text))
    except Exception as e:
        print(f"❌ Mesaj hatası: {e}")
        return False


# ════════════════════════════════════════════════════════════
# PROFESYONEL SİNYAL FORMATLAMA
# ════════════════════════════════════════════════════════════

def format_signal_for_telegram(signal):
    """Sinyali Telegram için HTML formatında hazırla - PROFESYONEL"""
    if not signal:
        return None
    
    # Veriler
    emoji = signal['emoji']
    label = signal['label']
    symbol = signal['symbol']
    price = signal['current_price']
    score = signal['score']
    score_bar = signal['score_bar']
    stars = signal['stars']
    confidence = signal['confidence']
    action = signal['action']
    t = signal['targets']
    
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
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💼 <b>İŞLEM PLANI - 3 HEDEF</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # ── GİRİŞ ──
    msg += f"📥 <b>GİRİŞ:</b> {t['entry']:.2f} TL\n\n"
    
    # ── HEDEF 1 ──
    msg += f"🎯 <b>HEDEF 1:</b> {t['target_1']:.2f} TL "
    msg += f"<b>(+{t['target_1_pct']}%)</b>\n"
    msg += f"   💡 <i>%33 sat, stop'u girişe çek</i>\n\n"
    
    # ── HEDEF 2 ──
    msg += f"🎯 <b>HEDEF 2:</b> {t['target_2']:.2f} TL "
    msg += f"<b>(+{t['target_2_pct']}%)</b>\n"
    msg += f"   💡 <i>%33 sat, stop'u Hedef 1'e çek</i>\n\n"
    
    # ── HEDEF 3 ──
    msg += f"🎯 <b>HEDEF 3:</b> {t['target_3']:.2f} TL "
    msg += f"<b>(+{t['target_3_pct']}%)</b>\n"
    msg += f"   💡 <i>Kalanı sat (trend kırılırsa)</i>\n\n"
    
    # ── STOP ──
    msg += f"🛑 <b>STOP-LOSS:</b> {t['stop_loss']:.2f} TL "
    msg += f"<b>(-{t['stop_pct']}%)</b>\n"
    msg += f"⚖️ <b>Risk/Ödül:</b> 1 / {t['risk_reward']}\n\n"
    
    # ── ALMA SEBEPLERİ ──
    if signal['reasons']:
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"✅ <b>ALMA SEBEPLERİ ({len(signal['reasons'])})</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, r in enumerate(signal['reasons'], 1):
            msg += f"{r['icon']} <b>{r['title']}</b>\n"
            msg += f"   📌 {r['detail']}\n"
            msg += f"   → <i>{r['meaning']}</i>\n\n"
    
    # ── UYARILAR ──
    if signal.get('warnings'):
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"⚠️ <b>UYARILAR ({len(signal['warnings'])})</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for w in signal['warnings']:
            msg += f"{w['icon']} <b>{w['title']}</b>\n"
            msg += f"   📌 {w['detail']}\n"
            msg += f"   💡 <b>{w['action']}</b>\n\n"
    
    # ── KIRILIMLAR ──
    if signal.get('breakouts'):
        up_breakouts = [b for b in signal['breakouts'] if b.get('type') == 'UP']
        if up_breakouts:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "🚀 <b>KIRILIMLAR</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for br in up_breakouts:
                msg += f"{br['icon']} <b>{br['detail']}</b>\n"
                msg += f"   → <i>{br['meaning']}</i>\n\n"
    
    # ── MUM FORMASYONLARI ──
    if signal.get('candle_patterns'):
        patterns = signal['candle_patterns'][:3]  # En fazla 3 göster
        if patterns:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "🕯️ <b>MUM FORMASYONLARI</b>\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for cp in patterns:
                msg += f"{cp['icon']} <b>{cp['name']}</b>\n"
                msg += f"   → <i>{cp['meaning']}</i>\n\n"
    
    # ── PUAN DAĞILIMI ──
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📊 <b>PUAN DAĞILIMI</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    b = signal['breakdown']
    msg += f"💥 Hacim       : <b>{b['volume']['score']}/{b['volume']['max']}</b>\n"
    msg += f"⚡ Momentum    : <b>{b['momentum']['score']}/{b['momentum']['max']}</b>\n"
    msg += f"📈 Trend       : <b>{b['trend']['score']}/{b['trend']['max']}</b>\n"
    msg += f"⭐ VWAP/Pivot  : <b>{b['vwap_pivot']['score']}/{b['vwap_pivot']['max']}</b>\n"
    msg += f"🚀 Kırılım/Mum : <b>{b['breakout_candle']['score']}/{b['breakout_candle']['max']}</b>\n"
    msg += f"💧 Likidite    : <b>{b['liquidity']['score']}/{b['liquidity']['max']}</b>\n\n"
    
    # ── ÖNEMLİ SEVİYELER ──
    kl = signal.get('key_levels', {})
    has_levels = any([kl.get('vwap'), kl.get('pivot'), kl.get('ema_9')])
    
    if has_levels:
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📍 <b>ÖNEMLİ SEVİYELER</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if kl.get('vwap'):
            arrow = "🟢" if price > kl['vwap'] else "🔴"
            msg += f"{arrow} VWAP    : <b>{kl['vwap']:.2f} TL</b>\n"
        if kl.get('pivot'):
            msg += f"🎯 Pivot   : <b>{kl['pivot']:.2f} TL</b>\n"
        if kl.get('r1'):
            msg += f"⬆️ R1      : <b>{kl['r1']:.2f} TL</b>\n"
        if kl.get('r2'):
            msg += f"⬆️ R2      : <b>{kl['r2']:.2f} TL</b>\n"
        if kl.get('s1'):
            msg += f"⬇️ S1      : <b>{kl['s1']:.2f} TL</b>\n"
        if kl.get('ema_9'):
            msg += f"📊 EMA 9   : <b>{kl['ema_9']:.2f} TL</b>\n"
        if kl.get('ema_21'):
            msg += f"📊 EMA 21  : <b>{kl['ema_21']:.2f} TL</b>\n"
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
            msg += f"{sug['icon']} <i>{sug['text']}</i>\n"
        msg += "\n"
    
    # ── ALT BİLGİ ──
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"⏱️ <i>Day Trade • Tutma: 1-3 gün</i>\n"
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
    for signal in signals[:max_signals]:
        success = await send_signal_async(signal)
        if success:
            sent += 1
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
    msg = f"""🎉 <b>BORSA SİNYAL BOT - PROFESYONEL</b>
━━━━━━━━━━━━━━━━━━━━━━━

✅ Bot bağlantısı başarılı
🤖 Sistem hazır
📊 Tüm indikatörler aktif

🎯 <b>AKTIF ÖZELLİKLER:</b>
• VWAP analizi
• Pivot Points (P, R1-R3, S1-S3)
• Supertrend
• 10 mum formasyonu
• Çoklu kırılım tespiti
• 3 hedefli işlem planı
• ATR bazlı dinamik stop
• Momentum azalma uyarısı
• Kar al önerileri

⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}

━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Artık profesyonel sinyaller buradan gelecek</i>
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
    print("🤖 TELEGRAM BOT TEST - PROFESYONEL")
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