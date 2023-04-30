class PositionManager:
    def __init__(self, exchange, symbol):
        self.exchange = exchange
        self.symbol = symbol
        self.position = None
        self.update_position()

    def update_position(self):
        try:
            response = self.exchange.fetchPositions()
            positions = response
            for position in positions:
                if position['symbol'] == self.exchange.market_id(self.symbol):
                    self.position = position
                    break
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