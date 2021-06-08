import time
import pyupbit
import datetime
import requests
import numpy as np

# access = ""
# secret = ""
# myToken = ""

def trade_test(data, start, end, dist, rm, h, l):   
    """모의 트레이딩 for 파라미터 최적화"""
    money = 100
    coin = 0
    df = data.close
    rm = df - df.rolling(rm).mean() # rm = 5, 20
 
    for t in range(start, end):
        check = rm[t-dist:t]      
        high = check.quantile(q=h, interpolation='nearest')
        low  = check.quantile(q=l, interpolation='nearest')

        if (money > 0) and (check[t-1] <= low):
            buy_price = df[t-1]  
            coin = money*0.9995
            money = 0
        elif (coin > 0) and (check[t-1] >= high):    
            cell_price  = df[t-1] 
            money = coin*0.9995*cell_price/buy_price
            coin = 0       
    return money+coin*0.9995

def parameter_adjust(ticker, leng):   
    """최적 파라미터 찾기"""
    data = pyupbit.get_ohlcv(ticker, interval="minute5", count=leng+40 )
    data.index = range(0, leng+40)
    X = np.linspace(1, 20, 20).astype(int)
    Y = np.linspace(1, 20, 20).astype(int)
    Z = np.zeros((20, 20)) 
    for x in X:
        for y in Y:
            Z[x-1][y-1] = trade_test(data, 40, leng+40, x, y, 1, 0)
    best_x = np.argmax(Z)// 20 + 1
    best_y = np.argmax(Z) % 20 + 1 
    return best_x, best_y, round(Z.max(),1)

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
    high = dist[-ref-1:-1].quantile(q=h, interpolation='nearest') +ma[ref + rm-2]
    low  = dist[-ref-1:-1].quantile(q=l, interpolation='nearest') +ma[ref + rm-2]
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
trade_count = 0
# 파라미터 설정
ref, rm, expected = parameter_adjust("KRW-XRP", 12)
post_message(myToken,"#trading", "para:(ref)"+str(ref)+" (rm)"+str(rm)+" (ev)"+str(expected))

h_lim = 1
l_lim = 0

while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-XRP")
        end_time = start_time + datetime.timedelta(minutes=5)

        current_price = get_current_price("KRW-XRP")             # 현재가 가져오기
        high, low = get_quantile("KRW-XRP", ref, rm, h_lim, l_lim)        # 거래 기준값 계산하기 

        if start_time < now < end_time - datetime.timedelta(seconds=3):

            if current_price < low:
                krw = get_balance("KRW")
                if krw > 5000 :
                    buy_order = upbit.buy_limit_order("KRW-XRP", current_price, krw*0.9995/current_price)
                    post_message(myToken,"#trading", "XRP buy order : " +str(buy_order))
                    trade_count += 1

            elif current_price > high:
                coin = get_balance("XRP")

                if coin*current_price > 5000:
                    sell_order = upbit.sell_limit_order("KRW-XRP", current_price, coin)
                    post_message(myToken,"#trading", "XRP sell : " +str(sell_order))
                    trade_count += 1
            
            time.sleep(1)
    
        else:
            counting = counting + 1             
            post_message(myToken,"#trading", str(counting)+" th 5 minutes and "+str(trade_count)+" times worked")
            post_message(myToken,"#trading", "(h)" +str(round(high,2))+"(p)"+str(current_price)+"(l) " +str(round(low,2)))

            if get_locked("KRW") > 0 and current_price > low:
                ret = upbit.cancel_order(buy_order["uuid"])
                post_message(myToken,"#trading", "XRP buy cenceled: "+str(ret))
                trade_count -= 1

            if get_locked("XRP") > 0 and current_price < high:
                ret = upbit.cancel_order(sell_order["uuid"])
                post_message(myToken,"#trading", "XRP cell cenceled: "+str(ret))
                trade_count -= 1

            if counting % 6 == 0:
                ref, rm = parameter_adjust("KRW-XRP", 12)
                post_message(myToken,"#trading", "para:(ref)"+str(ref)+" (rm)"+str(rm)+" (ev)"+str(expected))
                
            time.sleep(5)

    except Exception as e:
        print(e)
        post_message(myToken,"#trading", e)
        time.sleep(1)