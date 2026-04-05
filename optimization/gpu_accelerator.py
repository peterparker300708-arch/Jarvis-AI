"""
GPU Accelerator - GPU detection and acceleration utilities.
"""

import logging
from typing import Dict, List

from utils.config import Config

logger = logging.getLogger(__name__)


class GPUAccelerator:
    """
    Detects and provides information about available GPU resources.
    Enables CUDA/GPU acceleration when available.
    """

    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.get("optimization.gpu_enabled", False)
        self._cuda_available = False
        self._device_info: List[Dict] = []
        if self.enabled:
            self._detect()

    def _detect(self):
        """Detect available GPU devices."""
        try:
            import torch
            self._cuda_available = torch.cuda.is_available()
            if self._cuda_available:
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    self._device_info.append(
                        {
                            "index": i,
                            "name": props.name,
                            "memory_gb": round(props.total_memory / 1e9, 2),
                            "compute_capability": f"{props.major}.{props.minor}",
                        }
                    )
                logger.info(f"CUDA available: {len(self._device_info)} device(s)")
        except ImportError:
            logger.debug("PyTorch not available — GPU acceleration disabled")

    def is_available(self) -> bool:
        return self._cuda_available

    def get_devices(self) -> List[Dict]:
        return self._device_info

    def get_best_device(self) -> str:
        """Return 'cuda' if GPU available, else 'cpu'."""
        if self._cuda_available:
            return "cuda"
        return "cpu"

    def get_memory_usage(self) -> Dict:
        """Return GPU memory usage."""
        if not self._cuda_available:
            return {}
        try:
            import torch
            info = {}
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i)
                total = torch.cuda.get_device_properties(i).total_memory
                info[f"device_{i}"] = {
                    "allocated_gb": round(allocated / 1e9, 3),
                    "total_gb": round(total / 1e9, 3),
                    "percent": round(allocated / total * 100, 1),
                }
            return info
        except Exception:
            return {}

    def get_status(self) -> Dict:
        return {
            "enabled": self.enabled,
            "cuda_available": self._cuda_available,
            "devices": self._device_info,
            "best_device": self.get_best_device(),
        }
