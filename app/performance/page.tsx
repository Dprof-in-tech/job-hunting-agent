'use client'

import { useState, useEffect, useMemo, useCallback, memo } from 'react';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  BarElement, 
  Title, 
  Tooltip, 
  Legend,
  ArcElement,
  PointElement,
  LineElement
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import type { ChartData, ChartOptions } from 'chart.js';
import { Activity, RefreshCw, TrendingUp, Users, CheckCircle, AlertTriangle, Clock, Zap } from 'lucide-react';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement
);

// --- Types for API Data ---
interface QuickStats {
  success_rate_display: string;
  avg_response_time_display: string;
  user_satisfaction_display: string;
  effectiveness_display: string;
}

interface SystemOverview {
  status: 'healthy' | 'warning' | 'critical' | string;
  total_requests: number;
  success_rate: number;
  avg_response_time: number;
  uptime_percentage: number;
  system_grade: string;
}

interface UserSatisfaction {
  current_score: number;
  avg_satisfaction: number;
  total_feedback: number;
  satisfaction_distribution: {
    'excellent (9-10)': number;
    'good (7-8)': number;
    'fair (5-6)': number;
    'poor (1-4)': number;
    [key: string]: number;
  };
}

interface AgentPerformanceData {
  total_calls: number;
  success_rate: number;
  avg_processing_time: number;
  performance_grade: string;
}

interface AgentPerformance {
  resume_analyst?: AgentPerformanceData;
  job_researcher?: AgentPerformanceData;
  cv_creator?: AgentPerformanceData;
  job_matcher?: AgentPerformanceData;
  [key: string]: AgentPerformanceData | undefined;
}

interface Effectiveness {
  overall_score: number;
  effectiveness_grade: string;
  key_insights: string[];
  benchmark_comparison?: BenchmarkComparisonData;
}

interface Recommendations {
  top_priorities: string[];
}

interface BenchmarkComparisonData {
  performance_vs_targets: {
    [key: string]: {
      actual: number;
      target: number;
      status: string;
    };
  };
  efficiency_vs_manual: {
    [key: string]: {
      manual_time?: number;
      system_time?: number;
      efficiency_gain?: string;
    };
  };
}

interface PerformanceData {
  quick_stats: QuickStats;
  system_overview: SystemOverview;
  user_satisfaction: UserSatisfaction;
  agent_performance: AgentPerformance;
  effectiveness: Effectiveness;
  recommendations: Recommendations;
}

const PerformanceDashboard = () => {
  const [performance, setPerformance] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [lastUpdated, setLastUpdated] = useState<string>("");

  // Fetch performance data with useCallback for optimization
  const fetchPerformanceData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/performance');
      const data = await response.json();
      
      if (data.success) {
        setPerformance(data.data);
        setLastUpdated(new Date().toLocaleTimeString());
        setError("");
      } else {
        setError(data.error || 'Failed to fetch performance data');
      }
    } catch (err) {
      setError('Network error: Unable to fetch performance data');
      console.error('Performance data fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPerformanceData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchPerformanceData, 30000);
    
    return () => clearInterval(interval);
  }, [fetchPerformanceData]);

  // Loading state
  if (loading && !performance) {
    return (
      <div className="min-h-screen bg-white text-black flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black mx-auto"></div>
          <p className="mt-4 text-lg text-gray-600">Loading Performance Data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-white text-black flex items-center justify-center">
        <div className="text-center bg-white border border-gray-200 p-8 rounded-lg">
          <AlertTriangle className="w-8 h-8 text-black mx-auto mb-4" />
          <h2 className="text-2xl font-medium text-black mb-4">Error Loading Dashboard</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={fetchPerformanceData}
            className="bg-black text-white px-6 py-2 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white text-black">
      <div className="max-w-6xl mx-auto px-6 py-8">
        
        {/* Header */}
        <DashboardHeader 
          performance={performance} 
          lastUpdated={lastUpdated}
          onRefresh={fetchPerformanceData}
          refreshing={loading}
        />

        {/* Quick Stats Grid */}
        <QuickStatsGrid stats={performance?.quick_stats} overview={performance?.system_overview} />

        {/* Main Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          
          {/* System Performance Chart */}
          <SystemPerformanceChart performance={performance} />
          
          {/* User Satisfaction Chart */}
          <UserSatisfactionChart satisfaction={performance?.user_satisfaction} />
          
        </div>

        {/* Agent Performance Grid */}
        <AgentPerformanceGrid agents={performance?.agent_performance} />

        {/* Effectiveness & Recommendations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <EffectivenessCard effectiveness={performance?.effectiveness} />
          <RecommendationsCard recommendations={performance?.recommendations} />
        </div>

        {/* Benchmark Comparison */}
        <BenchmarkComparison benchmarks={performance?.effectiveness?.benchmark_comparison} />

      </div>
    </div>
  );
};

