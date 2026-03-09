from ai_engine.prompt_builder import PromptBuilder
from ai_engine.qwen_client import QwenClient


class AITestRefiner:
    def __init__(self, qwen_client: QwenClient, prompt_builder: PromptBuilder) -> None:
        self.qwen_client = qwen_client
        self.prompt_builder = prompt_builder

    def fix_test_code(self, test_code: str, error_logs: str) -> str:
        prompt = self.prompt_builder.build_fix_prompt(test_code, error_logs)
        return self.qwen_client.generate(prompt)

    def improve_coverage(self, class_code: str, existing_test_code: str, uncovered_items: str) -> str:
        prompt = self.prompt_builder.build_targeted_prompt(
            class_code=class_code,
            existing_test_code=existing_test_code,
            uncovered_items=uncovered_items,
        )
        return self.qwen_client.generate(prompt)
