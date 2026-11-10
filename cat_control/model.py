"""The published 134-D KMD-Transformer architecture."""

from __future__ import annotations

import torch
from torch import nn


class MotionTransformer(nn.Module):
    def __init__(
        self,
        input_size: int = 134,
        num_classes: int = 11,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.25,
    ) -> None:
        super().__init__()
        self.input_norm = nn.LayerNorm(input_size)
        self.projection = nn.Linear(input_size, hidden_size)
        self.position = nn.Parameter(torch.zeros(1, 30, hidden_size))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=4,
            dim_feedforward=hidden_size * 2,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(
            encoder_layer, num_layers=num_layers, enable_nested_tensor=False
        )
        self.classifier = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        values = self.projection(self.input_norm(inputs))
        values = values + self.position[:, : inputs.shape[1]]
        encoded = self.encoder(values)
        return self.classifier(encoded.max(dim=1).values)
