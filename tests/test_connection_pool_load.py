"""
Connection Pool and Database Load Testing
Tests database connections, session management, and resource pooling under load
"""

import threading
import time
import concurrent.futures
import random
import statistics
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import queue
import sqlite3
import tempfile
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from api.security import SecurityManager
from api.ai_safety import AISafetyCoordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConnectionPoolResult:
    """Result of connection pool testing"""
    test_name: str
    max_concurrent_connections: int
    connection_success_rate: float
    avg_connection_time_ms: float
    connection_timeouts: int
    connection_errors: int
    total_operations: int
    operations_per_second: float
    memory_usage_mb: float
    pool_efficiency_score: float  # 0-100

class DatabaseConnectionTester:
    """Test database connection patterns and limits"""
    
    def __init__(self):
        self.test_db_path = None
        self.connection_pool = []
        self.pool_lock = threading.Lock()
        self.max_pool_size = 20
        self.connection_timeout = 5.0
        
    def setup_test_database(self):
        """Create a temporary test database"""
        self.test_db_path = tempfile.mktemp(suffix='.db')
        
        # Create test tables
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE job_results (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                status TEXT,
                result_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT,
                metric_value REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    
    def cleanup_test_database(self):
        """Clean up test database"""
        if self.test_db_path and os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
            except:
                pass
    
    def get_connection(self) -> Optional[sqlite3.Connection]:
        """Get a connection from the pool or create a new one"""
        with self.pool_lock:
            if self.connection_pool:
                return self.connection_pool.pop()
        
        try:
            conn = sqlite3.connect(self.test_db_path, timeout=self.connection_timeout)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None
    
    def return_connection(self, conn: sqlite3.Connection):
        """Return connection to the pool"""
        if conn:
            with self.pool_lock:
                if len(self.connection_pool) < self.max_pool_size:
                    self.connection_pool.append(conn)
                else:
                    conn.close()
    
    def test_concurrent_connections(self, concurrent_count: int = 50, 
                                  operations_per_thread: int = 20) -> ConnectionPoolResult:
        """Test concurrent database connections"""
        
        if not self.test_db_path:
            self.setup_test_database()
        
        results_queue = queue.Queue()
        start_time = time.time()
        
        def database_worker(worker_id: int):
            """Worker that performs database operations"""
            worker_results = {
                'successful_operations': 0,
                'failed_operations': 0,
                'connection_times': [],
                'operation_times': []
            }
            
            for op_num in range(operations_per_thread):
                # Get connection
                conn_start = time.time()
                conn = self.get_connection()
                conn_time = (time.time() - conn_start) * 1000  # Convert to ms
                
                if not conn:
                    worker_results['failed_operations'] += 1
                    continue
                
                worker_results['connection_times'].append(conn_time)
                
                # Perform database operation
                op_start = time.time()
                try:
                    cursor = conn.cursor()
                    
                    # Mix of different operations
                    if op_num % 4 == 0:  # Insert session
                        cursor.execute(
                            "INSERT INTO sessions (id, user_id, data) VALUES (?, ?, ?)",
                            (f"session_{worker_id}_{op_num}", f"user_{worker_id}", f"test_data_{op_num}")
                        )
                    elif op_num % 4 == 1:  # Insert job result
                        cursor.execute(
                            "INSERT INTO job_results (id, session_id, status, result_data) VALUES (?, ?, ?, ?)",
                            (f"job_{worker_id}_{op_num}", f"session_{worker_id}_{op_num}", "completed", f"result_{op_num}")
                        )
                    elif op_num % 4 == 2:  # Query sessions
                        cursor.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (f"user_{worker_id}",))
                        cursor.fetchone()
                    else:  # Insert metrics
                        cursor.execute(
                            "INSERT INTO performance_metrics (metric_name, metric_value) VALUES (?, ?)",
                            (f"test_metric_{worker_id}", random.uniform(0, 100))
                        )
                    
                    conn.commit()
                    worker_results['successful_operations'] += 1
                    
                except Exception as e:
                    worker_results['failed_operations'] += 1
                    logger.debug(f"Database operation failed: {e}")
                
                op_time = (time.time() - op_start) * 1000
                worker_results['operation_times'].append(op_time)
                
                # Return connection to pool
                self.return_connection(conn)
                
                # Small delay between operations
                time.sleep(random.uniform(0.01, 0.05))
            
            results_queue.put(worker_results)
        
        # Start concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(database_worker, i) for i in range(concurrent_count)]
            
            # Wait for all workers to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
        
        # Collect results
        all_connection_times = []
        all_operation_times = []
        total_successful = 0
        total_failed = 0
        connection_errors = 0
        timeouts = 0
        
        while not results_queue.empty():
            worker_result = results_queue.get()
            all_connection_times.extend(worker_result['connection_times'])
            all_operation_times.extend(worker_result['operation_times'])
            total_successful += worker_result['successful_operations']
            total_failed += worker_result['failed_operations']
        
        total_operations = total_successful + total_failed
        test_duration = time.time() - start_time
        
        # Calculate metrics
        success_rate = total_successful / total_operations if total_operations > 0 else 0
        avg_connection_time = statistics.mean(all_connection_times) if all_connection_times else 0
        operations_per_sec = total_operations / test_duration if test_duration > 0 else 0
        
        # Estimate memory usage (simplified)
        estimated_memory = len(self.connection_pool) * 0.5 + concurrent_count * 0.1  # MB estimate
        
        # Calculate pool efficiency
        if success_rate > 0.95 and avg_connection_time < 50:  # < 50ms connection time
            pool_efficiency = 90
        elif success_rate > 0.8 and avg_connection_time < 100:
            pool_efficiency = 70
        elif success_rate > 0.6:
            pool_efficiency = 50
        else:
            pool_efficiency = 30
        
        return ConnectionPoolResult(
            test_name="Concurrent Database Connections",
            max_concurrent_connections=concurrent_count,
            connection_success_rate=success_rate,
            avg_connection_time_ms=avg_connection_time,
            connection_timeouts=timeouts,
            connection_errors=connection_errors,
            total_operations=total_operations,
            operations_per_second=operations_per_sec,
            memory_usage_mb=estimated_memory,
            pool_efficiency_score=pool_efficiency
        )

