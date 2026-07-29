// Intelligence.js — Enterprise Redesign
import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import "./intellegence.css";

const API_BASE   = "http://127.0.0.1:8000";
const SESSION_ID = `user_${Math.random().toString(36).slice(2, 9)}`;

// ── Field definitions ────────────────────────────────────────────────────────

const PRODUCT_FIELD_LABELS = {
  product_description:  "Product",
  product_name:         "Product Name",
  product_usps:         "USPs",
  product_pricing_tier: "Positioning",
  campaign_budget:      "Budget",
  ideal_buyer:          "Ideal Buyer",
  target_market_type:   "Market Type",
  buyer_stage:          "Buyer Stage",
};

const PRODUCT_FIELD_ORDER = [
  "product_description", "product_name", "product_usps",
  "product_pricing_tier", "campaign_budget", "ideal_buyer",
  "target_market_type", "buyer_stage",
];

const TARGETING_FIELD_LABELS = {
  geography:     "Geography",
  industry:      "Industry",
  job_function:  "Job Function",
  job_level:     "Seniority",
  employee_size: "Company Size",
  revenue_range: "Lead Revenue",
};

const TARGETING_FIELD_ORDER = [
  "geography", "industry", "job_function",
  "job_level", "employee_size", "revenue_range",
];

const SUGGESTION_LABELS = {
  geography:     "Target Geographies",
  industry:      "Industries",
  job_function:  "Job Functions",
  job_level:     "Seniority Levels",
  employee_size: "Company Sizes",
  revenue_range: "Lead Revenue Ranges",
};

const ALL_FIELDS = [...PRODUCT_FIELD_ORDER, ...TARGETING_FIELD_ORDER];

// ── Utility: parse lead text strings ────────────────────────────────────────
function parseLeadText(text) {
  if (typeof text !== "string") return null;
  const row = {};
  const companyMatch = text.match(/Lead works at ([^.]+)\./);
  if (companyMatch) row["Company"] = companyMatch[1].trim();
  const pairs = [
    ["Industry",      /Industry:\s*([^.]+)\./],
    ["Job Title",     /Job title:\s*([^.]+)\./],
    ["Job Function",  /Job function:\s*([^.]+)\./],
    ["Seniority",     /Seniority:\s*([^.]+?)(?:\.|$)/],
    ["Employee Size", /Employee[_ ](?:size|count)?:\s*([^.]+)\./i],
    ["Revenue",       /Revenue[_ ]range:\s*([^.]+)\./i],
    ["Geography",     /Geography:\s*([^.]+)\./i],
  ];
  for (const [key, rx] of pairs) {
    const m = text.match(rx);
    if (m) row[key] = m[1].trim();
  }
  return Object.keys(row).length > 0 ? row : null;
}

function normalizeRow(row) {
  if (typeof row === "string") return parseLeadText(row) || { Profile: row };
  if (row && typeof row === "object") {
    const out = {};
    for (const [k, v] of Object.entries(row)) {
      const label = k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      out[label] = v ?? "—";
    }
    return out;
  }
  return { Value: String(row) };
}

const PRIORITY_COLS = [
  "Company", "Job Title", "Seniority", "Industry",
  "Job Function", "Domain", "Employee Size", "Revenue", "Geography",
];

function sortColumns(cols) {
  const priority = PRIORITY_COLS.filter(c => cols.includes(c));
  const rest = cols.filter(c => !PRIORITY_COLS.includes(c));
  return [...priority, ...rest];
}

// ── Seniority badge ──────────────────────────────────────────────────────────
const SENIORITY_COLORS = {
  "c level":       { bg: "#fef3c7", text: "#92400e", border: "#fcd34d" },
  "c-level":       { bg: "#fef3c7", text: "#92400e", border: "#fcd34d" },
  "chief":         { bg: "#fef3c7", text: "#92400e", border: "#fcd34d" },
  "ceo":           { bg: "#fef3c7", text: "#92400e", border: "#fcd34d" },
  "cto":           { bg: "#fef3c7", text: "#92400e", border: "#fcd34d" },
  "cfo":           { bg: "#fef3c7", text: "#92400e", border: "#fcd34d" },
  "vp":            { bg: "#ede9fe", text: "#4c1d95", border: "#c4b5fd" },
  "vice president":{ bg: "#ede9fe", text: "#4c1d95", border: "#c4b5fd" },
  "director":      { bg: "#dbeafe", text: "#1e40af", border: "#93c5fd" },
  "manager":       { bg: "#dcfce7", text: "#14532d", border: "#86efac" },
  "senior":        { bg: "#f0fdf4", text: "#166534", border: "#bbf7d0" },
};

