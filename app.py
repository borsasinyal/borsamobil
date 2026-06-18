"""
Borsa Sinyal Uygulaması - Web Sunucusu
Mobil odaklı, PWA destekli, modern arayüz
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify, request, send_from_directory
from datetime import datetime, timedelta
import pandas as pd

from config import BIST_SYMBOLS
from database import get_connection, get_latest_signals, get_stock_history
from services.analyzer import analyze_stock
from services.signal_engine import generate_signal
from services.scanner import scan_single_stock


app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')


# ════════════════════════════════════════════════
# SAYFA ROUTES (HTML)
# ════════════════════════════════════════════════

@app.route('/')
def home():
    """Ana sayfa - Dashboard"""
    return render_template('index.html')


@app.route('/scanner')
def scanner_page():
    """Tarama sayfası"""
    return render_template('scanner.html')


@app.route('/signals')
def signals_page():
    """Sinyaller sayfası"""
    return render_template('signals.html')


@app.route('/portfolio')
def portfolio_page():
    """Portföy sayfası"""
    return render_template('portfolio.html')


@app.route('/settings')
def settings_page():
    """Ayarlar sayfası"""
    return render_template('settings.html')


@app.route('/stock/<symbol>')
def stock_detail(symbol):
    """Hisse detay sayfası"""
    return render_template('stock_detail.html', symbol=symbol)


# ════════════════════════════════════════════════
# API ROUTES (JSON)
# ════════════════════════════════════════════════

@app.route('/api/signals/latest')
def api_latest_signals():
    """Son sinyalleri getir"""
    limit = request.args.get('limit', 20, type=int)
    signals = get_latest_signals(limit)
    return jsonify(signals)


@app.route('/api/signals/today')
def api_today_signals():
    """Bugünkü sinyalleri getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM signals
        WHERE date(created_at) = date('now')
        ORDER BY score DESC
    """)
    
    signals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(signals)


@app.route('/api/stats')
def api_stats():
    """İstatistikler"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Bugünkü sinyaller
    cursor.execute("""
        SELECT COUNT(*) as count, AVG(score) as avg_score
        FROM signals 
        WHERE date(created_at) = date('now')
    """)
    today = cursor.fetchone()
    
    # Toplam sinyaller
    cursor.execute("SELECT COUNT(*) as count FROM signals")
    total = cursor.fetchone()
    
    # En yüksek skor
    cursor.execute("""
        SELECT symbol, score, price FROM signals
        WHERE date(created_at) = date('now')
        ORDER BY score DESC LIMIT 1
    """)
    top = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'today_count': today['count'] or 0,
        'today_avg_score': round(today['avg_score'] or 0),
        'total_signals': total['count'] or 0,
        'top_signal': dict(top) if top else None
    })


@app.route('/api/stock/<symbol>')
def api_stock_detail(symbol):
    """Tek hisse analizi"""
    full_symbol = f"{symbol}.IS" if not symbol.endswith('.IS') else symbol
    
    data = get_stock_history(full_symbol, days=300)
    
    if not data:
        return jsonify({'error': 'Veri yok'}), 404
    
    df = pd.DataFrame(data)
    analysis = analyze_stock(df)
    
    if not analysis:
        return jsonify({'error': 'Analiz yapılamadı'}), 500
    
    signal = generate_signal(full_symbol, analysis, df)
    
    return jsonify({
        'symbol': symbol,
        'analysis': analysis,
        'signal': signal,
        'history': data[:30]  # Son 30 gün
    })


@app.route('/api/scan')
def api_scan():
    """Anlık tarama yap"""
    from services.scanner import scan_all_stocks
    
    min_score = request.args.get('min_score', 65, type=int)
    
    signals = scan_all_stocks(min_score=min_score, save_to_db=False, verbose=False)
    
    return jsonify({
        'count': len(signals),
        'signals': signals[:20]  # İlk 20
    })


@app.route('/api/portfolio')
def api_portfolio():
    """Portföy getir"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM portfolio
        WHERE status = 'open'
        ORDER BY created_at DESC
    """)
    
    portfolio = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(portfolio)


@app.route('/api/portfolio/add', methods=['POST'])
def api_portfolio_add():
    """Portföye ekle"""
    data = request.json
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO portfolio (symbol, buy_price, quantity, buy_date, status)
        VALUES (?, ?, ?, ?, 'open')
    """, (
        data['symbol'],
        data['buy_price'],
        data['quantity'],
        datetime.now().strftime('%Y-%m-%d')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


# ════════════════════════════════════════════════
# PWA ROUTES
# ════════════════════════════════════════════════

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')


@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')


# ════════════════════════════════════════════════
# ÇALIŞTIR
# ════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 BORSA SİNYAL WEB SUNUCUSU")
    print("="*60)
    print("\n📱 Tarayıcıdan aç:")
    print("   💻 Bilgisayar: http://localhost:5000")
    print("   📱 Telefon   : http://[BILGISAYAR-IP]:5000")
    print("\n⌨️  Durdurmak için: CTRL+C")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)