class SessionManagerTester:
    """Test session management under load"""
    
    def __init__(self):
        self.security_manager = SecurityManager()
        self.active_sessions = {}
        self.session_lock = threading.Lock()
    
    def test_session_creation_load(self, concurrent_users: int = 100, 
                                 sessions_per_user: int = 5) -> ConnectionPoolResult:
        """Test session creation and management under load"""
        
        results_queue = queue.Queue()
        start_time = time.time()
        
        def session_worker(user_id: int):
            """Worker that creates and manages sessions"""
            worker_results = {
                'successful_sessions': 0,
                'failed_sessions': 0,
                'session_times': [],
                'validation_times': []
            }
            
            user_sessions = []
            
            for session_num in range(sessions_per_user):
                # Create session
                session_start = time.time()
                try:
                    client_ip = f"192.168.1.{(user_id % 254) + 1}"
                    session_data = self.security_manager.create_anonymous_session(client_ip)
                    
                    session_time = (time.time() - session_start) * 1000
                    worker_results['session_times'].append(session_time)
                    
                    if session_data and 'session_id' in session_data:
                        user_sessions.append(session_data)
                        worker_results['successful_sessions'] += 1
                        
                        # Store session for validation
                        with self.session_lock:
                            self.active_sessions[session_data['session_id']] = {
                                'user_id': user_id,
                                'created': time.time(),
                                'data': session_data
                            }
                    else:
                        worker_results['failed_sessions'] += 1
                
                except Exception as e:
                    worker_results['failed_sessions'] += 1
                    logger.debug(f"Session creation failed: {e}")
                
                # Validate random existing session
                if user_sessions and random.random() < 0.3:  # 30% chance
                    validation_start = time.time()
                    try:
                        random_session = random.choice(user_sessions)
                        is_valid = self.security_manager.validate_session_token(
                            random_session['token'], 
                            random_session['session_id']
                        )
                        validation_time = (time.time() - validation_start) * 1000
                        worker_results['validation_times'].append(validation_time)
                        
                    except Exception as e:
                        logger.debug(f"Session validation failed: {e}")
                
                # Small delay
                time.sleep(random.uniform(0.01, 0.1))
            
            results_queue.put(worker_results)
        
        # Run concurrent session workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(session_worker, i) for i in range(concurrent_users)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Session worker failed: {e}")
        
        # Collect results
        all_session_times = []
        all_validation_times = []
        total_successful = 0
        total_failed = 0
        
        while not results_queue.empty():
            worker_result = results_queue.get()
            all_session_times.extend(worker_result['session_times'])
            all_validation_times.extend(worker_result['validation_times'])
            total_successful += worker_result['successful_sessions']
            total_failed += worker_result['failed_sessions']
        
        total_operations = total_successful + total_failed
        test_duration = time.time() - start_time
        
        # Calculate metrics
        success_rate = total_successful / total_operations if total_operations > 0 else 0
        avg_session_time = statistics.mean(all_session_times) if all_session_times else 0
        operations_per_sec = total_operations / test_duration if test_duration > 0 else 0
        
        # Estimate memory usage for sessions
        estimated_memory = len(self.active_sessions) * 0.001  # ~1KB per session estimate
        
        # Calculate efficiency
        if success_rate > 0.95 and avg_session_time < 20:  # < 20ms session creation
            efficiency = 95
        elif success_rate > 0.9 and avg_session_time < 50:
            efficiency = 80
        elif success_rate > 0.8:
            efficiency = 60
        else:
            efficiency = 40
        
        
        return ConnectionPoolResult(
            test_name="Session Management Load",
            max_concurrent_connections=concurrent_users,
            connection_success_rate=success_rate,
            avg_connection_time_ms=avg_session_time,
            connection_timeouts=0,
            connection_errors=total_failed,
            total_operations=total_operations,
            operations_per_second=operations_per_sec,
            memory_usage_mb=estimated_memory,
            pool_efficiency_score=efficiency
        )

