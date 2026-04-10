from flask import Flask, render_template, request, jsonify, Response
import threading
import json
import os
import time

from src.main import SteamGifts
from src.logger import web_logger, log

app = Flask(__name__)

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

CONFIG_FILE = 'data/config.json'
HISTORY_FILE = 'data/history.json'

bot_thread = None
bot_instance = None

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "cookie": "",
        "gift_type": "All",
        "pinned": False,
        "min_points": 10,
        "sleep_low_points": 900,
        "sleep_list_ended": 120,
        "date_format": "US"
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def run_bot(cookie, gift_type, pinned, min_points, sleep_low_points, sleep_list_ended):
    global bot_instance
    try:
        bot_instance = SteamGifts(cookie, gift_type, pinned, min_points, sleep_low_points, sleep_list_ended)
        bot_instance.start()
    except Exception as e:
        log(f"Bot error: {str(e)}", "red")
    finally:
        bot_instance = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        data = request.json
        save_config(data)
        return jsonify({"status": "success", "config": data})
    else:
        return jsonify(load_config())

@app.route('/api/status', methods=['GET'])
def get_status():
    is_running = bot_thread is not None and bot_thread.is_alive()
    points = bot_instance.points if bot_instance and hasattr(bot_instance, 'points') else 0
    return jsonify({"running": is_running, "points": points})

@app.route('/api/start', methods=['POST'])
def start_bot():
    global bot_thread, bot_instance
    if bot_thread is not None and bot_thread.is_alive():
        return jsonify({"status": "error", "message": "Bot is already running"})
    
    config = load_config()
    if not config.get('cookie'):
        return jsonify({"status": "error", "message": "No cookie (PHPSESSID) configured."})

    bot_thread = threading.Thread(
        target=run_bot, 
        args=(config['cookie'], config['gift_type'], config['pinned'], config['min_points'], config.get('sleep_low_points', 900), config.get('sleep_list_ended', 120))
    )
    bot_thread.daemon = True
    bot_thread.start()
    
    return jsonify({"status": "success"})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    global bot_instance
    if bot_instance:
        bot_instance.stop()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Bot is not running"})

@app.route('/api/history', methods=['GET'])
def get_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route('/api/logs')
def stream_logs():
    def generate():
        last_yielded = -1
        while True:
            current_logs = web_logger.get_logs()
            if len(current_logs) > last_yielded + 1:
                # new logs available
                for i in range(last_yielded + 1, len(current_logs)):
                    log_obj = current_logs[i]
                    yield f"data: {json.dumps(log_obj)}\n\n"
                last_yielded = len(current_logs) - 1
            time.sleep(0.5)
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1738, threaded=True)
