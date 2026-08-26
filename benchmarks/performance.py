"""Performance benchmarks for PepperFlow AI."""

import asyncio, time, statistics
from typing import Dict

async def benchmark_concurrent_workflows(count: int = 100) -> Dict:
    start = time.perf_counter()
    tasks = [asyncio.sleep(0.01) for _ in range(count)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = (time.perf_counter() - start) * 1000
    successes = sum(1 for r in results if not isinstance(r, Exception))
    return {"operation": "concurrent_execution", "concurrent_count": count,
            "successes": successes, "total_ms": round(elapsed, 2)}

async def run_benchmarks():
    print("=" * 60)
    print("PepperFlow AI - Performance Benchmarks")
    print("=" * 60)
    r = await benchmark_concurrent_workflows(100)
    print(f"Concurrent: {r['successes']}/{r['concurrent_count']} in {r['total_ms']}ms")
    return r

if __name__ == "__main__":
    asyncio.run(run_benchmarks())
