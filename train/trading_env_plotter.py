import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

class TradingEnvPlotter:
    def __init__(self, action_space):
        self.action_space = action_space
        self.total_asset_history = []
        self.actions_history = []
        self.episode_rewards = []
        self.df_history = pd.DataFrame()
        
    def update_history(self, history, total_asset_history, actions_history, episode_rewards):
        self.df_history = pd.DataFrame(history)
        self.df_history.set_index('step', inplace=True)
        self.total_asset_history.append(total_asset_history)
        self.actions_history.append(actions_history)
        self.episode_rewards.append(episode_rewards)

    def plot_history(self):
        fig, ax = plt.subplots(2, 2, figsize=[8, 6])

        # Total Asset over time
        ax[0][0].plot(self.total_asset_history[-1], label='Total Asset', linestyle='-')
        ax[0][0].yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:.0f}"))
        ax[0][0].set_title('Total Asset over Time')
        ax[0][0].legend(loc='upper left')

        # Action over time
        ax[0][1].plot(self.actions_history[-1], label='Actions History', linestyle='-')
        ax[0][1].set_title('Action over time')
        ax[0][1].legend(loc='upper left')
        ax[0][1].set_yticks(range(self.action_space.n))

        # Cumulative reward plot
        ax[1][0].plot(np.cumsum(self.episode_rewards[-1]), label='Cumulative Reward', linestyle='-')
        ax[1][0].set_title('Cumulative Reward per Episode')
        ax[1][0].legend(loc='upper left')
        ax[1][0].autoscale_view(scalex=True, scaley=True)

        # Reward over time
        ax[1][1].plot(self.episode_rewards[-1], label='Reward', linestyle='-')
        ax[1][1].set_title('Reward over Time')
        ax[1][1].legend(loc='upper left')

        plt.tight_layout()
        plt.show()

    def plot_stock_price(self, df):
        fig, ax = plt.subplots(figsize=[16, 4])
        ax.plot(df.index, df['close'], label='Close Price')
        ax.set_title('Stock Price')
        ax.legend(loc='upper left')
        plt.tight_layout()
        plt.show()
