import collections
from datetime import datetime

class WebLogger:
    def __init__(self, maxlen=1000):
        self.logs = collections.deque(maxlen=maxlen)
        self.listeners = []

    def log(self, message, color="white"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "message": message,
            "color": color
        }
        self.logs.append(log_entry)
        for listener in self.listeners:
            try:
                listener(log_entry)
            except Exception:
                pass

    def get_logs(self):
        return list(self.logs)

    def add_listener(self, listener):
        if listener not in self.listeners:
            self.listeners.append(listener)

    def remove_listener(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)

web_logger = WebLogger()

def log(string, color="white", font=None, figlet=False):
    # Print to standard output as well for docker logs
    print(f"[{color.upper()}] {string}")
    web_logger.log(string, color)
