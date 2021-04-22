import os

project_name: str = 'trade_job'

root_dir: str = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
data_dir: str = f'{root_dir}/data'

notified_interval: int = 60  # 指定通貨の通知間隔(分単位)
notify_rate: float = 15  # 変化率の通知基準(%)
rate_interval: int = 30  # 変化率の通知間隔(分単位)

binance_api_key: str = 'BinanceのAPIキー'
binance_api_secret: str = 'Binanceの秘密キー'
dropbox_access_token: str = 'DropBoxのアクセストークン'
line_notify_token: str = 'LINE Notifyのアクセストークン'
