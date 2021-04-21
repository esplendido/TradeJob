# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for submodules, files, tool windows, actions, and settings.
import csv

from trade_job.submodules import binance_class as bc, dropbox_class as dc, line_notify, \
    properties as prop, const

FILE_NAME = 'TradeJob'


def is_equals_hash(content_hash):
    try:
        with open(f'{prop.data_dir}/{FILE_NAME}.content_hash', 'r') as f:
            s_line = f.readline()
    except FileNotFoundError:
        s_line = ''
    # hashが更新されている場合はファイルを書き換える
    if s_line != content_hash:
        with open(f'{prop.data_dir}/{FILE_NAME}.content_hash', 'w') as f:
            f.write(content_hash)
    return s_line == content_hash


def main():
    binance_set = bc.BinanceAPI()
    dropbox_set = dc.DropboxAPI()

    (meta_data, res) = dropbox_set.get_file_data(f'/{FILE_NAME}.csv')
    if res.status_code == 200:
        if not is_equals_hash(meta_data.content_hash):
            dropbox_set.download(f'/{FILE_NAME}.csv', f'{prop.data_dir}/{FILE_NAME}.csv')
            print('ダウンロードしたよ')

    notification_message = ''
    with open(f'{prop.data_dir}/{FILE_NAME}.csv', 'r') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            ticker = binance_set.get_ticker(row['銘柄'])
            if row['取得項目'] == 'askPrice' and float(row['目標数値']) > float(ticker[row['取得項目']]):
                notification_message = f'{notification_message}\n' \
                                       f'■{row["銘柄"]}\n' \
                                       f'  買い目標値({row["目標数値"]})\n' \
                                       f'  {const.price_info_lint[row["取得項目"]]}({ticker[row["取得項目"]]})'
            elif row['取得項目'] == 'bidPrice' and float(row['目標数値']) < float(ticker[row['取得項目']]):
                notification_message = f'{notification_message}\n' \
                                       f'■{row["銘柄"]}\n' \
                                       f'  売り目標値({row["目標数値"]})\n' \
                                       f'  {const.price_info_lint[row["取得項目"]]}({ticker[row["取得項目"]]})'
    # line_notify.notify(notification_message)
    print(notification_message)

    # ticker = binance_set.get_ticker_a('BNBUSDT')
    # print(ticker['askPrice'])
    #
    # asset_dict = binance_set.get_asset('BTC')
    # print(asset_dict)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
