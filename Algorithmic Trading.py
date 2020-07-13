"""
This script simulates buying and selling stocks by using a moving average algorithm to determine
whether a stock is worth buying. If the stock is owned, it also applies the same algorithm to 
determine if it is best to sell. You can manually sell stocks by pressing ctrl+shift

Available exchanges/locations: NYSE, Nasdaq, Canadian Stocks

Remember to set initial settings.
"""
#Imports
import yfinance as yf
import pandas as pd
import numpy as np
from pandas import read_csv
from pandas_datareader import data as pdr
from collections import defaultdict 

import time
import math
import csv
import sys
import json
import keyboard
import requests
from io import StringIO

import datetime
import pytz

from colorama import Fore, Back, Style
import colorama
colorama.init()


#Set initial investment
initial_investment = 5000
sell_list = list()
#Load previously owned stocks

def saveStocks():
	with open('owned_stocks.json','w') as fp:
		json.dump(owned_stocks, fp)

try:
	with open('owned_stocks.json', 'r') as fp:
		temp = json.load(fp)
		owned_stocks = defaultdict(list,temp)
		MONEY = owned_stocks['MONEY']
except:
	MONEY = initial_investment
	owned_stocks = defaultdict(list)
	owned_stocks['MONEY'] = MONEY
	saveStocks()

#Use pandas to get stock prices
yf.pdr_override()

#Initial Settings
################################
CSV_NASDAQ = "https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download"
CSV_NYSE = "https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download"
CSV_CANADA = "https://old.nasdaq.com/screening/companies-by-region.aspx?region=North+America&country=Canada&render=download"

#Change to current exchange, delete owned_stocks.json if you choose to change exchanges
current_CSV = CSV_CANADA

PERIOD = '5d' #1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
Amount_To_Fetch = 100 #top x stocks
profit_percentage = 3 #Sell at 3% profit
################################

total_invested = 0
total_profit = 0

#Custom writer to print and save output
class Writer(object):
	def __init__(self, *files):
		self.files = files
	def write(self, obj):
		for f in self.files:
			f.write(obj)
			f.flush()
	def flush(self) :
		for f in self.files:
			f.flush()
			
class NullWriter(object):
	def write(self, obj):
		pass
nullwrite = NullWriter()

#Setup logging
file = open("logs.txt", "a")
writer = Writer(sys.stdout, file)
sys.stdout = writer

#Get top x stocks from exchange sorted by market cap
def get_top_stocks():
	try:
		headers = {'User-Agent': 'Mozilla/5.0'}
		req = requests.get(current_CSV, headers=headers)
		data = StringIO(req.text)
		df = pd.read_csv(data)
		df.apply(lambda x: x.fillna(0)) 
		df['MarketCap'] = str(df['MarketCap'])
		df['MarketCap'] = df['MarketCap'].str[1:]
		if current_CSV in [CSV_NASDAQ, CSV_NYSE]:
			df['MarketCap'] = df['MarketCap'].replace({'K': '*1e3', 'M': '*1e6', 'B':'*1e9','T':'*1e12'},regex=True).fillna(0).map(pd.eval).astype(float)
		df = df.sort_values(by=["MarketCap"],ascending=False)
		return(df)
	except Exception as e:
		df = []

#Download stock prices for the top x chosen stocks
def download_stock_prices(tickers):
	sys.stdout = nullwrite
	try:
		data = pdr.get_data_yahoo(
				tickers = str(tickers),
				period =  PERIOD,
				group_by = 'ticker',
				threads = True,
				progress=False
				)
		data_compacted = data.loc[:,(slice(None),('Close'))]
		data_compacted = data_compacted.apply(lambda x: pd.Series(x.dropna().values)).fillna('')
		sys.stdout = writer
		return(data_compacted)
	except Exception as e:
		sys.stdout = writer
		data = []
		data_compacted = []
		pass

