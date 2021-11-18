# 抜けてるローソク足を補完したり、でもトレードの実績を確認したりするファイルです。
from datetime import datetime

from trade_job import trade_info_main as main
from trade_job.submodules import binance_class as bc, mongo_class as mc


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


def set_data():
    global symbols_info, buy_histories, buy_count
    # 取引所情報を取得、特定のSymbolの取引所情報を取得
    symbols_info = [i for i in binance_set.get_symbols_info()
                    if i['quoteAsset'] == 'BNB' and i['status'] == 'TRADING']
    # BNBを除く保持トークンを取得
    buy_histories = list(mongo_set.find('trade_histories',
                                        __filter__={"$and": [{'symbol': {'$ne': 'BNB'}}, {'sell_date': None}]}))
    buy_count = len(buy_histories)


def get_total_bnb():
    all_ticker = binance_set.get_symbol_ticker(None)
    bnb_ticker = {i['symbol']: i['price'] for i in all_ticker
                  if i['symbol'].endswith('BNB')}
    token_list = list(mongo_set.find('trade_histories', __filter__={'sell_date': None}))
    bnb_amount = 0.0
    token_to_bnb_total = 0.0
    for token in token_list:
        if token['symbol'] == 'BNB':
            bnb_amount = float(token['amount'])
            print(f'BNB：{bnb_amount}')
            continue
        token_to_bnb = float(token['buy_amount']) * float(bnb_ticker[token['symbol']])
        buy_bnb = float(token['buy_amount']) * float(token['buy_price'])
        print(f'{token["symbol"]}の差分：{token_to_bnb - buy_bnb}')
        token_to_bnb_total += token_to_bnb
    print(f'合計：{bnb_amount + token_to_bnb_total}')


def insert_klines(start, end):
    symbols_info_1 = [i for i in binance_set.get_symbols_info()
                      if i['quoteAsset'] == 'BNB' and i['status'] == 'TRADING']
    for info in symbols_info_1:
        klines = []
        klines_res = binance_set.get_historical_klines(info['symbol'], '5m', start_str=start, end_str=end)
        if klines_res is None or len(klines_res) == 0:
            continue
        for i, k in enumerate(klines_res):
            if i == (len(klines_res) - 1):
                continue
            kline = main.set_kline_info(info['symbol'], k)
            klines.append(kline)
        mongo_set.insert_many('crypto_info', klines)


def sell_tokens_demo(sell_token_list):
    all_ticker = binance_set.get_symbol_ticker(None)
    bnb_ticker = {i['symbol']: i['price'] for i in all_ticker
                  if i['symbol'].endswith('BNB')}
    token_list = list(mongo_set.find('trade_histories',
                                     __filter__={"$and": [{'symbol': {'$ne': 'BNB'}}, {'sell_date': None}]}))
    if sell_token_list[0] == "ALL":
        sell_token_list = {i['symbol'] for i in token_list if i['symbol'] != 'BNB'}
    for sell_token in sell_token_list:
        for token in token_list:
            if token['symbol'] != sell_token:
                continue
            bnb_token = mongo_set.find('trade_histories', __filter__={'symbol': 'BNB'})[0]
            order_amount = float(token['buy_amount'])
            amt_str = "{:0.0{}f}".format(order_amount, 8)
            # 'trade_histories'に売り日付/量を追加
            mongo_set.update_one('trade_histories',
                                 _filter={'symbol': token['symbol'], 'sell_date': None},
                                 _update={'$set': {'sell_amount': amt_str,
                                                   'sell_price': bnb_ticker[sell_token],
                                                   'sell_date': datetime.now()}})
            bnb_total_amount = str(float(bnb_token['amount']) + (float(amt_str) * float(bnb_ticker[sell_token])))
            mongo_set.update_one('trade_histories',
                                 _filter={'symbol': 'BNB'},
                                 _update={'$set': {'amount': bnb_total_amount}})
            print(f'{sell_token}を売りました')


def sell_tokens(sell_token_list):
    all_ticker = binance_set.get_symbol_ticker(None)
    bnb_ticker = {i['symbol']: i['price'] for i in all_ticker
                  if i['symbol'].endswith('BNB')}
    for sell_token in sell_token_list:
        # symbolから末尾3文字(BNB)を切り取ってassetを取得
        asset = binance_set.get_asset(sell_token[:-3])
        order_amount = float(asset['free'])
        result = binance_set.order_market_sell(sell_token, order_amount)  # 売りオーダー
        if result is None:
            return f'\n{sell_token}の売却失敗'
        print(result)
        # 'trade_histories'に売り日付/量を追加
        mongo_set.update_one('trade_histories',
                             _filter={'symbol': sell_token, 'sell_date': None},
                             _update={'$set': {'sell_date': datetime.now(),
                                               'sell_amount': result['fills'][0]['price'],
                                               'sell_price': bnb_ticker[sell_token]}})
        print(f'\n{sell_token}を売りました')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # asset_dict = binance_set.get_asset('BNB')
    # print(asset_dict['free'])
    # ローソク足手動取得
    # start = '2021-11-21T10:25+09:00'  # '3 hours ago UTC' or '2021-11-19T13:10+09:00'
    # end = '2021-11-21T12:35+09:00'
    # insert_klines(start, end)
    # デモ取引のトークンを売る
    # sell_tokens(['PROMBNB'])
    # sell_tokens_demo(['PROMBNB'])
    # bnb_amount_1 = 1.0 / 5
    # order_amount_1 = ((bnb_amount_1 / 0.00020714) // 1) * 1
    # amt_str_1 = "{:0.0{}f}".format(order_amount_1, 8)
    # print(bnb_amount_1, order_amount_1, amt_str_1)
    # デモのtotalBNBを'trade_histories'から計算
    get_total_bnb()
