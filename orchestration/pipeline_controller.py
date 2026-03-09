from pathlib import Path
from typing import Any

import yaml
from git import Repo

from ai_engine.prompt_builder import PromptBuilder
from ai_engine.qwen_client import QwenClient
from ai_engine.test_generator import AITestGenerator
from ai_engine.test_refiner import AITestRefiner
from coverage_engine.coverage_evaluator import is_coverage_met
from coverage_engine.jacoco_parser import CoverageSummary, parse_jacoco_xml
from coverage_engine.maven_runner import MavenRunner
from git_integration.branch_manager import create_ai_branch
from git_integration.commit_manager import commit_generated_tests
from git_integration.pr_creator import create_pull_request
from input_handlers.github_cloner import clone_github_repo
from input_handlers.local_repo_loader import load_local_repo
from orchestration.retry_manager import should_retry
from repo_analyzer.dependency_mapper import filter_target_classes
from repo_analyzer.java_parser import JavaClassInfo, extract_java_classes
from repo_analyzer.spring_context_detector import detect_build_system, detect_spring_boot
from test_processor.flaky_test_detector import looks_flaky
from test_processor.test_cleaner import normalize_generated_test
from utils.file_utils import ensure_dir, read_text, write_text
from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineController:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.config = self._load_yaml(root_dir / "config" / "app_config.yaml")
        self.prompt_builder = PromptBuilder(root_dir / "config" / "prompt_templates.yaml")
        qcfg = self.config["qwen"]
        self.qwen = QwenClient(
            api_base=qcfg["api_base"],
            model=qcfg["model"],
            timeout_seconds=qcfg["timeout_seconds"],
            temperature=qcfg["temperature"],
            max_tokens=qcfg["max_tokens"],
        )
        self.generator = AITestGenerator(self.qwen, self.prompt_builder)
        self.refiner = AITestRefiner(self.qwen, self.prompt_builder)
        self.maven = MavenRunner(
            test_cmd=self.config["maven_test_cmd"],
            jacoco_cmd=self.config["maven_jacoco_cmd"],
        )

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def _resolve_repo(self, github_url: str | None, local_path: str | None) -> Path:
        workspace = ensure_dir((self.root_dir / self.config["workspace_dir"]).resolve())
        if github_url:
            return clone_github_repo(github_url, workspace)
        if local_path:
            return load_local_repo(Path(local_path).resolve(), workspace)
        raise ValueError("Either github_url or local_path must be set")

    def _test_path_for_class(self, repo_dir: Path, class_info: JavaClassInfo) -> Path:
        src_path = str(class_info.source_path).replace("\\", "/")
        marker = "/src/main/java/"
        if marker not in src_path:
            return repo_dir / "src" / "test" / "java" / f"{class_info.class_name}Test.java"

        suffix = src_path.split(marker, 1)[1]
        target_suffix = suffix.replace(f"{class_info.class_name}.java", f"{class_info.class_name}Test.java")
        return repo_dir / "src" / "test" / "java" / target_suffix

    def _write_generated_test(self, repo_dir: Path, class_info: JavaClassInfo, test_code: str) -> Path:
        cleaned = normalize_generated_test(test_code)
        test_path = self._test_path_for_class(repo_dir, class_info)
        write_text(test_path, cleaned)
        return test_path

    def _parse_coverage(self, repo_dir: Path) -> CoverageSummary:
        jacoco_xml = repo_dir / "target" / "site" / "jacoco" / "jacoco.xml"
        if not jacoco_xml.exists():
            raise FileNotFoundError("JaCoCo XML not found. Ensure jacoco-maven-plugin is configured.")
        return parse_jacoco_xml(jacoco_xml)

    def run(
        self,
        github_url: str | None = None,
        local_path: str | None = None,
        create_pr: bool = False,
        repo_full_name: str | None = None,
        base_branch: str = "main",
        push_branch: bool = False,
    ) -> dict[str, Any]:
        repo_dir = self._resolve_repo(github_url, local_path)

        if not detect_spring_boot(repo_dir):
            logger.warning("Spring Boot not clearly detected; proceeding anyway")
        if detect_build_system(repo_dir) != "maven":
            raise ValueError("Current version supports Maven projects only")

        branch_name = None
        if github_url:
            branch_name = create_ai_branch(repo_dir)

        java_classes = extract_java_classes(repo_dir)
        target_classes = filter_target_classes(java_classes)
        logger.info("Found %s target classes", len(target_classes))

        generated_paths: list[str] = []
        for cls in target_classes:
            generated = self.generator.generate_for_class(cls)
            if looks_flaky(generated):
                logger.warning("Potential flaky test generated for %s", cls.class_name)
            file_path = self._write_generated_test(repo_dir, cls, generated)
            generated_paths.append(str(file_path))

        # Run test + coverage loop.
        max_rounds = int(self.config["max_retry_rounds"])
        round_idx = 1
        summary = CoverageSummary(0.0, 0.0, [])

        while True:
            test_result = self.maven.run_tests(repo_dir)
            if not test_result.ok:
                # Simple refinement: attempt one global fix by asking LLM with logs.
                logger.warning("Tests failing in round %s; attempting refinement", round_idx)
                for p in generated_paths:
                    pth = Path(p)
                    fixed = self.refiner.fix_test_code(read_text(pth), test_result.stderr[-4000:])
                    write_text(pth, normalize_generated_test(fixed))
                test_result = self.maven.run_tests(repo_dir)
                if not test_result.ok and not should_retry(round_idx, max_rounds):
                    raise RuntimeError(f"Tests failed after retries:\n{test_result.stderr}")

            jacoco_result = self.maven.run_jacoco_report(repo_dir)
            if not jacoco_result.ok:
                raise RuntimeError(f"jacoco:report failed:\n{jacoco_result.stderr}")

            summary = self._parse_coverage(repo_dir)
            if is_coverage_met(
                summary,
                float(self.config["min_line_coverage"]),
                float(self.config["min_branch_coverage"]),
            ):
                break

            if not should_retry(round_idx, max_rounds):
                break

            uncovered = "\n".join(summary.uncovered_hints[:30]) or "No details available"
            logger.info("Coverage below threshold in round %s. Improving targeted tests", round_idx)

            # Improve tests for each class in the current set.
            for cls in target_classes:
                path = self._test_path_for_class(repo_dir, cls)
                existing = read_text(path) if path.exists() else ""
                improved = self.refiner.improve_coverage(
                    class_code=cls.source_code,
                    existing_test_code=existing,
                    uncovered_items=uncovered,
                )
                write_text(path, normalize_generated_test(improved))

            round_idx += 1

        pr_url = None
        if github_url:
            commit_generated_tests(repo_dir)
            if push_branch and branch_name:
                Repo(repo_dir).git.push("-u", "origin", branch_name)
            if create_pr:
                if not repo_full_name:
                    raise ValueError("repo_full_name is required to create PR, e.g. owner/repo")
                if not branch_name:
                    raise ValueError("Branch name unavailable for PR creation")
                pr_url = create_pull_request(
                    repo_full_name=repo_full_name,
                    title="test: AI-generated Spring Boot unit tests",
                    body="Automated by ai-test-generator using Qwen and coverage feedback loop.",
                    head_branch=branch_name,
                    base_branch=base_branch,
                )

        return {
            "repo_dir": str(repo_dir),
            "generated_test_files": generated_paths,
            "line_coverage": summary.line_coverage,
            "branch_coverage": summary.branch_coverage,
            "pr_url": pr_url,
            "branch_name": branch_name,
        }
