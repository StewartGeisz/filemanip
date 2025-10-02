#!/usr/bin/env python3
"""
existing_projects_to_github.py

Converts existing project folders into Git repositories and pushes them to GitHub.
Does NOT move files - works with projects in their current locations.

Author: Stewart Geisz
GitHub: StewartGeisz
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import re


class ExistingProjectsManager:
    def __init__(self, github_username: str = "StewartGeisz"):
        self.github_username = github_username
        self.supported_code_extensions = {
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go',
            '.rs', '.swift', '.kt', '.scala', '.r', '.m', '.pl', '.sh', '.sql', 
            '.html', '.css', '.xml', '.json', '.yaml', '.yml', '.md', '.txt', '.ipynb'
        }
        
    def check_git_and_gh(self) -> tuple[bool, bool]:
        """Check if Git and GitHub CLI are available"""
        git_available = False
        gh_available = False
        
        try:
            subprocess.run(['git', '--version'], capture_output=True, check=True)
            git_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
            
        try:
            subprocess.run(['gh', '--version'], capture_output=True, check=True)
            gh_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
            
        return git_available, gh_available

    def detect_projects_in_directory(self, directory_path: str) -> List[Dict[str, str]]:
        """Detect project folders in the given directory"""
        if not os.path.exists(directory_path):
            print(f"❌ Directory not found: {directory_path}")
            return []
            
        projects = []
        print(f"🔍 Scanning for projects in: {directory_path}")
        
        # Check if the directory itself is a project
        if self.is_project_directory(directory_path):
            project_name = os.path.basename(directory_path)
            projects.append({
                'name': project_name,
                'path': directory_path,
                'description': f"Project: {project_name}"
            })
        
        # Check subdirectories
        try:
            for item in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    if self.is_project_directory(item_path):
                        projects.append({
                            'name': item,
                            'path': item_path,
                            'description': self.get_project_description(item_path, item)
                        })
        except PermissionError:
            print(f"⚠️ Permission denied accessing: {directory_path}")
            
        return projects

    def is_project_directory(self, directory_path: str) -> bool:
        """Determine if a directory contains a project worth putting on GitHub"""
        if not os.path.isdir(directory_path):
            return False
            
        # Skip common non-project directories
        dir_name = os.path.basename(directory_path).lower()
        if dir_name in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 
                       'env', '.pytest_cache', 'dist', 'build', 'target', 
                       '.idea', '.vscode', 'bin', 'obj'}:
            return False
            
        # Count code files
        code_files = 0
        total_files = 0
        
        try:
            for root, dirs, files in os.walk(directory_path):
                # Skip nested package directories
                dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', 
                          '.venv', 'venv', 'env', '.pytest_cache', 'dist', 'build'}]
                
                for file in files:
                    if not file.startswith('.'):
                        total_files += 1
                        file_ext = os.path.splitext(file)[1].lower()
                        if file_ext in self.supported_code_extensions:
                            code_files += 1
                            
                # Don't go too deep for performance
                if len(root.split(os.sep)) - len(directory_path.split(os.sep)) > 3:
                    dirs.clear()
                    
        except (PermissionError, OSError):
            return False
            
        # Project criteria: at least 1 code file or 3+ files total
        return code_files >= 1 or total_files >= 3

    def get_project_description(self, project_path: str, project_name: str) -> str:
        """Generate a description for the project"""
        # Check for existing README
        for readme_name in ['README.md', 'README.txt', 'readme.md', 'README']:
            readme_path = os.path.join(project_path, readme_name)
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()[:500]
                        # Extract first meaningful line
                        lines = content.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith('#') and len(line) > 10:
                                return line[:100] + "..." if len(line) > 100 else line
                except Exception:
                    pass
        
        # Analyze file types to generate description
        languages = set()
        special_files = set()
        
        try:
            for file in os.listdir(project_path):
                if os.path.isfile(os.path.join(project_path, file)):
                    file_lower = file.lower()
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    # Detect languages
                    lang_map = {
                        '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
                        '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.cs': 'C#',
                        '.ipynb': 'Jupyter Notebook', '.r': 'R', '.sql': 'SQL',
                        '.html': 'Web', '.css': 'Web', '.php': 'PHP'
                    }
                    if file_ext in lang_map:
                        languages.add(lang_map[file_ext])
                    
                    # Detect special project types
                    if file_lower in {'package.json', 'requirements.txt', 'pom.xml', 
                                    'cargo.toml', 'makefile', 'dockerfile'}:
                        special_files.add(file_lower)
        except Exception:
            pass
        
        # Generate description based on analysis
        if languages:
            main_lang = sorted(languages)[0]  # Pick first alphabetically
            if len(languages) == 1:
                desc = f"{main_lang} project"
            else:
                desc = f"Multi-language project ({', '.join(sorted(languages))})"
        else:
            desc = "Code project"
            
        # Add special context
        if 'requirements.txt' in special_files:
            desc += " with Python dependencies"
        elif 'package.json' in special_files:
            desc += " with Node.js dependencies"
        elif any(f in special_files for f in ['makefile', 'dockerfile']):
            desc += " with build configuration"
            
        return f"{desc}: {project_name}"

    def generate_gitignore_for_project(self, project_path: str) -> str:
        """Generate appropriate .gitignore based on files in project"""
        gitignores = []
        
        # Detect languages/frameworks in project
        has_python = False
        has_js = False
        has_java = False
        has_web = False
        
        try:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in ['.py', '.ipynb']:
                        has_python = True
                    elif ext in ['.js', '.ts', '.json'] or file == 'package.json':
                        has_js = True
                    elif ext == '.java' or file == 'pom.xml':
                        has_java = True
                    elif ext in ['.html', '.css']:
                        has_web = True
                break  # Only check top level for performance
        except Exception:
            pass
        
        # Base gitignore
        gitignore = """# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Editor files