// Dashboard Header Component
interface DashboardHeaderProps {
  performance: PerformanceData | null;
  lastUpdated: string;
  onRefresh: () => void;
  refreshing: boolean;
}
const DashboardHeader = memo(({ performance, lastUpdated, onRefresh, refreshing }: DashboardHeaderProps) => {
  const statusConfig = useMemo(() => {
    const status = performance?.system_overview?.status;
    switch (status) {
      case 'healthy': return { color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200', icon: CheckCircle };
      case 'warning': return { color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200', icon: AlertTriangle };
      case 'critical': return { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: AlertTriangle };
      default: return { color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200', icon: Activity };
    }
  }, [performance?.system_overview?.status]);

  const StatusIcon = statusConfig.icon;

  return (
    <header className="border-b border-gray-200 mb-8">
      <div className="py-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <Activity className="w-8 h-8 text-black" />
              <h1 className="text-3xl font-light tracking-tight text-black">Performance Dashboard</h1>
            </div>
            <p className="text-gray-600 text-lg leading-relaxed">
              Multi-Agent Job Hunting System Analytics
            </p>
          </div>
          
          <div className="flex flex-col items-end gap-3">
            <div className={`px-4 py-2 rounded-lg border ${statusConfig.bg} ${statusConfig.border} flex items-center gap-2`}>
              <StatusIcon className={`w-4 h-4 ${statusConfig.color}`} />
              <span className={`font-medium ${statusConfig.color} capitalize`}>
                {performance?.system_overview?.status || 'Unknown'}
              </span>
            </div>
            
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-500">
                Last updated: {lastUpdated || 'Never'}
              </span>
              <button
                onClick={onRefresh}
                disabled={refreshing}
                className="bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {refreshing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Refreshing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
});

// Quick Stats Grid Component
interface QuickStatsGridProps {
  stats: QuickStats | undefined;
  overview: SystemOverview | undefined;
}
const QuickStatsGrid = memo(({ stats, overview }: QuickStatsGridProps) => {
  const statCards = useMemo(() => [
    {
      title: 'Total Requests',
      value: overview?.total_requests || 0,
      icon: Activity,
      change: '+12%'
    },
    {
      title: 'Success Rate',
      value: stats?.success_rate_display || '0%',
      icon: CheckCircle,
      change: '+5.2%'
    },
    {
      title: 'Response Time',
      value: stats?.avg_response_time_display || '0s',
      icon: Clock,
      change: '-8.1%'
    },
    {
      title: 'User Satisfaction',
      value: stats?.user_satisfaction_display || '0/10',
      icon: Users,
      change: '+3.4%'
    },
    {
      title: 'Effectiveness',
      value: stats?.effectiveness_display || '0/100',
      icon: TrendingUp,
      change: '+15.2%'
    },
    {
      title: 'System Grade',
      value: overview?.system_grade || 'N/A',
      icon: Zap,
      change: null
    }
  ], [stats, overview]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
      {statCards.map((card, index) => {
        const IconComponent = card.icon;
        return (
          <div key={index} className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-sm transition-shadow">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-gray-600 text-sm font-medium mb-1">{card.title}</p>
                <p className="text-2xl font-light text-black">{card.value}</p>
                {card.change && (
                  <p className="text-xs text-gray-500 mt-1">{card.change} from last period</p>
                )}
              </div>
              <div className="ml-4">
                <IconComponent className="w-6 h-6 text-gray-400" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
});

// System Performance Chart Component
interface SystemPerformanceChartProps {
  performance: PerformanceData | null;
}
const SystemPerformanceChart = memo(({ performance }: SystemPerformanceChartProps) => {
  const chartData: ChartData<'bar'> = useMemo(() => ({
    labels: ['Success Rate', 'Response Time', 'Satisfaction', 'Uptime'],
    datasets: [
      {
        label: 'Performance Metrics',
        data: [
          performance?.system_overview?.success_rate || 0,
          (performance?.system_overview?.avg_response_time || 0) * 10,
          (performance?.user_satisfaction?.current_score || 0) * 10,
          performance?.system_overview?.uptime_percentage || 0
        ],
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: 'rgba(0, 0, 0, 1)',
        borderWidth: 1,
        borderRadius: 4
      }
    ]
  }), [performance]);

  const options: ChartOptions<'bar'> = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      title: {
        display: false
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        grid: {
          color: 'rgba(0, 0, 0, 0.1)'
        },
        ticks: {
          color: '#6B7280'
        }
      },
      x: {
        grid: {
          display: false
        },
        ticks: {
          color: '#6B7280'
        }
      }
    }
  }), []);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-lg font-medium text-black mb-4">System Performance</h3>
      <div className="h-64">
        <Bar data={chartData} options={options} />
      </div>
    </div>
  );
});

// User Satisfaction Chart Component
interface UserSatisfactionChartProps {
  satisfaction: UserSatisfaction | undefined;
}
const UserSatisfactionChart = memo(({ satisfaction }: UserSatisfactionChartProps) => {
  const chartData: ChartData<'doughnut'> = useMemo(() => {
    const distribution = satisfaction?.satisfaction_distribution;
    return {
      labels: ['Excellent', 'Good', 'Fair', 'Poor'],
      datasets: [
        {
          data: [
            distribution?.['excellent (9-10)'] || 0,
            distribution?.['good (7-8)'] || 0,
            distribution?.['fair (5-6)'] || 0,
            distribution?.['poor (1-4)'] || 0
          ],
          backgroundColor: [
            '#000000',
            '#4B5563',
            '#9CA3AF',
            '#D1D5DB'
          ],
          borderWidth: 0,
          cutout: '60%'
        }
      ]
    };
  }, [satisfaction]);

  const options: ChartOptions<'doughnut'> = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
          color: '#6B7280'
        }
      },
      title: {
        display: false
      }
    }
  }), []);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-black">User Satisfaction</h3>
        <span className="text-sm text-gray-500">
          {satisfaction?.total_feedback || 0} responses
        </span>
      </div>
      <div className="h-64 relative">
        <Doughnut data={chartData} options={options} />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-2xl font-light text-black">
              {satisfaction?.avg_satisfaction || 0}/10
            </p>
            <p className="text-xs text-gray-500">Average</p>
          </div>
        </div>
      </div>
    </div>
  );
});

