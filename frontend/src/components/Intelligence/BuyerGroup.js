// frontend/src/components/Intelligence/BuyerGroup.js
import { useState, useEffect } from "react";
import axios from "axios";
import "./buyer_group.css";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN || "http://127.0.0.1:8000";

// ============================================================
// Loading while MCP pipeline runs
// ============================================================

function AnalyzingState({ product }) {
    return (
        <div className="bg-loading-state bg-loading-large">
            <div className="bg-spin" />
            <h3>
                Building the buyer group{product ? ` for "${product}"` : ""}...
            </h3>
            <p>
                Scoring qualified leads by seniority, function, and
                company size to map out who's really in the room.
            </p>
        </div>
    );
}

// ============================================================
// Result — buyer group breakdown
// ============================================================

function BuyerGroupResult({ product, data }) {
    const insight = data?.buyer_group_insight || {};
    const roles = data?.roles || [];
    const summary = data?.summary || {};

    return (
        <div className="bg-result-panel">

            <div className="bg-result-header">
                <div>
                    <span className="bg-result-eyebrow">Buyer Group</span>
                    <h2 className="bg-result-brand">{product}</h2>
                </div>
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
// MAIN — orchestrates the flow.
//
// No brand picker: the buyer group is always built for the
// user's already-selected product, using the same brand match
// ICP discovery resolved. To analyze a different product, the
// user changes it via the sidebar product/service switcher card,
// same as CreateICP.
// ============================================================

export default function BuyerGroup({ userId, onClose }) {
    const [stage, setStage] = useState("analyzing"); // analyzing | result | error
    const [result, setResult] = useState(null);
    const [error, setError] = useState("");

    const runDiscovery = async () => {
        setStage("analyzing");
        setError("");

        try {
            const res = await axios.post(`${API_BASE_URL}/buyer-group/discover`, {
                user_id: userId
            });

            if (res.data?.data?.error === "no_product_selected") {
                setError(
                    "No product or service has been selected yet. Choose one from the sidebar first."
                );
                setStage("error");
                return;
            }

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

    useEffect(() => {
        runDiscovery();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [userId]);

    return (
        <div className="bg-container">
            {onClose && (
                <button className="bg-back-link" onClick={onClose}>
                    ← Back
                </button>
            )}

            {stage === "analyzing" && <AnalyzingState product={result?.product} />}

            {stage === "result" && (
                <BuyerGroupResult product={result?.product} data={result} />
            )}

            {stage === "error" && (
                <div className="bg-error-banner">
                    {error}
                    <button className="bg-retry-btn" onClick={runDiscovery}>
                        Try again
                    </button>
                </div>
            )}
        </div>
    );
}