function SeniorityBadge({ value }) {
  if (!value) return <span className="lt-cell-dash">—</span>;
  const key = value.toLowerCase();
  const style = Object.entries(SENIORITY_COLORS).find(([k]) => key.includes(k))?.[1];
  if (!style) return <span className="lt-cell-text">{value}</span>;
  return (
    <span className="lt-seniority-badge"
      style={{ background: style.bg, color: style.text, border: `1px solid ${style.border}` }}>
      {value}
    </span>
  );
}

const INDUSTRY_ICONS = {
  software: "💻", technology: "💻", computers: "💻",
  healthcare: "🏥", health: "🏥",
  finance: "🏦", financial: "🏦", banking: "🏦", fintech: "🏦",
  manufacturing: "🏭",
  retail: "🛍️",
  education: "🎓",
  "real estate": "🏢",
  energy: "⚡",
  media: "📺", entertainment: "📺",
  telecommunications: "📡",
  agriculture: "🌾",
};

function IndustryCell({ value }) {
  if (!value) return <span className="lt-cell-dash">—</span>;
  const icon = Object.entries(INDUSTRY_ICONS).find(([k]) => value.toLowerCase().includes(k))?.[1] || "🏢";
  return (
    <span className="lt-industry-cell">
      <span>{icon}</span>
      {value}
    </span>
  );
}

