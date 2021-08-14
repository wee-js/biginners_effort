import time
import pyupbit
import datetime
import requests
import numpy as np
import key

access = key.access
secret = key.secret
myToken = key.myToken

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

def get_target_price(ticker, k, k2):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    buy_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    cell_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k2

    return buy_price, cell_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="minute60", count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_locked(ticker):
    """주문 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['locked'] is not None:
                return float(b['locked'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]

# 파라미터 설정
# 100일 기준 coin = [["KRW-BTC", 0.71, -0.3],["KRW-ETH", 0.33, -0.49],["KRW-XRP", 0.5, -0.78],["KRW-ETC", 0.52, -0.31],["KRW-EOS", 0.59, -0.31]]
# 1000일 기준
coin = [["KRW-BTC", 0.36, -0.63],["KRW-ETH", 0.3, -0.65],["KRW-XRP", 0.5, -0.5],["KRW-ETC", 0.5, -0.75],["KRW-ADA", 0.3, -0.85]]


# 로그인
upbit = pyupbit.Upbit(access, secret)
start_time = get_start_time("KRW-BTC")
post_message(myToken,"#trading", "autotrade start: "+str(start_time))
print("autotrade start")

inv_size = 1000000
counting = 0     
trade_count = 0
log = []
hpr = 1

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-BTC")
        end_time = start_time + datetime.timedelta(minutes=60)

        if start_time < now < end_time - datetime.timedelta(seconds=20):
            
            for i in coin:
                buy_line, cell_line = get_target_price(i[0], i[1], i[2])
                current_price = get_current_price(i[0])
                wallet = get_balance(i[0][-3:])

                # 코인 잔고가 있으면 매도 검토
                if wallet > (5000/current_price):
                    if cell_line > current_price:
                        upbit.sell_market_order(i[0], wallet*0.9995)

                        trade_count = trade_count+1
                        ror = current_price*wallet*0.9995/inv_size
                        log.append([i[0][-3:], "sell", ror])
                        hpr = hpr * ror
                        post_message(myToken,"#trading", str(i[0][-3:])+" cell:"+str(current_price)+"/ ror:"+str(ror))

                # 매수 검토 후 잔고 확인
                elif buy_line < current_price:
                    print("it is chance to buy "+str(i[0][-3:]))

                    krw = get_balance("KRW")
                    if krw > inv_size:
                        upbit.buy_market_order(i[0], inv_size*0.9995)

                        trade_count = trade_count+1
                        log.append([i[0][-3:], "buy", current_price])
                        post_message(myToken,"#trading", str(i[0][-3:])+" buy:"+str(current_price)+"/ krw:"+str(krw))
        
                time.sleep(1)

        else:
            time.sleep(20)          
            counting = counting + 1
            post_message(myToken,"#trading", str(counting)+" th hour and "+str(trade_count)+" times worked")

            if counting % 12 == 0:
                post_message(myToken,"#trading", "hpr: "+str(hpr)+"     /log:"+str(log))

    except Exception as e:
        post_message(myToken,"#trading", e)
        time.sleep(1)
