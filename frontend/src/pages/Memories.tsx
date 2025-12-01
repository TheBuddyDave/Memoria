import { useState, useRef, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import * as d3 from "d3";
import type {
  Node,
  MemoryPath,
  ReasoningStep
} from '../data/memory_data';

import {
  sampleNodes,
  sampleEdges,
  sampleNodeDetails,
  memoryPaths,
  reasoningBank
} from '../data/memory_data';

const nodeTypeColors: Record<string, string> = {
  Event: "var(--color-orange-500)",
  DataSource: "var(--color-highlight)",
  AgentAnswer: "var(--color-success)",
  AgentAction: "var(--color-agent-action)",
  UserRequest: "var(--color-user-request)",
  UserPreference: "var(--color-user-preference)",
};

export default function Memories() {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Determine active tab from route
  const getActiveTab = (): "query" | "graph" | "reasoning" => {
    if (location.pathname === "/graph") return "graph";
    if (location.pathname === "/reasoning") return "reasoning";
    return "query"; // default to query
  };
  
  const activeTab = getActiveTab();
  
  // Query state - persisted across tab switches
  const [query, setQuery] = useState("How should we optimize treatment dosage while accounting for patient demographic variations?");
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<string | null>(null);
  const [reasoningSteps, setReasoningSteps] = useState<ReasoningStep[]>([]);
  const [expandedSubqueries, setExpandedSubqueries] = useState<Set<number>>(new Set());
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  
  const handleTabChange = (tab: "query" | "graph" | "reasoning") => {
    navigate(`/${tab}`);
  };
  
  return (
    <div className="h-screen flex flex-col bg-white text-text overflow-hidden">
      {/* Header */}
      <header className="bg-orange-500-10 border-b border-orange-500-20 flex-shrink-0 relative">
        <div className="w-full px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
          {/* Title */}
          <div className="flex items-center space-x-2 sm:space-x-3 flex-shrink-0">
            <h1 className="text-lg sm:text-2xl font-semibold text-text cursor-pointer whitespace-nowrap">Memoria</h1>
          </div>

          {/* Navigation Tabs - Absolutely Centered */}
          <div className="absolute left-1/2 transform -translate-x-1/2 flex items-center space-x-6">
            <Link
              to="/query"
              className={`flex items-center space-x-2 text-sm font-medium py-2 transition-colors ${
                activeTab === "query"
                  ? "text-text"
                  : "text-text-secondary hover:text-text"
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <span>Query</span>
            </Link>
            <Link
              to="/graph"
              className={`flex items-center space-x-2 text-sm font-medium py-2 transition-colors ${
                activeTab === "graph"
                  ? "text-text"
                  : "text-text-secondary hover:text-text"
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
              <span>Memory Graph</span>
            </Link>
            <Link
              to="/reasoning"
              className={`flex items-center space-x-2 text-sm font-medium py-2 transition-colors ${
                activeTab === "reasoning"
                  ? "text-text"
                  : "text-text-secondary hover:text-text"
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              <span>Reasoning Bank</span>
            </Link>
            <Link
              to="/documents"
              className={`flex items-center space-x-2 text-sm font-medium py-2 transition-colors ${
                location.pathname === "/documents"
                  ? "text-text"
                  : "text-text-secondary hover:text-text"
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Documents</span>
            </Link>
          </div>

          {/* Right side buttons */}
          <div className="flex items-center space-x-4 flex-shrink-0">
            <button className="text-text-secondary hover:text-text transition-colors py-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden min-h-0 p-4">
        {/* Tab Content */}
        <div className="flex-1 overflow-hidden min-h-0 h-full">
          {activeTab === "query" ? (
            <QueryView 
              query={query}
              setQuery={setQuery}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
              response={response}
              setResponse={setResponse}
              reasoningSteps={reasoningSteps}
              setReasoningSteps={setReasoningSteps}
              expandedSubqueries={expandedSubqueries}
              setExpandedSubqueries={setExpandedSubqueries}
              expandedPaths={expandedPaths}
              setExpandedPaths={setExpandedPaths}
              setActiveSubTab={handleTabChange}
            />
          ) : activeTab === "graph" ? (
            <MemoryGraphView reasoningSteps={reasoningSteps} />
          ) : (
            <ReasoningBankView />
          )}
        </div>
      </main>
    </div>
  );
}

// Helper function to parse duration string to milliseconds
const parseDuration = (duration: string): number => {
  const match = duration.match(/(\d+)/);
  return match ? parseInt(match[1], 10) : 0;
};

interface QueryViewProps {
  query: string;
  setQuery: (query: string) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  response: string | null;
  setResponse: (response: string | null) => void;
  reasoningSteps: ReasoningStep[];
  setReasoningSteps: (steps: ReasoningStep[] | ((prev: ReasoningStep[]) => ReasoningStep[])) => void;
  expandedSubqueries: Set<number>;
  setExpandedSubqueries: (set: Set<number> | ((prev: Set<number>) => Set<number>)) => void;
  expandedPaths: Set<string>;
  setExpandedPaths: (set: Set<string> | ((prev: Set<string>) => Set<string>)) => void;
  setActiveSubTab: (tab: "query" | "graph" | "reasoning") => void;
}

function QueryView({
  query,
  setQuery,
  isLoading,
  setIsLoading,
  response: _response,
  setResponse,
  reasoningSteps,
  setReasoningSteps,
  expandedSubqueries,
  setExpandedSubqueries,
  expandedPaths,
  setExpandedPaths,
  setActiveSubTab,
}: QueryViewProps) {
  const reasoningEndRef = useRef<HTMLDivElement>(null);

  const toggleSubquery = (index: number) => {
    setExpandedSubqueries((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const togglePath = (pathKey: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(pathKey)) {
        next.delete(pathKey);
      } else {
        next.add(pathKey);
      }
      return next;
    });
  };

  // Helper to get path nodes by title
  const getPathNodes = (pathTitle: string) => {
    const path = memoryPaths.find(p => p.title === pathTitle);
    if (!path) return [];
    return path.nodes.map(nodeId => sampleNodeDetails[nodeId]).filter(Boolean);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleQuery();
    }
  };

  const scrollReasoningToBottom = () => {
    reasoningEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollReasoningToBottom();
  }, [reasoningSteps]);

  const handleQuery = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setResponse(null);
    setReasoningSteps([]);

    // Generate subqueries based on the query (hard-coded for demo)
    const generateSubqueries = (userQuery: string): string[] => {
      const queryLower = userQuery.toLowerCase();
      if (queryLower.includes("dosage") && queryLower.includes("demographic")) {
        return [
          "How do patient demographics influence treatment dosage recommendations and efficacy outcomes?",
          "What specific dosage optimization scenarios and sensitivity analyses have been performed for different demographic groups?",
          "What statistical methodologies exist for adjusting treatment efficacy calculations based on patient demographic variations?",
        ];
      }
      if (queryLower.includes("dosage")) {
        return [
          "What dosage optimization strategies and recommendations exist in the memory?",
          "What sensitivity analyses have been performed for dosage adjustments?",
          "What are the clinical guidelines for dosage optimization?",
        ];
      }
      if (queryLower.includes("demographic")) {
        return [
          "How do patient demographics affect treatment efficacy calculations?",
          "What data merging techniques are used to combine demographic data with treatment metrics?",
          "What are the best practices for demographic-adjusted analysis?",
        ];
      }
      if (queryLower.includes("treatment") && queryLower.includes("efficacy")) {
        return [
          "What treatment efficacy analyses and comparisons are available?",
          "What methodologies are used for efficacy calculations?",
          "What are the key findings from efficacy studies?",
        ];
      }
      return [
        "What relevant memories exist related to this query?",
        "What additional context is needed to answer this query?",
        "What related patterns or lessons exist in the memory?",
      ];
    };

    // Generate all subqueries
    const subqueries = generateSubqueries(query);
    
    // Define memories for each subquery retrieval (varied combinations)
    const memoriesBySubquery = [
      [
        {
          type: "Memory Path",
          title: "Patient-Adjusted Efficacy Analysis",
          description: "Path tracking patient demographic adjustments to efficacy calculations, including data merges and methodology references. Contains nodes: Merge Patient Demographics, Patient Enrollment Data, Treatment Response Data, Efficacy Analysis Result, Statistical Methodology.",
        },
        {
          type: "Memory Path",
          title: "Clinical Trial Analysis",
          description: "Path showing clinical trial analysis from user requests through data sources to actions. Contains nodes: Compare Treatment Efficacy, Phase III Trial Data, Adverse Event Correlation, Regulatory Approval.",
        },
        {
          type: "Reasoning Bank",
          title: "Demographic-Aware Efficacy Calculation",
          description: "Always adjust efficacy calculations for patient demographics before making treatment recommendations.",
        },
      ],
      [
        {
          type: "Reasoning Bank",
          title: "Dosage Optimization Scenarios",
          description: "For dosage optimization tasks, always provide multiple scenarios with projected impacts rather than a single recommendation.",
        },
        {
          type: "Reasoning Bank",
          title: "User Preference Formatting",
          description: "Match the analysis format to user preferences—visualizations for researchers, detailed tables for regulatory review.",
        },
      ],
      [
        {
          type: "Memory Path",
          title: "Dosage Optimization Strategy",
          description: "Path showing dosage adjustment recommendations based on efficacy analysis and user preferences. Contains nodes: Researcher Prefers Charts, Generate Cohort Analysis, Clinical Trial Guidelines, Dosage Adjustment 15mg, Q3 Research Summary.",
        },
        {
          type: "Memory Path",
          title: "Patient-Adjusted Efficacy Analysis",
          description: "Path tracking patient demographic adjustments to efficacy calculations, including data merges and methodology references. Contains nodes: Merge Patient Demographics, Patient Enrollment Data, Treatment Response Data, Efficacy Analysis Result, Statistical Methodology.",
        },
        {
          type: "Memory Path",
          title: "Telehealth Monitoring Performance",
          description: "Path tracking telehealth monitoring analysis from event triggers through performance findings. Contains nodes: 2026 Telehealth Initiative, Remote Monitoring Success, Adverse Event Correlation.",
        },
      ],
    ];
    
    // Build all reasoning steps dynamically
    const allSteps: ReasoningStep[] = [];
    let stepId = 1;
    
    // Initial analysis
    allSteps.push({
      text: "Analyzing query to generate subquery for memory retrieval...",
      duration: "320ms",
      id: stepId++,
    });
    
    // Loop through 3 subqueries
    for (let i = 0; i < 3; i++) {
      const subquery = subqueries[i];
      const memories = memoriesBySubquery[i];
      
      // Generate subquery
      allSteps.push({
        text: i === 0 ? "Generated subquery for database search" : `Generated additional subquery ${i + 1} for deeper memory retrieval`,
        duration: "180ms",
        subquery: subquery,
        id: stepId++,
      });
      
      // Query database
      allSteps.push({
        text: "Querying memory database with subquery...",
        duration: "450ms",
        id: stepId++,
      });
      
      // Retrieve memories
      allSteps.push({
        text: i === 0 
          ? "Retrieved relevant memories and reasoning patterns"
          : `Retrieved ${memories.length} additional relevant memories`,
        duration: "280ms",
        id: stepId++,
        memories: memories,
      });
      
      // Decision step (except after last subquery)
      if (i < 2) {
        allSteps.push({
          text: "Evaluating retrieved memories... Need additional context to provide comprehensive answer",
          duration: "240ms",
          id: stepId++,
        });
      }
    }
    
    // Final decision step: Sufficient memories collected
    allSteps.push({
      text: "Evaluating retrieved memories... Sufficient memories collected to provide comprehensive answer",
      duration: "240ms",
      id: stepId++,
    });
    
    // Final step: Collect all retrieved memories grouped by subquery
    const collectedMemories = subqueries.map((subquery, idx) => ({
      subquery: subquery,
      memories: memoriesBySubquery[idx],
    }));
    
    allSteps.push({
      text: "Collected all retrieved memories, data sources, and reasoning patterns",
      duration: "200ms",
      id: stepId++,
      collectedMemories: collectedMemories,
    });

    // Calculate total delay from all reasoning steps
    const totalDelay = allSteps.reduce((sum, step) => {
      return sum + (step.duration ? parseDuration(step.duration) : 0);
    }, 0);

    // Add steps sequentially with actual delays
    let cumulativeDelay = 0;
    allSteps.forEach((step) => {
      setTimeout(() => {
        setReasoningSteps((prev) => {
          // Check if this step already exists to avoid duplicates
          if (prev.some(s => s.id === step.id)) {
            return prev;
          }
          return [...prev, step];
        });
      }, cumulativeDelay);
      
      // Add the duration of this step to the cumulative delay for the next step
      if (step.duration) {
        cumulativeDelay += parseDuration(step.duration);
      }
    });

    // Complete loading after all reasoning steps
    setTimeout(() => {
      setIsLoading(false);
    }, totalDelay);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Reasoning Panel - Takes up full viewport */}
      <div className="flex-1 flex flex-col bg-orange-500-5 border-2 border-orange-500-30 rounded-lg overflow-hidden min-h-0">
        <div className="p-4 border-b border-orange-500-20 bg-orange-500-10 flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-orange-500">Memoria Reasoning</h2>
            <p className="text-sm text-text-secondary">Step-by-step memory retrieval process</p>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
          {reasoningSteps.length > 0 ? (
            <>
              {reasoningSteps.map((step, idx) => {
                // Determine color based on step type
                let borderColor = "border-orange-500";
                let bgColor = "bg-orange-500-5";
                if (step.subquery) {
                  borderColor = "border-orange-500";
                  bgColor = "bg-orange-500-5";
                } else if (step.memories && step.memories.length > 0) {
                  borderColor = "border-success";
                  bgColor = "bg-success-5";
                } else if (step.collectedMemories) {
                  borderColor = "border-user-preference";
                  bgColor = "bg-user-preference-5";
                } else if (step.text.includes("Evaluating") || step.text.includes("Need additional")) {
                  borderColor = "border-amber";
                  bgColor = "bg-amber-5";
                }
                
                return (
                <div 
                  key={step.id || idx}
                  className={`${bgColor} border-2 ${borderColor} rounded-lg p-3 text-sm overflow-hidden reasoning-step-enter`}
                >
                  <div className="flex items-start">
                    <div className="flex-1 min-w-0">
                      <p className="text-text leading-relaxed reasoning-step-text">
                        <strong>{step.text}</strong>
                      </p>
                      {step.subquery && (
                        <div className="mt-2 p-2 bg-orange-500-10 rounded border-l-4 border-orange-500">
                          <p className="text-xs font-semibold text-orange-500 mb-1">Subquery:</p>
                          <p className="text-text italic">"{step.subquery}"</p>
                        </div>
                      )}
                      {step.memories && step.memories.length > 0 && (
                        <div className="mt-3 space-y-2">
                          <p className="text-xs text-text-secondary mb-2">Retrieved {step.memories.length} memories:</p>
                          {step.memories.map((memory, memIdx) => {
                            const memoryKey = `step-${step.id}-mem-${memIdx}`;
                            const isMemoryExpanded = expandedPaths.has(memoryKey);
                            const isPath = memory.type === "Memory Path";
                            const pathNodes = isPath ? getPathNodes(memory.title) : [];
                            
                            return (
                              <div key={memIdx} className="space-y-2">
                                {isPath ? (
                                  <button
                                    onClick={() => togglePath(memoryKey)}
                                    className="w-full p-2 bg-success-10 rounded border-l-4 border-success hover:bg-success-15 transition-colors text-left"
                                  >
                                    <div className="flex items-center justify-between mb-1">
                                      <div className="flex items-center gap-2">
                                        <span className="text-xs font-semibold text-success">{memory.type}</span>
                                        <span className="text-xs font-medium text-text">{memory.title}</span>
                                      </div>
                                      <svg
                                        className={`w-3 h-3 text-success transition-transform flex-shrink-0 ${isMemoryExpanded ? 'transform rotate-180' : ''}`}
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                      >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                      </svg>
                                    </div>
                                    <p className="text-xs text-text-secondary leading-relaxed mb-2">{memory.description}</p>
                                    {isMemoryExpanded && pathNodes.length > 0 && (
                                      <div className="mt-2 space-y-1.5">
                                        <p className="text-xs font-semibold text-success mb-1">Nodes in path ({pathNodes.length}):</p>
                                        {pathNodes.map((node, nodeIdx) => {
                                          const nodeColors = [
                                            { bg: "bg-orange-500-10", border: "border-orange-500", text: "text-orange-500" },
                                            { bg: "bg-highlight-10", border: "border-highlight", text: "text-highlight" },
                                            { bg: "bg-agent-action-10", border: "border-agent-action", text: "text-agent-action" },
                                            { bg: "bg-user-preference-10", border: "border-user-preference", text: "text-user-preference" },
                                            { bg: "bg-pink-10", border: "border-pink", text: "text-pink" },
                                          ];
                                          const color = nodeColors[nodeIdx % nodeColors.length];
                                          return (
                                            <div key={nodeIdx} className={`ml-3 p-1.5 ${color.bg} rounded border-l-2 ${color.border}`}>
                                              <div className="flex items-center gap-2 mb-0.5">
                                                <span className={`text-xs font-medium ${color.text}`}>{node.type}</span>
                                                <span className="text-xs font-medium text-text">{node.title}</span>
                                              </div>
                                              <p className="text-xs text-text-secondary leading-relaxed">{node.description}</p>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    )}
                                  </button>
                                ) : (
                                  <div className={`relative p-2 rounded border-l-4 ${
                                    memory.type === "Reasoning Bank" 
                                      ? "bg-highlight-10 border-highlight"
                                      : memory.type === "DataSource"
                                      ? "bg-agent-action-10 border-agent-action"
                                      : "bg-success-10 border-success"
                                  }`}>
                                    <div className="flex items-center gap-2 mb-1 pr-10">
                                      <span className={`text-xs font-semibold ${
                                        memory.type === "Reasoning Bank"
                                          ? "text-highlight"
                                          : memory.type === "DataSource"
                                          ? "text-agent-action"
                                          : "text-success"
                                      }`}>{memory.type}</span>
                                      <span className="text-xs font-medium text-text">{memory.title}</span>
                                    </div>
                                    {memory.type === "Reasoning Bank" && (
                                      <button
                                        onClick={() => {
                                          setActiveSubTab("reasoning");
                                          setTimeout(() => {
                                            const entry = reasoningBank.find(e => e.title === memory.title);
                                            if (entry) {
                                              const element = document.querySelector(`[data-rb-id="${entry.rb_id}"]`);
                                              if (element) {
                                                element.scrollIntoView({ behavior: "smooth", block: "center" });
                                                element.classList.add("ring-2", "ring-highlight", "ring-offset-2");
                                                setTimeout(() => {
                                                  element.classList.remove("ring-2", "ring-highlight", "ring-offset-2");
                                                }, 2000);
                                              }
                                            }
                                          }, 100);
                                        }}
                                        className="absolute top-0 right-0 bottom-0 text-highlight hover:text-highlight-dark transition-colors text-xs px-3 rounded-r hover:bg-highlight-10 flex items-center justify-center"
                                        title="View in Reasoning Bank"
                                      >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                        </svg>
                                      </button>
                                    )}
                                    <p className="text-xs text-text-secondary leading-relaxed">{memory.description}</p>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                      {step.collectedMemories && step.collectedMemories.length > 0 && (
                        <div className="mt-3 space-y-4">
                          <p className="text-xs text-text-secondary mb-2">All collected memories grouped by subquery:</p>
                          {step.collectedMemories.map((group, groupIdx) => {
                            const isSubqueryExpanded = expandedSubqueries.has(groupIdx);
                            return (
                              <div key={groupIdx} className="space-y-2">
                                <button
                                  onClick={() => toggleSubquery(groupIdx)}
                                  className="w-full p-2 bg-orange-500-10 rounded border-l-4 border-orange-500 hover:bg-orange-500-15 transition-colors text-left"
                                >
                                  <div className="flex items-center justify-between">
                                    <div className="flex-1">
                                      <p className="text-xs font-semibold text-orange-500 mb-1">Subquery {groupIdx + 1}:</p>
                                      <p className="text-xs text-text italic">"{group.subquery}"</p>
                                    </div>
                                    <svg
                                      className={`w-4 h-4 text-orange-500 transition-transform flex-shrink-0 ${isSubqueryExpanded ? 'transform rotate-180' : ''}`}
                                      fill="none"
                                      stroke="currentColor"
                                      viewBox="0 0 24 24"
                                    >
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                  </div>
                                </button>
                                {isSubqueryExpanded && (
                                  <div className="ml-4 space-y-2">
                                    {group.memories.map((memory, memIdx) => {
                                      const pathKey = `${groupIdx}-${memIdx}`;
                                      const isPathExpanded = expandedPaths.has(pathKey);
                                      const isPath = memory.type === "Memory Path";
                                      const pathNodes = isPath ? getPathNodes(memory.title) : [];
                                      
                                      return (
                                        <div key={memIdx} className="space-y-2">
                                          {isPath ? (
                                            <button
                                              onClick={() => togglePath(pathKey)}
                                              className="w-full p-2 bg-success-10 rounded border-l-4 border-success hover:bg-success-15 transition-colors text-left"
                                            >
                                              <div className="flex items-center justify-between mb-1">
                                                <div className="flex items-center gap-2">
                                                  <span className="text-xs font-semibold text-success">{memory.type}</span>
                                                  <span className="text-xs font-medium text-text">{memory.title}</span>
                                                </div>
                                                <svg
                                                  className={`w-3 h-3 text-success transition-transform flex-shrink-0 ${isPathExpanded ? 'transform rotate-180' : ''}`}
                                                  fill="none"
                                                  stroke="currentColor"
                                                  viewBox="0 0 24 24"
                                                >
                                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                                </svg>
                                              </div>
                                              <p className="text-xs text-text-secondary leading-relaxed mb-2">{memory.description}</p>
                                              {isPathExpanded && pathNodes.length > 0 && (
                                                <div className="mt-2 space-y-1.5">
                                                  <p className="text-xs font-semibold text-success mb-1">Nodes in path ({pathNodes.length}):</p>
                                                  {pathNodes.map((node, nodeIdx) => {
                                                    const nodeColors = [
                                                      { bg: "bg-orange-500-10", border: "border-orange-500", text: "text-orange-500" },
                                                      { bg: "bg-highlight-10", border: "border-highlight", text: "text-highlight" },
                                                      { bg: "bg-agent-action-10", border: "border-agent-action", text: "text-agent-action" },
                                                      { bg: "bg-user-preference-10", border: "border-user-preference", text: "text-user-preference" },
                                                      { bg: "bg-pink-10", border: "border-pink", text: "text-pink" },
                                                    ];
                                                    const color = nodeColors[nodeIdx % nodeColors.length];
                                                    return (
                                                      <div key={nodeIdx} className={`ml-3 p-1.5 ${color.bg} rounded border-l-2 ${color.border}`}>
                                                        <div className="flex items-center gap-2 mb-0.5">
                                                          <span className={`text-xs font-medium ${color.text}`}>{node.type}</span>
                                                          <span className="text-xs font-medium text-text">{node.title}</span>
                                                        </div>
                                                        <p className="text-xs text-text-secondary leading-relaxed">{node.description}</p>
                                                      </div>
                                                    );
                                                  })}
                                                </div>
                                              )}
                                            </button>
                                          ) : (
                                            <div className={`relative p-2 rounded border-l-4 ${
                                              memory.type === "Reasoning Bank" 
                                                ? "bg-highlight-10 border-highlight"
                                                : memory.type === "DataSource"
                                                ? "bg-agent-action-10 border-agent-action"
                                                : "bg-success-10 border-success"
                                            }`}>
                                              <div className="flex items-center gap-2 mb-1 pr-10">
                                                <span className={`text-xs font-semibold ${
                                                  memory.type === "Reasoning Bank"
                                                    ? "text-highlight"
                                                    : memory.type === "DataSource"
                                                    ? "text-agent-action"
                                                    : "text-success"
                                                }`}>{memory.type}</span>
                                                <span className="text-xs font-medium text-text">{memory.title}</span>
                                              </div>
                                              {memory.type === "Reasoning Bank" && (
                                                <button
                                                  onClick={() => {
                                                    setActiveSubTab("reasoning");
                                                    // Store the title to scroll to it
                                                    setTimeout(() => {
                                                      const entry = reasoningBank.find(e => e.title === memory.title);
                                                      if (entry) {
                                                        const element = document.querySelector(`[data-rb-id="${entry.rb_id}"]`);
                                                        if (element) {
                                                          element.scrollIntoView({ behavior: "smooth", block: "center" });
                                                          // Highlight it briefly
                                                          element.classList.add("ring-2", "ring-highlight", "ring-offset-2");
                                                          setTimeout(() => {
                                                            element.classList.remove("ring-2", "ring-highlight", "ring-offset-2");
                                                          }, 2000);
                                                        }
                                                      }
                                                    }, 100);
                                                  }}
                                                  className="absolute top-0 right-0 bottom-0 text-highlight hover:text-highlight-dark transition-colors text-xs px-3 rounded-r hover:bg-highlight-10 flex items-center justify-center"
                                                  title="View in Reasoning Bank"
                                                >
                                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                                  </svg>
                                                </button>
                                              )}
                                              <p className="text-xs text-text-secondary leading-relaxed">{memory.description}</p>
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                      {step.duration && (
                        <p className="text-text-secondary text-xs mt-1">{step.duration}</p>
                      )}
                      {step.isProcessing && (
                        <div className="flex items-center space-x-1 mt-1">
                          <span className="text-text-secondary text-xs">•••</span>
                          <span className="text-text-secondary text-xs">Processing...</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                );
              })}
              <div ref={reasoningEndRef} />
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-text-secondary">
              {isLoading && (
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                  <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                  <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 bg-background flex-shrink-0 flex-none border-t border-black/10">
        <div className="max-w-full mx-auto flex items-center space-x-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Query your memory..."
            className="flex-1 px-4 py-3 bg-background border border-black/20 rounded-lg focus:outline-none focus:ring-2 ring-orange-500-50 focus:border-orange-500-50 text-text placeholder:text-gray-400 placeholder:opacity-70 text-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleQuery}
            disabled={isLoading || !query.trim()}
            className="relative w-12 h-12 bg-primary hover:bg-primary-dark disabled:bg-gray-400 disabled:cursor-not-allowed rounded-lg flex items-center justify-center transition-colors flex-shrink-0"
          >
            <svg 
              className="w-5 h-5 text-white absolute" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
              style={{ 
                transform: 'translate(calc(-50% + 2px), calc(-50% - 2px)) rotate(45deg)',
                top: '50%',
                left: '50%',
                transformOrigin: 'center'
              }}
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

interface MemoryGraphViewProps {
  reasoningSteps: ReasoningStep[];
}

function MemoryGraphView({ reasoningSteps }: MemoryGraphViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<MemoryPath | null>(null);
  const [selectedSubquery, setSelectedSubquery] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"Paths" | "Details" | "Subqueries">("Paths");
  const [isDetailsCollapsed, setIsDetailsCollapsed] = useState(false);
  const [legendCollapsed, setLegendCollapsed] = useState(false);
  const simulationRef = useRef<d3.Simulation<Node, d3.SimulationLinkDatum<Node>> | null>(null);
  const initializedPathRef = useRef<string | null>(null);
  const zoomTransformRef = useRef<d3.ZoomTransform | null>(null);
  
  // Extract subqueries from reasoning steps
  // Subqueries and their memories are in separate steps, so we need to find the memories step that follows each subquery
  const subqueries: Array<{
    index: number;
    subquery: string;
    memories: Array<{ type: string; title: string; description: string }>;
    stepId: number;
  }> = [];
  
  reasoningSteps.forEach((step, idx) => {
    if (step.subquery) {
      // Find the next step that has memories (should be 2 steps after: subquery -> querying -> memories)
      let memories: Array<{ type: string; title: string; description: string }> = [];
      for (let j = idx + 1; j < reasoningSteps.length && j < idx + 5; j++) {
        const nextStep = reasoningSteps[j];
        if (nextStep && nextStep.memories && Array.isArray(nextStep.memories) && nextStep.memories.length > 0) {
          memories = nextStep.memories;
          break;
        }
      }
      
      subqueries.push({
        index: subqueries.length,
        subquery: step.subquery,
        memories: memories,
        stepId: step.id || idx
      });
    }
  });

  // Separate effect for graph initialization - only recreate when selectedPath changes
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    // Only recreate if selectedPath or selectedSubquery actually changed
    const currentPathId = selectedPath?.id || null;
    const currentSubqueryIndex = selectedSubquery;
    const selectionKey = `${currentPathId}-${currentSubqueryIndex}`;
    // Check if we need to recreate: either not initialized yet, or selection changed
    if (initializedPathRef.current !== null && initializedPathRef.current === selectionKey && simulationRef.current) {
      // Selection hasn't changed and graph is already initialized, don't recreate
      return;
    }
    initializedPathRef.current = selectionKey;

    // Stop existing simulation if any
    if (simulationRef.current) {
      simulationRef.current.stop();
    }

    const svgSelection = d3.select(svg);
    
    svgSelection.selectAll("*").remove();

    const width = svg.clientWidth || 800;
    const height = svg.clientHeight || 600;
    
    // Set explicit SVG dimensions
    svg.setAttribute("width", width.toString());
    svg.setAttribute("height", height.toString());

    const g = svgSelection.append("g");

    // Add subtle entry animation - start slightly smaller
    g.attr("transform", "scale(0.95)")
      .transition()
      .duration(400)
      .ease(d3.easeCubicOut)
      .attr("transform", "scale(1)");

    // Add zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 2])
      .on("zoom", (event) => {
        zoomTransformRef.current = event.transform;
        g.attr("transform", event.transform);
      });

    svgSelection.call(zoom);
    
    // Restore zoom transform after recreating the graph
    if (zoomTransformRef.current) {
      svgSelection.call(zoom.transform, zoomTransformRef.current);
    }

    // Filter nodes and edges based on selected path or subquery
    // Get nodes to highlight based on selection
    const getHighlightedNodeIds = (): string[] => {
      if (selectedSubquery !== null) {
        const subquery = subqueries[selectedSubquery];
        if (subquery) {
          const nodeIds: string[] = [];
          // Collect all node IDs from paths mentioned in subquery memories
          subquery.memories.forEach(memory => {
            if (memory.type === "Memory Path") {
              const path = memoryPaths.find(p => p.title === memory.title);
              if (path) {
                nodeIds.push(...path.nodes);
              }
            }
          });
          return nodeIds;
        }
      } else if (selectedPath) {
        return selectedPath.nodes;
      }
      return [];
    };
    
    const highlightedNodeIds = getHighlightedNodeIds();

    const visibleNodes = selectedPath || selectedSubquery !== null
      ? sampleNodes.filter((n) => highlightedNodeIds.includes(n.id))
      : sampleNodes;

    const visibleEdges = selectedPath || selectedSubquery !== null
      ? sampleEdges.filter(
          (e) =>
            highlightedNodeIds.includes(e.from) && highlightedNodeIds.includes(e.to)
        )
      : sampleEdges;

    // Give nodes a better initial layout (spread them in a circle)
    // Set initial positions and velocities to prevent nodes starting in one spot
    if (visibleNodes.length > 0) {
      const radius = Math.min(width, height) / 3;
      visibleNodes.forEach((node, i) => {
        const angle = (i / visibleNodes.length) * 2 * Math.PI;
        const x = width / 2 + radius * Math.cos(angle);
        const y = height / 2 + radius * Math.sin(angle);
        // Set initial position
        node.x = x;
        node.y = y;
        // Set initial velocity to 0 to prevent jerky movement
        node.vx = 0;
        node.vy = 0;
      });
    }

    // Create links with proper source/target references - only include links where both nodes exist
    const links = visibleEdges
      .map((edge) => {
        const sourceNode = visibleNodes.find((n) => n.id === edge.from);
        const targetNode = visibleNodes.find((n) => n.id === edge.to);
        if (!sourceNode || !targetNode) return null;
        return {
          source: sourceNode,
          target: targetNode,
          label: edge.label,
          id: edge.id,
        };
      })
      .filter((link) => link !== null) as Array<{
      source: Node;
      target: Node;
      label: string;
      id: string;
    }>;

    // Create simulation with reduced pushing force
    const simulation = d3
      .forceSimulation(visibleNodes as any)
      .force(
        "link",
        d3
          .forceLink(links as any)
          .id((d: any) => d.id)
          .distance((selectedPath || selectedSubquery !== null) ? 220 : 160)
          .strength((selectedPath || selectedSubquery !== null) ? 0.3 : 0.1)
      )
      .force("charge", d3.forceManyBody().strength((selectedPath || selectedSubquery !== null) ? -700 : -400))
      .force("collision", d3.forceCollide().radius(70).strength(0.8))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("x", d3.forceX(width / 2).strength(0.015))
      .force("y", d3.forceY(height / 2).strength(0.015))
      .alphaDecay(0.02)
      .alphaMin(0.001)
      .velocityDecay(0.3);

    simulationRef.current = simulation as any;
    
    // Set up tick handler
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x ?? width / 2)
        .attr("y1", (d: any) => d.source.y ?? height / 2)
        .attr("x2", (d: any) => d.target.x ?? width / 2)
        .attr("y2", (d: any) => d.target.y ?? height / 2);

      edgeLabel
        .attr("x", (d: any) => ((d.source.x ?? width / 2) + (d.target.x ?? width / 2)) / 2)
        .attr("y", (d: any) => ((d.source.y ?? height / 2) + (d.target.y ?? height / 2)) / 2);

      node.attr("transform", (d: any) => `translate(${d.x ?? width / 2},${d.y ?? height / 2})`);
    });

    // Add arrowhead marker
    svgSelection
      .append("defs")
      .append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 28)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "var(--color-black-30)")
      .attr("opacity", 0.6);

    // Draw edges
    const link = g
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("x1", (d: any) => d.source.x ?? width / 2)
      .attr("y1", (d: any) => d.source.y ?? height / 2)
      .attr("x2", (d: any) => d.target.x ?? width / 2)
      .attr("y2", (d: any) => d.target.y ?? height / 2)
      .attr("stroke", "var(--color-black-30)")
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.6)
      .attr("marker-end", "url(#arrowhead)");

    // Draw edge labels
    const edgeLabel = g
      .append("g")
      .selectAll("text")
      .data(links)
      .join("text")
      .attr("font-size", 11)
      .attr("fill", "var(--color-black-70)")
      .attr("text-anchor", "middle")
      .attr("dy", -5)
      .text((d: any) => d.label)
      .attr("opacity", 0.7);

    // Draw nodes
    const node = g
      .append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(visibleNodes)
      .join("g")
      .attr("class", "node-group")
      .attr("cursor", "pointer")
      .attr("transform", (d: any) => `translate(${d.x ?? width / 2},${d.y ?? height / 2})`)
      .call(
        d3
          .drag<any, any>()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended) as any
      );

    // Node circles
    node
      .append("circle")
      .attr("r", 24)
      .attr("fill", (d: any) => nodeTypeColors[d.type] || "var(--color-text)")
      .attr("stroke", (d: any) => {
        if (selectedSubquery !== null && highlightedNodeIds.includes(d.id)) {
          return "var(--color-orange-500)"; // Indigo for subquery highlighting
        }
        return "var(--color-black-50)";
      })
      .attr("stroke-width", (d: any) => {
        if (selectedSubquery !== null && highlightedNodeIds.includes(d.id)) {
          return 3; // Thicker stroke for subquery highlighting
        }
        return 2;
      })
      .attr("opacity", 0.9);

    // Node labels
    node
      .append("text")
      .attr("dy", 40)
      .attr("text-anchor", "middle")
      .attr("font-size", 13)
      .attr("fill", "var(--color-black-90)")
      .attr("font-weight", 500)
      .text((d: any) =>
        d.label.length > 20 ? d.label.substring(0, 20) + "..." : d.label
      );

    // Node interactions
    node
      .on("click", (event, d: any) => {
        event.stopPropagation();
        setSelectedNode(d.id);
        setActiveTab("Details");
      })
      .on("mouseenter", (event) => {
        d3.select(event.currentTarget)
          .select("circle")
          .transition()
          .duration(200)
          .attr("r", 28)
          .attr("opacity", 1);
      })
      .on("mouseleave", (event) => {
        d3.select(event.currentTarget)
          .select("circle")
          .transition()
          .duration(200)
          .attr("r", 24)
          .attr("opacity", 0.9);
      });

    // Update positions on simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x ?? width / 2)
        .attr("y1", (d: any) => d.source.y ?? height / 2)
        .attr("x2", (d: any) => d.target.x ?? width / 2)
        .attr("y2", (d: any) => d.target.y ?? height / 2);

      edgeLabel
        .attr("x", (d: any) => ((d.source.x ?? width / 2) + (d.target.x ?? width / 2)) / 2)
        .attr("y", (d: any) => ((d.source.y ?? height / 2) + (d.target.y ?? height / 2)) / 2);

      node.attr("transform", (d: any) => `translate(${d.x ?? width / 2},${d.y ?? height / 2})`);
    });
    
    // Start simulation with initial positions already set
    // Run simulation for a few ticks immediately to settle nodes before display
    // We'll use a separate temporary simulation for pre-settling to avoid consuming alpha
    const tempSimulation = d3
      .forceSimulation(visibleNodes as any)
      .force("link", d3.forceLink(links as any).id((d: any) => d.id).distance((selectedPath || selectedSubquery !== null) ? 250 : 180).strength((selectedPath || selectedSubquery !== null) ? 0.3 : 0.1))
      .force("charge", d3.forceManyBody().strength((selectedPath || selectedSubquery !== null) ? -800 : -500))
      .force("collision", d3.forceCollide().radius(80).strength(0.7))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("x", d3.forceX(width / 2).strength(0.015))
      .force("y", d3.forceY(height / 2).strength(0.015))
      .alpha(1)
      .alphaDecay(0);
    
    // Force a few ticks to ensure nodes are positioned before display
    for (let i = 0; i < 50; i++) {
      tempSimulation.tick();
    }
    
    tempSimulation.stop();
    
    // Update positions after initial ticks
    link
      .attr("x1", (d: any) => d.source.x ?? width / 2)
      .attr("y1", (d: any) => d.source.y ?? height / 2)
      .attr("x2", (d: any) => d.target.x ?? width / 2)
      .attr("y2", (d: any) => d.target.y ?? height / 2);

    edgeLabel
      .attr("x", (d: any) => ((d.source.x ?? width / 2) + (d.target.x ?? width / 2)) / 2)
      .attr("y", (d: any) => ((d.source.y ?? height / 2) + (d.target.y ?? height / 2)) / 2);

    node.attr("transform", (d: any) => `translate(${d.x ?? width / 2},${d.y ?? height / 2})`);
    
    // Now start the actual simulation for smooth animation
    // D3 force simulations start automatically, but we need to ensure it's running
    // Start it immediately with full alpha
    simulation.alpha(1).restart();
    
    // Also ensure it continues running by checking after a brief moment
    requestAnimationFrame(() => {
      if (simulation.alpha() < 0.001) {
        simulation.alpha(0.3).restart();
      }
    });

    // Click on background to deselect
    svgSelection.on("click", () => {
      setSelectedNode(null);
    });

    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.1).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [selectedPath, selectedSubquery, subqueries]); // Re-run when path or subquery selection changes

  // Separate effect to update node appearance when selection changes
  useEffect(() => {
    if (!svgRef.current) return;
    
    const svg = d3.select(svgRef.current);
    const g = svg.select<SVGGElement>("g");
    if (g.empty()) return;
    
    // Get highlighted node IDs for subquery
    let highlightedNodeIds: string[] = [];
    if (selectedSubquery !== null) {
      const subquery = subqueries[selectedSubquery];
      if (subquery) {
        subquery.memories.forEach(memory => {
          if (memory.type === "Memory Path") {
            const path = memoryPaths.find(p => p.title === memory.title);
            if (path) {
              highlightedNodeIds.push(...path.nodes);
            }
          }
        });
      }
    }
    
    // Select node groups using the class we added
    const nodesGroup = g.select<SVGGElement>(".nodes");
    if (nodesGroup.empty()) return;
    
    const nodeGroups = nodesGroup.selectAll<SVGGElement, Node>(".node-group");
    
    // Update circle stroke for selected nodes
    nodeGroups.each(function(d: any) {
      if (!d) return; // Guard against undefined data
      const nodeGroup = d3.select(this);
      const circle = nodeGroup.select("circle");
      if (circle.empty()) return;
      const isSelected = selectedNode === d.id;
      const isHighlighted = selectedSubquery !== null && highlightedNodeIds.includes(d.id);
      
      let strokeColor = "var(--color-black-50)";
      let strokeWidth = 2;
      
      if (isSelected) {
        strokeColor = "var(--color-orange-500)";
        strokeWidth = 3;
      } else if (isHighlighted) {
        strokeColor = "var(--color-orange-500)";
        strokeWidth = 3;
      }
      
      circle
        .attr("stroke", strokeColor)
        .attr("stroke-width", strokeWidth);
    });
  }, [selectedNode, selectedSubquery, subqueries]);

  const selectedDetails = selectedNode ? sampleNodeDetails[selectedNode] : null;

  return (
    <div className="relative h-full w-full min-h-0">
      {/* Graph Visualization - Full Viewport */}
      <div className="absolute inset-0 border border-black/10 rounded-lg bg-black/5">
        {/* Collapsible Legend */}
        <div className="absolute top-4 left-4 z-10 bg-black/5 backdrop-blur-sm border border-black/10 rounded-lg shadow-sm">
          <button
            onClick={() => setLegendCollapsed(!legendCollapsed)}
            className="w-full flex items-center justify-between gap-2 p-3 hover:bg-black/10 transition-colors rounded-lg"
          >
            <p className="text-sm font-semibold text-text">Node Types</p>
            <svg
              className={`w-4 h-4 transition-transform text-text-secondary ${
                legendCollapsed ? "-rotate-90" : ""
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          {!legendCollapsed && (
            <div className="p-3 pt-0 grid grid-cols-3 gap-x-4 gap-y-2">
              {Object.entries(nodeTypeColors).map(([type, color]) => (
                <div key={type} className="flex items-center gap-2">
                  <div
                    className="w-3.5 h-3.5 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-xs text-text-secondary">{type}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {(selectedPath || selectedSubquery !== null) && (
          <div className="absolute top-4 right-4 z-10">
            <button
              onClick={() => {
                setSelectedPath(null);
                setSelectedSubquery(null);
              }}
              className="px-3 py-1.5 bg-black/10 hover:bg-black/20 border border-black/20 rounded-lg text-sm text-text transition-colors flex items-center space-x-1"
            >
              <svg
                className="w-3 h-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              <span>Clear Focus</span>
            </button>
          </div>
        )}

          <svg
            ref={svgRef}
            className="w-full h-full"
            style={{ background: "transparent" }}
          />
        </div>

      {/* Details Panel - Overlay Card */}
      <div className={`absolute top-4 right-4 bottom-4 z-20 bg-white border-2 border-orange-500-30 rounded-lg shadow-lg overflow-hidden flex flex-col transition-all duration-300 ${
        isDetailsCollapsed ? 'w-12' : 'w-96'
      }`}>
          {isDetailsCollapsed ? (
            <button
              onClick={() => setIsDetailsCollapsed(false)}
              className="text-orange-500 hover:text-orange-600 transition-colors p-3 w-full flex-1 flex items-center justify-center"
              title="Expand Details"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          ) : (
            <div className="flex flex-col flex-1 min-h-0">
              <div className="p-4 border-b border-orange-500-20 bg-orange-500-10 flex items-center justify-between flex-shrink-0">
                <div>
                  <h2 className="text-lg font-semibold text-orange-500">Memory Details</h2>
                  <p className="text-sm text-text-secondary">Paths and information</p>
                </div>
                <button
                  onClick={() => setIsDetailsCollapsed(true)}
                  className="text-orange-500 hover:text-orange-600 transition-colors text-sm px-2 py-1"
                  title="Collapse"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-black/10 flex-shrink-0">
                <button
                  onClick={() => {
                    setActiveTab("Paths");
                    setSelectedSubquery(null);
                  }}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeTab === "Paths"
                      ? "text-text border-b-2 border-orange-500"
                      : "text-text-secondary hover:text-text"
                  }`}
                >
                  Paths
                </button>
                <button
                  onClick={() => {
                    setActiveTab("Details");
                    setSelectedSubquery(null);
                  }}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeTab === "Details"
                      ? "text-text border-b-2 border-orange-500"
                      : "text-text-secondary hover:text-text"
                  }`}
                >
                  Details
                </button>
                <button
                  onClick={() => {
                    setActiveTab("Subqueries");
                    setSelectedPath(null);
                  }}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeTab === "Subqueries"
                      ? "text-text border-b-2 border-orange-500"
                      : "text-text-secondary hover:text-text"
                  }`}
                >
                  Subqueries
                </button>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto p-4 min-h-0">
                {activeTab === "Details" && selectedDetails ? (
                  <div className="space-y-4">
                    <div>
                      <div className="text-xs text-text-secondary uppercase mb-1">{selectedDetails.type}</div>
                      <h3 className="text-lg font-semibold text-text mb-2">{selectedDetails.title}</h3>
                      <p className="text-sm text-text-secondary">{selectedDetails.description}</p>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-text-secondary">Activation Score</span>
                        <span className="text-sm font-medium text-text">{selectedDetails.activationScore}%</span>
                      </div>
                      <div className="w-full bg-black/10 rounded-full h-2">
                        <div
                          className="bg-success h-2 rounded-full transition-all"
                          style={{ width: `${selectedDetails.activationScore}%` }}
                        ></div>
                      </div>
                    </div>

                    <div>
                      <div className="text-sm text-text-secondary mb-2">Tags</div>
                      <div className="flex flex-wrap gap-2">
                        {selectedDetails.tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-2 py-1 bg-black/10 rounded text-xs text-text"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="text-sm text-text-secondary mb-2">Metadata</div>
                      <div className="space-y-1 text-xs text-text">
                        {Object.entries(selectedDetails.metadata).map(([key, value]) => (
                          <div key={key}>
                            <span className="text-text-secondary">{key}:</span> {value}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : activeTab === "Subqueries" ? (
                  <div className="space-y-3">
                    {subqueries.length === 0 ? (
                      <div className="text-center py-8 text-text-secondary">
                        <p className="text-sm">No subqueries available.</p>
                        <p className="text-xs mt-2">Run a query to see subqueries here.</p>
                      </div>
                    ) : (
                      subqueries.map((sq, idx) => {
                        // Separate Memory Paths from Reasoning Bank entries
                        const pathsInSubquery = sq.memories
                          .filter(m => m.type === "Memory Path")
                          .map(m => memoryPaths.find(p => p.title === m.title))
                          .filter(Boolean) as MemoryPath[];
                        
                        const reasoningBankEntries = sq.memories.filter(m => m.type === "Reasoning Bank");
                        
                        return (
                          <div
                            key={sq.stepId}
                            className={`p-3.5 cursor-pointer transition-all border rounded-lg ${
                              selectedSubquery === idx
                                ? "border-orange-500-50 bg-orange-500-10 shadow-lg"
                                : "border-black/10 hover:border-black/20 hover:bg-black/8"
                            }`}
                            onClick={() => {
                              setSelectedSubquery(selectedSubquery === idx ? null : idx);
                              setSelectedPath(null);
                            }}
                          >
                            <div className="space-y-2.5">
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1">
                                  <div className="text-xs text-text-secondary uppercase mb-1">Subquery {idx + 1}</div>
                                  <p className="text-sm font-medium text-text leading-snug">{sq.subquery}</p>
                                </div>
                                {selectedSubquery === idx && (
                                  <div className="w-2 h-2 rounded-full bg-orange-500 flex-shrink-0 mt-1"></div>
                                )}
                              </div>
                              
                              <div className="text-xs text-text-secondary">
                                {pathsInSubquery.length} {pathsInSubquery.length === 1 ? 'path' : 'paths'} retrieved
                                {reasoningBankEntries.length > 0 && (
                                  <span className="ml-1">
                                    • {reasoningBankEntries.length} reasoning {reasoningBankEntries.length === 1 ? 'pattern' : 'patterns'}
                                  </span>
                                )}
                              </div>
                              
                              {(pathsInSubquery.length > 0 || reasoningBankEntries.length > 0) && (
                                <div className="space-y-1.5 pt-1 border-t border-black/10">
                                  {pathsInSubquery.length > 0 && (
                                    <>
                                      {pathsInSubquery.map((path, pathIdx) => (
                                        <div key={`path-${pathIdx}`} className="text-xs text-text-secondary">
                                          <span className="font-medium text-text">Memory Path:</span> {path.title}
                                        </div>
                                      ))}
                                    </>
                                  )}
                                  {reasoningBankEntries.length > 0 && (
                                    <>
                                      {reasoningBankEntries.map((rb, rbIdx) => (
                                        <div key={`rb-${rbIdx}`} className="text-xs text-text-secondary">
                                          <span className="font-medium text-text">Reasoning Bank:</span> {rb.title}
                                        </div>
                                      ))}
                                    </>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                ) : activeTab === "Paths" ? (
                  <div className="space-y-3">
                    {memoryPaths.map((path) => (
                      <div
                        key={path.id}
                        className={`p-3.5 cursor-pointer transition-all border rounded-lg ${
                          selectedPath?.id === path.id
                            ? "border-orange-500-50 bg-black/10 shadow-lg"
                            : "border-black/10 hover:border-black/20 hover:bg-black/8"
                        }`}
                        onClick={() => setSelectedPath(path.id === selectedPath?.id ? null : path)}
                      >
                        <div className="space-y-2.5">
                          <div className="flex items-start justify-between gap-2">
                            <h4 className="text-sm font-semibold leading-tight text-text">{path.title}</h4>
                            <span className="px-2 py-1 text-xs bg-black/10 rounded text-text-secondary shrink-0">
                              {path.nodeCount} nodes
                            </span>
                          </div>

                          <div className="flex gap-3 text-sm">
                            <div>
                              <span className="text-text-secondary">Activation:</span>
                              <span className="ml-1 font-mono font-semibold text-success">
                                {(path.activationScore * 100).toFixed(0)}%
                              </span>
                            </div>
                            <div>
                              <span className="text-text-secondary">Similarity:</span>
                              <span className="ml-1 font-mono font-semibold text-highlight">
                                {(path.similarityScore * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>

                          <div className="relative flex items-center gap-2 pt-1">
                            {path.nodes.slice(0, 8).map((nodeId, idx) => {
                              const node = sampleNodes.find((n) => n.id === nodeId);
                            const color = node ? nodeTypeColors[node.type] : "var(--color-text)";
                              return (
                                <div key={nodeId} className="relative flex items-center">
                                  <div
                                    className="w-2.5 h-2.5 rounded-full z-10"
                                    style={{ backgroundColor: color }}
                                    title={node?.label}
                                  />
                                  {idx < path.nodes.slice(0, 8).length - 1 && (
                                    <div
                                      className="absolute left-2.5 top-1/2 w-2 h-[1.5px]"
                                      style={{
                                        backgroundColor: color,
                                        transform: "translateY(-50%)",
                                      }}
                                    />
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-text-secondary text-sm">
                    <p>Select a node to view details</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
  );
}

function ReasoningBankView() {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="mb-4 flex items-center gap-3 px-4 flex-shrink-0">
        <svg
          className="w-5 h-5 text-orange-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
          />
        </svg>
        <div>
          <h2 className="text-base font-bold text-text">Reasoning Bank</h2>
          <p className="text-sm text-text-secondary">
            Past lessons from agent reasoning relevant to current queries
          </p>
        </div>
        <span className="ml-auto px-2 py-1 text-xs bg-black/10 rounded text-text-secondary">
          {reasoningBank.length} lessons
        </span>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 pb-6">
        <div className="space-y-4 w-full max-w-[95%]">
          {reasoningBank.map((entry) => (
            <div
              key={entry.rb_id}
              data-rb-id={entry.rb_id}
              className="p-5 shadow-sm border border-black/10 rounded-lg bg-black/5 transition-all"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <svg
                      className="w-4 h-4 shrink-0 text-highlight"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                      />
                    </svg>
                    <h3 className="text-sm font-bold text-text">
                      {entry.rb_id}: {entry.title}
                    </h3>
                  </div>
                </div>

                <div className="space-y-3 text-sm">
                  <div className="p-3 rounded-lg bg-error border-l-4 border-error">
                    <p className="font-semibold mb-1.5 text-error">What it means:</p>
                    <p className="text-text-secondary leading-relaxed">{entry.whatItMeans}</p>
                  </div>

                  <div className="p-3 rounded-lg bg-success-light border-l-4 border-success">
                    <p className="font-semibold mb-1.5 text-success-dark">How it helps:</p>
                    <p className="text-text-secondary leading-relaxed">{entry.howItHelps}</p>
                  </div>

                  <div className="p-3 rounded-lg bg-purple-light border-l-4 border-orange-500">
                    <p className="font-semibold mb-1.5 text-purple-dark">Key Lesson:</p>
                    <p className="leading-relaxed italic text-text">
                      &ldquo;{entry.keyLesson}&rdquo;
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1.5 pt-2">
                  {entry.tags.slice(0, 6).map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-1 text-xs bg-black/10 rounded border border-black/20 text-text-secondary"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