// ── Leads Table ──────────────────────────────────────────────────────────────
function LeadsTable({ rows }) {
  const [page, setPage]             = useState(0);
  const [sortCol, setSortCol]       = useState(null);
  const [sortDir, setSortDir]       = useState("asc");
  const [search, setSearch]         = useState("");
  const [expandedRow, setExpandedRow] = useState(null);
  const PAGE_SIZE = 15;

  const normalized = useMemo(() =>
    !rows?.length ? [] : rows.map(normalizeRow).filter(Boolean), [rows]);

  const columns = useMemo(() => {
    if (!normalized.length) return [];
    const allKeys = new Set();
    normalized.forEach(r => Object.keys(r).forEach(k => allKeys.add(k)));
    return sortColumns([...allKeys]);
  }, [normalized]);

  const filtered = useMemo(() => {
    if (!search.trim()) return normalized;
    const q = search.toLowerCase();
    return normalized.filter(row =>
      Object.values(row).some(v => String(v).toLowerCase().includes(q))
    );
  }, [normalized, search]);

  const sorted = useMemo(() => {
    if (!sortCol) return filtered;
    return [...filtered].sort((a, b) => {
      const av = String(a[sortCol] ?? "");
      const bv = String(b[sortCol] ?? "");
      return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
    });
  }, [filtered, sortCol, sortDir]);

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const pageRows   = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleSort = col => {
    if (sortCol === col) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortCol(col); setSortDir("asc"); }
    setPage(0);
  };

  const pageWindow = () => {
    const start = Math.max(0, Math.min(page - 2, totalPages - 5));
    return Array.from({ length: Math.min(5, totalPages) }, (_, i) => start + i);
  };

  if (!rows?.length) {
    return (
      <div className="lt-empty">
        <div className="lt-empty-icon">🔍</div>
        <p>No matching leads found for this criteria.</p>
      </div>
    );
  }

  return (
    <div className="lt-wrapper">
      <div className="lt-toolbar">
        <div className="lt-count">
          <span className="lt-count-num">{sorted.length}</span>
          <span className="lt-count-label">leads found</span>
        </div>
        <div className="lt-search-wrap">
          <svg className="lt-search-icon" width="13" height="13" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            className="lt-search-input"
            placeholder="Filter results..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0); }}
          />
          {search && (
            <button className="lt-search-clear" onClick={() => setSearch("")}>✕</button>
          )}
        </div>
      </div>

      <div className="lt-scroll">
        <table className="lt-table">
          <thead>
            <tr>
              <th className="lt-th lt-th-num">#</th>
              {columns.map(col => (
                <th key={col}
                  className={`lt-th ${sortCol === col ? "lt-th-sorted" : ""}`}
                  onClick={() => handleSort(col)}
                >
                  <span className="lt-th-inner">
                    {col}
                    <span className="lt-sort-icon">
                      {sortCol === col ? (sortDir === "asc" ? "↑" : "↓") : "⇅"}
                    </span>
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, i) => {
              const absIdx = page * PAGE_SIZE + i;
              const isExpanded = expandedRow === absIdx;
              return (
                <React.Fragment key={absIdx}>
                  <tr
                    className={`lt-row ${isExpanded ? "lt-row-expanded" : ""}`}
                    onClick={() => setExpandedRow(isExpanded ? null : absIdx)}
                  >
                    <td className="lt-td lt-td-num">{absIdx + 1}</td>
                    {columns.map(col => (
                      <td key={col} className="lt-td">
                        {col === "Seniority"  ? <SeniorityBadge value={row[col]} /> :
                         col === "Industry"   ? <IndustryCell value={row[col]} /> :
                         col === "Company"    ? <span className="lt-cell-company">{row[col] || "—"}</span> :
                         col === "Job Title"  ? <span className="lt-cell-jobtitle">{row[col] || "—"}</span> :
                         <span className={row[col] && row[col] !== "—" ? "lt-cell-text" : "lt-cell-dash"}>
                           {row[col] || "—"}
                         </span>
                        }
                      </td>
                    ))}
                  </tr>
                  {isExpanded && (
                    <tr className="lt-detail-row">
                      <td colSpan={columns.length + 1}>
                        <div className="lt-detail-grid">
                          {columns.map(col =>
                            row[col] && row[col] !== "—" && (
                              <div key={col} className="lt-detail-item">
                                <span className="lt-detail-label">{col}</span>
                                <span className="lt-detail-value">{row[col]}</span>
                              </div>
                            )
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="lt-pagination">
          <span className="lt-page-info">Page {page + 1} of {totalPages} · {sorted.length} results</span>
          <div className="lt-page-btns">
            <button className="lt-page-btn" disabled={page === 0} onClick={() => setPage(0)}>«</button>
            <button className="lt-page-btn" disabled={page === 0} onClick={() => setPage(p => p - 1)}>‹</button>
            {pageWindow().map(p => (
              <button key={p}
                className={`lt-page-btn ${p === page ? "lt-page-btn-active" : ""}`}
                onClick={() => setPage(p)}
              >{p + 1}</button>
            ))}
            <button className="lt-page-btn" disabled={page === totalPages - 1} onClick={() => setPage(p => p + 1)}>›</button>
            <button className="lt-page-btn" disabled={page === totalPages - 1} onClick={() => setPage(totalPages - 1)}>»</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Sidebar Panel ────────────────────────────────────────────────────────────
function SidebarPanel({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="sidebar-panel">
      <button className="sidebar-panel-header" onClick={() => setOpen(v => !v)}>
        <span className="sidebar-panel-title">{title}</span>
        <span className={`sidebar-panel-chevron ${open ? "open" : ""}`}>›</span>
      </button>
      {open && <div className="sidebar-panel-body">{children}</div>}
    </div>
  );
}

// ── Icon set (line icons, no emoji) ─────────────────────────────────────────
const Icon = {
  Tag: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M20.59 13.41L13.41 20.59a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="7" cy="7" r="1.3" fill="currentColor"/>
    </svg>
  ),
  Compass: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8"/>
      <path d="M15.5 8.5l-2 5-5 2 2-5 5-2Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
    </svg>
  ),
  Clock: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8"/>
      <path d="M12 7v5l3.5 2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  Target: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.6"/>
      <circle cx="12" cy="12" r="4.5" stroke="currentColor" strokeWidth="1.6"/>
      <circle cx="12" cy="12" r="1.2" fill="currentColor"/>
    </svg>
  ),
  Users: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <circle cx="9" cy="8" r="3" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
      <circle cx="17" cy="9" r="2.4" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M15.2 14.3c2.4.2 4.3 2 4.3 4.7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  ),
  Bulb: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M9 18h6M10 21h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
      <path d="M12 3a6.5 6.5 0 0 0-4 11.6c.6.5 1 1.2 1 2v.4h6v-.4c0-.8.4-1.5 1-2A6.5 6.5 0 0 0 12 3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
    </svg>
  ),
  Trend: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M3 17l6-6 4 4 8-8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M15 7h6v6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
};

// ── Sidebar Section Card (base) ─────────────────────────────────────────────
function SectionCard({ icon, title, subtitle, onClick, active }) {
  return (
    <button className={`section-card ${active ? "active" : ""}`} onClick={onClick}>
      <div className="section-card-icon">{icon}</div>
      <div className="section-card-body">
        <span className="section-card-title">{title}</span>
        <span className="section-card-subtitle">{subtitle}</span>
      </div>
      <span className="section-card-arrow">›</span>
    </button>
  );
}

// ── Dedicated sidebar cards ─────────────────────────────────────────────────
function ProductServicesCard({ subtitle, active, onClick }) {
  return (
    <SectionCard
      icon={<Icon.Tag />}
      title="Product / Services"
      subtitle={subtitle || "Not set — tap to select"}
      active={active}
      onClick={onClick}
    />
  );
}

function ContextCard({ hasAnyContext, overallPct, active, onClick }) {
  return (
    <SectionCard
      icon={<Icon.Compass />}
      title="Context"
      subtitle={hasAnyContext ? `${overallPct}% complete` : "No context yet"}
      active={active}
      onClick={onClick}
    />
  );
}

function SearchHistoryCard({ chatHistory, active, onClick }) {
  return (
    <SectionCard
      icon={<Icon.Clock />}
      title="Search History"
      subtitle={chatHistory.length > 0 ? `${chatHistory.length} past searches` : "No history yet"}
      active={active}
      onClick={onClick}
    />
  );
}

// ── Middle Action Card (base) ───────────────────────────────────────────────
function ActionCard({ icon, title, description, onClick, disabled }) {
  return (
    <button className="action-card" onClick={onClick} disabled={disabled}>
      <div className="action-card-icon">{icon}</div>
      <div className="action-card-title">{title}</div>
      <div className="action-card-desc">{description}</div>
    </button>
  );
}

// ── Dedicated middle cards ──────────────────────────────────────────────────
function CreateICPCard({ productName, onClick }) {
  return (
    <ActionCard
      icon={<Icon.Target />}
      title={`Create ICP${productName ? ` for ${productName}` : ""}`}
      description="Build your ideal customer profile"
      onClick={onClick}
    />
  );
}

function DiscoverBuyerGroupCard({ onClick }) {
  return (
    <ActionCard
      icon={<Icon.Users />}
      title="Discover Buyer Group"
      description="Map the decision makers involved"
      onClick={onClick}
    />
  );
}

function InsightsCard({ onClick }) {
  return (
    <ActionCard
      icon={<Icon.Bulb />}
      title="Insights"
      description="Surface key signals about your market"
      onClick={onClick}
    />
  );
}

function CurrentTrendCard({ onClick }) {
  return (
    <ActionCard
      icon={<Icon.Trend />}
      title="Current Trend"
      description="See what's trending in your space"
      onClick={onClick}
    />
  );
}

// ── Simple Modal Wrapper ─────────────────────────────────────────────────────
function Modal({ title, onClose, children, wide }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className={`modal-panel ${wide ? "wide" : ""}`} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">{title}</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

// ── Context Pill ─────────────────────────────────────────────────────────────
function ContextPill({ label, value }) {
  return (
    <div className="context-pill">
      <span className="pill-label">{label}</span>
      <span className="pill-value" title={value}>{value}</span>
    </div>
  );
}

// ── Typing Dots ──────────────────────────────────────────────────────────────
function TypingDots() {
  return (
    <div className="typing-indicator">
      <span /><span /><span />
    </div>
  );
}

// ── Suggestion Group ─────────────────────────────────────────────────────────
function SuggestionGroup({ field, items, onSelect }) {
  return (
    <div className="suggestion-group">
      <div className="suggestion-group-label">
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

// ── Progress Bar ─────────────────────────────────────────────────────────────
function ProgressBar({ filled, total }) {
  const pct = total > 0 ? Math.round((filled / total) * 100) : 0;
  return (
    <div className="progress-bar-wrap">
      <div className="progress-bar-track">
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="progress-label">{pct}%</span>
    </div>
  );
}

// ── Phase Badge ──────────────────────────────────────────────────────────────
function PhaseBadge({ phase }) {
  if (!phase || phase === "complete") return null;
  const isProduct = phase === "product";
  const label = isProduct ? "Product & Campaign" : "Audience Targeting";
  const color = isProduct ? "var(--violet)" : "var(--accent)";
  const bg    = isProduct ? "var(--violet-soft)" : "var(--accent-soft)";
  return (
    <div className="phase-badge" style={{ background: bg, color, borderColor: color }}>
      <span className="phase-dot" style={{ background: color }} />
      {label}
    </div>
  );
}

// ── Editable Tag List (for Context modal: geography/industry/category/domain) ─
function EditableTagList({ values, onChange }) {
  const [draft, setDraft] = useState("");

  const addTag = () => {
    const v = draft.trim();
    if (!v) return;
    onChange([...(values || []), v]);
    setDraft("");
  };

  const removeTag = idx => {
    onChange((values || []).filter((_, i) => i !== idx));
  };

  return (
    <div>
      <div className="suggestion-chips">
        {(values || []).length === 0 && (
          <span className="lt-cell-dash">No values selected</span>
        )}
        {(values || []).map((v, i) => (
          <button key={`${v}-${i}`} className="chip" onClick={() => removeTag(i)}>
            {v} ✕
          </button>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <input
          className="modal-textarea"
          style={{ flex: 1, minHeight: "auto" }}
          value={draft}
          placeholder="Add value and press Enter..."
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
        />
        <button className="modal-btn modal-btn-primary" onClick={addTag}>Add</button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════

export default function Intellegence() {
  const [messages,      setMessages]      = useState([]);
  const [input,         setInput]         = useState("");
  const [loading,       setLoading]       = useState(false);
  const [context,       setContext]       = useState({});
  const [suggestions,   setSuggestions]   = useState({});
  const [phase,         setPhase]         = useState("product");
  const [chatHistory,   setChatHistory]   = useState([]);
  const [activeChatId,  setActiveChatId]  = useState(null);
  const [sidebarOpen,   setSidebarOpen]   = useState(true);
  const [darkMode,      setDarkMode]      = useState(() => {
    return localStorage.getItem("delphi-theme") === "dark";
  });

  // Section modal state: which sidebar card is expanded ("product" | "context" | "history" | null)
  const [activeSection,   setActiveSection]   = useState(null);

  // ── Product/Service selection (fetched from delphi_company_profiles) ──────
  const [productItems,     setProductItems]     = useState([]);
  const [selectedProduct,  setSelectedProduct]  = useState(null);
  const [productsLoading,  setProductsLoading]  = useState(false);

  // ── Targeting context (delphi_context_builder_user_selections) ────────────
  const [userContext,      setUserContext]      = useState(null);
  const [contextLoading,   setContextLoading]   = useState(false);

  // ── ICP generation ──────────────────────────────────────────────────────────
  const [icpModalOpen, setIcpModalOpen] = useState(false);
  const [icpLoading,   setIcpLoading]   = useState(false);
  const [icpData,      setIcpData]      = useState(null);
  const [icpForm,       setIcpForm]     = useState({ country_id: "", industry_id: "", brand_id: "" });

  const bottomRef   = useRef(null);
  const textareaRef = useRef(null);
  const sessionRef  = useRef(SESSION_ID);

  // Load user info from localStorage
  const user = useMemo(() => {
    try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
  }, []);

  const USER_ID = user.user_id || user.id;

  const userInitials = useMemo(() => {
    const name = user.full_name || user.email || "D";
    return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  }, [user]);

  // Apply theme to document root
  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.setAttribute("data-theme", "dark");
      localStorage.setItem("delphi-theme", "dark");
    } else {
      root.removeAttribute("data-theme");
      localStorage.setItem("delphi-theme", "light");
    }
  }, [darkMode]);

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

  const pushMessage = useCallback(msg => {
    setMessages(prev => [...prev, { id: Date.now() + Math.random(), ...msg }]);
  }, []);

  // ── Fetch product/service list + current selection ────────────────────────
  const fetchProducts = useCallback(async () => {
    if (!USER_ID) return;
    setProductsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/profile/products/${USER_ID}`);
      const data = await res.json();
      setProductItems(data.items || []);
      setSelectedProduct(data.selected || null);
    } catch (err) {
      console.error("Failed to fetch products:", err);
    } finally {
      setProductsLoading(false);
    }
  }, [USER_ID]);

  // ── Fetch targeting context (geographies/industries/categories/domains) ───
  const fetchUserContext = useCallback(async () => {
    if (!USER_ID) return;
    setContextLoading(true);
    try {
      const res = await fetch(`${API_BASE}/profile/context/${USER_ID}`);
      const data = await res.json();
      setUserContext(data.context || null);
    } catch (err) {
      console.error("Failed to fetch context:", err);
    } finally {
      setContextLoading(false);
    }
  }, [USER_ID]);

  useEffect(() => {
    if (USER_ID) {
      fetchProducts();
      fetchUserContext();
    }
  }, [USER_ID, fetchProducts, fetchUserContext]);

  // ── Select a product/service (sets flag in DB) ─────────────────────────────
  const selectProduct = async (item) => {
    try {
      await fetch(`${API_BASE}/profile/products/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: USER_ID,
          profile_id: item.profile_id,
          value: item.value,
          type: item.type,
        }),
      });
      setSelectedProduct({ ...item, selected: true });
      setProductItems(prev =>
        prev.map(i => ({
          ...i,
          selected: i.value === item.value && i.profile_id === item.profile_id,
        }))
      );
    } catch (err) {
      console.error("Failed to select product:", err);
    } finally {
      setActiveSection(null);
    }
  };

  // ── Update targeting context field (geography/industry/category/domain) ───
  const updateContextField = async (field, values) => {
    try {
      await fetch(`${API_BASE}/profile/context/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID, [field]: values }),
      });
      setUserContext(prev => ({ ...(prev || {}), [field]: values }));
    } catch (err) {
      console.error("Failed to update context:", err);
    }
  };

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
        body: JSON.stringify({ session_id: sessionRef.current, message: finalText }),
      });

      const data = await res.json();
      console.log("[API Response]", data);

      if (data.context)  setContext(data.context);
      if (data.phase)    setPhase(data.phase);

      if (data.status === "complete") {
        if (data.summary) pushMessage({ role: "bot", text: data.summary });
        pushMessage({ role: "bot", table: data.leads || data.data || [] });
        setSuggestions({});
        setPhase("complete");
      } else {
        if (data.response) {
          pushMessage({
            role: "bot",
            text: data.response,
            editApplied: data.edit_applied || null,
          });
        }
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

  const handleKeyDown = e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const startNewChat = async () => {
    if (messages.length > 0) {
      const title = messages.find(m => m.role === "user")?.text?.slice(0, 42) || "Chat";
      setChatHistory(prev => [{ id: Date.now(), title, messages, context }, ...prev]);
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
    setPhase("product");
    setActiveChatId(null);
  };

  const loadChat = chat => {
    setMessages(chat.messages);
    setContext(chat.context || {});
    setSuggestions({});
    setActiveChatId(chat.id);
    setActiveSection(null);
  };

  // ── ICP generation ──────────────────────────────────────────────────────────
  const runICP = async () => {
    setIcpLoading(true);
    setIcpData(null);
    try {
      const res = await fetch(`${API_BASE}/icp/generate-insight`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product: selectedProduct?.value || context.product_name || context.product_description,
          country_id: icpForm.country_id,
          industry_id: icpForm.industry_id,
          brand_id: icpForm.brand_id,
        }),
      });
      const data = await res.json();
      setIcpData(data.insight);
    } catch (err) {
      console.error("ICP generation failed:", err);
    } finally {
      setIcpLoading(false);
    }
  };

  const filledProductFields   = PRODUCT_FIELD_ORDER.filter(f => context[f]);
  const filledTargetingFields = TARGETING_FIELD_ORDER.filter(f => context[f]);
  const totalFilled           = filledProductFields.length + filledTargetingFields.length;
  const hasAnyContext         = totalFilled > 0;

  const overallPct = Math.round((totalFilled / ALL_FIELDS.length) * 100);

  const contextFieldsMap = [
    { key: "geographies", label: "Geographies" },
    { key: "industries",  label: "Industries" },
    { key: "categories",  label: "Categories" },
    { key: "domains",     label: "Domains" },
  ];

  return (
    <div className={`app-shell ${sidebarOpen ? "sidebar-open" : ""}`}>

      {/* ══ SIDEBAR ══════════════════════════════════════════════ */}
      <aside className="sidebar">

        {/* Header */}
        <div className="sidebar-header">
          <div className="sidebar-brand">Del<span>phi</span></div>
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(v => !v)}
            title="Collapse sidebar"
          >‹</button>
        </div>

        {/* New chat */}
        <button className="new-chat-btn" onClick={startNewChat}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
          New Search
        </button>

        {/* Phase */}
        <PhaseBadge phase={phase} />

        {/* Section cards */}
        <div className="sidebar-context-scroll">
          <ProductServicesCard
            subtitle={selectedProduct?.value}
            active={activeSection === "product"}
            onClick={() => setActiveSection("product")}
          />
          <ContextCard
            hasAnyContext={hasAnyContext}
            overallPct={overallPct}
            active={activeSection === "context"}
            onClick={() => setActiveSection("context")}
          />
          <SearchHistoryCard
            chatHistory={chatHistory}
            active={activeSection === "history"}
            onClick={() => setActiveSection("history")}
          />
        </div>

        {/* Footer */}
        <div className="sidebar-footer">
          <div className="avatar">{userInitials}</div>
          <div className="user-info">
            <span className="user-name">{user.full_name || "Delphi User"}</span>
            <span className="user-email">{user.email || "B2B Lead Intelligence"}</span>
          </div>
          {/* Theme toggle in footer */}
          <button
            className="theme-toggle"
            onClick={() => setDarkMode(v => !v)}
            title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
          >
            {darkMode ? "☀" : "🌙"}
          </button>
        </div>
      </aside>

      {/* ══ SECTION MODALS ══════════════════════════════════════ */}

      {/* PRODUCT / SERVICE MODAL */}
      {activeSection === "product" && (
        <Modal title="Product / Services" onClose={() => setActiveSection(null)}>
          <p className="modal-hint">
            These are the products, services, and brands detected for your account.
            Select one to make it the active context for searches and ICP generation.
          </p>
          <label className="modal-label">Currently Selected</label>
          <div className="modal-current-value">
            {selectedProduct?.value || "No product selected yet"}
          </div>
          <label className="modal-label">Choose one</label>
          {productsLoading && <p className="history-empty">Loading products...</p>}
          <div className="suggestion-chips">
            {productItems.map(item => (
              <button
                key={`${item.profile_id}-${item.type}-${item.value}`}
                className={`chip ${item.selected ? "chip-active" : ""}`}
                onClick={() => selectProduct(item)}
              >
                {item.value} <span className="chip-type">({item.type})</span>
              </button>
            ))}
            {!productsLoading && productItems.length === 0 && (
              <p className="history-empty">No products/services found.</p>
            )}
          </div>
        </Modal>
      )}

      {/* CONTEXT MODAL (geography/industry/category/domain) */}
      {activeSection === "context" && (
        <Modal title="Context" onClose={() => setActiveSection(null)} wide>
          <p className="modal-hint">
            The targeting context saved for your account. Add or remove values below —
            changes are saved automatically.
          </p>
          {contextLoading && <p className="history-empty">Loading context...</p>}
          {!contextLoading && contextFieldsMap.map(({ key, label }) => (
            <SidebarPanel key={key} title={label} defaultOpen>
              <EditableTagList
                values={userContext?.[key] || []}
                onChange={vals => updateContextField(key, vals)}
              />
            </SidebarPanel>
          ))}

          {hasAnyContext && (
            <div className="overall-progress">
              <span className="overall-label">Profile complete</span>
              <ProgressBar filled={totalFilled} total={ALL_FIELDS.length} />
            </div>
          )}
        </Modal>
      )}

      {activeSection === "history" && (
        <Modal title="Search History" onClose={() => setActiveSection(null)}>
          <div className="history-list history-list-modal">
            {messages.length > 0 && !activeChatId && (
              <div className="history-item active" onClick={() => setActiveSection(null)}>
                {messages.find(m => m.role === "user")?.text?.slice(0, 48) || "Current search"}
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
              <p className="history-empty">Your searches will appear here</p>
            )}
          </div>
        </Modal>
      )}

      {/* ICP MODAL */}
      {icpModalOpen && (
        <Modal
          title="Create ICP"
          onClose={() => { setIcpModalOpen(false); setIcpData(null); }}
          wide
        >
          {!icpData && (
            <>
              <label className="modal-label">Product</label>
              <div className="modal-current-value">
                {selectedProduct?.value || context.product_name || "No product selected"}
              </div>
              <label className="modal-label">Country ID</label>
              <input
                className="modal-textarea"
                value={icpForm.country_id}
                onChange={e => setIcpForm(f => ({ ...f, country_id: e.target.value }))}
              />
              <label className="modal-label">Industry ID</label>
              <input
                className="modal-textarea"
                value={icpForm.industry_id}
                onChange={e => setIcpForm(f => ({ ...f, industry_id: e.target.value }))}
              />
              <label className="modal-label">Brand ID</label>
              <input
                className="modal-textarea"
                value={icpForm.brand_id}
                onChange={e => setIcpForm(f => ({ ...f, brand_id: e.target.value }))}
              />
              <div className="modal-actions">
                <button
                  className="modal-btn modal-btn-primary"
                  disabled={icpLoading}
                  onClick={runICP}
                >
                  {icpLoading ? "Generating..." : "Generate ICP"}
                </button>
              </div>
            </>
          )}

          {icpData && (
            <div className="icp-result">
              <p className="modal-hint">{icpData.icp_summary}</p>

              <SidebarPanel title="Top Industries" defaultOpen>
                {icpData.top_industries?.map(i => (
                  <ContextPill key={i.name} label={i.name} value={i.score} />
                ))}
              </SidebarPanel>

              <SidebarPanel title="Top Job Titles" defaultOpen>
                {icpData.top_job_titles?.map(j => (
                  <ContextPill key={j.title} label={j.title} value={j.score} />
                ))}
              </SidebarPanel>

              <SidebarPanel title="Firmographics" defaultOpen>
                <ContextPill label="Employee Size" value={icpData.firmographics?.employee_size} />
                <ContextPill label="Revenue Range" value={icpData.firmographics?.revenue_range} />
                <ContextPill label="Geography" value={icpData.firmographics?.geography} />
              </SidebarPanel>

              <SidebarPanel title="Next Steps" defaultOpen>
                <ul>
                  {icpData.recommended_next_steps?.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </SidebarPanel>

              <div className="modal-actions">
                <button className="modal-btn modal-btn-secondary" onClick={() => setIcpData(null)}>
                  Regenerate
                </button>
              </div>
            </div>
          )}
        </Modal>
      )}

      {/* Collapsed toggle */}
      {!sidebarOpen && (
        <button
          className="sidebar-reopen"
          onClick={() => setSidebarOpen(true)}
          title="Open sidebar"
        >›</button>
      )}

      {/* ══ MAIN PANEL ═══════════════════════════════════════════ */}
      <main className="main-panel">

        {/* Quick action cards */}
        <div className="action-cards-grid">
          <CreateICPCard
            productName={selectedProduct?.value || context.product_name}
            onClick={() => setIcpModalOpen(true)}
          />
          <DiscoverBuyerGroupCard
            onClick={() => sendMessage("Help me discover the buyer group for my target accounts")}
          />
          <InsightsCard
            onClick={() => sendMessage("Give me insights about my target market")}
          />
          <CurrentTrendCard
            onClick={() => sendMessage("What are the current trends relevant to my product?")}
          />
        </div>

        {/* Messages */}
        <div className={`messages-area ${messages.length === 0 ? "no-scroll" : ""}`}>
          {messages.map(msg => (
            <div key={msg.id} className={`message-row ${msg.role}`}>
              {msg.role === "bot" && (
                <div className="bot-avatar" title="Delphi AI">D</div>
              )}
              <div className="message-content">
                {msg.text && <div className="bubble">{msg.text}</div>}
                {msg.editApplied && (
                  <div className="edit-badge">
                    ✓ Updated: {msg.editApplied.field?.replace(/_/g, " ")} → {msg.editApplied.value}
                  </div>
                )}
                {msg.table !== undefined && <LeadsTable rows={msg.table} />}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message-row bot">
              <div className="bot-avatar">D</div>
              <div className="message-content">
                <div className="bubble"><TypingDots /></div>
              </div>
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

        {/* Input */}
        <div className="input-zone">
          <div className="input-card">
            <textarea
              ref={textareaRef}
              className="chat-input"
              placeholder={
                phase === "product"
                  ? "Describe your product or campaign goal..."
                  : phase === "targeting"
                  ? "Specify your target audience..."
                  : "Ask a follow-up question or refine your search..."
              }
              value={input}
              rows={1}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button
              className="send-btn"
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              title="Send (Enter)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
          <p className="input-hint">Enter to send · Shift+Enter for new line · Type "change [field]" to edit</p>
        </div>
      </main>
    </div>
  );
}