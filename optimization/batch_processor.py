"""
Batch Processor - Process items in bulk for Jarvis AI.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, Iterable, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Process items in batches with:
    - Parallel execution
    - Error handling
    - Progress tracking
    - Result aggregation
    """

    def __init__(self, config: Config):
        self.config = config
        self.batch_size = config.get("optimization.batch_size", 32)
        self.max_workers = config.get("optimization.max_workers", 4)

    def process(
        self,
        items: List[Any],
        func: Callable,
        batch_size: Optional[int] = None,
        parallel: bool = True,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> Dict:
        """
        Process a list of items using `func`.
        Returns: {results, errors, total, success_count, duration_seconds}
        """
        batch_size = batch_size or self.batch_size
        start = time.time()
        results = []
        errors = []

        if parallel:
            results, errors = self._parallel_process(items, func, on_progress)
        else:
            results, errors = self._sequential_process(items, func, batch_size, on_progress)

        duration = round(time.time() - start, 3)
        return {
            "results": results,
            "errors": errors,
            "total": len(items),
            "success_count": len(results),
            "error_count": len(errors),
            "duration_seconds": duration,
        }

    def _parallel_process(
        self, items: List[Any], func: Callable, on_progress: Optional[Callable]
    ):
        results = []
        errors = []
        completed = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(func, item): item for item in items}
            for future in as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                    results.append({"input": str(item)[:100], "result": result})
                except Exception as e:
                    errors.append({"input": str(item)[:100], "error": str(e)})
                completed += 1
                if on_progress:
                    on_progress(completed, len(items))
        return results, errors

    def _sequential_process(
        self,
        items: List[Any],
        func: Callable,
        batch_size: int,
        on_progress: Optional[Callable],
    ):
        results = []
        errors = []
        for i, item in enumerate(items):
            try:
                result = func(item)
                results.append({"input": str(item)[:100], "result": result})
            except Exception as e:
                errors.append({"input": str(item)[:100], "error": str(e)})
            if on_progress:
                on_progress(i + 1, len(items))
        return results, errors

    def chunk(self, items: List[Any], size: Optional[int] = None) -> List[List[Any]]:
        """Split a list into chunks of given size."""
        size = size or self.batch_size
        return [items[i : i + size] for i in range(0, len(items), size)]
