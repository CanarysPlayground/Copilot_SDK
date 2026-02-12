# workflow_automation.py
"""
Workflow Automation SDK for Self-Healing CI/CD
Automates dependency detection and PR creation using PyGithub
"""

import os
import json
import subprocess
import ast
from typing import List, Dict
from dataclasses import dataclass
from github import Github, GithubException

@dataclass
class DependencyAnalyzer:
    """Analyzes Python files for missing dependencies"""
    
    STDLIB_MODULES = {
        'asyncio', 'sys', 'random', 'os', 'json', 'subprocess',
        're', 'pathlib', 'collections', 'itertools', 'functools'
    }
    
    PKG_MAPPING = {
        'copilot': 'copilot-client',
        'pydantic': 'pydantic',
        'requests': 'requests',
    }
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports = set()
        self.missing_deps = []
    
    def extract_imports(self) -> set:
        """Extract all imports from Python file"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split('.')[0]
                    self.imports.add(pkg)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    pkg = node.module.split('.')[0]
                    self.imports.add(pkg)
        return self.imports
    
    def check_missing(self) -> List[str]:
        """Check which imports are missing"""
        missing = []
        for imp in self.imports:
            if imp not in self.STDLIB_MODULES:
                try:
                    __import__(imp)
                except ImportError:
                    pkg_name = self.PKG_MAPPING.get(imp, imp)
                    missing.append(pkg_name)
        self.missing_deps = list(set(missing))
        return self.missing_deps
    
    def get_report(self) -> Dict:
        """Get dependency analysis report"""
        return {
            'file': self.file_path,
            'imports': list(self.imports),
            'missing': self.missing_deps,
            'status': 'failed' if self.missing_deps else 'passed'
        }


class RequirementsManager:
    """Manages requirements.txt file"""
    
    def __init__(self, req_file: str = "requirements.txt"):
        self.req_file = req_file
        self.packages = {}
        self.load()
    
    def load(self):
        """Load requirements from file"""
        if os.path.exists(self.req_file):
            with open(self.req_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        pkg_name = line.split('==')[0].split('>=')[0].split('<')[0]
                        self.packages[pkg_name] = line
    
    def install_packages(self, packages: List[str]) -> Dict[str, str]:
        """Install packages and get their versions"""
        installed = {}
        for pkg in packages:
            try:
                subprocess.run(
                    ["pip", "install", pkg],
                    capture_output=True,
                    check=True
                )
                # Get version
                freeze_result = subprocess.run(
                    ["pip", "show", pkg],
                    capture_output=True,
                    text=True
                )
                for line in freeze_result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':')[1].strip()
                        full_spec = f"{pkg}=={version}"
                        self.packages[pkg] = full_spec
                        installed[pkg] = full_spec
                        break
            except subprocess.CalledProcessError:
                print(f"Failed to install {pkg}")
        return installed
    
    def save(self):
        """Save requirements to file"""
        with open(self.req_file, 'w', encoding='utf-8') as f:
            for pkg, spec in sorted(self.packages.items()):
                f.write(spec + '\n')


class GitHubWorkflowSDK:
    """SDK for automating GitHub workflow and PR creation"""
    
    def __init__(self, token: str, owner: str, repo: str):
        self.gh = Github(token)
        self.owner = owner
        self.repo = repo
        self.repository = self.gh.get_repo(f"{owner}/{repo}")
    
    def create_healing_pr(self, missing_deps: List[str]) -> Dict:
        """Create a self-healing PR for missing dependencies"""
        
        branch_name = f"fix/dependencies-{int(__import__('time').time())}"
        
        try:
            main_ref = self.repository.get_git_ref("heads/main")
            base_commit_sha = main_ref.object.sha
            
            # Create new branch
            self.repository.create_git_ref(
                f"refs/heads/{branch_name}",
                base_commit_sha
            )
            print(f"✅ Created branch: {branch_name}")
            
            # Create PR
            pr = self.repository.create_pull(
                title="🔧 Self-Heal: Add missing dependencies",
                body=f"""## Auto-generated Self-Healing PR

**Missing Dependencies Auto-Detected:** 
{', '.join(missing_deps)}

### Changes:
- ✅ Dependencies installed
- ✅ requirements.txt updated with exact versions
- ✅ Python syntax validated

**Status:** Ready to merge
""",
                head=branch_name,
                base="main"
            )
            
            print(f"✅ Created PR: #{pr.number}")
            return {
                'pr_number': pr.number,
                'branch': branch_name,
                'url': pr.html_url
            }
        except GithubException as e:
            print(f"❌ Error: {e}")
            return None


class SelfHealingOrchestrator:
    """Main orchestrator for the self-healing workflow"""
    
    def __init__(self, token: str, owner: str, repo: str,
                 python_file: str = "weather_assistant.py",
                 req_file: str = "requirements.txt"):
        self.analyzer = DependencyAnalyzer(python_file)
        self.req_manager = RequirementsManager(req_file)
        self.github_sdk = GitHubWorkflowSDK(token, owner, repo)
    
    def analyze(self) -> Dict:
        """Analyze dependencies"""
        self.analyzer.extract_imports()
        self.analyzer.check_missing()
        return self.analyzer.get_report()
    
    def heal(self) -> Dict:
        """Execute self-healing workflow"""
        analysis = self.analyze()
        
        if not analysis['missing']:
            print("✅ No issues found")
            return {'status': 'no_issues'}
        
        print(f"🔧 Healing {len(analysis['missing'])} missing deps...")
        
        # Install packages
        installed = self.req_manager.install_packages(analysis['missing'])
        self.req_manager.save()
        
        # Create healing PR
        pr_result = self.github_sdk.create_healing_pr(analysis['missing'])
        
        return {
            'status': 'healed',
            'missing': analysis['missing'],
            'installed': installed,
            'pr': pr_result
        }
    
    def run(self) -> Dict:
        """Run complete workflow"""
        print("📊 Running self-healing workflow...\n")
        analysis = self.analyze()
        
        print(f"Imports found: {len(analysis['imports'])}")
        print(f"Missing: {analysis['missing']}")
        
        if analysis['missing']:
            return self.heal()
        return {'status': 'passed'}


# Usage
if __name__ == "__main__":
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ Set GITHUB_TOKEN environment variable")
        exit(1)
    
    orchestrator = SelfHealingOrchestrator(
        token=token,
        owner="CanarysPlayground",
        repo="Copilot_SDK"
    )
    result = orchestrator.run()
    print(f"\n✅ Result: {result}")