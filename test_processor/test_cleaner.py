import re


def normalize_generated_test(test_code: str) -> str:
    # Keep output deterministic and avoid markdown fences from LLM responses.
    cleaned = test_code.strip()
    cleaned = cleaned.replace("```java", "").replace("```", "").strip()
    return cleaned + "\n"


def enforce_expected_class_name(test_code: str, expected_class_name: str) -> str:
    """Force a deterministic class name to avoid duplicate-class compile errors."""
    pattern = re.compile(r"(public\s+class\s+)([A-Za-z_][A-Za-z0-9_]*)")
    updated, count = pattern.subn(rf"\1{expected_class_name}", test_code, count=1)
    if count > 0:
        return updated

    # Fallback for non-public class declarations.
    pattern = re.compile(r"(class\s+)([A-Za-z_][A-Za-z0-9_]*)")
    updated, _ = pattern.subn(rf"\1{expected_class_name}", test_code, count=1)
    return updated
