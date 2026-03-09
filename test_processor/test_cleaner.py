def normalize_generated_test(test_code: str) -> str:
    # Keep output deterministic and avoid markdown fences from LLM responses.
    cleaned = test_code.strip()
    cleaned = cleaned.replace("```java", "").replace("```", "").strip()
    return cleaned + "\n"
