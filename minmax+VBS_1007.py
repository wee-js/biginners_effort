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
        headers={"Authorization": "Bearer "+token}, data={"channel": channel,"text": text})

def get_target_price(ticker, k, k2):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    buy_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    cell_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k2
    return buy_price, cell_price

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

def get_locked(ticker):
    """주문 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['locked'] is not None: return float(b['locked'])
            else: return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]


def set_log(log):
    for i in log:
        wallet = get_balance(i[4:])
        current_price = get_current_price(i)  
        if (i[:3] == "KRW") and (wallet > 5100/current_price): log[i][1] = current_price/log[i][5]
        elif (i[:3] == "BTC") and (wallet > 0.0005/current_price): log[i][1] = current_price/log[i][5]
    return log

def get_minmax_start(param):
    # param = [ticker, buff, lengthh, lengthl, k1, k2]
    ticker, buff, lengthh, lengthl, k1, k2 = param[0],param[1],param[2],param[3],param[4],param[5]

    data = pyupbit.get_ohlcv(ticker, interval="minute5", count=buff*2)
    data.drop_duplicates(subset=None, keep='first', inplace=True, ignore_index=False)

    data["lo_max"] = max(data.close)
    data["lo_min"] = min(data.close)
    data["target_b"]= max(data.close)
    data["target_s"]= min(data.close)
    data["max_count"] = 0
    data["min_count"] = 0

    a_count = 0
    i_count = 0

    for i in range(buff, len( data.index)):

        local_max = max(data.high[i-lengthh:i+1])
        local_min = min(data.low[i-lengthl:i+1])

        data["lo_max"][i] = local_max 
        data["lo_min"][i] = local_min 

        data["target_b"][i] = local_min + (local_max - local_min)*k1
        data["target_s"][i] = local_max - (local_max - local_min)*k2

        if data["lo_max"][i] > data["lo_max"][i-1]: a_count = 0
        else: a_count = a_count + 1
        if data["lo_min"][i] < data["lo_min"][i-1]: i_count = 0
        else: i_count = i_count + 1

        data["max_count"][i] = a_count
        data["min_count"][i] = i_count

    return data.iloc[-buff-1:-1,:6], data.lo_max[-2], data.lo_min[-2], data.max_count[-2], data.min_count[-2]

def get_minmax_bs(param, df, past_max, past_min, max_count, min_count):
    # 과거데이터에 현재 5분을 추가하여 minmax, target_line 갱신
    ticker, buff, lengthh, lengthl, k1, k2 = param[0],param[1],param[2],param[3],param[4],param[5]

    data = pyupbit.get_ohlcv(ticker, interval="minute5", count=1)
    
    if df.index[-1] == data.index[0]:
        local_max = past_max
        local_min = past_min

    else:
        data = df[1:].append(data)
        local_max = max(data.high[-lengthh:])
        local_min = min( data.low[-lengthl:])

        if local_max > past_max: max_count = 0
        else: max_count = max_count + 1
        if local_min < past_min: min_count = 0
        else: min_count = min_count + 1

    target_b = local_min + (local_max - local_min)*k1
    target_s = local_max - (local_max - local_min)*k2

    return data, local_max, local_min, max_count, min_count, target_b, target_s

def recording_log(log, current_price):
    ror = round( current_price*log[5]*log[5] / log[1], 3 )
    log[0] += 1                   # 거래횟수 추가
    log[2] =  current_price       # 매도가 기록
    log[3] =  ror                 # 수익률 기록
    log[4] = round(log[4]*ror,3)  # 누적수익률 기록
    return log

# 파라미터 설정 ( 1000일 기준 )
# 100일 기준 coin = [["KRW-BTC", 0.71, -0.3],["KRW-ETH", 0.33, -0.49],["KRW-XRP", 0.5, -0.78],["KRW-ETC", 0.52, -0.31],["KRW-EOS", 0.59, -0.31]]
coin = [["KRW-ETH", 0.3, -0.65],["KRW-XRP", 0.5, -0.5],["KRW-ETC", 0.5, -0.75],["KRW-ADA", 0.3, -0.85],["KRW-BCH", 0.48, -0.63]]
celo = ["BTC-CELO", 100, 85, 75, 0.01, 0.01]  # minmax 파라미터 설정ticker, buff, lengthh, lengthl, k1, k2

# 로그인
upbit = pyupbit.Upbit(access, secret)
start_time = get_start_time("KRW-BTC", "minute5")
post_message(myToken,"#trading", "autotrade start: "+str(start_time))

start_time = get_start_time("KRW-BTC", "day") - datetime.timedelta(minutes=150)
end_time = start_time + datetime.timedelta(days=1)
print("autotrade start")

inv_size, counting = 2000000, 0
log = {"KRW-ETH" :[0,0,0,1,1,0.9995], "KRW-XRP" :[0,0,0,1,1,0.9995], "KRW-ETC" :[0,0,0,1,1,0.9995],
       "KRW-ADA" :[0,0,0,1,1,0.9995], "KRW-BCH" :[0,0,0,1,1,0.9995], "BTC-CELO":[0,0,0,1,1,0.9975]}
       # 거래횟수, 매수가, 매도가, 수익률, 누적수익률
log = set_log(log)
data, lo_max, lo_min, max_c, min_c = get_minmax_start(celo)

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        mid_time = get_start_time("KRW-BTC", "minute5") + datetime.timedelta(minutes=5)

        if mid_time - datetime.timedelta(seconds=10) < now < mid_time:
            data, lo_max, lo_min, max_c, min_c, target_b, target_s = get_minmax_bs(celo, data, lo_max, lo_min, max_c, min_c)

            current_price = get_current_price(celo[0])
            wallet = get_balance(celo[0][4:])
            bugget = get_balance(celo[0][:3])

            if (current_price < target_s) and (max_c < min_c) and (wallet > 0.0005/current_price) :
                upbit.sell_market_order(celo[0], wallet*0.9975)
                log[celo[0]] = recording_log(log[celo[0]], current_price) # 매도가, 수익률 기록
                post_message(myToken,"#trading", str(celo[0][4:])+" sell:"+str(current_price)+"/ ror:"+str(log[celo[0]][3]))

            if (current_price > target_b) and (max_c > min_c) and (bugget > 0.0005):
                upbit.buy_market_order(celo[0], bugget*0.9975)
                log[celo[0]][1] =  current_price   # 매수가 기록
                post_message(myToken,"#trading", str(celo[0][4:])+" buy:"+str(current_price)+"/ "+str(log[celo[0]][0]+1)+"st")
 
            time.sleep(1)

        elif start_time < now < end_time:
            
            for i in coin:
                buy_line, sell_line = get_target_price(i[0], i[1], i[2])
                current_price = get_current_price(i[0])
                wallet = get_balance(i[0][4:])
                
                if (wallet > 5000/current_price) and (sell_line > current_price):  # 코인 잔고가 있으면 매도 검토
                    upbit.sell_market_order(i[0], wallet*0.9995)
                    log[i[0]] = recording_log(log[i[0]], current_price)
                    post_message(myToken,"#trading", str(i[0][4:])+" sell:"+str(current_price)+"/ ror:"+str(log[i[0]][3]))
                
                elif buy_line < current_price:  # 매수 검토 후 잔고 확인
                    krw = get_balance("KRW")

                    if krw > inv_size:
                        upbit.buy_market_order(i[0], inv_size*0.9995)
                        log[i[0]][1] =  current_price   # 매수가 기록
                        post_message(myToken,"#trading", str(i[0][4:])+" buy:"+str(current_price)+"/ "+str(log[i[0]][0]+1)+"st")
        
                time.sleep(1)

        else:
            start_time = start_time + datetime.timedelta(days=1)
            end_time   = start_time + datetime.timedelta(days=1)
            counting = counting + 1
            post_message(myToken,"#trading", "time_reflash:"+str(start_time)+"/log:"+str(log))
            time.sleep(20)          

    except Exception as e:
        post_message(myToken,"#trading", e)
        time.sleep(1)
