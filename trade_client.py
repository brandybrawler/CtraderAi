import logging
from logging.handlers import RotatingFileHandler
from twisted.internet import reactor, task
from ctrader_fix import *
import pandas as pd
import time
import pandas as pd
from scipy import stats
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from keras.models import Sequential
from keras.layers import LSTM, Dense
import numpy as np
import main


class TradeClient:
    def __init__(self, config):
        self.config = config
        self.client = Client(config["Host"], config["Port"], ssl=config["SSL"])
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger("TradeClient")
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Set up a rotating file handler
        file_handler = RotatingFileHandler("trading.log", maxBytes=1048576, backupCount=5)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def start(self):
        self.client.setConnectedCallback(self.connected)
        self.client.setDisconnectedCallback(self.disconnected)
        self.client.setMessageReceivedCallback(self.onMessageReceived)
        self.client.startService()

        reactor.run()

    def printRequestingMarketData(self):
        print("Requesting market data...")

    def sendMarketDataRequest(self, marketDataRequest):
        try:
            self.client.send(marketDataRequest)
        except TimeoutError:
            self.logger.warning("Timeout occurred when sending market data request")
            # Implement timeout handling logic here
        except ConnectionError:
            self.logger.warning("Connection error occurred")
            # Implement reconnection logic here

    def connected(self, client):
        main.load_config()
        try:
            self.logger.info("Connected to the server at %s:%s", self.config["Host"], self.config["Port"])
            logonRequest = LogonRequest(self.config)
            client.send(logonRequest)

            # Send the market data request
            marketDataRequest = self.createMarketDataRequest(self.config)
            self.printRequestingMarketData()
            client.send(marketDataRequest)

            time.sleep(5)
            
            self.processMarketData(responseMessage=marketDataRequest)
        except Exception as e:
            self.logger.error("Error during connection: %s", str(e))
            # Handle reconnection logic or notify the user here

    def disconnected(self, client, reason):
        self.logger.info("Disconnected, reason: %s", reason)
        # Attempt to reconnect after 5 seconds
        reactor.callLater(5, self.client.startService)

    def onMessageReceived(self, client, responseMessage):
        self.logger.debug("Received: %s", responseMessage.getMessage().replace("�", "|"))
        messageType = responseMessage.getFieldValue(35)
        if messageType == "A":
            self.logger.info("We are logged in")
            self.createNewTrade(client)
        elif messageType == "W":  # MarketDataSnapshotFullRefresh
            self.logger.info("Received market data:")
            self.processMarketData(responseMessage)

    def createNewTrade(self, client):
        newOrderRequest = self.createOrderRequest(self.config)
        client.send(newOrderRequest)

    def createMarketDataRequest(self, config):

        marketDataRequest = MarketDataRequest(config)

        # Set the required parameters for the market data request
        marketDataRequest.MDReqID = "a"
        marketDataRequest.SubscriptionRequestType = "1"
        marketDataRequest.MarketDepth = "0"
        marketDataRequest.NoMDEntryTypes = "1"
        marketDataRequest.MDEntryType = "0"  
        marketDataRequest.NoRelatedSym = "1"
        marketDataRequest.Symbol = "1" 
         
        time.sleep(5)
        #logout = self.Logout(self.config)
        #client.send(logout)
        return marketDataRequest

    def createOrderRequest(self, config):
        newOrderRequest = NewOrderSingle(config)

        # Set the required parameters for the trade
        newOrderRequest.ClOrdID = "a"
        newOrderRequest.Symbol = "1"
        newOrderRequest.Side = "2"
        newOrderRequest.OrderQty = "1000"  # Update the value here
        newOrderRequest.OrdType = "1"

        return newOrderRequest

    def processMarketData(self, responseMessage):
        print("Processing market data.....")
        # Extract and process market data from the response message
        symbol = responseMessage.getFieldValue(55)
        entryTypes = responseMessage.getFieldValues(269)
        prices = responseMessage.getFieldValues(270)
        sizes = responseMessage.getFieldValues(271)

        # Convert market data into a pandas DataFrame
        market_data = pd.DataFrame({
            "Entry Type": entryTypes,
            "Price": prices,
            "Size": sizes
        })

        # Sort the market data by timestamp if available
        market_data.sort_values(by='Timestamp', inplace=True)  # Replace 'Timestamp' with the actual field name

        # Add features or columns for AI model training
        market_data['Price Lag'] = market_data['Price'].shift(1)
        market_data['Price Change'] = market_data['Price'] - market_data['Price Lag']
        market_data['Price Trend'] = np.where(market_data['Price Change'] > 0, 1, 0)

        # Remove any rows with missing or NaN values
        market_data.dropna(inplace=True)

        # Split the data into input features (X) and target variable (y)
        X = market_data[['Entry Type', 'Price Lag', 'Size']]  # Add more features if needed
        y = market_data['Price Trend']

        # Further preprocess the data if necessary, such as scaling or encoding categorical variables
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X)

        # Split the data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

        # Reshape the input data for LSTM model
        X_train = X_train.reshape((X_train.shape[0], 1, X_train.shape[1]))
        X_test = X_test.reshape((X_test.shape[0], 1, X_test.shape[1]))

        # Return the processed data
        return X_train, y_train, X_test, y_test

        
        


    def logMarketData(self, symbol, market_data):
        # Log the market data
        self.logger.info("Symbol: %s", symbol)
        self.logger.info("Market Data:\n%s", market_data.to_string(index=False))
