import requests

class DiscordNotifier:
    def __init__(self, config):
        self.webhook_url = config.get("discord", "webhook_url")

    def notify(self, trade_result, prediction):
        # Send trade_result and prediction to Discord channel here
        pass
