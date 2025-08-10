#!/usr/bin/env python3
"""
Comprehensive Load Testing Runner
Executes all load testing suites and generates unified report
"""

import sys
import os
import time
from datetime import datetime
import subprocess
import statistics
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(__file__))

def run_test_suite(test_file: str, test_name: str) -> Dict[str, Any]:
    """Run a test suite and capture results"""
    print(f"\n{'='*20} {test_name} {'='*20}")
    
    start_time = time.time()
    
    try:
        # Run the test file
        result = subprocess.run([
            sys.executable, test_file
        ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
        
        execution_time = time.time() - start_time
        
        return {
            'test_name': test_name,
            'success': result.returncode == 0,
            'execution_time': execution_time,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            'test_name': test_name,
            'success': False,
            'execution_time': time.time() - start_time,
            'stdout': '',
            'stderr': 'Test timed out after 10 minutes',
            'return_code': -1
        }
    except Exception as e:
        return {
            'test_name': test_name,
            'success': False,
            'execution_time': time.time() - start_time,
            'stdout': '',
            'stderr': f'Test execution failed: {str(e)}',
            'return_code': -2
        }

def extract_metrics_from_output(output: str) -> Dict[str, Any]:
    """Extract key metrics from test output"""
    metrics = {
        'requests_per_second': 0.0,
        'success_rate': 0.0,
        'avg_response_time': 0.0,
        'memory_usage_mb': 0.0,
        'concurrent_users': 0,
        'total_requests': 0
    }
    
    lines = output.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Extract various metrics patterns
        if 'req/s' in line or 'requests/second' in line:
            import re
            numbers = re.findall(r'(\d+\.?\d*)\s*(?:req/s|requests?/second)', line)
            if numbers:
                metrics['requests_per_second'] = max(metrics['requests_per_second'], float(numbers[0]))
        
        if 'success rate' in line.lower() or '% success' in line:
            import re
            percentages = re.findall(r'(\d+\.?\d*)%', line)
            if percentages:
                metrics['success_rate'] = max(metrics['success_rate'], float(percentages[0]))
        
        if 'response time' in line.lower() and ('ms' in line or 's' in line):
            import re
            times = re.findall(r'(\d+\.?\d*)\s*(?:ms|s)', line)
            if times:
                time_val = float(times[0])
                if 'ms' in line:
                    time_val = time_val / 1000  # Convert to seconds
                if metrics['avg_response_time'] == 0 or time_val < metrics['avg_response_time']:
                    metrics['avg_response_time'] = time_val
        
        if 'memory' in line.lower() and 'mb' in line.lower():
            import re
            memory = re.findall(r'(\d+\.?\d*)\s*mb', line.lower())
            if memory:
                metrics['memory_usage_mb'] = max(metrics['memory_usage_mb'], float(memory[0]))
        
        if 'concurrent' in line.lower() and 'users' in line.lower():
            import re
            users = re.findall(r'(\d+)\s*(?:concurrent\s*)?users?', line.lower())
            if users:
                metrics['concurrent_users'] = max(metrics['concurrent_users'], int(users[0]))
        
        if 'total requests' in line.lower() or 'requests processed' in line.lower():
            import re
            requests = re.findall(r'(\d+(?:,\d{3})*)\s*requests?', line.lower())
            if requests:
                # Remove commas and convert to int
                req_count = int(requests[0].replace(',', ''))
                metrics['total_requests'] = max(metrics['total_requests'], req_count)
    
    return metrics

def generate_unified_report(test_results: List[Dict[str, Any]]) -> str:
    """Generate a comprehensive unified load test report"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("COMPREHENSIVE LOAD TESTING REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {timestamp}")
    report_lines.append(f"Test Suites Executed: {len(test_results)}")
    report_lines.append("")
    
    # Executive Summary
    successful_tests = [r for r in test_results if r['success']]
    failed_tests = [r for r in test_results if not r['success']]
    
    report_lines.append("EXECUTIVE SUMMARY:")
    report_lines.append(f"• Total Test Suites: {len(test_results)}")
    report_lines.append(f"• Successful: {len(successful_tests)}")
    report_lines.append(f"• Failed: {len(failed_tests)}")
    
    if successful_tests:
        total_execution_time = sum(r['execution_time'] for r in test_results)
        report_lines.append(f"• Total Execution Time: {total_execution_time:.1f} seconds")
        report_lines.append("")
    
    # Extract and aggregate metrics
    all_metrics = []
    for result in successful_tests:
        metrics = extract_metrics_from_output(result['stdout'])
        if metrics['requests_per_second'] > 0 or metrics['total_requests'] > 0:
            all_metrics.append(metrics)
    
    if all_metrics:
        report_lines.append("AGGREGATED PERFORMANCE METRICS:")
        
        # Calculate aggregated metrics
        total_requests = sum(m['total_requests'] for m in all_metrics)
        avg_rps = statistics.mean([m['requests_per_second'] for m in all_metrics if m['requests_per_second'] > 0])
        avg_success_rate = statistics.mean([m['success_rate'] for m in all_metrics if m['success_rate'] > 0])
        avg_response_time = statistics.mean([m['avg_response_time'] for m in all_metrics if m['avg_response_time'] > 0])
        max_memory = max([m['memory_usage_mb'] for m in all_metrics if m['memory_usage_mb'] > 0], default=0)
        max_concurrent = max([m['concurrent_users'] for m in all_metrics if m['concurrent_users'] > 0], default=0)
        
        report_lines.append(f"• Total Requests Processed: {total_requests:,}")
        report_lines.append(f"• Average Throughput: {avg_rps:.1f} requests/second")
        report_lines.append(f"• Average Success Rate: {avg_success_rate:.1f}%")
        report_lines.append(f"• Average Response Time: {avg_response_time:.2f} seconds")
        report_lines.append(f"• Peak Memory Usage: {max_memory:.1f} MB")
        report_lines.append(f"• Max Concurrent Users: {max_concurrent}")
        report_lines.append("")
    
    # Individual Test Results
    report_lines.append("DETAILED TEST RESULTS:")
    report_lines.append("-" * 60)
    
    for result in test_results:
        report_lines.append(f"\n{result['test_name']}:")
        report_lines.append(f"  Status: {'✅ PASSED' if result['success'] else '❌ FAILED'}")
        report_lines.append(f"  Execution Time: {result['execution_time']:.1f} seconds")
        
        if result['success']:
            metrics = extract_metrics_from_output(result['stdout'])
            if metrics['requests_per_second'] > 0:
                report_lines.append(f"  Throughput: {metrics['requests_per_second']:.1f} req/s")
            if metrics['success_rate'] > 0:
                report_lines.append(f"  Success Rate: {metrics['success_rate']:.1f}%")
            if metrics['avg_response_time'] > 0:
                report_lines.append(f"  Avg Response Time: {metrics['avg_response_time']:.2f}s")
            if metrics['total_requests'] > 0:
                report_lines.append(f"  Total Requests: {metrics['total_requests']:,}")
        else:
            report_lines.append(f"  Error: {result['stderr'][:100]}...")
        
        # Include key output lines
        output_lines = result['stdout'].split('\n')
        important_lines = [
            line for line in output_lines 
            if any(keyword in line.lower() for keyword in [
                'excellent', 'good', 'poor', 'breaking point', 'verdict', 
                'assessment', 'ready', 'not ready', '✅', '❌', '⚠️'
            ])
        ]
        
        if important_lines:
            report_lines.append("  Key Findings:")
            for line in important_lines[:3]:  # Top 3 important lines
                report_lines.append(f"    • {line.strip()}")
    
    # Overall Assessment
    report_lines.append("")
    report_lines.append("=" * 60)
    report_lines.append("OVERALL SYSTEM ASSESSMENT")
    report_lines.append("=" * 60)
    
    success_percentage = (len(successful_tests) / len(test_results)) * 100 if test_results else 0
    
    if success_percentage >= 90:
        assessment = "EXCELLENT"
        status_emoji = "🟢"
        recommendation = "System is ready for production deployment with excellent load handling capabilities."
    elif success_percentage >= 70:
        assessment = "GOOD"
        status_emoji = "🟡"
        recommendation = "System shows good performance under load with minor optimizations needed."
    elif success_percentage >= 50:
        assessment = "FAIR"
        status_emoji = "🟡"
        recommendation = "System requires performance optimizations before production deployment."
    else:
        assessment = "POOR"
        status_emoji = "🔴"
        recommendation = "Significant performance improvements required before production use."
    
    report_lines.append(f"{status_emoji} OVERALL GRADE: {assessment}")
    report_lines.append(f"• Test Success Rate: {success_percentage:.1f}%")
    
    if all_metrics and avg_rps > 0:
        if avg_rps >= 10 and avg_success_rate >= 95:
            perf_grade = "A"
        elif avg_rps >= 5 and avg_success_rate >= 90:
            perf_grade = "B"
        elif avg_rps >= 2 and avg_success_rate >= 80:
            perf_grade = "C"
        else:
            perf_grade = "D"
        
        report_lines.append(f"• Performance Grade: {perf_grade}")
    
    report_lines.append("")
    report_lines.append("RECOMMENDATION:")
    report_lines.append(f"• {recommendation}")
    
    # Production Readiness Checklist
    report_lines.append("")
    report_lines.append("PRODUCTION READINESS CHECKLIST:")
    checklist_items = [
        ("Load Testing", len(successful_tests) >= 3),
        ("Concurrency Handling", any("concurrent" in r['stdout'].lower() for r in successful_tests)),
        ("Memory Management", any("memory" in r['stdout'].lower() for r in successful_tests)),
        ("Error Handling", any("error" in r['stdout'].lower() or "fail" in r['stdout'].lower() for r in successful_tests)),
        ("Performance Metrics", len(all_metrics) > 0),
    ]
    
    for item, passed in checklist_items:
        status = "✅" if passed else "❌"
        report_lines.append(f"{status} {item}")
    
    # Next Steps
    report_lines.append("")
    report_lines.append("RECOMMENDED NEXT STEPS:")
    
    if failed_tests:
        report_lines.append("1. Address failed test suites:")
        for failed_test in failed_tests:
            report_lines.append(f"   • Fix {failed_test['test_name']}: {failed_test['stderr'][:50]}...")
    
    if all_metrics:
        if avg_rps < 5:
            report_lines.append("2. Optimize system throughput - current performance below target")
        if max_memory > 1000:
            report_lines.append("3. Implement memory optimization - usage exceeds 1GB")
        if avg_response_time > 3:
            report_lines.append("4. Reduce response times - currently above 3 seconds")
    
    report_lines.append("5. Set up production monitoring based on load test baselines")
    report_lines.append("6. Implement auto-scaling based on load test thresholds")
    report_lines.append("7. Schedule regular load testing for regression detection")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("End of Load Testing Report")
    report_lines.append("=" * 80)
    
    return "\n".join(report_lines)

def main():
    """Main load testing execution"""
    print("🚀 COMPREHENSIVE LOAD TESTING SUITE")
    print("=" * 50)
    print(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Define test suites to run
    test_suites = [
        ("tests/test_performance_load.py", "Performance & Multi-Agent Load"),
        ("tests/test_connection_pool_load.py", "Connection Pool & Resource Load"),
        ("tests/test_stress_testing.py", "Stress Testing & Breaking Points"),
        # Note: Full HTTP load testing commented out as it requires server
        # ("tests/test_load_testing.py", "HTTP API Load Testing")
    ]
    
    results = []
    overall_start = time.time()
    
    # Run each test suite
    for test_file, test_name in test_suites:
        if os.path.exists(test_file):
            result = run_test_suite(test_file, test_name)
            results.append(result)
            
            # Print immediate results
            if result['success']:
                print(f"✅ {test_name}: PASSED ({result['execution_time']:.1f}s)")
            else:
                print(f"❌ {test_name}: FAILED ({result['execution_time']:.1f}s)")
                print(f"   Error: {result['stderr'][:100]}...")
        else:
            print(f"⚠️ {test_name}: SKIPPED (file not found: {test_file})")
    
    total_time = time.time() - overall_start
    
    # Generate and save comprehensive report
    print(f"\n📊 Generating comprehensive report...")
    report = generate_unified_report(results)
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"comprehensive_load_test_report_{timestamp}.txt"
    
    with open(report_filename, 'w') as f:
        f.write(report)
    
    # Display summary
    print(f"\n" + "=" * 50)
    print(f"LOAD TESTING COMPLETED")
    print(f"=" * 50)
    print(f"Total Execution Time: {total_time:.1f} seconds")
    print(f"Test Suites Run: {len(results)}")
    print(f"Successful: {len([r for r in results if r['success']])}")
    print(f"Failed: {len([r for r in results if not r['success']])}")
    print(f"\n📋 Full Report: {report_filename}")
    
    # Print key findings
    successful_tests = [r for r in results if r['success']]
    if successful_tests:
        success_rate = (len(successful_tests) / len(results)) * 100
        
        if success_rate >= 90:
            print(f"🎉 EXCELLENT: {success_rate:.0f}% test success rate")
        elif success_rate >= 70:
            print(f"✅ GOOD: {success_rate:.0f}% test success rate")
        else:
            print(f"⚠️ NEEDS IMPROVEMENT: {success_rate:.0f}% test success rate")
    
    print(f"\nNext steps:")
    print(f"1. Review detailed report: {report_filename}")
    print(f"2. Address any failed tests")
    print(f"3. Implement recommended optimizations")
    print(f"4. Set up production monitoring")
    
    return len([r for r in results if not r['success']])  # Return number of failures

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)