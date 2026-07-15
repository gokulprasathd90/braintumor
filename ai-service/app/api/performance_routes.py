"""
app/api/performance_routes.py — Performance monitoring & benchmarking API.

Endpoints
---------
GET  /performance/summary          Full JSON performance report (all subsystems).
GET  /performance/report/html      Self-contained HTML performance report.
GET  /performance/profiler         Function-level profiler summary.
GET  /performance/memory           Memory usage report.
GET  /performance/cache            Cache hit/miss/eviction report.
GET  /performance/api-stats        Per-endpoint latency and RPS stats.
GET  /performance/concurrency      Last concurrency / stress-test report.
POST /performance/benchmark/run    Run the benchmark suite (background or inline).
GET  /performance/benchmark/result Last completed benchmark suite result.
POST /performance/benchmark/single Run a single named benchmark inline.
DELETE /performance/profiler/reset  Clear all profiler and API-optimizer data.

All mutating or heavy endpoints require ADMIN or OPERATOR role.
Read-only endpoints require any authenticated user.
"""

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.security.auth import UserInDB
from app.security.dependencies import get_current_active_user, require_roles
from app.security.rate_limit import limiter, limits
from app.security.roles import Role

performance_router = APIRouter(prefix="/performance", tags=["Performance"])


# ─── Shared response schemas ──────────────────────────────────────────────────

class PerformanceResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    message: str = ""


class BenchmarkRunRequest(BaseModel):
    n_inference:  int = Field(default=10,  ge=1, le=100,  description="Inference iterations per benchmark")
    n_preprocess: int = Field(default=20,  ge=1, le=200,  description="Preprocessing iterations per benchmark")
    n_cache:      int = Field(default=50,  ge=1, le=500,  description="Cache iterations per benchmark")
    batch_sizes:  List[int] = Field(
        default=[4, 8, 16],
        description="Batch sizes to test in batch-inference benchmark",
    )
    background:   bool = Field(
        default=False,
        description="Run the suite in a background thread and return immediately",
    )


class SingleBenchmarkRequest(BaseModel):
    name: str = Field(
        description=(
            "Benchmark name. One of: preprocessing, image_quality_check, "
            "single_inference, cache_get_hit, cache_stats_call, "
            "dataset_metadata, system_metrics, inference_metrics"
        )
    )
    n: int = Field(default=10, ge=1, le=200, description="Number of iterations")


class BenchmarkRunResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    background: bool = False


# ─── In-process benchmark state ───────────────────────────────────────────────

_benchmark_lock   = threading.Lock()
_benchmark_running = False
_last_benchmark_result: Optional[Dict[str, Any]] = None


