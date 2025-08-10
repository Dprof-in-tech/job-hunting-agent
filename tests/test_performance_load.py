"""
Performance Load Testing for Multi-Agent Job Hunting System
Focused on testing core functionality under load without requiring server startup
"""

import threading
import time
import concurrent.futures
import statistics
import psutil
import random
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import tempfile
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from api.main import JobHuntingMultiAgent
from tools.security import SecurityManager
from api.ai_safety import AISafetyCoordinator
from tools.performance_evaluator import PerformanceEvaluator

@dataclass
class PerformanceResult:
    """Result of a performance test"""
    test_name: str
    execution_time: float
    memory_used_mb: float
    cpu_percent: float
    success: bool
    error_message: str = ""
    requests_completed: int = 0
    throughput_per_second: float = 0.0

class SystemPerformanceMonitor:
    """Monitor system performance during tests"""
    
    def __init__(self):
        self.monitoring = False
        self.start_memory = 0
        self.peak_memory = 0
        self.cpu_samples = []
        
    def start(self):
        """Start performance monitoring"""
        self.monitoring = True
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        self.cpu_samples = []
        
        # Start CPU monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitor_thread.start()
    
    def stop(self) -> Dict[str, float]:
        """Stop monitoring and return metrics"""
        self.monitoring = False
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        return {
            'memory_used_mb': current_memory - self.start_memory,
            'peak_memory_mb': self.peak_memory - self.start_memory,
            'avg_cpu_percent': statistics.mean(self.cpu_samples) if self.cpu_samples else 0
        }
    
    def _monitor_resources(self):
        """Monitor system resources in background"""
        while self.monitoring:
            try:
                # Monitor memory
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                self.peak_memory = max(self.peak_memory, current_memory)
                
                # Monitor CPU
                cpu_percent = psutil.Process().cpu_percent(interval=0.1)
                self.cpu_samples.append(cpu_percent)
                
                time.sleep(0.5)
            except:
                break

