#!/usr/bin/env python3
"""
example_usage.py

Demonstration of how to use the Project Organizer tool with different scenarios.

Author: Stewart Geisz
"""

import os
import sys
from project_organizer import ProjectOrganizer


def example_basic_usage():
    """Basic usage example"""
    print("=== Basic Usage Example ===")
    
    # Initialize organizer
    organizer = ProjectOrganizer(github_username="StewartGeisz")
    
    # Example directory (replace with your actual directory)
    input_dir = input("Enter directory path to organize: ")
    
    if not os.path.exists(input_dir):
        print(f"❌ Directory not found: {input_dir}")
        return
    
    # Organize projects
    projects = organizer.organize_projects(
        input_directory=input_dir,
        output_directory="my_organized_projects"
    )
    
    print(f"\n✅ Created {len(projects)} projects!")


def example_advanced_usage():
    """Advanced usage with custom settings"""
    print("=== Advanced Usage Example ===")
    
    # Custom organizer with different GitHub username
    organizer = ProjectOrganizer(github_username="YourGitHubUsername")
    
    # Simulate file analysis (normally done automatically)
    test_files = [
        {'path': 'test1.py', 'name': 'test1.py', 'extension': '.py', 'is_code': True},
        {'path': 'test2.js', 'name': 'test2.js', 'extension': '.js', 'is_code': True},
        {'path': 'data.csv', 'name': 'data.csv', 'extension': '.csv', 'is_data': True}
    ]
    
    # Show project detection logic
    print("🔍 Demonstrating project detection...")
    
    # Language detection
    for file_info in test_files:
        if file_info['is_code']:
            language = organizer.detect_language(file_info['extension'])
            print(f"  {file_info['name']} → {language}")
    
    # Show .gitignore generation
    print("\n📝 Sample .gitignore for Python:")
    gitignore = organizer.generate_gitignore('Python')
    print(gitignore[:200] + "...")


def example_project_analysis():
    """Example of analyzing project cohesion"""
    print("=== Project Analysis Example ===")
    
    organizer = ProjectOrganizer()
    
    # Sample file group
    code_files = [
        {'name': 'main.py', 'extension': '.py', 'path': 'main.py', 'size': 1000},
        {'name': 'utils.py', 'extension': '.py', 'path': 'utils.py', 'size': 500},
        {'name': 'config.json', 'extension': '.json', 'path': 'config.json', 'size': 100}
    ]
    
    # Analyze cohesion
    analysis = organizer.analyze_project_cohesion(code_files[:2])  # Only code files
    
    print(f"📊 Cohesion Analysis:")
    print(f"  Is Cohesive: {analysis['is_cohesive']}")
    print(f"  Main Language: {analysis['main_language']}")
    print(f"  Description: {analysis['description']}")


def example_readme_generation():
    """Example of README generation"""
    print("=== README Generation Example ===")
    
    organizer = ProjectOrganizer(github_username="StewartGeisz")
    
    # Sample project info
    project_info = {
        'main_language': 'Python',
        'description': 'A web scraping tool for data collection',
        'files': [
            {'name': 'scraper.py', 'extension': '.py', 'is_code': True, 'is_data': False},
            {'name': 'config.json', 'extension': '.json', 'is_code': False, 'is_data': True},
            {'name': 'requirements.txt', 'extension': '.txt', 'is_code': False, 'is_data': True}
        ]
    }
    
    # Generate README
    readme = organizer.generate_readme('web_scraper', project_info)
    
    print("📄 Generated README.md (first 500 chars):")
    print(readme[:500] + "...")


def interactive_demo():
    """Interactive demonstration"""
    print("🚀 Interactive Project Organizer Demo")
    print("=====================================")
    
    while True:
        print("\nChoose a demo:")
        print("1. Basic Usage")
        print("2. Advanced Settings")
        print("3. Project Analysis")
        print("4. README Generation")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            example_basic_usage()
        elif choice == '2':
            example_advanced_usage()
        elif choice == '3':
            example_project_analysis()
        elif choice == '4':
            example_readme_generation()
        elif choice == '5':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")


def workflow_example():
    """Complete workflow example"""
    print("=== Complete Workflow Example ===")
    print("This is how you would typically use the Project Organizer:")
    print()
    
    workflow_steps = [
        "1. 📂 Prepare your messy code directory",
        "2. 🔧 Run: python project_organizer.py /path/to/messy/code",
        "3. ✅ Review organized projects in 'organized_projects/' folder",
        "4. 🚀 Run: python github_setup.py organized_projects",
        "5. 🎉 Check your GitHub profile for new repositories!",
        "",
        "📈 Benefits:",
        "   - Clean, organized project structure",
        "   - Professional README.md for each project", 
        "   - Proper .gitignore files",
        "   - Git history and GitHub repositories",
        "   - Improved GitHub profile activity"
    ]
    
    for step in workflow_steps:
        print(step)


if __name__ == "__main__":
    print("🎯 Project Organizer - Usage Examples")
    print("====================================")
    
    if len(sys.argv) > 1:
        demo_type = sys.argv[1].lower()
        
        if demo_type == 'basic':
            example_basic_usage()
        elif demo_type == 'advanced':
            example_advanced_usage()
        elif demo_type == 'analysis':
            example_project_analysis()
        elif demo_type == 'readme':
            example_readme_generation()
        elif demo_type == 'workflow':
            workflow_example()
        else:
            print(f"❌ Unknown demo type: {demo_type}")
            print("Available demos: basic, advanced, analysis, readme, workflow")
    else:
        interactive_demo()