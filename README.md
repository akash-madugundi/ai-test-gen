# AI Test Generator (Qwen + Spring Boot)

Automates JUnit test generation for Spring Boot repositories using Qwen, then enforces line and branch coverage goals (>=80%).

## Features

- Input type 1: GitHub URL (`--github-url`)
- Input type 2: Local repository path (`--local-path`)
- Generates tests with Qwen for target classes
- Runs `mvn test` and `jacoco:report`
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
  .github/workflows/
    coverage-gate.yml
  main.py
  requirements.txt
```

## Prerequisites

- Python 3.11+
- Java 17/21
- Maven
- For PR mode: GitHub token with repo scope
- Qwen API endpoint and key

## Environment Variables

- `QWEN_API_KEY`: API key for your org Qwen endpoint
- `GITHUB_TOKEN`: required only for PR creation

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
python main.py --local-path "D:\path\to\spring-boot-repo"
```

## Notes

- Current implementation targets Maven projects.
- Ensure JaCoCo plugin is present in target repository `pom.xml`.
- Generated tests are written under copied/cloned repo `src/test/java`.
- Coverage goal defaults are in `config/app_config.yaml`.
