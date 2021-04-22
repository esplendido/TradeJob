from binance.client import Client

from trade_job.submodules import properties

BINANCE_API_KEY = properties.binance_api_key
BINANCE_API_SECRET = properties.binance_api_secret


class BinanceAPI:

    def __init__(self):

        self.client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

    # 指定通貨の統計情報を取得
    def get_ticker(self, pair):
        return self.__exe_func('get_ticker', symbol=pair)

    # 指定通貨の統計情報を取得
    def get_symbol_ticker(self, pair):
        return self.__exe_func('get_symbol_ticker', symbol=pair)

    # 指定通貨の資産情報を取得
    def get_asset(self, symbol):
        return self.__exe_func('get_asset_balance', asset=symbol)

    # 資産情報を取得
    def get_balances(self):
        balances = self.__exe_func('get_account')['balances']
        return [b for b in balances if float(b['free']) > 0]

    def __exe_func(self, name, **arg):
        try:
            # value = self.client.get_ticker(pair)
            method = getattr(self.client, name)
            value = method(**arg)
            return value
        except Exception as e:
            print('BinanceAPI Exception Message : {}'.format(e))
            return None
