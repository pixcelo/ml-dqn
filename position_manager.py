class PositionManager:
    def __init__(self, exchange, symbol):
        self.exchange = exchange
        self.symbol = symbol
        self.position = []
        self.update_positions()

    def update_positions(self):
        try:
            response = self.exchange.fetch_positions([self.symbol])
            positions = response
            self.positions = []  # init self.positions
            for position in positions:
                if position['entryPrice'] is not None and \
                   position['symbol'].split(':')[0].replace("/", "") == self.exchange.market_id(self.symbol).replace("/", ""):
                    self.positions.append(position)
        except Exception as e:
            print(f"An error occurred while fetching positions: {e}")

    def get_position_size(self):
        if self.position is not None:
            return abs(float(self.position['size']))
        return 0

    def get_position_side(self):
        if self.position is not None:
            side = 'long' if float(self.position['size']) > 0 else 'short'
            return side
        return None

    def get_position_pnl(self):
        if self.position is not None:
            return float(self.position['unrealised_pnl'])
        return None
    
    def separate_positions_by_side(self):
        long_positions = []
        short_positions = []

        for position in self.positions:
            if position['info']['side'] == 'Buy':
                long_positions.append(position)
            elif position['info']['side'] == 'Sell':
                short_positions.append(position)

        return long_positions, short_positions
