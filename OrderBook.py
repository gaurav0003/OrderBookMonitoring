import streamlit as st
import websocket
import threading
import json
import time

st.set_page_config(page_title="📊 Order Book Monitor", layout="centered")

st.title("📈 Binance Order Book Monitor")

# Initialize session state
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

# Log display
log_placeholder = st.empty()

# Start Monitoring Button
start_col, stop_col = st.columns(2)
with start_col:
    if st.button("🚀 Start Monitoring") and not st.session_state.monitoring:
        st.session_state.monitoring = True
        st.session_state.stop_flag.clear()

        def run_websocket():
            socket_url = f"wss://stream.binance.com:9443/ws/{coin_symbol}@depth"
            ws = websocket.WebSocketApp(
                socket_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.on_open = lambda ws: on_open(ws, coin_symbol)
            ws.run_forever()

        def on_message(ws, message):
            if st.session_state.stop_flag.is_set():
                ws.close()
                return

            data = json.loads(message)
            logs = ""
            if 'e' in data and data['e'] == 'depthUpdate':
                asks = data['a']
                bids = data['b']

                for ask in asks:
                    price = float(ask[0])
                    quantity = float(ask[1])
                    value = price * quantity
                    if value > high_ask_threshold:
                        logs += f"🔴 High Ask - Price: {price:.4f}, Qty: {quantity}, 💰Value: {value:.2f} USDT\n"

                for bid in bids:
                    price = float(bid[0])
                    quantity = float(bid[1])
                    value = price * quantity
                    if value > high_bid_threshold:
                        logs += f"🟢 High Bid - Price: {price:.4f}, Qty: {quantity}, 💰Value: {value:.2f} USDT\n"

            if logs:
                log_placeholder.code(logs, language="text")

        def on_error(ws, error):
            log_placeholder.error(f"❌ Error: {error}")

        def on_close(ws, close_status_code, close_msg):
            log_placeholder.warning("🔒 WebSocket closed.")
            st.session_state.monitoring = False

        def on_open(ws, symbol):
            subscribe_message = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol}@depth"],
                "id": 1
            }
            ws.send(json.dumps(subscribe_message))
            log_placeholder.info(f"🔗 Connected to WebSocket for {symbol.upper()}...")

        # Start thread
        st.session_state.ws_thread = threading.Thread(target=run_websocket)
        st.session_state.ws_thread.start()

# Stop Monitoring Button
with stop_col:
    if st.button("🛑 Stop Monitoring") and st.session_state.monitoring:
        st.session_state.stop_flag.set()
        st.session_state.monitoring = False
        log_placeholder.info("🛑 Monitoring stopped.")
