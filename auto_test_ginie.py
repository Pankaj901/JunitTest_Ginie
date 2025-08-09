#!/usr/bin/env python3
"""
JunitTest_Ginie - Automated JUnit Test Generator for Java Projects (Windows version)
- Clones target Java repo from GitHub
- Generates JUnit tests using Diffblue Cover CLI
- Builds & tests with Maven
- Checks coverage via JaCoCo
- Retries if below threshold
- Commits & pushes tests to a new branch
- Creates a Pull Request on GitHub
"""

import os
import subprocess
import sys
from github import Github  # pip install PyGithub
import tempfile
import time

# ======== CONFIGURATION ========
# you can also use env variable for this
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"  # Personal Access Token with repo permissions
REPO_URL = "https://github.com/your-username/your-java-repo.git"
BRANCH_NAME = "feature/auto-generated-tests"
COVERAGE_THRESHOLD = 95  # Minimum required % coverage
MAX_RETRIES = 3  # Number of retries if coverage < threshold
DIFFBLUE_CLI_PATH = r"C:\path\to\diffblue.exe"  # Path to Diffblue CLI executable

# ======== UTILITY FUNCTIONS ========

def run_cmd(cmd, cwd=None, check=True):
    """Run a shell command and print output in real-time."""
    print(f"[RUN] {cmd}")
    result = subprocess.run(
        cmd, cwd=cwd, shell=True, text=True, capture_output=True
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result

# ======== MAIN TASKS ========

def clone_repo():
    """Clone the target repository to a temporary directory."""
    tmp_dir = tempfile.mkdtemp()
    repo_dir = os.path.join(tmp_dir, "repo")
    run_cmd(f'git clone "{REPO_URL}" "{repo_dir}"')
    return repo_dir

def generate_tests_diffblue(repo_dir):
    """Generate JUnit tests using Diffblue Cover CLI."""
    src_path = os.path.join("src", "main", "java")
    test_path = os.path.join("src", "test", "java")
    run_cmd(
        f'"{DIFFBLUE_CLI_PATH}" cover create --src "{src_path}" --test "{test_path}" --overwrite',
        cwd=repo_dir
    )

def compile_and_test(repo_dir):
    """Build project and run tests via Maven."""
    run_cmd("mvn clean test", cwd=repo_dir)

def check_coverage(repo_dir):
    """Run JaCoCo coverage and return coverage percentage."""
    run_cmd("mvn jacoco:prepare-agent test jacoco:report", cwd=repo_dir)
    report_file = os.path.join(repo_dir, "target", "site", "jacoco", "jacoco.csv")
    if not os.path.exists(report_file):
        print("Coverage report not found!")
        return 0
    total_missed, total_covered = 0, 0
    with open(report_file) as f:
        next(f)  # Skip header
        for line in f:
            cols = line.strip().split(',')
            if len(cols) >= 5:
                try:
                    missed = int(cols[3])
                    covered = int(cols[4])
                    total_missed += missed
                    total_covered += covered
                except ValueError:
                    continue
    coverage_pct = (
        (total_covered / (total_covered + total_missed)) * 100
        if (total_covered + total_missed) > 0 else 0
    )
    print(f"Coverage: {coverage_pct:.2f}%")
    return coverage_pct

def commit_and_push(repo_dir):
    """Commit generated tests and push branch."""
    run_cmd(f'git checkout -b {BRANCH_NAME}', cwd=repo_dir)
    run_cmd('git add src/test/java', cwd=repo_dir)
    run_cmd('git commit -m "Automated JUnit test generation with Diffblue"', cwd=repo_dir)
    run_cmd(f'git push --set-upstream origin {BRANCH_NAME}', cwd=repo_dir)

def create_pull_request():
    """Create a GitHub pull request for the generated tests."""
    g = Github(GITHUB_TOKEN)
    repo_name = REPO_URL.split("github.com/")[-1].replace(".git", "")
    repo = g.get_repo(repo_name)
    pr = repo.create_pull(
        title="Automated JUnit Tests (Diffblue)",
        body=f"Generated tests with >= {COVERAGE_THRESHOLD}% coverage using Diffblue",
        head=BRANCH_NAME,
        base="main"
    )
    print(f"Pull Request created: {pr.html_url}")

# ======== MAIN WORKFLOW ========

def main():
    repo_dir = clone_repo()

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"=== Test Generation Attempt {attempt} ===")
        generate_tests_diffblue(repo_dir)
        compile_and_test(repo_dir)
        coverage = check_coverage(repo_dir)

        if coverage >= COVERAGE_THRESHOLD:
            print(f"✅ Coverage threshold met: {coverage:.2f}%")
            break
        elif attempt < MAX_RETRIES:
            print(f"⚠ Coverage {coverage:.2f}% below {COVERAGE_THRESHOLD}%. Retrying...")
            time.sleep(2)
        else:
            print(f"❌ Max retries reached. Coverage still below threshold ({coverage:.2f}%).")

    commit_and_push(repo_dir)
    create_pull_request()

if __name__ == "__main__":
    main()
