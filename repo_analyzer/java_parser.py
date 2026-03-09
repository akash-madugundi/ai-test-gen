from dataclasses import dataclass
from pathlib import Path

import javalang

from utils.file_utils import list_files, read_text


@dataclass
class JavaClassInfo:
    class_name: str
    package_name: str
    methods: list[str]
    annotations: list[str]
    source_path: Path
    source_code: str


def extract_java_classes(repo_dir: Path) -> list[JavaClassInfo]:
    java_files = list_files(repo_dir, ["*.java"])
    classes: list[JavaClassInfo] = []

    for file_path in java_files:
        if "src/test" in str(file_path).replace("\\", "/"):
            continue

        content = read_text(file_path)
        try:
            tree = javalang.parse.parse(content)
        except Exception:
            continue

        package_name = tree.package.name if tree.package else ""
        for t in tree.types:
            if not hasattr(t, "name"):
                continue
            methods = [m.name for m in getattr(t, "methods", [])]
            annotations = [a.name for a in getattr(t, "annotations", [])]
            classes.append(
                JavaClassInfo(
                    class_name=t.name,
                    package_name=package_name,
                    methods=methods,
                    annotations=annotations,
                    source_path=file_path,
                    source_code=content,
                )
            )

    return classes
