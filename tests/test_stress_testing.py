"""
Stress Testing Suite for Multi-Agent Job Hunting System
Tests system limits, breaking points, and recovery capabilities
"""

import threading
import time
import random
import concurrent.futures
import queue
import statistics
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from api.main import JobHuntingMultiAgent
from api.security import SecurityManager
from api.ai_safety import AISafetyCoordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StressTestResult:
    """Result of a stress test"""
    test_name: str
    breaking_point: Optional[int]
    max_successful_load: int
    failure_rate_at_breaking_point: float
    avg_response_time_at_limit: float
    memory_at_breaking_point_mb: float
    recovery_time_seconds: float
    total_requests_processed: int
    system_stability_score: float  # 0-100
    recommendations: List[str]

class SystemBreakingPointFinder:
    """Find the breaking point of various system components"""
    
    def __init__(self):
        self.multi_agent = None
        self.security_manager = SecurityManager()
        self.results_queue = queue.Queue()
        
    def setup_system(self):
        """Initialize system for testing"""
        try:
            self.multi_agent = JobHuntingMultiAgent()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            return False
    
    def find_concurrent_user_breaking_point(self) -> StressTestResult:
        """Find maximum concurrent users the system can handle"""
        
        if not self.setup_system():
            return self._create_failed_result("Concurrent User Breaking Point", "System initialization failed")
        
        user_levels = [1, 2, 5, 10, 15, 25, 40, 60, 80, 100, 150, 200]
        breaking_point = None
        max_successful = 0
        total_processed = 0
        test_results = []
        
        for user_count in user_levels:
            
            # Run test for this user count
            success_rate, avg_response_time, memory_usage, requests_processed = self._test_concurrent_load(
                user_count, duration_seconds=30
            )
            
            total_processed += requests_processed
            test_results.append({
                'user_count': user_count,
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'memory_usage': memory_usage,
                'requests_processed': requests_processed
            })
            
            
            # Check if system is failing (>20% failure rate or >10s response time)
            if success_rate < 0.8 or avg_response_time > 10.0:
                breaking_point = user_count
                logger.warning(f"Breaking point found at {user_count} users")
                break
            else:
                max_successful = user_count
        
        # Calculate system stability score
        stability_scores = []
        for result in test_results:
            if result['success_rate'] > 0.95 and result['avg_response_time'] < 3.0:
                stability_scores.append(100)
            elif result['success_rate'] > 0.8 and result['avg_response_time'] < 5.0:
                stability_scores.append(80)
            elif result['success_rate'] > 0.5:
                stability_scores.append(60)
            else:
                stability_scores.append(30)
        
        avg_stability = statistics.mean(stability_scores) if stability_scores else 0
        
        # Generate recommendations
        recommendations = self._generate_concurrency_recommendations(test_results, breaking_point)
        
        return StressTestResult(
            test_name="Concurrent User Breaking Point",
            breaking_point=breaking_point,
            max_successful_load=max_successful,
            failure_rate_at_breaking_point=(1 - test_results[-1]['success_rate']) if test_results else 0,
            avg_response_time_at_limit=test_results[-1]['avg_response_time'] if test_results else 0,
            memory_at_breaking_point_mb=test_results[-1]['memory_usage'] if test_results else 0,
            recovery_time_seconds=0.0,  # Not applicable for this test
            total_requests_processed=total_processed,
            system_stability_score=avg_stability,
            recommendations=recommendations
        )
    
    def find_memory_breaking_point(self) -> StressTestResult:
        """Find memory limits by processing many requests sequentially"""
        
        if not self.setup_system():
            return self._create_failed_result("Memory Breaking Point", "System initialization failed")
        
        import psutil
        import gc
        
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        current_memory = start_memory
        max_safe_memory = start_memory + 2048  # 2GB limit
        
        request_batches = [10, 25, 50, 100, 200, 300, 500, 750, 1000]
        breaking_point = None
        max_successful_batch = 0
        total_processed = 0
        memory_results = []
        
        for batch_size in request_batches:
            
            batch_start_memory = process.memory_info().rss / 1024 / 1024
            successful_requests = 0
            
            # Process batch of requests
            for i in range(batch_size):
                try:
                    prompt = f"Test request {i} - analyze resume and provide feedback"
                    result = self.multi_agent.process_request(prompt, "", f"memory_test_user_{i}")
                    
                    if result and result.get('success'):
                        successful_requests += 1
                    
                    # Check memory periodically
                    if i % 10 == 0:
                        current_memory = process.memory_info().rss / 1024 / 1024
                        if current_memory > max_safe_memory:
                            logger.warning(f"Memory limit exceeded: {current_memory:.1f} MB")
                            breaking_point = batch_size
                            break
                            
                except Exception as e:
                    logger.error(f"Request {i} failed: {e}")
                    break
            
            batch_end_memory = process.memory_info().rss / 1024 / 1024
            memory_used = batch_end_memory - batch_start_memory
            success_rate = successful_requests / batch_size if batch_size > 0 else 0
            
            memory_results.append({
                'batch_size': batch_size,
                'memory_used_mb': memory_used,
                'total_memory_mb': batch_end_memory,
                'success_rate': success_rate,
                'successful_requests': successful_requests
            })
            
            total_processed += successful_requests
            
                       f"{batch_end_memory:.1f} MB total, {success_rate:.1%} success")
            
            # Force garbage collection
            gc.collect()
            
            # Check if we hit memory limit or too many failures
            if current_memory > max_safe_memory or success_rate < 0.7:
                breaking_point = batch_size
                logger.warning(f"Memory breaking point at {batch_size} requests")
                break
            else:
                max_successful_batch = batch_size
        
        # Calculate stability score based on memory efficiency
        if memory_results:
            last_result = memory_results[-1]
            memory_per_request = last_result['memory_used_mb'] / last_result['batch_size']
            
            if memory_per_request < 1.0:  # < 1MB per request
                stability_score = 90
            elif memory_per_request < 5.0:  # < 5MB per request
                stability_score = 70
            elif memory_per_request < 10.0:  # < 10MB per request
                stability_score = 50
            else:
                stability_score = 30
        else:
            stability_score = 0
        
        recommendations = self._generate_memory_recommendations(memory_results)
        
        return StressTestResult(
            test_name="Memory Breaking Point",
            breaking_point=breaking_point,
            max_successful_load=max_successful_batch,
            failure_rate_at_breaking_point=0.0,  # Not applicable
            avg_response_time_at_limit=0.0,  # Not applicable
            memory_at_breaking_point_mb=current_memory - start_memory,
            recovery_time_seconds=0.0,
            total_requests_processed=total_processed,
            system_stability_score=stability_score,
            recommendations=recommendations
        )
    
    def test_system_recovery(self) -> StressTestResult:
        """Test system recovery after overload"""
        
        if not self.setup_system():
            return self._create_failed_result("System Recovery", "System initialization failed")
        
        # Phase 1: Establish baseline
        baseline_success, baseline_time, _, baseline_processed = self._test_concurrent_load(5, 30)
        
        # Phase 2: Overload system
        overload_start = time.time()
        overload_success, overload_time, overload_memory, overload_processed = self._test_concurrent_load(50, 60)
        overload_duration = time.time() - overload_start
        
        
        # Phase 3: Recovery period - gradual reduction
        recovery_start = time.time()
        
        recovery_phases = [
            (25, 30),  # Moderate load
            (10, 30),  # Light load
            (5, 30),   # Baseline load
        ]
        
        recovery_results = []
        for users, duration in recovery_phases:
            phase_start = time.time()
            success, response_time, memory, processed = self._test_concurrent_load(users, duration)
            
            recovery_results.append({
                'users': users,
                'success_rate': success,
                'response_time': response_time,
                'recovery_ratio': success / baseline_success if baseline_success > 0 else 0
            })
            
            
            if success >= baseline_success * 0.9:  # Within 90% of baseline
                recovery_time = time.time() - recovery_start
                break
        else:
            recovery_time = time.time() - recovery_start
            logger.warning(f"System did not fully recover after {recovery_time:.1f} seconds")
        
        # Calculate recovery metrics
        final_recovery = recovery_results[-1] if recovery_results else {'recovery_ratio': 0}
        recovery_ratio = final_recovery['recovery_ratio']
        
        if recovery_ratio >= 0.95:
            stability_score = 95
        elif recovery_ratio >= 0.8:
            stability_score = 80
        elif recovery_ratio >= 0.5:
            stability_score = 60
        else:
            stability_score = 30
        
        recommendations = [
            "Implement circuit breaker patterns for graceful degradation",
            "Add automatic scaling based on load metrics",
            "Implement request queuing for smooth load handling",
            "Add health checks and automatic recovery mechanisms"
        ]
        
        total_processed = baseline_processed + overload_processed + sum(
            self._estimate_requests_processed(r['users'], 30) for r in recovery_results
        )
        
        return StressTestResult(
            test_name="System Recovery Test",
            breaking_point=None,
            max_successful_load=50,  # The overload level
            failure_rate_at_breaking_point=1 - overload_success,
            avg_response_time_at_limit=overload_time,
            memory_at_breaking_point_mb=overload_memory,
            recovery_time_seconds=recovery_time,
            total_requests_processed=total_processed,
            system_stability_score=stability_score,
            recommendations=recommendations
        )
    
    def _test_concurrent_load(self, user_count: int, duration_seconds: int) -> Tuple[float, float, float, int]:
        """Test concurrent load and return success_rate, avg_response_time, memory_usage, requests_processed"""
        import psutil
        
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        results = []
        start_time = time.time()
        
        def user_worker():
            worker_results = []
            end_time = start_time + duration_seconds
            
            while time.time() < end_time:
                request_start = time.time()
                success = False
                
                try:
                    prompt = "Analyze my resume and provide feedback"
                    result = self.multi_agent.process_request(prompt, "", f"stress_test_user_{threading.current_thread().ident}")
                    success = result and result.get('success', False)
                    
                except Exception as e:
                    logger.debug(f"Request failed: {e}")
                
                response_time = time.time() - request_start
                worker_results.append({'success': success, 'response_time': response_time})
                
                # Small delay to prevent overwhelming
                time.sleep(random.uniform(0.1, 0.3))
            
            return worker_results
        
        # Run concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=user_count) as executor:
            futures = [executor.submit(user_worker) for _ in range(user_count)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    worker_results = future.result()
                    results.extend(worker_results)
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
        
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_used = end_memory - start_memory
        
        if not results:
            return 0.0, 0.0, memory_used, 0
        
        successful_results = [r for r in results if r['success']]
        success_rate = len(successful_results) / len(results)
        avg_response_time = statistics.mean([r['response_time'] for r in results])
        
        return success_rate, avg_response_time, memory_used, len(results)
    
    def _estimate_requests_processed(self, users: int, duration: int) -> int:
        """Estimate number of requests processed based on users and duration"""
        # Rough estimate: each user makes ~1 request every 2 seconds
        return users * duration // 2
    
    def _generate_concurrency_recommendations(self, results: List[Dict], breaking_point: Optional[int]) -> List[str]:
        """Generate recommendations based on concurrency test results"""
        recommendations = []
        
        if breaking_point and breaking_point < 50:
            recommendations.extend([
                "LOW CONCURRENCY LIMIT: Implement connection pooling and async processing",
                "Add request queuing to handle traffic spikes",
                "Consider implementing horizontal scaling"
            ])
        elif breaking_point and breaking_point < 100:
            recommendations.extend([
                "MODERATE CONCURRENCY: Optimize database connections and caching",
                "Implement load balancing for better distribution"
            ])
        
        if results:
            high_response_time_tests = [r for r in results if r['avg_response_time'] > 3.0]
            if high_response_time_tests:
                recommendations.append("SLOW RESPONSE TIMES: Optimize AI model inference and caching")
        
        recommendations.extend([
            "Implement circuit breaker patterns for graceful degradation",
            "Add comprehensive monitoring and alerting",
            "Consider implementing rate limiting per user/IP"
        ])
        
        return recommendations
    
    def _generate_memory_recommendations(self, results: List[Dict]) -> List[str]:
        """Generate recommendations based on memory test results"""
        recommendations = []
        
        if results:
            last_result = results[-1]
            memory_per_request = last_result['memory_used_mb'] / last_result['batch_size']
            
            if memory_per_request > 10.0:
                recommendations.extend([
                    "CRITICAL: Very high memory usage per request (>10MB)",
                    "Implement aggressive garbage collection",
                    "Review and optimize data structures",
                    "Consider streaming responses for large data"
                ])
            elif memory_per_request > 5.0:
                recommendations.extend([
                    "HIGH: Memory usage per request >5MB - optimization needed",
                    "Implement session cleanup and data compression"
                ])
        
        recommendations.extend([
            "Implement Redis for external session storage",
            "Add memory monitoring and automatic cleanup",
            "Consider implementing response caching",
            "Add memory limits and proper error handling"
        ])
        
        return recommendations
    
    def _create_failed_result(self, test_name: str, error_message: str) -> StressTestResult:
        """Create a failed test result"""
        return StressTestResult(
            test_name=test_name,
            breaking_point=None,
            max_successful_load=0,
            failure_rate_at_breaking_point=1.0,
            avg_response_time_at_limit=0.0,
            memory_at_breaking_point_mb=0.0,
            recovery_time_seconds=0.0,
            total_requests_processed=0,
            system_stability_score=0.0,
            recommendations=[f"Failed to run test: {error_message}"]
        )

def run_stress_testing_suite():
    """Run comprehensive stress testing suite"""
    
    print("💥 Starting Comprehensive Stress Testing Suite")
    print("=" * 60)
    
    stress_finder = SystemBreakingPointFinder()
    results = []
    
    # Test 1: Find concurrent user breaking point
    try:
        print("🔍 Test 1: Finding concurrent user breaking point...")
        concurrent_result = stress_finder.find_concurrent_user_breaking_point()
        results.append(concurrent_result)
        
        if concurrent_result.breaking_point:
            print(f"⚠️ Breaking point found: {concurrent_result.breaking_point} concurrent users")
            print(f"   Max stable load: {concurrent_result.max_successful_load} users")
        else:
            print(f"✅ No breaking point found. Max tested: {concurrent_result.max_successful_load} users")
            
    except Exception as e:
        print(f"❌ Concurrent user test failed: {e}")
    
    # Test 2: Find memory breaking point
    try:
        print(f"\n🧠 Test 2: Finding memory breaking point...")
        memory_result = stress_finder.find_memory_breaking_point()
        results.append(memory_result)
        
        if memory_result.breaking_point:
            print(f"⚠️ Memory breaking point: {memory_result.breaking_point} requests")
            print(f"   Memory used: {memory_result.memory_at_breaking_point_mb:.1f} MB")
        else:
            print(f"✅ No memory breaking point found. Max tested: {memory_result.max_successful_load} requests")
            
    except Exception as e:
        print(f"❌ Memory test failed: {e}")
    
    # Test 3: System recovery test
    try:
        print(f"\n🔄 Test 3: Testing system recovery capabilities...")
        recovery_result = stress_finder.test_system_recovery()
        results.append(recovery_result)
        
        print(f"✅ Recovery test completed:")
        print(f"   Recovery time: {recovery_result.recovery_time_seconds:.1f} seconds")
        print(f"   System stability: {recovery_result.system_stability_score:.0f}/100")
        
    except Exception as e:
        print(f"❌ Recovery test failed: {e}")
    
    # Generate comprehensive report
    print(f"\n📊 STRESS TEST COMPREHENSIVE REPORT")
    print("=" * 60)
    
    successful_tests = [r for r in results if r.system_stability_score > 0]
    
    if successful_tests:
        avg_stability = statistics.mean([r.system_stability_score for r in successful_tests])
        total_processed = sum([r.total_requests_processed for r in results])
        
        print(f"📈 OVERALL SYSTEM ASSESSMENT:")
        print(f"   • Tests Completed: {len(successful_tests)}/{len(results)}")
        print(f"   • Total Requests Processed: {total_processed:,}")
        print(f"   • Average System Stability: {avg_stability:.0f}/100")
        
        if avg_stability >= 80:
            print(f"   🎯 VERDICT: EXCELLENT - System handles stress very well")
        elif avg_stability >= 60:
            print(f"   🎯 VERDICT: GOOD - System handles moderate stress acceptably")
        elif avg_stability >= 40:
            print(f"   🎯 VERDICT: FAIR - System needs optimization for production")
        else:
            print(f"   🎯 VERDICT: POOR - Significant improvements needed")
        
        print(f"\n🔍 DETAILED RESULTS:")
        for result in results:
            print(f"\n   📋 {result.test_name}:")
            print(f"      • Stability Score: {result.system_stability_score:.0f}/100")
            if result.breaking_point:
                print(f"      • Breaking Point: {result.breaking_point}")
            print(f"      • Max Stable Load: {result.max_successful_load}")
            if result.recovery_time_seconds > 0:
                print(f"      • Recovery Time: {result.recovery_time_seconds:.1f}s")
        
        print(f"\n💡 PRIORITY RECOMMENDATIONS:")
        all_recommendations = []
        for result in results:
            all_recommendations.extend(result.recommendations[:2])  # Top 2 from each test
        
        for i, rec in enumerate(set(all_recommendations)[:5], 1):  # Top 5 unique recommendations
            print(f"   {i}. {rec}")
        
        print(f"\n🎯 PRODUCTION READINESS:")
        if avg_stability >= 70 and all(r.breaking_point is None or r.breaking_point > 20 for r in results):
            print("   ✅ READY: System can handle production load with monitoring")
        elif avg_stability >= 50:
            print("   ⚠️ CAUTION: Implement recommended optimizations before production")
        else:
            print("   ❌ NOT READY: Significant improvements required for production")
    
    else:
        print("❌ No successful stress tests completed")
    
    print(f"\n🏁 Stress testing completed!")
    return results

if __name__ == "__main__":
    # Run comprehensive stress testing
    results = run_stress_testing_suite()
    
    # Summary for quick reference
    print(f"\n📋 QUICK SUMMARY:")
    for result in results:
        stability_emoji = "🟢" if result.system_stability_score >= 70 else "🟡" if result.system_stability_score >= 40 else "🔴"
        print(f"   {stability_emoji} {result.test_name}: {result.system_stability_score:.0f}/100")
        
        if result.breaking_point:
            print(f"      ⚠️ Breaking point at: {result.breaking_point}")
        
        if result.total_requests_processed > 0:
            print(f"      📊 Processed: {result.total_requests_processed:,} requests")