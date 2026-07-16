//Intelligence.js
import React, { useState, useRef, useEffect, useCallback } from "react";
import "./intellegence.css";

const API_BASE = "http://127.0.0.1:8000";
const SESSION_ID = `user_${Math.random().toString(36).slice(2, 9)}`;

const FIELD_LABELS = {
  geography: "Geography",
  industry: "Industry",
  industry_domain: "Sector",
  job_function: "Job Function",
  job_level: "Seniority",
  employee_size: "Company Size",
  revenue_range: "Revenue",
};

const FIELD_ICONS = {
  geography: "🌍",
  industry: "🏢",
  industry_domain: "🔬",
  job_function: "💼",
  job_level: "⭐",
  employee_size: "👥",
  revenue_range: "💰",
};

const SUGGESTION_LABELS = {
  geography: "Target Geographies",
  industry: "Industries",
  industry_domain: "Sectors / Domains",
  job_function: "Job Functions",
  job_level: "Seniority Levels",
  employee_size: "Company Sizes",
  revenue_range: "Revenue Ranges",
};

const FIELD_ORDER = [
  "geography",
  "industry",
  "industry_domain",
  "job_function",
  "job_level",
  "employee_size",
  "revenue_range",
];

// ─────────────────────────────────────────────────────────────
// TREND CARD COMPONENTS
// ─────────────────────────────────────────────────────────────

const CHART_COLORS = [
  "#6366f1", "#1baf7a", "#eda100", "#e34948",
  "#a78bfa", "#eb6834", "#e87ba4", "#008300",
];

const REGION_COMMENTS = {
  "United States":  "Largest enterprise buyer pool; highest B2B adoption globally",
  "India":          "Fastest-growing mid-market; strong IT and healthcare enterprise demand",
  "United Kingdom": "Mature regulatory environment; NHS and finance drive procurement",
  "Germany":        "Largest EU economy; high-value but rigorous B2B sales cycles",
  "Australia":      "High per-capita IT spend; strong public sector and healthcare",
  "Canada":         "Close US buyer alignment; ideal for co-sell expansion",
  "Singapore":      "APAC regional HQ hub; progressive procurement environment",
  "UAE":            "High enterprise spending; gateway to GCC and MENA markets",
  "France":         "Large enterprise market; government and healthcare lead digital",
  "Netherlands":    "European tech hub; high-density enterprise cluster",
  "Japan":          "Premium market with regulatory-driven procurement",
  "South Korea":    "Rapid enterprise digitisation; strong telecom and manufacturing",
  "Brazil":         "Largest Latin America market; growing enterprise tech adoption",
  "Israel":         "High density of B2B tech buyers; strong scale-up ecosystem",
  "Sweden":         "High digitisation index; strong public sector and fintech",
  "Spain":          "Growing digital transformation investment across enterprise",
  "Poland":         "Fastest-growing Central European tech market",
  "Indonesia":      "Largest Southeast Asia market; rapid enterprise digitalisation",
  "Malaysia":       "Regional tech hub; high government digitisation spend",
  "South Africa":   "Largest African enterprise market; Sub-Saharan gateway",
};

function getRegionComment(region) {
  return REGION_COMMENTS[region] || "Active enterprise market with B2B growth potential";
}

function DonutChart({ slices }) {
  const r = 52, cx = 80, cy = 80;
  const circ = 2 * Math.PI * r;
  let cum = 0;
  const arcs = slices.map((s, i) => {
    const offset = circ * (1 - cum / 100);
    const dash   = circ * s.pct / 100;
    cum += s.pct;
    return { ...s, offset, dash, color: CHART_COLORS[i] || "#555" };
  });
  return (
    <svg width="160" height="160" viewBox="0 0 160 160">
      <circle cx={cx} cy={cy} r={r} fill="none"
        stroke="rgba(255,255,255,0.06)" strokeWidth="18" />
      {arcs.map((a, i) => (
        <circle key={i} cx={cx} cy={cy} r={r} fill="none"
          stroke={a.color} strokeWidth="18"
          strokeDasharray={`${a.dash} ${circ - a.dash}`}
          strokeDashoffset={a.offset}
          transform={`rotate(-90 ${cx} ${cy})`}
        />
      ))}
      <text x={cx} y={cy - 7} textAnchor="middle" fontSize="10"
        fill="rgba(255,255,255,0.35)">top market</text>
      <text x={cx} y={cy + 12} textAnchor="middle" fontSize="13"
        fontWeight="500" fill="#e8eaf0">
        {slices[0]?.region?.split(" ")[0] || ""}
      </text>
    </svg>
  );
}