class AISafetyLoadTester:
    """Test AI safety components under load"""
    
    def __init__(self):
        self.safety_coordinator = AISafetyCoordinator()
    
    def test_ai_safety_concurrent_load(self, concurrent_requests: int = 25, 
                                     operations_per_request: int = 10) -> ConnectionPoolResult:
        """Test AI safety operations under concurrent load"""
        
        results_queue = queue.Queue()
        start_time = time.time()
        
        def safety_worker(worker_id: int):
            """Worker that performs AI safety operations"""
            worker_results = {
                'successful_operations': 0,
                'failed_operations': 0,
                'operation_times': []
            }
            
            for op_num in range(operations_per_request):
                op_start = time.time()
                
                try:
                    # Rotate through different AI safety operations
                    if op_num % 3 == 0:  # Bias detection
                        result = self.safety_coordinator.fairness_monitor.detect_resume_scoring_bias(
                            resume_text=f"John Doe {worker_id} has excellent technical skills in Python and machine learning.",
                            score=random.uniform(60, 95),
                            recommendations=[f"Improve skill {op_num}", "Add more experience"]
                        )
                        success = result.bias_type is not None
                        
                    elif op_num % 3 == 1:  # Hallucination detection
                        test_data = {
                            'job_listings': [
                                {'title': f'Engineer {worker_id}', 'salary': f'${random.randint(80, 150)}k-{random.randint(120, 200)}k'}
                            ],
                            'role': 'software_engineer'
                        }
                        result = self.safety_coordinator.hallucination_detector.check_salary_claims(test_data)
                        success = hasattr(result, 'verified')
                        
                    else:  # Job listing bias detection
                        job_text = f"We're looking for a rockstar developer {worker_id} to join our young team"
                        result = self.safety_coordinator.fairness_monitor.detect_job_listing_bias(job_text, "software_engineer")
                        success = result.bias_type is not None
                    
                    if success:
                        worker_results['successful_operations'] += 1
                    else:
                        worker_results['failed_operations'] += 1
                
                except Exception as e:
                    worker_results['failed_operations'] += 1
                    logger.debug(f"AI safety operation failed: {e}")
                
                op_time = (time.time() - op_start) * 1000
                worker_results['operation_times'].append(op_time)
                
                # Small delay between operations
                time.sleep(random.uniform(0.01, 0.03))
            
            results_queue.put(worker_results)
        
        # Run concurrent AI safety workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(safety_worker, i) for i in range(concurrent_requests)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"AI safety worker failed: {e}")
        
        # Collect results
        all_operation_times = []
        total_successful = 0
        total_failed = 0
        
        while not results_queue.empty():
            worker_result = results_queue.get()
            all_operation_times.extend(worker_result['operation_times'])
            total_successful += worker_result['successful_operations']
            total_failed += worker_result['failed_operations']
        
        total_operations = total_successful + total_failed
        test_duration = time.time() - start_time
        
        # Calculate metrics
        success_rate = total_successful / total_operations if total_operations > 0 else 0
        avg_operation_time = statistics.mean(all_operation_times) if all_operation_times else 0
        operations_per_sec = total_operations / test_duration if test_duration > 0 else 0
        
        # Estimate memory usage
        estimated_memory = concurrent_requests * 0.5  # ~500KB per concurrent safety check
        
        # Calculate efficiency
        if success_rate > 0.95 and avg_operation_time < 100:  # < 100ms per operation
            efficiency = 90
        elif success_rate > 0.8 and avg_operation_time < 200:
            efficiency = 75
        elif success_rate > 0.6:
            efficiency = 50
        else:
            efficiency = 30
        
        return ConnectionPoolResult(
            test_name="AI Safety Concurrent Load",
            max_concurrent_connections=concurrent_requests,
            connection_success_rate=success_rate,
            avg_connection_time_ms=avg_operation_time,
            connection_timeouts=0,
            connection_errors=total_failed,
            total_operations=total_operations,
            operations_per_second=operations_per_sec,
            memory_usage_mb=estimated_memory,
            pool_efficiency_score=efficiency
        )