class MultiAgentLoadTester:
    """Load testing for multi-agent system components"""
    
    def __init__(self):
        self.multi_agent = None
        self.security_manager = SecurityManager()
        self.safety_coordinator = AISafetyCoordinator()
        self.performance_evaluator = PerformanceEvaluator()
        self.monitor = SystemPerformanceMonitor()
        
    def setup_system(self):
        """Initialize the multi-agent system"""
        try:
            self.multi_agent = JobHuntingMultiAgent()
            return True
        except Exception as e:
            print(f"Failed to initialize system: {e}")
            return False
    
    def generate_test_scenarios(self) -> List[Tuple[str, str]]:
        """Generate realistic test scenarios"""
        scenarios = [
            ("resume_analysis", "Analyze my resume and provide detailed feedback on strengths and weaknesses"),
            ("job_search", "Find software engineering jobs that match my background in Python and machine learning"),
            ("cv_creation", "Create an optimized CV for data science positions at tech companies"),
            ("comprehensive", "I need complete job hunting help - analyze my resume, find jobs, and create an optimized CV"),
            ("market_research", "Research the job market trends for product management roles in tech"),
            ("job_matching", "Compare my resume against specific job requirements and tell me which ones are the best fit"),
            ("skill_analysis", "What skills should I develop to be more competitive in the current job market"),
            ("industry_transition", "Help me transition from academia to industry data science roles")
        ]
        return scenarios
    
    def create_test_resume(self) -> str:
        """Create a temporary test resume file"""
        resume_content = """
John Doe
Software Engineer

EXPERIENCE:
- Senior Software Engineer at TechCorp (2020-2024)
  * Developed scalable web applications using Python, React, and PostgreSQL
  * Led a team of 5 engineers in building microservices architecture
  * Improved system performance by 40% through optimization initiatives
  
- Software Engineer at StartupXYZ (2018-2020)
  * Built full-stack applications using Django and React
  * Implemented CI/CD pipelines and automated testing
  * Collaborated with cross-functional teams on product development

EDUCATION:
- M.S. Computer Science, Stanford University (2018)
- B.S. Computer Science, UC Berkeley (2016)

SKILLS:
- Programming: Python, JavaScript, Java, SQL
- Frameworks: Django, React, Node.js, Flask
- Tools: Docker, Kubernetes, AWS, Git
- Databases: PostgreSQL, MongoDB, Redis
"""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write(resume_content)
        temp_file.close()
        
        return temp_file.name
    
    def test_concurrent_processing(self, concurrent_requests: int = 10, 
                                 duration_seconds: int = 30) -> PerformanceResult:
        """Test concurrent request processing"""
        print(f"🔄 Testing concurrent processing: {concurrent_requests} requests for {duration_seconds}s")
        
        if not self.multi_agent:
            if not self.setup_system():
                return PerformanceResult(
                    test_name="Concurrent Processing",
                    execution_time=0,
                    memory_used_mb=0,
                    cpu_percent=0,
                    success=False,
                    error_message="Failed to initialize system"
                )
        
        self.monitor.start()
        start_time = time.time()
        completed_requests = 0
        scenarios = self.generate_test_scenarios()
        resume_path = self.create_test_resume()
        
        try:
            def worker_thread(thread_id: int):
                """Worker thread for concurrent requests"""
                nonlocal completed_requests
                thread_start = time.time()
                requests_in_thread = 0
                
                while (time.time() - thread_start) < duration_seconds:
                    try:
                        # Select random scenario
                        scenario_type, prompt = random.choice(scenarios)
                        user_id = f"load_test_user_{thread_id}"
                        
                        # Process request
                        result = self.multi_agent.process_request(prompt, resume_path, user_id)
                        
                        if result and result.get('success'):
                            requests_in_thread += 1
                        
                        # Small delay to simulate realistic usage
                        time.sleep(random.uniform(0.1, 0.5))
                        
                    except Exception as e:
                        print(f"Worker {thread_id} error: {e}")
                        break
                
                completed_requests += requests_in_thread
                return requests_in_thread
            
            # Run concurrent workers
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
                futures = [executor.submit(worker_thread, i) for i in range(concurrent_requests)]
                
                # Wait for completion
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                    except Exception as e:
                        print(f"Thread execution error: {e}")
            
            execution_time = time.time() - start_time
            performance_metrics = self.monitor.stop()
            
            # Cleanup
            try:
                os.unlink(resume_path)
            except:
                pass
            
            return PerformanceResult(
                test_name="Concurrent Processing",
                execution_time=execution_time,
                memory_used_mb=performance_metrics['memory_used_mb'],
                cpu_percent=performance_metrics['avg_cpu_percent'],
                success=True,
                requests_completed=completed_requests,
                throughput_per_second=completed_requests / execution_time if execution_time > 0 else 0
            )
            
        except Exception as e:
            performance_metrics = self.monitor.stop()
            
            # Cleanup
            try:
                os.unlink(resume_path)
            except:
                pass
            
            return PerformanceResult(
                test_name="Concurrent Processing",
                execution_time=time.time() - start_time,
                memory_used_mb=performance_metrics.get('memory_used_mb', 0),
                cpu_percent=performance_metrics.get('avg_cpu_percent', 0),
                success=False,
                error_message=str(e)
            )
    
    def test_memory_usage_under_load(self, num_requests: int = 50) -> PerformanceResult:
        """Test memory usage patterns under sustained load"""
        print(f"🧠 Testing memory usage: {num_requests} sequential requests")
        
        if not self.multi_agent:
            if not self.setup_system():
                return PerformanceResult(
                    test_name="Memory Usage Test",
                    execution_time=0,
                    memory_used_mb=0,
                    cpu_percent=0,
                    success=False,
                    error_message="Failed to initialize system"
                )
        
        self.monitor.start()
        start_time = time.time()
        successful_requests = 0
        scenarios = self.generate_test_scenarios()
        resume_path = self.create_test_resume()
        
        try:
            for i in range(num_requests):
                # Select different scenarios to test various code paths
                scenario_type, prompt = scenarios[i % len(scenarios)]
                user_id = f"memory_test_user_{i}"
                
                try:
                    result = self.multi_agent.process_request(prompt, resume_path, user_id)
                    
                    if result and result.get('success'):
                        successful_requests += 1
                    
                    # Log progress
                    if (i + 1) % 10 == 0:
                        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                        print(f"  Progress: {i + 1}/{num_requests} requests, {current_memory:.1f} MB memory")
                
                except Exception as e:
                    print(f"Request {i} failed: {e}")
                    continue
            
            execution_time = time.time() - start_time
            performance_metrics = self.monitor.stop()
            
            # Cleanup
            try:
                os.unlink(resume_path)
            except:
                pass
            
            return PerformanceResult(
                test_name="Memory Usage Test",
                execution_time=execution_time,
                memory_used_mb=performance_metrics['memory_used_mb'],
                cpu_percent=performance_metrics['avg_cpu_percent'],
                success=True,
                requests_completed=successful_requests,
                throughput_per_second=successful_requests / execution_time if execution_time > 0 else 0
            )
            
        except Exception as e:
            performance_metrics = self.monitor.stop()
            
            # Cleanup
            try:
                os.unlink(resume_path)
            except:
                pass
            
            return PerformanceResult(
                test_name="Memory Usage Test",
                execution_time=time.time() - start_time,
                memory_used_mb=performance_metrics.get('memory_used_mb', 0),
                cpu_percent=performance_metrics.get('avg_cpu_percent', 0),
                success=False,
                error_message=str(e),
                requests_completed=successful_requests
            )
    
    def test_ai_safety_performance_impact(self, num_requests: int = 20) -> PerformanceResult:
        """Test performance impact of AI safety measures"""
        print(f"🛡️ Testing AI safety performance impact: {num_requests} requests")
        
        if not self.multi_agent:
            if not self.setup_system():
                return PerformanceResult(
                    test_name="AI Safety Performance",
                    execution_time=0,
                    memory_used_mb=0,
                    cpu_percent=0,
                    success=False,
                    error_message="Failed to initialize system"
                )
        
        self.monitor.start()
        start_time = time.time()
        successful_requests = 0
        resume_path = self.create_test_resume()
        
        try:
            # Test scenarios that trigger different AI safety checks
            safety_test_scenarios = [
                "Analyze this resume and tell me if I'm guaranteed to get hired at Google",  # Overconfidence detection
                "Find me jobs and tell me the exact salary I'll definitely receive",  # Hallucination detection  
                "Create a CV that emphasizes my young age and cultural fit",  # Bias detection
                "Give me career advice that will absolutely guarantee success",  # Ethical safeguards
            ]
            
            for i in range(num_requests):
                prompt = safety_test_scenarios[i % len(safety_test_scenarios)]
                user_id = f"safety_test_user_{i}"
                
                try:
                    result = self.multi_agent.process_request(prompt, resume_path, user_id)
                    
                    if result and result.get('success'):
                        successful_requests += 1
                        
                        # Check if AI safety measures were applied
                        if 'resume_analysis' in result and result['resume_analysis'].get('ai_safety'):
                            safety_data = result['resume_analysis']['ai_safety']
                            if safety_data.get('safety_warnings'):
                                print(f"  AI Safety triggered: {len(safety_data['safety_warnings'])} warnings")
                
                except Exception as e:
                    print(f"Safety test request {i} failed: {e}")
                    continue
            
            execution_time = time.time() - start_time
            performance_metrics = self.monitor.stop()
            
            # Cleanup
            try:
                os.unlink(resume_path)
            except:
                pass
            
            return PerformanceResult(
                test_name="AI Safety Performance",
                execution_time=execution_time,
                memory_used_mb=performance_metrics['memory_used_mb'],
                cpu_percent=performance_metrics['avg_cpu_percent'],
                success=True,
                requests_completed=successful_requests,
                throughput_per_second=successful_requests / execution_time if execution_time > 0 else 0
            )
            
        except Exception as e:
            performance_metrics = self.monitor.stop()
            
            # Cleanup
            try:
                os.unlink(resume_path)
            except:
                pass
            
            return PerformanceResult(
                test_name="AI Safety Performance",
                execution_time=time.time() - start_time,
                memory_used_mb=performance_metrics.get('memory_used_mb', 0),
                cpu_percent=performance_metrics.get('avg_cpu_percent', 0),
                success=False,
                error_message=str(e),
                requests_completed=successful_requests
            )
    
    def test_security_performance_impact(self, num_requests: int = 30) -> PerformanceResult:
        """Test performance impact of security measures"""
        print(f"🔒 Testing security performance impact: {num_requests} requests")
        
        self.monitor.start()
        start_time = time.time()
        successful_operations = 0
        
        try:
            # Test various security operations
            for i in range(num_requests):
                try:
                    # Test session creation and validation
                    session_data = self.security_manager.create_anonymous_session("127.0.0.1")
                    
                    # Test input sanitization
                    test_input = f"This is test input #{i} with <script>alert('xss')</script> malicious content"
                    sanitized = self.security_manager.sanitize_user_input(test_input)
                    
                    # Test file validation (simulated)
                    # Note: We're not actually uploading files to avoid filesystem overhead
                    
                    # Test data encryption/decryption
                    test_data = {"user_id": f"test_{i}", "data": f"sensitive data {i}"}
                    encrypted = self.security_manager.encrypt_sensitive_data(test_data)
                    decrypted = self.security_manager.decrypt_sensitive_data(encrypted)
                    
                    if decrypted == test_data:
                        successful_operations += 1
                
                except Exception as e:
                    print(f"Security operation {i} failed: {e}")
                    continue
            
            execution_time = time.time() - start_time
            performance_metrics = self.monitor.stop()
            
            return PerformanceResult(
                test_name="Security Performance",
                execution_time=execution_time,
                memory_used_mb=performance_metrics['memory_used_mb'],
                cpu_percent=performance_metrics['avg_cpu_percent'],
                success=True,
                requests_completed=successful_operations,
                throughput_per_second=successful_operations / execution_time if execution_time > 0 else 0
            )
            
        except Exception as e:
            performance_metrics = self.monitor.stop()
            
            return PerformanceResult(
                test_name="Security Performance",
                execution_time=time.time() - start_time,
                memory_used_mb=performance_metrics.get('memory_used_mb', 0),
                cpu_percent=performance_metrics.get('avg_cpu_percent', 0),
                success=False,
                error_message=str(e),
                requests_completed=successful_operations
            )

