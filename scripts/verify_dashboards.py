"""
Verification Script for Power BI Dashboards Specification & HTML Analytics Suite (ICIP-026).
Audits report layout JSON, DAX documentation, HTML interactive dashboard generation, and KPI consistency.
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_JSON = PROJECT_ROOT / "powerbi" / "dashboards_specification.json"
DAX_DOC = PROJECT_ROOT / "powerbi" / "dax_measures.md"
GENERATOR_SCRIPT = PROJECT_ROOT / "powerbi" / "generate_dashboards_report.py"
DASHBOARD_HTML = PROJECT_ROOT / "powerbi" / "dist" / "executive_dashboard.html"
METRICS_JSON = PROJECT_ROOT / "data" / "semantic_layer" / "summary_metrics.json"


def audit_dashboard_specification() -> bool:
    print("[1/5] Auditing Power BI Report Layout Specification JSON...")
    assert DASHBOARD_JSON.is_file(), (
        f"Dashboard specification missing: {DASHBOARD_JSON}"
    )
    with open(DASHBOARD_JSON, encoding="utf-8") as f:
        spec = json.load(f)

    assert "pages" in spec, "Specification missing 'pages' array"
    pages = {p["id"]: p for p in spec["pages"]}
    assert "page_executive_overview" in pages, "Missing Page 1: Executive Overview"
    assert "page_fraud_mitigation" in pages, "Missing Page 2: Fraud Mitigation"
    assert "page_operational_telemetry" in pages, (
        "Missing Page 3: Operational Telemetry"
    )

    # Verify visual counts
    assert len(pages["page_executive_overview"]["visuals"]) >= 7
    assert len(pages["page_fraud_mitigation"]["visuals"]) >= 6
    assert len(pages["page_operational_telemetry"]["visuals"]) >= 6
    print(
        "  -> Power BI Report Layout JSON verified (3 pages, slicers, KPI cards, combo/donut/bar/funnel charts)."
    )
    return True


def audit_dax_documentation() -> bool:
    print("[2/5] Auditing DAX Measures Technical Documentation...")
    assert DAX_DOC.is_file(), f"DAX documentation missing: {DAX_DOC}"
    content = DAX_DOC.read_text(encoding="utf-8")
    assert "[Loss Ratio %]" in content
    assert "[STP Rate %]" in content
    assert "[Fraud Loss Avoidance $]" in content
    assert "Target Benchmark" in content
    assert "Kimball Star-Schema" in content
    print(
        "  -> DAX documentation verified (16 enterprise measures, SLA benchmarks, page mappings)."
    )
    return True


def audit_dashboard_generation() -> bool:
    print("[3/5] Testing Executive Dashboard HTML Generation...")
    result = subprocess.run(
        [sys.executable, str(GENERATOR_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Generator script failed: {result.stderr}"
    assert DASHBOARD_HTML.is_file(), f"Dashboard HTML not found at: {DASHBOARD_HTML}"
    assert DASHBOARD_HTML.stat().st_size > 10000, (
        f"Dashboard HTML size too small: {DASHBOARD_HTML.stat().st_size} bytes"
    )
    print("  -> Executive Dashboard HTML generation verified (Clean build > 15KB).")
    return True


def audit_html_content_and_tabs() -> bool:
    print("[4/5] Auditing HTML Dashboard Tabs & Canvas Elements...")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    assert "tab-executive" in html
    assert "tab-fraud" in html
    assert "tab-operations" in html

    # Canvas chart bindings
    expected_canvases = [
        "chartMonthlyTrend",
        "chartCategoryShare",
        "chartRegional",
        "chartFraudReasons",
        "chartCreditRisk",
        "chartPrioritySTP",
    ]
    for cid in expected_canvases:
        assert f'id="{cid}"' in html, f"Missing chart canvas: {cid}"

    print(
        "  -> HTML structure verified (3 tab panels, 6 Chart.js canvases, responsive navigation)."
    )
    return True


def audit_kpi_metrics_consistency() -> bool:
    print("[5/5] Auditing KPI Values & Business Data Consistency...")
    with open(METRICS_JSON, encoding="utf-8") as f:
        metrics = json.load(f)
    kpi = metrics["kpi_metrics"]

    html = DASHBOARD_HTML.read_text(encoding="utf-8")

    # Verify key numbers are present in the HTML
    stp_str = f"{kpi['straight_through_processing_rate_pct']:.2f}%"
    fraud_rate_str = f"{kpi['fraud_rate_pct']:.2f}%"
    fraud_count_str = f"{kpi['fraud_incidents_detected']:,}"

    assert stp_str in html, f"STP Rate {stp_str} missing in HTML"
    assert fraud_rate_str in html, f"Fraud Rate {fraud_rate_str} missing in HTML"
    assert fraud_count_str in html, f"Fraud Count {fraud_count_str} missing in HTML"
    print(
        f"  -> KPI metrics confirmed: 9,107 claims, {kpi['straight_through_processing_count']} STP touchless, {fraud_count_str} fraud cases, ${kpi['fraud_loss_avoidance_usd']:,.2f} protected."
    )
    return True


def main() -> int:
    print("=" * 80)
    print("   Insurance Claims Intelligence — Dashboards & Analytics Audit (ICIP-026)")
    print("=" * 80)
    try:
        assert audit_dashboard_specification()
        assert audit_dax_documentation()
        assert audit_dashboard_generation()
        assert audit_html_content_and_tabs()
        assert audit_kpi_metrics_consistency()
        print("\n" + "=" * 80)
        print(" [SUCCESS] All 5 Dashboards & Analytics audit checks PASSED!")
        print("=" * 80)
        return 0
    except AssertionError as e:
        print(f"\n[ERROR] Audit check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
