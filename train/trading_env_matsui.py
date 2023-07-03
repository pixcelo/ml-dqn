import gym
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from gym import spaces

class TradingEnvMatsui(gym.Env):
    def __init__(self, df, gamma=0.95, f=0.5, eta=0.1):
        super(TradingEnvMatsui, self).__init__()

        self.df = df
        self.reward_range = (-np.inf, np.inf)
        self.action_space = spaces.Discrete(3)  # 0: Do nothing, 1: Buy, 2: Sell
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(self.df.shape[1] + 4,))

        self.cash = 1000000  # Initial cash position
        self.holdings = 0  # Initial asset holdings
        self.history = []  # Initialize history
        self.episode_rewards = [] 

        self.gamma = gamma  # Discount factor
        self.f = f  # Investment ratio
        self.eta = eta  # Learning rate for f
        self.purchase_price = 0  # To track purchase price for delayed reward calculation

    def step(self, action):
        assert self.action_space.contains(action)

        current_price = self.df.iloc[self.current_step]['close']
        
        # Check if done before incrementing the step
        done = self.current_step == len(self.df) - 1
        if done:
            return self._get_observation(), 0, done, {}  # return zero reward

        self.current_step += 1

        old_total_asset = self.cash + self.holdings * self.purchase_price

        reward = 0
        penalty = 0.1

        # Action logic
        if action == 1:  # Buy
            if self.cash >= current_price:
                self.holdings += 1
                self.cash -= current_price
                self.purchase_price = current_price
            else:
                reward -= penalty
        elif action == 2:  # Sell
            if self.holdings > 0:
                self.holdings -= 1
                self.cash += current_price
            else:
                reward -= penalty

        new_total_asset = self.cash + self.holdings * current_price

        # Calculate reward as increase in asset value
        if old_total_asset > 0:
            # Use return instead of asset increase
            reward = (new_total_asset - old_total_asset) / old_total_asset
            # Apply the compound return and discount
            reward = (1 + reward * self.f) ** self.gamma
        else:
            reward = 0

        # Update f using online gradient method
        self.f += self.eta * reward / (1 + reward * self.f)

        # Record the history
        self.history.append({
            "step": self.current_step,
            "cash": self.cash,
            "action": action,
            "total_asset": self.cash + self.holdings * current_price
        })

        return self._get_observation(), reward, done, {}

    def reset(self):
        self.cash = 1000000
        self.holdings = 0
        self.current_step = 0
        self.purchase_price = 0 
        self.f = 0.5  # Reset the investment ratio
        return self._get_observation()
    
    def _get_observation(self):
        total_asset = self.cash + self.holdings * self.purchase_price
        if total_asset > 0:
            cash_ratio = self.cash / total_asset
            holdings_ratio = self.holdings * self.purchase_price / total_asset
        else:
            cash_ratio = 0
            holdings_ratio = 0
        return np.append(self.df.iloc[self.current_step], [self.holdings, self.cash, cash_ratio, holdings_ratio])
           
    def plot_history(self):
        df_history = pd.DataFrame(self.history)
        df_history.set_index('step', inplace=True)

        fig, ax = plt.subplots(2, 2, figsize=[16, 10])

        # Total Asset over time
        ax[0][0].plot(df_history['total_asset'], label='Total Asset', linestyle='-')
        ax[0][0].set_title('Total Asset over Time')
        ax[0][0].legend(loc='upper left')

        # Action over time
        ax[0][1].plot(df_history['action'], label='Action over time', linestyle='-')
        ax[0][1].set_title('Action over Time')
        ax[0][1].legend(loc='upper left')

        # Cumulative reward plot
        ax[1][0].plot(np.cumsum(self.episode_rewards), label='Cumulative Reward', linestyle='-')
        ax[1][0].set_title('Cumulative Reward per Episode')
        ax[1][0].legend(loc='upper left')

        # Learning curve plot
        ax[1][1].plot([np.mean(self.episode_rewards[i-100:i]) if i >= 100 else np.mean(self.episode_rewards[:i]) for i in range(1, len(self.episode_rewards)+1)], label='Learning Curve (Reward per 100 episodes)')
        ax[1][1].set_title('Learning Curve')
        ax[1][1].legend(loc='upper left')

        plt.tight_layout()
        plt.show()

    def plot_stock_price(self):
        fig, ax = plt.subplots(figsize=[16, 4])
        ax.plot(self.df.index, self.df['close'], label='Close Price')
        ax.set_title('Stock Price')
        ax.legend(loc='upper left')
        plt.tight_layout()
        plt.show()