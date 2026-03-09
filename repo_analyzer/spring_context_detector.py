from pathlib import Path

from utils.file_utils import read_text


def detect_build_system(repo_dir: Path) -> str:
    if (repo_dir / "pom.xml").exists():
        return "maven"
    if (repo_dir / "build.gradle").exists() or (repo_dir / "build.gradle.kts").exists():
        return "gradle"
    return "unknown"


def detect_spring_boot(repo_dir: Path) -> bool:
    pom = repo_dir / "pom.xml"
    if pom.exists():
        return "spring-boot" in read_text(pom)

    gradle = repo_dir / "build.gradle"
    if gradle.exists():
        return "spring-boot" in read_text(gradle)

    return False
