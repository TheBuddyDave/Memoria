import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

interface Document {
  id: string;
  name: string;
  type: string;
  size: string;
  isGenerated: boolean;
  usedInMessages: string[];
  metadata?: {
    createdBy?: string;
    purpose?: string;
    summary?: string;
    keyFindings?: string[];
  };
  highlightedSections?: {
    id: string;
    location: string;
    content: string;
    relevance: string;
  }[];
  docPointer?: string;
  relevantParts?: string;
}

const sampleDocuments: Document[] = [
  {
    id: "doc1",
    name: "E:BudgetReallocationGuidance.pdf",
    type: "pdf",
    size: "2.4 MB",
    isGenerated: false,
    usedInMessages: ["msg1", "msg2"],
    docPointer: "/documents/guidance/E_BudgetReallocationGuidance.pdf",
    relevantParts: "Section 3: Best Practices, Section 5: Lessons Learned",
  },
  {
    id: "doc2",
    name: "Q4_2025_Review_Deck.pbix",
    type: "pbix",
    size: "15.8 MB",
    isGenerated: false,
    usedInMessages: ["msg3"],
    docPointer: "/presentations/Q4_2025_Review_Deck.pbix",
    relevantParts: "Slide 4: Budget Recommendations, Slide 7: Channel Performance",
  },
  {
    id: "doc3",
    name: "Rundown_Allocation_May-Jul_2025.csv",
    type: "csv",
    size: "856 KB",
    isGenerated: false,
    usedInMessages: ["msg4", "msg5"],
    docPointer: "/data/rundown/Rundown_Allocation_May-Jul_2025.csv",
    relevantParts: "All columns, date_range: 2025-05-01 to 2025-07-31",
  },
  {
    id: "doc4",
    name: "Channel_Source_Performance_May-Jul_2025.csv",
    type: "csv",
    size: "1.2 MB",
    isGenerated: false,
    usedInMessages: ["msg6"],
    docPointer: "/data/channels/Channel_Source_Performance_May-Jul_2025.csv",
    relevantParts: "Columns: channel, cps, cpl, conversion_rate, date",
  },
  {
    id: "doc5",
    name: "EV9_Campaign_Data_May-Jul_2025.csv",
    type: "csv",
    size: "3.1 MB",
    isGenerated: false,
    usedInMessages: ["msg7", "msg8"],
    docPointer: "/data/campaigns/EV9_Campaign_Data_May-Jul_2025.csv",
    relevantParts: "Columns: creative_type, channel, impressions, clicks, conversions, cost",
  },
  {
    id: "doc6",
    name: "A_Supply-AdjustedROIAnalysis_v2.1.pdf",
    type: "pdf",
    size: "4.7 MB",
    isGenerated: false,
    usedInMessages: ["msg9"],
    docPointer: "/documents/analysis/A_Supply-AdjustedROIAnalysis_v2.1.pdf",
    relevantParts: "Section 2: Methodology, Section 4: Calculation Examples",
  },
  {
    id: "doc7",
    name: "Budget_Reallocation_Recommendations_2025.xlsx",
    type: "xlsx",
    size: "892 KB",
    isGenerated: true,
    usedInMessages: ["msg10"],
    metadata: {
      createdBy: "AI Agent",
      purpose: "Budget reallocation analysis and recommendations for Q4 2025",
      summary: "Comprehensive analysis showing optimal budget shift of 12% from Meta to CRM and video content, projected to increase conversions by 6-9%.",
      keyFindings: [
        "CRM retargeting shows 18-24% CPS advantage over Meta",
        "Video education content achieves 12-19% CPL reduction",
        "Aligned dealers demonstrate 14% conversion lift",
        "Supply constraints require adjusted ROI calculations",
      ],
    },
  },
  {
    id: "doc8",
    name: "EV9_Creative_Performance_Comparison.pptx",
    type: "pptx",
    size: "5.3 MB",
    isGenerated: true,
    usedInMessages: ["msg11"],
    metadata: {
      createdBy: "AI Agent",
      purpose: "Creative performance comparison for EV9 campaign optimization",
      summary: "Analysis of 8 creative variations showing optimal performance metrics and recommendations for future campaigns.",
      keyFindings: [
        "Video creatives outperform static by 23% in engagement",
        "Channel-specific creative tailoring increases CTR by 15%",
        "VTR-Lead conversion highest in automotive-focused content",
      ],
    },
  },
];