*.swp
*.swo
*~
.vscode/
.idea/

# Logs
*.log

# Environment variables
.env
.env.local
.env.*.local
"""

        if has_python:
            gitignore += """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
.pytest_cache/
.coverage
htmlcov/
.tox/
.venv/
venv/
env/
ENV/

# Jupyter Notebook
.ipynb_checkpoints
"""

        if has_js:
            gitignore += """
# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.eslintcache
dist/
build/
"""

        if has_java:
            gitignore += """
# Java
*.class
*.jar
*.war
*.ear
target/
.gradle/
build/
"""

        return gitignore

    def generate_readme_for_project(self, project_name: str, project_path: str, description: str) -> str:
        """Generate README.md for existing project"""
        
        # Check what files exist
        files_info = []
        main_files = []
        
        try:
            for file in sorted(os.listdir(project_path)):
                if os.path.isfile(os.path.join(project_path, file)) and not file.startswith('.'):
                    files_info.append(file)
                    # Identify likely main files
                    file_lower = file.lower()
                    if file_lower in ['main.py', 'index.js', 'app.py', 'server.js', 
                                    'main.java', 'index.html', 'run.py']:
                        main_files.append(file)
        except Exception:
            pass
        
        readme = f"""# {project_name.replace('_', ' ').replace('-', ' ').title()}

## Description
{description}

## Files
"""
        
        if files_info:
            for file in files_info[:10]:  # Limit to first 10 files
                ext = os.path.splitext(file)[1].lower()
                if ext in {'.py', '.js', '.java', '.cpp', '.c', '.html', '.css'}:
                    readme += f"- `{file}` - Source code\n"
                elif ext in {'.md', '.txt'}:
                    readme += f"- `{file}` - Documentation\n"  
                elif ext in {'.json', '.yaml', '.yml', '.xml'}:
                    readme += f"- `{file}` - Configuration\n"
                else:
                    readme += f"- `{file}`\n"
            
            if len(files_info) > 10:
                readme += f"- ... and {len(files_info) - 10} more files\n"
        
        readme += f"""
## Getting Started

"""
        
        if main_files:
            readme += f"### Running the Project\n"
            for main_file in main_files:
                ext = os.path.splitext(main_file)[1].lower()
                if ext == '.py':
                    readme += f"```bash\npython {main_file}\n```\n"
                elif ext == '.js':
                    readme += f"```bash\nnode {main_file}\n```\n"
                elif ext == '.java':
                    readme += f"```bash\njavac {main_file}\njava {os.path.splitext(main_file)[0]}\n```\n"
                elif ext == '.html':
                    readme += f"Open `{main_file}` in your web browser\n"
        
        readme += f"""
### Prerequisites
- Appropriate runtime for the project files
- Git for version control

