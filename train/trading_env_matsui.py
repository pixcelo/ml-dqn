import gym
import numpy as np
import pandas as pd
from gym import spaces

class TradingEnvMatsui(gym.Env):
    def __init__(self, df, gamma=0.95, f=0.5, eta=0.1, max_holdings=1):
        super(TradingEnvMatsui, self).__init__()

        self.df = df
        self.reward_range = (-np.inf, np.inf)
        self.action_space = spaces.Discrete(3)  # 0: Do nothing, 1: Buy, 2: Sell
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(self.df.shape[1] + 4,))

        self.cash_initial = 1000000
        self.cash = self.cash_initial
        self.holdings = 0
        self.max_holdings = max_holdings
        self.history = []
        self.episode_reward = 0
        self.episode_rewards = []
        self.actions_history = []
        self.total_asset_history = []
        self.holdings_history = []
        
        self.gamma = gamma  # Discount factor
        self.f = f  # Investment ratio parameter (bet fraction)
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
            if self.cash >= current_price and self.holdings < self.max_holdings:
                self.holdings += 1
                self.cash -= current_price * (1 + self.transaction_cost)
                self.purchase_price = current_price
            else:
                reward -= penalty
        elif action == 2:  # Sell
            if self.holdings > 0:
                self.holdings -= 1
                self.cash += current_price * (1 - self.transaction_cost)
            else:
                reward -= penalty

        new_total_asset = self.cash + self.holdings * current_price

        # Calculate reward as increase in asset value
        if old_total_asset > 0:
            # Use return instead of asset increase
            reward = (new_total_asset - old_total_asset) / old_total_asset
            # Apply the compound return and discount
            reward = (1 + reward * self.f) ** self.gamma
            # print(f"reward:{reward}, self.f:{self.f}, self.gamma:{self.gamma}")
        else:
            reward = 0

        # If no stocks are held and no action is taken, reward is zero due to lost opportunity.
        if self.holdings == 0 and action == 0:
            reward = -0.5

        # Update f using online gradient method
        self.f += self.eta * reward / (1 + reward * self.f)
        self.f = max(0, min(self.f, 0.99))  # ensure f is less than 1
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

        self.episode_rewards.append(self.episode_reward)
        self.actions_history.append(action)
        self.total_asset_history.append(total_asset)
        self.holdings_history.append(self.holdings)

        return self._get_observation(), reward, done, {}
    
    def reset(self):
        self.cash = self.cash_initial
        self.holdings = 0
        self.current_step = 0
        self.purchase_price = 0 
        self.f = 0.5  # Reset the investment ratio
        self.episode_reward = 0
        return self._get_observation()
    
    def _get_observation(self):
        total_asset = self.cash + self.holdings * self.purchase_price
        cash_ratio = self.cash / total_asset
        holdings_ratio = self.holdings * self.purchase_price / total_asset
        return np.append(self.df.iloc[self.current_step], [self.holdings, self.cash, cash_ratio, holdings_ratio])