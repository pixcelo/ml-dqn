import configparser
from trade import Trade
from predict import Predictor
from logger import Logger
from discord_notifier import DiscordNotifier
import time

def main():
    # Read configuration
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Initialize components
    trade = Trade(config)
    predictor = Predictor(config)
    logger = Logger()
    discord_notifier = DiscordNotifier(config)

    # Main loop
    while True:
        # Get market data
        market_data = trade.get_market_data()

        # Make predictions
        prediction = predictor.predict(market_data)
        print(prediction)

        time.sleep(2)

        # Execute trade
        # trade_result = trade.execute_trade(prediction)

        # Log and notify
        # logger.log(trade_result, prediction)
        # discord_notifier.notify(trade_result, prediction)

if __name__ == "__main__":
    main()
