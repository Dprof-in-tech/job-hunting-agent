#!/usr/bin/env python3
"""
System Test Script - Tests core functionality without requiring OpenAI API
"""

import os
import sys
import tempfile
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(__file__))

def test_ai_safety():
    """Test AI safety components"""
    print("🛡️ Testing AI Safety Components...")
    
    try:
        from api.ai_safety import AISafetyCoordinator
        
        safety = AISafetyCoordinator()
        print("   ✅ AI Safety Coordinator initialized")
        
        # Test bias detection
        bias_result = safety.fairness_monitor.detect_resume_scoring_bias(
            resume_text="John Smith has excellent technical skills in Python and machine learning",
            score=85.0,
            recommendations=["Add more projects", "Improve formatting"]
        )
        print(f"   ✅ Bias detection: {bias_result.bias_type}, detected={bias_result.bias_detected}")
        
        # Test hallucination detection
        hall_check = safety.hallucination_detector.check_salary_claims({
            'job_listings': [
                {'title': 'Software Engineer', 'salary': '80000-120000'},
                {'title': 'Senior Developer', 'salary': '100000-150000'}
            ]
        })
        print(f"   ✅ Hallucination detection: verified={hall_check.verified}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ AI Safety test failed: {e}")
        return False

def test_security():
    """Test security components"""
    print("\n🔒 Testing Security Components...")
    
    try:
        from api.security import SecurityManager
        
        security = SecurityManager()
        print("   ✅ Security Manager initialized")
        
        # Test session creation
        session_token, session_id = security.create_anonymous_session("192.168.1.100")
        print(f"   ✅ Session created: {session_id[:8]}...")
        
        # Test input sanitization
        malicious_input = "<script>alert('xss')</script>Test input"
        sanitized = security.sanitize_user_input(malicious_input)
        print(f"   ✅ Input sanitization: {len(sanitized)} chars (from {len(malicious_input)})")
        
        # Test data encryption
        test_data = "sensitive information"
        encrypted = security.encrypt_sensitive_data(test_data)
        decrypted = security.decrypt_sensitive_data(encrypted)
        print(f"   ✅ Encryption/decryption: {decrypted == test_data}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Security test failed: {e}")
        return False

def test_performance_evaluator():
    """Test performance evaluation"""
    print("\n📊 Testing Performance Evaluator...")
    
    try:
        from api.performance_evaluator import PerformanceEvaluator
        
        evaluator = PerformanceEvaluator()
        print("   ✅ Performance Evaluator initialized")
        
        # Test metrics recording
        evaluator.record_request_metrics(
            agent_name="test_agent",
            request_type="test_request",
            processing_time=1.5,
            success=True
        )
        print("   ✅ Metrics recording working")
        
        # Test performance summary
        summary = evaluator.get_system_performance_summary()
        print(f"   ✅ Performance summary: {len(summary)} metrics")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Performance evaluator test failed: {e}")
        return False

def test_utilities():
    """Test utility functions"""
    print("\n🔧 Testing Utility Functions...")
    
    try:
        from api.utils import make_serializable, serialize_messages
        
        # Test message serialization
        test_messages = ["Hello", "World", 42]
        serialized = serialize_messages(test_messages)
        print(f"   ✅ Message serialization: {len(serialized)} messages")
        
        # Test data serialization
        test_data = {
            "user": "test",
            "messages": ["msg1", "msg2"],
            "nested": {"key": "value"}
        }
        serialized_data = make_serializable(test_data)
        print(f"   ✅ Data serialization: {len(serialized_data)} keys")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Utilities test failed: {e}")
        return False

