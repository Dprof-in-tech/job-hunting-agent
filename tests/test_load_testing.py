"""
Comprehensive Load Testing Suite for Multi-Agent Job Hunting System
Tests system performance under various load conditions
"""

import asyncio
import concurrent.futures
import time
import threading
import requests
import json
import psutil
import statistics
import random
import string
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from api.main import JobHuntingMultiAgent
from tools.security import SecurityManager

# Configure logging for load tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing"""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    p95_response_time: float
    p99_response_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    concurrent_users: int
    test_duration_seconds: float
    error_rate: float
    throughput_mb_per_second: float

@dataclass
class LoadTestResult:
    """Result of a single request in load test"""
    success: bool
    response_time: float
    status_code: int
    response_size: int
    error_message: str = ""

class SystemMonitor:
    """Monitor system resources during load testing"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start system resource monitoring"""
        self.monitoring = True
        self.metrics = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring and return metrics"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        return self.metrics
    
    def _monitor_loop(self):
        """Monitor system resources in a loop"""
        while self.monitoring:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                
                self.metrics.append({
                    'timestamp': datetime.now(),
                    'cpu_percent': cpu_percent,
                    'memory_used_mb': memory.used / 1024 / 1024,
                    'memory_percent': memory.percent,
                    'available_memory_mb': memory.available / 1024 / 1024
                })
                
                time.sleep(1)  # Monitor every second
            except Exception as e:
                logger.warning(f"Monitoring error: {e}")
                time.sleep(1)

