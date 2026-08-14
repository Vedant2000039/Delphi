// frontend/src/components/Intelligence/BuyerGroup.js
import { useState, useEffect } from "react";
import axios from "axios";
import "./buyer_group.css";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN || "http://127.0.0.1:8000";

// ============================================================
// STEP 1: Brand Selector
// ============================================================

function BrandSelector({ userId, onConfirm }) {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [options, setOptions] = useState([]);
    const [selected, setSelected] = useState(null);

    useEffect(() => {
        let cancelled = false;

        async function loadOptions() {
            setLoading(true);
            setError("");

            try {
                const res = await axios.get(
                    `${API_BASE_URL}/buyer-group/brand-options/${userId}`
                );

                if (cancelled) return;

                const opts = res.data.options || [];
                setOptions(opts);
                setSelected(opts[0] || null);

            } catch (err) {
                if (!cancelled) {
                    setError("Could not load your brands. Please try again.");
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        loadOptions();
        return () => { cancelled = true; };
    }, [userId]);

    if (loading) {
        return (
            <div className="bg-loading-state">
                <div className="bg-spin" />
                <span>Loading your brands...</span>
            </div>
        );
    }

    if (error) {
        return <div className="bg-error-banner">{error}</div>;
    }

    return (
        <div className="bg-select-panel">
            <h3 className="bg-select-title">
                Which brand do you want to build a buyer group for?
            </h3>
            <p className="bg-select-subtitle">
                We'll size the roles, seniority, and firmographics that
                typically show up together on deals for this brand.
            </p>

            <div className="bg-option-grid">
                {options.map((opt) => (
                    <button
                        key={opt.brand_id}
                        className={`bg-option-card${selected?.brand_id === opt.brand_id ? " bg-option-active" : ""}`}
                        onClick={() => setSelected(opt)}
                    >
                        {opt.brand_name}
                    </button>
                ))}
            </div>

            <button
                className="bg-btn-primary"
                disabled={!selected}
                onClick={() => onConfirm(selected)}
            >
                Build Buyer Group{selected ? ` for "${selected.brand_name}"` : ""}
            </button>
        </div>
    );
}

// ============================================================
// STEP 2: Loading while MCP pipeline runs
// ============================================================

function AnalyzingState({ brandName }) {
    return (
        <div className="bg-loading-state bg-loading-large">
            <div className="bg-spin" />
            <h3>Building the buyer group for "{brandName}"...</h3>
            <p>
                Scoring qualified leads by seniority, function, and
                company size to map out who's really in the room.
            </p>
        </div>
    );
}

// ============================================================
// STEP 3: Result — buyer group breakdown
// ============================================================

function BuyerGroupResult({ brandName, data, onChangeBrand }) {
    const insight = data?.buyer_group_insight || {};
    const roles = data?.roles || [];
    const summary = data?.summary || {};

    return (
        <div className="bg-result-panel">

            <div className="bg-result-header">
                <div>
                    <span className="bg-result-eyebrow">Buyer Group</span>
                    <h2 className="bg-result-brand">{brandName}</h2>
                </div>
                <button className="bg-btn-secondary" onClick={onChangeBrand}>
                    Change brand
                </button>
            </div>

            <div className="bg-tag-row">
                {(summary.job_levels || []).map((jl) => (
                    <span className="bg-tag" key={jl}>{jl}</span>
                ))}
            </div>

            {/* Committee roles */}
            <div className="bg-card-grid">

                <div className="bg-insight-card bg-insight-highlight">
                    <span className="bg-card-label">Economic Buyer</span>
                    <p className="bg-card-body">{insight.economic_buyer}</p>
                </div>

                <div className="bg-insight-card">
                    <span className="bg-card-label">Champion</span>
                    <p className="bg-card-body">{insight.champion}</p>
                </div>

                <div className="bg-insight-card">
                    <span className="bg-card-label">Influencers</span>
                    <ul className="bg-card-list">
                        {(insight.influencers || []).map((r) => (
                            <li key={r}>{r}</li>
                        ))}
                    </ul>
                </div>

                <div className="bg-insight-card">
                    <span className="bg-card-label">Group Size</span>
                    <p className="bg-card-body">{insight.group_size}</p>
                </div>

            </div>

            <div className="bg-why-panel">
                <span className="bg-card-label">Why?</span>
                <p className="bg-card-body">{insight.why}</p>
            </div>

            {/* Full role breakdown table */}
            <div className="bg-table-wrap">
                <span className="bg-card-label">Role Breakdown</span>
                <table className="bg-role-table">
                    <thead>
                        <tr>
                            <th>Job Level</th>
                            <th>Job Function</th>
                            <th>Employee Size</th>
                            <th>Revenue Size</th>
                            <th>Share</th>
                        </tr>
                    </thead>
                    <tbody>
                        {roles.map((r, i) => (
                            <tr key={i}>
                                <td>{r.job_level}</td>
                                <td>{r.job_function}</td>
                                <td>{r.employee_size}</td>
                                <td>{r.revenue_size}</td>
                                <td>
                                    <div className="bg-share-cell">
                                        <div className="bg-share-bar">
                                            <div
                                                className="bg-share-fill"
                                                style={{ width: `${Math.min(r.percentage, 100)}%` }}
                                            />
                                        </div>
                                        <span>{r.percentage}%</span>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="bg-stats-row">
                <div className="bg-stat">
                    <span className="bg-stat-value">{roles.length}</span>
                    <span className="bg-stat-label">Distinct Roles</span>
                </div>
                <div className="bg-stat">
                    <span className="bg-stat-value">{data?.total_qualified_leads ?? 0}</span>
                    <span className="bg-stat-label">Qualified Leads</span>
                </div>
            </div>

        </div>
    );
}

// ============================================================
// MAIN — orchestrates the 3 steps
// ============================================================

export default function BuyerGroup({ userId, onClose }) {
    const [stage, setStage] = useState("select"); // select | analyzing | result | error
    const [brand, setBrand] = useState(null);
    const [result, setResult] = useState(null);
    const [error, setError] = useState("");

    const runDiscovery = async (selectedBrand) => {
        setBrand(selectedBrand);
        setStage("analyzing");
        setError("");

        try {
            const res = await axios.post(`${API_BASE_URL}/buyer-group/discover`, {
                brand_id: selectedBrand.brand_id,
                brand_name: selectedBrand.brand_name
            });

            setResult(res.data.data);
            setStage("result");

        } catch (err) {
            setError(
                err.response?.data?.detail ||
                "Something went wrong while building the buyer group. Please try again."
            );
            setStage("error");
        }
    };

    return (
        <div className="bg-container">
            {onClose && (
                <button className="bg-back-link" onClick={onClose}>
                    ← Back
                </button>
            )}

            {stage === "select" && (
                <BrandSelector userId={userId} onConfirm={runDiscovery} />
            )}

            {stage === "analyzing" && <AnalyzingState brandName={brand?.brand_name} />}

            {stage === "result" && (
                <BuyerGroupResult
                    brandName={brand?.brand_name}
                    data={result}
                    onChangeBrand={() => setStage("select")}
                />
            )}

            {stage === "error" && (
                <div className="bg-error-banner">
                    {error}
                    <button className="bg-retry-btn" onClick={() => setStage("select")}>
                        Try again
                    </button>
                </div>
            )}
        </div>
    );
}