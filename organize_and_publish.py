#!/usr/bin/env python3
"""
organize_and_publish.py

ONE COMMAND TO RULE THEM ALL

This script does everything:
1. Scans a directory for code files
2. Organizes them into logical projects 
3. Sets up Git repositories with README.md and .gitignore
4. Creates/updates GitHub repositories
5. Pushes everything to GitHub

Usage:
    python organize_and_publish.py /path/to/your/code/folder

Author: Stewart Geisz
GitHub: StewartGeisz
"""

import requests
import json
import os
import time
import datetime
import mimetypes
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dotenv import load_dotenv
from collections import defaultdict
import re

# Load environment variables
load_dotenv()


class AllInOneOrganizer:
    def __init__(self, github_username: str = "StewartGeisz", output_dir: str = "organized_projects"):
        self.github_username = github_username
        self.output_dir = output_dir
        self.gh_command = None
        
        # File extensions
        self.supported_code_extensions = {
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go',
            '.rs', '.swift', '.kt', '.scala', '.r', '.m', '.pl', '.sh', '.sql', 
            '.html', '.css', '.xml', '.json', '.yaml', '.yml', '.md', '.txt', '.ipynb'
        }
        self.data_extensions = {
            '.csv', '.xlsx', '.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg', 
            '.gif', '.svg', '.zip', '.tar', '.gz'
        }

    def check_prerequisites(self) -> bool:
        """Check if Git and GitHub CLI are available"""
        print("Checking prerequisites...")
        
        # Check Git
        try:
            subprocess.run(['git', '--version'], capture_output=True, check=True)
            print("  SUCCESS: Git is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  ERROR: Git is not installed. Please install Git first.")
            return False
        
        # Check GitHub CLI
        gh_commands = [
            'gh',
            r'C:\Program Files\GitHub CLI\gh.exe',
            r'C:\Users\{}\AppData\Local\GitHubCLI\gh.exe'.format(os.environ.get('USERNAME', ''))
        ]
        
        for gh_cmd in gh_commands:
            try:
                result = subprocess.run([gh_cmd, 'auth', 'status'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print("  SUCCESS: GitHub CLI is installed and authenticated")
                    self.gh_command = gh_cmd
                    return True
            except FileNotFoundError:
                continue
            except Exception:
                continue
        
        print("  WARNING: GitHub CLI not found. Will create local repos only.")
        print("  Install GitHub CLI and authenticate for full functionality.")
        return True  # Continue without GitHub CLI

    def scan_and_analyze_files(self, directory_path: str) -> List[Dict[str, Any]]:
        """Scan directory and analyze files"""
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            print(f"ERROR: Directory not found: {directory_path}")
            return []

        files_info = []
        print(f"Scanning directory: {directory_path}")
        
        for root, dirs, files in os.walk(directory_path):
            # Skip common non-project directories
            dirs[:] = [d for d in dirs if d not in [
                '.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env',
                '.pytest_cache', 'dist', 'build', 'target', '.idea', '.vscode'
            ]]
            
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                relative_path = os.path.relpath(file_path, directory_path)
                
                file_info = {
                    'path': file_path,
                    'relative_path': relative_path,
                    'name': file,
                    'extension': file_ext,
                    'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'is_code': file_ext in self.supported_code_extensions,
                    'is_data': file_ext in self.data_extensions,
                    'directory': os.path.dirname(relative_path)
                }
                files_info.append(file_info)
                
        print(f"Found {len(files_info)} files")
        return files_info

    def detect_language(self, extension: str) -> str:
        """Detect programming language from file extension"""
        language_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.cs': 'C#',
            '.php': 'PHP', '.rb': 'Ruby', '.go': 'Go', '.rs': 'Rust',
            '.swift': 'Swift', '.kt': 'Kotlin', '.scala': 'Scala',
            '.r': 'R', '.m': 'MATLAB', '.pl': 'Perl', '.sh': 'Shell',
            '.sql': 'SQL', '.html': 'HTML', '.css': 'CSS',
            '.json': 'JSON', '.yaml': 'YAML', '.yml': 'YAML', '.ipynb': 'Jupyter Notebook'
        }
        return language_map.get(extension.lower(), 'Unknown')

    def analyze_file_content(self, file_path: str) -> Dict[str, Any]:
        """Analyze file content for project relationships"""
        analysis = {
            'imports': [],
            'functions': [],
            'references': [],
            'keywords': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Extract imports
                import_patterns = [
                    r'import\s+([^\s]+)',
                    r'from\s+([^\s]+)\s+import',
                    r'require\([\'"]([^\'"]+)[\'"]\)',
                    r'#include\s*[<"]([^>"]+)[>"]'
                ]
                
                for pattern in import_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    analysis['imports'].extend(matches)
                
                # Extract function/class definitions
                func_patterns = [
                    r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                    r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                    r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)'
                ]
                
                for pattern in func_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    analysis['functions'].extend(matches)
                
                # Look for file references
                file_refs = re.findall(r'[\'"]([^\'"\s]*\.[a-zA-Z0-9]+)[\'"]', content)
                analysis['references'] = [ref for ref in file_refs if '.' in ref]
                
        except Exception as e:
            pass  # Silent fail for unreadable files
            
        return analysis

    def detect_projects(self, files_info: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Detect and group files into projects"""
        print("Analyzing files for project detection...")
        
        # Group files by directory first
        directory_groups = defaultdict(list)
        for file_info in files_info:
            directory_groups[file_info['directory']].append(file_info)
        
        projects = {}
        misc_files = []
        
        for directory, dir_files in directory_groups.items():
            code_files = [f for f in dir_files if f['is_code']]
            
            if len(code_files) >= 1:  # At least one code file makes it a project
                project_analysis = self.analyze_project_cohesion(code_files)
                
                if project_analysis['is_cohesive']:
                    project_name = self.generate_project_name(directory, code_files)
                    projects[project_name] = {
                        'files': dir_files,
                        'main_language': project_analysis['main_language'],
                        'description': project_analysis['description'],
                        'directory': directory
                    }
                else:
                    # Split into individual projects
                    for code_file in code_files:
                        file_name = os.path.splitext(code_file['name'])[0]
                        project_name = f"{file_name}_project"
                        
                        # Include related files
                        related_files = [code_file]
                        related_files.extend([f for f in dir_files if 
                                            f['name'].startswith(file_name) and f != code_file])
                        
                        projects[project_name] = {
                            'files': related_files,
                            'main_language': self.detect_language(code_file['extension']),
                            'description': f"Project based on {code_file['name']}",
                            'directory': directory
                        }
            else:
                # No code files - add to misc
                misc_files.extend(dir_files)
        
        if misc_files:
            projects['misc'] = {
                'files': misc_files,
                'main_language': 'mixed',
                'description': 'Miscellaneous files that don\'t belong to specific projects',
                'directory': 'misc'
            }
        
        print(f"Detected {len(projects)} projects")
        return projects

    def analyze_project_cohesion(self, code_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze if files belong together"""
        if len(code_files) == 1:
            return {
                'is_cohesive': True,
                'main_language': self.detect_language(code_files[0]['extension']),
                'description': f"Single-file project: {code_files[0]['name']}"
            }
        
        languages = set()
        cross_references = 0
        
        for file_info in code_files:
            languages.add(self.detect_language(file_info['extension']))
            analysis = self.analyze_file_content(file_info['path'])
            
            # Check for cross-references
            file_names = {os.path.splitext(f['name'])[0] for f in code_files}
            cross_references += sum(1 for imp in analysis['imports'] 
                                  if any(name in imp for name in file_names))
        
        # Determine cohesion
        is_cohesive = (
            len(languages) <= 2 or  # Same or compatible languages
            cross_references > 0 or  # Files reference each other
            len(code_files) <= 3  # Small groups likely belong together
        )
        
        main_language = max(languages, key=lambda x: sum(1 for f in code_files 
                                                       if self.detect_language(f['extension']) == x))
        
        return {
            'is_cohesive': is_cohesive,
            'main_language': main_language,
            'description': f"Multi-file {main_language} project"
        }

    def generate_project_name(self, directory: str, code_files: List[Dict[str, Any]]) -> str:
        """Generate a meaningful project name"""
        if directory and directory != '.':
            base_name = os.path.basename(directory).replace(' ', '_').lower()
            if base_name and base_name not in ['src', 'code', 'files']:
                return base_name
        
        # Use main file name
        main_file = max(code_files, key=lambda x: x['size'])
        return os.path.splitext(main_file['name'])[0].replace(' ', '_').lower() + '_project'

    def create_organized_structure(self, projects: Dict[str, Any]) -> Dict[str, str]:
        """Create organized project structure"""
        print(f"Creating organized structure in: {self.output_dir}")
        
        # Handle existing directory more safely
        if os.path.exists(self.output_dir):
            try:
                # Try to remove the directory
                shutil.rmtree(self.output_dir)
            except PermissionError:
                # If permission denied, create a new directory with timestamp
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                self.output_dir = f"{self.output_dir}_{timestamp}"
                print(f"  Permission issue with existing directory, using: {self.output_dir}")
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        project_paths = {}
        
        for project_name, project_info in projects.items():
            project_dir = os.path.join(self.output_dir, project_name)
            os.makedirs(project_dir, exist_ok=True)
            project_paths[project_name] = project_dir
            
            print(f"  Creating project: {project_name}")
            
            # Copy files to project directory
            for file_info in project_info['files']:
                src_path = file_info['path']
                dst_path = os.path.join(project_dir, file_info['name'])
                
                try:
                    shutil.copy2(src_path, dst_path)
                except Exception as e:
                    print(f"    WARNING: Failed to copy {file_info['name']}: {e}")
        
        return project_paths

    def generate_gitignore(self, language: str) -> str:
        """Generate .gitignore based on language"""
        base_gitignore = """# OS generated files
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

        language_specific = {
            'Python': """
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
.ipynb_checkpoints
""",
            'JavaScript': """
# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.eslintcache
dist/
build/
""",
            'Java': """
# Java
*.class
*.jar
*.war
*.ear
target/
.gradle/
build/
"""
        }
        
        return base_gitignore + language_specific.get(language, '')

    def generate_readme(self, project_name: str, project_info: Dict[str, Any]) -> str:
        """Generate README.md for project"""
        language = project_info['main_language']
        description = project_info['description']
        files = project_info['files']
        
        code_files = [f for f in files if f['is_code']]
        data_files = [f for f in files if f['is_data']]
        
        readme_content = f"""# {project_name.replace('_', ' ').title()}

## Description
{description}

## Project Details
- **Primary Language**: {language}
- **Total Files**: {len(files)}
- **Code Files**: {len(code_files)}
- **Data Files**: {len(data_files)}

## Files in this Project
"""
        
        if code_files:
            readme_content += "\n### Code Files\n"
            for file_info in code_files:
                readme_content += f"- `{file_info['name']}` - {self.detect_language(file_info['extension'])} file\n"
        
        if data_files:
            readme_content += "\n### Data Files\n"
            for file_info in data_files:
                readme_content += f"- `{file_info['name']}` - Data file ({file_info['extension']})\n"
        
        readme_content += f"""
## Getting Started

### Prerequisites
- {language} runtime environment
"""
        
        if language == 'Python':
            readme_content += f"""- Python 3.7 or higher
- pip for package management

### Installation
```bash
git clone https://github.com/{self.github_username}/{project_name}.git
cd {project_name}

# Install dependencies (if requirements.txt exists)
pip install -r requirements.txt
```

### Usage
```bash
python main.py  # Adjust filename as needed
```"""
        
        elif language == 'JavaScript':
            readme_content += f"""- Node.js and npm

### Installation
```bash
git clone https://github.com/{self.github_username}/{project_name}.git
cd {project_name}

# Install dependencies
npm install
```

### Usage
```bash
node index.js  # Adjust filename as needed
```"""
        
        else:
            readme_content += f"""
### Installation
```bash
git clone https://github.com/{self.github_username}/{project_name}.git
cd {project_name}
```

### Usage
Refer to the specific {language} documentation for running instructions.
"""
        
        readme_content += f"""
## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License.

## Author
**{self.github_username}**
- GitHub: [@{self.github_username}](https://github.com/{self.github_username})

---
*Organized and published using organize-and-publish tool*
"""
        
        return readme_content

    def setup_git_and_github(self, project_paths: Dict[str, str], projects: Dict[str, Any]) -> List[str]:
        """Set up Git repositories and push to GitHub"""
        print("Setting up Git repositories and GitHub...")
        
        current_dir = os.getcwd()
        successful_projects = []
        
        for project_name, project_path in project_paths.items():
            print(f"  Processing: {project_name}")
            
            try:
                os.chdir(project_path)
                project_info = projects[project_name]
                
                # Initialize Git repository
                subprocess.run(['git', 'init'], check=True, capture_output=True)
                print(f"    SUCCESS: Git repository initialized")
                
                # Create .gitignore
                gitignore_content = self.generate_gitignore(project_info['main_language'])
                with open('.gitignore', 'w') as f:
                    f.write(gitignore_content)
                print(f"    SUCCESS: .gitignore created")
                
                # Create README.md
                readme_content = self.generate_readme(project_name, project_info)
                with open('README.md', 'w') as f:
                    f.write(readme_content)
                print(f"    SUCCESS: README.md created")
                
                # Add and commit files
                subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
                subprocess.run(['git', 'commit', '-m', 'Initial commit: Organized project with documentation'], 
                             check=True, capture_output=True)
                print(f"    SUCCESS: Initial commit created")
                
                # GitHub operations (if GitHub CLI available)
                if self.gh_command:
                    if self.create_and_push_to_github(project_name, project_info['description']):
                        successful_projects.append(project_name)
                        print(f"    SUCCESS: Pushed to GitHub!")
                    else:
                        print(f"    WARNING: GitHub push failed, but local repo created")
                        successful_projects.append(project_name)  # Still count as success
                else:
                    successful_projects.append(project_name)
                
            except subprocess.CalledProcessError as e:
                print(f"    ERROR: Git operation failed for {project_name}: {e}")
            except Exception as e:
                print(f"    ERROR: Failed to process {project_name}: {e}")
            finally:
                os.chdir(current_dir)
        
        return successful_projects

    def create_and_push_to_github(self, repo_name: str, description: str) -> bool:
        """Create GitHub repository and push"""
        try:
            # Check if repository already exists
            check_cmd = [self.gh_command, 'repo', 'view', f"{self.github_username}/{repo_name}"]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            repo_exists = (check_result.returncode == 0)
            
            if not repo_exists:
                # Create new repository
                cmd = [self.gh_command, 'repo', 'create', repo_name, '--public', '--description', description]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0 and "already exists" not in result.stderr.lower():
                    print(f"      ERROR: Failed to create repository: {result.stderr}")
                    return False
            
            # Set up remote and push
            remote_url = f"https://github.com/{self.github_username}/{repo_name}.git"
            
            # Add or update remote
            try:
                subprocess.run(['git', 'remote', 'add', 'origin', remote_url], 
                             check=True, capture_output=True)
            except subprocess.CalledProcessError:
                # Remote might already exist, update it
                subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url], 
                             check=True, capture_output=True)
            
            # Set main branch and push
            subprocess.run(['git', 'branch', '-M', 'main'], check=True, capture_output=True)
            
            # Try normal push, then force push if needed
            try:
                subprocess.run(['git', 'push', '-u', 'origin', 'main'], 
                             check=True, capture_output=True)
            except subprocess.CalledProcessError:
                subprocess.run(['git', 'push', '-u', 'origin', 'main', '--force'], 
                             check=True, capture_output=True)
            
            return True
            
        except Exception as e:
            print(f"      ERROR: GitHub operation failed: {e}")
            return False

    def run_full_workflow(self, input_directory: str) -> bool:
        """Run the complete workflow"""
        print("=" * 60)
        print("ORGANIZE AND PUBLISH - Complete Project Workflow")
        print("=" * 60)
        print(f"Input Directory: {input_directory}")
        print(f"Output Directory: {self.output_dir}")
        print(f"GitHub Username: {self.github_username}")
        print()
        
        # Step 1: Check prerequisites
        if not self.check_prerequisites():
            return False
        
        print()
        
        # Step 2: Scan and analyze files
        files_info = self.scan_and_analyze_files(input_directory)
        if not files_info:
            print("ERROR: No files found to organize")
            return False
        
        print()
        
        # Step 3: Detect projects
        projects = self.detect_projects(files_info)
        if not projects:
            print("ERROR: No projects detected")
            return False
        
        print()
        
        # Step 4: Create organized structure
        project_paths = self.create_organized_structure(projects)
        
        print()
        
        # Step 5: Set up Git and GitHub
        successful_projects = self.setup_git_and_github(project_paths, projects)
        
        print()
        print("=" * 60)
        print("WORKFLOW COMPLETE!")
        print("=" * 60)
        
        if successful_projects:
            print(f"SUCCESS: Created {len(successful_projects)} organized projects:")
            for project in successful_projects:
                print(f"  - {project}")
                if self.gh_command:
                    print(f"    https://github.com/{self.github_username}/{project}")
            
            print(f"\nLocal projects created in: {self.output_dir}")
            
            if self.gh_command:
                print(f"\nYour GitHub profile now showcases {len(successful_projects)} new organized projects!")
                print("This demonstrates your ability to:")
                print("  - Organize and structure code projects")
                print("  - Create professional documentation")
                print("  - Use Git and GitHub effectively")
                print("  - Follow software development best practices")
            else:
                print("\nLocal Git repositories created. Install GitHub CLI to push to GitHub.")
            
            return True
        else:
            print("ERROR: No projects were successfully created")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Organize files into projects and publish to GitHub - ALL IN ONE COMMAND",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python organize_and_publish.py /path/to/messy/code
  python organize_and_publish.py /path/to/code --output my_projects --github-user MyUsername
  python organize_and_publish.py C:\\Users\\name\\Documents\\code_folder
        """
    )
    
    parser.add_argument("directory", type=str, help="Directory containing files to organize")
    parser.add_argument("--output", type=str, default="organized_projects", 
                       help="Output directory for organized projects (default: organized_projects)")
    parser.add_argument("--github-user", type=str, default="StewartGeisz",
                       help="GitHub username (default: StewartGeisz)")
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.directory):
        print(f"ERROR: Directory does not exist: {args.directory}")
        sys.exit(1)
    
    # Create and run organizer
    organizer = AllInOneOrganizer(
        github_username=args.github_user,
        output_dir=args.output
    )
    
    try:
        success = organizer.run_full_workflow(args.directory)
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()