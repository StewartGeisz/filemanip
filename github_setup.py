#!/usr/bin/env python3
"""
github_setup.py

Helper script to create GitHub repositories for organized projects and set up remotes.
Requires GitHub CLI (gh) to be installed and authenticated.

Author: Stewart Geisz
GitHub: StewartGeisz
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Optional


class GitHubSetup:
    def __init__(self, github_username: str = "StewartGeisz"):
        self.github_username = github_username
        self.gh_command = None  # Will store working gh command
        
    def check_github_cli(self) -> bool:
        """Check if GitHub CLI is installed and authenticated"""
        # Try different ways to find gh
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
                    print("GitHub CLI is installed and authenticated")
                    # Store the working command for later use
                    self.gh_command = gh_cmd
                    return True
                else:
                    print("X GitHub CLI is not authenticated")
                    return False
            except FileNotFoundError:
                continue
            except Exception as e:
                continue
        
        print("X GitHub CLI (gh) is not found in PATH")
        print("   Try restarting your terminal, or run:")
        print(r'   "C:\Program Files\GitHub CLI\gh.exe" auth status')
        return False

    def create_or_check_github_repo(self, repo_name: str, description: str, private: bool = False) -> bool:
        """Create a GitHub repository or verify it exists"""
        try:
            # First, check if repository already exists
            check_cmd = [self.gh_command, 'repo', 'view', f"{self.github_username}/{repo_name}"]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode == 0:
                print(f"    INFO: Repository {repo_name} already exists - will push to existing repo")
                return True
            
            # Repository doesn't exist, try to create it
            cmd = [self.gh_command, 'repo', 'create', repo_name, '--description', description]
            if private:
                cmd.append('--private')
            else:
                cmd.append('--public')
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"    SUCCESS: GitHub repository created: {repo_name}")
                return True
            elif "already exists" in result.stderr.lower():
                print(f"    INFO: Repository {repo_name} already exists - will push to existing repo")
                return True
            else:
                print(f"    ERROR: Failed to create repository: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"    ERROR: Error with GitHub repository: {e}")
            return False

    def setup_remote_and_push(self, project_path: str, repo_name: str) -> bool:
        """Set up remote origin and push to GitHub"""
        try:
            os.chdir(project_path)
            
            # Check if remote already exists
            remote_url = f"https://github.com/{self.github_username}/{repo_name}.git"
            
            try:
                # Check existing remote
                existing_remote = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                               capture_output=True, text=True, check=True)
                current_url = existing_remote.stdout.strip()
                
                if current_url != remote_url:
                    # Update remote URL
                    subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url], 
                                 check=True, capture_output=True)
                    print(f"    INFO: Updated remote origin URL")
                else:
                    print(f"    INFO: Remote origin already correctly set")
                    
            except subprocess.CalledProcessError:
                # Remote doesn't exist, add it
                subprocess.run(['git', 'remote', 'add', 'origin', remote_url], 
                             check=True, capture_output=True)
                print(f"    SUCCESS: Remote origin added")
            
            # Set main as default branch
            subprocess.run(['git', 'branch', '-M', 'main'], 
                         check=True, capture_output=True)
            
            # Push to GitHub with force to handle any conflicts
            try:
                # Try normal push first
                subprocess.run(['git', 'push', '-u', 'origin', 'main'], 
                             check=True, capture_output=True)
                print(f"    SUCCESS: Pushed to GitHub: https://github.com/{self.github_username}/{repo_name}")
            except subprocess.CalledProcessError:
                # If normal push fails, try force push
                print(f"    INFO: Normal push failed, trying force push...")
                subprocess.run(['git', 'push', '-u', 'origin', 'main', '--force'], 
                             check=True, capture_output=True)
                print(f"    SUCCESS: Force pushed to GitHub: https://github.com/{self.github_username}/{repo_name}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"    ERROR: Git operation failed: {e}")
            return False
        except Exception as e:
            print(f"    ERROR: Error setting up remote: {e}")
            return False

    def process_organized_projects(self, organized_projects_dir: str, private: bool = False) -> List[str]:
        """Process all projects in the organized projects directory"""
        if not os.path.exists(organized_projects_dir):
            print(f"ERROR: Directory not found: {organized_projects_dir}")
            return []
        
        if not self.check_github_cli():
            return []
        
        current_dir = os.getcwd()
        successful_repos = []
        
        print(f"Processing projects in: {organized_projects_dir}")
        
        for project_name in os.listdir(organized_projects_dir):
            project_path = os.path.join(organized_projects_dir, project_name)
            
            if not os.path.isdir(project_path):
                continue
                
            if not os.path.exists(os.path.join(project_path, '.git')):
                print(f"WARNING: Skipping {project_name}: Not a Git repository")
                continue
            
            print(f"Processing project: {project_name}")
            
            # Read README for description
            readme_path = os.path.join(project_path, 'README.md')
            description = f"Organized project: {project_name}"
            
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, 'r') as f:
                        lines = f.readlines()
                        for line in lines:
                            if line.startswith('## Description'):
                                # Get next non-empty line
                                idx = lines.index(line) + 1
                                while idx < len(lines) and lines[idx].strip() == '':
                                    idx += 1
                                if idx < len(lines):
                                    description = lines[idx].strip()
                                break
                except Exception:
                    pass
            
            # Create or check GitHub repository
            if self.create_or_check_github_repo(project_name, description, private):
                # Set up remote and push
                if self.setup_remote_and_push(project_path, project_name):
                    successful_repos.append(project_name)
            
            os.chdir(current_dir)
        
        return successful_repos

    def setup_single_project(self, project_path: str, repo_name: str, description: str = "", private: bool = False) -> bool:
        """Set up GitHub repository for a single project"""
        if not os.path.exists(project_path):
            print(f"❌ Project path not found: {project_path}")
            return False
        
        if not os.path.exists(os.path.join(project_path, '.git')):
            print(f"❌ Not a Git repository: {project_path}")
            return False
        
        if not self.check_github_cli():
            return False
        
        current_dir = os.getcwd()
        
        try:
            print(f"Setting up GitHub repository for: {repo_name}")
            
            if not description:
                description = f"Project: {repo_name}"
            
            # Create or check GitHub repository
            if self.create_or_check_github_repo(repo_name, description, private):
                # Set up remote and push
                return self.setup_remote_and_push(project_path, repo_name)
            
            return False
            
        finally:
            os.chdir(current_dir)


def main():
    parser = argparse.ArgumentParser(description="Create GitHub repositories for organized projects")
    parser.add_argument("projects_dir", type=str, 
                       help="Directory containing organized projects")
    parser.add_argument("--private", action="store_true", 
                       help="Create private repositories (default: public)")
    parser.add_argument("--github-user", type=str, default="StewartGeisz",
                       help="GitHub username")
    parser.add_argument("--single", type=str,
                       help="Process only a single project directory")
    
    args = parser.parse_args()
    
    github_setup = GitHubSetup(github_username=args.github_user)
    
    try:
        if args.single:
            # Process single project
            project_path = os.path.join(args.projects_dir, args.single)
            success = github_setup.setup_single_project(
                project_path, args.single, private=args.private
            )
            if success:
                print(f"\nSUCCESS: Set up GitHub repository for {args.single}")
            else:
                print(f"\nERROR: Failed to set up GitHub repository for {args.single}")
                sys.exit(1)
        else:
            # Process all projects
            successful_repos = github_setup.process_organized_projects(
                args.projects_dir, private=args.private
            )
            
            if successful_repos:
                print(f"\nSUCCESS: Created {len(successful_repos)} GitHub repositories:")
                for repo in successful_repos:
                    print(f"  - https://github.com/{args.github_user}/{repo}")
                
                print(f"\nYour GitHub profile now shows {len(successful_repos)} new repositories!")
                print("   This will significantly boost your GitHub activity and showcase your projects.")
            else:
                print("\nERROR: No repositories were successfully created.")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()