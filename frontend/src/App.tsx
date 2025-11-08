import "./index.css";
import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface Memory {
  id: string;
  type: string;
  content: string;
  relevance_score: number;
}

interface SubQuery {
  query: string;
  purpose: string;
}

interface MemoryUpdate {
  action: string;
  memory_type: string;
  content?: string;
  memory_id?: string;
}

interface QueryResponse {
  response: string;
  reasoning: string;
  memories_used: Memory[];
  sub_queries_generated: SubQuery[];
  memory_updates: MemoryUpdate[];
  conversation_id: string;
}

/**
 * Root React component for the AI Research Analyst chat interface.
 */
function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [lastResponse, setLastResponse] = useState<QueryResponse | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      role: "user",
      content: inputValue,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: inputValue,
          conversation_history: messages,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const data: QueryResponse = await response.json();
      setLastResponse(data);

      const assistantMessage: Message = {
        role: "assistant",
        content: data.response,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error:", error);
      const errorMessage: Message = {
        role: "assistant",
        content:
          "Sorry, I encountered an error. Please make sure the backend server is running at http://localhost:8000",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-primary text-white p-6 shadow-lg">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-semibold tracking-tight">AI Research Analyst</h1>
          <p className="text-white/90 mt-1.5 text-sm font-light">
            AI-powered analyst with long-term memory
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col max-w-6xl w-full mx-auto p-4">
        {/* Chat Messages */}
        <div className="flex-1 bg-card rounded-lg shadow-md p-4 mb-4 overflow-y-auto border border-main">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center text-subtle">
              <div className="text-center max-w-md">
                <h2 className="text-xl font-semibold text-text mb-3">Welcome</h2>
                <p className="text-secondary leading-relaxed">
                  Ask me anything about AI research, model performance, or
                  insights.
                </p>
                <div className="mt-6 text-left">
                  <p className="text-sm font-medium text-text mb-3">Example queries:</p>
                  <ul className="text-sm space-y-2 text-secondary">
                    <li className="flex items-start">
                      <span className="text-subtle mr-2">•</span>
                      <span>"What is the performance of the transformer model?"</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-subtle mr-2">•</span>
                      <span>"Tell me about training data quality issues"</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-subtle mr-2">•</span>
                      <span>"How should I present results in a research paper?"</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[70%] p-4 rounded-lg ${
                      msg.role === "user"
                        ? "bg-primary text-white"
                        : "bg-primary-light text-text border border-main"
                    }`}
                  >
                    <div className="leading-relaxed markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                    <div
                      className={`text-xs mt-2.5 opacity-70 ${
                        msg.role === "user" ? "text-white" : "text-secondary"
                      }`}
                    >
                      {msg.role === "user" ? "You" : "Analyst"} • {new Date(msg.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-primary-light p-4 rounded-lg border border-main">
                    <div className="flex items-center space-x-3">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                      <span className="text-secondary text-sm">
                        Analyzing and retrieving memories...
                      </span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Details Panel */}
        {lastResponse && (
          <div className="bg-card rounded-lg shadow-md p-4 mb-4 border border-main">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="w-full flex items-center justify-between text-left font-semibold text-text hover:text-primary transition-colors py-2"
            >
              <span className="text-sm uppercase tracking-wide">Workflow Details</span>
              <span className="text-secondary text-xs">{showDetails ? "▼" : "▶"}</span>
            </button>

            {showDetails && lastResponse && (
              <div className="mt-4 space-y-4 text-sm">
                {/* Reasoning */}
                <div>
                  <h3 className="font-semibold text-text mb-2 text-sm uppercase tracking-wide">
                    Agent Reasoning
                  </h3>
                  <p className="text-secondary bg-primary-light p-3 rounded border border-main leading-relaxed text-sm">
                    {lastResponse.reasoning}
                  </p>
                </div>

                {/* Sub-queries */}
                <div>
                  <h3 className="font-semibold text-text mb-2 text-sm uppercase tracking-wide">
                    Sub-queries Generated ({lastResponse.sub_queries_generated.length})
                  </h3>
                  <ul className="space-y-2">
                    {lastResponse.sub_queries_generated.map((sq, idx) => (
                      <li
                        key={idx}
                        className="bg-icon-blue-bg p-3 rounded border-l-4 border-icon-blue"
                      >
                        <div className="font-medium text-icon-blue text-sm">
                          "{sq.query}"
                        </div>
                        <div className="text-icon-blue/70 text-xs mt-1.5 font-light">
                          Purpose: {sq.purpose}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Memories Used */}
                <div>
                  <h3 className="font-semibold text-text mb-2 text-sm uppercase tracking-wide">
                    Memories Retrieved ({lastResponse.memories_used.length})
                  </h3>
                  <ul className="space-y-2">
                    {lastResponse.memories_used.map((mem) => (
                      <li
                        key={mem.id}
                        className="bg-success-bg p-3 rounded border-l-4 border-success"
                      >
                        <div className="flex items-center justify-between mb-1.5 flex-wrap gap-2">
                          <span className="font-mono text-xs text-success font-medium">
                            {mem.id}
                          </span>
                          <span className="text-xs bg-success-bg px-2 py-1 rounded border border-success text-success font-medium">
                            {mem.type}
                          </span>
                          <span className="text-xs text-success font-medium">
                            Score: {mem.relevance_score.toFixed(2)}
                          </span>
                        </div>
                        <div className="text-text text-sm leading-relaxed">{mem.content}</div>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Memory Updates */}
                <div>
                  <h3 className="font-semibold text-text mb-2 text-sm uppercase tracking-wide">
                    Memory Updates ({lastResponse.memory_updates.length})
                  </h3>
                  <ul className="space-y-2">
                    {lastResponse.memory_updates.map((upd, idx) => (
                      <li
                        key={idx}
                        className="bg-icon-pink-bg p-3 rounded border-l-4 border-icon-pink"
                      >
                        <div className="flex items-center space-x-2 mb-1.5 flex-wrap gap-2">
                          <span className="text-xs bg-icon-pink-bg px-2 py-1 rounded font-semibold border border-icon-pink text-icon-pink">
                            {upd.action.toUpperCase()}
                          </span>
                          <span className="text-xs text-icon-pink font-medium">
                            {upd.memory_type}
                          </span>
                        </div>
                        <div className="text-text text-xs leading-relaxed">
                          {upd.content || upd.memory_id}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Input Area */}
        <div className="bg-card rounded-lg shadow-md p-4 border border-main">
          <div className="flex space-x-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me about AI research insights..."
              className="flex-1 px-4 py-3 border border-main rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary bg-card text-text placeholder:text-subtle text-sm"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !inputValue.trim()}
              className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:bg-border disabled:text-subtle disabled:cursor-not-allowed transition-colors font-medium text-sm uppercase tracking-wide"
            >
              {isLoading ? "Processing..." : "Send"}
            </button>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-card border-t border-main text-secondary text-center py-4 mt-4">
        <small className="text-xs">© Bo & Hussain</small>
      </footer>
    </div>
  );
}

export default App;