def run_connection_pool_load_tests():
    """Run comprehensive connection pool and resource load tests"""
    
    print("🔌 Starting Connection Pool & Resource Load Testing")
    print("=" * 60)
    
    results = []
    
    # Test 1: Database Connection Pool
    try:
        print("💾 Test 1: Database connection pool load testing...")
        db_tester = DatabaseConnectionTester()
        db_result = db_tester.test_concurrent_connections(concurrent_count=30, operations_per_thread=15)
        results.append(db_result)
        
        print(f"✅ Database test: {db_result.connection_success_rate:.1%} success rate, "
              f"{db_result.avg_connection_time_ms:.1f}ms avg connection time")
        
        db_tester.cleanup_test_database()
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
    
    # Test 2: Session Management Load
    try:
        print(f"\n🔐 Test 2: Session management load testing...")
        session_tester = SessionManagerTester()
        session_result = session_tester.test_session_creation_load(concurrent_users=50, sessions_per_user=3)
        results.append(session_result)
        
        print(f"✅ Session test: {session_result.connection_success_rate:.1%} success rate, "
              f"{session_result.operations_per_second:.1f} ops/sec")
              
    except Exception as e:
        print(f"❌ Session management test failed: {e}")
    
    # Test 3: AI Safety Load
    try:
        print(f"\n🛡️ Test 3: AI safety components load testing...")
        safety_tester = AISafetyLoadTester()
        safety_result = safety_tester.test_ai_safety_concurrent_load(concurrent_requests=20, operations_per_request=8)
        results.append(safety_result)
        
        print(f"✅ AI Safety test: {safety_result.connection_success_rate:.1%} success rate, "
              f"{safety_result.avg_connection_time_ms:.1f}ms avg operation time")
              
    except Exception as e:
        print(f"❌ AI safety load test failed: {e}")
    
    # Generate comprehensive report
    print(f"\n📊 CONNECTION POOL & RESOURCE LOAD TEST REPORT")
    print("=" * 60)
    
    if results:
        successful_tests = [r for r in results if r.pool_efficiency_score > 0]
        
        print(f"📈 OVERALL RESULTS:")
        print(f"   • Tests Completed: {len(successful_tests)}/{len(results)}")
        
        if successful_tests:
            avg_success_rate = statistics.mean([r.connection_success_rate for r in successful_tests])
            avg_efficiency = statistics.mean([r.pool_efficiency_score for r in successful_tests])
            total_operations = sum([r.total_operations for r in results])
            avg_ops_per_sec = statistics.mean([r.operations_per_second for r in successful_tests if r.operations_per_second > 0])
            
            print(f"   • Average Success Rate: {avg_success_rate:.1%}")
            print(f"   • Average Efficiency Score: {avg_efficiency:.0f}/100")
            print(f"   • Total Operations: {total_operations:,}")
            print(f"   • Average Throughput: {avg_ops_per_sec:.1f} ops/second")
            
            # Detailed results
            print(f"\n🔍 DETAILED RESULTS:")
            for result in results:
                print(f"\n   📋 {result.test_name}:")
                print(f"      • Success Rate: {result.connection_success_rate:.1%}")
                print(f"      • Efficiency Score: {result.pool_efficiency_score:.0f}/100")
                print(f"      • Avg Response Time: {result.avg_connection_time_ms:.1f}ms")
                print(f"      • Throughput: {result.operations_per_second:.1f} ops/sec")
                print(f"      • Memory Usage: {result.memory_usage_mb:.1f}MB")
                if result.connection_errors > 0:
                    print(f"      • Errors: {result.connection_errors}")
            
            # Assessment
            print(f"\n🎯 RESOURCE MANAGEMENT ASSESSMENT:")
            if avg_efficiency >= 80 and avg_success_rate >= 0.9:
                print("   ✅ EXCELLENT: Resource management is highly efficient")
            elif avg_efficiency >= 60 and avg_success_rate >= 0.8:
                print("   ✅ GOOD: Resource management is adequate for production")
            elif avg_efficiency >= 40:
                print("   ⚠️ FAIR: Resource management needs optimization")
            else:
                print("   ❌ POOR: Significant resource management improvements needed")
            
            # Recommendations
            print(f"\n💡 RECOMMENDATIONS:")
            if avg_success_rate < 0.9:
                print("   • Implement connection retry logic with exponential backoff")
                print("   • Add connection health checks and automatic recovery")
            
            if any(r.avg_connection_time_ms > 50 for r in successful_tests):
                print("   • Optimize connection establishment and pooling strategies")
                print("   • Consider implementing connection pre-warming")
            
            if any(r.memory_usage_mb > 100 for r in successful_tests):
                print("   • Implement memory usage monitoring and limits")
                print("   • Add automatic cleanup for idle resources")
            
            print("   • Implement Redis for distributed session management")
            print("   • Add comprehensive monitoring for resource usage")
            print("   • Consider implementing circuit breaker patterns")
            
            # Production readiness
            print(f"\n🚀 PRODUCTION READINESS:")
            if avg_efficiency >= 70 and avg_success_rate >= 0.85:
                print("   ✅ READY: Resource management suitable for production")
            elif avg_efficiency >= 50 and avg_success_rate >= 0.7:
                print("   ⚠️ CAUTION: Implement optimizations before high-load production")
            else:
                print("   ❌ NOT READY: Significant improvements required")
        
    else:
        print("❌ No successful tests completed")
    
    print(f"\n🏁 Connection pool and resource load testing completed!")
    return results

if __name__ == "__main__":
    # Run comprehensive connection pool load tests
    results = run_connection_pool_load_tests()
    
    print(f"\n📋 SUMMARY:")
    for result in results:
        efficiency_emoji = "🟢" if result.pool_efficiency_score >= 70 else "🟡" if result.pool_efficiency_score >= 40 else "🔴"
        print(f"   {efficiency_emoji} {result.test_name}:")
        print(f"      Efficiency: {result.pool_efficiency_score:.0f}/100 | Success: {result.connection_success_rate:.1%} | {result.operations_per_second:.1f} ops/sec")