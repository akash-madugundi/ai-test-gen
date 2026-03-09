from pathlib import Path

from utils.file_utils import write_text


def write_test_file(test_output_dir: Path, class_name: str, test_code: str) -> Path:
    test_file = test_output_dir / f"{class_name}Test.java"
    write_text(test_file, test_code)
    return test_file
