"""
Profesyonel Zamanlayici - SON HAL v2
YENI SAATLER: 10:30, 12:00, 14:00, 16:00, 18:15, 19:00
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta, time as dt_time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BIST_SYMBOLS
from database import get_connection
from services.data_fetcher import fetch_all_daily, fetch_all_15m
from services.scanner import (
    scan_all_stocks,
    scan_hourly_stocks,
    scan_4h_stocks,
    filter_new_signals
)
from telegram_bot.bot import send_message, send_multiple_signals


TR_TIMEZONE = timezone(timedelta(hours=3))
def tr_now(): return datetime.now(TR_TIMEZONE)
def is_weekday(): return tr_now().weekday() < 5
def log_event(msg):
    print(f"[{tr_now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def job_morning_preparation():
    log_event("SABAH HAZIRLIK")
    send_message(f"SABAH HAZIRLIK BASLADI\n{tr_now().strftime('%H:%M - %d.%m.%Y')}\nVeriler guncelleniyor...")
    if not is_weekday():
        send_message("Hafta sonu")
        return
    try:
        fetch_all_daily(symbols_list=BIST_SYMBOLS, delay=0.05)
        send_message("SABAH HAZIRLIK TAMAM\nVeriler guncellendi\nIlk tarama: 10:30")
    except Exception as e:
        send_message(f"Hata: {str(e)[:200]}")


def job_premarket_report():
    log_event("PRE-MARKET")
    send_message(f"PRE-MARKET - {tr_now().strftime('%H:%M')}")
    if not is_weekday(): return
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=False, verbose=False)
        if signals:
            top = signals[:5]
            msg = "PRE-MARKET RAPORU\nBugun izlenecekler:\n\n"
            for i, s in enumerate(top, 1):
                msg += f"{i}. {s['symbol']} - {s['current_price']:.2f} TL ({s['score']}/100)\n"
            msg += "\nAcilista takip edecegim"
            send_message(msg)
        else:
            send_message("PRE-MARKET - Dikkat cekici hisse yok")
    except Exception as e:
        send_message(f"Hata: {str(e)[:200]}")


def job_market_open_scan():
    log_event("ACILIS TARAMASI (10:30)")
    send_message(f"ACILIS TARAMASI - {tr_now().strftime('%H:%M')}\nIlk 30 dk volatilite gecti")
    if not is_weekday(): return
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=True, verbose=False)
        if not signals:
            send_message("ACILIS - Sinyal yok, 12:00'de tekrar")
            return
        send_message(f"ACILIS - {len(signals)} SINYAL!")
        send_multiple_signals(signals, max_signals=5)
    except Exception as e:
        send_message(f"Hata: {str(e)[:200]}")


def job_full_scan_2h():
    log_event("2 SAATLIK TARAMA")
    hour = tr_now().hour
    scan_label = "OGLE ONCESI" if hour < 14 else "OGLEDEN SONRA"
    send_message(f"{scan_label} TARAMA - {tr_now().strftime('%H:%M')}")
    if not is_weekday(): return
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=True, verbose=False)
        if not signals:
            send_message(f"{scan_label} - Sinyal yok")
            return
        send_message(f"{scan_label} - {len(signals)} SINYAL!")
        send_multiple_signals(signals, max_signals=5)
    except Exception as e:
        send_message(f"Hata: {str(e)[:200]}")


def job_quick_scan():
    log_event("HIZLI TARAMA (MANUEL)")
    send_message(f"HIZLI TARAMA - {tr_now().strftime('%H:%M')}")
    try:
        signals = scan_all_stocks(min_score=65, save_to_db=False, verbose=False)
        if not signals:
            send_message("HIZLI TARAMA - Sinyal yok")
            return
        send_message(f"{len(signals)} SINYAL!")
        send_multiple_signals(signals, max_signals=3)
    except Exception as e:
        send_message(f"Hata: {str(e)[:200]}")


def job_full_scan():
    log_event("TAM TARAMA (MANUEL)")
    send_message(f"TAM TARAMA - {tr_now().strftime('%H:%M')}")
    try:
        signals = scan_all_stocks(min_score=60, save_to_db=True, verbose=False)
        if not signals:
            send_message("TAM TARAMA - Sinyal yok")
            return
        send_message(f"{len(signals)} SINYAL!")
        send_multiple_signals(signals, max_signals=5)
    except Exception as e:
        send_message(f"Hata: {str(e)[:200]}")


def job_hourly_scan():
    log_event(f"SAATLIK TARAMA (MANUEL) - Saat: {tr_now().hour}")
    try:
        from telegram_bot.bot import send_hourly_signals
        hourly_signals = scan_hourly_stocks(min_score=68, symbols_list=BIST_SYMBOLS[:200])
        if hourly_signals:
            log_event(f"{len(hourly_signals)} saatlik sinyal")
            send_hourly_signals(hourly_signals, max_signals=3)
        else:
            send_message("SAATLIK TARAMA - Guclu saatlik sinyal yok")
    except Exception as e:
        log_event(f"Saatlik hata: {e}")


def job_4h_scan():
    log_event("1. 4H TARAMA (14:00)")
    send_message(f"1. 4 SAATLIK TARAMA - Ogle Mumu\n{tr_now().strftime('%H:%M - %d.%m.%Y')}\nIlk 4H mum kapandi (10:00-14:00)")
    try:
        from telegram_bot.bot import send_4h_signals
        signals_4h = scan_4h_stocks(min_score=65, symbols_list=BIST_SYMBOLS)
        if signals_4h:
            log_event(f"{len(signals_4h)} adet 4H sinyal")
            send_4h_signals(signals_4h, max_signals=5)
        else:
            send_message("1. 4H TARAMA - Guclu 4H sinyal yok")
    except Exception as e:
        log_event(f"4H hata: {e}")
        send_message(f"4H Hata: {str(e)[:200]}")


def job_4h_scan_evening():
    log_event("2. 4H TARAMA (18:15 - YARIN ICIN)")
    send_message(f"2. 4 SAATLIK TARAMA - KAPANIS MUMU\n{tr_now().strftime('%H:%M - %d.%m.%Y')}\n2. 4H mum kapandi (14:00-18:00)\nYarin sabah icin hazir liste")
    try:
        from telegram_bot.bot import send_4h_signals
        signals_4h = scan_4h_stocks(min_score=65, symbols_list=BIST_SYMBOLS)
        if signals_4h:
            log_event(f"{len(signals_4h)} adet 4H sinyal (YARIN)")
            send_4h_signals(signals_4h, max_signals=5)
        else:
            send_message("2. 4H TARAMA - Guclu 4H sinyal yok")
    except Exception as e:
        log_event(f"4H aksam hata: {e}")
        send_message(f"4H Aksam Hata: {str(e)[:200]}")


def calculate_fibonacci_levels(df, lookback=90):
    if len(df) < lookback:
        lookback = len(df)
    recent = df.tail(lookback)
    high = recent['high'].max()
    low = recent['low'].min()
    diff = high - low
    return {
        'zirve': high,
        'fib_786': high - (diff * 0.214),
        'fib_618': high - (diff * 0.382),
        'fib_50': high - (diff * 0.5),
        'fib_382': high - (diff * 0.618),
        'fib_236': high - (diff * 0.764),
        'dip': low,
        'range': diff
    }


def analyze_bist100():
    try:
        import yfinance as yf
        from services.analyzer import analyze_stock
        import pandas as pd
        
        log_event("BIST 100 Fibonacci analizi")
        
        ticker = yf.Ticker("XU100.IS")
        hist = ticker.history(period="6mo")
        if len(hist) < 50:
            return None
        
        df = pd.DataFrame({
            'date': [d.strftime('%Y-%m-%d') for d in hist.index],
            'open': hist['Open'].values, 'high': hist['High'].values,
            'low': hist['Low'].values, 'close': hist['Close'].values,
            'volume': hist['Volume'].values
        })
        
        analysis = analyze_stock(df, timeframe='daily')
        if not analysis:
            return None
        
        fib_levels = calculate_fibonacci_levels(df, lookback=90)
        
        today_close = analysis.get('current_price')
        prev_close = analysis.get('prev_close')
        daily_change = ((today_close - prev_close) / prev_close) * 100 if prev_close else 0
        
        ema_5 = analysis.get('ema_5')
        ema_22 = analysis.get('ema_22')
        ema_50 = analysis.get('ema_50')
        
        trend_status = "YATAY"
        trend_detail = ""
        
        if ema_5 and ema_22 and ema_50:
            if today_close > ema_5 > ema_22 > ema_50:
                trend_status = "GUCLU BOGA"
                trend_detail = "Tum EMA sirali yukari"
            elif today_close > ema_22 and today_close > ema_50:
                trend_status = "BOGA"
                trend_detail = "EMA22 ve EMA50 uzerinde"
            elif today_close > ema_50:
                trend_status = "POZITIF"
                trend_detail = "EMA50 uzerinde"
            elif today_close < ema_5 < ema_22 < ema_50:
                trend_status = "GUCLU AYI"
                trend_detail = "Tum EMA sirali asagi"
            elif today_close < ema_50:
                trend_status = "AYI"
                trend_detail = "EMA50 altinda"
        
        rsi = analysis.get('rsi', 50)
        prev_rsi = analysis.get('prev_rsi', 50)
        
        if rsi > 70: rsi_status = "ASIRI ALIM"
        elif rsi > 60: rsi_status = "GUCLU"
        elif rsi > 50: rsi_status = "POZITIF"
        elif rsi > 40: rsi_status = "NOTR"
        elif rsi > 30: rsi_status = "ZAYIF"
        else: rsi_status = "ASIRI SATIM"
        
        momentum = "NOTR"
        momentum_detail = ""
        
        if rsi and prev_rsi:
            rsi_change = rsi - prev_rsi
            if rsi_change > 3 and rsi > 50:
                momentum = "GUCLENIYOR"
                momentum_detail = f"RSI +{rsi_change:.1f} artti"
            elif rsi_change > 1:
                momentum = "HAFIF YUKARI"
                momentum_detail = "Ivme kazaniyor"
            elif rsi_change < -3:
                momentum = "ZAYIFLIYOR"
                momentum_detail = f"RSI {rsi_change:.1f} azaldi"
            elif rsi_change < -1:
                momentum = "HAFIF ASAGI"
                momentum_detail = "Ivme kaybediyor"
        
        macd = analysis.get('macd')
        macd_signal = analysis.get('macd_signal')
        macd_status = "NOTR"
        
        if macd is not None and macd_signal is not None:
            if macd > macd_signal and macd > 0:
                macd_status = "POZITIF"
            elif macd > macd_signal:
                macd_status = "YUKARI KESISIM"
            elif macd < macd_signal and macd < 0:
                macd_status = "NEGATIF"
            else:
                macd_status = "ASAGI KESISIM"
        
        adx = analysis.get('adx', 0)
        if adx > 30: adx_status = "COK GUCLU"
        elif adx > 25: adx_status = "GUCLU"
        elif adx > 20: adx_status = "ORTA"
        else: adx_status = "ZAYIF"
        
        beklenti_list = []
        cp = today_close
        
        if cp >= fib_levels['fib_786']:
            beklenti_list.append(f"Fibonacci 0.786 ({fib_levels['fib_786']:.0f}) ustunde - Guclu")
            beklenti_list.append(f"Zirve testi: {fib_levels['zirve']:.0f}")
        elif cp >= fib_levels['fib_618']:
            beklenti_list.append("Altin Oran (0.618) ustu - Saglam")
            beklenti_list.append(f"Sonraki hedef: {fib_levels['fib_786']:.0f}")
        elif cp >= fib_levels['fib_50']:
            beklenti_list.append("0.5 orta bolge - Kararsiz")
            beklenti_list.append(f"Yukari: {fib_levels['fib_618']:.0f} | Asagi: {fib_levels['fib_382']:.0f}")
        elif cp >= fib_levels['fib_382']:
            beklenti_list.append("0.382 altinda - Zayif")
            beklenti_list.append(f"Kritik destek: {fib_levels['fib_236']:.0f}")
        elif cp >= fib_levels['fib_236']:
            beklenti_list.append("0.236 yakin - Dip bolge")
            beklenti_list.append(f"Son destek: {fib_levels['dip']:.0f}")
        else:
            beklenti_list.append("Dip bolgesinde - Riskli")
            beklenti_list.append("Asiri satim - tepki alisi olabilir")
        
        if trend_status in ["GUCLU BOGA", "BOGA"]:
            if rsi < 70:
                beklenti_list.append("Trend guclu, yukselis devam edebilir")
            else:
                beklenti_list.append("RSI yuksek, duzeltme gelebilir")
        elif trend_status in ["AYI", "GUCLU AYI"]:
            if rsi < 30:
                beklenti_list.append("Asiri satimda, tepki alisi gelebilir")
        
        return {
            'price': today_close, 'change': daily_change,
            'trend_status': trend_status, 'trend_detail': trend_detail,
            'rsi': rsi, 'rsi_status': rsi_status,
            'momentum': momentum, 'momentum_detail': momentum_detail,
            'macd_status': macd_status, 'adx': adx, 'adx_status': adx_status,
            'beklenti_list': beklenti_list,
            'ema_5': ema_5, 'ema_22': ema_22, 'ema_50': ema_50,
            'fibonacci': fib_levels,
        }
    except Exception as e:
        log_event(f"BIST 100 hata: {e}")
        return None


def format_bist100_analysis(bist):
    if not bist:
        return "BIST 100 - Veri alinamadi\n\n"
    
    change_sign = "+" if bist['change'] > 0 else ""
    
    msg = "BIST 100 ANALIZI\n===========================\n\n"
    msg += f"Kapanis: {bist['price']:.0f} puan\n"
    msg += f"Degisim: {change_sign}%{bist['change']:.2f}\n\n"
    
    msg += "GENEL DURUM\n"
    msg += f"Trend: {bist['trend_status']}\n"
    if bist['trend_detail']:
        msg += f"  {bist['trend_detail']}\n"
    msg += f"ADX: {bist['adx']:.1f} - {bist['adx_status']}\n\n"
    
    msg += "TEKNIK GOSTERGELER\n"
    msg += f"RSI: {bist['rsi']:.1f} - {bist['rsi_status']}\n"
    msg += f"MACD: {bist['macd_status']}\n\n"
    
    msg += "MOMENTUM\n"
    msg += f"Yon: {bist['momentum']}\n"
    if bist['momentum_detail']:
        msg += f"  {bist['momentum_detail']}\n"
    msg += "\n"
    
    fib = bist.get('fibonacci')
    if fib:
        price = bist['price']
        msg += "FIBONACCI DESTEK/DIRENC\nSon 90 gun\n\n"
        msg += f"ZIRVE: {fib['zirve']:.0f}\n\n"
        
        if price < fib['fib_786']:
            msg += f"Direnc (0.786): {fib['fib_786']:.0f}\n"
        if price < fib['fib_618']:
            msg += f"Direnc (0.618) Altin: {fib['fib_618']:.0f}\n"
        if price < fib['fib_50']:
            msg += f"Direnc (0.5): {fib['fib_50']:.0f}\n"
        
        msg += f"\nSU AN: {price:.0f}\n\n"
        
        if price > fib['fib_50']:
            msg += f"Destek (0.5): {fib['fib_50']:.0f}\n"
        if price > fib['fib_382']:
            msg += f"Destek (0.382): {fib['fib_382']:.0f}\n"
        if price > fib['fib_236']:
            msg += f"Destek (0.236): {fib['fib_236']:.0f}\n"
        
        msg += f"\nDIP: {fib['dip']:.0f}\n\n"
    
    if bist.get('ema_5') and bist.get('ema_22') and bist.get('ema_50'):
        msg += "EMA SEVIYELERI\n"
        msg += f"EMA5 : {bist['ema_5']:.0f}\n"
        msg += f"EMA22: {bist['ema_22']:.0f}\n"
        msg += f"EMA50: {bist['ema_50']:.0f}\n\n"
    
    if bist['beklenti_list']:
        msg += "YARIN ICIN BEKLENTI\n"
        for beklenti in bist['beklenti_list']:
            msg += f"- {beklenti}\n"
        msg += "\n"
    
    return msg


def format_performance_report():
    try:
        from database import get_today_signals_summary, get_today_signal_details, get_performance_summary, get_active_signals
        import yfinance as yf
        
        msg = "BOT PERFORMANS RAPORU\n===========================\n\n"
        
        today_summary = get_today_signals_summary()
        today_details = get_today_signal_details()
        
        if today_summary and today_summary.get('total_sent', 0) > 0:
            msg += "BUGUN VERILEN SINYALLER\n"
            msg += f"Toplam: {today_summary['total_sent']}\n"
            msg += f"Farkli hisse: {today_summary['unique_symbols']}\n"
            msg += f"Ort skor: {today_summary['avg_score']:.0f}\n"
            msg += f"En yuksek: {today_summary['max_score']}\n\n"
            
            if today_details:
                msg += "BUGUNKU SINYALLERIN DURUMU\n\n"
                
                win_count = 0
                loss_count = 0
                total_pnl = 0
                checked = 0
                
                for s in today_details[:10]:
                    symbol = s['symbol']
                    entry_price = s['entry_price']
                    score = s['score']
                    
                    current_price = None
                    try:
                        ticker = yf.Ticker(f"{symbol}.IS")
                        info = ticker.history(period="1d")
                        if not info.empty:
                            current_price = float(info['Close'].iloc[-1])
                    except:
                        pass
                    
                    if current_price and entry_price > 0:
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        total_pnl += pnl_pct
                        checked += 1
                        
                        if pnl_pct > 0:
                            win_count += 1
                            emoji = "+"
                        elif pnl_pct < -2:
                            loss_count += 1
                            emoji = "-"
                        else:
                            emoji = "="
                        
                        msg += f"[{emoji}] {symbol} ({score}/100)\n"
                        msg += f"    {entry_price:.2f} -> {current_price:.2f} ({pnl_pct:+.2f}%)\n\n"
                    else:
                        msg += f"[?] {symbol} ({score}/100)\n\n"
                
                if checked > 0:
                    avg_pnl = total_pnl / checked
                    win_rate = (win_count / checked) * 100
                    
                    msg += "BUGUNKU SONUC\n"
                    msg += f"Karli: {win_count}\n"
                    msg += f"Zararli: {loss_count}\n"
                    msg += f"Notr: {checked - win_count - loss_count}\n"
                    msg += f"Ortalama: {avg_pnl:+.2f}%\n"
                    msg += f"Bugunku basari: %{win_rate:.0f}\n\n"
        else:
            msg += "Bugun sinyal verilmedi\n\n"
        
        active = get_active_signals()
        if active:
            msg += f"AKTIF TAKIP ({len(active)} sinyal)\n\n"
            
            for s in active[:5]:
                symbol = s['symbol']
                entry = s['entry_price']
                
                current_price = None
                try:
                    ticker = yf.Ticker(f"{symbol}.IS")
                    info = ticker.history(period="1d")
                    if not info.empty:
                        current_price = float(info['Close'].iloc[-1])
                except:
                    pass
                
                if current_price:
                    pnl = ((current_price - entry) / entry) * 100
                    msg += f"{symbol} {entry:.2f}->{current_price:.2f} ({pnl:+.2f}%)\n"
                else:
                    msg += f"{symbol} {entry:.2f}\n"
            
            if len(active) > 5:
                msg += f"\n+{len(active)-5} sinyal daha aktif\n"
            msg += "\n"
        
        perf = get_performance_summary(days=7)
        if perf and perf.get('total_closed', 0) > 0:
            msg += "HAFTALIK PERFORMANS (7 gun)\n\n"
            msg += f"Kapanan: {perf['total_closed']}\n"
            msg += f"Karli: {perf.get('wins', 0)}\n"
            msg += f"Zararli: {perf.get('losses', 0)}\n"
            msg += f"H1 vurma: {perf.get('t1_hit', 0)}\n"
            msg += f"H2 vurma: {perf.get('t2_hit', 0)}\n"
            msg += f"H3 vurma: {perf.get('t3_hit', 0)}\n"
            msg += f"Stop: {perf.get('stopped', 0)}\n\n"
            msg += f"WIN RATE: %{perf['win_rate']}\n"
            
            avg_pnl = perf.get('avg_pnl')
            if avg_pnl is not None:
                msg += f"Ortalama K/Z: {avg_pnl:+.2f}%\n"
            
            best = perf.get('best_trade')
            worst = perf.get('worst_trade')
            if best is not None: msg += f"En iyi: +{best:.2f}%\n"
            if worst is not None: msg += f"En kotu: {worst:.2f}%\n"
            
            pf = perf.get('profit_factor', 0)
            if pf > 0: msg += f"Profit Factor: {pf}\n"
            
            msg += "\n"
        else:
            msg += "HAFTALIK\nSon 7 gunde kapanmis sinyal yok\n\n"
        
        return msg
    except Exception as e:
        log_event(f"Performans hatasi: {e}")
        return "PERFORMANS - Hesaplanamadi\n\n"


def job_weekly_report():
    log_event("HAFTALIK RAPOR")
    
    try:
        from database import get_performance_summary, get_active_signals, get_connection
        import yfinance as yf
        
        send_message(f"HAFTALIK RAPOR HAZIRLANIYOR - {tr_now().strftime('%H:%M')}")
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_sent, COUNT(DISTINCT symbol) as unique_symbols, AVG(score) as avg_score, MAX(score) as max_score FROM signals WHERE created_at >= datetime('now', '-7 days')")
        weekly_signals = dict(cursor.fetchone())
        conn.close()
        
        perf = get_performance_summary(days=7)
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, entry_price, final_price, final_pnl_pct, target_1_hit, target_2_hit, target_3_hit, stop_hit FROM active_signals WHERE created_at >= datetime('now', '-7 days') AND status != 'active' AND final_pnl_pct > 0 ORDER BY final_pnl_pct DESC LIMIT 5")
        top_winners = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        active_signals = get_active_signals()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, MAX(score) as max_score, MAX(price) as last_price FROM signals WHERE created_at >= datetime('now', '-5 days') GROUP BY symbol ORDER BY MAX(score) DESC LIMIT 5")
        monday_watchlist = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        today = tr_now()
        week_start = today - timedelta(days=7)
        week_str = f"{week_start.strftime('%d %b')} - {today.strftime('%d %b %Y')}"
        
        msg = "HAFTALIK BOT RAPORU\n===========================\n\n"
        msg += f"Hafta: {week_str}\n\n"
        
        msg += "GENEL ISTATISTIKLER\n"
        if weekly_signals.get('total_sent'):
            msg += f"Toplam sinyal: {weekly_signals['total_sent']}\n"
            msg += f"Farkli hisse: {weekly_signals['unique_symbols']}\n"
            msg += f"Ort skor: {weekly_signals.get('avg_score', 0):.0f}\n"
            msg += f"En yuksek: {weekly_signals.get('max_score', 0)}\n\n"
        else:
            msg += "Bu hafta sinyal verilmedi\n\n"
        
        if perf and perf.get('total_closed', 0) > 0:
            msg += "KAPANAN POZISYONLAR\n"
            msg += f"Kapanan: {perf['total_closed']}\n"
            msg += f"Kazanan: {perf.get('wins', 0)}\n"
            msg += f"Kaybeden: {perf.get('losses', 0)}\n\n"
            msg += f"H1: {perf.get('t1_hit', 0)}\n"
            msg += f"H2: {perf.get('t2_hit', 0)}\n"
            msg += f"H3: {perf.get('t3_hit', 0)}\n"
            msg += f"Stop: {perf.get('stopped', 0)}\n\n"
            
            msg += "PERFORMANS\n"
            msg += f"WIN RATE: %{perf['win_rate']}\n"
            
            avg_pnl = perf.get('avg_pnl')
            if avg_pnl is not None:
                msg += f"Ortalama K/Z: {avg_pnl:+.2f}%\n"
            
            best = perf.get('best_trade')
            worst = perf.get('worst_trade')
            if best is not None: msg += f"En iyi: +{best:.2f}%\n"
            if worst is not None: msg += f"En kotu: {worst:.2f}%\n"
            
            pf = perf.get('profit_factor', 0)
            if pf > 0: msg += f"Profit Factor: {pf}\n"
            
            msg += "\n"
        else:
            msg += "KAPANAN POZISYONLAR\nBu hafta kapanmis pozisyon yok\n\n"
        
        if top_winners:
            msg += "EN BASARILI 5 HISSE\n\n"
            for i, w in enumerate(top_winners, 1):
                symbol = w['symbol']
                pnl = w['final_pnl_pct']
                entry = w['entry_price']
                exit_p = w['final_price']
                
                target_info = ""
                if w.get('target_3_hit'):
                    target_info = " (H3 vurdu)"
                elif w.get('target_2_hit'):
                    target_info = " (H2 vurdu)"
                elif w.get('target_1_hit'):
                    target_info = " (H1 vurdu)"
                
                msg += f"{i}. {symbol} +{pnl:.2f}%{target_info}\n"
                msg += f"   {entry:.2f} -> {exit_p:.2f}\n\n"
        
        if active_signals:
            msg += f"HALA AKTIF TAKIPTE ({len(active_signals)})\n\n"
            
            for s in active_signals[:10]:
                symbol = s['symbol']
                entry = s['entry_price']
                
                current_price = None
                try:
                    ticker = yf.Ticker(f"{symbol}.IS")
                    info = ticker.history(period="1d")
                    if not info.empty:
                        current_price = float(info['Close'].iloc[-1])
                except:
                    pass
                
                if current_price:
                    pnl = ((current_price - entry) / entry) * 100
                    msg += f"{symbol}: {entry:.2f}->{current_price:.2f} ({pnl:+.2f}%)\n"
                else:
                    msg += f"{symbol}: {entry:.2f}\n"
            
            if len(active_signals) > 10:
                msg += f"\n+{len(active_signals)-10} sinyal daha\n"
            msg += "\n"
        
        if monday_watchlist:
            msg += "PAZARTESI IZLENECEK 5 HISSE\n\n"
            for i, w in enumerate(monday_watchlist, 1):
                msg += f"{i}. {w['symbol']} (Skor: {w['max_score']})\n"
                msg += f"   Son fiyat: {w['last_price']:.2f} TL\n\n"
        
        msg += "BOT DEGERLENDIRMESI\n"
        if perf and perf.get('total_closed', 0) > 0:
            win_rate = perf['win_rate']
            avg_pnl = perf.get('avg_pnl', 0)
            
            if win_rate >= 70 and avg_pnl > 3:
                msg += "MUKEMMEL HAFTA\n"
            elif win_rate >= 60:
                msg += "IYI HAFTA\n"
            elif win_rate >= 50:
                msg += "ORTA HAFTA\n"
            else:
                msg += "ZAYIF HAFTA - Dikkat\n"
        else:
            msg += "Degerlendirme icin veri yok\n"
        
        msg += "\nPazartesi 09:45'te bot tekrar basliyor"
        
        send_message(msg)
        log_event("Haftalik rapor gonderildi")
    except Exception as e:
        log_event(f"Haftalik hata: {e}")
        send_message(f"Haftalik hata: {str(e)[:200]}")


def get_4h_candidates_for_tomorrow():
    try:
        from services.tradingview_fetcher import fetch_stock_tv, TV_AVAILABLE
        from services.analyzer import analyze_stock
        from services.signal_engine import generate_signal
        import pandas as pd
        
        if not TV_AVAILABLE:
            log_event("TV yok, 4H adaylari alinamiyor")
            return []
        
        log_event("4H mum adaylari araniyor...")
        candidates = []
        
        for symbol in BIST_SYMBOLS:
            try:
                data = fetch_stock_tv(symbol, n_bars=100, interval='4h')
                if not data or len(data) < 20:
                    continue
                
                df = pd.DataFrame(data)
                analysis = analyze_stock(df, timeframe='4h')
                if not analysis:
                    continue
                
                cp = analysis.get('current_price')
                if not cp or cp < 2:
                    continue
                
                rvol = analysis.get('rvol', 0)
                if rvol < 1.2:
                    continue
                
                signal = generate_signal(symbol, analysis, df)
                if not signal or signal['score'] < 65:
                    continue
                
                candidates.append({
                    'symbol': symbol.replace('.IS', ''),
                    'price': cp,
                    'score': signal['score'],
                    'rvol': rvol,
                    'rsi': analysis.get('rsi', 0),
                    'targets': signal.get('targets', {}),
                    'reasons': signal.get('reasons', [])[:3],
                    'is_dual_signal': signal.get('is_dual_signal', False),
                    'is_dual_dip': signal.get('is_dual_dip', False)
                })
            except:
                continue
        
        candidates.sort(key=lambda x: x['score'], reverse=True)
        log_event(f"{len(candidates)} adet 4H aday")
        return candidates[:10]
    except Exception as e:
        log_event(f"4H aday hata: {e}")
        return []


def format_active_positions_review():
    try:
        from database import get_active_signals
        from services.analyzer import analyze_stock
        import yfinance as yf
        import pandas as pd
        
        active = get_active_signals()
        if not active:
            return ""
        
        msg = f"AKTIF POZISYONLAR ({len(active)}) - YORUM\n===========================\n\n"
        
        for s in active[:10]:
            symbol = s['symbol']
            entry = s['entry_price']
            t1 = s['target_1']
            t2 = s['target_2']
            stop = s['stop_loss']
            
            current_price = None
            analysis = None
            
            try:
                ticker = yf.Ticker(f"{symbol}.IS")
                hist = ticker.history(period="3mo")
                if len(hist) >= 30:
                    current_price = float(hist['Close'].iloc[-1])
                    df = pd.DataFrame({
                        'date': [d.strftime('%Y-%m-%d') for d in hist.index],
                        'open': hist['Open'].values, 'high': hist['High'].values,
                        'low': hist['Low'].values, 'close': hist['Close'].values,
                        'volume': hist['Volume'].values
                    })
                    analysis = analyze_stock(df, timeframe='daily')
            except:
                pass
            
            if not current_price:
                msg += f"{symbol} - fiyat alinamadi\n\n"
                continue
            
            pnl = ((current_price - entry) / entry) * 100
            
            if s.get('target_2_hit'):
                status = "H2 vuruldu"
            elif s.get('target_1_hit'):
                status = "H1 vuruldu"
            elif pnl >= 3:
                status = "Karda, gidiyor"
            elif pnl >= 0:
                status = "Notr bolge"
            elif pnl >= -2:
                status = "Hafif zararda"
            else:
                status = "Zararda - dikkat"
            
            msg += f"{symbol} - {status}\n"
            msg += f"  {entry:.2f} -> {current_price:.2f} ({pnl:+.2f}%)\n"
            msg += f"  H1: {t1:.2f} | H2: {t2:.2f} | Stop: {stop:.2f}\n"
            
            if analysis:
                rsi = analysis.get('rsi', 50)
                ema22 = analysis.get('ema_22')
                ema50 = analysis.get('ema_50')
                macd = analysis.get('macd')
                ms = analysis.get('macd_signal')
                
                comments = []
                
                if ema22 and ema50 and current_price:
                    if current_price > ema22 > ema50:
                        comments.append("Trend guclu, tutmaya devam")
                    elif current_price > ema22:
                        comments.append("EMA22 ustunde, saglikli")
                    elif current_price < ema22 and current_price > ema50:
                        comments.append("EMA22 kirildi, izle")
                    elif current_price < ema50:
                        comments.append("EMA50 altinda, stop yakin olabilir")
                
                if rsi >= 75:
                    comments.append("RSI asiri yuksek - kar al dusun")
                elif rsi >= 65:
                    comments.append("Momentum guclu")
                elif rsi < 35:
                    comments.append("RSI dusuk - dip toparlanma olabilir")
                
                if macd is not None and ms is not None:
                    if macd < ms and pnl > 0:
                        comments.append("MACD zayifliyor - kar kilitle")
                    elif macd > ms:
                        comments.append("MACD pozitif")
                
                if s.get('target_1_hit') and not s.get('target_2_hit'):
                    if pnl > 5:
                        comments.append("ONERI: %33 daha sat, H2'yi bekle")
                elif pnl >= 8:
                    comments.append("ONERI: Kismi kar al")
                elif pnl <= -3:
                    comments.append("ONERI: Stop yaklasti, hazir ol")
                
                if comments:
                    for c in comments[:3]:
                        msg += f"  > {c}\n"
            
            msg += "\n"
        
        if len(active) > 10:
            msg += f"+{len(active)-10} sinyal daha aktif\n\n"
        
        return msg
    except Exception as e:
        log_event(f"Aktif pozisyon hata: {e}")
        return ""


def job_end_of_day_report():
    log_event("GUN SONU RAPORU v2")
    
    try:
        import yfinance as yf
        from services.analyzer import analyze_stock
        from services.signal_engine import generate_signal
        import pandas as pd
        
        send_message(f"GUN SONU RAPORU HAZIRLANIYOR - {tr_now().strftime('%H:%M')}")
        
        bist100 = analyze_bist100()
        msg1 = f"GUN SONU RAPORU\n{tr_now().strftime('%d.%m.%Y - %A')}\n\n"
        msg1 += format_bist100_analysis(bist100)
        send_message(msg1)
        
        perf_msg = format_performance_report()
        send_message(perf_msg)
        
        active_msg = format_active_positions_review()
        if active_msg:
            send_message(active_msg)
        
        movers_data = []
        tomorrow_candidates = []
        
        for symbol in BIST_SYMBOLS:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                if len(hist) < 2: continue
                
                today_close = float(hist['Close'].iloc[-1])
                yesterday_close = float(hist['Close'].iloc[-2])
                today_volume = int(hist['Volume'].iloc[-1])
                today_high = float(hist['High'].iloc[-1])
                today_low = float(hist['Low'].iloc[-1])
                today_open = float(hist['Open'].iloc[-1])
                
                daily_change = ((today_close - yesterday_close) / yesterday_close) * 100
                avg_volume = hist['Volume'].mean()
                rvol = today_volume / avg_volume if avg_volume > 0 else 0
                volume_tl = today_close * today_volume
                
                candle_strength = ((today_close - today_low) / (today_high - today_low)) * 100 if today_high > today_low else 50
                green_candle = today_close > today_open
                
                movers_data.append({
                    'symbol': symbol.replace('.IS', ''), 'full_symbol': symbol,
                    'price': today_close, 'daily_change': daily_change,
                    'volume_tl': volume_tl, 'rvol': rvol,
                    'candle_strength': candle_strength, 'green_candle': green_candle
                })
                
                if (green_candle and candle_strength > 60 and rvol >= 1.2 and
                    daily_change > 0 and daily_change < 9.5 and volume_tl > 2_000_000):
                    tomorrow_candidates.append({
                        'symbol': symbol.replace('.IS', ''), 'full_symbol': symbol,
                        'price': today_close, 'daily_change': daily_change,
                        'rvol': rvol, 'candle_strength': candle_strength
                    })
            except: continue
        
        tomorrow_signals = []
        for candidate in tomorrow_candidates:
            try:
                ticker = yf.Ticker(candidate['full_symbol'])
                hist = ticker.history(period="1y")
                if len(hist) < 50: continue
                
                df = pd.DataFrame({
                    'date': [d.strftime('%Y-%m-%d') for d in hist.index],
                    'open': hist['Open'].values, 'high': hist['High'].values,
                    'low': hist['Low'].values, 'close': hist['Close'].values,
                    'volume': hist['Volume'].values
                })
                
                analysis = analyze_stock(df, timeframe='daily')
                if not analysis: continue
                signal = generate_signal(candidate['full_symbol'], analysis, df)
                if not signal: continue
                
                ts = int(signal['score'])
                
                if ts >= 60:
                    tomorrow_signals.append({
                        'symbol': candidate['symbol'],
                        'price': candidate['price'],
                        'daily_change': candidate['daily_change'],
                        'rvol': candidate['rvol'],
                        'candle_strength': candidate['candle_strength'],
                        'tomorrow_score': ts,
                        'targets': signal.get('targets', {})
                    })
            except: continue
        
        tomorrow_signals.sort(key=lambda x: x['tomorrow_score'], reverse=True)
        top_5_daily = tomorrow_signals[:5]
        
        liquid = [m for m in movers_data if m['volume_tl'] > 1_000_000]
        gainers = sorted([m for m in liquid if m['daily_change'] > 0], key=lambda x: x['daily_change'], reverse=True)[:5]
        losers = sorted([m for m in liquid if m['daily_change'] < 0], key=lambda x: x['daily_change'])[:5]
        total_up = len([m for m in movers_data if m['daily_change'] > 0])
        total_down = len([m for m in movers_data if m['daily_change'] < 0])
        
        msg4 = "PIYASA DURUMU\n"
        msg4 += f"Yukselen: {total_up}\n"
        msg4 += f"Dusen: {total_down}\n\n"
        
        if gainers:
            msg4 += "EN COK YUKSELENLER\n"
            for i, g in enumerate(gainers, 1):
                msg4 += f"{i}. {g['symbol']} +%{g['daily_change']:.2f} ({g['price']:.2f})\n"
            msg4 += "\n"
        
        if losers:
            msg4 += "EN COK DUSENLER\n"
            for i, l in enumerate(losers, 1):
                msg4 += f"{i}. {l['symbol']} %{l['daily_change']:.2f} ({l['price']:.2f})\n"
            msg4 += "\n"
        
        if top_5_daily:
            msg4 += "YARIN ICIN GUNLUK MUM ADAYLARI\n\n"
            for i, t in enumerate(top_5_daily, 1):
                msg4 += f"{i}. {t['symbol']}\n"
                msg4 += f"   Kapanis: {t['price']:.2f} TL\n"
                msg4 += f"   Bugun: +%{t['daily_change']:.2f} | Hacim: {t['rvol']:.1f}x\n"
                targets = t.get('targets', {})
                if targets.get('target_1'):
                    msg4 += f"   Hedef: {targets['target_1']:.2f} (+{targets.get('target_1_pct',0)}%)\n"
                msg4 += "\n"
        
        send_message(msg4)
        
        candidates_4h = get_4h_candidates_for_tomorrow()
        
        msg5 = "4H MUM ONERILERI\nKapanis 4H mum analizi\n\n"
        
        if candidates_4h:
            top_5_4h = candidates_4h[:5]
            
            for i, c in enumerate(top_5_4h, 1):
                dual_tag = ""
                if c.get('is_dual_dip'):
                    dual_tag = " [GUCLU DIP DONUSU]"
                elif c.get('is_dual_signal'):
                    dual_tag = " [CIFTLI DONUS]"
                
                msg5 += f"{i}. {c['symbol']} (Skor: {c['score']}){dual_tag}\n"
                msg5 += f"   4H Kapanis: {c['price']:.2f} TL\n"
                msg5 += f"   RVOL: {c['rvol']:.1f}x | RSI: {c['rsi']:.0f}\n"
                
                targets = c.get('targets', {})
                if targets.get('target_1'):
                    msg5 += f"   Hedef: {targets['target_1']:.2f} (+{targets.get('target_1_pct',0)}%)\n"
                if targets.get('stop_loss'):
                    msg5 += f"   Stop: {targets['stop_loss']:.2f}\n"
                msg5 += "\n"
            
            daily_symbols = set(t['symbol'] for t in top_5_daily)
            fourh_symbols = set(c['symbol'] for c in top_5_4h)
            overlapping = daily_symbols & fourh_symbols
            
            if overlapping:
                msg5 += "CAKISAN HISSELER (EN GUCLU)\nHem gunluk hem 4H onayli\n\n"
                for sym in overlapping:
                    msg5 += f"* {sym} - Cift zaman dilimi onayi\n"
                msg5 += "\n"
        else:
            msg5 += "Guclu 4H aday bulunamadi\n\n"
        
        msg5 += "YARIN STRATEJI\n"
        if bist100:
            trend = bist100.get('trend_status', '')
            if trend in ["GUCLU BOGA", "BOGA"]:
                msg5 += "BIST 100 guclu, AL firsatlarina odaklan\nCakisan hisseler oncelik olsun\n\n"
            elif trend in ["AYI", "GUCLU AYI"]:
                msg5 += "BIST 100 zayif, DIKKATLI ol\nSadece guclu sinyallere gir\n\n"
            else:
                msg5 += "BIST 100 kararsiz, secici ol\n\n"
        
        watchlist = []
        if top_5_daily:
            watchlist.extend([t['symbol'] for t in top_5_daily])
        if candidates_4h:
            for c in candidates_4h[:5]:
                if c['symbol'] not in watchlist:
                    watchlist.append(c['symbol'])
        
        if watchlist:
            msg5 += "YARIN IZLE: " + ", ".join(watchlist[:8]) + "\n\n"
        
        msg5 += "Yarin 09:45'te tekrar!"
        
        send_message(msg5)
        log_event("Gun sonu raporu gonderildi (5 mesaj)")
    except Exception as e:
        log_event(f"Gun sonu hata: {e}")
        send_message(f"Gun sonu hata: {str(e)[:200]}")


def job_full_scan_with_tracking():
    log_event("TAM TARAMA + TAKIP")
    job_full_scan()
    log_event("TAKIP BASLATILIYOR...")
    try:
        from services.signal_tracker import track_signals_job
        track_signals_job()
    except Exception as e:
        send_message(f"Takip hatasi: {str(e)[:200]}")


def setup_scheduler():
    scheduler = BlockingScheduler(timezone='Europe/Istanbul')
    
    scheduler.add_job(job_morning_preparation, CronTrigger(hour=9, minute=45, day_of_week='mon-fri'), id='morning')
    scheduler.add_job(job_premarket_report, CronTrigger(hour=9, minute=55, day_of_week='mon-fri'), id='premarket')
    scheduler.add_job(job_market_open_scan, CronTrigger(hour=10, minute=30, day_of_week='mon-fri'), id='open')
    scheduler.add_job(job_full_scan_2h, CronTrigger(hour=12, minute=0, day_of_week='mon-fri'), id='scan_12')
    scheduler.add_job(job_4h_scan, CronTrigger(hour=14, minute=0, day_of_week='mon-fri'), id='4h_1')
    scheduler.add_job(job_full_scan_2h, CronTrigger(hour=16, minute=0, day_of_week='mon-fri'), id='scan_16')
    scheduler.add_job(job_4h_scan_evening, CronTrigger(hour=18, minute=15, day_of_week='mon-fri'), id='4h_2')
    scheduler.add_job(job_end_of_day_report, CronTrigger(hour=19, minute=0, day_of_week='mon-fri'), id='eod')
    scheduler.add_job(job_weekly_report, CronTrigger(hour=10, minute=0, day_of_week='sat'), id='weekly')
    
    return scheduler


def start_scheduler():
    scheduler = setup_scheduler()
    try:
        send_message(f"BOT AKTIF v2 - {tr_now().strftime('%H:%M - %d.%m.%Y')}\nYeni saatler: 10:30, 12:00, 14:00, 16:00, 18:15, 19:00")
    except: pass
    try: scheduler.start()
    except (KeyboardInterrupt, SystemExit): print("Durduruldu")


if __name__ == "__main__":
    print(f"\nZAMANLAYICI v2 - {tr_now().strftime('%H:%M')}")
    print("\nYENI PROGRAM:")
    print("  09:45 -> Sabah hazirlik")
    print("  09:55 -> Pre-market rapor")
    print("  10:30 -> Acilis taramasi")
    print("  12:00 -> 2. gunluk tarama")
    print("  14:00 -> 1. 4H tarama")
    print("  16:00 -> 3. gunluk tarama")
    print("  18:15 -> 2. 4H tarama (yarin icin)")
    print("  19:00 -> Gun sonu raporu")
    print("  Cumartesi 10:00 -> Haftalik rapor")
    print("\nMANUEL SECENEKLER:")
    print("1->Baslat  2->Sabah  3->PreMarket  4->Acilis  5->2 Saatlik")
    print("6->1. 4H  7->2. 4H Aksam  8->Gun Sonu  9->Haftalik")
    print("10->Saatlik  11->Full Scan  12->Full+Takip")
    
    c = input("\nSecim: ").strip()
    if c=="1": start_scheduler()
    elif c=="2": job_morning_preparation()
    elif c=="3": job_premarket_report()
    elif c=="4": job_market_open_scan()
    elif c=="5": job_full_scan_2h()
    elif c=="6": job_4h_scan()
    elif c=="7": job_4h_scan_evening()
    elif c=="8": job_end_of_day_report()
    elif c=="9": job_weekly_report()
    elif c=="10": job_hourly_scan()
    elif c=="11": job_full_scan()
    elif c=="12": job_full_scan_with_tracking()
