import { useState, useRef, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import * as d3 from "d3";

interface Node {
  id: string;
  label: string;
  type: "Event" | "DataSource" | "AgentAnswer" | "AgentAction" | "UserRequest" | "UserPreference";
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface Edge {
  id: string;
  from: string;
  to: string;
  label: string;
}

interface NodeDetails {
  id: string;
  type: string;
  title: string;
  description: string;
  activationScore: number;
  tags: string[];
  metadata: {
    [key: string]: string | undefined;
  };
}

const sampleNodes: Node[] = [
  { id: "N1001", label: "Patient Adherence +23%", type: "AgentAnswer" },
  { id: "N1002", label: "Link EHR to Prescription Data", type: "AgentAction" },
  { id: "N1003", label: "Researcher Prefers Charts", type: "UserPreference" },
  { id: "N1004", label: "Generate Cohort Analysis", type: "AgentAction" },
  { id: "N1005", label: "B:ClinicalTrialGuidelines", type: "DataSource" },
  { id: "N1006", label: "Dosage Adjustment 15mg", type: "AgentAnswer" },
  { id: "N1007", label: "Q3 Research Summary", type: "DataSource" },
  { id: "N1008", label: "2026 Telehealth Initiative", type: "Event" },
  { id: "N1009", label: "Remote Monitoring Success", type: "AgentAnswer" },
  { id: "N1010", label: "Adverse Event Correlation", type: "AgentAction" },
  { id: "N1011", label: "Compare Treatment Efficacy", type: "UserRequest" },
  { id: "N1012", label: "Phase III Trial Data", type: "DataSource" },
  { id: "N1013", label: "Regulatory Approval", type: "Event" },
  { id: "N1014", label: "Merge Patient Demographics", type: "AgentAction" },
  { id: "N1015", label: "Patient Enrollment Data...", type: "DataSource" },
  { id: "N1016", label: "Treatment Response Data...", type: "DataSource" },
  { id: "N1017", label: "Efficacy Analysis Result", type: "AgentAnswer" },
  { id: "N1018", label: "C:StatisticalMethodology", type: "DataSource" },
  { id: "N1019", label: "Drug A vs Drug B Comparison", type: "AgentAnswer" },
];

const sampleEdges: Edge[] = [
  { id: "E3001", from: "N1001", to: "N1002", label: "Provides the finding that directly fed into the action to link patient records" },
  { id: "E3002", from: "N1003", to: "N1004", label: "Tailored the analysis format to match the user's preference for visual presentation" },
  { id: "E3003", from: "N1006", to: "N1007", label: "Documented the dosage adjustment recommendation in the quarterly research summary" },
  { id: "E3004", from: "N1008", to: "N1009", label: "Shaped the analysis by triggering investigation into remote monitoring performance" },
  { id: "E3005", from: "N1009", to: "N1010", label: "Used the remote monitoring findings to inform the adverse event correlation methodology" },
  { id: "E3006", from: "N1010", to: "N1011", label: "Triggered the user request for treatment efficacy comparison based on the analysis results" },
  { id: "E3007", from: "N1010", to: "N1012", label: "Used the Phase III trial dataset to perform the adverse event correlation analysis" },
  { id: "E3008", from: "N1013", to: "N1014", label: "Applied the regulatory approval event context to the data merge action" },
  { id: "E3009", from: "N1015", to: "N1014", label: "Provided patient enrollment data that was merged with demographic information" },
  { id: "E3010", from: "N1016", to: "N1014", label: "Supplied treatment response metrics that were integrated into the merge" },
  { id: "E3011", from: "N1014", to: "N1017", label: "Informed the efficacy analysis result through the merged patient-adjusted data" },
  { id: "E3012", from: "N1018", to: "N1014", label: "Derived the methodology for statistical analysis from the source document" },
];

const nodeTypeColors: Record<string, string> = {
  Event: "#6366f1",
  DataSource: "#0ea5e9",
  AgentAnswer: "#22c55e",
  AgentAction: "#f97316",
  UserRequest: "#fbbf24",
  UserPreference: "#a855f7",
};

interface MemoryPath {
  id: string;
  title: string;
  description: string;
  nodes: string[];
  activationScore: number;
  similarityScore: number;
  relevance: string;
  nodeCount: number;
}

const memoryPaths: MemoryPath[] = [
  {
    id: "path_a",
    title: "Patient-Adjusted Efficacy Analysis",
    description: "Path tracking patient demographic adjustments to efficacy calculations, including data merges and methodology references.",
    nodes: ["N1014", "N1015", "N1016", "N1017", "N1018"],
    activationScore: 0.89,
    similarityScore: 0.92,
    relevance: "Critical for understanding true treatment efficacy when patient demographics distort raw metrics.",
    nodeCount: 5,
  },
  {
    id: "path_b",
    title: "Dosage Optimization Strategy",
    description: "Path showing dosage adjustment recommendations based on efficacy analysis and user preferences.",
    nodes: ["N1003", "N1004", "N1005", "N1006", "N1007"],
    activationScore: 0.87,
    similarityScore: 0.88,
    relevance: "Demonstrates how user preferences and clinical guidelines inform dosage optimization decisions.",
    nodeCount: 5,
  },
  {
    id: "path_c",
    title: "Patient Adherence Impact",
    description: "Path connecting patient adherence analysis to actionable recommendations and documentation.",
    nodes: ["N1001", "N1002"],
    activationScore: 0.85,
    similarityScore: 0.86,
    relevance: "Shows the direct connection between adherence findings and data linking actions.",
    nodeCount: 2,
  },
  {
    id: "path_d",
    title: "Telehealth Monitoring Performance",
    description: "Path tracking telehealth monitoring analysis from event triggers through performance findings.",
    nodes: ["N1008", "N1009", "N1010"],
    activationScore: 0.91,
    similarityScore: 0.90,
    relevance: "Links strategic initiatives to performance analysis and actionable insights.",
    nodeCount: 3,
  },
  {
    id: "path_e",
    title: "Clinical Trial Analysis",
    description: "Path showing clinical trial analysis from user requests through data sources to actions.",
    nodes: ["N1011", "N1012", "N1010", "N1013"],
    activationScore: 0.83,
    similarityScore: 0.84,
    relevance: "Demonstrates how regulatory events and user requests drive data-driven analysis workflows.",
    nodeCount: 4,
  },
];

interface ReasoningBankEntry {
  rb_id: string;
  title: string;
  whatItMeans: string;
  howItHelps: string;
  keyLesson: string;
  tags: string[];
}

const reasoningBank: ReasoningBankEntry[] = [
  {
    rb_id: "RB-01",
    title: "Demographic-Aware Efficacy Calculation",
    whatItMeans: "When evaluating treatment efficacy, raw success rates can be misleading if patient demographics vary significantly across groups. Treatments may appear less effective simply because they were tested on higher-risk populations rather than actual performance issues.",
    howItHelps: "By merging patient demographic data with treatment response metrics, we can calculate demographic-adjusted efficacy that reveals true treatment performance. This prevents misallocation of resources away from effective treatments that were tested on challenging patient populations.",
    keyLesson: "Always adjust efficacy calculations for patient demographics before making treatment recommendations.",
    tags: ["efficacy", "demographics", "treatment_allocation", "data_merge"],
  },
  {
    rb_id: "RB-02",
    title: "Dosage Optimization Scenarios",
    whatItMeans: "When clinicians request dosage optimization, they prefer sensitivity analysis showing multiple scenarios rather than a single recommendation. This allows them to understand trade-offs and make informed decisions based on patient characteristics.",
    howItHelps: "Creating sensitivity analysis with multiple dosage scenarios (10mg, 15mg, 20mg, 25mg) helps clinicians understand the range of potential outcomes and choose the optimal strategy based on patient tolerance and clinical constraints.",
    keyLesson: "For dosage optimization tasks, always provide multiple scenarios with projected impacts rather than a single recommendation.",
    tags: ["dosage", "sensitivity_analysis", "scenarios", "clinical_preference"],
  },
  {
    rb_id: "RB-03",
    title: "User Preference Formatting",
    whatItMeans: "Different stakeholders prefer different data presentation formats. Researchers often prefer visualizations and charts over tabular data, while regulatory reviewers may prefer detailed tables with exact values.",
    howItHelps: "By tracking user preferences and formatting analysis results accordingly, we increase the likelihood that insights are understood and acted upon. Format alignment improves decision-making speed and accuracy in clinical settings.",
    keyLesson: "Match the analysis format to user preferences—visualizations for researchers, detailed tables for regulatory review.",
    tags: ["formatting", "user_preference", "presentation", "stakeholder"],
  },
];


const sampleNodeDetails: Record<string, NodeDetails> = {
  "N1001": {
    id: "N1001",
    type: "AgentAnswer",
    title: "Patient Adherence +23%",
    description: "Analysis showing that patients with medication reminders demonstrated a 23% adherence improvement compared to those without reminders. This finding was critical for treatment protocol optimization and resource allocation decisions.",
    activationScore: 87,
    tags: ["patient_adherence", "medication", "q3_2025", "treatment"],
    metadata: {
      analysis_types: "cohort_analysis,performance_analysis",
      metrics: "adherence_rate,treatment_outcome",
      conv_id: "2025-11-15_Med_Q3Protocol_01",
      ingestion_time: "2025-11-15T15:45:00Z",
    },
  },
  "N1002": {
    id: "N1002",
    type: "AgentAction",
    title: "Link EHR to Prescription Data",
    description: "Action to link electronic health records with prescription fulfillment data. This linkage was necessary to properly track medication adherence and correlate with treatment outcomes.",
    activationScore: 78,
    tags: ["data_linking", "ehr", "prescription"],
    metadata: {
      status: "complete",
      parameter_field: "JOIN ehr_table ON prescription_table.patient_id = ehr_table.patient_id WHERE date_range = '2025-Q3'",
      conv_id: "2025-11-15_Med_Q3Protocol_01",
      ingestion_time: "2025-11-15T15:42:00Z",
    },
  },
  "N1003": {
    id: "N1003",
    type: "UserPreference",
    title: "Researcher Prefers Charts",
    description: "User preference indicating that the researcher prefers data presented in visual chart format rather than tables. This preference influences how analysis results are formatted.",
    activationScore: 95,
    tags: ["user_preference", "format", "researcher", "report_style"],
    metadata: {
      preference_type: "report_style",
      user_role: "Research Director",
      conv_id: "2025-10-20_Med_Preference_01",
      ingestion_time: "2025-10-20T10:15:00Z",
    },
  },
  "N1004": {
    id: "N1004",
    type: "AgentAction",
    title: "Generate Cohort Analysis",
    description: "Created a comprehensive cohort analysis for treatment efficacy scenarios. This analysis compared multiple treatment protocols and their projected impacts on patient outcomes and recovery rates.",
    activationScore: 91,
    tags: ["cohort_analysis", "treatment", "scenario"],
    metadata: {
      status: "complete",
      parameter_field: "scenarios: 4, variables: ['dosage_a', 'dosage_b', 'combination', 'standard'], sensitivity_range: ±15%",
      conv_id: "2025-11-10_Med_TreatmentAnalysis_01",
      ingestion_time: "2025-11-10T14:30:00Z",
    },
  },
  "N1005": {
    id: "N1005",
    type: "DataSource",
    title: "B:ClinicalTrialGuidelines",
    description: "Historical guidance document containing best practices and lessons learned from previous clinical trials. Includes recommendations from Q3 2024 and Q1 2025 reviews.",
    activationScore: 82,
    tags: ["guidance", "clinical_trial", "historical"],
    metadata: {
      source_type: "document",
      doc_pointer: "/documents/guidance/B_ClinicalTrialGuidelines.pdf",
      relevant_parts: "Section 3: Best Practices, Section 5: Lessons Learned",
      conv_id: "2025-09-01_Med_Guidance_01",
      ingestion_time: "2025-09-01T10:00:00Z",
    },
  },
  "N1006": {
    id: "N1006",
    type: "AgentAnswer",
    title: "Dosage Adjustment 15mg",
    description: "Recommended dosage adjustment to 15mg based on patient response analysis. This adjustment is projected to improve treatment efficacy by 8-12% while maintaining safety profile.",
    activationScore: 89,
    tags: ["dosage_optimization", "recommendation", "drug_a", "drug_b"],
    metadata: {
      analysis_types: "dosage_optimization,sensitivity_analysis",
      metrics: "efficacy_rate,adverse_events,patient_response",
      conv_id: "2025-11-10_Med_TreatmentAnalysis_01",
      ingestion_time: "2025-11-10T15:15:00Z",
    },
  },
  "N1007": {
    id: "N1007",
    type: "DataSource",
    title: "Q3 Research Summary",
    description: "Quarterly research summary presentation containing patient outcomes, treatment analysis, and clinical recommendations. Includes data from July through September 2025.",
    activationScore: 85,
    tags: ["presentation", "q3", "summary"],
    metadata: {
      source_type: "pbi",
      doc_pointer: "/presentations/Q3_2025_Research_Summary.pbix",
      relevant_parts: "Slide 4: Dosage Recommendations, Slide 7: Treatment Performance",
      conv_id: "2025-09-30_Med_Q3Summary_01",
      ingestion_time: "2025-09-30T16:00:00Z",
    },
  },
  "N1008": {
    id: "N1008",
    type: "Event",
    title: "2026 Telehealth Initiative",
    description: "Strategic initiative launched in early 2026 to expand telehealth monitoring capabilities and remote patient care. This event triggered multiple analysis requests and protocol optimizations.",
    activationScore: 88,
    tags: ["event", "telehealth", "2026", "initiative"],
    metadata: {
      source_type: "Calendar",
      start_date: "2026-01-01",
      end_date: "2026-12-31",
      conv_id: "2026-01-01_Med_Event_01",
      ingestion_time: "2026-01-01T00:00:00Z",
    },
  },
  "N1009": {
    id: "N1009",
    type: "AgentAnswer",
    title: "Remote Monitoring Success",
    description: "Analysis showing that remote monitoring protocols achieved 15-22% improvement in early intervention rates compared to traditional in-person visits. This finding supported the decision to expand telehealth infrastructure.",
    activationScore: 93,
    tags: ["remote_monitoring", "telehealth", "intervention", "performance"],
    metadata: {
      analysis_types: "performance_comparison,protocol_analysis",
      metrics: "intervention_rate,patient_satisfaction,outcome",
      conv_id: "2026-01-15_Med_TelehealthAnalysis_01",
      ingestion_time: "2026-01-15T11:20:00Z",
    },
  },
  "N1010": {
    id: "N1010",
    type: "AgentAction",
    title: "Adverse Event Correlation",
    description: "Grouped by treatment_type and patient_cohort; computed adverse event correlation. This analysis compared adverse event rates across different treatment protocols and patient demographics.",
    activationScore: 92,
    tags: ["adverse_events", "correlation", "safety", "analysis"],
    metadata: {
      status: "complete",
      parameter_field: "GROUP BY treatment_type, patient_cohort; METRIC: adverse_event_correlation",
      conv_id: "2025-07-11_Med_SafetyAnalysis_01",
      ingestion_time: "2025-07-11T12:00:00Z",
    },
  },
  "N1011": {
    id: "N1011",
    type: "UserRequest",
    title: "Compare Treatment Efficacy",
    description: "User requested comparison of treatment efficacy metrics for the Phase III trial. This analysis examined response rates, recovery metrics, and safety profiles across different treatment variations.",
    activationScore: 84,
    tags: ["user_request", "phase_iii", "treatment", "comparison"],
    metadata: {
      user_role: "Clinical Research Director",
      user_id: "user_456",
      conv_id: "2025-07-10_Med_TreatmentRequest_01",
      ingestion_time: "2025-07-10T09:30:00Z",
    },
  },
  "N1012": {
    id: "N1012",
    type: "DataSource",
    title: "Phase III Trial Data",
    description: "Comprehensive dataset containing efficacy metrics for the Phase III clinical trial. Includes patient response data, adverse event reports, and biomarker measurements by treatment arm and time point.",
    activationScore: 90,
    tags: ["clinical_trial", "phase_iii", "trial_data"],
    metadata: {
      source_type: "csv",
      doc_pointer: "/data/trials/PhaseIII_Trial_Data_May-Jul_2025.csv",
      relevant_parts: "Columns: treatment_arm, patient_id, response_rate, adverse_events, biomarkers",
      conv_id: "2025-07-10_Med_DataIngestion_01",
      ingestion_time: "2025-07-10T08:00:00Z",
    },
  },
  "N1013": {
    id: "N1013",
    type: "Event",
    title: "Regulatory Approval",
    description: "Regulatory agency approval granted for expanded treatment protocol. This event triggered efficacy analysis and protocol optimization for broader patient population.",
    activationScore: 79,
    tags: ["event", "regulatory", "approval", "protocol"],
    metadata: {
      source_type: "Calendar",
      start_date: "2025-07-05",
      end_date: "2025-07-05",
      conv_id: "2025-07-05_Med_Event_01",
      ingestion_time: "2025-07-05T10:00:00Z",
    },
  },
  "N1014": {
    id: "N1014",
    type: "AgentAction",
    title: "Merge Patient Demographics",
    description: "Action to merge patient demographic data with treatment response metrics. This merge was necessary to adjust efficacy calculations for demographic-adjusted analysis, accounting for population variations.",
    activationScore: 86,
    tags: ["data_merge", "demographics", "efficacy", "adjustment"],
    metadata: {
      status: "complete",
      parameter_field: "MERGE patient_demographics ON treatment_response.patient_id WHERE date_range = '2025-08'",
      conv_id: "2025-08-20_Med_DataMerge_01",
      ingestion_time: "2025-08-20T16:15:00Z",
    },
  },
  "N1015": {
    id: "N1015",
    type: "DataSource",
    title: "Patient Enrollment Data...",
    description: "Patient enrollment data covering May through July 2025. Contains detailed breakdown of patient recruitment across different sites, demographics, and time periods.",
    activationScore: 83,
    tags: ["enrollment", "recruitment", "patients"],
    metadata: {
      source_type: "csv",
      doc_pointer: "/data/enrollment/Patient_Enrollment_May-Jul_2025.csv",
      relevant_parts: "All columns, date_range: 2025-05-01 to 2025-07-31",
      conv_id: "2025-08-15_Med_DataIngestion_02",
      ingestion_time: "2025-08-15T09:00:00Z",
    },
  },
  "N1016": {
    id: "N1016",
    type: "DataSource",
    title: "Treatment Response Data...",
    description: "Treatment response metrics dataset containing efficacy rates, adverse events, and patient outcomes across all treatment arms. Includes both primary and secondary endpoint data.",
    activationScore: 88,
    tags: ["treatment", "response", "metrics"],
    metadata: {
      source_type: "csv",
      doc_pointer: "/data/treatment/Treatment_Response_May-Jul_2025.csv",
      relevant_parts: "Columns: treatment_arm, efficacy_rate, adverse_events, patient_outcome, date",
      conv_id: "2025-08-15_Med_DataIngestion_03",
      ingestion_time: "2025-08-15T10:00:00Z",
    },
  },
  "N1017": {
    id: "N1017",
    type: "AgentAnswer",
    title: "Efficacy Analysis Result",
    description: "Demographic-adjusted efficacy analysis results showing corrected performance metrics after accounting for patient population variations. This analysis revealed that some treatments appeared less effective due to demographic factors rather than actual performance issues.",
    activationScore: 91,
    tags: ["efficacy", "demographic_adjusted", "analysis"],
    metadata: {
      analysis_types: "efficacy_adjustment,demographic_analysis",
      metrics: "efficacy_rate,adverse_events,demographic_adjusted_efficacy",
      conv_id: "2025-08-20_Med_EfficacyAnalysis_01",
      ingestion_time: "2025-08-20T16:45:00Z",
    },
  },
  "N1018": {
    id: "N1018",
    type: "DataSource",
    title: "C:StatisticalMethodology",
    description: "Analysis document containing statistical methodology for demographic-adjusted efficacy calculations. This document explains how to properly account for patient demographics when evaluating treatment performance.",
    activationScore: 87,
    tags: ["analysis", "efficacy", "demographics", "methodology"],
    metadata: {
      source_type: "document",
      doc_pointer: "/documents/analysis/C_StatisticalMethodology_v2.1.pdf",
      relevant_parts: "Section 2: Methodology, Section 4: Calculation Examples",
      conv_id: "2025-08-01_Med_Methodology_01",
      ingestion_time: "2025-08-01T14:00:00Z",
    },
  },
  "N1019": {
    id: "N1019",
    type: "AgentAnswer",
    title: "Drug A vs Drug B Comparison",
    description: "Comparative analysis showing that Drug A achieved 20-28% efficacy advantage over Drug B in similar patient populations. This finding supported treatment protocol recommendations.",
    activationScore: 94,
    tags: ["comparison", "drug_a", "drug_b", "efficacy"],
    metadata: {
      analysis_types: "treatment_comparison,performance_analysis",
      metrics: "efficacy_rate,adverse_events,patient_response",
      conv_id: "2025-11-08_Med_TreatmentComparison_01",
      ingestion_time: "2025-11-08T14:00:00Z",
    },
  },
};

interface ReasoningStep {
  text: string;
  duration?: string;
  isProcessing?: boolean;
  subquery?: string;
  id?: number;
  memories?: Array<{
    type: string;
    title: string;
    description: string;
  }>;
  collectedMemories?: Array<{
    subquery: string;
    memories: Array<{
      type: string;
      title: string;
      description: string;
    }>;
  }>;
}

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
      <header className="bg-[#6366f1]/10 border-b border-[#6366f1]/20 flex-shrink-0 relative">
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
      <div className="flex-1 flex flex-col bg-[#6366f1]/5 border-2 border-[#6366f1]/30 rounded-lg overflow-hidden min-h-0">
        <div className="p-4 border-b border-[#6366f1]/20 bg-[#6366f1]/10 flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-[#6366f1]">Memoria Reasoning</h2>
            <p className="text-sm text-text-secondary">Step-by-step memory retrieval process</p>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
          {reasoningSteps.length > 0 ? (
            <>
              {reasoningSteps.map((step, idx) => {
                // Determine color based on step type
                let borderColor = "border-[#6366f1]";
                let bgColor = "bg-[#6366f1]/5";
                if (step.subquery) {
                  borderColor = "border-[#6366f1]";
                  bgColor = "bg-[#6366f1]/5";
                } else if (step.memories && step.memories.length > 0) {
                  borderColor = "border-[#22c55e]";
                  bgColor = "bg-[#22c55e]/5";
                } else if (step.collectedMemories) {
                  borderColor = "border-[#a855f7]";
                  bgColor = "bg-[#a855f7]/5";
                } else if (step.text.includes("Evaluating") || step.text.includes("Need additional")) {
                  borderColor = "border-[#f59e0b]";
                  bgColor = "bg-[#f59e0b]/5";
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
                        <div className="mt-2 p-2 bg-[#6366f1]/10 rounded border-l-4 border-[#6366f1]">
                          <p className="text-xs font-semibold text-[#6366f1] mb-1">Subquery:</p>
                          <p className="text-text italic text-[#0f172a]">"{step.subquery}"</p>
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
                                    className="w-full p-2 bg-[#22c55e]/10 rounded border-l-4 border-[#22c55e] hover:bg-[#22c55e]/15 transition-colors text-left"
                                  >
                                    <div className="flex items-center justify-between mb-1">
                                      <div className="flex items-center gap-2">
                                        <span className="text-xs font-semibold text-[#22c55e]">{memory.type}</span>
                                        <span className="text-xs font-medium text-text">{memory.title}</span>
                                      </div>
                                      <svg
                                        className={`w-3 h-3 text-[#22c55e] transition-transform flex-shrink-0 ${isMemoryExpanded ? 'transform rotate-180' : ''}`}
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
                                        <p className="text-xs font-semibold text-[#22c55e] mb-1">Nodes in path ({pathNodes.length}):</p>
                                        {pathNodes.map((node, nodeIdx) => {
                                          const nodeColors = [
                                            { bg: "bg-[#6366f1]/10", border: "border-[#6366f1]", text: "text-[#6366f1]" },
                                            { bg: "bg-[#0ea5e9]/10", border: "border-[#0ea5e9]", text: "text-[#0ea5e9]" },
                                            { bg: "bg-[#f97316]/10", border: "border-[#f97316]", text: "text-[#f97316]" },
                                            { bg: "bg-[#a855f7]/10", border: "border-[#a855f7]", text: "text-[#a855f7]" },
                                            { bg: "bg-[#ec4899]/10", border: "border-[#ec4899]", text: "text-[#ec4899]" },
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
                                      ? "bg-[#0ea5e9]/10 border-[#0ea5e9]"
                                      : memory.type === "DataSource"
                                      ? "bg-[#f97316]/10 border-[#f97316]"
                                      : "bg-[#22c55e]/10 border-[#22c55e]"
                                  }`}>
                                    <div className="flex items-center gap-2 mb-1 pr-10">
                                      <span className={`text-xs font-semibold ${
                                        memory.type === "Reasoning Bank"
                                          ? "text-[#0ea5e9]"
                                          : memory.type === "DataSource"
                                          ? "text-[#f97316]"
                                          : "text-[#22c55e]"
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
                                                element.classList.add("ring-2", "ring-[#0ea5e9]", "ring-offset-2");
                                                setTimeout(() => {
                                                  element.classList.remove("ring-2", "ring-[#0ea5e9]", "ring-offset-2");
                                                }, 2000);
                                              }
                                            }
                                          }, 100);
                                        }}
                                        className="absolute top-0 right-0 bottom-0 text-[#0ea5e9] hover:text-[#0284c7] transition-colors text-xs px-3 rounded-r hover:bg-[#0ea5e9]/10 flex items-center justify-center"
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
                                  className="w-full p-2 bg-[#6366f1]/10 rounded border-l-4 border-[#6366f1] hover:bg-[#6366f1]/15 transition-colors text-left"
                                >
                                  <div className="flex items-center justify-between">
                                    <div className="flex-1">
                                      <p className="text-xs font-semibold text-[#6366f1] mb-1">Subquery {groupIdx + 1}:</p>
                                      <p className="text-xs text-text italic">"{group.subquery}"</p>
                                    </div>
                                    <svg
                                      className={`w-4 h-4 text-[#6366f1] transition-transform flex-shrink-0 ${isSubqueryExpanded ? 'transform rotate-180' : ''}`}
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
                                              className="w-full p-2 bg-[#22c55e]/10 rounded border-l-4 border-[#22c55e] hover:bg-[#22c55e]/15 transition-colors text-left"
                                            >
                                              <div className="flex items-center justify-between mb-1">
                                                <div className="flex items-center gap-2">
                                                  <span className="text-xs font-semibold text-[#22c55e]">{memory.type}</span>
                                                  <span className="text-xs font-medium text-text">{memory.title}</span>
                                                </div>
                                                <svg
                                                  className={`w-3 h-3 text-[#22c55e] transition-transform flex-shrink-0 ${isPathExpanded ? 'transform rotate-180' : ''}`}
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
                                                  <p className="text-xs font-semibold text-[#22c55e] mb-1">Nodes in path ({pathNodes.length}):</p>
                                                  {pathNodes.map((node, nodeIdx) => {
                                                    const nodeColors = [
                                                      { bg: "bg-[#6366f1]/10", border: "border-[#6366f1]", text: "text-[#6366f1]" },
                                                      { bg: "bg-[#0ea5e9]/10", border: "border-[#0ea5e9]", text: "text-[#0ea5e9]" },
                                                      { bg: "bg-[#f97316]/10", border: "border-[#f97316]", text: "text-[#f97316]" },
                                                      { bg: "bg-[#a855f7]/10", border: "border-[#a855f7]", text: "text-[#a855f7]" },
                                                      { bg: "bg-[#ec4899]/10", border: "border-[#ec4899]", text: "text-[#ec4899]" },
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
                                                ? "bg-[#0ea5e9]/10 border-[#0ea5e9]"
                                                : memory.type === "DataSource"
                                                ? "bg-[#f97316]/10 border-[#f97316]"
                                                : "bg-[#22c55e]/10 border-[#22c55e]"
                                            }`}>
                                              <div className="flex items-center gap-2 mb-1 pr-10">
                                                <span className={`text-xs font-semibold ${
                                                  memory.type === "Reasoning Bank"
                                                    ? "text-[#0ea5e9]"
                                                    : memory.type === "DataSource"
                                                    ? "text-[#f97316]"
                                                    : "text-[#22c55e]"
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
                                                          element.classList.add("ring-2", "ring-[#0ea5e9]", "ring-offset-2");
                                                          setTimeout(() => {
                                                            element.classList.remove("ring-2", "ring-[#0ea5e9]", "ring-offset-2");
                                                          }, 2000);
                                                        }
                                                      }
                                                    }, 100);
                                                  }}
                                                  className="absolute top-0 right-0 bottom-0 text-[#0ea5e9] hover:text-[#0284c7] transition-colors text-xs px-3 rounded-r hover:bg-[#0ea5e9]/10 flex items-center justify-center"
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
            className="flex-1 px-4 py-3 bg-background border border-black/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6366f1]/50 focus:border-[#6366f1]/50 text-text placeholder:text-gray-400 placeholder:opacity-70 text-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleQuery}
            disabled={isLoading || !query.trim()}
            className="relative w-12 h-12 bg-[#2563eb] hover:bg-[#1d4ed8] disabled:bg-gray-400 disabled:cursor-not-allowed rounded-lg flex items-center justify-center transition-colors flex-shrink-0"
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
    
    // Preserve zoom transform before removing elements
    const currentTransform = zoomTransformRef.current || d3.zoomIdentity;
    
    svgSelection.selectAll("*").remove();

    const width = svg.clientWidth || 800;
    const height = svg.clientHeight || 600;
    
    // Set explicit SVG dimensions
    svg.setAttribute("width", width.toString());
    svg.setAttribute("height", height.toString());

    const g = svgSelection.append("g");

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
          .distance((selectedPath || selectedSubquery !== null) ? 180 : 120)
          .strength((selectedPath || selectedSubquery !== null) ? 0.5 : 0.15)
      )
      .force("charge", d3.forceManyBody().strength((selectedPath || selectedSubquery !== null) ? -600 : -300))
      .force("collision", d3.forceCollide().radius(60).strength(0.9))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("x", d3.forceX(width / 2).strength(0.02))
      .force("y", d3.forceY(height / 2).strength(0.02))
      .alphaDecay(0.0228)
      .alphaMin(0.001)
      .velocityDecay(0.4);

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
      .attr("fill", "rgba(0, 0, 0, 0.3)")
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
      .attr("stroke", "rgba(0, 0, 0, 0.3)")
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
      .attr("fill", "rgba(0, 0, 0, 0.7)")
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
      .attr("fill", (d: any) => nodeTypeColors[d.type] || "#0f172a")
      .attr("stroke", (d: any) => {
        if (selectedSubquery !== null && highlightedNodeIds.includes(d.id)) {
          return "#6366f1"; // Indigo for subquery highlighting
        }
        return "rgba(0, 0, 0, 0.5)";
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
      .attr("fill", "rgba(0, 0, 0, 0.9)")
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
      .force("link", d3.forceLink(links as any).id((d: any) => d.id).distance((selectedPath || selectedSubquery !== null) ? 180 : 120).strength((selectedPath || selectedSubquery !== null) ? 0.5 : 0.15))
      .force("charge", d3.forceManyBody().strength((selectedPath || selectedSubquery !== null) ? -600 : -300))
      .force("collision", d3.forceCollide().radius(60).strength(0.9))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("x", d3.forceX(width / 2).strength(0.02))
      .force("y", d3.forceY(height / 2).strength(0.02))
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
      
      let strokeColor = "rgba(0, 0, 0, 0.5)";
      let strokeWidth = 2;
      
      if (isSelected) {
        strokeColor = "#6366f1";
        strokeWidth = 3;
      } else if (isHighlighted) {
        strokeColor = "#6366f1";
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
      <div className={`absolute top-4 right-4 bottom-4 z-20 bg-white border-2 border-[#6366f1]/30 rounded-lg shadow-lg overflow-hidden flex flex-col transition-all duration-300 ${
        isDetailsCollapsed ? 'w-12' : 'w-96'
      }`}>
          {isDetailsCollapsed ? (
            <button
              onClick={() => setIsDetailsCollapsed(false)}
              className="text-[#6366f1] hover:text-[#4f46e5] transition-colors p-3 w-full flex-1 flex items-center justify-center"
              title="Expand Details"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          ) : (
            <div className="flex flex-col flex-1 min-h-0">
              <div className="p-4 border-b border-[#6366f1]/20 bg-[#6366f1]/10 flex items-center justify-between flex-shrink-0">
                <div>
                  <h2 className="text-lg font-semibold text-[#6366f1]">Memory Details</h2>
                  <p className="text-sm text-text-secondary">Paths and information</p>
                </div>
                <button
                  onClick={() => setIsDetailsCollapsed(true)}
                  className="text-[#6366f1] hover:text-[#4f46e5] transition-colors text-sm px-2 py-1"
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
                      ? "text-text border-b-2 border-[#6366f1]"
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
                      ? "text-text border-b-2 border-[#6366f1]"
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
                      ? "text-text border-b-2 border-[#6366f1]"
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
                          className="bg-[#22c55e] h-2 rounded-full transition-all"
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
                                ? "border-[#6366f1]/50 bg-[#6366f1]/10 shadow-lg"
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
                                  <div className="w-2 h-2 rounded-full bg-[#6366f1] flex-shrink-0 mt-1"></div>
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
                            ? "border-[#6366f1]/50 bg-black/10 shadow-lg"
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
                              <span className="ml-1 font-mono font-semibold text-[#22c55e]">
                                {(path.activationScore * 100).toFixed(0)}%
                              </span>
                            </div>
                            <div>
                              <span className="text-text-secondary">Similarity:</span>
                              <span className="ml-1 font-mono font-semibold text-[#0ea5e9]">
                                {(path.similarityScore * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>

                          <div className="relative flex items-center gap-2 pt-1">
                            {path.nodes.slice(0, 8).map((nodeId, idx) => {
                              const node = sampleNodes.find((n) => n.id === nodeId);
                            const color = node ? nodeTypeColors[node.type] : "#0f172a";
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
          className="w-5 h-5 text-[#6366f1]"
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
                      className="w-4 h-4 shrink-0 text-[#0ea5e9]"
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
                  <div className="p-3 rounded-lg bg-[#fee2e2] border-l-4 border-[#f43f5e]">
                    <p className="font-semibold mb-1.5 text-[#b91c1c]">What it means:</p>
                    <p className="text-text-secondary leading-relaxed">{entry.whatItMeans}</p>
                  </div>

                  <div className="p-3 rounded-lg bg-[#dcfce7] border-l-4 border-[#22c55e]">
                    <p className="font-semibold mb-1.5 text-[#15803d]">How it helps:</p>
                    <p className="text-text-secondary leading-relaxed">{entry.howItHelps}</p>
                  </div>

                  <div className="p-3 rounded-lg bg-[#ede9fe] border-l-4 border-[#6366f1]">
                    <p className="font-semibold mb-1.5 text-[#4c1d95]">Key Lesson:</p>
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
