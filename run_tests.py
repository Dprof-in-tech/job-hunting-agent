#!/usr/bin/env python3
"""
Comprehensive test runner for the multi-agent job hunting system
"""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime
from pathlib import Path


def run_command(command, capture_output=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=capture_output,
            text=True,
            check=True
        )
        return result.stdout if capture_output else None
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {command}")
        print(f"Error: {e.stderr}" if e.stderr else f"Return code: {e.returncode}")
        return None


def install_dependencies():
    """Install test dependencies"""
    print("📦 Installing test dependencies...")
    
    commands = [
        "pip install -r requirements.txt",
        "pip install --upgrade deepeval pytest pytest-asyncio pytest-mock pytest-cov pytest-timeout pytest-benchmark responses faker"
    ]
    
    for cmd in commands:
        print(f"Running: {cmd}")
        result = run_command(cmd, capture_output=False)
        if result is None:
            print(f"❌ Failed to run: {cmd}")
            return False
    
    print("✅ Dependencies installed successfully")
    return True


def run_unit_tests():
    """Run unit tests"""
    print("\n🔬 Running unit tests...")
    
    cmd = "python -m pytest tests/ -m 'unit or not (integration or performance or slow)' -v --tb=short"
    result = run_command(cmd, capture_output=False)
    
    return result is not None


def run_integration_tests():
    """Run integration tests"""
    print("\n🔗 Running integration tests...")
    
    cmd = "python -m pytest tests/test_integration.py -v --tb=short"
    result = run_command(cmd, capture_output=False)
    
    return result is not None


def run_performance_tests():
    """Run performance tests"""
    print("\n⚡ Running performance tests...")
    
    cmd = "python -m pytest tests/test_performance.py -v --tb=short --benchmark-skip"
    result = run_command(cmd, capture_output=False)
    
    return result is not None


def run_benchmark_tests():
    """Run benchmark tests"""
    print("\n📊 Running benchmark tests...")
    
    cmd = "python -m pytest tests/test_performance.py -v --benchmark-only --benchmark-sort=mean"
    result = run_command(cmd, capture_output=False)
    
    return result is not None


def run_error_handling_tests():
    """Run error handling and resilience tests"""
    print("\n🛡️ Running error handling tests...")
    
    cmd = "python -m pytest tests/test_error_handling.py -v --tb=short"
    result = run_command(cmd, capture_output=False)
    
    return result is not None


def run_evaluation_tests():
    """Run DeepEval evaluation tests"""
    print("\n📈 Running evaluation tests...")
    
    cmd = "python -m pytest tests/test_complete_evaluation.py -v --tb=short"
    result = run_command(cmd, capture_output=False)
    
    return result is not None


def run_coverage_analysis():
    """Run coverage analysis"""
    print("\n📋 Running coverage analysis...")
    
    cmd = "python -m pytest tests/ --cov=api --cov-report=html --cov-report=term-missing --cov-fail-under=70"
    result = run_command(cmd, capture_output=False)
    
    if result is not None:
        print("📊 Coverage report generated in htmlcov/index.html")
    
    return result is not None


def run_full_test_suite():
    """Run the complete test suite"""
    print("🚀 Running full test suite for multi-agent job hunting system")
    print("=" * 70)
    
    test_results = {}
    
    # Run all test categories
    test_categories = [
        ("Unit Tests", run_unit_tests),
        ("Integration Tests", run_integration_tests),
        ("Performance Tests", run_performance_tests),
        ("Error Handling Tests", run_error_handling_tests),
        ("Evaluation Tests", run_evaluation_tests),
        ("Coverage Analysis", run_coverage_analysis)
    ]
    
    for category, test_func in test_categories:
        print(f"\n{'='*20} {category} {'='*20}")
        success = test_func()
        test_results[category] = success
        
        if success:
            print(f"✅ {category} completed successfully")
        else:
            print(f"❌ {category} failed")
    
    # Generate summary report
    print("\n" + "="*70)
    print("📋 TEST SUITE SUMMARY")
    print("="*70)
    
    total_categories = len(test_results)
    passed_categories = sum(1 for success in test_results.values() if success)
    
    print(f"Total test categories: {total_categories}")
    print(f"Passed: {passed_categories}")
    print(f"Failed: {total_categories - passed_categories}")
    print(f"Success rate: {passed_categories/total_categories*100:.1f}%")
    
    print("\nCategory breakdown:")
    for category, success in test_results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {category}: {status}")
    
    # Save results to file
    results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_categories": total_categories,
                "passed_categories": passed_categories,
                "failed_categories": total_categories - passed_categories,
                "success_rate": passed_categories/total_categories
            },
            "detailed_results": test_results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    return passed_categories == total_categories


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(
        description="Test runner for multi-agent job hunting system"
    )
    
    parser.add_argument(
        "--install-deps", 
        action="store_true",
        help="Install test dependencies before running tests"
    )
    
    parser.add_argument(
        "--category",
        choices=["unit", "integration", "performance", "benchmark", "error", "evaluation", "coverage"],
        help="Run specific test category only"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true", 
        help="Run quick tests only (excludes slow and benchmark tests)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not os.path.exists("api/main.py"):
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Install dependencies if requested
    if args.install_deps:
        if not install_dependencies():
            print("❌ Failed to install dependencies")
            sys.exit(1)
    
    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "test_key_12345")
    
    # Run specific test category
    if args.category:
        category_runners = {
            "unit": run_unit_tests,
            "integration": run_integration_tests,
            "performance": run_performance_tests,
            "benchmark": run_benchmark_tests,
            "error": run_error_handling_tests,
            "evaluation": run_evaluation_tests,
            "coverage": run_coverage_analysis
        }
        
        runner = category_runners[args.category]
        success = runner()
        sys.exit(0 if success else 1)
    
    # Run quick tests
    elif args.quick:
        print("⚡ Running quick test suite...")
        cmd = "python -m pytest tests/ -m 'not (slow or benchmark)' -x --tb=short"
        success = run_command(cmd, capture_output=False) is not None
        sys.exit(0 if success else 1)
    
    # Run full test suite
    else:
        success = run_full_test_suite()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()