import sys
import configparser
import requests
import json
import threading
import os
import re

from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from time import sleep
from random import randint
from requests import RequestException
from bs4 import BeautifulSoup
from datetime import datetime

from src.logger import log

class SteamGifts:
    def __init__(self, cookie, gifts_type, pinned, min_points, sleep_low_points=900, sleep_list_ended=120, webhook_url=""):
        self.cookie = {
            'PHPSESSID': cookie
        }
        self.gifts_type = gifts_type
        self.pinned = pinned
        self.min_points = int(min_points)
        self.sleep_low_points = int(sleep_low_points)
        self.sleep_list_ended = int(sleep_list_ended)

        self.base = "https://www.steamgifts.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        self.filter_url = {
            'All': "search?page=%d",
            'Wishlist': "search?page=%d&type=wishlist",
            'Recommended': "search?page=%d&type=recommended",
            'Copies': "search?page=%d&copy_min=2",
            'DLC': "search?page=%d&dlc=true",
            'New': "search?page=%d&type=new"
        }
        self.running = False
        self.history_file = "data/history.json"
        
        self.webhook_urls = [u.strip() for u in webhook_url.split(',')] if webhook_url else []

    def requests_retry_session(
        self,
        retries=5,
        backoff_factor=0.3
    ):
        session = self.session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(500, 502, 504),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def get_soup_from_page(self, url):
        r = self.requests_retry_session().get(url, cookies=self.cookie)
        soup = BeautifulSoup(r.text, 'html.parser')
        return soup

    def update_info(self):
        soup = self.get_soup_from_page(self.base)

        try:
            self.xsrf_token = soup.find('input', {'name': 'xsrf_token'})['value']
            self.points = int(soup.find('span', {'class': 'nav__points'}).text)  # storage points
        except TypeError:
            log("⛔  Cookie is not valid (or Cloudflare verification blocked us). Check logs or update PHPSESSID.", "red")
            if soup.title:
                log(f"Page title was: {soup.title.text.strip()}", "red")
            self.running = False

    def sleep_with_check(self, seconds):
        if not self.running:
            return
        sleep_interval = 1
        elapsed = 0
        while elapsed < seconds and self.running:
            sleep(sleep_interval)
            elapsed += sleep_interval

    def record_history(self, game_name, game_cost, game_link, image_url):
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                pass
        
        history.append({
            "name": game_name,
            "cost": game_cost,
            "link": game_link,
            "image": image_url,
            "date": datetime.now().isoformat()
        })

        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

    def dispatch_webhooks(self, game_name, game_cost, game_link, image_url):
        payload = {
            "content": "",
            "tts": False,
            "embeds": [
                {
                    "description": f"Cost: **{game_cost} P**",
                    "fields": [],
                    "author": {
                        "name": "Steam Gifts Bot",
                        "icon_url": image_url if image_url else ""
                    },
                    "title": f"Giveaway Entered: {game_name}",
                    "url": game_link,
                    "image": {
                        "url": image_url if image_url else ""
                    },
                    "thumbnail": {
                        "url": image_url if image_url else ""
                    }
                }
            ],
            "components": [],
            "actions": {},
            "flags": 0,
            "username": "Steam Gifts Bot",
            "avatar_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRW9I42jCj0xWN8ZhM_uEGT08icJv0OUD5Wsg&s"
        }

        for url in self.webhook_urls:
            try:
                if url.startswith('tgram://'):
                    parts = url.split('/')
                    token = parts[2]
                    chat_id = parts[3]
                    txt = f"🎉 Successfully entered **{game_name}** ({game_cost} P)\n{game_link}"
                    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": txt, "parse_mode": "Markdown"})
                elif url.startswith('discord://'):
                    pass # Handled below
                else: 
                    requests.post(url.replace('json://', 'http://').replace('jsons://', 'https://'), json=payload)
            except Exception as e:
                log(f"Dispatch error for {url}: {str(e)}", "red")

    def get_game_content(self, page=1):
        n = page
        while self.running:
            txt = "⚙️  Retrieving games from %d page." % n
            log(txt, "magenta")

            filtered_url = self.filter_url[self.gifts_type] % n
            paginated_url = f"{self.base}/giveaways/{filtered_url}"

            soup = self.get_soup_from_page(paginated_url)

            game_list = soup.find_all('div', {'class': 'giveaway__row-inner-wrap'})

            if not len(game_list):
                log("⛔  Page is empty. Please, select another type.", "red")
                self.running = False
                break

            for item in game_list:
                if not self.running:
                    return

                if len(item.get('class', [])) == 2 and not self.pinned:
                    continue

                if self.points == 0 or self.points < self.min_points:
                    txt = f"🛋️  Sleeping due to low points! We have {self.points} points, but we need {self.min_points} to start."
                    log(txt, "yellow")
                    self.sleep_with_check(self.sleep_low_points)
                    if not self.running:
                        return
                    self.start()
                    return

                game_cost = item.find_all('span', {'class': 'giveaway__heading__thin'})[-1]

                if game_cost:
                    game_cost = game_cost.getText().replace('(', '').replace(')', '').replace('P', '')
                else:
                    continue

                game_name = item.find('a', {'class': 'giveaway__heading__name'}).text

                if self.points - int(game_cost) < 0:
                    txt = f"⛔ Not enough points to enter: {game_name}"
                    log(txt, "red")
                    continue

                elif self.points - int(game_cost) >= 0:
                    game_href = item.find('a', {'class': 'giveaway__heading__name'})['href']
                    game_id = game_href.split('/')[2]
                    game_link = self.base + game_href

                    # Extract image
                    image_url = ""
                    img_match = re.search(r'url\((https?://[^)]+/(?:apps|subs)/[^)]+)\)', str(item))
                    if img_match:
                        image_url = img_match.group(1)

                    res = self.entry_gift(game_id)
                    if res:
                        self.points -= int(game_cost)
                        txt = f"🎉 One more game! Has just entered {game_name}"
                        log(txt, "green")
                        self.record_history(game_name, int(game_cost), game_link, image_url)
                        
                        try:
                            self.dispatch_webhooks(game_name, game_cost, game_link, image_url)
                        except Exception as e:
                            log(f"Webhook error: {str(e)}", "red")

                        self.sleep_with_check(randint(3, 7))

            n = n+1


        if not self.running:
            return

        log(f"🛋️  List of games is ended. Waiting {self.sleep_list_ended} seconds to update...", "yellow")
        self.sleep_with_check(self.sleep_list_ended)
        if self.running:
            self.start()

    def entry_gift(self, game_id):
        payload = {'xsrf_token': self.xsrf_token, 'do': 'entry_insert', 'code': game_id}
        entry = self.requests_retry_session().post('https://www.steamgifts.com/ajax.php', data=payload, cookies=self.cookie)
        try:
            json_data = json.loads(entry.text)
            if json_data['type'] == 'success':
                return True
        except:
            pass
        return False

    def start(self):
        if not self.running:
            self.running = True

        self.update_info()

        if not self.running:
            return

        if self.points > 0:
            txt = "🤖 Hoho! I am back! You have %d points. Lets hack." % self.points
            log(txt, "blue")

        self.get_game_content()

    def stop(self):
        self.running = False
        log("⛔ Bot stopping gracefully...", "red")
