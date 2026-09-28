"""Experimental Transformer reweighting scaffold.

This script does not train a scientifically validated QEC model. Its current
supervision target is deliberately synthetic: time-like edges are labelled 1
and all other edges are labelled 0. The output is useful only for exercising
the optional model-loading path during development.

Do not commit generated checkpoints or cite them as evidence of decoder
performance. A production training pipeline needs a documented dataset,
objective, held-out evaluation, provenance, and reproducible configuration.
"""

from __future__ import annotations

import os
from typing import List

try:
    import torch.nn as nn

    TORCH_OK = True
except Exception:
    TORCH_OK = False

from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout
from a3d.graph import DecodingGraph
from a3d.reweight_transformer import _TinyEdgeTransformer  # type: ignore


def _make_batch(cfg: AegisConfig) -> tuple[DecodingGraph, List[float]]:
    layout = RotatedSurfaceLayout(cfg.distance)
    runtime = DecoderRuntime(cfg, layout)
    w_space_x, w_time_x, p_erase_x = runtime._weight_dicts_from_cfg("X")
    graph = runtime.builder.build("X", w_space_x, w_time_x, p_erase_x)

    # Placeholder supervision for development-path testing only.
    targets = [1.0 if edge.etype == "time" else 0.0 for edge in graph.edges]
    return graph, targets


def main(out_path: str = "artifacts/edge_reweighter.pt") -> int:
    if not TORCH_OK:
        print("Torch not available; experimental training scaffold skipped.")
        return 0

    import torch

    cfg = AegisConfig(distance=3, rounds=3, decoder_type="mwpm")
    graph, targets = _make_batch(cfg)

    from a3d.reweight_transformer import _edge_features

    features = _edge_features(graph)
    x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
    y = torch.tensor(targets, dtype=torch.float32).unsqueeze(0)

    model = _TinyEdgeTransformer()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()

    for _ in range(10):
        optimizer.zero_grad()
        prediction = model(x)
        loss = loss_fn(prediction, y)
        loss.backward()
        optimizer.step()

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    torch.save(model.state_dict(), out_path)
    print("Saved experimental checkpoint to", out_path)
    print("This checkpoint is development scaffolding, not a validated QEC model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
