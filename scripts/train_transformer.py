
# FILE: scripts/train_transformer.py
from __future__ import annotations

from typing import List

try:
    import torch.nn as nn
    TORCH_OK=True
except Exception:
    TORCH_OK=False

from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout
from a3d.reweight_transformer import _TinyEdgeTransformer  # type: ignore


def _make_batch(cfg) -> List[float]:
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    nX = len(rt.builder.node_order("X"))
    import random
    random.seed(123)
    sX = [1 if random.random()<0.05 else 0 for _ in range(nX)]
    sZ = [0]*len(rt.builder.node_order("Z"))
    w_space_X, w_time_X, p_erase_X = rt._weight_dicts_from_cfg("X")
    g = rt.builder.build("X", w_space_X, w_time_X, p_erase_X)
    # Super simple target: 1.0 for time edges, else 0.0 (placeholder signal)
    y = [1.0 if e.etype=="time" else 0.0 for e in g.edges]
    return g, y

def main(out_path: str = "edge_reweighter.pt") -> int:
    if not TORCH_OK:
        print("Torch not available; training skipped.")
        return 0
    cfg = AegisConfig(distance=3, rounds=3, decoder_type="mwpm")
    g, y = _make_batch(cfg)
    import torch
    x = torch.tensor([[0.0]*10 for _ in g.edges], dtype=torch.float32).unsqueeze(0)
    # reuse the feature extractor path by calling the reweighter once
    from a3d.reweight_transformer import _edge_features
    feats = _edge_features(g)
    x = torch.tensor(feats, dtype=torch.float32).unsqueeze(0)
    y = torch.tensor(y, dtype=torch.float32).unsqueeze(0)

    model = _TinyEdgeTransformer()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()

    for _ in range(10):
        opt.zero_grad()
        pred = model(x)
        loss = loss_fn(pred, y)
        loss.backward()
        opt.step()

    torch.save(model.state_dict(), out_path)
    print("Saved", out_path)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