def run_performance_load_tests():
    """Run comprehensive performance load tests"""
    
    print("🚀 Starting Performance Load Testing Suite")
    print("=" * 60)
    
    load_tester = MultiAgentLoadTester()
    results = []
    
    # Test 1: Concurrent Processing
    try:
        concurrent_result = load_tester.test_concurrent_processing(
            concurrent_requests=5,  # Conservative for testing
            duration_seconds=30
        )
        results.append(concurrent_result)
        
        if concurrent_result.success:
            print(f"✅ Concurrent test: {concurrent_result.throughput_per_second:.2f} req/s, "
                  f"{concurrent_result.memory_used_mb:.1f} MB memory")
        else:
            print(f"❌ Concurrent test failed: {concurrent_result.error_message}")
            
    except Exception as e:
        print(f"❌ Concurrent test error: {e}")
    
    # Test 2: Memory Usage  
    try:
        memory_result = load_tester.test_memory_usage_under_load(num_requests=25)
        results.append(memory_result)
        
        if memory_result.success:
            print(f"✅ Memory test: {memory_result.memory_used_mb:.1f} MB used, "
                  f"{memory_result.requests_completed} requests completed")
        else:
            print(f"❌ Memory test failed: {memory_result.error_message}")
            
    except Exception as e:
        print(f"❌ Memory test error: {e}")
    
    # Test 3: AI Safety Performance Impact
    try:
        safety_result = load_tester.test_ai_safety_performance_impact(num_requests=15)
        results.append(safety_result)
        
        if safety_result.success:
            print(f"✅ AI Safety test: {safety_result.throughput_per_second:.2f} req/s, "
                  f"{safety_result.cpu_percent:.1f}% CPU")
        else:
            print(f"❌ AI Safety test failed: {safety_result.error_message}")
            
    except Exception as e:
        print(f"❌ AI Safety test error: {e}")
    
    # Test 4: Security Performance Impact
    try:
        security_result = load_tester.test_security_performance_impact(num_requests=20)
        results.append(security_result)
        
        if security_result.success:
            print(f"✅ Security test: {security_result.throughput_per_second:.2f} ops/s, "
                  f"{security_result.memory_used_mb:.1f} MB memory")
        else:
            print(f"❌ Security test failed: {security_result.error_message}")
            
    except Exception as e:
        print(f"❌ Security test error: {e}")
    
    # Generate Summary Report
    print("\n📊 PERFORMANCE LOAD TEST SUMMARY")
    print("=" * 60)
    
    successful_tests = [r for r in results if r.success]
    failed_tests = [r for r in results if not r.success]
    
    print(f"✅ Successful Tests: {len(successful_tests)}/{len(results)}")
    if failed_tests:
        print(f"❌ Failed Tests: {len(failed_tests)}")
        for test in failed_tests:
            print(f"   - {test.test_name}: {test.error_message}")
    
    if successful_tests:
        print(f"\n📈 PERFORMANCE METRICS:")
        avg_throughput = statistics.mean([r.throughput_per_second for r in successful_tests if r.throughput_per_second > 0])
        avg_memory = statistics.mean([r.memory_used_mb for r in successful_tests])
        avg_cpu = statistics.mean([r.cpu_percent for r in successful_tests])
        
        print(f"   • Average Throughput: {avg_throughput:.2f} requests/second")
        print(f"   • Average Memory Usage: {avg_memory:.1f} MB")
        print(f"   • Average CPU Usage: {avg_cpu:.1f}%")
        
        # Performance Assessment
        print(f"\n🎯 PERFORMANCE ASSESSMENT:")
        if avg_throughput > 2.0 and avg_memory < 500 and avg_cpu < 50:
            print("   EXCELLENT: System shows excellent performance characteristics")
        elif avg_throughput > 1.0 and avg_memory < 1000 and avg_cpu < 70:
            print("   GOOD: System performance is acceptable for production")
        elif avg_throughput > 0.5:
            print("   MODERATE: System performance needs optimization")
        else:
            print("   POOR: Significant performance improvements needed")
        
        print(f"\n📋 RECOMMENDATIONS:")
        if avg_memory > 500:
            print("   • Consider implementing memory optimization strategies")
        if avg_cpu > 60:
            print("   • CPU usage is high - consider optimizing computational operations")
        if avg_throughput < 1.0:
            print("   • Throughput is low - consider caching and async processing")
        
        print("   • Implement Redis for session storage to improve scalability")
        print("   • Add connection pooling for database operations")
        print("   • Consider horizontal scaling for production deployment")
    
    print(f"\n🏁 Performance load testing completed!")
    return results

if __name__ == "__main__":
    # Run the performance load tests
    results = run_performance_load_tests()
    
    print(f"\n🔍 Test Results Summary:")
    for result in results:
        status = "✅ PASS" if result.success else "❌ FAIL"
        print(f"   {status} {result.test_name}: "
              f"{result.throughput_per_second:.2f} req/s, "
              f"{result.memory_used_mb:.1f} MB, "
              f"{result.cpu_percent:.1f}% CPU")