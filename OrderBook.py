import streamlit as st
import websocket
import threading
import json
import queue
import time

# Thread-safe message queue
msg_queue = queue.Queue()

# UI setup
st.set_page_config(page_title="📊 Order Book Monitor", layout="centered")
st.title("📈 Binance Order Book Monitor")

# Session state setup
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False
if "ws_thread" not in st.session_state:
    st.session_state.ws_thread = None
if "stop_flag" not in st.session_state:
    st.session_state.stop_flag = threading.Event()

# Input controls
coin_symbol = st.text_input("Enter Coin Symbol (e.g., btcusdt):", "btcusdt").lower()
high_ask_threshold = st.number_input("High Ask Threshold (USDT):", value=10000.0, step=100.0)
high_bid_threshold = st.number_input("High Bid Threshold (USDT):", value=10000.0, step=100.0)

# Log placeholder
log_box = st.empty()

# WebSocket background thread
def run_websocket():
    url = f"wss://stream.binance.com:9443/ws/{coin_symbol}@depth"
    try:
        ws = websocket.WebSocketApp(
            url,
            on_open=lambda ws: on_open(ws),
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.run_forever()
    except Exception as e:
        msg_queue.put(f"❌ Thread crashed: {e}")

def on_open(ws):
    sub_msg = {
        "method": "SUBSCRIBE",
        "params": [f"{coin_symbol}@depth"],
        "id": 1
    }
    ws.send(json.dumps(sub_msg))
    msg_queue.put(f"🔗 Connected to WebSocket: {coin_symbol.upper()}")

def on_close(ws, code, msg):
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
    for ask in data.get('a', []):
        price, qty = float(ask[0]), float(ask[1])
        value = price * qty
        if value >= high_ask_threshold:
            logs += f"🔴 High Ask - Price: {price:.2f}, Qty: {qty:.4f}, Value: {value:.2f} USDT\n"

    for bid in data.get('b', []):
        price, qty = float(bid[0]), float(bid[1])
        value = price * qty
        if value >= high_bid_threshold:
            logs += f"🟢 High Bid - Price: {price:.2f}, Qty: {qty:.4f}, Value: {value:.2f} USDT\n"

    if logs:
        msg_queue.put(logs)

# Start/Stop buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 Start Monitoring") and not st.session_state.monitoring:
        st.session_state.stop_flag.clear()
        st.session_state.monitoring = True
        st.session_state.ws_thread = threading.Thread(target=run_websocket, daemon=True)
        st.session_state.ws_thread.start()
        msg_queue.put("✅ Started monitoring...")

with col2:
    if st.button("🛑 Stop Monitoring") and st.session_state.monitoring:
        st.session_state.stop_flag.set()
        st.session_state.monitoring = False
        msg_queue.put("🛑 Stopped monitoring.")

# Show live logs
logs_displayed = ""
while True:
    try:
        msg = msg_queue.get_nowait()
        logs_displayed += msg + "\n"
    except queue.Empty:
        break

if logs_displayed:
    log_box.code(logs_displayed, language="text")