class LoadTestExecutor:
    """Execute various types of load tests"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30  # 30 second timeout
        
    def generate_test_data(self) -> Dict[str, Any]:
        """Generate realistic test data for requests"""
        prompts = [
            "Analyze my resume and provide feedback",
            "Find software engineering jobs that match my skills",
            "Create an optimized CV for tech companies",
            "Help me improve my resume for data science roles",
            "Research job market trends for product management",
            "Compare my resume against specific job requirements",
            "Generate a professional CV for marketing positions",
            "Find remote work opportunities in my field"
        ]
        
        return {
            "prompt": random.choice(prompts),
            "user_id": f"load_test_user_{random.randint(1000, 9999)}"
        }
    
    def execute_single_request(self, endpoint: str, data: Dict[str, Any]) -> LoadTestResult:
        """Execute a single request and measure performance"""
        start_time = time.time()
        
        try:
            if endpoint.startswith('/api/'):
                # For secure endpoints, need to create session first
                session_response = self.session.post(f"{self.base_url}/api/session")
                if session_response.status_code != 200:
                    return LoadTestResult(
                        success=False,
                        response_time=time.time() - start_time,
                        status_code=session_response.status_code,
                        response_size=0,
                        error_message="Failed to create session"
                    )
                
                session_data = session_response.json()
                headers = {
                    'Authorization': f"Bearer {session_data['token']}",
                    'Content-Type': 'application/json'
                }
                
                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    json=data,
                    headers=headers
                )
            else:
                # Regular API endpoint
                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    json=data,
                    headers={'Content-Type': 'application/json'}
                )
            
            response_time = time.time() - start_time
            
            return LoadTestResult(
                success=200 <= response.status_code < 300,
                response_time=response_time,
                status_code=response.status_code,
                response_size=len(response.content) if response.content else 0
            )
            
        except requests.exceptions.RequestException as e:
            return LoadTestResult(
                success=False,
                response_time=time.time() - start_time,
                status_code=0,
                response_size=0,
                error_message=str(e)
            )

class LoadTester:
    """Main load testing class with various test scenarios"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.executor = LoadTestExecutor(base_url)
        self.monitor = SystemMonitor()
        
    def run_concurrent_user_test(self, concurrent_users: int, duration_seconds: int, 
                                endpoint: str = "/api/process") -> LoadTestMetrics:
        """Test with multiple concurrent users"""
        
        results = []
        start_time = time.time()
        
        # Start system monitoring
        self.monitor.start_monitoring()
        
        def user_session(user_id: int):
            """Simulate a single user session"""
            session_results = []
            end_time = start_time + duration_seconds
            
            while time.time() < end_time:
                test_data = self.executor.generate_test_data()
                test_data['user_id'] = f"load_test_user_{user_id}"
                
                result = self.executor.execute_single_request(endpoint, test_data)
                session_results.append(result)
                
                # Random think time between requests (0.5-2 seconds)
                time.sleep(random.uniform(0.5, 2.0))
            
            return session_results
        
        # Execute concurrent user sessions
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            future_to_user = {
                executor.submit(user_session, user_id): user_id 
                for user_id in range(concurrent_users)
            }
            
            for future in concurrent.futures.as_completed(future_to_user):
                user_results = future.result()
                results.extend(user_results)
        
        # Stop monitoring and collect metrics
        system_metrics = self.monitor.stop_monitoring()
        test_duration = time.time() - start_time
        
        return self._calculate_metrics(
            test_name=f"Concurrent Users ({concurrent_users})",
            results=results,
            test_duration=test_duration,
            concurrent_users=concurrent_users,
            system_metrics=system_metrics
        )
    
    def run_spike_test(self, max_users: int, spike_duration: int = 30, 
                      endpoint: str = "/api/process") -> LoadTestMetrics:
        """Test sudden spike in traffic"""
        
        results = []
        start_time = time.time()
        
        # Start system monitoring
        self.monitor.start_monitoring()
        
        # Gradually increase load
        phases = [
            (5, 10),    # 5 users for 10 seconds (warmup)
            (max_users, spike_duration),  # Spike to max users
            (10, 20),   # Cool down to 10 users for 20 seconds
        ]
        
        for users, duration in phases:
            phase_start = time.time()
            
            def user_requests(user_id: int):
                session_results = []
                phase_end = phase_start + duration
                
                while time.time() < phase_end:
                    test_data = self.executor.generate_test_data()
                    result = self.executor.execute_single_request(endpoint, test_data)
                    session_results.append(result)
                    time.sleep(random.uniform(0.1, 0.5))  # Aggressive requests during spike
                
                return session_results
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
                futures = [executor.submit(user_requests, i) for i in range(users)]
                for future in concurrent.futures.as_completed(futures):
                    results.extend(future.result())
        
        # Stop monitoring
        system_metrics = self.monitor.stop_monitoring()
        test_duration = time.time() - start_time
        
        return self._calculate_metrics(
            test_name=f"Spike Test ({max_users} peak)",
            results=results,
            test_duration=test_duration,
            concurrent_users=max_users,
            system_metrics=system_metrics
        )
    
    def run_sustained_load_test(self, users: int, duration_minutes: int, 
                               endpoint: str = "/api/process") -> LoadTestMetrics:
        """Test sustained load over extended period"""
        
        results = []
        start_time = time.time()
        duration_seconds = duration_minutes * 60
        
        # Start system monitoring
        self.monitor.start_monitoring()
        
        def sustained_user_session(user_id: int):
            session_results = []
            end_time = start_time + duration_seconds
            request_count = 0
            
            while time.time() < end_time:
                test_data = self.executor.generate_test_data()
                result = self.executor.execute_single_request(endpoint, test_data)
                session_results.append(result)
                request_count += 1
                
                # Log progress periodically
                if request_count % 10 == 0:
                    logger.debug(f"User {user_id}: {request_count} requests completed")
                
                # Realistic user behavior - varying think time
                time.sleep(random.uniform(1.0, 3.0))
            
            return session_results
        
        # Execute sustained load
        with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
            futures = [executor.submit(sustained_user_session, i) for i in range(users)]
            
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())
        
        # Stop monitoring
        system_metrics = self.monitor.stop_monitoring()
        test_duration = time.time() - start_time
        
        return self._calculate_metrics(
            test_name=f"Sustained Load ({users} users, {duration_minutes}min)",
            results=results,
            test_duration=test_duration,
            concurrent_users=users,
            system_metrics=system_metrics
        )
    
    def run_stress_test(self, endpoint: str = "/api/process") -> LoadTestMetrics:
        """Find breaking point of the system"""
        
        all_results = []
        start_time = time.time()
        
        # Start system monitoring
        self.monitor.start_monitoring()
        
        # Gradually increase load until failure
        user_counts = [1, 5, 10, 25, 50, 75, 100, 150, 200]
        breaking_point = None
        
        for user_count in user_counts:
            
            # Run short burst with current user count
            phase_results = []
            phase_start = time.time()
            test_duration = 60  # 1 minute per phase
            
            def stress_user_session():
                session_results = []
                end_time = phase_start + test_duration
                
                while time.time() < end_time:
                    test_data = self.executor.generate_test_data()
                    result = self.executor.execute_single_request(endpoint, test_data)
                    session_results.append(result)
                    
                    # Aggressive load - minimal think time
                    time.sleep(random.uniform(0.1, 0.3))
                
                return session_results
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=user_count) as executor:
                futures = [executor.submit(stress_user_session) for _ in range(user_count)]
                
                for future in concurrent.futures.as_completed(futures):
                    phase_results.extend(future.result())
            
            all_results.extend(phase_results)
            
            # Check if system is failing (>20% error rate)
            phase_error_rate = sum(1 for r in phase_results if not r.success) / len(phase_results)
            avg_response_time = statistics.mean([r.response_time for r in phase_results])
            
            
            if phase_error_rate > 0.2 or avg_response_time > 30:
                breaking_point = user_count
                logger.warning(f"Breaking point reached at {user_count} concurrent users")
                break
        
        # Stop monitoring
        system_metrics = self.monitor.stop_monitoring()
        total_duration = time.time() - start_time
        
        metrics = self._calculate_metrics(
            test_name=f"Stress Test (Breaking point: {breaking_point or 'Not found'})",
            results=all_results,
            test_duration=total_duration,
            concurrent_users=breaking_point or max(user_counts),
            system_metrics=system_metrics
        )
        
        return metrics
    
    def _calculate_metrics(self, test_name: str, results: List[LoadTestResult], 
                          test_duration: float, concurrent_users: int,
                          system_metrics: List[Dict]) -> LoadTestMetrics:
        """Calculate comprehensive metrics from test results"""
        
        if not results:
            return LoadTestMetrics(
                test_name=test_name,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                average_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                requests_per_second=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                concurrent_users=concurrent_users,
                test_duration_seconds=test_duration,
                error_rate=0.0,
                throughput_mb_per_second=0.0
            )
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        response_times = [r.response_time for r in results]
        response_sizes = [r.response_size for r in results]
        
        # Calculate percentiles
        response_times_sorted = sorted(response_times)
        p95_idx = int(len(response_times_sorted) * 0.95)
        p99_idx = int(len(response_times_sorted) * 0.99)
        
        # System resource metrics
        avg_memory = 0.0
        avg_cpu = 0.0
        if system_metrics:
            avg_memory = statistics.mean([m['memory_used_mb'] for m in system_metrics])
            avg_cpu = statistics.mean([m['cpu_percent'] for m in system_metrics])
        
        # Throughput calculation
        total_data_mb = sum(response_sizes) / (1024 * 1024)
        throughput = total_data_mb / test_duration if test_duration > 0 else 0
        
        return LoadTestMetrics(
            test_name=test_name,
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            average_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            requests_per_second=len(results) / test_duration if test_duration > 0 else 0,
            p95_response_time=response_times_sorted[p95_idx] if response_times_sorted else 0,
            p99_response_time=response_times_sorted[p99_idx] if response_times_sorted else 0,
            memory_usage_mb=avg_memory,
            cpu_usage_percent=avg_cpu,
            concurrent_users=concurrent_users,
            test_duration_seconds=test_duration,
            error_rate=len(failed_results) / len(results) if results else 0,
            throughput_mb_per_second=throughput
        )

