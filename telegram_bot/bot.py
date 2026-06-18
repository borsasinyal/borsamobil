"""
Telegram Bot - Sinyal Gönderici
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


# ════════════════════════════════════════════════
# BOT BAĞLANTI
# ════════════════════════════════════════════════

def get_bot():
    """Bot örneğini döndür"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("❌ TELEGRAM_BOT_TOKEN config.py'de boş!")
    if not TELEGRAM_CHAT_ID:
        raise ValueError("❌ TELEGRAM_CHAT_ID config.py'de boş!")
    
    return Bot(token=TELEGRAM_BOT_TOKEN)


# ════════════════════════════════════════════════
# MESAJ GÖNDERME (Basit metin)
# ════════════════════════════════════════════════

async def send_message_async(text, parse_mode=ParseMode.HTML):
    """Telegram'a mesaj gönder"""
    bot = get_bot()
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=parse_mode
        )
        return True
    except Exception as e:
        print(f"❌ Mesaj gönderme hatası: {e}")
        return False


def send_message(text):
    """Senkron mesaj gönderme (kolaylık için)"""
    try:
        return asyncio.run(send_message_async(text))
    except Exception as e:
        print(f"❌ Mesaj hatası: {e}")
        return False


# ════════════════════════════════════════════════
# SİNYAL MESAJI FORMATLA (HTML)
# ════════════════════════════════════════════════

def format_signal_for_telegram(signal):
    """
    Sinyali Telegram için HTML formatında hazırla
    """
    if not signal:
        return None
    
    # Başlık ve emoji
    emoji = signal['emoji']
    label = signal['label']
    symbol = signal['symbol']
    price = signal['current_price']
    score = signal['score']
    score_bar = signal['score_bar']
    stars = signal['stars']
    
    # İşlem planı
    t = signal['targets']
    
    # Sebepler
    reasons_text = ""
    for reason in signal['reasons']:
        reasons_text += f"\n{reason['icon']} <b>{reason['title']}</b>\n"
        reasons_text += f"   <i>{reason['detail']}</i>\n"
        reasons_text += f"   → {reason['meaning']}\n"
    
    # Puan dağılımı
    b = signal['breakdown']
    
    # Tam mesaj
    msg = f"""
{emoji} <b>{label}</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>{symbol}</b>
💰 Güncel: <b>{price:.2f} TL</b>
⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}

━━━━━━━━━━━━━━━━━━━━━━━
💯 <b>SKOR: {score}/100</b>

<code>{score_bar}</code>
{stars}

━━━━━━━━━━━━━━━━━━━━━━━
💼 <b>İŞLEM PLANI</b>

📥 Giriş    : <b>{t['entry']:.2f} TL</b>
🎯 Hedef 1  : <b>{t['target_1']:.2f} TL</b> (+{t['target_1_pct']}%)
🎯 Hedef 2  : <b>{t['target_2']:.2f} TL</b> (+{t['target_2_pct']}%)
🛑 Stop     : <b>{t['stop_loss']:.2f} TL</b> (-{t['stop_pct']}%)
⚖️ R/Ö      : <b>1/{t['risk_reward']}</b>

━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>ALMA SEBEPLERİM ({len(signal['reasons'])})</b>
{reasons_text}

━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>PUAN DAĞILIMI</b>

💥 Hacim    : <b>{b['volume']['score']}/{b['volume']['max']}</b>
⚡ Momentum : <b>{b['momentum']['score']}/{b['momentum']['max']}</b>
📈 Trend    : <b>{b['trend']['score']}/{b['trend']['max']}</b>
🚀 Kırılım  : <b>{b['breakout']['score']}/{b['breakout']['max']}</b>
🎯 Likidite : <b>{b['liquidity']['score']}/{b['liquidity']['max']}</b>

━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Day Trade • Tutma: 1-3 gün</i>
"""
    return msg.strip()


# ════════════════════════════════════════════════
# SİNYAL GÖNDER
# ════════════════════════════════════════════════

