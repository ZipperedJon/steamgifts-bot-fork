from flask import Flask, render_template, request, jsonify, Response
import threading
import json
import os
import time
import requests

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
        "date_format": "US",
        "timezone": "UTC",
        "discord_webhook": "",
        "telegram_token": "",
        "telegram_chat_id": "",
        "n8n_webhook": "",
        "auto_start": False,
        "safety_check": True
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def run_bot(cookie, gift_type, pinned, min_points, sleep_low_points, sleep_list_ended, webhook_url, safety_check):
    global bot_instance
    try:
        bot_instance = SteamGifts(cookie, gift_type, pinned, min_points, sleep_low_points, sleep_list_ended, webhook_url, safety_check)
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

@app.route('/api/test_notification', methods=['POST'])
def test_notification():
    data = request.json
    
    urls = []
    if data.get("discord_webhook"):
        urls.append(data.get("discord_webhook"))
    if data.get("telegram_token") and data.get("telegram_chat_id"):
        urls.append(f"tgram://{data.get('telegram_token')}/{data.get('telegram_chat_id')}")
    if data.get("n8n_webhook"):
        n8n = data.get("n8n_webhook")
        if n8n.startswith("http://"): n8n = "n8n://" + n8n[7:]
        elif n8n.startswith("https://"): n8n = "n8ns://" + n8n[8:]
        urls.append(n8n)
        
    if not urls:
        return jsonify({"status": "error", "message": "No valid webhooks provided."})
      
    image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRW9I42jCj0xWN8ZhM_uEGT08icJv0OUD5Wsg&s"
    payload = {
        "content": "",
        "tts": False,
        "embeds": [
            {
                "description": "Cost: **10 P**",
                "fields": [],
                "author": {
                    "name": "Steam Gifts Bot",
                    "icon_url": image_url
                },
                "title": f"Giveaway Entered: TEST GAME NAME",
                "url": "https://steamgifts.com/",
                "image": {
                    "url": image_url
                },
                "thumbnail": {
                    "url": image_url
                }
            }
        ],
        "components": [],
        "actions": {},
        "flags": 0,
        "username": "Steam Gifts Bot",
        "avatar_url": image_url
    }
    
    try:
        for url in urls:
            if url.startswith('tgram://'):
                parts = url.split('/')
                token = parts[2]
                chat_id = parts[3]
                txt = f"🎉 Successfully entered **TEST GAME NAME** (10 P)\nhttps://steamgifts.com/"
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": txt, "parse_mode": "Markdown"})
            elif url.startswith('n8n://') or url.startswith('n8ns://'):
                pure_url = url.replace('n8n://', 'http://').replace('n8ns://', 'https://')
                requests.post(pure_url, json={
                    "Game Name": "TEST GAME NAME",
                    "Points used": 10,
                    "Thumbnail URL": image_url,
                    "Link to giveaway URL": "https://steamgifts.com/"
                })
            else: 
                requests.post(url.replace('json://', 'http://').replace('jsons://', 'https://'), json=payload)
                
        return jsonify({"status": "success", "message": "Test notifications transmitted successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/history', methods=['DELETE'])
def clear_history():
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return jsonify({"status": "success", "message": "History cleared."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
        
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

    urls = []
    if config.get("discord_webhook"):
        urls.append(config.get("discord_webhook"))
    if config.get("telegram_token") and config.get("telegram_chat_id"):
        urls.append(f"tgram://{config.get('telegram_token')}/{config.get('telegram_chat_id')}")
    if config.get("n8n_webhook"):
        n8n = config.get("n8n_webhook")
        if n8n.startswith("http://"): n8n = "n8n://" + n8n[7:]
        elif n8n.startswith("https://"): n8n = "n8ns://" + n8n[8:]
        urls.append(n8n)

    bot_thread = threading.Thread(
        target=run_bot, 
        args=(config['cookie'], config['gift_type'], config['pinned'], config['min_points'], config.get('sleep_low_points', 900), config.get('sleep_list_ended', 120), ','.join(urls), config.get('safety_check', True))
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

def auto_start_bot():
    """Check config and auto-start the bot if enabled."""
    global bot_thread
    config = load_config()
    if config.get('auto_start') and config.get('cookie'):
        log("Auto-start enabled. Starting bot...", "green")
        urls = []
        if config.get("discord_webhook"):
            urls.append(config.get("discord_webhook"))
        if config.get("telegram_token") and config.get("telegram_chat_id"):
            urls.append(f"tgram://{config.get('telegram_token')}/{config.get('telegram_chat_id')}")
        if config.get("n8n_webhook"):
            n8n = config.get("n8n_webhook")
            if n8n.startswith("http://"): n8n = "n8n://" + n8n[7:]
            elif n8n.startswith("https://"): n8n = "n8ns://" + n8n[8:]
            urls.append(n8n)

        bot_thread = threading.Thread(
            target=run_bot,
            args=(config['cookie'], config['gift_type'], config['pinned'], config['min_points'], config.get('sleep_low_points', 900), config.get('sleep_list_ended', 120), ','.join(urls), config.get('safety_check', True))
        )
        bot_thread.daemon = True
        bot_thread.start()

if __name__ == '__main__':
    auto_start_bot()
    app.run(host='0.0.0.0', port=1738, threaded=True)