def test_file_operations():
    """Test file operations"""
    print("\n📁 Testing File Operations...")
    
    try:
        # Create a temporary test file
        test_content = """
        John Doe
        Software Engineer
        
        Experience:
        - Senior Developer at TechCorp (2020-2024)
        - Software Engineer at StartupXYZ (2018-2020)
        
        Skills:
        - Python, JavaScript, SQL
        - React, Django, PostgreSQL
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            temp_file = f.name
        
        try:
            # Test basic file reading (without OpenAI dependency)
            with open(temp_file, 'r') as f:
                content = f.read()
            print(f"   ✅ File reading: {len(content)} characters read")
            
            # Test file existence check
            if os.path.exists(temp_file):
                print(f"   ✅ File existence check: file found")
            else:
                print(f"   ❌ File existence check: file not found")
                return False
            
        finally:
            # Clean up
            os.unlink(temp_file)
        
        return True
        
    except Exception as e:
        print(f"   ❌ File operations test failed: {e}")
        return False

def test_load_testing_framework():
    """Test that load testing framework is available"""
    print("\n⚡ Testing Load Testing Framework...")
    
    try:
        # Check if load testing files exist
        load_test_files = [
            "tests/test_performance_load.py",
            "tests/test_stress_testing.py",
            "tests/test_connection_pool_load.py",
            "run_load_tests.py"
        ]
        
        existing_files = []
        for file_path in load_test_files:
            if os.path.exists(file_path):
                existing_files.append(file_path)
        
        print(f"   ✅ Load testing files available: {len(existing_files)}/{len(load_test_files)}")
        
        if len(existing_files) >= 3:
            print("   ✅ Load testing framework ready")
            return True
        else:
            print("   ⚠️ Some load testing files missing")
            return False
        
    except Exception as e:
        print(f"   ❌ Load testing framework check failed: {e}")
        return False

def main():
    """Run all system tests"""
    print("🧪 SYSTEM TESTING SUITE")
    print("=" * 50)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    test_results = []
    test_results.append(("AI Safety", test_ai_safety()))
    test_results.append(("Security", test_security()))
    test_results.append(("Performance Evaluator", test_performance_evaluator()))
    test_results.append(("Utilities", test_utilities()))
    test_results.append(("File Operations", test_file_operations()))
    test_results.append(("Load Testing Framework", test_load_testing_framework()))
    
    # Summary
    print("\n" + "=" * 50)
    print("SYSTEM TEST SUMMARY")
    print("=" * 50)
    
    passed_tests = [name for name, result in test_results if result]
    failed_tests = [name for name, result in test_results if not result]
    
    print(f"✅ Passed: {len(passed_tests)}/{len(test_results)} tests")
    for test_name in passed_tests:
        print(f"   • {test_name}")
    
    if failed_tests:
        print(f"\n❌ Failed: {len(failed_tests)} tests")
        for test_name in failed_tests:
            print(f"   • {test_name}")
    
    success_rate = len(passed_tests) / len(test_results) * 100
    
    print(f"\n📊 Success Rate: {success_rate:.0f}%")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT: System is working very well")
        status = "READY"
    elif success_rate >= 70:
        print("✅ GOOD: System is working with minor issues")
        status = "MOSTLY READY"
    elif success_rate >= 50:
        print("⚠️ FAIR: System has some issues to resolve")
        status = "NEEDS WORK"
    else:
        print("❌ POOR: System has significant issues")
        status = "NOT READY"
    
    print(f"\n🏁 SYSTEM STATUS: {status}")
    
    # Next steps
    if failed_tests:
        print(f"\n📋 NEXT STEPS:")
        print("1. Fix failed components:")
        for test_name in failed_tests:
            print(f"   • Address {test_name} issues")
        print("2. Re-run tests to verify fixes")
        print("3. Set up OpenAI API key for full functionality")
    else:
        print(f"\n🚀 READY FOR USE:")
        print("1. Set OPENAI_API_KEY environment variable")
        print("2. Run: python api/index.py (for API)")
        print("3. Run: python run_load_tests.py (for load testing)")
    
    return len(failed_tests)

if __name__ == "__main__":
    failed_count = main()
    sys.exit(failed_count)