from trade_job.submodules import binance_class as bc, line_notify


def main():
    binance_set = bc.BinanceAPI()
    all_ticker = binance_set.get_symbol_ticker(None)
    usdt_ticker = {i['symbol']: i['price'] for i in all_ticker
                   if i['symbol'].endswith('USDT')
                   and not(i['symbol'].endswith('UPUSDT') or i['symbol'].endswith('DOWNUSDT'))}
    token_list = binance_set.get_balances()
    amount_list = []
    total_amount = 0
    for token in token_list:
        try:
            token_price = usdt_ticker[f'{token["asset"]}USDT']
            holding_amount = round(float(token_price) * float(token["free"]), 3)
            amount_list.append({'asset': token['asset'], 'amount': f'${holding_amount}'})
            total_amount = total_amount + holding_amount
        except KeyError:
            continue

    notify_message = f'\n■資産状況\n  TOTAL:{f"${round(total_amount, 3)}": >9}'
    for amount in amount_list:
        notify_message = f'{notify_message}\n' \
                         f'  {amount["asset"]: <5}:{amount["amount"]: >9}'
    # print(notify_message)
    line_notify.notify(notify_message)


if __name__ == '__main__':
    main()
