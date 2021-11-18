import csv
from datetime import datetime, timedelta
import pickle

from trade_job.submodules import binance_class as bc, mongo_class as mc, line_notify, \
    properties as prop, const


class TradeJobData:
    def __init__(self):
        self.notified_list: dict = {}
        self.rate_notified_list: dict = {}
        self.usdt_ticker_list: list = []


FILE_NAME = 'TradeJob'
binance_set = bc.BinanceAPI()
mongo_set = mc.MongoAPI()
job_data: TradeJobData = TradeJobData()
symbols_info = []
buy_histories = []
buy_count = 0


def load_data():
    try:
        with open(f'{prop.DATA_DIR}/job_data.pickle', 'rb') as f:
            global job_data
            job_data = pickle.load(f)
    except FileNotFoundError:
        job_data = TradeJobData()


def set_data():
    global symbols_info, buy_histories, buy_count
    # 取引所情報を取得、特定のSymbolの取引所情報を取得
    symbols_info = [i for i in binance_set.get_symbols_info()
                    if i['quoteAsset'] == 'BNB' and i['status'] == 'TRADING']
    # BNBを除く保持トークンを取得
    buy_histories = list(mongo_set.find('trade_histories',
                                        __filter__={"$and": [{'symbol': {'$ne': 'BNB'}}, {'sell_date': None}]}))
    buy_count = len(buy_histories)
    print(f'{datetime.now()}    buy_count:{buy_count}')


def dump_data():
    with open(f'{prop.DATA_DIR}/job_data.pickle', 'wb') as f:
        pickle.dump(job_data, f)


def is_notified(pair: str, notified_list: dict, interval: int):
    if pair not in notified_list:
        return False
    return datetime.now() - notified_list[pair] < timedelta(minutes=interval)


def add_trade_message(notify_message, row, ticker, trade_name):
    return f'{notify_message}\n' \
           f'■{row["銘柄"]}\n' \
           f'  {trade_name}目標値(${row["目標数値"]})\n' \
           f'  {const.price_info_lint[row["取得項目"]]}(${round(float(ticker[row["取得項目"]]), 4)})'


def add_rate_message(notify_rate_message, symbol, change_rate, price):
    return f'{notify_rate_message}\n' \
           f'{symbol.replace("USDT", ""): <5}' \
           f'：30分変化率({round(change_rate * float(100), 2): >6}%)' \
           f'：${round(float(price), 3)}'


def check_goal():
    notify_message = ''
    with open(f'{prop.DATA_DIR}/{FILE_NAME}.csv', 'r') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            if not is_notified(row['銘柄'], job_data.notified_list, prop.NOTIFIED_INTERVAL):
                ticker = binance_set.get_ticker(row['銘柄'])
                if row['取得項目'] == 'askPrice' and float(row['目標数値']) > float(ticker[row['取得項目']]):
                    notify_message = add_trade_message(notify_message, row, ticker, '買い')
                    job_data.notified_list[row["銘柄"]] = datetime.now()
                elif row['取得項目'] == 'bidPrice' and float(row['目標数値']) < float(ticker[row['取得項目']]):
                    notify_message = add_trade_message(notify_message, row, ticker, '売り')
                    job_data.notified_list[row["銘柄"]] = datetime.now()
    return notify_message


# 30分変化率のリストを作成
def check_rate_30m():
    notify_rate_message = ''
    all_ticker = binance_set.get_symbol_ticker(None)
    bnb_ticker = {i['symbol']: i['price'] for i in all_ticker
                  if i['symbol'].endswith('BNB')}
    job_data.usdt_ticker_list.append(bnb_ticker)
    if len(job_data.usdt_ticker_list) == 7:
        # 6回前に取得したデータを取り出す
        data_ticker = job_data.usdt_ticker_list.pop(0)
        for symbol, price in bnb_ticker.items():
            if not is_notified(symbol, job_data.rate_notified_list, prop.RATE_INTERVAL):
                if symbol in data_ticker:
                    price_30m_ago = data_ticker[symbol]
                else:
                    continue
                change_rate = (float(price) / float(price_30m_ago)) - float(1)
                if change_rate <= -prop.REFERENCE_RATE_30m / 100 or prop.REFERENCE_RATE_30m / 100 <= change_rate:
                    notify_rate_message = add_rate_message(notify_rate_message, symbol, change_rate, price)
                    job_data.rate_notified_list[symbol] = datetime.now()
    return notify_rate_message, bnb_ticker


