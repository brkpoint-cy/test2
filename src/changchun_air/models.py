import torch
from torch import nn


class LSTMClassifier(nn.Module):
    def __init__(self, n_features: int, hidden_size: int):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden_size, batch_first=True)
        self.output = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
        sequence, _ = self.lstm(x)
        logits = self.output(sequence[:, -1]).squeeze(1)
        return logits, {}
