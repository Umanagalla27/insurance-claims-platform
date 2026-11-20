"""
CLI Entrypoint for Automated BI Snapshot Pipeline (ICIP-027).
Provides enterprise command-line orchestration for scheduled or on-demand
Apache Parquet columnar exports and executive briefing reports.
"""

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from powerbi.snapshot_pipeline import create_bi_snapshot  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bi_snapshot_cli")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEMANTIC_DIR = PROJECT_ROOT / "data" / "semantic_layer"
SNAPSHOTS_ROOT = PROJECT_ROOT / "data" / "snapshots"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Automated Star-Schema BI Snapshot & Columnar Parquet Pipeline (ICIP-027)"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=SEMANTIC_DIR,
        help="Path to conformed semantic layer CSVs",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SNAPSHOTS_ROOT,
        help="Base directory for snapshot storage",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="Custom tag or reference ID for the snapshot",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate snapshot execution without writing files",
    )

    args = parser.parse_args()

    if args.dry_run:
        logger.info(
            "[DRY-RUN] Simulating BI snapshot pipeline from %s to %s",
            args.source_dir,
            args.output_dir,
        )
        return 0

    try:
        manifest = create_bi_snapshot(
            source_dir=args.source_dir,
            snapshots_root=args.output_dir,
            snapshot_tag=args.tag,
        )
        logger.info(
            "BI snapshot '%s' created successfully with %d tables.",
            manifest["snapshot_id"],
            manifest["tables_count"],
        )
        return 0
    except Exception as e:
        logger.error("BI snapshot pipeline failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
