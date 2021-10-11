import time
import pyupbit
import datetime
import requests
import pandas as pd
import key

access = key.access
secret = key.secret
myToken = key.myToken

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token}, data={"channel": channel,"text": text})

def get_start_time(ticker, interv):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval= interv, count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None: return float(b['balance'])
            else: return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]

def get_minmax_start(param):
    # param = [ticker, buff, lengthh, lengthl, k1, k2]
    ticker, buff, lengthh, lengthl, k1, k2 = param[0],param[1],param[2],param[3],param[4],param[5]

    data = pyupbit.get_ohlcv(ticker, interval="minute5", count=buff*2)
    data.drop_duplicates(subset=None, keep='first', inplace=True, ignore_index=False)

    data.loc[:,"max_count"] = 0
    data.loc[:,"min_count"] = 0

    for i in range(buff, len( data.index)):
        local_max = max(data.high[i-lengthh:i+1])
        local_min = min(data.low[i-lengthl:i+1])

        t1, t2 = data.index[i], data.index[i-1]

        data.loc[t1,"lo_max"] = local_max 
        data.loc[t1,"lo_min"] = local_min 
        data.loc[t1,"target_b"] = local_min + (local_max - local_min)*k1
        data.loc[t1,"target_s"] = local_max - (local_max - local_min)*k2

        if data.loc[t1,"lo_max"] > data.loc[t2,"lo_max"]: data.loc[t1,"max_count"] = 0
        else: data.loc[t1,"max_count"] = data.loc[t2,"max_count"] + 1
        if data.loc[t1,"lo_min"] < data.loc[t2,"lo_min"]: data.loc[t1,"min_count"] = 0
        else: data.loc[t1,"min_count"] = data.loc[t2,"min_count"] + 1
    
    data.loc[t1, "wallet"] = get_balance(coin[0][4:]) 
    data.loc[t1, "bugget"] = get_balance(coin[0][:3]) 

    if data.loc[t1,"wallet"]*data.loc[t1,"close"] > 5000:
        past_data = pd.read_excel("mm1010_monitoring_data.xlsx", index_col= "Unnamed: 0")
        data.loc[t2:, "bought"] = past_data["bought"][-1] 
    else: data.loc[t2:, "bought"] = None

    data.loc[t2:,"return" ] = None
    data.loc[t2:,"acc_rtn"] = 1

    return data[-buff:]

def get_minmax_bs(param, df2):
    # 과거데이터에 현재 5분을 추가하여 minmax, target_line 갱신
    ticker,  lengthh, lengthl, k1, k2 = param[0], param[2],param[3],param[4],param[5]

    data2 = pyupbit.get_ohlcv(ticker, interval="minute5", count=1)

    if (df2.index[-1] == data2.index[0]):   
        df2.iloc[-1, :6] = data2.iloc[:, :6].copy()
    else:   
        df2 = df2.append(data2)
        df2.iloc[-1,6:] = df2.iloc[-2:,6:].copy()

    local_max = max(df2.high[-lengthh-1:])
    local_min = min(df2.low[-lengthl-1:])

    t = df2.index[-1]
    df2.loc[t,"lo_max"] = local_max 
    df2.loc[t,"lo_min"] = local_min 

    df2.loc[t,"target_b"] = local_min + (local_max - local_min)*k1
    df2.loc[t,"target_s"] = local_max - (local_max - local_min)*k2

    if df2["lo_max"][-1] > df2["lo_max"][-2]: df2.loc[t,"max_count"] = 0
    else: df2.loc[t,"max_count"] = df2["max_count"][-2] + 1
    if df2["lo_min"][-1] < df2["lo_min"][-2]: df2.loc[t,"min_count"] = 0
    else: df2.loc[t,"min_count"] = df2["min_count"][-2] + 1

    df2.loc[t, "wallet"] = get_balance(coin[0][4:]) 
    df2.loc[t, "bugget"] = get_balance(coin[0][:3]) 

    return df2

def money_work(coin, data):
    max_c, min_c   = data.max_count[-1], data.min_count[-1] 
    target_b, target_s = data.target_b[-1], data.target_s[-1] 
    current_price = get_current_price(coin[0])
    t = data.index[-1]

    print(1, data[-1:] )            

    if (current_price > target_b) and (max_c > min_c):
        if (data.loc[t, "wallet"]*current_price < 5000) and (data.loc[t, "bugget"] > 5000):
            data.loc[t, 'trace_b'] =  current_price
            data.loc[t, "bought"] = current_price 
            upbit.buy_market_order(coin[0], data.loc[t, "bugget"]*0.9995)
            post_message(myToken,"#trading", str(coin[0][4:])+"mm_buy:"+str(current_price))
        
    elif (current_price < target_s) and (max_c < min_c):
        if ( data.loc[t, "bugget"] < 5000) and (data.loc[t, "wallet"]*current_price > 5000):
            data.loc[t, 'trace_s'] = current_price        
            data.loc[t, 'return'] = round(current_price/data.loc[t,"bought"]*0.9995*0.9995, 3)
            data.loc[t, 'acc_rtn']= round(data.loc[t,'acc_rtn']*data.loc[t, 'return'], 3)
            data.loc[t, "bought"] = None
            upbit.sell_market_order(coin[0], data.loc[t, "wallet"])
            post_message(myToken,"#trading", str(coin[0][4:])+"mm_sell:"+str(current_price)+"/log:"+str(data.iloc[-1,6:]))

    print(2, data[-1:])
    return data


# # 로그인
upbit = pyupbit.Upbit(access, secret)
standard_time = get_start_time("KRW-BTC", "minute60")
post_message(myToken,"#trading", "MM autotrade start: "+str(standard_time))

# 기본 세팅
coin = ["KRW-ETC", 100, 75, 70, 0.01, 0.09]     # minmax 파라미터 설정ticker, buff, lengthh, lengthl, k1, k2
data= get_minmax_start(coin)

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-BTC", "minute5")
        mid_time = start_time + datetime.timedelta(minutes=5)

        if mid_time - datetime.timedelta(seconds=5) < now < mid_time:
            data = get_minmax_bs(coin, data)
            data = money_work(coin, data)
            data.to_excel("mm1010_monitoring_data.xlsx")

            time.sleep(5)

        elif standard_time + datetime.timedelta(minutes =15) == start_time:
            standard_time = standard_time + datetime.timedelta(minutes =15)
            post_message(myToken,"#trading", str(start_time)+"/log:"+str(data.iloc[-1,6:]))

        time.sleep(1)          

    except Exception as e:
        post_message(myToken,"#trading", e)
        time.sleep(1)
