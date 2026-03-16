# AI Test Generator (Qwen + Java)

Automates JUnit test generation for Java repositories (Maven/Gradle) using Qwen, then enforces line and branch coverage goals (>=80%).

## Features

- Input type 1: GitHub URL (`--github-url`)
- Input type 2: Local repository path (`--local-path`)
- Generates tests with Qwen for target classes
- Supports Maven and Gradle Java projects
- Preserves manual tests by generating dedicated `AiGeneratedTest` classes
- Stores execution logs and test cache under `runtime_artifacts/`
- Reuses cached generated tests across reruns to avoid starting from scratch
- Coverage retry loop to improve uncovered areas
- Optional branch commit and PR creation for GitHub repos

## Project Structure

```text
ai-test-generator/
  config/
    app_config.yaml
    prompt_templates.yaml
  input_handlers/
    github_cloner.py
    local_repo_loader.py
  repo_analyzer/
    java_parser.py
    dependency_mapper.py
    spring_context_detector.py
  ai_engine/
    qwen_client.py
    prompt_builder.py
    test_generator.py
    test_refiner.py
  coverage_engine/
    maven_runner.py
    jacoco_parser.py
    coverage_evaluator.py
  test_processor/
    test_cleaner.py
    test_merger.py
    flaky_test_detector.py
  git_integration/
    branch_manager.py
    commit_manager.py
    pr_creator.py
  orchestration/
    pipeline_controller.py
    retry_manager.py
    workflow_manager.py
  utils/
    file_utils.py
    logger.py
    command_executor.py
  output/
    generated_tests/
    reports/
  runtime_artifacts/
  .github/workflows/
    coverage-gate.yml
  main.py
  requirements.txt
```

## Prerequisites

- Python 3.11+
- Java 17/21
- Maven or Gradle
- For PR mode: GitHub token with repo scope
- Qwen API endpoint and auth

## Environment Variables

- `QWEN_API_KEY`: for `BEARER` auth mode
- `AUTH_METHOD`: `BEARER`, `S2B`, or `B2B`
- `AIGW_USER`: required for `S2B` and `B2B`
- `AMTOKEN`: required for `S2B`
- `JWT`: required for `B2B`
- `GITHUB_TOKEN`: required for private clone/push/PR flows
- `GITHUB_BASE_URL`: optional, set only for GitHub Enterprise API base URL

## Setup

```powershell
cd "d:\My Projects\Intern\HSBC\UC5\ai-test-generator"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

### 1) GitHub input (clone, generate tests, optional PR)

```powershell
python main.py --github-url "https://github.com/<owner>/<repo>.git"
```

With push + PR:

```powershell
python main.py --github-url "https://github.com/<owner>/<repo>.git" --push-branch --create-pr --repo-full-name "<owner>/<repo>"
```

### 2) Local input (copy local repo and generate tests)

```powershell
python main.py --local-path "D:\path\to\java-repo"
```

## Notes

- Ensure JaCoCo plugin/tasks are present in target build configuration.
- Generated AI tests are written under copied/cloned repo `src/test/java` with `AiGeneratedTest` suffix.
- If `mvn/gradle test` fails, logs are saved in `runtime_artifacts/<repo>/logs` and auto-fix retries are attempted.
- If JaCoCo XML is missing, the pipeline retries before finalizing instead of crashing immediately.
- Coverage goal defaults are in `config/app_config.yaml`.



https://github.com/robsonagapito/unit-testing-java.git
https://github.com/in28minutes/spring-unit-testing-with-junit-and-mockito.git