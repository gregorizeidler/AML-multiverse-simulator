import { useRef, useState } from "react";
import { Send, Bot, User, RefreshCw, Cpu } from "lucide-react";
import { cn } from "../lib/utils.js";
import PageHeader from "../components/PageHeader.jsx";

const API_BASE = "/api";

const SUGGESTED = [
  "Which universe has the best F1 score and why?",
  "Explain the difference between smurfing and structuring",
  "What's the cost tradeoff between conservative and aggressive policies?",
  "How does the graph-enhanced universe detect round-tripping?",
  "Should I deploy the ML model universe in production?",
  "Summarize the backtesting results and flag any drift",
];

async function sendMessage(message, signal) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5",
          isUser ? "bg-brand-600" : "bg-surface-border"
        )}
      >
        {isUser ? <User size={14} className="text-white" /> : <Bot size={14} className="text-gray-300" />}
      </div>
      <div
        className={cn(
          "max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-brand-600/20 border border-brand-600/30 text-white"
            : "bg-surface-card border border-surface-border text-gray-200"
        )}
      >
        {msg.role === "assistant" && msg.llm_mode && (
          <div className="flex items-center gap-1 mb-2">
            <Cpu size={10} className="text-gray-600" />
            <span className="text-[10px] text-gray-600 uppercase tracking-wider">
              {msg.llm_mode === "openai" ? "GPT-4o-mini" : msg.llm_mode === "ollama" ? "Ollama" : "Heuristic"}
            </span>
          </div>
        )}
        <p className="whitespace-pre-wrap">{msg.content}</p>
      </div>
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm your AML Intelligence Assistant. I have full context of your simulation results — universes, metrics, backtesting, SAR reports, and recommendations.\n\nAsk me anything about the simulation or AML policy.",
      llm_mode: null,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);
  const bottomRef = useRef(null);

  const submit = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);

    abortRef.current = new AbortController();
    try {
      const data = await sendMessage(msg, abortRef.current.signal);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          llm_mode: data.llm_mode,
          is_real_llm: data.is_real_llm,
        },
      ]);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Sorry, I couldn't reach the API. Make sure the backend is running on port 8000.",
            llm_mode: "error",
          },
        ]);
      }
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    }
  };

  const reset = async () => {
    await fetch("/api/chat/reset", { method: "POST" }).catch(() => {});
    setMessages([
      {
        role: "assistant",
        content: "Conversation reset. How can I help you?",
        llm_mode: null,
      },
    ]);
  };

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="AML Intelligence Chat"
        subtitle="Ask questions about universes, typologies, policies, SAR reports, and simulation results"
      >
        <button onClick={reset} className="btn-ghost text-sm">
          <RefreshCw size={14} /> Reset
        </button>
      </PageHeader>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto px-8 py-6 space-y-4">
            {messages.map((msg, i) => (
              <Message key={i} msg={msg} />
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-surface-border flex items-center justify-center shrink-0">
                  <Bot size={14} className="text-gray-300" />
                </div>
                <div className="bg-surface-card border border-surface-border rounded-xl px-4 py-3">
                  <div className="flex gap-1 items-center">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce"
                        style={{ animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="px-8 py-4 border-t border-surface-border">
            <div className="flex gap-3">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && submit()}
                placeholder="Ask about the simulation results…"
                className="flex-1 bg-surface-card border border-surface-border rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-brand-500 transition-colors"
              />
              <button
                onClick={() => submit()}
                disabled={!input.trim() || loading}
                className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>

        {/* Suggested questions sidebar */}
        <div className="w-64 shrink-0 border-l border-surface-border p-5 overflow-y-auto hidden lg:block">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Suggested Questions
          </p>
          <div className="space-y-2">
            {SUGGESTED.map((q, i) => (
              <button
                key={i}
                onClick={() => submit(q)}
                disabled={loading}
                className="w-full text-left text-xs text-gray-400 hover:text-white bg-surface-hover hover:bg-surface-border rounded-lg px-3 py-2.5 transition-colors leading-relaxed"
              >
                {q}
              </button>
            ))}
          </div>

          <div className="mt-6 pt-4 border-t border-surface-border">
            <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2">LLM Mode</p>
            <div className="text-xs text-gray-500 space-y-1">
              <p>Set <code className="font-mono text-brand-400 bg-surface px-1 rounded">OPENAI_API_KEY</code> for GPT-4o-mini</p>
              <p>Or run <code className="font-mono text-green-400 bg-surface px-1 rounded">ollama</code> locally for Llama 3</p>
              <p>Falls back to heuristic engine otherwise.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
