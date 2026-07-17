"""
app/performance/reports.py — Automated performance report generation.

Generates:
  - JSON performance report (all modules)
  - HTML report with tables and colour-coded results
  - Benchmark report
  - Memory report
  - Cache report
  - API performance report
  - Optimization summary

Usage
-----
    from app.performance.reports import generate_performance_report, generate_html_report

    report = generate_performance_report()          # full JSON dict
    html   = generate_html_report(report)           # HTML string
    path   = get_report_generator().save_report(report, output_dir="reports/")
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging import logger


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_display() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ─── ReportGenerator ─────────────────────────────────────────────────────────

class ReportGenerator:
    """Generates and persists performance reports."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        if output_dir is None:
            try:
                from app.core.config import settings
                output_dir = settings.log_dir / "performance"
            except Exception:
                output_dir = Path("logs") / "performance"
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # ── Data collection ───────────────────────────────────────────────────────

    def _collect_system(self) -> Dict[str, Any]:
        try:
            from app.metrics.system import get_system_metrics
            return get_system_metrics()
        except Exception as exc:
            return {"error": str(exc)}

    def _collect_inference_metrics(self) -> Dict[str, Any]:
        try:
            from app.metrics.inference import get_inference_metrics
            return get_inference_metrics()
        except Exception as exc:
            return {"error": str(exc)}

    def _collect_cache_report(self) -> Dict[str, Any]:
        try:
            from app.performance.cache import get_cache_report
            return get_cache_report()
        except Exception as exc:
            return {"error": str(exc)}

    def _collect_memory_report(self) -> Dict[str, Any]:
        try:
            from app.performance.memory import get_memory_profiler
            return get_memory_profiler().get_report()
        except Exception as exc:
            return {"error": str(exc)}

    def _collect_api_report(self) -> Dict[str, Any]:
        try:
            from app.performance.optimizer import get_api_stats
            return get_api_stats()
        except Exception as exc:
            return {"error": str(exc)}

    def _collect_profiler_summary(self) -> Dict[str, Any]:
        try:
            from app.performance.profiler import get_profiler
            return get_profiler().summary()
        except Exception as exc:
            return {"error": str(exc)}

    def _collect_concurrency_report(self) -> Dict[str, Any]:
        try:
            from app.performance.concurrency import get_concurrency_profiler
            return get_concurrency_profiler().get_report()
        except Exception as exc:
            return {"error": str(exc)}

    # ── Report assembly ───────────────────────────────────────────────────────

    def build_performance_report(self) -> Dict[str, Any]:
        """Collect and assemble the full performance report."""
        return {
            "report_type":   "performance",
            "generated_at":  _now_iso(),
            "system":        self._collect_system(),
            "inference":     self._collect_inference_metrics(),
            "cache":         self._collect_cache_report(),
            "memory":        self._collect_memory_report(),
            "api":           self._collect_api_report(),
            "profiler":      self._collect_profiler_summary(),
            "concurrency":   self._collect_concurrency_report(),
        }

    def build_benchmark_report(
        self, benchmark_result: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Build a benchmark-focused report, optionally from a BenchmarkResult."""
        if benchmark_result is not None:
            data = benchmark_result.to_dict() if hasattr(benchmark_result, "to_dict") else benchmark_result
        else:
            # Run a quick suite
            try:
                from app.performance.benchmark import BenchmarkSuite
                suite = BenchmarkSuite(n_inference=5, n_preprocess=10, n_cache=20)
                result = suite.run_all()
                data = result.to_dict()
            except Exception as exc:
                data = {"error": str(exc)}

        return {
            "report_type":  "benchmark",
            "generated_at": _now_iso(),
            "benchmark":    data,
            "system":       self._collect_system(),
        }

    # ── Serialisation ─────────────────────────────────────────────────────────

    def save_report(
        self,
        report: Dict[str, Any],
        *,
        filename: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Save *report* as JSON and return the path."""
        out_dir = Path(output_dir) if output_dir else self._output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            rtype = report.get("report_type", "report")
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{rtype}_{ts}.json"

        path = out_dir / filename
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
        logger.info(f"[Reports] Saved {report.get('report_type', 'report')} → {path}")
        return path

    def save_html_report(
        self,
        report: Dict[str, Any],
        *,
        filename: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Save *report* as an HTML file and return the path."""
        out_dir = Path(output_dir) if output_dir else self._output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            rtype = report.get("report_type", "report")
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{rtype}_{ts}.html"

        html = _build_html_from_report(report)
        path = out_dir / filename
        path.write_text(html, encoding="utf-8")
        logger.info(f"[Reports] Saved HTML report → {path}")
        return path


# ─── HTML report builder ──────────────────────────────────────────────────────

def _build_html_report(report: Dict[str, Any]) -> str:
    """Convert a performance report dict into a self-contained HTML page."""
    title = f"Performance Report — {report.get('report_type', 'report').title()}"
    generated = report.get("generated_at", _now_display())

    sections: List[str] = []

    # System metrics
    system = report.get("system", {})
    if system and "error" not in system:
        sections.append(_html_section("System Metrics", [
            ("CPU %",       f"{system.get('cpu_percent', 'N/A')}%"),
            ("RAM used",    f"{system.get('ram_used_mb', 'N/A')} MB"),
            ("RAM %",       f"{system.get('ram_percent', 'N/A')}%"),
            ("Process RSS", f"{system.get('process_rss_mb', 'N/A')} MB"),
            ("Uptime",      f"{system.get('uptime_seconds', 'N/A')}s"),
            ("Platform",    str(system.get("platform", "N/A"))),
        ]))

    # Inference metrics
    inf = report.get("inference", {})
    if inf and "error" not in inf:
        sections.append(_html_section("Inference Metrics", [
            ("Total predictions",  str(inf.get("total_predictions", 0))),
            ("Success rate",       f"{inf.get('success_rate', 0):.1%}"),
            ("Avg latency",        f"{inf.get('avg_latency_ms', 'N/A')} ms"),
            ("P95 latency",        f"{inf.get('p95_latency_ms', 'N/A')} ms"),
            ("Batch runs",         str(inf.get("batch_runs", 0))),
        ]))

    # Cache
    cache = report.get("cache", {})
    mc = cache.get("model_cache", {}) if isinstance(cache, dict) else {}
    if mc:
        sections.append(_html_section("Model Cache", [
            ("Capacity",   str(mc.get("capacity", "N/A"))),
            ("Size",       str(mc.get("size", "N/A"))),
            ("Hit rate",   f"{mc.get('hit_rate', 0):.1%}"),
            ("Total hits", str(mc.get("total_hits", 0))),
            ("Misses",     str(mc.get("total_misses", 0))),
        ]))

    # Memory
    mem = report.get("memory", {})
    if mem and "error" not in mem:
        sections.append(_html_section("Memory", [
            ("Current RSS",    f"{mem.get('current_rss_mb', 'N/A')} MB"),
            ("Ops tracked",    str(mem.get("total_operations_tracked", 0))),
            ("Warnings",       str(mem.get("warning_count", 0))),
        ]))

    # API
    api = report.get("api", {})
    if api and "error" not in api:
        sections.append(_html_section("API", [
            ("Endpoints tracked", str(api.get("total_endpoints_tracked", 0))),
            ("Slow endpoints",    str(len(api.get("slow_endpoints", [])))),
        ]))
        # Ranked endpoints table
        ranked = api.get("ranked_by_latency", [])
        if ranked:
            sections.append(_html_table(
                "Top Endpoints by Latency",
                ["Endpoint", "Method", "Calls", "Avg (ms)", "P95 (ms)", "Error rate"],
                [
                    [s["path"], s["method"], str(s["total_calls"]),
                     f"{s['avg_ms']:.1f}", f"{s['p95_ms']:.1f}",
                     f"{s['error_rate']:.1%}"]
                    for s in ranked[:10]
                ],
            ))

    # Benchmark
    bench = report.get("benchmark", {})
    if bench and "error" not in bench:
        benchmarks = bench.get("benchmarks", [])
        if benchmarks:
            sections.append(_html_table(
                "Benchmark Results",
                ["Name", "N", "Avg (ms)", "P95 (ms)", "Throughput (rps)", "Status"],
                [
                    [b.get("name", ""), str(b.get("n", 0)),
                     f"{b.get('avg_ms', 0):.1f}",
                     f"{b.get('p95_ms', 0):.1f}",
                     f"{b.get('throughput_rps', 0):.1f}",
                     b.get("status", "")]
                    for b in benchmarks
                ],
            ))

    # Concurrency
    conc = report.get("concurrency", {})
    if conc and isinstance(conc, dict):
        conc_results = conc.get("results", [])
        if conc_results:
            sections.append(_html_table(
                "Concurrency Test Results",
                ["Label", "Workers", "Requests", "Completed", "Errors",
                 "Avg (ms)", "P95 (ms)", "Throughput (rps)"],
                [
                    [r.get("label", ""), str(r.get("workers", "")),
                     str(r.get("total_requests", "")), str(r.get("completed", "")),
                     str(r.get("failed", "")),
                     f"{r.get('avg_ms', 0):.1f}",
                     f"{r.get('p95_ms', 0):.1f}",
                     f"{r.get('throughput_rps', 0):.1f}"]
                    for r in conc_results
                ],
            ))

    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          margin: 0; padding: 24px; background: #f5f6fa; color: #222; }}
  h1   {{ color: #1a1a2e; border-bottom: 3px solid #4361ee; padding-bottom: 8px; }}
  h2   {{ color: #4361ee; margin-top: 32px; }}
  .meta{{ color: #666; font-size: 0.9em; margin-bottom: 32px; }}
  .card{{ background: white; border-radius: 8px; padding: 20px;
           box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 24px; }}
  table{{ border-collapse: collapse; width: 100%; }}
  th   {{ background: #4361ee; color: white; padding: 8px 12px;
           text-align: left; font-size: 0.85em; }}
  td   {{ padding: 7px 12px; border-bottom: 1px solid #eee; font-size: 0.88em; }}
  tr:hover td {{ background: #f0f4ff; }}
  .kv  {{ display: grid; grid-template-columns: 200px 1fr; gap: 6px 16px; }}
  .kv-key {{ color: #555; font-size: 0.88em; }}
  .kv-val {{ font-weight: 600; font-size: 0.9em; }}
  .warn{{ color: #e84393; }}
  .ok  {{ color: #2dc653; }}
</style>
</head>
<body>
<h1>🧠 {title}</h1>
<div class="meta">Generated: {generated}</div>
{body}
</body>
</html>"""


def _html_section(title: str, kv_pairs: List[tuple]) -> str:
    rows = "\n".join(
        f'  <div class="kv-key">{k}</div><div class="kv-val">{v}</div>'
        for k, v in kv_pairs
    )
    return f'<div class="card"><h2>{title}</h2><div class="kv">{rows}</div></div>'


def _html_table(title: str, headers: List[str], rows: List[List[str]]) -> str:
    th = "".join(f"<th>{h}</th>" for h in headers)
    tr_rows = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return (
        f'<div class="card"><h2>{title}</h2>'
        f"<table><thead><tr>{th}</tr></thead><tbody>{tr_rows}</tbody></table></div>"
    )


# ── Singletons & convenience functions ────────────────────────────────────────
_report_generator: Optional[ReportGenerator] = None
_rg_lock = threading.Lock()


def get_report_generator() -> ReportGenerator:
    global _report_generator
    with _rg_lock:
        if _report_generator is None:
            _report_generator = ReportGenerator()
    return _report_generator


def generate_performance_report() -> Dict[str, Any]:
    """Build and return the full performance report dict."""
    return get_report_generator().build_performance_report()


def generate_html_report(report: Optional[Dict[str, Any]] = None) -> str:
    """Generate an HTML report string.

    If *report* is None, builds a fresh performance report first.
    Delegates to the module-level HTML builder ``_build_html_report``.
    """
    if report is None:
        report = generate_performance_report()
    return _build_html_report(report)


def _build_html_from_report(report: Dict[str, Any]) -> str:
    """Internal alias used by ReportGenerator.save_html_report."""
    return _build_html_report(report)
