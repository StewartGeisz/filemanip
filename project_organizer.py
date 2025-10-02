#!/usr/bin/env python3
"""
project_organizer.py

Scans a directory, analyzes files to detect projects, organizes them into 
separate folders, and creates Git repositories with README.md and .gitignore 
files for each project.

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

# Load environment variables from .env file
load_dotenv()


class ProjectOrganizer:
    def __init__(self, github_username: str = "StewartGeisz"):
        self.github_username = github_username
        self.supported_code_extensions = {
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go',
            '.rs', '.swift', '.kt', '.scala', '.r', '.m', '.pl', '.sh', '.sql', 
            '.html', '.css', '.xml', '.json', '.yaml', '.yml', '.md', '.txt'
        }
        self.data_extensions = {
            '.csv', '.xlsx', '.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg', 
            '.gif', '.svg', '.zip', '.tar', '.gz'
        }
        
    def validate_api_key(self) -> Optional[str]:
        """Validate that the API key is available"""
        API_KEY = os.getenv("AMPLIFY_API_KEY")
        if not API_KEY:
            print("❌ Error: AMPLIFY_API_KEY not found in environment variables")
            print("Please set your API key in a .env file or environment variable")
            return None
        return API_KEY

    def get_headers(self) -> Optional[Dict[str, str]]:
        """Get headers for API requests"""
        API_KEY = self.validate_api_key()
        if not API_KEY:
            return None
        return {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    def scan_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Scan directory and return file information"""
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            print(f"❌ Error: Directory not found: {directory_path}")
            return []

        files_info = []
        print(f"📂 Scanning directory: {directory_path}")
        
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
                
        print(f"📊 Total files found: {len(files_info)}")
        return files_info

    def analyze_file_content(self, file_path: str) -> Dict[str, Any]:
        """Analyze file content to determine project relationships"""
        analysis = {
            'imports': [],
            'functions': [],
            'classes': [],
            'keywords': [],
            'references': [],
            'content_summary': ''
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                analysis['content_summary'] = content[:500] + '...' if len(content) > 500 else content
                
                # Extract imports (Python, JS, etc.)
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
            print(f"⚠️ Could not analyze {file_path}: {e}")
            
        return analysis

    def detect_projects(self, files_info: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Detect and group files into projects based on content analysis"""
        print("🔍 Analyzing files for project detection...")
        
        # Group files by directory first
        directory_groups = defaultdict(list)
        for file_info in files_info:
            directory_groups[file_info['directory']].append(file_info)
        
        projects = {}
        misc_files = []
        
        for directory, dir_files in directory_groups.items():
            code_files = [f for f in dir_files if f['is_code']]
            
            if len(code_files) >= 1:  # At least one code file makes it a project
                # Analyze file relationships
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
                    # Split into individual projects if files don't belong together
                    for code_file in code_files:
                        file_name = os.path.splitext(code_file['name'])[0]
                        project_name = f"{file_name}_project"
                        
                        # Include related data files
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
        
        print(f"✅ Detected {len(projects)} projects")
        return projects

    def analyze_project_cohesion(self, code_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze if files belong together in the same project"""
        if len(code_files) == 1:
            return {
                'is_cohesive': True,
                'main_language': self.detect_language(code_files[0]['extension']),
                'description': f"Single-file project: {code_files[0]['name']}"
            }
        
        # Analyze file content for relationships
        languages = set()
        shared_imports = set()
        all_imports = []
        
        for file_info in code_files:
            languages.add(self.detect_language(file_info['extension']))
            analysis = self.analyze_file_content(file_info['path'])
            all_imports.extend(analysis['imports'])
        
        # Check for cross-references between files
        file_names = {os.path.splitext(f['name'])[0] for f in code_files}
        cross_references = sum(1 for imp in all_imports if any(name in imp for name in file_names))
        
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

    def detect_language(self, extension: str) -> str:
        """Detect programming language from file extension"""
        language_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.cs': 'C#',
            '.php': 'PHP', '.rb': 'Ruby', '.go': 'Go', '.rs': 'Rust',
            '.swift': 'Swift', '.kt': 'Kotlin', '.scala': 'Scala',
            '.r': 'R', '.m': 'MATLAB', '.pl': 'Perl', '.sh': 'Shell',
            '.sql': 'SQL', '.html': 'HTML', '.css': 'CSS',
            '.json': 'JSON', '.yaml': 'YAML', '.yml': 'YAML'
        }
        return language_map.get(extension.lower(), 'Unknown')

    def generate_project_name(self, directory: str, code_files: List[Dict[str, Any]]) -> str:
        """Generate a meaningful project name"""
        if directory and directory != '.':
            # Use directory name if meaningful
            base_name = os.path.basename(directory).replace(' ', '_').lower()
            if base_name and base_name not in ['src', 'code', 'files']:
                return base_name
        
        # Use main file name
        main_file = max(code_files, key=lambda x: x['size'])
        return os.path.splitext(main_file['name'])[0].replace(' ', '_').lower() + '_project'

    def create_project_structure(self, projects: Dict[str, Any], output_dir: str) -> Dict[str, str]:
        """Create organized project structure"""
        print(f"📁 Creating project structure in: {output_dir}")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        project_paths = {}
        
        for project_name, project_info in projects.items():
            project_dir = os.path.join(output_dir, project_name)
            os.makedirs(project_dir, exist_ok=True)
            project_paths[project_name] = project_dir
            
            print(f"  📂 Creating project: {project_name}")
            
            # Copy files to project directory
            for file_info in project_info['files']:
                src_path = file_info['path']
                dst_path = os.path.join(project_dir, file_info['name'])
                
                try:
                    shutil.copy2(src_path, dst_path)
                    print(f"    ✅ Copied: {file_info['name']}")
                except Exception as e:
                    print(f"    ❌ Failed to copy {file_info['name']}: {e}")
        
        return project_paths

    def generate_gitignore(self, language: str) -> str:
        """Generate appropriate .gitignore for the project language"""
        gitignore_templates = {
            'Python': """# Byte-compiled / optimized / DLL files
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

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json
""",
            'JavaScript': """# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Directory for instrumented libs generated by jscoverage/JSCover
lib-cov

# Coverage directory used by tools like istanbul
coverage

# nyc test coverage
.nyc_output

# Grunt intermediate storage (https://gruntjs.com/creating-plugins#storing-task-files)
.grunt

# Bower dependency directory (https://bower.io/)
bower_components

# node-waf configuration
.lock-wscript

# Compiled binary addons (https://nodejs.org/api/addons.html)
build/Release

# Dependency directories
node_modules/
jspm_packages/

# TypeScript v1 declaration files
typings/

# Optional npm cache directory
.npm

# Optional eslint cache
.eslintcache

# Optional REPL history
.node_repl_history

# Output of 'npm pack'
*.tgz

# Yarn Integrity file
.yarn-integrity

# dotenv environment variables file
.env

# parcel-bundler cache (https://parceljs.org/)
.cache
.parcel-cache

# next.js build output
.next

# nuxt.js build output
.nuxt

# vuepress build output
.vuepress/dist

# Serverless directories
.serverless
""",
            'Java': """# Compiled class file
*.class

# Log file
*.log

# BlueJ files
*.ctxt

# Mobile Tools for Java (J2ME)
.mtj.tmp/

# Package Files #
*.jar
*.war
*.nar
*.ear
*.zip
*.tar.gz
*.rar

# virtual machine crash logs, see http://www.java.com/en/download/help/error_hotspot.xml
hs_err_pid*

# Eclipse
.classpath
.project
.settings/

# IntelliJ IDEA
.idea/
*.iml
*.iws

# NetBeans
/nbproject/private/
/build/
/nbbuild/
/dist/
/nbdist/
/.nb-gradle/

# Gradle
.gradle/
/build/

# Maven
target/
pom.xml.tag
pom.xml.releaseBackup
pom.xml.versionsBackup
pom.xml.next
release.properties
dependency-reduced-pom.xml
buildNumber.properties
.mvn/timing.properties
.mvn/wrapper/maven-wrapper.jar
""",
            'default': """# OS generated files
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

# Build outputs
/dist/
/build/
/out/

# Dependencies
node_modules/
vendor/
"""
        }
        
        return gitignore_templates.get(language, gitignore_templates['default'])

    def generate_readme(self, project_name: str, project_info: Dict[str, Any]) -> str:
        """Generate README.md content for a project"""
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
            readme_content += """- Python 3.7 or higher
- pip for package management

### Installation
```bash
# Clone the repository
git clone https://github.com/{github_username}/{project_name}.git
cd {project_name}

# Install dependencies (if requirements.txt exists)
pip install -r requirements.txt
```

### Usage
```bash
python main.py  # Adjust filename as needed
```""".format(github_username=self.github_username, project_name=project_name)
        
        elif language == 'JavaScript':
            readme_content += """- Node.js and npm
- Modern web browser (if applicable)

### Installation
```bash
# Clone the repository
git clone https://github.com/{github_username}/{project_name}.git
cd {project_name}

# Install dependencies
npm install
```

### Usage
```bash
node index.js  # Adjust filename as needed
# or
npm start
```""".format(github_username=self.github_username, project_name=project_name)
        
        else:
            readme_content += f"""
### Installation
```bash
# Clone the repository
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
This project is licensed under the MIT License - see the LICENSE file for details.

## Author
**{self.github_username}**
- GitHub: [@{self.github_username}](https://github.com/{self.github_username})

---
*Generated automatically by Project Organizer*
"""
        
        return readme_content

    def initialize_git_repo(self, project_path: str, project_name: str, project_info: Dict[str, Any]) -> bool:
        """Initialize Git repository with README and .gitignore"""
        try:
            os.chdir(project_path)
            
            # Initialize git repo
            subprocess.run(['git', 'init'], check=True, capture_output=True)
            print(f"    ✅ Git repository initialized")
            
            # Create .gitignore
            gitignore_content = self.generate_gitignore(project_info['main_language'])
            with open('.gitignore', 'w') as f:
                f.write(gitignore_content)
            print(f"    ✅ .gitignore created")
            
            # Create README.md
            readme_content = self.generate_readme(project_name, project_info)
            with open('README.md', 'w') as f:
                f.write(readme_content)
            print(f"    ✅ README.md created")
            
            # Add and commit files
            subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit: Project setup'], 
                         check=True, capture_output=True)
            print(f"    ✅ Initial commit created")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"    ❌ Git operation failed: {e}")
            return False
        except Exception as e:
            print(f"    ❌ Error initializing git repo: {e}")
            return False

    def organize_projects(self, input_directory: str, output_directory: str = "organized_projects"):
        """Main method to organize projects"""
        print("🚀 Starting Project Organization Process")
        print(f"📂 Input Directory: {input_directory}")
        print(f"📁 Output Directory: {output_directory}")
        
        # Step 1: Scan directory
        files_info = self.scan_directory(input_directory)
        if not files_info:
            print("❌ No files found to organize")
            return
        
        # Step 2: Detect projects
        projects = self.detect_projects(files_info)
        if not projects:
            print("❌ No projects detected")
            return
        
        # Step 3: Create project structure
        project_paths = self.create_project_structure(projects, output_directory)
        
        # Step 4: Initialize Git repos
        current_dir = os.getcwd()
        successful_projects = []
        
        for project_name, project_path in project_paths.items():
            print(f"🔧 Setting up Git repository for: {project_name}")
            
            if self.initialize_git_repo(project_path, project_name, projects[project_name]):
                successful_projects.append(project_name)
            
            os.chdir(current_dir)  # Return to original directory
        
        # Step 5: Summary
        print(f"\n🎉 Project Organization Complete!")
        print(f"✅ Successfully created {len(successful_projects)} projects:")
        for project in successful_projects:
            print(f"  - {project}")
        
        print(f"\n📋 Next Steps:")
        print(f"1. Review the organized projects in: {output_directory}")
        print(f"2. Create GitHub repositories for each project")
        print(f"3. Push to GitHub to improve your profile activity")
        
        return successful_projects


def main():
    parser = argparse.ArgumentParser(description="Organize files into Git projects")
    parser.add_argument("directory", type=str, help="Directory to analyze and organize")
    parser.add_argument("--output", type=str, default="organized_projects", 
                       help="Output directory for organized projects")
    parser.add_argument("--github-user", type=str, default="StewartGeisz",
                       help="GitHub username for README files")
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.directory):
        print(f"❌ Error: Directory does not exist: {args.directory}")
        sys.exit(1)
    
    # Create organizer and run
    organizer = ProjectOrganizer(github_username=args.github_user)
    
    try:
        successful_projects = organizer.organize_projects(args.directory, args.output)
        if successful_projects:
            print(f"\n🎯 Organization successful! {len(successful_projects)} projects created.")
        else:
            print("\n❌ No projects were successfully created.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()