// Agent Performance Grid Component
interface AgentPerformanceGridProps {
  agents: AgentPerformance | undefined;
}
const AgentPerformanceGrid = memo(({ agents }: AgentPerformanceGridProps) => {
  const agentConfig = useMemo(() => ({
    resume_analyst: { name: 'Resume Analyst', icon: Activity },
    job_researcher: { name: 'Job Researcher', icon: TrendingUp },
    cv_creator: { name: 'CV Creator', icon: Users },
    job_matcher: { name: 'Job Matcher', icon: CheckCircle }
  }), []);

  const getGradeStyle = useCallback((grade: string | undefined) => {
    switch (grade) {
      case 'A': return 'bg-gray-900 text-white';
      case 'B': return 'bg-gray-700 text-white';
      case 'C': return 'bg-gray-500 text-white';
      case 'D': return 'bg-gray-300 text-gray-800';
      case 'F': return 'bg-gray-100 text-gray-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  }, []);

  if (!agents) return null;

  return (
    <div className="mb-8">
      <h2 className="text-xl font-medium text-black mb-6">Agent Performance</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Object.entries(agents).map(([agentKey, agentData]) => {
          const config = agentConfig[agentKey as keyof typeof agentConfig] || { name: agentKey, icon: Activity };
          const data = agentData as AgentPerformanceData;
          const IconComponent = config.icon;
          
          return (
            <div key={agentKey} className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-sm transition-shadow">
              <div className="flex items-center gap-3 mb-4">
                <IconComponent className="w-5 h-5 text-gray-600" />
                <h3 className="font-medium text-black">{config.name}</h3>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Calls</span>
                  <span className="font-medium text-black">{data?.total_calls || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Success Rate</span>
                  <span className="font-medium text-black">{data?.success_rate || 0}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Avg Time</span>
                  <span className="font-medium text-black">{data?.avg_processing_time || 0}s</span>
                </div>
                <div className="flex justify-between items-center pt-2 border-t border-gray-100">
                  <span className="text-sm text-gray-600">Grade</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getGradeStyle(data?.performance_grade)}`}>
                    {data?.performance_grade || 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

// Effectiveness Card Component
interface EffectivenessCardProps {
  effectiveness: Effectiveness | undefined;
}
const EffectivenessCard = memo(({ effectiveness }: EffectivenessCardProps) => {
  const scoreColor = useMemo(() => {
    const score = effectiveness?.overall_score ?? 0;
    if (score >= 85) return 'text-black';
    if (score >= 65) return 'text-gray-700';
    if (score >= 45) return 'text-gray-500';
    return 'text-gray-400';
  }, [effectiveness?.overall_score]);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center gap-2 mb-6">
        <TrendingUp className="w-5 h-5 text-gray-600" />
        <h3 className="text-lg font-medium text-black">System Effectiveness</h3>
      </div>
      
      <div className="text-center mb-6">
        <div className={`text-4xl font-light ${scoreColor}`}>
          {effectiveness?.overall_score || 0}/100
        </div>
        <p className="text-sm text-gray-500 mt-1">
          {effectiveness?.effectiveness_grade || 'Not Available'}
        </p>
      </div>
      
      <div className="space-y-3">
        <div className="border-t border-gray-100 pt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Key Insights</h4>
          <ul className="space-y-2">
            {(effectiveness?.key_insights || []).slice(0, 3).map((insight, index) => (
              <li key={index} className="text-sm text-gray-600 leading-relaxed">
                • {insight}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
});

// Recommendations Card Component
interface RecommendationsCardProps {
  recommendations: Recommendations | undefined;
}
const RecommendationsCard = memo(({ recommendations }: RecommendationsCardProps) => {
  const getPriorityStyle = useCallback((text: string) => {
    if (text.includes('🎉') || text.includes('✅')) return 'border-l-green-500';
    if (text.includes('⚠️') || text.includes('❌')) return 'border-l-yellow-500';
    return 'border-l-gray-400';
  }, []);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center gap-2 mb-6">
        <Zap className="w-5 h-5 text-gray-600" />
        <h3 className="text-lg font-medium text-black">Recommendations</h3>
      </div>
      
      <div className="space-y-3">
        {(recommendations?.top_priorities || []).map((rec, index) => (
          <div key={index} className={`border-l-4 pl-4 py-2 ${getPriorityStyle(rec)}`}>
            <p className="text-sm text-gray-700 leading-relaxed">{rec}</p>
          </div>
        ))}
        
        {(!recommendations?.top_priorities || recommendations.top_priorities.length === 0) && (
          <div className="text-center py-8">
            <p className="text-gray-500">No recommendations available</p>
          </div>
        )}
      </div>
    </div>
  );
});

// Benchmark Comparison Component
interface BenchmarkComparisonProps {
  benchmarks: BenchmarkComparisonData | undefined;
}
const BenchmarkComparison = memo(({ benchmarks }: BenchmarkComparisonProps) => {
  if (!benchmarks) return null;

  const performanceVsTargets = benchmarks.performance_vs_targets || {};
  const efficiencyVsManual = benchmarks.efficiency_vs_manual || {};

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center gap-2 mb-6">
        <TrendingUp className="w-5 h-5 text-gray-600" />
        <h3 className="text-lg font-medium text-black">Benchmark Comparison</h3>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Performance vs Targets */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-4">Performance vs Targets</h4>
          <div className="space-y-3">
            {Object.entries(performanceVsTargets).map(([key, data]) => (
              <div key={key} className="border border-gray-100 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <p className="font-medium text-black capitalize text-sm">{key.replace('_', ' ')}</p>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    (data as { status: string }).status?.includes('✅') 
                      ? 'bg-gray-900 text-white' 
                      : 'bg-gray-200 text-gray-700'
                  }`}>
                    {(data as { status: string }).status?.includes('✅') ? 'Met' : 'Below'}
                  </span>
                </div>
                <p className="text-xs text-gray-600">
                  {(data as { actual: number; target: number }).actual} / {(data as { actual: number; target: number }).target} target
                </p>
              </div>
            ))}
          </div>
        </div>
        {/* Efficiency vs Manual */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-4">Efficiency vs Manual Process</h4>
          <div className="space-y-3">
            {Object.entries(efficiencyVsManual).map(([key, data]) => (
              <div key={key} className="border border-gray-100 rounded-lg p-4">
                <p className="font-medium text-black capitalize text-sm mb-3">{key.replace('_', ' ')}</p>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">Manual:</span>
                    <span className="text-black font-medium">
                      {(data as { manual_time?: number })?.manual_time ?? '-'}min
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">System:</span>
                    <span className="text-black font-medium">
                      {(data as { system_time?: number })?.system_time ?? '-'}min
                    </span>
                  </div>
                  <div className="flex justify-between text-xs pt-1 border-t border-gray-100">
                    <span className="text-gray-600">Gain:</span>
                    <span className="text-black font-medium">
                      {(data as { efficiency_gain?: string })?.efficiency_gain ?? '-'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
});

export default PerformanceDashboard;