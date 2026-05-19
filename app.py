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

bot_threads = {}
bot_instances = {}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            if 'accounts' not in data:
                # Migrate old config
                new_data = {
                    "accounts": [],
                    "global": {
                        "date_format": data.get("date_format", "US"),
                        "timezone": data.get("timezone", "UTC"),
                        "discord_webhook": data.get("discord_webhook", ""),
                        "telegram_token": data.get("telegram_token", ""),
                        "telegram_chat_id": data.get("telegram_chat_id", ""),
                        "n8n_webhook": data.get("n8n_webhook", "")
                    }
                }
                if data.get("cookie"):
                    new_data["accounts"].append({
                        "id": "1",
                        "name": "Main",
                        "cookie": data.get("cookie", ""),
                        "gift_type": data.get("gift_type", "All"),
                        "pinned": data.get("pinned", False),
                        "min_points": data.get("min_points", 10),
                        "sleep_low_points": data.get("sleep_low_points", 900),
                        "sleep_list_ended": data.get("sleep_list_ended", 120),
                        "safety_check": data.get("safety_check", True),
                        "auto_start": data.get("auto_start", False)
                    })
                save_config(new_data)
                return new_data
            return data
    return {
        "accounts": [],
        "global": {
            "date_format": "US",
            "timezone": "UTC",
            "discord_webhook": "",
            "telegram_token": "",
            "telegram_chat_id": "",
            "n8n_webhook": ""
        }
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def run_bot(account_id, account_name, cookie, gift_type, pinned, min_points, sleep_low_points, sleep_list_ended, webhook_url, safety_check):
    global bot_instances
    try:
        bot_instances[account_id] = SteamGifts(cookie, gift_type, pinned, min_points, sleep_low_points, sleep_list_ended, webhook_url, safety_check, account_id, account_name)
        bot_instances[account_id].start()
    except Exception as e:
        log(f"Bot error ({account_name}): {str(e)}", "red")
    finally:
        if account_id in bot_instances:
            del bot_instances[account_id]

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
                "description": "Cost: **10 P**\nAccount: **Test Account**",
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
                txt = f"🎉 Successfully entered **TEST GAME NAME** (10 P) on account **Test Account**\nhttps://steamgifts.com/"
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": txt, "parse_mode": "Markdown"})
            elif url.startswith('n8n://') or url.startswith('n8ns://'):
                pure_url = url.replace('n8n://', 'http://').replace('n8ns://', 'https://')
                requests.post(pure_url, json={
                    "Game Name": "TEST GAME NAME",
                    "Points used": 10,
                    "Account Name": "Test Account",
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
    status_data = {}
    config = load_config()
    for acc in config.get('accounts', []):
        acc_id = acc['id']
        is_running = acc_id in bot_threads and bot_threads[acc_id].is_alive()
        points = bot_instances[acc_id].points if acc_id in bot_instances and hasattr(bot_instances[acc_id], 'points') else 0
        status_data[acc_id] = {"running": is_running, "points": points}
    return jsonify(status_data)

@app.route('/api/start', methods=['POST'])
def start_bot():
    global bot_threads, bot_instances
    data = request.json
    account_id = data.get('account_id')
    
    if not account_id:
        return jsonify({"status": "error", "message": "No account_id provided"})

    if account_id in bot_threads and bot_threads[account_id].is_alive():
        return jsonify({"status": "error", "message": "Bot is already running"})
    
    config = load_config()
    account = next((a for a in config.get('accounts', []) if a['id'] == account_id), None)
    
    if not account:
        return jsonify({"status": "error", "message": "Account not found"})
        
    if not account.get('cookie'):
        return jsonify({"status": "error", "message": "No cookie (PHPSESSID) configured for this account."})

    global_config = config.get('global', {})
    urls = []
    if global_config.get("discord_webhook"):
        urls.append(global_config.get("discord_webhook"))
    if global_config.get("telegram_token") and global_config.get("telegram_chat_id"):
        urls.append(f"tgram://{global_config.get('telegram_token')}/{global_config.get('telegram_chat_id')}")
    if global_config.get("n8n_webhook"):
        n8n = global_config.get("n8n_webhook")
        if n8n.startswith("http://"): n8n = "n8n://" + n8n[7:]
        elif n8n.startswith("https://"): n8n = "n8ns://" + n8n[8:]
        urls.append(n8n)

    thread = threading.Thread(
        target=run_bot, 
        args=(account['id'], account['name'], account['cookie'], account['gift_type'], account['pinned'], account['min_points'], account.get('sleep_low_points', 900), account.get('sleep_list_ended', 120), ','.join(urls), account.get('safety_check', True))
    )
    thread.daemon = True
    bot_threads[account_id] = thread
    thread.start()
    
    return jsonify({"status": "success"})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    global bot_instances
    data = request.json
    account_id = data.get('account_id')
    
    if not account_id:
        return jsonify({"status": "error", "message": "No account_id provided"})
        
    if account_id in bot_instances:
        bot_instances[account_id].stop()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Bot is not running"})

@app.route('/api/start_all', methods=['POST'])
def start_all_bots():
    global bot_threads, bot_instances
    
    config = load_config()
    accounts = config.get('accounts', [])
    if not accounts:
        return jsonify({"status": "error", "message": "No accounts configured"})
        
    global_config = config.get('global', {})
    urls = []
    if global_config.get("discord_webhook"):
        urls.append(global_config.get("discord_webhook"))
    if global_config.get("telegram_token") and global_config.get("telegram_chat_id"):
        urls.append(f"tgram://{global_config.get('telegram_token')}/{global_config.get('telegram_chat_id')}")
    if global_config.get("n8n_webhook"):
        n8n = global_config.get("n8n_webhook")
        if n8n.startswith("http://"): n8n = "n8n://" + n8n[7:]
        elif n8n.startswith("https://"): n8n = "n8ns://" + n8n[8:]
        urls.append(n8n)
        
    started = 0
    for account in accounts:
        account_id = account['id']
        if not account.get('cookie'):
            continue
        if account_id in bot_threads and bot_threads[account_id].is_alive():
            continue
            
        thread = threading.Thread(
            target=run_bot, 
            args=(account['id'], account['name'], account['cookie'], account['gift_type'], account['pinned'], account['min_points'], account.get('sleep_low_points', 900), account.get('sleep_list_ended', 120), ','.join(urls), account.get('safety_check', True))
        )
        thread.daemon = True
        bot_threads[account_id] = thread
        thread.start()
        started += 1
        
    return jsonify({"status": "success", "started": started})

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
    global bot_threads
    config = load_config()
    global_config = config.get('global', {})
    
    urls = []
    if global_config.get("discord_webhook"):
        urls.append(global_config.get("discord_webhook"))
    if global_config.get("telegram_token") and global_config.get("telegram_chat_id"):
        urls.append(f"tgram://{global_config.get('telegram_token')}/{global_config.get('telegram_chat_id')}")
    if global_config.get("n8n_webhook"):
        n8n = global_config.get("n8n_webhook")
        if n8n.startswith("http://"): n8n = "n8n://" + n8n[7:]
        elif n8n.startswith("https://"): n8n = "n8ns://" + n8n[8:]
        urls.append(n8n)

    for account in config.get('accounts', []):
        if account.get('cookie') and account.get('auto_start'):
            log(f"Auto-start enabled. Starting bot for {account['name']}...", "green")
            thread = threading.Thread(
                target=run_bot,
                args=(account['id'], account['name'], account['cookie'], account['gift_type'], account['pinned'], account['min_points'], account.get('sleep_low_points', 900), account.get('sleep_list_ended', 120), ','.join(urls), account.get('safety_check', True))
            )
            thread.daemon = True
            bot_threads[account['id']] = thread
            thread.start()

if __name__ == '__main__':
    auto_start_bot()
    app.run(host='0.0.0.0', port=1738, threaded=True)
