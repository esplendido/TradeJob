import requests

from trade_job.submodules import properties


LINE_NOTIFY_TOKEN = properties.line_notify_token


def notify(notification_message):
    # LINEに通知する
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {LINE_NOTIFY_TOKEN}'}
    data = {'message': notification_message}
    requests.post(line_notify_api, headers=headers, data=data)
