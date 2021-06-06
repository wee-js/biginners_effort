import time
import pyupbit
import datetime
import requests

access = ""
secret = ""
myToken = ""

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="minute5", count=1)
    start_time = df.index[0]
    return start_time

def get_quantile(ticker, ref, rm, h, l):
    """이동 평균선(rm일) 대비 시세 분포(ref 기간) 조회"""   
    df = pyupbit.get_ohlcv(ticker, interval="minute5", count = ref + rm)
    ma = df['close'].rolling(rm).mean()    
    dist = df['close'] - ma
    high = dist[-ref:].quantile(q=h, interpolation='nearest') +ma[ref + rm-1]
    low  = dist[-ref:].quantile(q=l, interpolation='nearest') +ma[ref + rm-1]
    return high, low

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
    """잔고 조회"""
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

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
# 시작 메세지 슬랙 전송
post_message(myToken,"#trading", "autotrade start")

counting = 0

# 파라미터 설정
ref = 14
rm   = 2
h_lim = 0.95
l_lim = 0.05

while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-XRP")
        end_time = start_time + datetime.timedelta(minutes=5)

        current_price = get_current_price("KRW-XRP")             # 현재가 가져오기
        high, low = get_quantile("KRW-XRP", ref, rm, 0.95, 0.05)        # 거래 기준값 계산하기 

        if start_time < now < end_time - datetime.timedelta(seconds=5):

            if current_price < low:
                krw = get_balance("KRW")
                if krw > 5000 :
                    buy_order = upbit.buy_limit_order("KRW-XRP", current_price, krw*0.9995/current_price)
                    post_message(myToken,"#trading", "XRP buy order : " +str(buy_order))
                    counting = 0            #noti_test
                else:
                    if counting%100 == 0:
                        post_message(myToken,"#trading", "XRP no buy : "+str(current_price)+" < "+str(low)+" / "+str(counting)+"th")
                    counting = counting + 1 

            elif current_price > high:
                coin = get_balance("XRP")

                if coin*current_price > 5000:
                    sell_order = upbit.sell_limit_order("KRW-XRP", current_price, coin)
                    post_message(myToken,"#trading", "XRP sell : " +str(sell_order))
                    counting = 0            #noti_test
                else:
                    if counting%100 == 0:
                        post_message(myToken,"#trading", "XRP no sell : "+str(current_price)+" > "+str(high)+" / "+str(counting)+"th")
                    counting = counting + 1 

            else:
                if counting%100 == 0:
                    post_message(myToken,"#trading", "tried " +str(counting)+"th 5min")
                counting = counting + 1 
            
            time.sleep(1)
    
        else:
            if get_locked("KRW") > 0 and current_price > low:
                ret = upbit.cancel_order(buy_order["uuid"])
                post_message(myToken,"#trading", "XRP buy cenceled: "+str(ret))
            if get_locked("XRP") > 0 and current_price < high:
                ret = upbit.cancel_order(sell_order["uuid"])
                post_message(myToken,"#trading", "XRP cell cenceled: "+str(ret))
            else:
                post_message(myToken,"#trading", "5 minutes passed and its working")
                post_message(myToken,"#trading", "current price : " +str(current_price))
                post_message(myToken,"#trading", "high : " +str(high)+" / low  : " +str(low))

            time.sleep(7)

    except Exception as e:
        print(e)
        post_message(myToken,"#trading", e)
        time.sleep(1)