#Print summary of stock information
def print_information(total_profit, total_invested, MONEY):
	if round(total_profit,4) > 0:
		print(Fore.GREEN + "TOTAL Profit: {:.4f}".format(round(total_profit,4)) + Style.RESET_ALL)
	else:
		print(Fore.RED + "TOTAL Profit: {:.4f}".format(round(total_profit,4)) + Style.RESET_ALL)
	print("TOTAL Invested: {:.4f}".format(round(total_invested,4)))
	print("TOTAL Money: {:.4f}".format(round(MONEY,4)))
	overall_profit = MONEY + total_invested + total_profit - initial_investment
	if round(overall_profit,4) > 0:
		print(Fore.GREEN + "OVERALL Profit: {:.4f}".format(round(overall_profit,4)) + Style.RESET_ALL)
	else:
		print(Fore.RED + "OVERALL Profit: {:.4f}".format(round(overall_profit,4)) + Style.RESET_ALL)
		
#Buy a stock and subtract from total money
def buy_stock(symbol, current_Value, SELL, ROI):
	global MONEY
	if MONEY >= (0.25*MONEY)/round(current_Value,4):
		if math.floor((0.25*MONEY)/round(current_Value,4)) > 49:
			print("BUY: {} Price Buy: {:.4f} Price Sell: {:.4f} ROI: {:.4f}%".format(symbol, round(current_Value,4),SELL, ROI), end = '')
			owned_stocks[symbol] = {}
			owned_stocks[symbol]['BUY PRICE'] =round(current_Value,4)
			owned_stocks[symbol]['SELL PRICE'] = round(SELL, 4)
			owned_stocks[symbol]['QUANTITY'] = math.floor((0.25*MONEY)/round(current_Value,4))
			
			i = owned_stocks[symbol]['QUANTITY']
			print(Fore.RED + " Spent: {:.4f} ({} Shares)".format(round(current_Value,4)*i,i)+ Style.RESET_ALL, end ='')
			print(Fore.GREEN + " Remaining: {:.4f}".format(MONEY - i*round(current_Value,4))+ Style.RESET_ALL)
			MONEY = MONEY - i*round(current_Value,4)

#Sell a stock and show profit
def sell_stock(symbol, current_Value):
	global MONEY
	profit = (round(current_Value,4) -  owned_stocks[symbol]['BUY PRICE'])*owned_stocks[symbol]['QUANTITY']
	MONEY = MONEY + (round(current_Value,4)*owned_stocks[symbol]['QUANTITY'])
	print("Sell {} Price {:.4f} Profit: {:.4f}".format(symbol, round(current_Value,4),round(profit,4)))
	del owned_stocks[symbol]

#Print individual stock summary
def print_stock_info(symbol, current_Value):
	global total_profit, total_invested
	profit = 0
	invested = 0
	profit = (round(current_Value,4) -  owned_stocks[symbol]['BUY PRICE'])*owned_stocks[symbol]['QUANTITY']
	invested = owned_stocks[symbol]['BUY PRICE']*owned_stocks[symbol]['QUANTITY']
	total_invested = total_invested + invested
	total_profit = total_profit + profit
	if round(profit,4) > 0:
		print(Fore.GREEN + "{} Profit: {:.4f} (Current @ {:.4f}, Sell @ {:.4f}, Bought @ {:.4f}, Quantity: {})".format(symbol, round(profit,4),round(current_Value,4), owned_stocks[symbol]['SELL PRICE'],owned_stocks[symbol]['BUY PRICE'],owned_stocks[symbol]['QUANTITY'])+ Style.RESET_ALL)
	else:
		print(Fore.RED + "{} Profit: {:.4f} (Current @ {:.4f}, Sell @ {:.4f}, Bought @ {:.4f}, Quantity: {})".format(symbol, round(profit,4),round(current_Value,4),owned_stocks[symbol]['SELL PRICE'],owned_stocks[symbol]['BUY PRICE'],owned_stocks[symbol]['QUANTITY'])+ Style.RESET_ALL)

#Find potential Return on Investment
def getROI(current_Value, SELL):
	return ((float(SELL) - float(current_Value))/float(current_Value))*100.00