class LoadTestReporter:
    """Generate comprehensive load test reports"""
    
    @staticmethod
    def generate_report(metrics_list: List[LoadTestMetrics]) -> str:
        """Generate a comprehensive load test report"""
        
        report = []
        report.append("=" * 80)
        report.append("COMPREHENSIVE LOAD TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Executive Summary
        total_requests = sum(m.total_requests for m in metrics_list)
        total_successful = sum(m.successful_requests for m in metrics_list)
        avg_error_rate = statistics.mean([m.error_rate for m in metrics_list])
        avg_response_time = statistics.mean([m.average_response_time for m in metrics_list])
        
        report.append("EXECUTIVE SUMMARY:")
        report.append(f"• Total Requests Processed: {total_requests:,}")
        report.append(f"• Successful Requests: {total_successful:,}")
        report.append(f"• Overall Success Rate: {((total_successful/total_requests)*100):.1f}%")
        report.append(f"• Average Error Rate: {(avg_error_rate*100):.1f}%")
        report.append(f"• Average Response Time: {avg_response_time:.2f}s")
        report.append("")
        
        # Individual Test Results
        for metrics in metrics_list:
            report.append("-" * 60)
            report.append(f"TEST: {metrics.test_name}")
            report.append("-" * 60)
            
            # Performance Metrics
            report.append("PERFORMANCE METRICS:")
            report.append(f"  Total Requests: {metrics.total_requests:,}")
            report.append(f"  Successful: {metrics.successful_requests:,}")
            report.append(f"  Failed: {metrics.failed_requests:,}")
            report.append(f"  Success Rate: {((metrics.successful_requests/metrics.total_requests)*100):.1f}%")
            report.append(f"  Duration: {metrics.test_duration_seconds:.1f}s")
            report.append("")
            
            # Response Time Analysis
            report.append("RESPONSE TIME ANALYSIS:")
            report.append(f"  Average: {metrics.average_response_time:.2f}s")
            report.append(f"  Minimum: {metrics.min_response_time:.2f}s")
            report.append(f"  Maximum: {metrics.max_response_time:.2f}s")
            report.append(f"  95th Percentile: {metrics.p95_response_time:.2f}s")
            report.append(f"  99th Percentile: {metrics.p99_response_time:.2f}s")
            report.append("")
            
            # Throughput Metrics
            report.append("THROUGHPUT METRICS:")
            report.append(f"  Requests/Second: {metrics.requests_per_second:.1f}")
            report.append(f"  Data Throughput: {metrics.throughput_mb_per_second:.2f} MB/s")
            report.append(f"  Concurrent Users: {metrics.concurrent_users}")
            report.append("")
            
            # System Resource Usage
            report.append("SYSTEM RESOURCES:")
            report.append(f"  Average Memory Usage: {metrics.memory_usage_mb:.1f} MB")
            report.append(f"  Average CPU Usage: {metrics.cpu_usage_percent:.1f}%")
            report.append("")
            
            # Performance Assessment
            assessment = LoadTestReporter._assess_performance(metrics)
            report.append(f"ASSESSMENT: {assessment}")
            report.append("")
        
        # Recommendations
        report.extend(LoadTestReporter._generate_recommendations(metrics_list))
        
        return "\n".join(report)
    
    @staticmethod
    def _assess_performance(metrics: LoadTestMetrics) -> str:
        """Assess performance based on metrics"""
        
        issues = []
        
        if metrics.error_rate > 0.05:  # >5% error rate
            issues.append("HIGH ERROR RATE")
        
        if metrics.average_response_time > 5.0:  # >5s average response time
            issues.append("SLOW RESPONSE TIMES")
        
        if metrics.p95_response_time > 10.0:  # >10s for 95th percentile
            issues.append("POOR P95 PERFORMANCE")
        
        if metrics.cpu_usage_percent > 80:  # >80% CPU usage
            issues.append("HIGH CPU USAGE")
        
        if metrics.memory_usage_mb > 2048:  # >2GB memory usage
            issues.append("HIGH MEMORY USAGE")
        
        if not issues:
            if metrics.requests_per_second > 10 and metrics.error_rate < 0.01:
                return "EXCELLENT - System performs well under load"
            elif metrics.requests_per_second > 5:
                return "GOOD - Acceptable performance"
            else:
                return "MODERATE - Performance within acceptable range"
        else:
            return f"ISSUES DETECTED: {', '.join(issues)}"
    
    @staticmethod
    def _generate_recommendations(metrics_list: List[LoadTestMetrics]) -> List[str]:
        """Generate performance improvement recommendations"""
        
        recommendations = []
        recommendations.append("RECOMMENDATIONS:")
        
        # Analyze patterns across all tests
        high_error_rate_tests = [m for m in metrics_list if m.error_rate > 0.05]
        slow_response_tests = [m for m in metrics_list if m.average_response_time > 3.0]
        high_cpu_tests = [m for m in metrics_list if m.cpu_usage_percent > 70]
        high_memory_tests = [m for m in metrics_list if m.memory_usage_mb > 1024]
        
        if high_error_rate_tests:
            recommendations.append("• HIGH PRIORITY: Investigate and fix error causes - error rate >5% detected")
            recommendations.append("  - Check logs for error patterns")
            recommendations.append("  - Verify database connection limits")
            recommendations.append("  - Review timeout configurations")
        
        if slow_response_tests:
            recommendations.append("• MEDIUM PRIORITY: Optimize response times - >3s average detected")
            recommendations.append("  - Implement caching for frequent requests")
            recommendations.append("  - Optimize database queries")
            recommendations.append("  - Consider async processing for heavy operations")
        
        if high_cpu_tests:
            recommendations.append("• MEDIUM PRIORITY: CPU optimization needed - >70% usage detected")
            recommendations.append("  - Profile CPU-intensive operations")
            recommendations.append("  - Consider horizontal scaling")
            recommendations.append("  - Implement request queuing")
        
        if high_memory_tests:
            recommendations.append("• MEDIUM PRIORITY: Memory optimization needed - >1GB usage detected")
            recommendations.append("  - Implement session cleanup")
            recommendations.append("  - Add memory limits and garbage collection")
            recommendations.append("  - Consider external storage for large objects")
        
        # General recommendations
        recommendations.append("• GENERAL IMPROVEMENTS:")
        recommendations.append("  - Implement Redis for session storage")
        recommendations.append("  - Add database connection pooling")
        recommendations.append("  - Set up load balancer for horizontal scaling")
        recommendations.append("  - Implement circuit breaker patterns")
        recommendations.append("  - Add comprehensive monitoring and alerting")
        
        return recommendations

def run_comprehensive_load_tests():
    """Run all load tests and generate comprehensive report"""
    
    print("🚀 Starting Comprehensive Load Testing Suite")
    print("=" * 60)
    
    # Initialize load tester
    load_tester = LoadTester()
    all_metrics = []
    
    try:
        # Test 1: Concurrent Users Test
        print("📊 Test 1: Concurrent Users (25 users for 2 minutes)")
        concurrent_metrics = load_tester.run_concurrent_user_test(
            concurrent_users=25,
            duration_seconds=120
        )
        all_metrics.append(concurrent_metrics)
        print(f"✅ Completed: {concurrent_metrics.requests_per_second:.1f} req/s, "
              f"{concurrent_metrics.error_rate:.1%} error rate")
        
        # Test 2: Spike Test  
        print("\n⚡ Test 2: Spike Test (50 users peak)")
        spike_metrics = load_tester.run_spike_test(max_users=50)
        all_metrics.append(spike_metrics)
        print(f"✅ Completed: Peak {spike_metrics.requests_per_second:.1f} req/s, "
              f"{spike_metrics.error_rate:.1%} error rate")
        
        # Test 3: Sustained Load Test
        print("\n⏱️ Test 3: Sustained Load (15 users for 5 minutes)")
        sustained_metrics = load_tester.run_sustained_load_test(
            users=15,
            duration_minutes=5
        )
        all_metrics.append(sustained_metrics)
        print(f"✅ Completed: {sustained_metrics.requests_per_second:.1f} req/s sustained, "
              f"{sustained_metrics.error_rate:.1%} error rate")
        
        # Test 4: Stress Test (commented out by default - can take very long)
        # print("\n💥 Test 4: Stress Test (Finding Breaking Point)")
        # stress_metrics = load_tester.run_stress_test()
        # all_metrics.append(stress_metrics)
        # print(f"✅ Completed: Breaking point analysis")
        
    except KeyboardInterrupt:
        print("\n⚠️ Load testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Load testing failed: {e}")
        return
    
    # Generate comprehensive report
    print("\n📋 Generating Comprehensive Load Test Report...")
    report = LoadTestReporter.generate_report(all_metrics)
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"load_test_report_{timestamp}.txt"
    
    with open(report_filename, 'w') as f:
        f.write(report)
    
    print(f"✅ Report saved to: {report_filename}")
    print("\n" + "="*60)
    print("LOAD TEST SUMMARY:")
    
    for metrics in all_metrics:
        print(f"• {metrics.test_name}:")
        print(f"  - {metrics.requests_per_second:.1f} req/s")
        print(f"  - {metrics.error_rate:.1%} error rate") 
        print(f"  - {metrics.average_response_time:.2f}s avg response")
    
    print("\n🎯 Load testing completed successfully!")
    return report_filename

if __name__ == "__main__":
    # Run comprehensive load tests
    report_file = run_comprehensive_load_tests()
    
    # Display key findings
    print(f"\n📊 Detailed results available in: {report_file}")
    print("\nNext steps:")
    print("1. Review the detailed report for performance bottlenecks")
    print("2. Implement recommended optimizations")
    print("3. Run load tests again to validate improvements")
    print("4. Set up monitoring and alerting based on baseline metrics")