import streamlit as st
import websocket
import threading
import json
import queue

# 🧠 Thread-safe global message queue
msg_queue = queue.Queue()

# Page setup
st.set_page_config(page_title="📊 Order Book Monitor", layout="centered")
st.title("📈 Binance Order Book Monitor")

# Session state defaults
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False
if "ws_thread" not in st.session_state:
    st.session_state.ws_thread = None
if "stop_flag" not in st.session_state:
    st.session_state.stop_flag = threading.Event()

# Inputs
coin_symbol = st.text_input("Enter Coin Symbol (e.g., btcusdt):", "btcusdt").lower()
high_ask_threshold = st.number_input("High Ask Threshold (USDT):", value=10000.0, step=100.0)
high_bid_threshold = st.number_input("High Bid Threshold (USDT):", value=10000.0, step=100.0)

# Log output area
log_placeholder = st.empty()

# WebSocket Thread
def run_websocket():
    socket_url = f"wss://stream.binance.com:9443/ws/{coin_symbol}@depth"

    try:
        ws = websocket.WebSocketApp(
            socket_url,
            on_open=lambda ws: on_open(ws, coin_symbol),
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.run_forever()
    except Exception as e:
        msg_queue.put(f"❌ Thread crashed: {e}")

def on_open(ws, symbol):
    msg = {
        "method": "SUBSCRIBE",
        "params": [f"{symbol}@depth"],
        "id": 1
    }
    ws.send(json.dumps(msg))
    msg_queue.put(f"🔗 Connected to {symbol.upper()} WebSocket...")

def on_close(ws, close_status_code, close_msg):
    msg_queue.put("🔒 WebSocket closed.")
    st.session_state.monitoring = False

def on_error(ws, error):
    msg_queue.put(f"❌ Error: {error}")

def on_message(ws, message):
    if st.session_state.stop_flag.is_set():
        ws.close()
        return

    data = json.loads(message)
    logs = ""
    if data.get('e') == 'depthUpdate':
        for ask in data.get('a', []):
            price, qty = float(ask[0]), float(ask[1])
            value = price * qty
            if value > high_ask_threshold:
                logs += f"🔴 High Ask - Price: {price:.4f}, Qty: {qty}, 💰Value: {value:.2f} USDT\n"

        for bid in data.get('b', []):
            price, qty = float(bid[0]), float(bid[1])
            value = price * qty
            if value > high_bid_threshold:
                logs += f"🟢 High Bid - Price: {price:.4f}, Qty: {qty}, 💰Value: {value:.2f} USDT\n"

    if logs:
        msg_queue.put(logs)

# Start/Stop buttons
start_col, stop_col = st.columns(2)
with start_col:
    if st.button("🚀 Start Monitoring") and not st.session_state.monitoring:
        st.session_state.monitoring = True
        st.session_state.stop_flag.clear()
        st.session_state.ws_thread = threading.Thread(target=run_websocket)
        st.session_state.ws_thread.start()

with stop_col:
    if st.button("🛑 Stop Monitoring") and st.session_state.monitoring:
        st.session_state.stop_flag.set()
        st.session_state.monitoring = False
        msg_queue.put("🛑 Monitoring stopped by user.")

# Message queue UI update
logs_to_display = ""
while not msg_queue.empty():
    logs_to_display += msg_queue.get() + "\n"
if logs_to_display:
    log_placeholder.code(logs_to_display, language="text")
