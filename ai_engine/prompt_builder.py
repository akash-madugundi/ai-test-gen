from pathlib import Path

import yaml


class PromptBuilder:
    def __init__(self, template_file: Path) -> None:
        self.templates = yaml.safe_load(template_file.read_text(encoding="utf-8"))

    def build_base_test_prompt(self, class_code: str) -> str:
        return self.templates["base_test_generation"].format(class_code=class_code)

    def build_targeted_prompt(self, class_code: str, existing_test_code: str, uncovered_items: str) -> str:
        return self.templates["targeted_coverage_improvement"].format(
            class_code=class_code,
            existing_test_code=existing_test_code,
            uncovered_items=uncovered_items,
        )

    def build_fix_prompt(self, test_code: str, error_logs: str) -> str:
        return self.templates["fix_compilation_errors"].format(
            test_code=test_code,
            error_logs=error_logs,
        )