#Refresh all information, provide new output and buy/sell stocks accordingly
def refresh_information():
	global total_invested, total_profit
	start_time = time.time()
	dateTimeObj = datetime.datetime.now(pytz.timezone('US/Eastern'))
	timestampStr = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S)")
	print('Current Timestamp : ', timestampStr)

	df = get_top_stocks()
	ticker_symbols = " ".join(df[['Symbol']].head(Amount_To_Fetch).values.flatten())
	data_compacted = download_stock_prices(ticker_symbols)
	stock_symbols = data_compacted.columns.levels[0]
	total_invested = 0
	total_profit = 0

	print("================")
	print("OWNED STOCKS")
	print("================")
	#Loop through all stock symbols and determine whether to buy, sell, or do nothing
	global owned_stocks_list
	owned_stocks_list = list(owned_stocks.keys())
	owned_stocks_list.remove("MONEY")
	for symbol in stock_symbols:
		try:
			current_Value =  data_compacted[symbol]['Close'][int(PERIOD[:-1])-1]
			if symbol in owned_stocks:
				if symbol in sell_list:
					sell_stock(symbol, current_Value)
					sell_list.remove(symbol)
				elif symbol == 'MONEY':
					continue
				else:
					print_stock_info(symbol, current_Value)
					owned_stocks_list.remove(symbol)
					if round(current_Value,4) >= owned_stocks[symbol]['SELL PRICE']:
						sell_stock(symbol, current_Value)
					elif round(current_Value,4) <= owned_stocks[symbol]['BUY PRICE'] * 0.90:
						sell_stock(symbol, current_Value)
			elif symbol not in owned_stocks:
				rollingMean =  data_compacted[symbol]['Close'].rolling(int(PERIOD[:-1])).mean().values
			
				data_compacted.loc[:,(symbol,PERIOD)] = rollingMean
				data_compacted.loc[:,(symbol,'BUY')] = rollingMean * 0.95
				data_compacted.loc[:,(symbol,'SELL')] = rollingMean * 1.03
				
				BUY = data_compacted.loc[:,(symbol,'BUY')][data_compacted.loc[:,(symbol,'BUY')].first_valid_index()]
				SELL = data_compacted.loc[:,(symbol,'SELL')][data_compacted.loc[:,(symbol,'SELL')].first_valid_index()]
				ROI = getROI(current_Value, SELL)
				if round(current_Value,4) < BUY:
					buy_stock(symbol, current_Value, SELL, ROI)
			else: 
				pass
		except Exception as e:
			ROI = 0
			BUY=0
			SELL=0
			current_Value = 0
	print()
	print("================")
	if len(owned_stocks_list) == 0:
		print(Fore.GREEN + "SUMMARY (Accurate) " + Style.RESET_ALL)
	else:
		print(FORE.RED + "SUMMARY (inaccurate, missing: " + Style.RESET_ALL,end ='')
		print(", ".join(owned_stocks_list))
	print("================")
	print_information(total_profit, total_invested, MONEY)
	print("================")
	
	owned_stocks['MONEY'] = MONEY
	saveStocks()
	print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == "__main__":
	while True:				
		#Only enable script while stock market is open (9:30 Eastern to 4PM Eastern)
		now = datetime.datetime.now(pytz.timezone('US/Eastern'))
		today930am = now.replace(hour=9, minute = 30)
		today4pm = now.replace(hour=16, minute = 0)

		script_enabled = False
		if now.weekday() not in [5,6]:
			if now >= today930am and now < today4pm:
				if now.hour == 9 and now.minute == 30:
					print('%s:%s:%s' % (now.hour, now.minute, now.second),end='')
					print(' Market is open')
				script_enabled = True
			elif now >= today4pm:
				if now.hour == 16 and now.minute in [0, 1, 2] and now.second == 0:
					print('%s:%s:%s' % (now.hour, now.minute,now.second),end='')
					print(' Market is now closed')
				script_enabled = False
				
			if script_enabled:
				try:
					refresh_information()
					timeout_start = time.time()
					while time.time() <= timeout_start + 120:
						try:
							if keyboard.is_pressed('ctrl+shift'):
								sell_list = input("Enter comma separated string of stocks to sell: ").replace(' ', '').split(',')
								break
							else: 
								continue
						except KeyboardInterrupt:
							print("Program has terminated")
							sys.exit()
				except Exception as e:
					print(e)
					time.sleep(120)
			else:
				time.sleep(1)