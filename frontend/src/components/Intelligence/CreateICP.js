// frontend/src/components/Intelligence/CreateICP.js
import { useState, useEffect } from "react";
import axios from "axios";
import "./create_icp.css";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN || "http://127.0.0.1:8000";

// ============================================================
// STEP 1: Product / Service Selector
// ============================================================

function ProductSelector({ userId, onConfirm }) {
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
                    `${API_BASE_URL}/mcp-icp/product-options/${userId}`
                );

                if (cancelled) return;

                const opts = res.data.options || [];
                setOptions(opts);
                setSelected(res.data.selected_product || opts[0] || null);

            } catch (err) {
                if (!cancelled) {
                    setError("Could not load your products/services. Please try again.");
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
            <div className="icp-loading-state">
                <div className="icp-spin" />
                <span>Loading your products & services...</span>
            </div>
        );
    }

    if (error) {
        return <div className="icp-error-banner">{error}</div>;
    }

    return (
        <div className="icp-select-panel">
            <h3 className="icp-select-title">
                Which product or service do you want to analyze?
            </h3>
            <p className="icp-select-subtitle">
                We detected these from your company profile. Pick one to
                find its Ideal Customer Profile — or change it anytime.
            </p>

            <div className="icp-option-grid">
                {options.map((opt) => (
                    <button
                        key={opt}
                        className={`icp-option-card${selected === opt ? " icp-option-active" : ""}`}
                        onClick={() => setSelected(opt)}
                    >
                        {opt}
                    </button>
                ))}
            </div>

            <button
                className="icp-btn-primary"
                disabled={!selected}
                onClick={() => onConfirm(selected)}
            >
                Find ICP for "{selected}"
            </button>
        </div>
    );
}

// ============================================================
// STEP 2: Loading while MCP pipeline runs
// ============================================================

function AnalyzingState({ product }) {
    return (
        <div className="icp-loading-state icp-loading-large">
            <div className="icp-spin" />
            <h3>Finding the ICP for "{product}"...</h3>
            <p>
                Analyzing competitor brands, matching historical
                campaigns, and scoring qualified leads.
            </p>
        </div>
    );
}

// ============================================================
// STEP 3: Result — enterprise-level ICP summary
// ============================================================

function ICPResult({ product, data, onChangeProduct }) {
    const insight = data?.icp_insight || {};
    const analysis = data?.product_analysis || {};

    return (
        <div className="icp-result-panel">

            <div className="icp-result-header">
                <div>
                    <span className="icp-result-eyebrow">Ideal Customer Profile</span>
                    <h2 className="icp-result-product">{product}</h2>
                </div>
                <button className="icp-btn-secondary" onClick={onChangeProduct}>
                    Change product
                </button>
            </div>

            <div className="icp-tag-row">
                {analysis.category && <span className="icp-tag">{analysis.category}</span>}
                {analysis.industry && <span className="icp-tag">{analysis.industry}</span>}
                {analysis.product_type && <span className="icp-tag">{analysis.product_type}</span>}
            </div>

            <div className="icp-card-grid">

                <div className="icp-insight-card">
                    <span className="icp-card-label">Companies</span>
                    <p className="icp-card-body">{insight.companies}</p>
                </div>

                <div className="icp-insight-card">
                    <span className="icp-card-label">Decision Makers</span>
                    <ul className="icp-card-list">
                        {(insight.decision_makers || []).map((dm) => (
                            <li key={dm}>{dm}</li>
                        ))}
                    </ul>
                </div>

                <div className="icp-insight-card">
                    <span className="icp-card-label">Regions</span>
                    <ul className="icp-card-list">
                        {(insight.regions || []).map((r) => (
                            <li key={r}>{r}</li>
                        ))}
                    </ul>
                </div>

                <div className="icp-insight-card">
                    <span className="icp-card-label">Buying Intent</span>
                    <p className="icp-card-body">{insight.buying_intent}</p>
                </div>

            </div>

            <div className="icp-why-panel">
                <span className="icp-card-label">Why?</span>
                <p className="icp-card-body">{insight.why}</p>
            </div>

            <div className="icp-stats-row">
                <div className="icp-stat">
                    <span className="icp-stat-value">{data?.total_matched_clients ?? 0}</span>
                    <span className="icp-stat-label">Similar Clients</span>
                </div>
                <div className="icp-stat">
                    <span className="icp-stat-value">{data?.total_campaigns ?? 0}</span>
                    <span className="icp-stat-label">Campaigns Analyzed</span>
                </div>
                <div className="icp-stat">
                    <span className="icp-stat-value">{data?.total_leads ?? 0}</span>
                    <span className="icp-stat-label">Qualified Leads</span>
                </div>
            </div>

        </div>
    );
}

// ============================================================
// MAIN — orchestrates the 3 steps
// ============================================================

export default function CreateICP({ userId, onClose }) {
    const [stage, setStage] = useState("select"); // select | analyzing | result | error
    const [product, setProduct] = useState(null);
    const [result, setResult] = useState(null);
    const [error, setError] = useState("");

    const runDiscovery = async (selectedProduct) => {
        setProduct(selectedProduct);
        setStage("analyzing");
        setError("");

        try {
            const res = await axios.post(`${API_BASE_URL}/mcp-icp/discover`, {
                user_id: userId,
                product: selectedProduct
            });

            setResult(res.data.data);
            setStage("result");

        } catch (err) {
            setError(
                err.response?.data?.detail ||
                "Something went wrong while finding your ICP. Please try again."
            );
            setStage("error");
        }
    };

    return (
        <div className="icp-container">
            {onClose && (
                <button className="icp-back-link" onClick={onClose}>
                    ← Back
                </button>
            )}

            {stage === "select" && (
                <ProductSelector userId={userId} onConfirm={runDiscovery} />
            )}

            {stage === "analyzing" && <AnalyzingState product={product} />}

            {stage === "result" && (
                <ICPResult
                    product={product}
                    data={result}
                    onChangeProduct={() => setStage("select")}
                />
            )}

            {stage === "error" && (
                <div className="icp-error-banner">
                    {error}
                    <button className="icp-retry-btn" onClick={() => setStage("select")}>
                        Try again
                    </button>
                </div>
            )}
        </div>
    );
}