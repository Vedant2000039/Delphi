// ChatSection.jsx — Chat/messages section wired to the Context Engine backend
import React, {
  useState, useRef, useEffect, useCallback, useImperativeHandle, forwardRef,
} from "react";
import CreateICP from "./CreateICP";
import BuyerGroup from "./BuyerGroup";
import { LeadsTable } from "./intellegence";

const API_BASE = "http://127.0.0.1:8000";

function getAuthHeaders() {
  try {
    const auth = JSON.parse(localStorage.getItem("context_engine_auth") || "null");
    const token = auth?.token || localStorage.getItem("token") || JSON.parse(localStorage.getItem("user") || "{}")?.token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch { return {}; }
}

function TypingDots() {
  return <div className="typing-indicator"><span /><span /><span /></div>;
}

const SUGGESTION_LABELS = {
  geography: "Target Geographies", industry: "Industries", job_function: "Job Functions",
  job_level: "Seniority Levels", employee_size: "Company Sizes", revenue_range: "Lead Revenue Ranges",
};

function SuggestionGroup({ field, items, onSelect }) {
  return (
    <div className="suggestion-group">
      <div className="suggestion-group-label"><span>{SUGGESTION_LABELS[field] || field}</span></div>
      <div className="suggestion-chips">
        {items.map(item => (
          <button key={item} className="chip" onClick={() => onSelect(item)}>{item}</button>
        ))}
      </div>
    </div>
  );
}

const ChatSection = forwardRef(function ChatSection(
  { userId, onContextUpdate, onPhaseUpdate, onSessionsChange, onOpenProductPicker },
  ref
) {
  const [sessionId, setSessionId]   = useState(null);
  const [messages, setMessages]     = useState([]);
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [suggestions, setSuggestions] = useState({});

  const bottomRef   = useRef(null);
  const textareaRef = useRef(null);
  const headers = getAuthHeaders();

  const pushMessage = useCallback((msg) => {
    setMessages(prev => [...prev, { id: Date.now() + Math.random(), ...msg }]);
  }, []);

  // ── Session management ──────────────────────────────────────────────────
  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/context/sessions`, { headers });
      if (!res.ok) return [];
      const data = await res.json();
      onSessionsChange?.(data.sessions ?? []);
      return data.sessions ?? [];
    } catch { return []; }
  }, [onSessionsChange]);

  const loadHistory = useCallback(async (id) => {
    if (!id) { setMessages([]); return; }
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/context/sessions/${id}/messages`, { headers });
      if (!res.ok) throw new Error("Could not restore this chat.");
      const data = await res.json();
      setMessages((data.messages ?? []).map(({ role, content, token_count }) => ({
        id: Date.now() + Math.random(),
        role: role === "user" ? "user" : "bot",
        text: content,
        tokenCount: token_count,
      })));
    } catch (err) {
      setMessages([{ id: Date.now(), role: "bot", text: err.message }]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const ensureSession = useCallback(async () => {
    if (sessionId) return sessionId;
    const res = await fetch(`${API_BASE}/context/sessions`, { method: "POST", headers });
    const session = await res.json();
    setSessionId(session.id);
    await loadSessions();
    return session.id;
  }, [sessionId, headers, loadSessions]);

  const startNewChat = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/context/sessions`, { method: "POST", headers });
      const session = await res.json();
      setSessionId(session.id);
      setMessages([]);
      setSuggestions({});
      await loadSessions();
      return session.id;
    } catch (err) {
      pushMessage({ role: "bot", text: "Could not create a new chat." });
    }
  }, [headers, loadSessions, pushMessage]);

  const selectSession = useCallback((id) => {
    setSessionId(id);
    setSuggestions({});
    loadHistory(id);
  }, [loadHistory]);

  // ── Bootstrap: load sessions on mount ───────────────────────────────────
  useEffect(() => {
    if (!userId) return;
    loadSessions().then((sessions) => {
      if (sessions.length > 0) selectSession(sessions[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, suggestions, loading]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
  }, [input]);

  // ── Send message (context-engine chat endpoint) ─────────────────────────
  const sendMessage = useCallback(async (text) => {
    const finalText = (text ?? input).trim();
    if (!finalText || loading) return;
    const activeSession = await ensureSession();
    pushMessage({ role: "user", text: finalText });
    setInput("");
    setLoading(true);
    setSuggestions({});
    try {
      const res = await fetch(`${API_BASE}/context/chat`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: activeSession, message: finalText }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not send message.");

      if (data.context) onContextUpdate?.(data.context);
      if (data.phase)   onPhaseUpdate?.(data.phase);

      if (data.status === "complete") {
        if (data.summary) pushMessage({ role: "bot", text: data.summary });
        pushMessage({ role: "bot", table: data.leads || data.data || [] });
        setSuggestions({});
        onPhaseUpdate?.("complete");
      } else {
        if (data.response) {
          pushMessage({ role: "bot", text: data.response, editApplied: data.edit_applied || null });
        }
        if (data.suggestions) {
          const filtered = {};
          for (const [k, v] of Object.entries(data.suggestions)) {
            if (Array.isArray(v) && v.length > 0) filtered[k] = v;
          }
          setSuggestions(filtered);
        }
      }
      await loadSessions();
    } catch (err) {
      pushMessage({ role: "bot", text: `Error: ${err.message}` });
    } finally {
      setLoading(false);
    }
  }, [input, loading, headers, ensureSession, pushMessage, onContextUpdate, onPhaseUpdate, loadSessions]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // ── Exposed imperative API for the parent (Intellegence.js) ─────────────
  useImperativeHandle(ref, () => ({
    sendMessage,
    pushMessage,
    startNewChat,
    selectSession,
    getSessionId: () => sessionId,
  }), [sendMessage, pushMessage, startNewChat, selectSession, sessionId]);

  return (
    <>
      <div className="messages-area">
        {messages.map(msg => (
          <div key={msg.id} className={`message-row ${msg.role}`}>
            {msg.role === "bot" && <div className="bot-avatar" title="Delphi AI">D</div>}
            <div className="message-content">
              {msg.text && <div className="bubble">{msg.text}</div>}
              {msg.editApplied && (
                <div className="edit-badge">
                  ✓ Updated: {msg.editApplied.field?.replace(/_/g, " ")} → {msg.editApplied.value}
                </div>
              )}
              {msg.tokenCount != null && <small>≈ {msg.tokenCount} estimated tokens</small>}
              {msg.table !== undefined && <LeadsTable rows={msg.table} />}
              {msg.icpFlow && (
                <CreateICP userId={userId} onDiscoverBuyerGroup={() => sendMessage("Discover Buyer Group")} onOpenProductPicker={onOpenProductPicker} />
              )}
              {msg.buyerGroupFlow && (
                <BuyerGroup userId={userId} brandIds={msg.brandIds} onOpenProductPicker={onOpenProductPicker} />
              )}
            </div>
          </div>
        ))}
        {historyLoading && <div className="empty">Restoring chat…</div>}
        {loading && (
          <div className="message-row bot">
            <div className="bot-avatar">D</div>
            <div className="message-content"><div className="bubble"><TypingDots /></div></div>
          </div>
        )}
        {!loading && Object.keys(suggestions).length > 0 && (
          <div className="suggestions-area">
            {Object.entries(suggestions).map(([field, items]) => (
              <SuggestionGroup key={field} field={field} items={items} onSelect={sendMessage} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="input-zone">
        <div className="input-card">
          <textarea
            ref={textareaRef}
            className="chat-input"
            placeholder="Ask a question or refine your search..."
            value={input}
            rows={1}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="send-btn" onClick={() => sendMessage()} disabled={!input.trim() || loading} title="Send (Enter)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
        <p className="input-hint">Enter to send · Shift+Enter for new line · Type "change [field]" to edit</p>
      </div>
    </>
  );
});

export default ChatSection;