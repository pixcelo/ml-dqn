import torch
from torch import nn

class QNetwork(nn.Module):
    def __init__(self, state_size, action_size, atom_size, support, v_min, v_max):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, action_size * atom_size)

        self.v_min = v_min
        self.v_max = v_max
        self.atom_size = atom_size
        self.delta_z = (self.v_max - self.v_min) / (self.atom_size - 1)
        self.action_size = action_size
        self.support = support

    def forward(self, state):
        x = torch.relu(self.fc1(state))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return torch.softmax(x.view(-1, self.action_size, self.atom_size), dim=2) * self.support