import time

def telegram_log(message):
    print(f"[Telegram Notifier]: {message}")

class DiscordNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url

    def send_log(self, message):
        print(f"[Discord Log]: {message}")

    def notify_trade(self, trade_details):
        print(f"[Discord Alert] Trade Executed: {trade_details}")

# Expose a global default notifier for compatibility
discord_bot = DiscordNotifier()
