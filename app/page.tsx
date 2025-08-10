'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Upload, FileText, Search, Users, Briefcase, TrendingUp, Download, Loader2, CheckCircle, AlertCircle, Brain, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

interface ApiResponse {
  success: boolean;
  message: string;
  data?: {
    agent_workflow?: string;
    completed_tasks?: string[];
    execution_time?: string;
    resume_analysis?: any;
    job_market_data?: any;
    job_listings?: any[];
    cv_path?: string;
    cv_download_url?: string;
    cv_filename?: string;
    comparison_results?: any;
    agent_messages?: Array<{
      content: string;
      timestamp: string;
    }>;
    hitl_checkpoint?: string;
    hitl_data?: any;
    job_id?: string;
    revision?: boolean;
  };
  error?: string;
  timestamp?: string;
  needsApproval?: boolean;
}

interface QuickPrompt {
  id: string;
  title: string;
  description: string;
  prompt: string;
  icon: React.ReactNode;
  needsFile: boolean;
  category: 'analysis' | 'search' | 'creation' | 'research';
}

const quickPrompts: QuickPrompt[] = [
  {
    id: 'analyze-resume',
    title: 'Analyze My Resume',
    description: 'Get detailed feedback and improvement suggestions',
    prompt: 'Please analyze my resume thoroughly and provide detailed feedback on strengths, weaknesses, and specific improvements I should make to stand out to employers.',
    icon: <FileText className="w-5 h-5" />,
    needsFile: true,
    category: 'analysis'
  },
  {
    id: 'find-jobs',
    title: 'Find Relevant Jobs',
    description: 'Discover opportunities that match your profile',
    prompt: 'Based on my background and experience, find relevant job opportunities and provide insights about the current market demand for my skills.',
    icon: <Search className="w-5 h-5" />,
    needsFile: true,
    category: 'search'
  },
  {
    id: 'create-cv',
    title: 'Create Optimized CV',
    description: 'Generate a professional, ATS-friendly CV',
    prompt: 'Create a professional, ATS-optimized CV that enhances my strengths and addresses any weaknesses. Make it compelling for recruiters and modern hiring systems.',
    icon: <Briefcase className="w-5 h-5" />,
    needsFile: true,
    category: 'creation'
  },
  {
    id: 'complete-help',
    title: 'Complete Job Hunt',
    description: 'Full analysis, job search, and CV creation',
    prompt: 'I need comprehensive job hunting assistance. Please analyze my resume, research relevant job opportunities, and create an optimized CV. Provide a complete strategy for my job search.',
    icon: <Sparkles className="w-5 h-5" />,
    needsFile: true,
    category: 'creation'
  },
  {
    id: 'market-research',
    title: 'Market Research',
    description: 'Explore trends and demand in your field',
    prompt: 'Research the current job market trends in my field. What skills are most in demand? What companies are hiring? What salary ranges can I expect?',
    icon: <TrendingUp className="w-5 h-5" />,
    needsFile: false,
    category: 'research'
  },
  {
    id: 'career-switch',
    title: 'Career Transition',
    description: 'Guidance for changing career paths',
    prompt: 'I\'m considering a career change. Based on my current background, what opportunities exist in different fields? What skills should I develop and how can I position myself for a successful transition?',
    icon: <Users className="w-5 h-5" />,
    needsFile: true,
    category: 'research'
  }
];

// Approval Components
interface ApprovalComponentProps {
  checkpoint: string;
  data: any;
  jobId: string;
  onApproval: (jobId: string, response: any) => void;
}

const ApprovalComponent = ({ checkpoint, data, jobId, onApproval }: ApprovalComponentProps) => {
  if (checkpoint === 'coordinator_plan') {
    return <CoordinatorPlanApproval data={data} jobId={jobId} onApproval={onApproval} />;
  } else if (checkpoint === 'job_role_clarification') {
    return <JobRoleClarification data={data} jobId={jobId} onApproval={onApproval} />;
  }
  return null;
};

