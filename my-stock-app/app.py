from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import datetime
import pytz
import uuid
import os
from flask import send_from_directory

app = Flask(__name__)
CORS(app)

# 模擬台股清單
STOCK_LIST = [
    {"id": "2330", "name": "台積電"},
    {"id": "2317", "name": "鴻海"},
    {"id": "2454", "name": "聯發科"},
    {"id": "2303", "name": "聯電"},
    {"id": "2881", "name": "富邦金"},
    {"id": "2882", "name": "國泰金"},
    {"id": "2603", "name": "長榮"},
    {"id": "2308", "name": "台達電"},
    {"id": "2412", "name": "中華電"},
    {"id": "1301", "name": "台塑"},
]

# 用於模擬持倉與交易紀錄
portfolio = {}
trade_history = []
order_book = []  # 掛單簿

# 產生模擬日K線資料
def generate_kline(stock_id, days=60):
    base_price = random.randint(50, 600)
    today = datetime.date.today()
    kline = []
    price = base_price
    for i in range(days):
        date = today - datetime.timedelta(days=days - i)
        open_p = price + random.uniform(-3, 3)
        close_p = open_p + random.uniform(-5, 5)
        high_p = max(open_p, close_p) + random.uniform(0, 3)
        low_p = min(open_p, close_p) - random.uniform(0, 3)
        volume = random.randint(1000, 10000)
        kline.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": volume
        })
        price = close_p
    return kline

# 撮合掛單（市價觸及即成交）
def match_orders(stock_id, kline):
    global order_book, portfolio, trade_history
    last_price = kline[-1]['close']
    matched = []
    for order in order_book:
        if order['stock_id'] != stock_id or order['status'] != 'open':
            continue
        # 買單：市價<=掛單價，賣單：市價>=掛單價
        if order['action'] == 'buy' and last_price <= order['price']:
            matched.append(order)
        elif order['action'] == 'sell' and last_price >= order['price']:
            matched.append(order)
    for order in matched:
        # 成交，更新持倉與歷史
        if order['stock_id'] not in portfolio:
            portfolio[order['stock_id']] = 0
        if order['action'] == 'buy':
            portfolio[order['stock_id']] += order['quantity']
        elif order['action'] == 'sell':
            portfolio[order['stock_id']] -= order['quantity']
            if portfolio[order['stock_id']] < 0:
                portfolio[order['stock_id']] = 0
        trade_history.append({
            "date": order['date'],
            "stock_id": order['stock_id'],
            "action": order['action'],
            "price": order['price'],
            "quantity": order['quantity'],
            "matched": True
        })
        order['status'] = 'matched'

@app.route('/api/stocks')
def get_stocks():
    return jsonify(STOCK_LIST)

@app.route('/api/kline/<stock_id>')
def get_kline(stock_id):
    kline = generate_kline(stock_id)
    match_orders(stock_id, kline)
    return jsonify(kline)

@app.route('/api/trade', methods=['POST'])
def trade():
    # 台股交易時段：週一至週五 09:00~13:30（台北時間）
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.datetime.now(tz)
    if now.weekday() >= 5 or not (now.hour > 9 or (now.hour == 9 and now.minute >= 0)) or (now.hour > 13 or (now.hour == 13 and now.minute > 30)):
        return jsonify({"status": "fail", "msg": "非台股交易時段（週一至週五 09:00~13:30）不可下單"}), 403
    data = request.json
    stock_id = data.get('stock_id')
    action = data.get('action')  # 'buy' or 'sell'
    price = data.get('price')
    quantity = data.get('quantity')
    date = datetime.date.today().strftime("%Y-%m-%d")
    # 掛單進 order_book
    order = {
        "id": str(uuid.uuid4()),
        "date": date,
        "stock_id": stock_id,
        "action": action,
        "price": price,
        "quantity": quantity,
        "matched": False,
        "status": "open"
    }
    order_book.append(order)
    return jsonify({"status": "success", "msg": "已掛單，待市價觸及自動成交"})

@app.route('/api/orders')
def get_orders():
    stock_id = request.args.get('stock_id')
    if stock_id:
        return jsonify([o for o in order_book if o['stock_id'] == stock_id and o['status'] == 'open'])
    return jsonify([o for o in order_book if o['status'] == 'open'])

@app.route('/api/cancel_order/<order_id>', methods=['POST'])
def cancel_order(order_id):
    for o in order_book:
        if o['id'] == order_id and o['status'] == 'open':
            o['status'] = 'canceled'
            return jsonify({"status": "success", "msg": "已取消掛單"})
    return jsonify({"status": "fail", "msg": "找不到可取消的掛單"}), 404

@app.route('/api/portfolio')
def get_portfolio():
    # 查詢目前持倉與交易紀錄
    result = []
    for stock in STOCK_LIST:
        qty = portfolio.get(stock["id"], 0)
        if qty > 0:
            result.append({"stock_id": stock["id"], "name": stock["name"], "quantity": qty})
    return jsonify({"portfolio": result, "trade_history": trade_history})


@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')


if __name__ == '__main__':
    app.run(debug=True) 