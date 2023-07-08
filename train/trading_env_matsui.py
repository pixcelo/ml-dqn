import gym
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import plotly.graph_objects as go
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
        self.actions_history = []
        self.total_asset_history = []
        
        self.gamma = gamma  # Discount factor
        self.f = f  # Investment ratio
        self.eta = eta  # Learning rate for f
        self.purchase_price = 0  # To track purchase price for delayed reward calculation
        self.transaction_cost = 0.001

    def step(self, action):
        assert self.action_space.contains(action)

        current_price = self.df.iloc[self.current_step]['close']
        # Check if done before incrementing the step
        done = self.current_step == len(self.df) - 1
        if done:
            return self._get_observation(), 0, done, {}

        self.current_step += 1
        old_total_asset = self.cash + self.holdings * self.purchase_price
        reward = 0
        penalty = 0.1

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
        self.episode_reward += reward

        total_asset = self.cash + self.holdings * current_price

        # Record the history
        self.history.append({
            "step": self.current_step,
            "cash": self.cash,
            "action": action,
            "total_asset": total_asset,
            "reward": reward,
            "done": done
        })

        self.episode_rewards.append(reward)
        self.actions_history.append(action)
        self.total_asset_history.append(total_asset)

        return self._get_observation(), reward, done, {}
    
    def reset(self):
        self.cash = 1000000
        self.holdings = 0
        self.current_step = 0
        self.purchase_price = 0 
        self.f = 0.5  # Reset the investment ratio
        self.episode_reward = 0
        self.history = []
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

        fig, ax = plt.subplots(2, 2, figsize=[8, 6])

        # Total Asset over time
        ax[0][0].plot(self.total_asset_history, label='Total Asset', linestyle='-')
        ax[0][0].yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:.0f}"))
        ax[0][0].set_title('Total Asset over Time')
        ax[0][0].legend(loc='upper left')

        # Action over time
        ax[0][1].plot(self.actions_history, label='Actions History', linestyle='-')
        ax[0][1].set_title('Action over time')
        ax[0][1].legend(loc='upper left')
        ax[0][1].set_yticks(range(self.action_space.n))

        # Cumulative reward plot
        ax[1][0].plot(np.cumsum(self.episode_rewards), label='Cumulative Reward', linestyle='-')
        ax[1][0].set_title('Cumulative Reward per Episode')
        ax[1][0].legend(loc='upper left')
        ax[1][0].autoscale_view(scalex=True, scaley=True)

        # Reward over time
        ax[1][1].plot(self.episode_rewards, label='Reward', linestyle='-')
        ax[1][1].set_title('Reward over Time')
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