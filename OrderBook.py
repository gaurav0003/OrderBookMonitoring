import streamlit as st
import websocket
import threading
import json
import queue
import time

st.set_page_config(page_title="📊 Order Book Monitor", layout="centered")

st.title("📈 Binance Order Book Monitor")

# Session state setup
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False
if "ws_thread" not in st.session_state:
    st.session_state.ws_thread = None
if "stop_flag" not in st.session_state:
    st.session_state.stop_flag = threading.Event()
if "msg_queue" not in st.session_state:
    st.session_state.msg_queue = queue.Queue()

# Inputs
coin_symbol = st.text_input("Enter Coin Symbol (e.g., btcusdt):", "btcusdt").lower()
high_ask_threshold = st.number_input("High Ask Threshold (USDT):", value=10000.0, step=100.0)
high_bid_threshold = st.number_input("High Bid Threshold (USDT):", value=10000.0, step=100.0)

# Log area
log_placeholder = st.empty()

def run_websocket():
    socket_url = f"wss://stream.binance.com:9443/ws/{coin_symbol}@depth"
    try:
        ws = websocket.WebSocketApp(
            socket_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.on_open = lambda ws: on_open(ws, coin_symbol)
        ws.run_forever()
    except Exception as e:
        st.session_state.msg_queue.put(f"❌ Thread crashed: {e}")

def on_open(ws, symbol):
    msg = {
        "method": "SUBSCRIBE",
        "params": [f"{symbol}@depth"],
        "id": 1
    }
    ws.send(json.dumps(msg))
    st.session_state.msg_queue.put(f"🔗 Connected to {symbol.upper()} WebSocket...")

def on_close(ws, close_status_code, close_msg):
    st.session_state.msg_queue.put("🔒 WebSocket closed.")
    st.session_state.monitoring = False

def on_error(ws, error):
    st.session_state.msg_queue.put(f"❌ Error: {error}")

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
        st.session_state.msg_queue.put(logs)

# UI buttons
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
        st.session_state.msg_queue.put("🛑 Monitoring stopped.")

# Message Queue Display
while not st.session_state.msg_queue.empty():
    msg = st.session_state.msg_queue.get()
    log_placeholder.code(msg, language="text")
