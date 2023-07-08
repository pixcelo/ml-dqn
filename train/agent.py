import numpy as np
import random
import torch
from torch import optim
from collections import deque
from qnetwork import QNetwork
import datetime

class Agent:
    def __init__(self, env, state_size, action_size, atom_size=51, gamma=0.99, lr=0.9):
        self.env = env
        self.state_size = state_size
        self.action_size = action_size
        self.atom_size = atom_size
        self.v_min = -10
        self.v_max = 10
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.support = torch.linspace(self.v_min, self.v_max, self.atom_size).to(self.device)

        # Initialize Q-Network and target network
        self.q_network = QNetwork(state_size, action_size, atom_size, self.support, self.v_min, self.v_max).to(self.device)
        self.target_network = QNetwork(state_size, action_size, atom_size, self.support, self.v_min, self.v_max).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.target_network.eval()
        # delta_zは、DQNにおけるDistributional DQNの一部となる確率分布の離散化のための間隔
        self.delta_z = (self.v_max - self.v_min) / (self.atom_size - 1)

        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        self.gamma = gamma

        # epsilon-greedy method
        self.epsilon_min = 0.01
        self.epsilon_max = 1.0
        self.epsilon_decay = 0.995

        # Initialize experience replay memory
        self.memory = deque(maxlen=2000)
        self.batch_size = 64

    # 確率的に行動を選択するε-グリーディー法と、ネットワークによるQ値予測を用いた行動選択を行う
    def get_action(self, state, episode):
        # Decrease epsilon over time
        epsilon = max(self.epsilon_min, self.epsilon_max - self.epsilon_decay * episode)
        
        if np.random.rand() <= epsilon:
            return random.randrange(self.action_size)
        
        state = torch.from_numpy(state).float().unsqueeze(0).to(self.device)
        with torch.no_grad():
            act_values = (self.q_network(state) * self.support).sum(dim=2)

        action = np.argmax(act_values.cpu().data.numpy())
        return action

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def replay(self):
        # Sample a minibatch from memory
        minibatch = random.sample(self.memory, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*minibatch)
        states = torch.tensor(states).float().to(self.device)
        actions = torch.tensor(actions).long().unsqueeze(1).to(self.device)
        rewards = torch.tensor(rewards).float().unsqueeze(1).to(self.device)
        next_states = torch.tensor(next_states).float().to(self.device)
        dones = torch.tensor(dones).float().unsqueeze(1).to(self.device)

        # Compute Q(s_t, a)
        q_dist = self.q_network(states)
        q_dist = q_dist.gather(2, actions.unsqueeze(2).expand(-1, -1, self.atom_size))

        # Compute distributional Bellman update
        with torch.no_grad():
            next_action = (self.q_network(next_states) * self.support).sum(2).max(1)[1]
            next_dist = self.target_network(next_states)[torch.arange(self.batch_size), next_action]
            t_z = rewards + (1 - dones) * self.gamma * self.support.unsqueeze(0)
            t_z = t_z.clamp(min=self.v_min, max=self.v_max)
            b = (t_z - self.v_min) / self.delta_z
            l = b.floor().long()
            u = b.ceil().long()
            d_m_l = (u.float() + (l == u).float() - b) * next_dist
            d_m_u = (b - l.float()) * next_dist
        m = states.new_zeros(self.batch_size, self.atom_size)
        m.scatter_add_(1, l, d_m_l)
        m.scatter_add_(1, u, d_m_u)

        # Update Q_Network
        self.q_network.train()
        self.optimizer.zero_grad()
        loss = -(m * q_dist.log()).sum(1).mean()
        loss.backward()
        self.optimizer.step()

        # Update target network
        self.update_target_network()

    def update_target_network(self, tau=0.05):
        for target_param, param in zip(self.target_network.parameters(), self.q_network.parameters()):
            target_param.data.copy_(tau*param.data + (1.0-tau)*target_param.data)

    def learn(self, current_episode, total_episodes):
        state = self.env.reset()
        state = np.reshape(state, [1, self.state_size])
        for time in range(total_episodes):
            action = self.get_action(state, current_episode)
            next_state, reward, done, _ = self.env.step(action)
            next_state = np.reshape(next_state, [1, self.state_size])
            self.remember(state, action, reward, next_state, done)
            state = next_state
            if done:
                # print("Episode: {}/{}, Score: {}" 
                #         .format(current_episode, total_episodes, self.env.episode_reward))
                break
            if len(self.memory) > self.batch_size:
                self.replay()
            
        return self.env.episode_reward
    
    def save_model(self):
        # Get current date and time
        now = datetime.datetime.now()

        # Format datetime object to string
        now_str = now.strftime('%Y%m%d_%H%M%S')

        # Save model weights with datetime in filename
        torch.save(self.q_network.state_dict(), '../model/model_weights_' + now_str + '.pth')

    def load_model(self, model_path):
        self.q_network.load_state_dict(torch.load(model_path))
        self.q_network.eval()

    def perform_action(self, state):
        state = torch.from_numpy(state).float().unsqueeze(0).to(self.device)
        with torch.no_grad():
            act_values = (self.q_network(state) * self.support).sum(dim=2)
        return np.argmax(act_values.cpu().data.numpy())