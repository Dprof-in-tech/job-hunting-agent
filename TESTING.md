# 🧪 Testing Framework Documentation

Comprehensive testing and evaluation framework for the Multi-Agent Job Hunting System using DeepEval, pytest, and custom metrics.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Categories](#test-categories)
- [DeepEval Integration](#deepeval-integration)
- [Custom Evaluation Metrics](#custom-evaluation-metrics)
- [Running Tests](#running-tests)
- [Test Data](#test-data)
- [Performance Benchmarking](#performance-benchmarking)
- [Error Handling Testing](#error-handling-testing)
- [Integration Testing](#integration-testing)
- [Continuous Integration](#continuous-integration)

## 🎯 Overview

This testing framework provides comprehensive evaluation of the multi-agent system across multiple dimensions:

- **Functionality**: Unit and integration tests for all agents
- **Performance**: Response time, throughput, and resource usage
- **Quality**: DeepEval metrics for content quality and relevance  
- **Resilience**: Error handling and recovery testing
- **Scalability**: Load testing and concurrent request handling

## 🏗 Test Categories

### 1. Unit Tests (`tests/test_*.py`)
- Individual agent functionality
- Core business logic
- Utility functions
- Mock-based isolated testing

### 2. Integration Tests (`tests/test_integration.py`)
- Complete workflow testing
- Agent coordination and data flow
- End-to-end scenarios
- Cross-agent communication

### 3. Performance Tests (`tests/test_performance.py`)
- Response time benchmarking
- Resource usage monitoring
- Concurrent request handling
- Scalability assessment

### 4. Error Handling Tests (`tests/test_error_handling.py`)
- API failure scenarios
- Input validation and sanitization
- Recovery mechanisms
- Graceful degradation

### 5. Evaluation Tests (`tests/test_complete_evaluation.py`)
- DeepEval metric validation
- Quality assessment
- Content relevance scoring
- System coherence evaluation

## 📊 DeepEval Integration

### Custom Metrics

The framework includes specialized DeepEval metrics for each agent:

#### `ResumeAnalysisAccuracyMetric`
Evaluates resume analysis quality:
- Required sections validation
- Score reasonableness checks
- Content meaningfulness assessment
- ATS compatibility indicators

```python
metric = ResumeAnalysisAccuracyMetric(threshold=0.8)
score = metric.measure(test_case)
```

#### `JobSearchRelevanceMetric`
Assesses job search results quality:
- Minimum job count requirements
- Job listing completeness
- Relevance to search criteria
- Data quality validation

#### `CVGenerationQualityMetric`
Measures CV generation effectiveness:
- File generation success
- Standard CV sections presence
- ATS optimization indicators
- Professional formatting

#### `JobMatchingAccuracyMetric`
Evaluates job-resume compatibility:
- Match score reasonableness
- Skill alignment assessment
- Explanation quality
- Fit level accuracy

#### `SystemCoherenceMetric`
Assesses overall system coordination:
- Multi-agent workflow completion
- Data consistency across agents
- Logical execution order
- Result comprehensiveness

#### `PerformanceEfficiencyMetric`
Measures system performance:
- Response time evaluation
- Success rate assessment
- Efficiency rating validation
- Resource utilization

### Usage Example

```python
from tests.evaluation.evaluator import MultiAgentEvaluator
from deepeval.test_case import LLMTestCase

evaluator = MultiAgentEvaluator()

test_case = LLMTestCase(
    input="Analyze this resume",
    actual_output=resume_analysis_result,
    expected_output="Quality analysis"
)

results = evaluator.evaluate_agent("resume_analyst", [test_case])
report = evaluator.generate_comprehensive_report()
```

## 🏃‍♂️ Running Tests

### Quick Start

```bash
# Install dependencies and run all tests
python run_tests.py --install-deps

# Run quick test suite (excludes slow tests)
python run_tests.py --quick

# Run specific test category
python run_tests.py --category unit
python run_tests.py --category performance
python run_tests.py --category evaluation
```

### Pytest Commands

```bash
# Run all tests with coverage
pytest tests/ --cov=api --cov-report=html

# Run only unit tests
pytest tests/ -m "unit" -v

# Run performance tests with benchmarks
pytest tests/test_performance.py --benchmark-only

# Run integration tests
pytest tests/test_integration.py -v

# Run evaluation tests
pytest tests/test_complete_evaluation.py -v

# Run specific test file
pytest tests/test_error_handling.py -v

# Run tests with timeout
pytest tests/ --timeout=300
```

### Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.benchmark` - Benchmark tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.evaluation` - DeepEval tests

## 📁 Test Data

### Sample Resumes (`tests/test_data/sample_resumes.py`)

Comprehensive resume samples for testing:

- **Senior Software Engineer**: High-quality resume with quantified achievements
- **Recent Graduate**: Entry-level resume with projects and education
- **Career Changer**: Professional transitioning from finance to tech
- **Poorly Formatted**: Resume with formatting and content issues

### Sample Job Listings (`tests/test_data/sample_job_listings.py`)

Diverse job listings across categories:

- Software engineering positions
- Data science roles
- Entry-level opportunities
- Remote and on-site positions

### Mock API Responses

Predefined responses for various scenarios:
- Successful job searches
- API failures and timeouts
- Rate limiting scenarios
- Empty result sets

## ⚡ Performance Benchmarking

### Benchmark Tests

The framework includes comprehensive performance testing:

```python
@pytest.mark.benchmark(group="agent_performance")
def test_resume_analysis_benchmark(benchmark, mock_agent):
    def analyze_resume():
        return mock_agent.process_request("Analyze resume")
    
    result = benchmark(analyze_resume)
    assert result["success"] is True
```

### Performance Metrics Tracked

- **Response Time**: Average, min, max, p95
- **Throughput**: Requests per minute
- **Resource Usage**: Memory, CPU utilization
- **Concurrency**: Parallel request handling
- **Success Rate**: Percentage of successful requests

### Benchmarking Commands

```bash
# Run all benchmarks
pytest tests/test_performance.py --benchmark-only

# Sort benchmarks by mean time
pytest --benchmark-sort=mean

# Save benchmark results
pytest --benchmark-save=baseline

# Compare with previous benchmarks
pytest --benchmark-compare
```

## 🛡️ Error Handling Testing

### Error Scenarios Tested

1. **API Failures**
   - OpenAI API errors
   - Job search API timeouts
   - Network connectivity issues
   - Rate limiting

2. **Input Validation**
   - Malicious input sanitization
   - File upload validation
   - Large file handling
   - Invalid file formats

3. **System Resilience**
   - Agent failure recovery
   - Cascading failure prevention
   - Memory pressure handling
   - Concurrent request conflicts

4. **Data Corruption**
   - Malformed JSON handling
   - Empty response processing
   - Corrupted file handling

### Example Error Test

```python
def test_api_failure_handling(self, mock_agent):
    with patch('api.tools.llm.invoke') as mock_llm:
        mock_llm.side_effect = APIConnectionError("Connection failed")
        
        result = coordinator_agent(sample_state)
        
        # Should handle error gracefully
        assert "error" in str(result).lower()
        assert result.get("next_agent") == "END"
```

## 🔗 Integration Testing

### Workflow Testing

Tests complete agent workflows:

1. **Complete Job Hunt Workflow**
   - Coordinator → Resume Analyst → Job Researcher → CV Creator
   - Data flow validation
   - Result consistency checks

2. **Partial Workflows**
   - Resume analysis only
   - Job search only
   - CV generation only

3. **Edge Cases**
   - Empty resume handling
   - No jobs found scenarios
   - Partial completion handling

### Data Flow Validation

Ensures proper data transfer between agents:

- Resume analysis data flows to job search
- Job market insights inform CV generation
- Skills and keywords consistency across agents

## 📈 Evaluation Reports

### Report Generation

```python
evaluator = MultiAgentEvaluator()
# ... run evaluations ...

report = evaluator.generate_comprehensive_report()
evaluator.export_report(report, "evaluation_report.json")
```

### Report Contents

- **Summary Statistics**: Total tests, pass/fail rates, scores
- **Agent Performance**: Individual agent metrics and scores
- **Performance Metrics**: Response times, success rates
- **Error Analysis**: Error patterns and failure modes
- **Recommendations**: Actionable improvement suggestions

### Sample Report Structure

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "summary": {
    "total_tests": 50,
    "passed_tests": 42,
    "failed_tests": 8,
    "overall_score": 0.84,
    "success_rate": 0.84
  },
  "agent_scores": {
    "resume_analyst": 0.87,
    "job_researcher": 0.81,
    "cv_creator": 0.89,
    "job_matcher": 0.79
  },
  "performance_metrics": {
    "avg_response_time": 8.2,
    "max_response_time": 15.6,
    "success_rate": 0.84
  },
  "recommendations": [
    "Improve job_matcher performance - score below 0.8",
    "Optimize response time - average above 8 seconds",
    "Focus on error handling - 16% failure rate"
  ]
}
```

## 🔄 Continuous Integration

### GitHub Actions Integration

```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: python run_tests.py --install-deps
      - name: Run quick test suite
        run: python run_tests.py --quick
      - name: Run evaluation tests
        run: python run_tests.py --category evaluation
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

### Test Automation

- Automated testing on code changes
- Performance regression detection
- Quality metric monitoring
- Coverage requirement enforcement

## 📚 Best Practices

### Writing Tests

1. **Use Descriptive Names**: Test names should clearly indicate what's being tested
2. **Mock External Dependencies**: Isolate tests from external APIs
3. **Test Edge Cases**: Include failure scenarios and boundary conditions
4. **Validate All Outputs**: Check both success and failure paths
5. **Keep Tests Fast**: Use mocks to avoid slow operations

### Evaluation Guidelines

1. **Set Appropriate Thresholds**: Balance strictness with realism
2. **Use Diverse Test Data**: Cover various scenarios and edge cases
3. **Monitor Trends**: Track metrics over time for regression detection
4. **Regular Reviews**: Periodically review and update evaluation criteria

### Performance Testing

1. **Establish Baselines**: Record baseline performance for comparisons
2. **Test Under Load**: Simulate realistic usage patterns
3. **Monitor Resources**: Track memory, CPU, and network usage
4. **Test Scalability**: Verify performance under increasing load

## 🚀 Getting Started

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   python run_tests.py --install-deps
   ```

2. **Run Quick Tests**:
   ```bash
   python run_tests.py --quick
   ```

3. **Run Full Test Suite**:
   ```bash
   python run_tests.py
   ```

4. **View Results**:
   - Test results: Console output
   - Coverage report: `htmlcov/index.html`
   - Evaluation report: `test_results_*.json`

## 📞 Support

For questions or issues with the testing framework:

1. Check existing test examples in `tests/`
2. Review DeepEval documentation: https://docs.deepeval.com/
3. Consult pytest documentation: https://docs.pytest.org/
4. Create an issue for bugs or feature requests

---

*This testing framework ensures the multi-agent job hunting system meets high standards for functionality, performance, and quality.*