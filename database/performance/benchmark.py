"""
database/performance/benchmark.py
=================================
SQL Performance Benchmarking and Query Plan Profiling Engine.
Compares query execution latency Before vs After composite covering indexes.
Measures real execution time (ms) and captures EXPLAIN query execution plans.

Usage:
    python database/performance/benchmark.py
"""

import json
import sys
import time
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.loader import WarehouseLoader  # noqa: E402
from etl.utils.logging import logger  # noqa: E402


def run_benchmark(db_url: str | None = None, iterations: int = 25) -> dict[str, Any]:
    """
    Executes comparative query benchmark with and without composite covering indexes.
    Returns latency statistics and EXPLAIN execution plans.
    """
    # Use SQLite file database populated with our 9,107 staged claims
    db_file = PROJECT_ROOT / "data" / "staging" / "benchmark_warehouse.db"
    default_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url or default_url)

    # Initialize data if not loaded
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        ).fetchall()
        table_names = [t[0] for t in tables]

    if "claims" not in table_names:
        logger.info("Populating benchmark database from staging CSVs...")
        loader = WarehouseLoader(db_url=str(engine.url))
        loader.load_all()

    # Analytical Query under test: Date-bounded category aggregation
    test_query = """
        SELECT
            claim_category,
            status,
            COUNT(*) AS total_claims,
            SUM(claim_amount) AS total_amount,
            AVG(claim_amount) AS avg_amount
        FROM claims
        WHERE claim_category = 'Auto'
          AND status = 'Approved'
          AND incident_date >= '2025-01-01'
        GROUP BY claim_category, status;
    """

    # ── Phase 1: Measure WITHOUT Composite Index (Baseline) ──────
    with engine.begin() as conn:
        # Drop composite index if exists
        conn.execute(text("DROP INDEX IF EXISTS idx_clm_perf_cat_stat_date;"))

    # Capture unindexed query plan
    with engine.connect() as conn:
        explain_raw = conn.execute(text(f"EXPLAIN QUERY PLAN {test_query}")).fetchall()
        baseline_plan = " | ".join(
            [
                f"{row[2]} ({row[3]})" if len(row) > 3 else str(row)
                for row in explain_raw
            ]
        )

    # Warm-up run
    with engine.connect() as conn:
        conn.execute(text(test_query)).fetchall()

    baseline_times: list[float] = []
    with engine.connect() as conn:
        for _ in range(iterations):
            t0 = time.perf_counter()
            conn.execute(text(test_query)).fetchall()
            t1 = time.perf_counter()
            baseline_times.append((t1 - t0) * 1000)  # ms

    avg_baseline_ms = sum(baseline_times) / len(baseline_times)

    # ── Phase 2: Measure WITH Composite Covering Index ───────────
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE INDEX idx_clm_perf_cat_stat_date
            ON claims (claim_category, status, incident_date, claim_amount);
        """)
        )

    # Capture indexed query plan
    with engine.connect() as conn:
        explain_indexed = conn.execute(
            text(f"EXPLAIN QUERY PLAN {test_query}")
        ).fetchall()
        indexed_plan = " | ".join(
            [
                f"{row[2]} ({row[3]})" if len(row) > 3 else str(row)
                for row in explain_indexed
            ]
        )

    # Warm-up run
    with engine.connect() as conn:
        conn.execute(text(test_query)).fetchall()

    optimized_times: list[float] = []
    with engine.connect() as conn:
        for _ in range(iterations):
            t0 = time.perf_counter()
            conn.execute(text(test_query)).fetchall()
            t1 = time.perf_counter()
            optimized_times.append((t1 - t0) * 1000)  # ms

    avg_optimized_ms = sum(optimized_times) / len(optimized_times)

    # Compute improvement metrics
    speedup_multiplier = (
        avg_baseline_ms / avg_optimized_ms if avg_optimized_ms > 0 else 1.0
    )
    latency_reduction_pct = (
        ((avg_baseline_ms - avg_optimized_ms) / avg_baseline_ms * 100)
        if avg_baseline_ms > 0
        else 0.0
    )

    report = {
        "iterations": iterations,
        "rows_scanned": 9107,
        "baseline_unindexed": {
            "avg_latency_ms": round(avg_baseline_ms, 3),
            "min_latency_ms": round(min(baseline_times), 3),
            "max_latency_ms": round(max(baseline_times), 3),
            "query_plan": baseline_plan,
        },
        "optimized_covering_index": {
            "avg_latency_ms": round(avg_optimized_ms, 3),
            "min_latency_ms": round(min(optimized_times), 3),
            "max_latency_ms": round(max(optimized_times), 3),
            "query_plan": indexed_plan,
        },
        "performance_gain": {
            "speedup_multiplier": f"{speedup_multiplier:.2f}x",
            "latency_reduction_pct": f"{latency_reduction_pct:.1f}%",
        },
    }

    # Save benchmark report to disk
    report_file = PROJECT_ROOT / "database" / "performance" / "benchmark_results.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    _print_benchmark_card(report)
    return report


def _print_benchmark_card(report: dict[str, Any]) -> None:
    """Prints an executive summary card of SQL performance gains."""
    b = report["baseline_unindexed"]
    o = report["optimized_covering_index"]
    g = report["performance_gain"]

    print("\n" + "=" * 70)
    print("  SQL PERFORMANCE TUNING & QUERY OPTIMIZATION BENCHMARK")
    print("=" * 70)
    print(f"  Rows Evaluated:              {report['rows_scanned']:,} claims")
    print(f"  Test Iterations:             {report['iterations']} runs (averaged)")
    print("-" * 70)
    print("  BASELINE (Without Covering Index):")
    print(f"    Avg Execution Time:        {b['avg_latency_ms']} ms")
    print(
        f"    Latency Range:             {b['min_latency_ms']} ms - {b['max_latency_ms']} ms"
    )
    print(f"    Execution Plan:            {b['query_plan'][:60]}...")
    print("-" * 70)
    print("  OPTIMIZED (With Composite Covering Index):")
    print(f"    Avg Execution Time:        {o['avg_latency_ms']} ms")
    print(
        f"    Latency Range:             {o['min_latency_ms']} ms - {o['max_latency_ms']} ms"
    )
    print(f"    Execution Plan:            {o['query_plan'][:60]}...")
    print("-" * 70)
    print(
        f"  MEASURABLE OUTCOME:          {g['speedup_multiplier']} FASTER ({g['latency_reduction_pct']} Latency Reduction)"
    )
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_benchmark()
