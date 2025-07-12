'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Upload, FileText, Search, Users, Briefcase, TrendingUp, Download, Loader2, CheckCircle, AlertCircle, Brain, Sparkles } from 'lucide-react';

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
  };
  error?: string;
  timestamp?: string;
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

export default function JobHuntingPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [customPrompt, setCustomPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [jobId, setJobId] = useState<string | null>(null);
const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

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

  const processRequest = async (prompt: string, needsFile: boolean = false) => {
    if (needsFile && !selectedFile) {
      alert('Please upload your resume first');
      return;
    }
  
    setIsLoading(true);
    setResponse(null);
  
    try {
      const formData = new FormData();
      if (selectedFile) formData.append('file', selectedFile);
      formData.append('prompt', prompt);
  
      const res = await fetch('/api/process', {
        method: 'POST',
        body: formData,
      });
  
      const result = await res.json();
  
      if (res.status === 202 && result.job_id) {
        setJobId(result.job_id);
        pollJobStatus(result.job_id);
      } else {
        setIsLoading(false);
        setResponse({
          success: false,
          message: result.message || 'Unexpected response from server',
          error: result.error || 'Unknown error',
        });
      }
    } catch (err) {
      setIsLoading(false);
      setResponse({
        success: false,
        message: 'Request failed',
        error: 'An error occurred while processing the request.',
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

  const formatAgentMessage = (content: string) => {
    // Basic formatting for agent messages
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>')
      .replace(/•/g, '&bull;');
  };

  const pollJobStatus = async (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/status/${jobId}`);
        const data = await res.json();
  
        if (data.status === 'completed') {
          clearInterval(interval);
          setIsLoading(false);
          setJobId(null);
          setResponse({
            success: true,
            message: data.summary || '✅ Job completed',
            data: data.result,
          });
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setIsLoading(false);
          setJobId(null);
          setResponse({
            success: false,
            message: '❌ Job failed',
            error: data.error || 'Unknown error occurred.',
          });
        }
      } catch (err) {
        clearInterval(interval);
        setIsLoading(false);
        setJobId(null);
        setResponse({
          success: false,
          message: '❌ Polling failed',
          error: 'Could not retrieve job status',
        });
      }
    }, 2500);
  
    setPollingInterval(interval);
  };
  
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
                    : 'border-red-200 bg-red-50'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {response.success ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-red-600" />
                    )}
                    <span className={`font-medium ${
                      response.success ? 'text-green-800' : 'text-red-800'
                    }`}>
                      {response.success ? 'Success' : 'Error'}
                    </span>
                  </div>
                  <p className={`text-sm ${
                    response.success ? 'text-green-700' : 'text-red-700'
                  }`}>
                    {response.message || response.error}
                  </p>
                  {response.data?.agent_workflow && (
                    <p className="text-xs text-green-600 mt-2">
                      {response.data.agent_workflow}
                    </p>
                  )}
                </div>

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
                    {response.data.agent_messages.map((message, index) => (
                      <div key={index} className="border border-gray-200 rounded-lg p-6 bg-white">
                        <div 
                          className="prose prose-sm max-w-none text-gray-700 leading-relaxed"
                          dangerouslySetInnerHTML={{
                            __html: formatAgentMessage(message.content)
                          }}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {/* Additional Data */}
                {response.success && response.data?.job_listings && response.data.job_listings.length > 0 && (
                  <div className="border border-gray-200 rounded-lg p-4">
                    <h3 className="font-medium text-black mb-3">
                      Job Opportunities ({response.data.job_listings.length})
                    </h3>
                    <div className="space-y-3 max-h-64 overflow-y-auto">
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