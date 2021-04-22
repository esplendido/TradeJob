# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for submodules, files, tool windows, actions, and settings.
import csv
import datetime
import pickle

from trade_job.submodules import binance_class as bc, dropbox_class as dc, line_notify, \
    trade_job_data as data, \
    properties as prop, const

FILE_NAME = 'TradeJob'

job_data: data.TradeJobData = None


def load_data():
    try:
        with open(f'{prop.data_dir}/job_data.pickle', 'rb') as f:
            global job_data
            job_data = pickle.load(f)
    except FileNotFoundError:
        job_data = data.TradeJobData()


def dump_data():
    with open(f'{prop.data_dir}/job_data.pickle', 'wb') as f:
        pickle.dump(job_data, f)


def is_equals_hash(content_hash):
    last_hash = job_data.trade_job_hash
    # hashが更新されている場合は書き換える
    if last_hash != content_hash:
        job_data.trade_job_hash = content_hash
    return last_hash == content_hash


def is_notified(pair: str, notified_list: dict, interval: int):
    if pair not in notified_list:
        return False
    return datetime.datetime.now() - notified_list[pair] < datetime.timedelta(minutes=interval)


def add_trade_message(notify_message, row, ticker, trade_name):
    return f'{notify_message}\n' \
           f'■{row["銘柄"]}\n' \
           f'  {trade_name}目標値(${row["目標数値"]})\n' \
           f'  {const.price_info_lint[row["取得項目"]]}(${round(float(ticker[row["取得項目"]]), 4)})'


def add_rate_message(notify_rate_message, symbol, change_rate, price):
    return f'{notify_rate_message}\n' \
           f'{symbol.replace("USDT",""): <5}' \
           f'：30分変化率({round(change_rate * float(100), 2): >6}%)' \
           f'：${round(float(price), 3)}'


def main():
    load_data()

    binance_set = bc.BinanceAPI()
    dropbox_set = dc.DropboxAPI()

    (meta_data, res) = dropbox_set.get_file_data(f'/{FILE_NAME}.csv')
    if res.status_code == 200:
        if not is_equals_hash(meta_data.content_hash):
            dropbox_set.download(f'/{FILE_NAME}.csv', f'{prop.data_dir}/{FILE_NAME}.csv')
            print('ダウンロードしたよ')

    notify_message = ''
    with open(f'{prop.data_dir}/{FILE_NAME}.csv', 'r') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            if not is_notified(row['銘柄'], job_data.notified_list, prop.notified_interval):
                ticker = binance_set.get_ticker(row['銘柄'])
                if row['取得項目'] == 'askPrice' and float(row['目標数値']) > float(ticker[row['取得項目']]):
                    notify_message = add_trade_message(notify_message, row, ticker, '買い')
                    job_data.notified_list[row["銘柄"]] = datetime.datetime.now()
                elif row['取得項目'] == 'bidPrice' and float(row['目標数値']) < float(ticker[row['取得項目']]):
                    notify_message = add_trade_message(notify_message, row, ticker, '売り')
                    job_data.notified_list[row["銘柄"]] = datetime.datetime.now()

    # 30分変化率のリストを作成
    notify_rate_message = ''
    all_ticker = binance_set.get_symbol_ticker(None)
    usdt_ticker = {i['symbol']: i['price'] for i in all_ticker
                   if i['symbol'].endswith('USDT')
                   and not(i['symbol'].endswith('UPUSDT') or i['symbol'].endswith('DOWNUSDT'))}
    job_data.usdt_ticker_list.append(usdt_ticker)
    if len(job_data.usdt_ticker_list) == 7:
        # 6回前に取得したデータを取り出す
        data_ticker = job_data.usdt_ticker_list.pop(0)
        for symbol, price in usdt_ticker.items():
            if not is_notified(symbol, job_data.rate_notified_list, prop.rate_interval):
                if symbol in data_ticker:
                    price_30m_ago = data_ticker[symbol]
                else:
                    continue
                change_rate = (float(price) / float(price_30m_ago)) - float(1)
                if change_rate <= -prop.notify_rate/100 or prop.notify_rate/100 <= change_rate:
                    notify_rate_message = add_rate_message(notify_rate_message, symbol, change_rate, price)
                    job_data.rate_notified_list[symbol] = datetime.datetime.now()

    # LINEに通知する
    message_list = filter(lambda x: x != '', [notify_message, notify_rate_message])
    message = '\n'.join(message_list)
    if message != '':
        # print(message)
        line_notify.notify(message)

    dump_data()

    # ticker = binance_set.get_symbol_ticker(None)
    # print(ticker)
    #
    # asset_dict = binance_set.get_asset('BTC')
    # print(asset_dict)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