// Coordinator Plan Approval Component
const CoordinatorPlanApproval = ({ data, jobId, onApproval }: { data: any; jobId: string; onApproval: (jobId: string, response: any) => void }) => {
  const planSummary = data?.plan_summary || data?.plan?.reasoning || 'Plan details unavailable';
  const planGoal = data?.plan?.primary_goal || 'Goal not specified';
  const planAgents = data?.plan?.execution_order || [];
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');
  
  const handleRequestChanges = () => {
    if (feedbackText.trim()) {
      // Provide immediate visual feedback
      setShowFeedbackForm(false);
      
      onApproval(jobId, { 
        approved: false, 
        feedback: feedbackText.trim() 
      });
      setFeedbackText('');
    }
  };

  const commonFeedbackOptions = [
    "Focus more on remote work opportunities",
    "I want higher salary ranges",
    "Include more entry-level positions", 
    "Focus on specific companies (Google, Microsoft, etc.)",
    "Prioritize work-life balance",
    "I prefer contract/freelance work",
    "Focus on startups instead of large companies",
    "Include more senior-level positions"
  ];
  
  return (
    <div className="border border-gray-200 rounded-lg p-6 bg-white">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-5 h-5 text-black" />
        <h3 className="text-lg font-medium text-black">Review Execution Plan</h3>
      </div>
      
      <div className="bg-gray-50 rounded-lg p-4 mb-6 space-y-3">
        <div>
          <h4 className="font-medium text-black mb-1">Goal:</h4>
          <p className="text-sm text-gray-700">{planGoal}</p>
        </div>
        
        {planAgents.length > 0 && (
          <div>
            <h4 className="font-medium text-black mb-1">Agents Needed:</h4>
            <p className="text-sm text-gray-700">{planAgents.join(' → ')}</p>
          </div>
        )}
        
        <div>
          <h4 className="font-medium text-black mb-1">Strategy:</h4>
          <pre className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {planSummary}
          </pre>
        </div>
      </div>

      {!showFeedbackForm ? (
        <div className="flex gap-3">
          <button
            onClick={() => onApproval(jobId, { approved: true })}
            className="flex-1 bg-black text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
          >
            <CheckCircle className="w-4 h-4" />
            Approve & Continue
          </button>
          <button
            onClick={() => setShowFeedbackForm(true)}
            className="flex-1 border border-gray-300 text-gray-700 py-3 px-4 rounded-lg font-medium hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
          >
            <AlertCircle className="w-4 h-4" />
            Request Changes
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <h4 className="font-medium text-black mb-2">What should be done differently?</h4>
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="Describe what you'd like to change about this plan..."
              className="w-full h-24 p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:border-black transition-colors text-sm"
              autoFocus
            />
          </div>

          <div>
            <p className="text-sm text-gray-600 mb-2">Common requests:</p>
            <div className="flex flex-wrap gap-2">
              {commonFeedbackOptions.map((option, index) => (
                <button
                  key={index}
                  onClick={() => setFeedbackText(option)}
                  className="text-xs px-3 py-1 border border-gray-200 rounded-full text-gray-600 hover:border-black hover:text-black transition-colors"
                >
                  {option}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleRequestChanges}
              disabled={!feedbackText.trim()}
              className="flex-1 bg-black text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-800 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <AlertCircle className="w-4 h-4" />
              Submit Changes
            </button>
            <button
              onClick={() => {
                setShowFeedbackForm(false);
                setFeedbackText('');
              }}
              className="border border-gray-300 text-gray-700 py-3 px-4 rounded-lg font-medium hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Job Role Clarification Component
const JobRoleClarification = ({ data, jobId, onApproval }: { data: any; jobId: string; onApproval: (jobId: string, response: any) => void }) => {
  const [clarifiedRole, setClarifiedRole] = useState('');

  const handleSubmit = () => {
    if (clarifiedRole.trim()) {
      onApproval(jobId, { clarified_role: clarifiedRole.trim() });
    }
  };

  const commonRoles = [
    'Software Engineer',
    'Data Scientist', 
    'Product Manager',
    'Marketing Manager',
    'Sales Representative',
    'UI/UX Designer',
    'DevOps Engineer',
    'Business Analyst'
  ];

  return (
    <div className="border border-gray-200 rounded-lg p-6 bg-white">
      <div className="flex items-center gap-2 mb-4">
        <Search className="w-5 h-5 text-black" />
        <h3 className="text-lg font-medium text-black">Clarify Job Role</h3>
      </div>
      
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <p className="text-sm text-gray-700 leading-relaxed">
          {data?.clarification_message || 'Please specify the job role you\'re interested in.'}
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Specific Job Role
          </label>
          <input
            type="text"
            value={clarifiedRole}
            onChange={(e) => setClarifiedRole(e.target.value)}
            placeholder="e.g., Software Engineer, Marketing Manager, Data Scientist"
            className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:border-black transition-colors"
          />
        </div>

        <div>
          <p className="text-sm text-gray-600 mb-2">Common roles:</p>
          <div className="flex flex-wrap gap-2">
            {commonRoles.map((role) => (
              <button
                key={role}
                onClick={() => setClarifiedRole(role)}
                className="text-xs px-3 py-1 border border-gray-200 rounded-full text-gray-600 hover:border-black hover:text-black transition-colors"
              >
                {role}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={!clarifiedRole.trim()}
          className="w-full bg-black text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-800 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <CheckCircle className="w-4 h-4" />
          Continue with "{clarifiedRole || 'Selected Role'}"
        </button>
      </div>
    </div>
  );
};

// Utility function to handle API responses and check for rate limits
const handleAPIResponse = async (response: Response, apiName: string = 'API') => {
  if (response.status === 429) {
    const errorData = await response.json().catch(() => ({}));
    const retryAfter = response.headers.get('retry-after') || errorData.retry_after || 60;
    throw new Error(`🚫 Rate limit exceeded for ${apiName}. Please try again in ${retryAfter} seconds.`);
  }
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
    throw new Error(errorData.error || errorData.message || `${apiName} request failed`);
  }
  
  return response.json();
};

export default function JobHuntingPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [customPrompt, setCustomPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [jobId, setJobId] = useState<string | null>(null);
const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  const [justProcessedApproval, setJustProcessedApproval] = useState<boolean>(false);
  const [expandedSections, setExpandedSections] = useState<{[key: number]: boolean}>({});

  // Toggle function for expandable sections
  const toggleSection = useCallback((index: number) => {
    setExpandedSections(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  }, []);

  // Helper functions for job description processing
  const getCleanDescription = (description: string) => {
    if (!description || description === "No description available") {
      return "No description available";
    }

    // Look for "Description:" part in the pipe-separated string
    const parts = description.split(' | ');
    const descPart = parts.find(part => part.trim().startsWith("Description:"));
    
    if (descPart) {
      const clean = descPart.replace("Description:", "").trim();
      return clean.length > 150 ? clean.substring(0, 150) + "..." : clean;
    }

    // Fallback: return first 150 characters
    return description.length > 150 
      ? description.substring(0, 150) + "..." 
      : description;
  };

  const getSkills = (description: string) => {
    if (!description) return [];
    
    const parts = description.split(' | ');
    const skillsPart = parts.find(part => part.trim().startsWith("Key Skills:"));
    
    if (skillsPart) {
      const skillsText = skillsPart.replace("Key Skills:", "").trim();
      return skillsText.split(",").map(skill => skill.trim()).slice(0, 4); // First 4 skills
    }
    
    return [];
  };

  const getJobDetails = (description: string) => {
    if (!description) return {};
    
    const parts = description.split(' | ');
    const details: { [key: string]: string } = {};
    
    parts.forEach(part => {
      const trimmed = part.trim();
      if (trimmed.includes(":") && !trimmed.startsWith("Description:") && !trimmed.startsWith("Key Skills:")) {
        const [key, value] = trimmed.split(":", 2);
        const keyTrimmed = key.trim();
        
        // Only extract important details
        if (["Role", "Work Type", "Workplace", "Contract Type"].includes(keyTrimmed)) {
          details[keyTrimmed] = value.trim();
        }
      }
    });
    
    return details;
  };

  const handleFileSelect = useCallback((file: File) => {
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
    if (allowedTypes.includes(file.type)) {
      setSelectedFile(file);
    } else {
      alert('Please select a PDF, DOCX, or TXT file');
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const createNewSession = async () => {
    const sessionRes = await fetch('/api/session', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const sessionData = await handleAPIResponse(sessionRes, 'Session Creation');
    const newSessionId = sessionData.session_id;
    
    // Store session ID for future requests
    localStorage.setItem('session_id', newSessionId);
    localStorage.setItem('session_created_at', Date.now().toString());
    
    return newSessionId;
  };

  const isSessionValid = async (sessionId: string) => {
    try {
      // Use a session-required endpoint for validation - job status endpoint requires @require_session
      const testRes = await fetch('/api/status/validation-test-job', {
        method: 'GET',
        headers: {
          'X-Session-ID': sessionId
        }
      });
      
      // If we get 401, session is invalid
      // If we get 404, session is valid but job doesn't exist (which is what we expect)
      // Any other status means session is valid
      const isValid = testRes.status !== 401;
      return isValid;
    } catch (error) {
      return false;
    }
  };

  const processRequest = async (prompt: string, needsFile: boolean = false) => {
    if (needsFile && !selectedFile) {
      alert('Please upload your resume first');
      return;
    }
  
    setIsLoading(true);
    setResponse(null);
  
    try {
      // Check for existing session first
      let sessionId = localStorage.getItem('session_id');
      
      // If no existing session, create a new one
      if (!sessionId) {
        sessionId = await createNewSession();
      } else {
        // Validate existing session
        const isValid = await isSessionValid(sessionId);
        if (!isValid) {
          localStorage.removeItem('session_id');
          localStorage.removeItem('session_created_at');
          sessionId = await createNewSession();
        }
      }
      
      // Now make the request with session
      const formData = new FormData();
      if (selectedFile) formData.append('file', selectedFile);
      formData.append('prompt', prompt);
  
      const res = await fetch('/api/process', {
        method: 'POST',
        headers: {
          'X-Session-ID': sessionId!
        },
        body: formData,
      });
  
      const finalResult = await handleAPIResponse(res, 'Job Processing');
  
      if (finalResult.job_id) {
        setJobId(finalResult.job_id);
        // Clear any existing intervals before starting new polling
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        pollJobStatus(finalResult.job_id, true);
      } else {
        setIsLoading(false);
        setResponse({
          success: false,
          message: finalResult.message || 'Unexpected response from server',
          error: finalResult.error || 'Unknown error',
        });
      }
    } catch (err) {
      setIsLoading(false);
      const errorMessage = err instanceof Error ? err.message : 'An error occurred while processing the request.';
      setResponse({
        success: false,
        message: errorMessage.includes('🚫') ? errorMessage : 'Request failed',
        error: errorMessage,
      });
    }
  };
  

  const handleCustomSubmit = () => {
    if (!customPrompt.trim()) {
      alert('Please enter your request');
      return;
    }
    processRequest(customPrompt);
  };

  const handleQuickPrompt = (quickPrompt: QuickPrompt) => {
    processRequest(quickPrompt.prompt, quickPrompt.needsFile);
  };

  const handleApproval = async (jobId: string, approvalResponse: any) => {
    try {
      const sessionId = localStorage.getItem('session_id');
      if (!sessionId) {
        setResponse({
          success: false,
          message: '❌ Session expired',
          error: 'Please refresh and try again',
        });
        return;
      }
      
      // Set flag to indicate we just processed approval
      setJustProcessedApproval(true);
      
      const res = await fetch(`/api/approve/${jobId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({ response: approvalResponse }),
      });

      const result = await handleAPIResponse(res, 'Job Approval');
      
      // Check if the approval response indicates the job is already completed or needs new approval
      if (result.success === true) {
        // Approval was processed successfully
        setResponse({
          success: false,
          message: approvalResponse.approved ? 
            '⏳ Plan approved - Starting execution...' : 
            '⏳ Changes submitted - Creating revised plan...',
          data: undefined
        });
      } else if (result.needsApproval) {
        // Backend returned a new approval request (e.g., revised plan)
        setResponse({
          success: false,
          message: result.message || '🔄 New plan ready for approval',
          data: result.data,
          needsApproval: true
        });
        setIsLoading(false);
        return; // Don't start polling, we have a new approval request
      } else {
        // Handle other cases
        setResponse({
          success: result.success,
          message: result.message || 'Approval processed',
          data: result.data,
          error: result.error
        });
        if (result.success) {
          setIsLoading(false);
          return; // Job might already be completed
        }
      }
      
      // Resume polling with fast polling after a brief delay to allow backend processing
      setIsLoading(true);
      setTimeout(() => {
        // Clear any existing intervals before starting new polling
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        pollJobStatus(jobId, true);
        // Clear flag after a delay to allow for proper processing
        // Increased timeout to match the increased polling tolerance
        setTimeout(() => setJustProcessedApproval(false), 5000);
      }, 1000); // Wait 1 second before starting polling
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Network error while processing approval';
      setResponse({
        success: false,
        message: errorMessage.includes('🚫') ? errorMessage : '❌ Approval failed',
        error: errorMessage,
      });
    }
  };

  const formatAgentMessage = (content: string) => {
    // Basic formatting for agent messages
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>')
      .replace(/•/g, '&bull;');
  };

  const pollJobStatus = async (jobId: string, fastPolling = false) => {
    // Clear any existing polling interval first
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    
    // Use faster polling immediately after user actions, then slow down
    const pollInterval = fastPolling ? 500 : 2500; // 0.5s vs 2.5s
    let pollCount = 0;
    
    const interval = setInterval(async () => {
      pollCount++;
      
      // After 10 fast polls (5 seconds), switch to slower polling
      if (fastPolling && pollCount > 10) {
        clearInterval(interval);
        setPollingInterval(null);
        pollJobStatus(jobId, false); // Switch to slow polling
        return;
      }
      
      try {
        const sessionId = localStorage.getItem('session_id');
        if (!sessionId) {
          clearInterval(interval);
          setPollingInterval(null);
          setIsLoading(false);
          setResponse({
            success: false,
            message: '❌ Session expired',
            error: 'Please refresh and try again',
          });
          return;
        }
        
        const res = await fetch(`/api/status/${jobId}`, {
          headers: {
            'X-Session-ID': sessionId
          }
        });
        
        // Handle session expiration during polling
        if (res.status === 401) {
          clearInterval(interval);
          setPollingInterval(null);
          setIsLoading(false);
          localStorage.removeItem('session_id');
          localStorage.removeItem('session_created_at');
          setResponse({
            success: false,
            message: '❌ Session expired during processing',
            error: 'Please refresh and try your request again',
          });
          return;
        }
        
        const data = await handleAPIResponse(res, 'Job Status');
  
        if (data.status === 'completed') {
          clearInterval(interval);
          setPollingInterval(null);
          setIsLoading(false);
          setJobId(null);
          setJustProcessedApproval(false); // Clear flag on completion
          setResponse({
            success: true,
            message: data.summary || '✅ Job completed',
            data: data.result,
          });
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setPollingInterval(null);
          setIsLoading(false);
          setJobId(null);
          setResponse({
            success: false,
            message: '❌ Job failed',
            error: data.error || 'Unknown error occurred.',
          });
        } else if (data.status === 'processing' || data.status === 'in_progress' || data.status === 'executing') {
          // Job is processing - show processing message and continue polling
          setJustProcessedApproval(false); // Clear approval flag since we're now processing
          setResponse({
            success: false,
            message: '⚙️ Executing approved plan...',
            data: undefined // Clear any previous approval data
          });
          // Continue polling - don't clear interval
        } else if (data.status === 'awaiting_approval') {
          // Check if we just processed an approval to avoid immediate double requests
          if (justProcessedApproval && pollCount < 8) {
            // Skip showing approval for first few polls after processing approval
            // Increased from 5 to 8 to give backend more time to process
            return;
          }
          
          clearInterval(interval);
          setPollingInterval(null);
          setIsLoading(false);
          setResponse({
            success: false,
            message: data.revision ? '🔄 Revised Plan Ready - Review Changes' : '⏸️ Approval Required',
            data: {
              hitl_checkpoint: data.hitl_checkpoint,
              hitl_data: data.hitl_data,
              job_id: data.job_id || jobId,
              revision: data.revision || false
            },
            needsApproval: true
          });
        } else {
          // Handle any other status (fallback) - continue polling
          setResponse({
            success: false,
            message: `⚙️ Processing... (${data.status})`,
            data: undefined
          });
          // Continue polling - don't clear interval
        }
      } catch (err) {
        clearInterval(interval);
        setPollingInterval(null);
        setIsLoading(false);
        setJobId(null);
        const errorMessage = err instanceof Error ? err.message : 'Could not retrieve job status';
        setResponse({
          success: false,
          message: errorMessage.includes('🚫') ? errorMessage : '❌ Polling failed',
          error: errorMessage,
        });
      }
    }, pollInterval);
  
    setPollingInterval(interval);
  };
  
  // Validate session on page load
  useEffect(() => {
    const validateSessionOnLoad = async () => {
      const sessionId = localStorage.getItem('session_id');
      if (sessionId) {
        const isValid = await isSessionValid(sessionId);
        if (!isValid) {
          localStorage.removeItem('session_id');
          localStorage.removeItem('session_created_at');
        }
      }
    };
    
    validateSessionOnLoad();
  }, []);

  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);
  

  return (
    <div className="min-h-screen bg-white text-black">
      {/* Header */}
      <header className="border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3 mb-4">
            <Brain className="w-8 h-8 text-black" />
            <h1 className="text-3xl font-light tracking-tight">Intelligent Career Assistant</h1>
          </div>
          <p className="text-gray-600 text-lg leading-relaxed max-w-2xl">
            AI-powered job hunting with autonomous multi-agent coordination. 
            Upload your resume and describe what you need—our specialists will handle the rest.
          </p>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid lg:grid-cols-2 gap-12">
          {/* Left Column - Input */}
          <div className="space-y-8">
            {/* File Upload */}
            <div className="space-y-4">
              <h2 className="text-xl font-medium text-black">Resume Upload</h2>
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 ${
                  dragActive
                    ? 'border-black bg-gray-50'
                    : selectedFile
                    ? 'border-black bg-gray-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onDragEnter={() => setDragActive(true)}
                onDragLeave={() => setDragActive(false)}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={handleFileInputChange}
                  className="hidden"
                />
                
                {selectedFile ? (
                  <div className="space-y-2">
                    <CheckCircle className="w-8 h-8 text-black mx-auto" />
                    <p className="font-medium text-black">{selectedFile.name}</p>
                    <p className="text-sm text-gray-500">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Upload className="w-8 h-8 text-gray-400 mx-auto" />
                    <div>
                      <p className="font-medium text-gray-700">Drop your resume here</p>
                      <p className="text-sm text-gray-500">or click to browse</p>
                    </div>
                    <p className="text-xs text-gray-400">Supports PDF, DOCX, TXT</p>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="space-y-4">
              <h2 className="text-xl font-medium text-black">Quick Actions</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                {quickPrompts.map((prompt) => (
                  <button
                    key={prompt.id}
                    onClick={() => handleQuickPrompt(prompt)}
                    disabled={isLoading || (prompt.needsFile && !selectedFile)}
                    className={`p-4 text-left border rounded-lg transition-all duration-200 ${
                      prompt.needsFile && !selectedFile
                        ? 'border-gray-200 bg-gray-50 text-gray-400 cursor-not-allowed'
                        : 'border-gray-200 hover:border-black hover:shadow-sm bg-white text-black'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 text-gray-600">{prompt.icon}</div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-sm mb-1">{prompt.title}</h3>
                        <p className="text-xs text-gray-500 leading-relaxed">
                          {prompt.description}
                        </p>
                        {prompt.needsFile && !selectedFile && (
                          <p className="text-xs text-red-400 mt-1">Requires resume upload</p>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Prompt */}
            <div className="space-y-4">
              <h2 className="text-xl font-medium text-black">Custom Request</h2>
              <div className="space-y-3">
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Describe what you need help with... 
                  
Examples:
• 'Analyze my resume for marketing positions'
• 'Find remote software engineering jobs'
• 'Help me transition from finance to tech'
• 'Research the job market for UX designers'"
                  className="w-full h-32 p-4 border border-gray-300 rounded-lg resize-none focus:outline-none focus:border-black transition-colors duration-200 text-sm leading-relaxed"
                  disabled={isLoading}
                />
                <button
                  onClick={handleCustomSubmit}
                  disabled={isLoading || !customPrompt.trim()}
                  className="w-full bg-black text-white py-3 rounded-lg font-medium disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-gray-800 transition-colors duration-200 flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    'Process Request'
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Right Column - Results */}
          <div className="space-y-6">
            <h2 className="text-xl font-medium text-black">Results</h2>
            
            {isLoading && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
                <Loader2 className="w-8 h-8 animate-spin text-black mx-auto mb-4" />
                <p className="text-gray-600 font-medium">AI agents are working on your request...</p>
                <p className="text-sm text-gray-500 mt-2">This may take a few moments</p>
              </div>
            )}

            {response && !isLoading && (
              <div className="space-y-6">
                {/* Status */}
                <div className={`border rounded-lg p-4 ${
                  response.success 
                    ? 'border-green-200 bg-green-50' 
                    : response.needsApproval 
                    ? 'border-blue-200 bg-blue-50'
                    : 'border-red-200 bg-red-50'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {response.success ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : response.needsApproval ? (
                      <Brain className="w-5 h-5 text-blue-600" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-red-600" />
                    )}
                    <span className={`font-medium ${
                      response.success 
                        ? 'text-green-800' 
                        : response.needsApproval
                        ? 'text-blue-800'
                        : 'text-red-800'
                    }`}>
                      {response.success ? 'Success' : response.needsApproval ? 'Approval Required' : 'Error'}
                    </span>
                  </div>
                  <p className={`text-sm ${
                    response.success 
                      ? 'text-green-700' 
                      : response.needsApproval
                      ? 'text-blue-700'
                      : 'text-red-700'
                  }`}>
                    {response.message || response.error}
                  </p>
                  {response.data?.agent_workflow && (
                    <p className="text-xs text-green-600 mt-2">
                      {response.data.agent_workflow}
                    </p>
                  )}
                </div>

                {/* Approval UI */}
                {response.needsApproval && response.data?.hitl_checkpoint && response.data?.job_id && (
                  <ApprovalComponent
                    checkpoint={response.data.hitl_checkpoint}
                    data={response.data.hitl_data}
                    jobId={response.data.job_id}
                    onApproval={handleApproval}
                  />
                )}

                {/* Download CV */}
                {response.success && response.data?.cv_download_url && (
                  <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-black">Generated CV</h3>
                        <p className="text-sm text-gray-600">
                          {response.data.cv_filename || 'optimized_cv.pdf'}
                        </p>
                      </div>
                      <a
                        href={response.data.cv_download_url}
                        download
                        className="bg-black text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors duration-200 flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        Download
                      </a>
                    </div>
                  </div>
                )}

                {/* Agent Messages */}
                {response.success && response.data?.agent_messages && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-medium text-black">AI Analysis & Results</h3>
                      <span className="text-xs text-gray-500">
                        {response.data.agent_messages.length} section{response.data.agent_messages.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                    <div className="space-y-3 max-h-[750px] overflow-y-auto pr-2 scrollbar-thin">
                      {response.data.agent_messages.map((message, index) => {
                        const isExpanded = expandedSections[index] ?? (index === 0); // First section expanded by default
                        const previewText = message.content.substring(0, 200) + (message.content.length > 200 ? '...' : '');
                        
                        return (
                          <div key={index} className="border border-gray-200 rounded-lg bg-white overflow-hidden">
                            {/* Message Header - Clickable */}
                            <button
                              onClick={() => toggleSection(index)}
                              className="w-full flex items-center justify-between p-4 pb-3 border-b border-gray-100 hover:bg-gray-50 transition-colors text-left"
                            >
                              <div className="flex items-center gap-2">
                                <Sparkles className="w-4 h-4 text-gray-600" />
                                <span className="text-sm font-medium text-gray-700">
                                  Analysis Section {index + 1}
                                </span>
                                {!isExpanded && (
                                  <span className="text-xs text-gray-500 ml-2">
                                    ({message.content.length} characters)
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                {message.timestamp && (
                                  <span className="text-xs text-gray-500">
                                    {new Date(message.timestamp).toLocaleTimeString()}
                                  </span>
                                )}
                                {isExpanded ? (
                                  <ChevronUp className="w-4 h-4 text-gray-500" />
                                ) : (
                                  <ChevronDown className="w-4 h-4 text-gray-500" />
                                )}
                              </div>
                            </button>
                            
                            {/* Message Content - Collapsible */}
                            <div className={`transition-all duration-200 ${isExpanded ? 'max-h-none' : 'max-h-0 overflow-hidden'}`}>
                              {isExpanded ? (
                                <div className="p-4 pt-3">
                                  <div 
                                    className="prose prose-sm max-w-none text-gray-700 leading-relaxed [&>h1]:text-lg [&>h1]:font-semibold [&>h1]:text-black [&>h1]:mb-3 [&>h2]:text-base [&>h2]:font-medium [&>h2]:text-black [&>h2]:mb-2 [&>h3]:text-sm [&>h3]:font-medium [&>h3]:text-gray-900 [&>h3]:mb-2 [&>ul]:space-y-1 [&>ol]:space-y-1 [&>li]:text-sm [&>p]:text-sm [&>p]:mb-3 [&>strong]:font-medium [&>strong]:text-black"
                                    dangerouslySetInnerHTML={{
                                      __html: formatAgentMessage(message.content)
                                    }}
                                  />
                                </div>
                              ) : (
                                <div className="p-4 pt-3 bg-gray-50">
                                  <p className="text-sm text-gray-600 line-clamp-3">
                                    {previewText}
                                  </p>
                                  <button
                                    onClick={() => toggleSection(index)}
                                    className="text-xs text-blue-600 hover:text-blue-800 mt-2 font-medium"
                                  >
                                    Click to expand →
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Job Listings */}
                {response.success && response.data?.job_listings && response.data.job_listings.length > 0 && (
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="p-4 border-b border-gray-100 bg-gray-50">
                      <div className="flex items-center justify-between">
                        <h3 className="font-medium text-black">
                          Job Opportunities
                        </h3>
                        <span className="text-sm text-gray-600">
                          {response.data.job_listings.length} found
                        </span>
                      </div>
                    </div>
                    <div className="max-h-[400px] overflow-y-auto scrollbar-thin p-4">
                      <div className="space-y-4">
                      {response.data.job_listings.slice(0, 10).map((job: any, index: number) => {
                        const cleanDescription = getCleanDescription(job.description);
                        const skills = getSkills(job.description);
                        const jobDetails = getJobDetails(job.description);

                        return (
                          <div key={index} className="border-l-2 border-gray-200 pl-4 space-y-3">
                            {/* Job Title */}
                            <h4 className="font-medium text-md text-black">{job.title}</h4>
                            
                            {/* Skills Tags (if available) */}
                            {skills.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {skills.map((skill, skillIndex) => (
                                  <span 
                                    key={skillIndex}
                                    className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800"
                                  >
                                    {skill}
                                  </span>
                                ))}
                              </div>
                            )}

                            {/* Job Details Tags */}
                            {Object.keys(jobDetails).length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {Object.entries(jobDetails).map(([key, value], detailIndex) => (
                                  <span 
                                    key={detailIndex}
                                    className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700"
                                  >
                                    {key}: {value}
                                  </span>
                                ))}
                              </div>
                            )}
                            
                            {/* Clean Description */}
                            <h5 className="font-medium text-sm text-black leading-relaxed">
                              {cleanDescription}
                            </h5>
                            
                            {/* Company and Location */}
                            <p className="text-xs text-gray-600">{job.company} • {job.location}</p>
                            
                            {/* Salary (if available) */}
                            {job.salary && job.salary !== "Salary not specified" && (
                              <p className="text-xs text-green-600 font-medium">{job.salary}</p>
                            )}
                            
                            {/* Apply Link */}
                            {job.apply_url && (
                              <a
                                href={job.apply_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-black hover:underline inline-flex items-center gap-1"
                              >
                                View Job →
                              </a>
                            )}
                          </div>
                        );
                      })}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {!response && !isLoading && (
              <div className="border-2 border-dashed border-gray-200 rounded-lg p-12 text-center">
                <Brain className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500 font-medium">Upload your resume and select an action</p>
                <p className="text-sm text-gray-400 mt-1">
                  Our AI agents will provide comprehensive career assistance
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-16">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <p className="text-sm text-gray-500">
              Powered by multi-agent AI system with autonomous coordination
            </p>
            <div className="flex flex-wrap md:flex-row items-center gap-2 text-xs text-gray-400">
              <span>Specialists:</span>
              <span>Resume Analyst</span>
              <span>•</span>
              <span>Job Researcher</span>
              <span>•</span>
              <span>CV Creator</span>
              <span>•</span>
              <span>Job Matcher</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}