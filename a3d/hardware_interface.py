# FILE: a3d/hardware_interface.py
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple

import numpy as np


class QuantumHardwareInterface:
    def __init__(self, backend_name: str = "simulator"):
        self.backend_name = backend_name
        # Keep this base class stateless (no shared mutable fields) for thread safety.

    def _simulate_realistic_noise(self) -> Dict[str, Any]:
        rng = np.random.default_rng(123)
        return {
            "T1_times": rng.exponential(50e-6, size=64),
            "T2_times": rng.exponential(25e-6, size=64),
            "gate_errors": rng.beta(2, 1000, size=64) * 0.01,
            "crosstalk_matrix": rng.normal(0, 0.001, (64, 64)),
            "leakage_rates": rng.beta(1, 1000, size=64) * 0.001,
            "base_error_rate": 1e-3,
            "timestamp": time.time(),
        }

    def get_real_noise_parameters(self) -> Dict[str, Any]:
        return self._simulate_realistic_noise()


class IBMQuantumInterface(QuantumHardwareInterface):
    """
    Cross-platform timeout using a worker thread (best effort).
    If the call does not complete within `timeout_s`, returns the cached result
    (or a simulated fallback). The worker thread is not forcibly killed.
    """

    def __init__(
        self,
        backend_name: str,
        token: str = None,
        cache_duration: float = 300.0,
        timeout_s: float = 30.0,
    ):
        super().__init__(backend_name)
        self.token = token
        self.cache_duration = float(cache_duration)
        self.timeout_s = float(timeout_s)
        self._last_cal: Dict[str, Any] = {}
        self._last_fetch_time = 0.0
        self._api_call_count = 0
        self._window_start_time = time.time()
        self._max_api_calls_per_hour = 100
        self._lock = threading.Lock()
        self.backend = None  # lazy

    def _init_ibm_connection(self) -> None:
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService

            svc = QiskitRuntimeService(channel="ibm_quantum", token=self.token)
            self.backend = svc.backend(self.backend_name)
        except Exception:
            self.backend = None

    def _extract_calibration_safely(self, props, config) -> Dict[str, Any]:
        try:
            n = config.n_qubits
            t1 = np.array([props.t1(q) for q in range(n)], dtype=np.float64)
            t2 = np.array([props.t2(q) for q in range(n)], dtype=np.float64)
            gerrs = []
            for g in props.gates:
                try:
                    if g.gate in ("cx", "cz"):
                        gerrs.append(float(g.parameters[0].value))
                except Exception:
                    continue
            gerrs = (
                np.array(gerrs, dtype=np.float64)
                if len(gerrs)
                else np.array([1e-3], dtype=np.float64)
            )
            crosstalk = np.zeros((n, n), dtype=np.float64)
            if hasattr(config, "coupling_map") and config.coupling_map:
                est = float(np.mean(gerrs) * 0.01)
                for a, b in config.coupling_map:
                    crosstalk[a, b] = crosstalk[b, a] = est
            return {
                "T1_times": t1,
                "T2_times": t2,
                "gate_errors": gerrs,
                "crosstalk_matrix": crosstalk,
                "leakage_rates": np.full(n, 1e-3),
                "base_error_rate": float(np.mean(gerrs)),
                "timestamp": time.time(),
            }
        except Exception:
            return self._simulate_realistic_noise()

    def _fetch_props_and_config(self) -> Optional[Tuple[Any, Any]]:
        try:
            props = self.backend.properties()
            config = self.backend.configuration()
            return props, config
        except Exception:
            return None

    def get_real_noise_parameters(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()

            # Reset per-hour window if needed
            if (now - self._window_start_time) >= 3600.0:
                self._window_start_time = now
                self._api_call_count = 0

            # Rate limit
            if self._api_call_count >= self._max_api_calls_per_hour:
                return self._last_cal or self._simulate_realistic_noise()

            # Cache
            if self._last_cal and (now - self._last_fetch_time) < self.cache_duration:
                return self._last_cal

            try:
                if self.backend is None:
                    self._init_ibm_connection()
                if self.backend is None:
                    raise ConnectionError("IBM backend unavailable")

                result_box: Dict[str, Optional[Tuple[Any, Any]]] = {"val": None}
                done = threading.Event()

                def worker():
                    result_box["val"] = self._fetch_props_and_config()
                    done.set()

                t = threading.Thread(target=worker, daemon=True)
                t.start()
                done.wait(self.timeout_s)

                if not done.is_set() or result_box["val"] is None:
                    return self._last_cal or self._simulate_realistic_noise()

                props, config = result_box["val"]
                self._api_call_count += 1
                cal = self._extract_calibration_safely(props, config)
                self._last_cal = cal
                self._last_fetch_time = now
                return cal
            except Exception:
                return self._last_cal or self._simulate_realistic_noise()
