export interface Node {
  id: string;
  label: string;
  type:
    | "Event"
    | "DataSource"
    | "AgentAnswer"
    | "AgentAction"
    | "UserRequest"
    | "UserPreference";
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface Edge {
  id: string;
  from: string;
  to: string;
  label: string;
}

export interface NodeDetails {
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

export const sampleNodes: Node[] = [
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

export const sampleEdges: Edge[] = [
  {
    id: "E3001",
    from: "N1001",
    to: "N1002",
    label: "INFORMS_ACTION",
  },
  {
    id: "E3002",
    from: "N1003",
    to: "N1004",
    label: "FORMATS_ANALYSIS_FOR",
  },
  {
    id: "E3003",
    from: "N1006",
    to: "N1007",
    label: "DOCUMENTED_IN",
  },
  {
    id: "E3004",
    from: "N1008",
    to: "N1009",
    label: "TRIGGERS_ANALYSIS",
  },
  {
    id: "E3005",
    from: "N1009",
    to: "N1010",
    label: "INFORMS_METHOD",
  },
  {
    id: "E3006",
    from: "N1010",
    to: "N1011",
    label: "TRIGGERS_REQUEST",
  },
  {
    id: "E3007",
    from: "N1010",
    to: "N1012",
    label: "USES_DATASET",
  },
  {
    id: "E3008",
    from: "N1013",
    to: "N1014",
    label: "CONTEXT_FOR_ACTION",
  },
  {
    id: "E3009",
    from: "N1015",
    to: "N1014",
    label: "PROVIDES_DATA_FOR",
  },
  {
    id: "E3010",
    from: "N1016",
    to: "N1014",
    label: "SUPPLIES_METRICS_FOR",
  },
  {
    id: "E3011",
    from: "N1014",
    to: "N1017",
    label: "INFORMS_RESULT",
  },
  {
    id: "E3012",
    from: "N1018",
    to: "N1014",
    label: "DERIVES_METHOD_FOR",
  },
];

export interface MemoryPath {
  id: string;
  title: string;
  description: string;
  nodes: string[];
  activationScore: number;
  similarityScore: number;
  relevance: string;
  nodeCount: number;
}

export const memoryPaths: MemoryPath[] = [
  {
    id: "path_a",
    title: "Patient-Adjusted Efficacy Analysis",
    description:
      "Path tracking patient demographic adjustments to efficacy calculations, including data merges and methodology references.",
    nodes: ["N1014", "N1015", "N1016", "N1017", "N1018"],
    activationScore: 0.89,
    similarityScore: 0.92,
    relevance:
      "Critical for understanding true treatment efficacy when patient demographics distort raw metrics.",
    nodeCount: 5,
  },
  {
    id: "path_b",
    title: "Dosage Optimization Strategy",
    description:
      "Path showing dosage adjustment recommendations based on efficacy analysis and user preferences.",
    nodes: ["N1003", "N1004", "N1005", "N1006", "N1007"],
    activationScore: 0.87,
    similarityScore: 0.88,
    relevance:
      "Demonstrates how user preferences and clinical guidelines inform dosage optimization decisions.",
    nodeCount: 5,
  },
  {
    id: "path_c",
    title: "Patient Adherence Impact",
    description:
      "Path connecting patient adherence analysis to actionable recommendations and documentation.",
    nodes: ["N1001", "N1002"],
    activationScore: 0.85,
    similarityScore: 0.86,
    relevance:
      "Shows the direct connection between adherence findings and data linking actions.",
    nodeCount: 2,
  },
  {
    id: "path_d",
    title: "Telehealth Monitoring Performance",
    description:
      "Path tracking telehealth monitoring analysis from event triggers through performance findings.",
    nodes: ["N1008", "N1009", "N1010"],
    activationScore: 0.91,
    similarityScore: 0.9,
    relevance:
      "Links strategic initiatives to performance analysis and actionable insights.",
    nodeCount: 3,
  },
  {
    id: "path_e",
    title: "Clinical Trial Analysis",
    description:
      "Path showing clinical trial analysis from user requests through data sources to actions.",
    nodes: ["N1011", "N1012", "N1010", "N1013"],
    activationScore: 0.83,
    similarityScore: 0.84,
    relevance:
      "Demonstrates how regulatory events and user requests drive data-driven analysis workflows.",
    nodeCount: 4,
  },
];

export interface ReasoningBankEntry {
  rb_id: string;
  title: string;
  whatItMeans: string;
  howItHelps: string;
  keyLesson: string;
  tags: string[];
}

export const reasoningBank: ReasoningBankEntry[] = [
  {
    rb_id: "RB-01",
    title: "Demographic-Aware Efficacy Calculation",
    whatItMeans:
      "When evaluating treatment efficacy, raw success rates can be misleading if patient demographics vary significantly across groups. Treatments may appear less effective simply because they were tested on higher-risk populations rather than actual performance issues.",
    howItHelps:
      "By merging patient demographic data with treatment response metrics, we can calculate demographic-adjusted efficacy that reveals true treatment performance. This prevents misallocation of resources away from effective treatments that were tested on challenging patient populations.",
    keyLesson:
      "Always adjust efficacy calculations for patient demographics before making treatment recommendations.",
    tags: ["efficacy", "demographics", "treatment_allocation", "data_merge"],
  },
  {
    rb_id: "RB-02",
    title: "Dosage Optimization Scenarios",
    whatItMeans:
      "When clinicians request dosage optimization, they prefer sensitivity analysis showing multiple scenarios rather than a single recommendation. This allows them to understand trade-offs and make informed decisions based on patient characteristics.",
    howItHelps:
      "Creating sensitivity analysis with multiple dosage scenarios (10mg, 15mg, 20mg, 25mg) helps clinicians understand the range of potential outcomes and choose the optimal strategy based on patient tolerance and clinical constraints.",
    keyLesson:
      "For dosage optimization tasks, always provide multiple scenarios with projected impacts rather than a single recommendation.",
    tags: [
      "dosage",
      "sensitivity_analysis",
      "scenarios",
      "clinical_preference",
    ],
  },
  {
    rb_id: "RB-03",
    title: "User Preference Formatting",
    whatItMeans:
      "Different stakeholders prefer different data presentation formats. Researchers often prefer visualizations and charts over tabular data, while regulatory reviewers may prefer detailed tables with exact values.",
    howItHelps:
      "By tracking user preferences and formatting analysis results accordingly, we increase the likelihood that insights are understood and acted upon. Format alignment improves decision-making speed and accuracy in clinical settings.",
    keyLesson:
      "Match the analysis format to user preferences—visualizations for researchers, detailed tables for regulatory review.",
    tags: ["formatting", "user_preference", "presentation", "stakeholder"],
  },
];

export const sampleNodeDetails: Record<string, NodeDetails> = {
  N1001: {
    id: "N1001",
    type: "AgentAnswer",
    title: "Patient Adherence +23%",
    description:
      "Analysis showing that patients with medication reminders demonstrated a 23% adherence improvement compared to those without reminders. This finding was critical for treatment protocol optimization and resource allocation decisions.",
    activationScore: 87,
    tags: ["patient_adherence", "medication", "q3_2025", "treatment"],
    metadata: {
      analysis_types: "cohort_analysis,performance_analysis",
      metrics: "adherence_rate,treatment_outcome",
      conv_id: "2025-11-15_Med_Q3Protocol_01",
      ingestion_time: "2025-11-15T15:45:00Z",
    },
  },
  N1002: {
    id: "N1002",
    type: "AgentAction",
    title: "Link EHR to Prescription Data",
    description:
      "Action to link electronic health records with prescription fulfillment data. This linkage was necessary to properly track medication adherence and correlate with treatment outcomes.",
    activationScore: 78,
    tags: ["data_linking", "ehr", "prescription"],
    metadata: {
      status: "complete",
      parameter_field:
        "JOIN ehr_table ON prescription_table.patient_id = ehr_table.patient_id WHERE date_range = '2025-Q3'",
      conv_id: "2025-11-15_Med_Q3Protocol_01",
      ingestion_time: "2025-11-15T15:42:00Z",
    },
  },
  N1003: {
    id: "N1003",
    type: "UserPreference",
    title: "Researcher Prefers Charts",
    description:
      "User preference indicating that the researcher prefers data presented in visual chart format rather than tables. This preference influences how analysis results are formatted.",
    activationScore: 95,
    tags: ["user_preference", "format", "researcher", "report_style"],
    metadata: {
      preference_type: "report_style",
      user_role: "Research Director",
      conv_id: "2025-10-20_Med_Preference_01",
      ingestion_time: "2025-10-20T10:15:00Z",
    },
  },
  N1004: {
    id: "N1004",
    type: "AgentAction",
    title: "Generate Cohort Analysis",
    description:
      "Created a comprehensive cohort analysis for treatment efficacy scenarios. This analysis compared multiple treatment protocols and their projected impacts on patient outcomes and recovery rates.",
    activationScore: 91,
    tags: ["cohort_analysis", "treatment", "scenario"],
    metadata: {
      status: "complete",
      parameter_field:
        "scenarios: 4, variables: ['dosage_a', 'dosage_b', 'combination', 'standard'], sensitivity_range: ±15%",
      conv_id: "2025-11-10_Med_TreatmentAnalysis_01",
      ingestion_time: "2025-11-10T14:30:00Z",
    },
  },
  N1005: {
    id: "N1005",
    type: "DataSource",
    title: "B:ClinicalTrialGuidelines",
    description:
      "Historical guidance document containing best practices and lessons learned from previous clinical trials. Includes recommendations from Q3 2024 and Q1 2025 reviews.",
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
  N1006: {
    id: "N1006",
    type: "AgentAnswer",
    title: "Dosage Adjustment 15mg",
    description:
      "Recommended dosage adjustment to 15mg based on patient response analysis. This adjustment is projected to improve treatment efficacy by 8-12% while maintaining safety profile.",
    activationScore: 89,
    tags: ["dosage_optimization", "recommendation", "drug_a", "drug_b"],
    metadata: {
      analysis_types: "dosage_optimization,sensitivity_analysis",
      metrics: "efficacy_rate,adverse_events,patient_response",
      conv_id: "2025-11-10_Med_TreatmentAnalysis_01",
      ingestion_time: "2025-11-10T15:15:00Z",
    },
  },
  N1007: {
    id: "N1007",
    type: "DataSource",
    title: "Q3 Research Summary",
    description:
      "Quarterly research summary presentation containing patient outcomes, treatment analysis, and clinical recommendations. Includes data from July through September 2025.",
    activationScore: 85,
    tags: ["presentation", "q3", "summary"],
    metadata: {
      source_type: "pbi",
      doc_pointer: "/presentations/Q3_2025_Research_Summary.pbix",
      relevant_parts:
        "Slide 4: Dosage Recommendations, Slide 7: Treatment Performance",
      conv_id: "2025-09-30_Med_Q3Summary_01",
      ingestion_time: "2025-09-30T16:00:00Z",
    },
  },
  N1008: {
    id: "N1008",
    type: "Event",
    title: "2026 Telehealth Initiative",
    description:
      "Strategic initiative launched in early 2026 to expand telehealth monitoring capabilities and remote patient care. This event triggered multiple analysis requests and protocol optimizations.",
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
  N1009: {
    id: "N1009",
    type: "AgentAnswer",
    title: "Remote Monitoring Success",
    description:
      "Analysis showing that remote monitoring protocols achieved 15-22% improvement in early intervention rates compared to traditional in-person visits. This finding supported the decision to expand telehealth infrastructure.",
    activationScore: 93,
    tags: ["remote_monitoring", "telehealth", "intervention", "performance"],
    metadata: {
      analysis_types: "performance_comparison,protocol_analysis",
      metrics: "intervention_rate,patient_satisfaction,outcome",
      conv_id: "2026-01-15_Med_TelehealthAnalysis_01",
      ingestion_time: "2026-01-15T11:20:00Z",
    },
  },
  N1010: {
    id: "N1010",
    type: "AgentAction",
    title: "Adverse Event Correlation",
    description:
      "Grouped by treatment_type and patient_cohort; computed adverse event correlation. This analysis compared adverse event rates across different treatment protocols and patient demographics.",
    activationScore: 92,
    tags: ["adverse_events", "correlation", "safety", "analysis"],
    metadata: {
      status: "complete",
      parameter_field:
        "GROUP BY treatment_type, patient_cohort; METRIC: adverse_event_correlation",
      conv_id: "2025-07-11_Med_SafetyAnalysis_01",
      ingestion_time: "2025-07-11T12:00:00Z",
    },
  },
  N1011: {
    id: "N1011",
    type: "UserRequest",
    title: "Compare Treatment Efficacy",
    description:
      "User requested comparison of treatment efficacy metrics for the Phase III trial. This analysis examined response rates, recovery metrics, and safety profiles across different treatment variations.",
    activationScore: 84,
    tags: ["user_request", "phase_iii", "treatment", "comparison"],
    metadata: {
      user_role: "Clinical Research Director",
      user_id: "user_456",
      conv_id: "2025-07-10_Med_TreatmentRequest_01",
      ingestion_time: "2025-07-10T09:30:00Z",
    },
  },
  N1012: {
    id: "N1012",
    type: "DataSource",
    title: "Phase III Trial Data",
    description:
      "Comprehensive dataset containing efficacy metrics for the Phase III clinical trial. Includes patient response data, adverse event reports, and biomarker measurements by treatment arm and time point.",
    activationScore: 90,
    tags: ["clinical_trial", "phase_iii", "trial_data"],
    metadata: {
      source_type: "csv",
      doc_pointer: "/data/trials/PhaseIII_Trial_Data_May-Jul_2025.csv",
      relevant_parts:
        "Columns: treatment_arm, patient_id, response_rate, adverse_events, biomarkers",
      conv_id: "2025-07-10_Med_DataIngestion_01",
      ingestion_time: "2025-07-10T08:00:00Z",
    },
  },
  N1013: {
    id: "N1013",
    type: "Event",
    title: "Regulatory Approval",
    description:
      "Regulatory agency approval granted for expanded treatment protocol. This event triggered efficacy analysis and protocol optimization for broader patient population.",
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
  N1014: {
    id: "N1014",
    type: "AgentAction",
    title: "Merge Patient Demographics",
    description:
      "Action to merge patient demographic data with treatment response metrics. This merge was necessary to adjust efficacy calculations for demographic-adjusted analysis, accounting for population variations.",
    activationScore: 86,
    tags: ["data_merge", "demographics", "efficacy", "adjustment"],
    metadata: {
      status: "complete",
      parameter_field:
        "MERGE patient_demographics ON treatment_response.patient_id WHERE date_range = '2025-08'",
      conv_id: "2025-08-20_Med_DataMerge_01",
      ingestion_time: "2025-08-20T16:15:00Z",
    },
  },
  N1015: {
    id: "N1015",
    type: "DataSource",
    title: "Patient Enrollment Data...",
    description:
      "Patient enrollment data covering May through July 2025. Contains detailed breakdown of patient recruitment across different sites, demographics, and time periods.",
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
  N1016: {
    id: "N1016",
    type: "DataSource",
    title: "Treatment Response Data...",
    description:
      "Treatment response metrics dataset containing efficacy rates, adverse events, and patient outcomes across all treatment arms. Includes both primary and secondary endpoint data.",
    activationScore: 88,
    tags: ["treatment", "response", "metrics"],
    metadata: {
      source_type: "csv",
      doc_pointer: "/data/treatment/Treatment_Response_May-Jul_2025.csv",
      relevant_parts:
        "Columns: treatment_arm, efficacy_rate, adverse_events, patient_outcome, date",
      conv_id: "2025-08-15_Med_DataIngestion_03",
      ingestion_time: "2025-08-15T10:00:00Z",
    },
  },
  N1017: {
    id: "N1017",
    type: "AgentAnswer",
    title: "Efficacy Analysis Result",
    description:
      "Demographic-adjusted efficacy analysis results showing corrected performance metrics after accounting for patient population variations. This analysis revealed that some treatments appeared less effective due to demographic factors rather than actual performance issues.",
    activationScore: 91,
    tags: ["efficacy", "demographic_adjusted", "analysis"],
    metadata: {
      analysis_types: "efficacy_adjustment,demographic_analysis",
      metrics: "efficacy_rate,adverse_events,demographic_adjusted_efficacy",
      conv_id: "2025-08-20_Med_EfficacyAnalysis_01",
      ingestion_time: "2025-08-20T16:45:00Z",
    },
  },
  N1018: {
    id: "N1018",
    type: "DataSource",
    title: "C:StatisticalMethodology",
    description:
      "Analysis document containing statistical methodology for demographic-adjusted efficacy calculations. This document explains how to properly account for patient demographics when evaluating treatment performance.",
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
  N1019: {
    id: "N1019",
    type: "AgentAnswer",
    title: "Drug A vs Drug B Comparison",
    description:
      "Comparative analysis showing that Drug A achieved 20-28% efficacy advantage over Drug B in similar patient populations. This finding supported treatment protocol recommendations.",
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

export interface ReasoningStep {
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
