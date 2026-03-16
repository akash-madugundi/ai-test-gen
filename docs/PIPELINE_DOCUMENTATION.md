# AI Test Generator Documentation

## 1. Purpose

This platform automates Java unit test generation using Qwen and pushes coverage toward organizational thresholds (line >= 80%, branch >= 80%) with an iterative feedback loop.

It supports two input modes:
- GitHub repository URL
- Local Java repository path

It supports two Java build ecosystems:
- Maven
- Gradle

## 2. End-to-End Pipeline Flow

```mermaid
flowchart TD
  A[Input: --github-url or --local-path] --> B[Repository Setup]
  B --> C[Build System Detection Maven/Gradle]
  C --> D[Java Class Analysis]
  D --> E[Test Generation via Qwen]
  E --> F[Write AI test files with AiGeneratedTest suffix]
  F --> G[Run test command]
  G -->|Pass| H[Run JaCoCo report command]
  G -->|Fail| I[Test Fix Retry Loop]
  I --> G
  H --> J{JaCoCo XML found?}
  J -->|No| K[Retry round]
  J -->|Yes| L[Parse Coverage]
  L --> M{Line & Branch >= threshold?}
  M -->|No| N[Targeted test refinement]
  N --> G
  M -->|Yes| O[Commit / Push / Create PR (optional)]
```

## 3. Main Pipeline Components

### 3.1 Entry Point
- CLI command starts execution and prints build system, coverage, and elapsed time.
- File: `main.py`

### 3.2 Orchestration Brain
- Coordinates all phases: setup, generation, execution, retries, coverage checks, and GitHub integration.
- Caches generated tests and logs all rounds for traceability.
- File: `orchestration/pipeline_controller.py`

### 3.3 Input Handlers
- GitHub mode: clone repo to workspace.
- Local mode: copy repo safely while ignoring problematic folders (`.git`, `.idea`, `target`, etc.).
- Files:
  - `input_handlers/github_cloner.py`
  - `input_handlers/local_repo_loader.py`

### 3.4 Java Analyzer
- Parses Java classes and methods.
- Selects candidate classes for test generation.
- Files:
  - `repo_analyzer/java_parser.py`
  - `repo_analyzer/dependency_mapper.py`

### 3.5 AI Engine (Qwen)
- Builds prompts for initial generation and targeted refinement.
- Handles gateway authentication modes and network/transient retries.
- Files:
  - `ai_engine/qwen_client.py`
  - `ai_engine/prompt_builder.py`
  - `ai_engine/test_generator.py`
  - `ai_engine/test_refiner.py`

### 3.6 Test Processing
- Normalizes LLM output.
- Enforces deterministic class names to avoid duplicate-class compile errors.
- Uses dedicated suffix (`AiGeneratedTest`) so existing manual tests are not overwritten.
- File: `test_processor/test_cleaner.py`

### 3.7 Coverage Engine
- Executes tests and coverage commands.
- Parses JaCoCo XML into line/branch metrics.
- Files:
  - `coverage_engine/maven_runner.py`
  - `coverage_engine/jacoco_parser.py`
  - `coverage_engine/coverage_evaluator.py`

### 3.8 Git Integration
- Creates AI branch, commits generated tests, pushes branch, and opens PR.
- Supports GitHub.com and GitHub Enterprise APIs.
- Files:
  - `git_integration/branch_manager.py`
  - `git_integration/commit_manager.py`
  - `git_integration/pr_creator.py`

## 4. Retry Mechanism (Detailed)

The pipeline has layered retries to avoid failing too early:

1. **Qwen API retries** (`ai_engine/qwen_client.py`)
- Retries transient statuses: 429, 502, 503, 504
- Retries on timeout and connection errors
- Exponential backoff + jitter
- Supports auth modes:
  - `BEARER` (`QWEN_API_KEY`)
  - `S2B` (`AIGW_USER` + `AMTOKEN`)
  - `B2B` (`AIGW_USER` + `JWT`)

2. **Test fix retries** (`orchestration/pipeline_controller.py`)
- If `mvn/gradle test` fails, test logs are saved under runtime artifacts.
- Failed generated test files are sent back for AI-assisted correction.
- Retries this fix cycle up to `test_fix_attempts` per round.

3. **Round retries** (`orchestration/pipeline_controller.py`)
- Entire round can retry up to `max_retry_rounds` when:
  - tests still fail,
  - JaCoCo command fails,
  - JaCoCo XML is missing,
  - coverage is below threshold.

4. **Coverage refinement retries**
- If coverage is below target, uncovered hints are fed back to Qwen for targeted tests.
- Refined tests are saved and next round is executed.

## 5. Handling Pre-Existing Manual Tests

To avoid conflicts with manually authored tests:
- Generated tests are created as separate classes with suffix `AiGeneratedTest`.
- Existing manual test files are not overwritten.
- Deterministic class-name enforcement prevents duplicate class names inside generated files.

## 6. Runtime Artifacts for Auditability

Each run stores execution evidence under:
- `runtime_artifacts/<repo-name>/logs`
- `runtime_artifacts/<repo-name>/tests_cache`

Benefits:
- Faster reruns (cache reuse)
- Root-cause debugging from logs
- Better demo story for stakeholders

## 7. Config Knobs You Can Explain to Leadership

From `config/app_config.yaml`:
- `min_line_coverage`, `min_branch_coverage`: quality gates
- `max_retry_rounds`: total robustness budget
- `test_fix_attempts`: per-round recovery budget
- `maven_*` / `gradle_*`: execution commands
- `qwen.*`: model/auth/timeout tuning
- `runtime_artifacts_dir`: traceability path

## 8. CI/CD and Governance Story

Suggested governance model:
- Run generator in feature branch (`ai-test-generation/<timestamp>`)
- Open PR automatically
- Enforce coverage gate in CI (`>=80%` line and branch)
- Human reviewer approves AI-generated tests

This balances automation speed with engineering controls.

## 9. Manager-Ready Pitch (Short)

Use this 30-second summary:

> We built a resilient AI-driven Java test pipeline that generates tests, auto-fixes failing AI tests, iteratively improves coverage with JaCoCo feedback, and integrates into GitHub PR workflows. It supports both Maven and Gradle, preserves existing manual tests, and logs every retry round for full auditability. This reduces manual effort while maintaining coverage quality gates and review governance.

## 10. Runbook (Operator)

1. Configure `.env` and `config/app_config.yaml`.
2. Run:
   - `python main.py --github-url <repo-url>`
   - or `python main.py --local-path <path>`
3. Inspect output summary (coverage + elapsed time).
4. If failures occur, inspect logs in `runtime_artifacts/<repo>/logs`.
5. For GitHub flow, run with `--push-branch --create-pr --repo-full-name <owner/repo>`.
