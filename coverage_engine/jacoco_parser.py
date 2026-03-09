from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


@dataclass
class CoverageSummary:
    line_coverage: float
    branch_coverage: float
    uncovered_hints: list[str]


def _pct(covered: int, missed: int) -> float:
    total = covered + missed
    if total == 0:
        return 100.0
    return round((covered / total) * 100, 2)


def parse_jacoco_xml(jacoco_xml_path: Path) -> CoverageSummary:
    root = ET.parse(jacoco_xml_path).getroot()

    line_missed, line_covered = 0, 0
    branch_missed, branch_covered = 0, 0
    uncovered_hints: list[str] = []

    for c in root.findall("counter"):
        counter_type = c.attrib.get("type")
        missed = int(c.attrib.get("missed", "0"))
        covered = int(c.attrib.get("covered", "0"))

        if counter_type == "LINE":
            line_missed, line_covered = missed, covered
        if counter_type == "BRANCH":
            branch_missed, branch_covered = missed, covered

    for pkg in root.findall("package"):
        pkg_name = pkg.attrib.get("name", "")
        for cls in pkg.findall("class"):
            cls_name = cls.attrib.get("name", "")
            for counter in cls.findall("counter"):
                if counter.attrib.get("type") == "LINE" and int(counter.attrib.get("missed", "0")) > 0:
                    uncovered_hints.append(f"{pkg_name}/{cls_name} has uncovered lines")

    return CoverageSummary(
        line_coverage=_pct(line_covered, line_missed),
        branch_coverage=_pct(branch_covered, branch_missed),
        uncovered_hints=uncovered_hints,
    )