async def send_signal_async(signal):
    """Tek bir sinyali Telegram'a gönder"""
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
        await send_message_async("⚠️ <b>Şu an güçlü sinyal bulunamadı</b>")
        return 0
    
    # Önce özet mesaj
    summary = f"""
🔍 <b>BIST TARAMASI TAMAMLANDI</b>
━━━━━━━━━━━━━━━━━━━━━━━

📊 Toplam {len(signals)} güçlü sinyal bulundu
🏆 En iyi {min(len(signals), max_signals)} tanesi gönderiliyor

⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}
"""
    await send_message_async(summary.strip())
    await asyncio.sleep(1)
    
    # Sinyalleri gönder
    sent = 0
    for signal in signals[:max_signals]:
        success = await send_signal_async(signal)
        if success:
            sent += 1
        await asyncio.sleep(1.5)  # Spam koruması
    
    return sent


def send_multiple_signals(signals, max_signals=5):
    """Senkron çoklu sinyal gönderme"""
    try:
        return asyncio.run(send_multiple_signals_async(signals, max_signals))
    except Exception as e:
        print(f"❌ Çoklu sinyal hatası: {e}")
        return 0


# ════════════════════════════════════════════════
# TEST MESAJI
# ════════════════════════════════════════════════

async def send_test_message_async():
    """Test mesajı gönder"""
    msg = f"""
🎉 <b>BORSA SİNYAL BOT AKTİF!</b>
━━━━━━━━━━━━━━━━━━━━━━━

✅ Bot bağlantısı başarılı
🤖 Sistem hazır
📊 BIST taranıyor...

⏰ {datetime.now().strftime('%H:%M - %d.%m.%Y')}

━━━━━━━━━━━━━━━━━━━━━━━
💡 <i>Artık AL/SAT sinyalleri buradan gelecek</i>
"""
    return await send_message_async(msg.strip())


def send_test_message():
    """Senkron test mesajı"""
    try:
        return asyncio.run(send_test_message_async())
    except Exception as e:
        print(f"❌ Test mesajı hatası: {e}")
        return False


# ════════════════════════════════════════════════
# ANA TEST
# ════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 TELEGRAM BOT TEST")
    print("="*60)
    
    # Token kontrol
    if not TELEGRAM_BOT_TOKEN:
        print("\n❌ HATA: config.py'de TELEGRAM_BOT_TOKEN boş!")
        print("   BotFather'dan aldığın token'ı yaz")
        sys.exit(1)
    
    if not TELEGRAM_CHAT_ID:
        print("\n❌ HATA: config.py'de TELEGRAM_CHAT_ID boş!")
        print("   @userinfobot'tan aldığın ID'yi yaz")
        sys.exit(1)
    
    print(f"\n✅ Token  : {TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")
    
    print("\n📋 Seçenekler:")
    print("  1 → Test mesajı gönder")
    print("  2 → Gerçek sinyalleri tara ve gönder")
    
    choice = input("\nSeçim (1/2): ").strip()
    
    if choice == "1":
        print("\n📤 Test mesajı gönderiliyor...")
        success = send_test_message()
        
        if success:
            print("✅ Mesaj gönderildi! Telefonunu kontrol et 📱")
        else:
            print("❌ Mesaj gönderilemedi")
            print("\nKontrol et:")
            print("  - Token doğru mu?")
            print("  - Chat ID doğru mu?")
            print("  - Bot'a START dedin mi?")
    
    elif choice == "2":
        print("\n🔍 BIST taraması başlıyor...")
        
        from services.scanner import scan_all_stocks
        
        signals = scan_all_stocks(min_score=65, save_to_db=True, verbose=False)
        
        if signals:
            print(f"\n✅ {len(signals)} sinyal bulundu!")
            print(f"📤 En iyi 5 sinyal Telegram'a gönderiliyor...")
            
            sent = send_multiple_signals(signals, max_signals=5)
            
            print(f"\n✅ {sent} mesaj gönderildi!")
            print("📱 Telefonunu kontrol et")
        else:
            print("\n⚠️ Sinyal bulunamadı")
            send_message("⚠️ <b>Şu an güçlü sinyal yok</b>\n\nBir sonraki tarama için bekleyin.")
    
    else:
        print("❌ Geçersiz seçim")