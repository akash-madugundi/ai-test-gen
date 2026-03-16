from pathlib import Path
import time
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
from repo_analyzer.spring_context_detector import detect_build_system
from test_processor.flaky_test_detector import looks_flaky
from test_processor.test_cleaner import enforce_expected_class_name, normalize_generated_test
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
            user=qcfg.get("user"),
            auth_method=qcfg.get("auth_method", ""),
        )
        self.generator = AITestGenerator(self.qwen, self.prompt_builder)
        self.refiner = AITestRefiner(self.qwen, self.prompt_builder)
        self.maven: MavenRunner | None = None

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def _resolve_repo(self, github_url: str | None, local_path: str | None) -> Path:
        workspace = ensure_dir((self.root_dir / self.config["workspace_dir"]).resolve())
        if github_url:
            return clone_github_repo(github_url, workspace)
        if local_path:
            return load_local_repo(Path(local_path).resolve(), workspace)
        raise ValueError("Either github_url or local_path must be set")

    def _generated_test_class_name(self, class_info: JavaClassInfo) -> str:
        # Dedicated suffix prevents collision with manually written tests.
        return f"{class_info.class_name}AiGeneratedTest"

    def _test_path_for_class(self, repo_dir: Path, class_info: JavaClassInfo) -> Path:
        src_path = str(class_info.source_path).replace("\\", "/")
        marker = "/src/main/java/"
        generated_name = self._generated_test_class_name(class_info)
        if marker not in src_path:
            return repo_dir / "src" / "test" / "java" / f"{generated_name}.java"

        suffix = src_path.split(marker, 1)[1]
        target_suffix = suffix.replace(f"{class_info.class_name}.java", f"{generated_name}.java")
        return repo_dir / "src" / "test" / "java" / target_suffix

    def _artifact_root(self, repo_dir: Path) -> Path:
        artifacts_dir = self.config.get("runtime_artifacts_dir", "./runtime_artifacts")
        return ensure_dir((self.root_dir / artifacts_dir / repo_dir.name).resolve())

    def _artifact_test_cache_path(self, repo_dir: Path, class_info: JavaClassInfo) -> Path:
        package_path = class_info.package_name.replace(".", "/") if class_info.package_name else "default"
        return self._artifact_root(repo_dir) / "tests_cache" / package_path / f"{self._generated_test_class_name(class_info)}.java"

    def _write_log(self, repo_dir: Path, filename: str, content: str) -> Path:
        log_path = self._artifact_root(repo_dir) / "logs" / filename
        write_text(log_path, content)
        return log_path

    def _write_generated_test(self, repo_dir: Path, class_info: JavaClassInfo, test_code: str) -> Path:
        expected_class_name = self._generated_test_class_name(class_info)
        cleaned = normalize_generated_test(test_code)
        cleaned = enforce_expected_class_name(cleaned, expected_class_name)
        test_path = self._test_path_for_class(repo_dir, class_info)
        write_text(test_path, cleaned)
        write_text(self._artifact_test_cache_path(repo_dir, class_info), cleaned)
        return test_path

    def _parse_coverage(self, repo_dir: Path, build_system: str) -> CoverageSummary | None:
        candidates: list[Path] = []
        if build_system == "maven":
            candidates.append(repo_dir / "target" / "site" / "jacoco" / "jacoco.xml")
        if build_system == "gradle":
            candidates.append(repo_dir / "build" / "reports" / "jacoco" / "test" / "jacocoTestReport.xml")
            candidates.append(repo_dir / "build" / "reports" / "jacoco" / "test" / "jacocoTestReport" / "jacocoTestReport.xml")

        for jacoco_xml in candidates:
            if jacoco_xml.exists():
                return parse_jacoco_xml(jacoco_xml)
        return None

    def run(
        self,
        github_url: str | None = None,
        local_path: str | None = None,
        create_pr: bool = False,
        repo_full_name: str | None = None,
        base_branch: str = "main",
        push_branch: bool = False,
    ) -> dict[str, Any]:
        start_ts = time.perf_counter()
        repo_dir = self._resolve_repo(github_url, local_path)

        build_system = detect_build_system(repo_dir)
        if build_system == "maven":
            self.maven = MavenRunner(
                test_cmd=self.config["maven_test_cmd"],
                jacoco_cmd=self.config["maven_jacoco_cmd"],
            )
        elif build_system == "gradle":
            self.maven = MavenRunner(
                test_cmd=self.config.get("gradle_test_cmd", "gradle -q test"),
                jacoco_cmd=self.config.get("gradle_jacoco_cmd", "gradle -q jacocoTestReport"),
            )
        else:
            raise ValueError("Only Java Maven/Gradle projects are supported")

        branch_name = None
        if github_url:
            branch_name = create_ai_branch(repo_dir)

        java_classes = extract_java_classes(repo_dir)
        target_classes = filter_target_classes(java_classes)
        logger.info("Found %s target classes", len(target_classes))

        generated_paths: list[str] = []
        for cls in target_classes:
            cache_path = self._artifact_test_cache_path(repo_dir, cls)
            if cache_path.exists():
                generated = read_text(cache_path)
                logger.info("Using cached generated test for %s", cls.class_name)
            else:
                generated = self.generator.generate_for_class(cls)
            if looks_flaky(generated):
                logger.warning("Potential flaky test generated for %s", cls.class_name)
            file_path = self._write_generated_test(repo_dir, cls, generated)
            generated_paths.append(str(file_path))

        # Run test + coverage loop.
        max_rounds = int(self.config["max_retry_rounds"])
        test_fix_attempts = int(self.config.get("test_fix_attempts", 2))
        round_idx = 1
        summary = CoverageSummary(0.0, 0.0, [])

        while True:
            test_result = self.maven.run_tests(repo_dir)
            self._write_log(
                repo_dir,
                f"round-{round_idx}-mvn-test.log",
                (test_result.stdout or "") + "\n" + (test_result.stderr or ""),
            )
            if not test_result.ok:
                logger.warning("Tests failing in round %s; attempting refinement", round_idx)
                for fix_attempt in range(1, test_fix_attempts + 1):
                    for p in generated_paths:
                        pth = Path(p)
                        fixed = self.refiner.fix_test_code(read_text(pth), test_result.stderr[-5000:])
                        cls_name = pth.stem
                        fixed = enforce_expected_class_name(normalize_generated_test(fixed), cls_name)
                        write_text(pth, fixed)
                    test_result = self.maven.run_tests(repo_dir)
                    self._write_log(
                        repo_dir,
                        f"round-{round_idx}-mvn-test-fix-{fix_attempt}.log",
                        (test_result.stdout or "") + "\n" + (test_result.stderr or ""),
                    )
                    if test_result.ok:
                        break

                if not test_result.ok:
                    if should_retry(round_idx, max_rounds):
                        round_idx += 1
                        continue
                    raise RuntimeError(
                        "Tests still failing after retries. Check runtime_artifacts logs under this repository run."
                    )

            jacoco_result = self.maven.run_jacoco_report(repo_dir)
            self._write_log(
                repo_dir,
                f"round-{round_idx}-jacoco.log",
                (jacoco_result.stdout or "") + "\n" + (jacoco_result.stderr or ""),
            )
            if not jacoco_result.ok:
                logger.warning("jacoco report command failed in round %s", round_idx)
                if should_retry(round_idx, max_rounds):
                    round_idx += 1
                    continue
                break

            summary_or_none = self._parse_coverage(repo_dir, build_system)
            if summary_or_none is None:
                logger.warning("JaCoCo XML not found after tests. Retrying before finalizing.")
                if should_retry(round_idx, max_rounds):
                    round_idx += 1
                    continue
                break
            summary = summary_or_none
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
                improved = enforce_expected_class_name(
                    normalize_generated_test(improved),
                    self._generated_test_class_name(cls),
                )
                write_text(path, improved)
                write_text(self._artifact_test_cache_path(repo_dir, cls), improved)

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
                    title="test: AI-generated Java unit tests",
                    body="Automated by ai-test-generator using Qwen and coverage feedback loop.",
                    head_branch=branch_name,
                    base_branch=base_branch,
                )

        elapsed_seconds = round(time.perf_counter() - start_ts, 2)

        return {
            "repo_dir": str(repo_dir),
            "generated_test_files": generated_paths,
            "line_coverage": summary.line_coverage,
            "branch_coverage": summary.branch_coverage,
            "pr_url": pr_url,
            "branch_name": branch_name,
            "build_system": build_system,
            "elapsed_seconds": elapsed_seconds,
        }
