"""
app/performance — Production-grade performance profiling, benchmarking,
memory management, cache optimization, and concurrency analysis.

Public API
----------
Profiling:
    Profiler, profile_function, profile_block, get_profile_report

Benchmarking:
    BenchmarkSuite, BenchmarkResult, run_benchmark, run_all_benchmarks

Memory:
    MemoryProfiler, MemorySnapshot, get_memory_report, track_memory

Cache:
    CacheOptimizer, CacheBenchmark, get_cache_report

Concurrency:
    ConcurrencyProfiler, run_concurrent, get_concurrency_report

Reports:
    ReportGenerator, generate_performance_report, generate_html_report
"""

from __future__ import annotations

from app.performance.profiler import (
    Profiler,
    ProfileResult,
    FunctionProfile,
    profile_function,
    profile_block,
    get_profiler,
)
from app.performance.benchmark import (
    BenchmarkSuite,
    BenchmarkResult,
    BenchmarkStats,
    run_benchmark,
)
from app.performance.memory import (
    MemoryProfiler,
    MemorySnapshot,
    get_memory_profiler,
    track_memory,
)
from app.performance.cache import (
    CacheOptimizer,
    CacheStats,
    get_cache_optimizer,
)
from app.performance.concurrency import (
    ConcurrencyProfiler,
    ConcurrencyResult,
    run_concurrent,
    get_concurrency_profiler,
)
from app.performance.optimizer import (
    APIOptimizer,
    EndpointStats,
    record_request,
    get_api_stats,
)
from app.performance.reports import (
    ReportGenerator,
    get_report_generator,
    generate_performance_report,
    generate_html_report,
)

__all__ = [
    # Profiler
    "Profiler", "ProfileResult", "FunctionProfile",
    "profile_function", "profile_block", "get_profiler",
    # Benchmark
    "BenchmarkSuite", "BenchmarkResult", "BenchmarkStats", "run_benchmark",
    # Memory
    "MemoryProfiler", "MemorySnapshot", "get_memory_profiler", "track_memory",
    # Cache
    "CacheOptimizer", "CacheStats", "get_cache_optimizer",
    # Concurrency
    "ConcurrencyProfiler", "ConcurrencyResult", "run_concurrent",
    "get_concurrency_profiler",
    # Optimizer
    "APIOptimizer", "EndpointStats", "record_request", "get_api_stats",
    # Reports
    "ReportGenerator", "get_report_generator",
    "generate_performance_report", "generate_html_report",
]
