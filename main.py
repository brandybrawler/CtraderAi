import logging
import json
import signal
from twisted.internet import reactor
from trade_client import *

IsTradeAcc = False

def load_config():
    global IsTradeAcc
    if IsTradeAcc:
        with open('config-trade.json', 'r') as file:
            config = json.load(file)

    else:
        with open("config-quote.json") as configFile:
            config = json.load(configFile)
    return config


def shutdown_handler(signum, frame):
    # Handle program shutdown here
    reactor.stop()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # Load configuration
    config = load_config()

    # Create an instance of the TradeClient class
    trade_client = TradeClient(config)

    # Set up shutdown signal handler
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        # Start the TradeClient
        trade_client.start()

        # Run the Twisted reactor
        reactor.run()
    except Exception as e:
        logger.exception("An error occurred: %s", str(e))
        # Perform any necessary cleanup or error handling here
    finally:
        # Perform any necessary cleanup here
        pass
