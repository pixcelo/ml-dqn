class Account:
    def __init__(self, exchange):
        self.exchange = exchange

    def get_balance(self):
        balance = self.exchange.fetch_balance()
        
        print('='*40)
        usdt_balance = balance['total']['USDT']
        print(f'USDT balance: {round(usdt_balance, 2)}')
        
        btc_balance = balance['total']['BTC']
        # print(f'BTC balance: {round(btc_balance, 2)}')
        
        margin_balance = self.exchange.fetch_balance(params={'type': 'margin'})
        usdt_margin_balance = margin_balance['total']['USDT']
        print(f'USDT margin balance: {round(usdt_margin_balance, 2)}')
        btc_margin_balance = margin_balance['total']['BTC']
        # print(f'BTC margin balance: {round(btc_margin_balance, 2)}')
        
        free_margin = margin_balance['free']['USDT']
        print(f'Free margin (USDT): {round(free_margin, 2)}')
        
        if usdt_margin_balance != 0:
            margin_utilization_rate = (usdt_balance - free_margin) / usdt_margin_balance * 100
            print(f'Margin utilization rate: {round(margin_utilization_rate, 2)}%')
        else:
            print("No margin balance available.")

        print('='*40)