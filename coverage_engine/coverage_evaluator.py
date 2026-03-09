from coverage_engine.jacoco_parser import CoverageSummary


def is_coverage_met(summary: CoverageSummary, min_line: float, min_branch: float) -> bool:
    return summary.line_coverage >= min_line and summary.branch_coverage >= min_branch
