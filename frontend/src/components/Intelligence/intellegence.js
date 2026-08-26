// Intelligence.js — Enterprise Redesign (v2: unified product context flow, chat via ChatSection)
import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import "./intellegence.css";
import CreateICP from "./CreateICP";
import BuyerGroup from "./BuyerGroup";
import ChatSection from "./ChatSection";

const API_BASE = "http://127.0.0.1:8000";

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
export function LeadsTable({ rows }) {
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
  Pin: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
      <circle cx="12" cy="9" r="2.3" stroke="currentColor" strokeWidth="1.6"/>
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

// ── Insights sidebar panel ───────────────────────────────────────────────────
function InsightItem({ icon, label, active, onClick }) {
  return (
    <button className={`insight-item ${active ? "active" : ""}`} onClick={onClick}>
      <span className="insight-item-icon">{icon}</span>
      <span className="insight-item-label">{label}</span>
      {active && <span className="insight-item-dot" />}
    </button>
  );
}

function InsightsPanel({ activeInsight, onSelect }) {
  return (
    <div className="insights-panel">
      <div className="insights-panel-title">Insights</div>
      {/* Parent: Create ICP with nested actions */}
      <InsightItem
        icon={<Icon.Target />}
        label="Create ICP"
        active={["icp", "buyer_group", "geo"].includes(activeInsight)}
        onClick={() => onSelect("icp")}
      />
      <div style={{ paddingLeft: 18, marginTop: 6, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <button className={`insight-subitem ${activeInsight === "buyer_group" ? "active" : ""}`} onClick={() => onSelect("buyer_group")}> 
          <span className="insight-item-icon"><Icon.Users /></span>
          <span className="insight-item-label">Discover Buyer Group</span>
          {activeInsight === "buyer_group" && <span className="insight-item-dot" />}
        </button>
        <button className={`insight-subitem ${activeInsight === "geo" ? "active" : ""}`} onClick={() => onSelect("geo")}>
          <span className="insight-item-icon"><Icon.Bulb /></span>
          <span className="insight-item-label">Uncover Persona</span>
          {activeInsight === "geo" && <span className="insight-item-dot" />}
        </button>
      </div>
      <InsightItem
        icon={<Icon.Pin />}
        label="Geo Based Personalization"
        active={activeInsight === "geo"}
        onClick={() => onSelect("geo")}
      />
    </div>
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
      title="Insight"
      description=""
      onClick={onClick}
    />
  );
}

function InsightsCard({ onClick }) {
  return (
    <ActionCard
      icon={<Icon.Bulb />}
      title="Insights"
      description=""
      onClick={onClick}
    />
  );
}

function CurrentTrendCard({ onClick }) {
  return (
    <ActionCard
      icon={<Icon.Trend />}
      title="Insight"
      description=""
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
          {onClose && <button className="modal-close" onClick={onClose}>✕</button>}
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

// ── Product/Service icon by type ────────────────────────────────────────────
function ProductTypeIcon({ type }) {
  const t = (type || "").toLowerCase();
  if (t === "brand") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
        <path d="M12 2 3 7v6c0 5 3.8 8.7 9 9 5.2-.3 9-4 9-9V7l-9-5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      </svg>
    );
  }
  if (t === "service") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
        <path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="12" cy="12" r="3.2" stroke="currentColor" strokeWidth="1.8" />
      </svg>
    );
  }
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <rect x="3.5" y="3.5" width="17" height="17" rx="4" stroke="currentColor" strokeWidth="1.8" />
      <path d="M8 12h8M12 8v8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

// ── Shared Product/Service Selector (search + grouped grid + add new) ──────
function ProductServiceSelector({
  items,
  loading,
  selectedValue,
  selectedType,
  onSelect,
  selecting,
  onAddNew,
  adding,
}) {
  const [query, setQuery]         = useState("");
  const [showAddForm, setShowAdd] = useState(false);
  const [newValue, setNewValue]   = useState("");
  const [newType, setNewType]     = useState("product");

  const filtered = items.filter(i =>
    i.value.toLowerCase().includes(query.trim().toLowerCase())
  );

  const groups = filtered.reduce((acc, item) => {
    const key = (item.type || "product").toLowerCase();
    (acc[key] = acc[key] || []).push(item);
    return acc;
  }, {});

  const GROUP_ORDER = ["product", "brand", "service"];
  const GROUP_LABELS = { product: "Products", brand: "Brands", service: "Services" };
  const orderedGroupKeys = [
    ...GROUP_ORDER.filter(k => groups[k]),
    ...Object.keys(groups).filter(k => !GROUP_ORDER.includes(k)),
  ];

  const submitNew = async () => {
    const value = newValue.trim();
    if (!value || adding) return;
    await onAddNew({ value, type: newType });
    setNewValue("");
    setShowAdd(false);
  };

  return (
    <div className="pp-selector">
      <div className="pp-search-box">
        <svg className="pp-search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="M21 21l-4.3-4.3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          className="pp-search-input"
          placeholder="Search products, brands, services..."
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
      </div>

      {loading && <p className="history-empty">Loading products...</p>}

      {!loading && orderedGroupKeys.map(key => (
        <div className="pp-group" key={key}>
          <div className="pp-group-label">
            {GROUP_LABELS[key] || key}
            <span className="pp-group-count">{groups[key].length}</span>
          </div>
          <div className="pp-card-grid">
            {groups[key].map(item => {
              const isActive = item.value === selectedValue && item.type === selectedType;
              return (
                <button
                  key={`${item.type}-${item.value}`}
                  className={`pp-select-card ${isActive ? "pp-select-card-active" : ""}`}
                  disabled={selecting}
                  onClick={() => onSelect(item)}
                >
                  <span className="pp-select-card-icon"><ProductTypeIcon type={item.type} /></span>
                  <span className="pp-select-card-value">{item.value}</span>
                  {isActive && (
                    <span className="pp-select-card-check">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                        <path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ))}

      {!loading && filtered.length === 0 && (
        <p className="history-empty">
          {query ? "No matches for that search." : "No products/services found in your company profile."}
        </p>
      )}

      {/* ── Add new product/service ── */}
      <div className="pp-add-section">
        {!showAddForm ? (
          <button className="pp-add-trigger" onClick={() => setShowAdd(true)}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
            Add a new product or service
          </button>
        ) : (
          <div className="pp-add-form">
            <div className="pp-add-type-toggle">
              {["product", "brand", "service"].map(t => (
                <button
                  key={t}
                  type="button"
                  className={`pp-add-type-btn ${newType === t ? "pp-add-type-btn-active" : ""}`}
                  onClick={() => setNewType(t)}
                >
                  {GROUP_LABELS[t]}
                </button>
              ))}
            </div>
            <div className="pp-add-input-row">
              <input
                type="text"
                autoFocus
                className="pp-add-input"
                placeholder="e.g. MacBook Pro"
                value={newValue}
                onChange={e => setNewValue(e.target.value)}
                onKeyDown={e => e.key === "Enter" && submitNew()}
              />
              <button
                className="pp-add-confirm"
                disabled={!newValue.trim() || adding}
                onClick={submitNew}
              >
                {adding ? "Adding..." : "Add"}
              </button>
              <button
                className="pp-add-cancel"
                onClick={() => { setShowAdd(false); setNewValue(""); }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── First-time Product Picker Modal (forced, no close button) ──────────────
function ProductPickerModal({ userId, onSelected }) {
  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const [adding, setAdding]   = useState(false);

  const loadItems = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/intellegence/product-options/${userId}`);
      const data = await res.json();
      setItems(data.items || []);
    } catch (err) {
      console.error("Failed to load product options:", err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { loadItems(); }, [loadItems]);

  const pick = async (item) => {
    setSaving(true);
    try {
      await fetch(`${API_BASE}/intellegence/select-product`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, product: item.value, type: item.type }),
      });
      onSelected(item);
    } catch (err) {
      console.error("Failed to select product:", err);
    } finally {
      setSaving(false);
    }
  };

  const addNew = async ({ value, type }) => {
    setAdding(true);
    try {
      const res = await fetch(`${API_BASE}/intellegence/add-product`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, value, type }),
      });
      const data = await res.json();
      if (data?.items) setItems(data.items);
      else await loadItems();
    } catch (err) {
      console.error("Failed to add product:", err);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-panel wide" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Which product or service do you want insights on?</span>
        </div>
        <div className="modal-body">
          <p className="modal-hint">
            We detected these from your company profile. Pick one to make it the active context for
            ICP, Buyer Group, and every future search — you can change it anytime from the sidebar.
            Don't see what you're looking for? Add it below.
          </p>
          <ProductServiceSelector
            items={items}
            loading={loading}
            selectedValue={null}
            selectedType={null}
            onSelect={pick}
            selecting={saving}
            onAddNew={addNew}
            adding={adding}
          />
        </div>
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
  const [context,       setContext]       = useState({});
  const [phase,         setPhase]         = useState("product");
  const [sessions,      setSessions]      = useState([]);
  const [sidebarOpen,   setSidebarOpen]   = useState(true);
  const [darkMode,      setDarkMode]      = useState(() => {
    return localStorage.getItem("delphi-theme") === "dark";
  });

  // Section modal state: which sidebar card is expanded ("product" | null)
  const [activeSection,   setActiveSection]   = useState(null);

  // Which Insight is currently active (drives the sidebar dot indicator)
  const [activeInsight,   setActiveInsight]   = useState(null);

  // First-time-user forced product picker
  const [showProductPicker, setShowProductPicker] = useState(false);

  // ── Product/Service selection (fetched from delphi_company_profiles) ──────
  const [productItems,     setProductItems]     = useState([]);
  const [selectedProduct,  setSelectedProduct]  = useState(null);
  const [productsLoading,  setProductsLoading]  = useState(false);

  // ── Chat section ref (owns messages/input/session logic against context-engine backend)
  const chatRef = useRef(null);

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

  // ── Check selected product on load — forces the picker modal for
  //    first-time users, otherwise silently loads the existing selection ──
  useEffect(() => {
    if (!USER_ID) return;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/intellegence/selected-product/${USER_ID}`);
        const data = await res.json();
        if (data.is_first_time) {
          setShowProductPicker(true);
        } else {
          setSelectedProduct({ value: data.selected_product, type: data.selected_type });
        }
      } catch (err) {
        console.error("Failed to check selected product:", err);
      }
    })();
  }, [USER_ID]);

  const handleProductPicked = (item) => {
    setSelectedProduct(item);
    setShowProductPicker(false);
  };

  // ── Start Create ICP as an inline chat message ─────────────────────────────
  const startCreateICP = useCallback(() => {
    setActiveInsight("icp");
    chatRef.current?.pushMessage({ role: "user", text: "Create ICP" });
    chatRef.current?.pushMessage({ role: "bot", icpFlow: true });
  }, []);

  const startDiscoverBuyerGroup = useCallback((brandIds) => {
    setActiveInsight("buyer_group");
    chatRef.current?.pushMessage({ role: "user", text: "Discover Buyer Group" });
    chatRef.current?.pushMessage({ role: "bot", buyerGroupFlow: true, brandIds: brandIds || null });
  }, []);

  const handleInsightSelect = useCallback((key) => {
    if (key === "icp") {
      startCreateICP();
    } else if (key === "buyer_group") {
      startDiscoverBuyerGroup();
    } else if (key === "geo") {
      setActiveInsight("geo");
      chatRef.current?.sendMessage("Give me geo-based personalization insights for my product");
    }
  }, [startCreateICP, startDiscoverBuyerGroup]);

  // ── Fetch product/service list for the sidebar "Product / Services" modal ─
  const fetchProducts = useCallback(async () => {
    if (!USER_ID) return;
    setProductsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/intellegence/product-options/${USER_ID}`);
      const data = await res.json();
      setProductItems(data.items || []);
      if (data.selected) setSelectedProduct(data.selected);
    } catch (err) {
      console.error("Failed to fetch products:", err);
    } finally {
      setProductsLoading(false);
    }
  }, [USER_ID]);

  useEffect(() => {
    if (USER_ID && activeSection === "product") {
      fetchProducts();
    }
  }, [USER_ID, activeSection, fetchProducts]);

  // ── Select a product/service (sets the active context) ────────────────────
  const selectProduct = async (item) => {
    try {
      await fetch(`${API_BASE}/intellegence/select-product`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: USER_ID,
          product: item.value,
          type: item.type,
        }),
      });
      setSelectedProduct({ ...item, selected: true });
      setProductItems(prev =>
        prev.map(i => ({
          ...i,
          selected: i.value === item.value && i.type === item.type,
        }))
      );
    } catch (err) {
      console.error("Failed to select product:", err);
    } finally {
      setActiveSection(null);
    }
  };

  // ── Add a new product/service from the sidebar modal ──────────────────────
  const [addingProduct, setAddingProduct] = useState(false);
  const addProduct = async ({ value, type }) => {
    setAddingProduct(true);
    try {
      const res = await fetch(`${API_BASE}/intellegence/add-product`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID, value, type }),
      });
      const data = await res.json();
      if (data?.items) setProductItems(data.items);
      else await fetchProducts();
    } catch (err) {
      console.error("Failed to add product:", err);
    } finally {
      setAddingProduct(false);
    }
  };

  const filledProductFields   = PRODUCT_FIELD_ORDER.filter(f => context[f]);
  const filledTargetingFields = TARGETING_FIELD_ORDER.filter(f => context[f]);
  const totalFilled           = filledProductFields.length + filledTargetingFields.length;
  const hasAnyContext         = totalFilled > 0;
  const overallPct = Math.round((totalFilled / ALL_FIELDS.length) * 100);

  return (
    <div className={`app-shell ${sidebarOpen ? "sidebar-open" : ""}`}>

      {/* ══ FORCED PRODUCT PICKER (first-time users) ══════════════ */}
      {showProductPicker && (
        <ProductPickerModal userId={USER_ID} onSelected={handleProductPicked} />
      )}

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
        <button className="new-chat-btn" onClick={() => chatRef.current?.startNewChat()}>
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
          <InsightsPanel
            activeInsight={activeInsight}
            onSelect={handleInsightSelect}
          />

          {/* Chat history (persisted sessions from context-engine backend) */}
          {sessions.length > 0 && (
            <div className="sidebar-panel">
              <div className="sidebar-panel-title" style={{ padding: "0 8px", marginTop: 10 }}>
                Recent chats
              </div>
              <div className="session-list">
                {sessions.map(session => (
                  <button
                    key={session.id}
                    className="session-item"
                    onClick={() => chatRef.current?.selectSession(session.id)}
                    title={session.title}
                  >
                    {session.title}
                  </button>
                ))}
              </div>
            </div>
          )}
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
        <Modal title="Product / Services" onClose={() => setActiveSection(null)} wide>
          <p className="modal-hint">
            These are the products, services, and brands detected for your account.
            Select one to make it the active context for searches, ICP, and Buyer Group.
            Don't see what you're looking for? Add it below.
          </p>
          <label className="modal-label">Currently Selected</label>
          <div className="modal-current-value">
            {selectedProduct?.value || "No product selected yet"}
          </div>
          <label className="modal-label">Choose one</label>
          <ProductServiceSelector
            items={productItems}
            loading={productsLoading}
            selectedValue={selectedProduct?.value}
            selectedType={selectedProduct?.type}
            onSelect={selectProduct}
            selecting={false}
            onAddNew={addProduct}
            adding={addingProduct}
          />
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
            onClick={startCreateICP}
          />
          <DiscoverBuyerGroupCard
            onClick={startDiscoverBuyerGroup}
          />
          <InsightsCard
            onClick={() => chatRef.current?.sendMessage("Give me insights about my target market")}
          />
          <CurrentTrendCard
            onClick={() => chatRef.current?.sendMessage("What are the current trends relevant to my product?")}
          />
        </div>

        {/* Chat: messages + input, backed by the context-engine backend */}
        <ChatSection
          ref={chatRef}
          userId={USER_ID}
          onContextUpdate={setContext}
          onPhaseUpdate={setPhase}
          onSessionsChange={setSessions}
          onOpenProductPicker={() => setActiveSection("product")}
        />
      </main>
    </div>
  );
}