def _run_suite_background(
    n_inference: int,
    n_preprocess: int,
    n_cache: int,
    batch_sizes: List[int],
) -> None:
    """Thread target: run benchmark suite and cache the result."""
    global _benchmark_running, _last_benchmark_result
    try:
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(
            n_inference=n_inference,
            n_preprocess=n_preprocess,
            n_cache=n_cache,
        )
        result = suite.run_all(batch_sizes=batch_sizes)
        with _benchmark_lock:
            _last_benchmark_result = result.to_dict()
        logger.info("[Performance] Background benchmark suite completed.")
    except Exception as exc:
        logger.exception(f"[Performance] Background benchmark suite failed: {exc}")
        with _benchmark_lock:
            _last_benchmark_result = {
                "error": f"{type(exc).__name__}: {exc}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
    finally:
        with _benchmark_lock:
            _benchmark_running = False


# ─── GET /performance/summary ─────────────────────────────────────────────────

@performance_router.get(
    "/summary",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Full JSON performance report across all subsystems",
)
@limiter.limit(limits.DASHBOARD)
def performance_summary(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
) -> PerformanceResponse:
    """
    Return a composite JSON snapshot that covers:

    - **system** — CPU %, RAM, disk, GPU (if available), process RSS
    - **inference** — total predictions, success rate, avg / p95 latency
    - **cache** — model-cache and prediction-cache hit/miss rates
    - **memory** — RSS, memory-profiler operation log, leak warnings
    - **api** — per-endpoint call counts, avg/p95 latency, error rates
    - **profiler** — top-10 slowest profiled functions
    - **concurrency** — last concurrent-load test result

    **Required role**: any authenticated user.
    """
    try:
        from app.performance.reports import generate_performance_report
        report = generate_performance_report()
        return PerformanceResponse(
            success=True,
            data=report,
            message="Performance report generated.",
        )
    except Exception as exc:
        logger.exception("Failed to generate performance summary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not generate performance report: {exc}",
        )


# ─── GET /performance/report/html ─────────────────────────────────────────────

@performance_router.get(
    "/report/html",
    status_code=status.HTTP_200_OK,
    summary="Self-contained HTML performance report",
    response_class=None,   # handled manually below
)
@limiter.limit(limits.DASHBOARD)
def performance_html_report(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Return the full performance report as a self-contained HTML page.

    Suitable for opening in a browser or embedding in an iframe.
    Content-Type is ``text/html``.

    **Required role**: any authenticated user.
    """
    from fastapi.responses import HTMLResponse

    try:
        from app.performance.reports import generate_performance_report, generate_html_report
        report = generate_performance_report()
        html   = generate_html_report(report)
        return HTMLResponse(content=html, status_code=200)
    except Exception as exc:
        logger.exception("Failed to generate HTML performance report")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not generate HTML report: {exc}",
        )


# ─── GET /performance/profiler ────────────────────────────────────────────────

@performance_router.get(
    "/profiler",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Function-level profiler summary",
)
@limiter.limit(limits.DASHBOARD)
def performance_profiler(
    request: Request,
    top: int = Query(default=20, ge=1, le=200, description="Number of top functions to return"),
    current_user: UserInDB = Depends(get_current_active_user),
) -> PerformanceResponse:
    """
    Return a summary of all functions timed by the global ``Profiler`` instance.

    Results are sorted by **avg_ms descending** (slowest first).

    Query params
    ------------
    - ``top`` — how many entries to return (default 20, max 200)

    **Required role**: any authenticated user.
    """
    try:
        from app.performance.profiler import get_profiler
        profiler = get_profiler()
        summary  = profiler.summary(top=top)
        return PerformanceResponse(
            success=True,
            data=summary,
            message=f"Profiler summary: {summary.get('total_functions', 0)} function(s) tracked.",
        )
    except Exception as exc:
        logger.exception("Failed to get profiler summary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profiler error: {exc}",
        )


# ─── GET /performance/memory ──────────────────────────────────────────────────

@performance_router.get(
    "/memory",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Memory usage and leak-detection report",
)
@limiter.limit(limits.DASHBOARD)
def performance_memory(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
) -> PerformanceResponse:
    """
    Return the memory profiler report including:

    - Current process RSS (MB)
    - Memory deltas per tracked operation
    - Leak warnings (operations where RSS grew more than the threshold)
    - tracemalloc top allocations (if active)

    **Required role**: any authenticated user.
    """
    try:
        from app.performance.memory import get_memory_profiler
        report = get_memory_profiler().get_report()
        return PerformanceResponse(
            success=True,
            data=report,
            message=(
                f"Memory report. Current RSS: {report.get('current_rss_mb', 'N/A')} MB. "
                f"Warnings: {report.get('warning_count', 0)}."
            ),
        )
    except Exception as exc:
        logger.exception("Failed to get memory report")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Memory report error: {exc}",
        )


# ─── GET /performance/cache ───────────────────────────────────────────────────

@performance_router.get(
    "/cache",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Cache hit/miss/eviction report across all caches",
)
@limiter.limit(limits.DASHBOARD)
def performance_cache(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
) -> PerformanceResponse:
    """
    Return a composite cache report covering:

    - **model_cache** — LRU model-weights cache (hits, misses, evictions, hit rate)
    - **prediction_cache** — repeated-prediction short-circuit cache
    - **dataset_metadata_cache** — dataset_info.json read cache
    - **dashboard_cache** — time-bounded dashboard snapshot cache
    - **recommendations** — tuning suggestions from CacheOptimizer

    **Required role**: any authenticated user.
    """
    try:
        from app.performance.cache import get_cache_report
        report = get_cache_report()
        mc = report.get("model_cache", {})
        hit_rate = mc.get("hit_rate", 0.0)
        return PerformanceResponse(
            success=True,
            data=report,
            message=f"Cache report. Model cache hit rate: {hit_rate:.1%}.",
        )
    except Exception as exc:
        logger.exception("Failed to get cache report")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache report error: {exc}",
        )


# ─── GET /performance/api-stats ───────────────────────────────────────────────

@performance_router.get(
    "/api-stats",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Per-endpoint request latency and RPS statistics",
)
@limiter.limit(limits.DASHBOARD)
def performance_api_stats(
    request: Request,
    slow_only: bool = Query(
        default=False,
        description="When true, return only endpoints with p95 latency > 500 ms",
    ),
    current_user: UserInDB = Depends(get_current_active_user),
) -> PerformanceResponse:
    """
    Return per-endpoint call counts, avg / median / p95 / p99 latency,
    error rates, and RPS derived from the ``APIOptimizer`` singleton.

    The optimizer is fed by the ``log_requests`` middleware in ``main.py``
    so data accumulates from the moment the server starts.

    Query params
    ------------
    - ``slow_only`` — filter to endpoints where p95 > 500 ms (default false)

    **Required role**: any authenticated user.
    """
    try:
        from app.performance.optimizer import get_api_optimizer
        optimizer = get_api_optimizer()
        report = optimizer.get_api_report()

        if slow_only:
            endpoints = report.get("all_endpoints", [])
            report["all_endpoints"] = [e for e in endpoints if e.get("is_slow", False)]
            report["slow_only_filter"] = True

        total = len(report.get("all_endpoints", []))
        return PerformanceResponse(
            success=True,
            data=report,
            message=f"API stats report. {total} endpoint(s) tracked.",
        )
    except Exception as exc:
        logger.exception("Failed to get API stats")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API stats error: {exc}",
        )


# ─── GET /performance/concurrency ─────────────────────────────────────────────

@performance_router.get(
    "/concurrency",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Last concurrency / stress-test report",
)
@limiter.limit(limits.DASHBOARD)
def performance_concurrency(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
) -> PerformanceResponse:
    """
    Return the most recent result from the ``ConcurrencyProfiler`` singleton.

    This is populated whenever a concurrent load test is run either
    programmatically via ``run_concurrent()`` or from the benchmark suite.

    **Required role**: any authenticated user.
    """
    try:
        from app.performance.concurrency import get_concurrency_profiler
        profiler = get_concurrency_profiler()
        report   = profiler.get_report()
        count    = report.get("total_tests", 0)
        return PerformanceResponse(
            success=True,
            data=report,
            message=f"Concurrency report. {count} run(s) recorded.",
        )
    except Exception as exc:
        logger.exception("Failed to get concurrency report")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Concurrency report error: {exc}",
        )


# ─── POST /performance/benchmark/run ─────────────────────────────────────────

@performance_router.post(
    "/benchmark/run",
    response_model=BenchmarkRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the full benchmark suite",
)
@limiter.limit(limits.TRAINING)   # benchmark is CPU-heavy; use the same conservative cap as training
async def benchmark_run(
    request: Request,
    body: BenchmarkRunRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
) -> BenchmarkRunResponse:
    """
    Run all benchmarks in ``BenchmarkSuite``.

    **Inline mode** (``background: false``, default)
    — Runs synchronously and returns the full result in the response.
      Can take 30-120 seconds depending on the iteration counts.

    **Background mode** (``background: true``)
    — Returns immediately with ``202``-style payload; the suite runs in a
      background thread.  Poll ``GET /performance/benchmark/result`` for the
      outcome.

    Only one benchmark suite may run at a time.  A ``409 Conflict`` is
    returned if a run is already in progress.

    **Required role**: ADMIN or OPERATOR.
    """
    global _benchmark_running, _last_benchmark_result

    with _benchmark_lock:
        if _benchmark_running:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A benchmark suite is already running. Poll GET /performance/benchmark/result.",
            )

        if body.background:
            _benchmark_running = True

    if body.background:
        background_tasks.add_task(
            _run_suite_background,
            body.n_inference,
            body.n_preprocess,
            body.n_cache,
            body.batch_sizes,
        )
        logger.info(
            "[Performance] Benchmark suite started in background "
            f"(n_inference={body.n_inference}, n_preprocess={body.n_preprocess}, "
            f"n_cache={body.n_cache})"
        )
        return BenchmarkRunResponse(
            success=True,
            message="Benchmark suite started in background. Poll GET /performance/benchmark/result.",
            background=True,
        )

    # ── Inline (synchronous) run ──────────────────────────────────────────────
    try:
        from app.performance.benchmark import BenchmarkSuite
        suite = BenchmarkSuite(
            n_inference=body.n_inference,
            n_preprocess=body.n_preprocess,
            n_cache=body.n_cache,
        )
        result = suite.run_all(batch_sizes=body.batch_sizes)
        result_dict = result.to_dict()

        with _benchmark_lock:
            _last_benchmark_result = result_dict

        summary = result.summary()
        logger.info(
            f"[Performance] Inline benchmark suite finished: "
            f"{summary.get('ok', 0)} ok, {summary.get('errors', 0)} errors, "
            f"{summary.get('total_ms', 0):.0f}ms total"
        )
        return BenchmarkRunResponse(
            success=True,
            message=(
                f"Benchmark suite completed. "
                f"{summary.get('ok', 0)}/{summary.get('total', 0)} benchmarks passed."
            ),
            data=result_dict,
            background=False,
        )
    except Exception as exc:
        logger.exception("Benchmark suite failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark suite error: {exc}",
        )


# ─── GET /performance/benchmark/result ────────────────────────────────────────

@performance_router.get(
    "/benchmark/result",
    response_model=BenchmarkRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Last completed benchmark suite result",
)
@limiter.limit(limits.DASHBOARD)
def benchmark_result(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
) -> BenchmarkRunResponse:
    """
    Return the result of the last ``POST /performance/benchmark/run`` call
    (whether inline or background).

    Returns **404** when no benchmark has been run yet in this server process.

    If a background run is still in progress ``running: true`` is included in
    the data payload.

    **Required role**: any authenticated user.
    """
    with _benchmark_lock:
        running = _benchmark_running
        result  = _last_benchmark_result

    if result is None and not running:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No benchmark result available. Run POST /performance/benchmark/run first.",
        )

    if running and result is None:
        return BenchmarkRunResponse(
            success=True,
            message="Benchmark suite is still running.",
            data={"running": True},
            background=True,
        )

    return BenchmarkRunResponse(
        success=True,
        message="Last benchmark result." + (" (suite still running)" if running else ""),
        data={**(result or {}), "running": running},
        background=not running,
    )


# ─── POST /performance/benchmark/single ───────────────────────────────────────

@performance_router.post(
    "/benchmark/single",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Run a single named benchmark inline",
)
@limiter.limit(limits.TRAINING)
async def benchmark_single(
    request: Request,
    body: SingleBenchmarkRequest,
    current_user: UserInDB = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
) -> PerformanceResponse:
    """
    Run one benchmark by name and return its statistics immediately.

    Available benchmark names
    -------------------------
    ``preprocessing``, ``image_quality_check``, ``single_inference``,
    ``cache_get_hit``, ``cache_stats_call``, ``dataset_metadata``,
    ``system_metrics``, ``inference_metrics``

    **Request body**:
    ```json
    {"name": "single_inference", "n": 20}
    ```

    **Required role**: ADMIN or OPERATOR.
    """
    try:
        from app.performance.benchmark import run_benchmark
        stat = run_benchmark(body.name, n=body.n)
        return PerformanceResponse(
            success=stat.status == "ok",
            data=stat.to_dict(),
            message=(
                f"Benchmark '{body.name}' completed with status '{stat.status}'."
                + (f" Error: {stat.error}" if stat.error else "")
            ),
        )
    except Exception as exc:
        logger.exception(f"Single benchmark '{body.name}' failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark error: {exc}",
        )


# ─── DELETE /performance/profiler/reset ───────────────────────────────────────

@performance_router.delete(
    "/profiler/reset",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear all profiler and API-optimizer data",
)
def profiler_reset(
    current_user: UserInDB = Depends(require_roles(Role.ADMIN)),
) -> PerformanceResponse:
    """
    Wipe all accumulated data from:

    - The global ``Profiler`` (function timing history)
    - The global ``APIOptimizer`` (per-endpoint latency records)
    - The global ``MemoryProfiler`` (operation log)

    This is useful before running a clean benchmark baseline.

    **Required role**: ADMIN only.
    """
    cleared: List[str] = []
    errors:  List[str] = []

    try:
        from app.performance.profiler import get_profiler
        get_profiler().reset()
        cleared.append("profiler")
    except Exception as exc:
        errors.append(f"profiler: {exc}")

    try:
        from app.performance.optimizer import get_api_optimizer
        get_api_optimizer().reset()
        cleared.append("api_optimizer")
    except Exception as exc:
        errors.append(f"api_optimizer: {exc}")

    try:
        from app.performance.memory import get_memory_profiler
        get_memory_profiler().reset()
        cleared.append("memory_profiler")
    except Exception as exc:
        errors.append(f"memory_profiler: {exc}")

    return PerformanceResponse(
        success=len(errors) == 0,
        data={"cleared": cleared, "errors": errors},
        message=(
            f"Reset {len(cleared)} subsystem(s)."
            + (f" Errors: {errors}" if errors else "")
        ),
    )