function Sparkline({ data }) {
  if (!data || data.length < 2) return null;
  const w = 220, h = 40;
  const vals = data.map(d => d.value);
  const min = Math.min(...vals);
  const max = Math.max(...vals) || 1;
  const pts = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * w;
    const y = h - ((v - min) / (max - min || 1)) * h;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ display: "block" }}>
      <polyline points={pts} fill="none" stroke="#6366f1"
        strokeWidth="2" strokeLinejoin="round" />
      <polyline
        points={`0,${h} ${pts} ${w},${h}`}
        fill="#6366f1" fillOpacity="0.1" stroke="none" />
    </svg>
  );
}

function TrendCard({ data, onTargetGeo }) {
  if (!data) return null;
  const {
    product, kpi, top_regions, pie_slices, time_trend,
    rising, summary, recommendation, cta_geographies, data_source,
  } = data;

  return (
    <div className="trend-card">

      {/* Header */}
      <div className="trend-header">
        <div>
          <div className="trend-title">
            Trend Analysis: {product.charAt(0).toUpperCase() + product.slice(1)}
          </div>
          <div className="trend-source">
            {data_source} · Last 12 months · Worldwide
          </div>
        </div>
        <span className={`trend-badge ${data_source === "Google Trends (live)" ? "live" : "est"}`}>
          {data_source === "Google Trends (live)" ? "● Live" : "● Estimated"}
        </span>
      </div>

      {/* KPI Row */}
      <div className="trend-kpi-row">
        {[
          { label: "Top market",       value: `${kpi.top_market_flag} ${kpi.top_market}`, sub: `Score ${kpi.top_market_score}/100` },
          { label: "Markets analysed", value: kpi.markets_analysed,                        sub: "B2B-relevant only" },
          { label: "Avg. interest",    value: `${kpi.avg_score}/100`,                      sub: "across top markets" },
          { label: "Rising signals",   value: kpi.rising_count,                            sub: "breakout queries" },
        ].map(k => (
          <div key={k.label} className="trend-kpi-tile">
            <div className="trend-kpi-label">{k.label}</div>
            <div className="trend-kpi-value">{k.value}</div>
            <div className="trend-kpi-sub">{k.sub}</div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="trend-charts-row">

        {/* Bar list */}
        <div className="trend-bar-panel">
          <div className="trend-panel-title">Top regions by search interest</div>
          {top_regions.map((r, i) => (
            <div key={r.region} className="trend-region-row">
              <div className="trend-region-top">
                <span className="trend-region-flag">{r.flag}</span>
                <span className="trend-region-name">{i + 1}. {r.region}</span>
                <div className="trend-bar-wrap">
                  <div
                    className="trend-bar-fill"
                    style={{ width: `${r.score}%`, background: CHART_COLORS[i] || "#6366f1" }}
                  />
                </div>
                <span className="trend-bar-score">{r.score}</span>
              </div>
              <div className="trend-region-comment">{getRegionComment(r.region)}</div>
            </div>
          ))}
        </div>

        {/* Donut */}
        <div className="trend-donut-panel">
          <div className="trend-panel-title">Interest distribution</div>
          <DonutChart slices={pie_slices} />
          <div className="trend-donut-legend">
            {pie_slices.slice(0, 5).map((s, i) => (
              <div key={s.region} className="trend-legend-row">
                <div className="trend-legend-dot" style={{ background: CHART_COLORS[i] }} />
                <span className="trend-legend-name">{s.region}</span>
                <span className="trend-legend-pct">{s.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sparkline — only shown when time data available */}
      {time_trend && time_trend.length > 2 && (
        <div className="trend-sparkline-panel">
          <div className="trend-panel-title">Interest over time (12 months)</div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <Sparkline data={time_trend} />
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", lineHeight: 1.8 }}>
              <div>{time_trend[0]?.date}</div>
              <div>→ {time_trend[time_trend.length - 1]?.date}</div>
            </div>
          </div>
        </div>
      )}

      {/* AI Insight */}
      {summary && (
        <div className="trend-insight-box">
          <div className="trend-box-label">Market insight</div>
          <p className="trend-box-text">{summary}</p>
        </div>
      )}

      {/* Recommendation */}
      {recommendation && (
        <div className="trend-insight-box recommendation">
          <div className="trend-box-label recommendation">Campaign recommendation</div>
          <p className="trend-box-text">{recommendation}</p>
        </div>
      )}

      {/* Rising signals */}
      {rising && rising.length > 0 && (
        <div className="trend-rising-section">
          <div className="trend-panel-title">Rising search signals</div>
          <div className="trend-rising-grid">
            {rising.map((r, i) => (
              <div key={i} className="trend-rising-chip">
                <div className="trend-rising-query">{r.query}</div>
                <div className="trend-rising-value">{r.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CTA buttons */}
      {cta_geographies && cta_geographies.length > 0 && (
        <div className="trend-cta-row">
          <span className="trend-cta-label">Find leads in:</span>
          {cta_geographies.map((cta, i) => (
            <button
              key={i}
              className={`trend-cta-btn ${i === 0 ? "primary" : "ghost"}`}
              onClick={() => onTargetGeo && onTargetGeo(cta.geography)}
            >
              {top_regions[i]?.flag} {cta.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// EXISTING COMPONENTS (unchanged)
// ─────────────────────────────────────────────────────────────

function ContextPill({ field, value }) {
  return (
    <div className="context-pill">
      <span className="pill-icon">{FIELD_ICONS[field]}</span>
      <span className="pill-label">{FIELD_LABELS[field]}</span>
      <span className="pill-value">{value}</span>
    </div>
  );
}

function ProgressBar({ filled, total }) {
  const pct = Math.round((filled / total) * 100);
  return (
    <div className="progress-bar-wrap">
      <div className="progress-bar-track">
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="progress-label">{filled}/{total} fields</span>
    </div>
  );
}

function LeadsTable({ rows }) {
  if (!rows || rows.length === 0) return (
    <div className="empty-table">No matching leads found for this criteria.</div>
  );
  const cols = Object.keys(rows[0]);
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>{cols.map(c => <th key={c}>{c.replace(/_/g, " ")}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {cols.map(c => <td key={c}>{row[c] ?? "—"}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SuggestionGroup({ field, items, onSelect }) {
  return (
    <div className="suggestion-group">
      <div className="suggestion-group-label">
        <span>{FIELD_ICONS[field]}</span>
        <span>{SUGGESTION_LABELS[field] || field}</span>
      </div>
      <div className="suggestion-chips">
        {items.map(item => (
          <button key={item} className="chip" onClick={() => onSelect(item)}>
            {item}
          </button>
        ))}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="typing-indicator">
      <span /><span /><span />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────

export default function Intellegence() {
  const [messages, setMessages]         = useState([]);
  const [input, setInput]               = useState("");
  const [loading, setLoading]           = useState(false);
  const [context, setContext]           = useState({});
  const [suggestions, setSuggestions]   = useState({});
  const [progress, setProgress]         = useState({ filled: 0, total: 7 });
  const [chatHistory, setChatHistory]   = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [sidebarOpen, setSidebarOpen]   = useState(true);

  const bottomRef   = useRef(null);
  const textareaRef = useRef(null);
  const sessionRef  = useRef(SESSION_ID);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, suggestions, loading]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
  }, [input]);

  const pushMessage = useCallback((msg) => {
    setMessages(prev => [...prev, { id: Date.now() + Math.random(), ...msg }]);
  }, []);

  const sendMessage = useCallback(async (text) => {
    const finalText = (text || input).trim();
    if (!finalText || loading) return;

    pushMessage({ role: "user", text: finalText });
    setInput("");
    setLoading(true);
    setSuggestions({});

    try {
      const res = await fetch(`${API_BASE}/context/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionRef.current,
          message: finalText,
        }),
      });

      const data = await res.json();
      console.log("[API Response]", data);

      if (data.context)  setContext(data.context);
      if (data.progress) setProgress(data.progress);

      // ── Trend query ───────────────────────────────────────
      if (data.status === "intent_handled" && data.intent_type === "trend_query") {
        if (data.response) {
          pushMessage({ role: "bot", text: data.response });
        }
        if (data.trend_data) {
          pushMessage({ role: "bot", trendData: data.trend_data });
        }
        setSuggestions({});

      // ── General / off-topic ───────────────────────────────
      } else if (data.status === "intent_handled") {
        if (data.response) pushMessage({ role: "bot", text: data.response });
        setSuggestions({});

      // ── Lead flow complete ────────────────────────────────
      } else if (data.status === "complete") {
        if (data.summary) pushMessage({ role: "bot", text: data.summary });
        pushMessage({ role: "bot", table: data.leads || data.data || [] });
        setSuggestions({});
        setProgress({ filled: 7, total: 7 });

      // ── In progress — collecting context ──────────────────
      } else {
        if (data.response) pushMessage({ role: "bot", text: data.response });
        if (data.suggestions) {
          const filtered = {};
          for (const [k, v] of Object.entries(data.suggestions)) {
            if (Array.isArray(v) && v.length > 0) filtered[k] = v;
          }
          setSuggestions(filtered);
        }
      }

    } catch (err) {
      console.error(err);
      pushMessage({ role: "bot", text: "Something went wrong connecting to the server. Please try again." });
    } finally {
      setLoading(false);
    }
  }, [input, loading, pushMessage]);

  // Called when user clicks "Target United States" etc. on the TrendCard
  const handleGeoSelect = useCallback((geography) => {
    sendMessage(`Use ${geography}`);
  }, [sendMessage]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const startNewChat = async () => {
    if (messages.length > 0) {
      const title = messages.find(m => m.role === "user")?.text?.slice(0, 40) || "Chat";
      setChatHistory(prev => [
        { id: Date.now(), title, messages, context },
        ...prev,
      ]);
    }
    try {
      await fetch(`${API_BASE}/context/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionRef.current }),
      });
    } catch {}

    setMessages([]);
    setInput("");
    setSuggestions({});
    setContext({});
    setProgress({ filled: 0, total: 7 });
    setActiveChatId(null);
  };

  const loadChat = (chat) => {
    setMessages(chat.messages);
    setContext(chat.context || {});
    setSuggestions({});
    setActiveChatId(chat.id);
  };

  const filledFields = FIELD_ORDER.filter(f => context[f]);

  return (
    <div className={`app-shell ${sidebarOpen ? "sidebar-open" : ""}`}>

      {/* ═══ SIDEBAR ═════════════════════════════════════ */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <span>Delphi</span>
          </div>
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(v => !v)} title="Toggle sidebar">
            ‹
          </button>
        </div>

        <button className="new-chat-btn" onClick={startNewChat}>
          <span>＋</span> New Search
        </button>

        {filledFields.length > 0 && (
          <div className="context-panel">
            <div className="context-panel-title">Context</div>
            {filledFields.map(f => (
              <ContextPill key={f} field={f} value={context[f]} />
            ))}
            <ProgressBar filled={filledFields.length} total={7} />
          </div>
        )}

        <div className="history-list">
          {messages.length > 0 && !activeChatId && (
            <div className="history-item active">
              {messages.find(m => m.role === "user")?.text?.slice(0, 38) || "Current chat"}
            </div>
          )}
          {chatHistory.map(chat => (
            <div
              key={chat.id}
              className={`history-item ${activeChatId === chat.id ? "active" : ""}`}
              onClick={() => loadChat(chat)}
            >
              {chat.title}
            </div>
          ))}
          {chatHistory.length === 0 && messages.length === 0 && (
            <p className="history-empty">Start a conversation to find leads</p>
          )}
        </div>

        <div className="sidebar-footer">
          <div className="avatar">D</div>
          <div className="user-info">
            <span className="user-name">Delphi User</span>
            <span className="user-email">B2B Lead Intelligence</span>
          </div>
        </div>
      </aside>

      {!sidebarOpen && (
        <button className="sidebar-reopen" onClick={() => setSidebarOpen(true)} title="Open sidebar">
          ›
        </button>
      )}

      {/* ═══ MAIN PANEL ══════════════════════════════════ */}
      <main className="main-panel">

        {messages.length === 0 && (
          <div className="empty-state">
            <h1 className="empty-title">Describe your target audience and find the best matching leads</h1>
            <div className="starter-prompts">
              {[
                "I want to run a campaign targeting C-Level at mid-size tech companies in the US",
                "Find me marketing leads in the healthcare sector in Europe",
                "Which region is trending for laptop products?",
              ].map(prompt => (
                <button key={prompt} className="starter-chip" onClick={() => sendMessage(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className={`messages-area ${messages.length === 0 ? "no-scroll" : ""}`}>
          {messages.map((msg) => (
            <div key={msg.id} className={`message-row ${msg.role}`}>
              {msg.role === "bot" && (
                <div className="bot-avatar" />
              )}
              <div className="message-content">
                {msg.text && <div className="bubble">{msg.text}</div>}
                {msg.table !== undefined && <LeadsTable rows={msg.table} />}
                {/* ── TREND CARD rendered here ── */}
                {msg.trendData && (
                  <TrendCard
                    data={msg.trendData}
                    onTargetGeo={handleGeoSelect}
                  />
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message-row bot">
              <div className="bot-avatar" />
              <div className="message-content">
                <div className="bubble"><TypingDots /></div>
              </div>
            </div>
          )}

          {!loading && Object.keys(suggestions).length > 0 && (
            <div className="suggestions-area">
              {Object.entries(suggestions).map(([field, items]) => (
                <SuggestionGroup
                  key={field}
                  field={field}
                  items={items}
                  onSelect={(val) => sendMessage(val)}
                />
              ))}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* ═══ INPUT ═══════════════════════════════════════ */}
        <div className="input-zone">
          <div className="input-card">
            <textarea
              ref={textareaRef}
              className="chat-input"
              placeholder=""
              value={input}
              rows={1}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button
              className="send-btn"
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              title="Send"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
          <p className="input-hint"></p>
        </div>

      </main>
    </div>
  );
}