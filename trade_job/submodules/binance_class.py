from binance.client import Client

from trade_job.submodules import properties as prop


class BinanceAPI:

    def __init__(self):

        self.client = Client(prop.BINANCE_API_KEY, prop.BINANCE_API_SECRET)

    # 指定通貨の統計情報を取得
    def get_ticker(self, pair):
        return self.__exe_func('get_ticker', symbol=pair)

    # 指定通貨の統計情報を取得
    def get_symbol_ticker(self, pair):
        return self.__exe_func('get_symbol_ticker', symbol=pair)

    # 資産情報を取得
    def get_balances(self):
        balances = self.__exe_func('get_account')['balances']
        return [b for b in balances if float(b['free']) > 0]

    # 指定通貨の資産情報を取得
    def get_asset(self, symbol):
        return self.__exe_func('get_asset_balance', asset=symbol)

    # 指定通貨のローソク足情報を取得
    def get_historical_klines(self, pair, interval='5m', start_str='1 hour ago UTC', end_str=None):
        return self.__exe_func('get_historical_klines',
                               symbol=pair,
                               interval=interval,
                               start_str=start_str,
                               end_str=end_str
                               )

    # 取引通貨情報を取得
    def get_symbols_info(self):
        return self.__exe_func('get_exchange_info')['symbols']

    # 成行注文_買い
    def order_market_buy(self, symbol, quantity):
        return self.__exe_func('order_market_buy', symbol=symbol, quantity=quantity)

    # 成行注文_売り
    def order_market_sell(self, symbol, quantity):
        return self.__exe_func('order_market_sell', symbol=symbol, quantity=quantity)

    def __exe_func(self, name, **arg):
        try:
            # value = self.client.get_ticker(pair)
            method = getattr(self.client, name)
            value = method(**arg)
            return value
        except Exception as e:
            print('BinanceAPI Exception Message : {}'.format(e))
            return None
