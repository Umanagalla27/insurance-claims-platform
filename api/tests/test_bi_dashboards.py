"""
Automated Pytest Suite for Power BI Dashboards Specification & Executive Analytics Suite (ICIP-026).
Validates report layout JSON, DAX documentation, interactive HTML generation, and KPI consistency.
"""

import json
from pathlib import Path

from powerbi.generate_dashboards_report import generate_executive_dashboard

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_JSON = PROJECT_ROOT / "powerbi" / "dashboards_specification.json"
DAX_DOC = PROJECT_ROOT / "powerbi" / "dax_measures.md"
METRICS_JSON = PROJECT_ROOT / "data" / "semantic_layer" / "summary_metrics.json"
DASHBOARD_HTML = PROJECT_ROOT / "powerbi" / "dist" / "executive_dashboard.html"


class TestDashboardsSpecification:
    """Validates Power BI Report Layout JSON declarative specification."""

    def test_specification_file_exists(self):
        assert DASHBOARD_JSON.is_file()

    def test_specification_pages_and_slicers(self):
        with open(DASHBOARD_JSON, encoding="utf-8") as f:
            spec = json.load(f)
        assert "pages" in spec
        page_ids = [p["id"] for p in spec["pages"]]
        assert "page_executive_overview" in page_ids
        assert "page_fraud_mitigation" in page_ids
        assert "page_operational_telemetry" in page_ids

        exec_page = next(
            p for p in spec["pages"] if p["id"] == "page_executive_overview"
        )
        slicer_fields = [s["field"] for s in exec_page.get("slicers", [])]
        assert "dim_date.calendar_year" in slicer_fields
        assert "dim_customer.us_region" in slicer_fields

    def test_specification_visuals_declared(self):
        with open(DASHBOARD_JSON, encoding="utf-8") as f:
            spec = json.load(f)
        all_visuals = []
        for p in spec["pages"]:
            all_visuals.extend(p.get("visuals", []))

        types = {v["type"] for v in all_visuals}
        assert "card" in types
        assert "gauge" in types
        assert "donutChart" in types
        assert "treemap" in types
        assert "funnel" in types


class TestDAXDocumentation:
    """Validates DAX measures technical reference guide."""

    def test_dax_documentation_exists(self):
        assert DAX_DOC.is_file()

    def test_dax_documentation_benchmarks(self):
        content = DAX_DOC.read_text(encoding="utf-8")
        assert "Loss Ratio %" in content
        assert "60% - 75%" in content
        assert "STP Rate %" in content
        assert "Fraud Loss Avoidance $" in content
        assert "Kimball Star-Schema" in content


class TestInteractiveDashboardGeneration:
    """Validates generation and content of the HTML executive dashboard."""

    def test_generate_dashboard_html_success(self):
        out_path = generate_executive_dashboard()
        assert out_path.is_file()
        assert out_path.stat().st_size > 10000

    def test_dashboard_html_tabs_and_canvases(self):
        assert DASHBOARD_HTML.is_file()
        html = DASHBOARD_HTML.read_text(encoding="utf-8")

        # Tab containers
        assert "tab-executive" in html
        assert "tab-fraud" in html
        assert "tab-operations" in html

        # Canvas elements
        assert 'id="chartMonthlyTrend"' in html
        assert 'id="chartCategoryShare"' in html
        assert 'id="chartRegional"' in html
        assert 'id="chartFraudReasons"' in html
        assert 'id="chartCreditRisk"' in html
        assert 'id="chartPrioritySTP"' in html

    def test_dashboard_kpi_consistency(self):
        with open(METRICS_JSON, encoding="utf-8") as f:
            metrics = json.load(f)
        kpi = metrics["kpi_metrics"]

        html = DASHBOARD_HTML.read_text(encoding="utf-8")
        assert f"{kpi['straight_through_processing_rate_pct']:.2f}%" in html
        assert f"{kpi['fraud_rate_pct']:.2f}%" in html
        assert f"{kpi['fraud_incidents_detected']:,}" in html
        assert f"{kpi['average_settlement_lag_days']:.1f} Days" in html