# ローソク足(5分)を取得
def check_rate_5m(bnb_ticker):
    notify_rate_message = ''
    klines = []
    for info in symbols_info:
        klines_res = binance_set.get_historical_klines(info['symbol'], '5m', '10 minute ago UTC')
        if klines_res is None or len(klines_res) == 0:
            continue
        kline = set_kline_info(info['symbol'], klines_res[0])
        # 同一symbolで売却していない購入履歴があるか確認
        is_buy_history = next(filter(lambda x: x['symbol'] == kline['symbol'], buy_histories), None)
        action = pass_or_buy_or_sell(kline, bnb_ticker[info['symbol']], is_buy_history)
        notify_rate_message += check_and_order(kline, bnb_ticker[info['symbol']], action)  # 本番用
        # notify_rate_message += check_and_order_demo(kline, bnb_ticker[info['symbol']], action)  # デモトレード用
        klines.append(kline)
    mongo_set.insert_many('crypto_info', klines)
    return notify_rate_message


def pass_or_buy_or_sell(kline, current_price, is_buy_history):
    change_rate = (float(kline['close']) / float(kline['open'])) - float(1)
    if (prop.REFERENCE_RATE_5m / 100 <= change_rate
            and float(kline['taker_buy_quote_asset_volume']) > 10):
        # トークン未購入でtotal5つ以上購入済みの場合は無視
        if (not is_buy_history) and buy_count >= 5:
            return 'pass'
        # 過去2回分の情報を取得
        result = mongo_set.find('crypto_info',
                                __filter__={
                                    'symbol': kline['symbol'],
                                    'open_time': {"$gte": datetime.now() + timedelta(minutes=-30)}
                                },
                                sort=[('open_time', mc.DESCENDING)], limit=2)
        try:
            # 第2条件(過去2回ともプラスで終わっている)
            if result[0]['open'] < result[0]['close'] and result[1]['open'] < result[1]['close']:
                # 購入済とそれ以外で処理分岐
                if is_buy_history:
                    return 'buy_but_pass'
                else:
                    return 'buy'
                    # return 'pass'
        except IndexError:
            pass
    if is_buy_history:
        # 購入時の情報を取得する
        result = mongo_set.find('trade_histories', __filter__={'symbol': kline['symbol'], 'sell_date': None})[0]
        # 買値より上で'AUTO_SELL_RATE'以下 and 3時間以上経過(高利益のものは売却したくないため)
        is_higher = float(result['buy_price']) < float(current_price)
        buy_current_rate = (float(current_price) / float(result['buy_price'])) - float(1)
        elapsed_days = datetime.now() - result['buy_date']
        is_3hour_ago = elapsed_days.total_seconds() > prop.AUTO_SELL_INTERVAL
        if is_higher and prop.AUTO_SELL_RATE / 100 >= buy_current_rate and is_3hour_ago:
            return 'sell'
    return 'pass'


def check_and_order(kline, current_price, action):
    global buy_count
    if action == 'buy':
        asset = binance_set.get_asset('BNB')
        bnb_amount = float(asset['free']) / (5 - buy_count)
        order_amount = bnb_amount / float(current_price)
        amt_str = format_amt_str(kline['symbol'], 'quote', order_amount)
        result = binance_set.order_market_buy(kline['symbol'], amt_str)  # 買いオーダー
        if result is None:
            return f'\n{kline["symbol"]}の購入失敗'
        # 'trade_histories'に買い情報追加
        mongo_set.insert_one('trade_histories', {'symbol': kline['symbol'],
                                                 'buy_amount': amt_str,
                                                 'buy_price': current_price,
                                                 'buy_date': datetime.now()})
        buy_count += 1
        return f'\n{kline["symbol"]}を{current_price}で買いました'
    elif action == 'sell':
        # symbolから末尾3文字(BNB)を切り取ってassetを取得
        asset = binance_set.get_asset(kline['symbol'][:-3])
        order_amount = float(asset['free'])
        amt_str = format_amt_str(kline['symbol'], 'quote', order_amount)
        result = binance_set.order_market_sell(kline['symbol'], amt_str)  # 売りオーダー
        if result is None:
            return f'\n{kline["symbol"]}の売却失敗'
        # 'trade_histories'に売り日付/量を追加
        mongo_set.update_one('trade_histories',
                             _filter={'symbol': kline['symbol'], 'sell_date': None},
                             _update={'$set': {'sell_date': datetime.now(),
                                               'sell_amount': amt_str,
                                               'sell_price': current_price}})
        return f'\n{kline["symbol"]}を売りました'
    elif action == 'buy_but_pass':
        return f'\n{kline["symbol"]}は上昇中'
    elif action == 'pass':
        pass
    return ''