## Author
**{self.github_username}**
- GitHub: [@{self.github_username}](https://github.com/{self.github_username})

---
*Project uploaded using existing-projects-to-github tool*
"""
        
        return readme

    def setup_git_repo(self, project_path: str, project_name: str, description: str) -> bool:
        """Set up Git repository in existing project directory"""
        original_dir = os.getcwd()
        
        try:
            os.chdir(project_path)
            
            # Check if already a git repo
            if os.path.exists('.git'):
                print(f"    ⚠️ Already a Git repository, skipping git init")
            else:
                # Initialize git repo
                subprocess.run(['git', 'init'], check=True, capture_output=True)
                print(f"    ✅ Git repository initialized")
            
            # Create .gitignore if it doesn't exist
            if not os.path.exists('.gitignore'):
                gitignore_content = self.generate_gitignore_for_project(project_path)
                with open('.gitignore', 'w') as f:
                    f.write(gitignore_content)
                print(f"    ✅ .gitignore created")
            else:
                print(f"    ℹ️ .gitignore already exists")
            
            # Create README.md if it doesn't exist
            if not any(os.path.exists(f) for f in ['README.md', 'README.txt', 'readme.md']):
                readme_content = self.generate_readme_for_project(project_name, project_path, description)
                with open('README.md', 'w') as f:
                    f.write(readme_content)
                print(f"    ✅ README.md created")
            else:
                print(f"    ℹ️ README file already exists")
            
            # Add and commit files
            subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
            
            # Check if there are any changes to commit
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True)
            
            if result.stdout.strip():
                subprocess.run(['git', 'commit', '-m', 'Initial commit: Add project files'], 
                             check=True, capture_output=True)
                print(f"    ✅ Initial commit created")
            else:
                print(f"    ℹ️ No changes to commit")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"    ❌ Git operation failed: {e}")
            return False
        except Exception as e:
            print(f"    ❌ Error setting up git repo: {e}")
            return False
        finally:
            os.chdir(original_dir)

    def create_github_repo_and_push(self, project_path: str, project_name: str, description: str) -> bool:
        """Create GitHub repository and push existing project"""
        original_dir = os.getcwd()
        
        try:
            os.chdir(project_path)
            
            # Create GitHub repository
            cmd = ['gh', 'repo', 'create', project_name, '--public', 
                   '--description', description[:100]]  # GitHub has description limits
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"    ✅ GitHub repository created")
            else:
                if "already exists" in result.stderr.lower():
                    print(f"    ℹ️ GitHub repository already exists")
                else:
                    print(f"    ❌ Failed to create GitHub repo: {result.stderr}")
                    return False
            
            # Set up remote and push
            try:
                # Check if remote already exists
                subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                             check=True, capture_output=True)
                print(f"    ℹ️ Remote 'origin' already exists")
            except subprocess.CalledProcessError:
                # Add remote
                remote_url = f"https://github.com/{self.github_username}/{project_name}.git"
                subprocess.run(['git', 'remote', 'add', 'origin', remote_url], 
                             check=True, capture_output=True)
                print(f"    ✅ Remote origin added")
            
            # Set main as default branch and push
            subprocess.run(['git', 'branch', '-M', 'main'], 
                         check=True, capture_output=True)
            subprocess.run(['git', 'push', '-u', 'origin', 'main'], 
                         check=True, capture_output=True)
            print(f"    ✅ Pushed to GitHub: https://github.com/{self.github_username}/{project_name}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"    ❌ GitHub operation failed: {e}")
            return False
        except Exception as e:
            print(f"    ❌ Error with GitHub setup: {e}")
            return False
        finally:
            os.chdir(original_dir)

    def process_existing_projects(self, directory_path: str, create_github_repos: bool = True) -> List[str]:
        """Main method to process existing projects"""
        print("🚀 Processing Existing Projects for GitHub")
        print(f"📂 Scanning Directory: {directory_path}")
        
        # Check prerequisites
        git_available, gh_available = self.check_git_and_gh()
        
        if not git_available:
            print("❌ Git is not available. Please install Git first.")
            return []
        
        if create_github_repos and not gh_available:
            print("⚠️ GitHub CLI not available. Will set up Git repos only.")
            print("   Install GitHub CLI later and use manual setup.")
            create_github_repos = False
        
        # Detect projects
        projects = self.detect_projects_in_directory(directory_path)
        
        if not projects:
            print("❌ No projects found in directory")
            return []
        
        print(f"✅ Found {len(projects)} projects:")
        for project in projects:
            print(f"  - {project['name']}: {project['description']}")
        
        print()
        
        # Process each project
        successful_projects = []
        
        for project in projects:
            print(f"🔧 Processing: {project['name']}")
            
            # Set up Git repository
            if self.setup_git_repo(project['path'], project['name'], project['description']):
                if create_github_repos:
                    # Create GitHub repo and push
                    if self.create_github_repo_and_push(project['path'], project['name'], project['description']):
                        successful_projects.append(project['name'])
                else:
                    successful_projects.append(project['name'])
            
            print()
        
        return successful_projects


def main():
    parser = argparse.ArgumentParser(description="Convert existing projects to GitHub repositories")
    parser.add_argument("directory", type=str, help="Directory containing existing projects")
    parser.add_argument("--github-user", type=str, default="StewartGeisz", help="GitHub username")
    parser.add_argument("--no-github", action="store_true", help="Skip GitHub repository creation")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"❌ Directory not found: {args.directory}")
        sys.exit(1)
    
    manager = ExistingProjectsManager(github_username=args.github_user)
    
    try:
        successful_projects = manager.process_existing_projects(
            args.directory, 
            create_github_repos=not args.no_github
        )
        
        if successful_projects:
            print(f"🎉 Successfully processed {len(successful_projects)} projects:")
            for project in successful_projects:
                print(f"  - {project}")
                print(f"    https://github.com/{args.github_user}/{project}")
            
            print(f"\n🎯 Your GitHub profile now showcases these organized projects!")
            print("   This demonstrates your ability to manage and document code effectively.")
        else:
            print("❌ No projects were successfully processed.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()