export default function Documents() {
  const location = useLocation();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [activeTab, setActiveTab] = useState<"used" | "generated">("used");

  const usedDocuments = sampleDocuments.filter((d) => !d.isGenerated);
  const generatedDocuments = sampleDocuments.filter((d) => d.isGenerated);

  const getDocIcon = (type: string) => {
    switch (type) {
      case "pdf":
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        );
      case "csv":
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        );
      case "xlsx":
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
      case "pptx":
      case "pbix":
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
    }
  };

  const filteredDocuments =
    activeTab === "used" ? usedDocuments : generatedDocuments;

  const filteredBySearch = filteredDocuments.filter((doc) =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
                location.pathname === "/query"
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
                location.pathname === "/graph"
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
                location.pathname === "/reasoning"
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
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <span>Documents</span>
            </Link>
          </div>

          {/* Right side buttons */}
          <div className="flex items-center space-x-4 flex-shrink-0">
            <button className="text-text-secondary hover:text-text transition-colors py-2">
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden min-h-0 gap-4 p-4">
        {/* Document List - Left Side */}
        <div className="flex-[55] flex flex-col min-h-0">
          {/* Search and Tabs */}
          <div className="mb-4 space-y-3 flex-shrink-0">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-secondary"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-black/5 border border-black/10 rounded-lg text-text placeholder:text-text-secondary placeholder:opacity-70 focus:outline-none focus:border-[#6366f1]/50 transition-colors"
              />
            </div>

            {/* Tabs */}
            <div className="flex border-b border-black/10">
              <button
                onClick={() => {
                  setActiveTab("used");
                  setSelectedDoc(null);
                }}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === "used"
                    ? "text-text border-b-2 border-[#6366f1]"
                    : "text-text-secondary hover:text-text"
                }`}
              >
                Used Documents ({usedDocuments.length})
              </button>
              <button
                onClick={() => {
                  setActiveTab("generated");
                  setSelectedDoc(null);
                }}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === "generated"
                    ? "text-text border-b-2 border-[#6366f1]"
                    : "text-text-secondary hover:text-text"
                }`}
              >
                Generated ({generatedDocuments.length})
              </button>
            </div>
          </div>

          {/* Document Grid */}
          <div className="flex-1 overflow-y-auto min-h-0">
            <div className="grid gap-3 grid-cols-2 pb-4">
              {filteredBySearch.map((doc) => (
                <div
                  key={doc.id}
                    className={`p-4 bg-black/5 border rounded-lg cursor-pointer transition-all ${
                      selectedDoc?.id === doc.id
                        ? "border-[#6366f1]/50 bg-black/10 shadow-lg"
                        : "border-black/10 hover:border-black/20 hover:bg-black/8"
                    }`}
                  onClick={() => setSelectedDoc(doc)}
                >
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-black/5 shrink-0 text-[#0ea5e9]">
                        {getDocIcon(doc.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-semibold leading-tight break-words mb-1 text-text">
                          {doc.name}
                        </h4>
                        <p className="text-sm text-text-secondary">{doc.size}</p>
                      </div>
                    </div>

                    {doc.isGenerated && (
                      <span className="inline-block px-2 py-1 bg-[#22c55e]/20 text-[#22c55e] text-xs rounded border border-[#22c55e]/30">
                        AI Generated
                      </span>
                    )}

                    {doc.usedInMessages.length > 0 && (
                      <p className="text-sm text-text-secondary">
                        Used in {doc.usedInMessages.length} message
                        {doc.usedInMessages.length > 1 ? "s" : ""}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Document Details Panel - Right Side */}
        <div className="flex-[45] border-l border-black/10 pl-4 flex flex-col min-h-0">
          {selectedDoc ? (
            <>
              <div className="flex items-start justify-between mb-4 flex-shrink-0">
                <h3 className="text-lg font-bold leading-tight pr-2 text-text">
                  {selectedDoc.name}
                </h3>
                <button
                  onClick={() => setSelectedDoc(null)}
                  className="text-text-secondary hover:text-text transition-colors p-1"
                >
                  <svg
                    className="w-5 h-5"
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
                </button>
              </div>

              <div className="flex-1 overflow-y-auto min-h-0">
                <div className="space-y-4 pr-2">
                  <button
                    className="w-full px-4 py-2 bg-[#2563eb] hover:bg-[#1d4ed8] text-white rounded-lg transition-colors flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                      />
                    </svg>
                    <span>Preview Document</span>
                  </button>

                  {/* Document Info */}
                  <div className="p-3.5 bg-[#dbeafe] border-l-4 border-[#2563eb] rounded-lg">
                    <h4 className="text-sm font-semibold mb-2.5 text-[#1d4ed8]">
                      Document Info
                    </h4>
                    <div className="space-y-2.5 text-sm">
                      <div className="flex justify-between">
                        <span className="text-text-secondary">Size:</span>
                        <span className="font-semibold text-text">
                          {selectedDoc.size}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-text-secondary">Type:</span>
                        <span className="font-semibold text-text uppercase">
                          {selectedDoc.type}
                        </span>
                      </div>
                      {selectedDoc.usedInMessages.length > 0 && (
                        <div className="flex justify-between">
                          <span className="text-text-secondary">Used in:</span>
                          <span className="font-semibold text-text">
                            {selectedDoc.usedInMessages.length} message(s)
                          </span>
                        </div>
                      )}
                      {selectedDoc.docPointer && (
                        <div className="flex flex-col">
                          <span className="text-text-secondary mb-1">Path:</span>
                          <span className="font-mono text-xs text-text break-all">
                            {selectedDoc.docPointer}
                          </span>
                        </div>
                      )}
                      {selectedDoc.relevantParts && (
                        <div className="flex flex-col">
                          <span className="text-text-secondary mb-1">
                            Relevant Parts:
                          </span>
                          <span className="text-sm text-text">
                            {selectedDoc.relevantParts}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* AI Generation Metadata */}
                  {selectedDoc.metadata && (
                  <div className="p-3.5 bg-[#dcfce7] border-l-4 border-[#22c55e] rounded-lg">
                    <h4 className="text-sm font-semibold mb-3 text-[#15803d]">
                        AI Generation Metadata
                      </h4>
                      <div className="space-y-3 text-sm">
                        {selectedDoc.metadata.createdBy && (
                          <div>
                            <p className="text-sm text-text-secondary mb-1">
                              Created By
                            </p>
                            <p className="leading-relaxed text-text">
                              {selectedDoc.metadata.createdBy}
                            </p>
                          </div>
                        )}
                        {selectedDoc.metadata.purpose && (
                          <div>
                            <p className="text-sm text-text-secondary mb-1">
                              Purpose
                            </p>
                            <p className="leading-relaxed text-text">
                              {selectedDoc.metadata.purpose}
                            </p>
                          </div>
                        )}
                        {selectedDoc.metadata.summary && (
                          <div>
                            <p className="text-sm text-text-secondary mb-1">
                              Summary
                            </p>
                            <p className="leading-relaxed text-text">
                              {selectedDoc.metadata.summary}
                            </p>
                          </div>
                        )}
                        {selectedDoc.metadata.keyFindings && (
                          <div>
                            <p className="text-sm text-text-secondary mb-2">
                              Key Findings
                            </p>
                            <ul className="space-y-2">
                              {selectedDoc.metadata.keyFindings.map(
                                (finding, idx) => (
                                  <li
                                    key={idx}
                              className="text-sm leading-relaxed text-text pl-3 relative before:content-['•'] before:absolute before:left-0 before:text-[#6366f1]"
                                  >
                                    {finding}
                                  </li>
                                )
                              )}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Highlighted Sections */}
                  {selectedDoc.highlightedSections &&
                    selectedDoc.highlightedSections.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold mb-2 text-[#6366f1]">
                          Highlighted Sections
                        </h4>
                        <p className="text-sm text-text-secondary mb-3">
                          Sections referenced by the agent during analysis
                        </p>
                        <div className="space-y-2.5">
                          {selectedDoc.highlightedSections.map((section) => (
                            <div
                              key={section.id}
                            className="p-3.5 bg-[#ede9fe] border-l-4 border-[#6366f1] rounded-lg"
                            >
                              <div className="space-y-2.5">
                                <div className="flex items-start gap-2">
                                <span className="px-2 py-1 text-xs border border-[#6366f1]/50 text-[#6366f1] rounded shrink-0">
                                    {section.location}
                                  </span>
                                </div>
                                <div className="p-2.5 rounded text-sm leading-relaxed font-mono bg-black/5 text-text">
                                  {section.content}
                                </div>
                                <p className="text-sm italic text-[#6366f1]">
                                  {section.relevance}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-3">
                <svg
                  className="w-16 h-16 mx-auto opacity-20 text-text-secondary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p className="text-base text-text-secondary">
                  Pick a document to see details
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}







