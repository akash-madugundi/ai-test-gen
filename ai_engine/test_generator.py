from ai_engine.prompt_builder import PromptBuilder
from ai_engine.qwen_client import QwenClient
from repo_analyzer.java_parser import JavaClassInfo


class AITestGenerator:
    def __init__(self, qwen_client: QwenClient, prompt_builder: PromptBuilder) -> None:
        self.qwen_client = qwen_client
        self.prompt_builder = prompt_builder

    def generate_for_class(self, class_info: JavaClassInfo) -> str:
        prompt = self.prompt_builder.build_base_test_prompt(class_info.source_code)
        return self.qwen_client.generate(prompt)