def format_amt_str(symbol: str, precision_type: str, order_amount: float):
    symbol_info = next(filter(lambda x: x['symbol'] == symbol, symbols_info), None)
    # 最小単位を取得
    step_size = float([i['stepSize'] for i in symbol_info['filters'] if i['filterType'] == 'LOT_SIZE'][0])
    # オーダー量を最小単位に調整
    format_order_amount = (order_amount // step_size) * step_size
    precision = symbol_info[f'{precision_type}AssetPrecision']
    return "{:0.0{}f}".format(format_order_amount, precision)


def set_kline_info(symbol, kline):
    return {
        'symbol': symbol,
        'open_time': datetime.fromtimestamp(kline[0] / 1000),
        'open': kline[1],
        'high': kline[2],
        'low': kline[3],
        'close': kline[4],
        'volume': kline[5],
        'close_time': datetime.fromtimestamp(kline[6] / 1000),
        'quote_asset_volume': kline[7],
        'number_of_trades': kline[8],
        'taker_buy_base_asset_volume': kline[9],
        'taker_buy_quote_asset_volume': kline[10],
        'can_be_ignored': kline[11]
    }


def main():
    load_data()
    set_data()

    notify_message = check_goal()
    notify_rate_message_30m, bnb_ticker = check_rate_30m()
    notify_rate_message_5m = check_rate_5m(bnb_ticker)

    # LINEに通知する
    message_list = filter(lambda x: x != '', [notify_message, notify_rate_message_30m, notify_rate_message_5m])
    message = '\n'.join(message_list)
    if message != '':
        # print(message)
        line_notify.notify(message)

    dump_data()


def check_and_order_demo(kline, current_price, action):
    global buy_count
    order_message = ''
    if action == 'buy':
        bnb_token = list(mongo_set.find('trade_histories', __filter__={'symbol': 'BNB'}))[0]
        bnb_amount = float(bnb_token['amount']) / (5 - buy_count)
        order_amount = bnb_amount / float(current_price)
        amt_str = format_amt_str(kline['symbol'], 'base', order_amount)
        # 'trade_histories'に買い情報追加
        mongo_set.insert_one('trade_histories', {'symbol': kline['symbol'],
                                                 'buy_amount': amt_str,
                                                 'buy_price': current_price,
                                                 'buy_date': datetime.now()})
        bnb_total_amount = str(float(bnb_token['amount']) - (float(amt_str) * float(current_price)))
        mongo_set.update_one('trade_histories',
                             _filter={'symbol': 'BNB'},
                             _update={'$set': {'amount': bnb_total_amount}})
        buy_count += 1
        order_message = f'\n{kline["symbol"]}を{current_price}で買いました'
    elif action == 'sell':
        bnb_token = list(mongo_set.find('trade_histories', __filter__={'symbol': 'BNB'}))[0]
        token = mongo_set.find('trade_histories', __filter__={'symbol': kline['symbol'], 'sell_date': None})
        order_amount = float(token['buy_amount'])
        amt_str = format_amt_str(kline['symbol'], 'quote', order_amount)
        # 'trade_histories'に売り日付/量を追加
        mongo_set.update_one('trade_histories',
                             _filter={'symbol': kline['symbol'], 'sell_date': None},
                             _update={'$set': {'sell_amount': amt_str,
                                               'sell_price': current_price,
                                               'sell_date': datetime.now()}})
        bnb_total_amount = str(float(bnb_token['amount']) + (float(amt_str) * float(current_price)))
        mongo_set.update_one('trade_histories',
                             _filter={'symbol': 'BNB'},
                             _update={'$set': {'amount': bnb_total_amount}})
        buy_count += -1
        order_message = f'\n{kline["symbol"]}を売りました'
    elif action == 'buy_but_pass':
        order_message = f'\n{kline["symbol"]}は上昇中'
    elif action == 'pass':
        pass
    return order_message


if __name__ == '__main__':
    # main()
    print('何もしないよ')
