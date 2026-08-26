// frontend/src/components/Intelligence/CreateICP.js

import { useState, useEffect } from "react";
import axios from "axios";
import "./create_icp.css";

const API_BASE_URL =
    process.env.REACT_APP_API_DOMAIN || "http://127.0.0.1:8000";


// ============================================================
// STEP 1: PRODUCT / SERVICE SELECTOR
// ============================================================

function ProductSelector({
    userId,
    initialOptions,
    initialSelected,
    onConfirm
}) {

    const [loading, setLoading] = useState(!initialOptions);
    const [error, setError] = useState("");
    const [options, setOptions] = useState(initialOptions || []);
    const [selected, setSelected] = useState(initialSelected || null);


    useEffect(() => {

        if (initialOptions) {
            return;
        }

        let cancelled = false;


        async function loadOptions() {

            setLoading(true);
            setError("");

            try {

                const res = await axios.get(
                    `${API_BASE_URL}/mcp-icp/product-options/${userId}`
                );


                if (cancelled) {
                    return;
                }


                const opts =
                    Array.isArray(res.data?.options)
                        ? res.data.options
                        : [];


                setOptions(opts);


                setSelected(
                    res.data?.selected_product ||
                    opts[0] ||
                    null
                );

            } catch (err) {

                if (!cancelled) {

                    setError(
                        err.response?.data?.detail ||
                        "Could not load your products/services. Please try again."
                    );
                }

            } finally {

                if (!cancelled) {
                    setLoading(false);
                }

            }
        }


        loadOptions();


        return () => {
            cancelled = true;
        };

    }, [userId, initialOptions]);


    if (loading) {

        return (
            <div className="icp-loading-state">

                <div className="icp-spin" />

                <span>
                    Loading your products & services...
                </span>

            </div>
        );
    }


    if (error) {

        return (
            <div className="icp-error-banner">
                {error}
            </div>
        );
    }


    return (

        <div className="icp-select-panel">

            <h3 className="icp-select-title">
                Which product or service do you want to analyze?
            </h3>


            <p className="icp-select-subtitle">

                We detected these from your company profile.
                Pick one to find its Ideal Customer Profile —
                or change it anytime.

            </p>


            <div className="icp-option-grid">

                {options.map((opt) => (

                    <button
                        key={opt}
                        type="button"
                        className={
                            `icp-option-card${
                                selected === opt
                                    ? " icp-option-active"
                                    : ""
                            }`
                        }
                        onClick={() => setSelected(opt)}
                    >
                        {opt}
                    </button>

                ))}

            </div>


            <button
                type="button"
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
// STEP 2: ICP ANALYZING STATE
// ============================================================

function AnalyzingState({ product }) {

    return (

        <div className="icp-loading-state icp-loading-large">

            <div className="icp-spin" />

            <h3>
                Finding the ICP
                {product ? ` for "${product}"` : ""}...
            </h3>

            <p>
                Analyzing competitor brands, matching historical
                campaigns, and scoring qualified leads.
            </p>

        </div>

    );
}


// ============================================================
// COMPANIES INSIGHT PARSER
//
// Backend currently returns something like:
//
// **Companies**
//
// Ideal companies are small businesses...
//
// - **Industry:** Consumer Electronics
// - **Company size:** 1-19
// - **Revenue size:** $,
//
// A smaller segment includes...
//
// This function converts that into:
//
// description
// industry
// companySize
// revenueSize
// additionalContext
//
// ============================================================

function parseCompaniesInsight(rawCompanies) {

    if (!rawCompanies) {

        return {
            description: "",
            industry: "",
            companySize: "",
            revenueSize: "",
            additionalContext: ""
        };

    }


    let text = String(rawCompanies)
        .replace(/\r\n/g, "\n")
        .trim();


    // --------------------------------------------------------
    // Remove "**Companies**" heading
    // --------------------------------------------------------

    text = text
        .replace(
            /^\s*#{0,6}\s*\*{0,2}Companies\*{0,2}\s*/i,
            ""
        )
        .trim();


    // --------------------------------------------------------
    // Helper to clean Markdown
    // --------------------------------------------------------

    function cleanValue(value) {

        if (!value) {
            return "";
        }

        return String(value)
            .replace(/\*\*/g, "")
            .replace(/\*/g, "")
            .replace(/^[-•]\s*/, "")
            .trim();

    }


    // --------------------------------------------------------
    // INDUSTRY
    // --------------------------------------------------------

    let industry = "";

    const industryMatch = text.match(
        /(?:^|\n)\s*(?:[-•*]\s*)?\*{0,2}Industry\*{0,2}\s*:\s*(.+?)(?=\n|$)/i
    );


    if (industryMatch) {

        industry = cleanValue(
            industryMatch[1]
        );


        text = text.replace(
            industryMatch[0],
            ""
        );
    }


    // --------------------------------------------------------
    // COMPANY SIZE
    // --------------------------------------------------------

    let companySize = "";

    const companySizeMatch = text.match(
        /(?:^|\n)\s*(?:[-•*]\s*)?\*{0,2}(?:Company\s*size|Employee\s*size)\*{0,2}\s*:\s*(.+?)(?=\n|$)/i
    );


    if (companySizeMatch) {

        companySize = cleanValue(
            companySizeMatch[1]
        );


        text = text.replace(
            companySizeMatch[0],
            ""
        );
    }


    // --------------------------------------------------------
    // REVENUE SIZE
    // --------------------------------------------------------

    let revenueSize = "";

    const revenueMatch = text.match(
        /(?:^|\n)\s*(?:[-•*]\s*)?\*{0,2}Revenue\s*size\*{0,2}\s*:\s*(.+?)(?=\n|$)/i
    );


    if (revenueMatch) {

        revenueSize = cleanValue(
            revenueMatch[1]
        );


        text = text.replace(
            revenueMatch[0],
            ""
        );
    }


    // --------------------------------------------------------
    // Remove malformed revenue values
    //
    // "$,"
    // "$"
    // ","
    // "N/A"
    // "Not Available"
    // --------------------------------------------------------

    if (
        !revenueSize ||
        revenueSize === "$" ||
        revenueSize === "$," ||
        revenueSize === "," ||
        /^n\/?a$/i.test(revenueSize) ||
        /^not\s+available$/i.test(revenueSize)
    ) {

        revenueSize = "";

    }


    // --------------------------------------------------------
    // Clean remaining text
    // --------------------------------------------------------

    text = text
        .replace(/^\s*[-•]\s*/gm, "")
        .replace(/\n{2,}/g, "\n")
        .trim();


    // --------------------------------------------------------
    // Find additional context
    //
    // Example:
    //
    // A smaller segment includes mid-sized firms...
    //
    // Though some mid-sized firms...
    // --------------------------------------------------------

    let description = text;
    let additionalContext = "";


    const contextRegex =
        /\b(?:A smaller segment|A smaller group|A smaller portion|Some mid[- ]sized|Though some|However,|Additionally,|A smaller number)\b[\s\S]*/i;


    const contextMatch =
        text.match(contextRegex);


    if (contextMatch) {

        additionalContext =
            contextMatch[0]
                .replace(/\s+/g, " ")
                .trim();


        const contextIndex =
            contextMatch.index;


        description =
            text
                .slice(0, contextIndex)
                .trim();

    }


    // --------------------------------------------------------
    // FALLBACK: Extract company size from description
    // --------------------------------------------------------

    if (!companySize) {

        const employeeMatch =
            description.match(
                /\b(\d{1,4}\s*[-–]\s*\d{1,4})\s*(?:employees|employee|staff)\b/i
            );


        if (employeeMatch) {

            companySize =
                employeeMatch[1]
                    .replace(/\s+/g, "");

        }

    }


    // --------------------------------------------------------
    // FALLBACK: Extract revenue from description
    // --------------------------------------------------------

    if (!revenueSize) {

        const revenueFromDescription =
            description.match(
                /\b(?:under|below|up to|less than)\s*\$?\s*([0-9,.]+)\s*(M|B|K)?\b/i
            );


        if (revenueFromDescription) {

            revenueSize =
                `Under $${revenueFromDescription[1]}${
                    revenueFromDescription[2] || ""
                }`;

        }

    }


    // --------------------------------------------------------
    // Normalize spaces
    // --------------------------------------------------------

    description =
        description
            .replace(/\s+/g, " ")
            .trim();


    additionalContext =
        additionalContext
            .replace(/\s+/g, " ")
            .trim();


    industry =
        industry
            .replace(/\s+/g, " ")
            .trim();


    companySize =
        companySize
            .replace(/\s+/g, " ")
            .trim();


    revenueSize =
        revenueSize
            .replace(/\s+/g, " ")
            .trim();


    return {
        description,
        industry,
        companySize,
        revenueSize,
        additionalContext
    };
}


// ============================================================
// STEP 3: ICP RESULT
// ============================================================

function ICPResult({
    product,
    data,
    onChangeProduct,
    onDiscoverBuyerGroup,
    buyerGroupLoading
}) {

    const insight =
        data?.icp_insight || {};


    const analysis =
        data?.product_analysis || {};


    // --------------------------------------------------------
    // Parse Companies
    // --------------------------------------------------------

    const companies =
        parseCompaniesInsight(
            insight.companies
        );


    // --------------------------------------------------------
    // Safe arrays
    // --------------------------------------------------------

    const decisionMakers =
        Array.isArray(insight.decision_makers)
            ? insight.decision_makers
            : [];


    const regions =
        Array.isArray(insight.regions)
            ? insight.regions
            : [];


    // --------------------------------------------------------
    // UI
    // --------------------------------------------------------

    return (

        <div className="icp-result-panel">


            {/* ==================================================
                HEADER
            ================================================== */}

            <div className="icp-result-header">

                <div>

                    <span className="icp-result-eyebrow">
                        Ideal Customer Profile
                    </span>


                    <h2 className="icp-result-product">
                        {product}
                    </h2>

                </div>


                {/* <button
                    type="button"
                    className="icp-btn-secondary"
                    onClick={onChangeProduct}
                >
                    Change product
                </button> */}

            </div>


            {/* ==================================================
                TAGS
            ================================================== */}

            <div className="icp-tag-row">

                {analysis.category && (

                    <span className="icp-tag">
                        {analysis.category}
                    </span>

                )}


                {analysis.industry && (

                    <span className="icp-tag">
                        {analysis.industry}
                    </span>

                )}


                {analysis.product_type && (

                    <span className="icp-tag">
                        {analysis.product_type}
                    </span>

                )}

            </div>


            {/* ==================================================
                ICP CARDS
            ================================================== */}

            <div className="icp-card-grid">


                {/* =================================================
                    COMPANIES
                ================================================= */}

                <div className="icp-insight-card">

                    <span className="icp-card-label">
                        Companies
                    </span>


                    {/* Description */}

                    {companies.description && (

                        <p className="icp-card-body">
                            {companies.description}
                        </p>

                    )}


                    {/* Structured information */}

                    <ul className="icp-card-list">

                        {companies.industry && (

                            <li>
                                <strong>
                                    Industry:
                                </strong>{" "}
                                {companies.industry}
                            </li>

                        )}


                        {companies.companySize && (

                            <li>
                                <strong>
                                    Company size:
                                </strong>{" "}
                                {companies.companySize}
                            </li>

                        )}


                        {companies.revenueSize && (

                            <li>
                                <strong>
                                    Revenue size:
                                </strong>{" "}
                                {companies.revenueSize}
                            </li>

                        )}

                    </ul>


                    {/* Additional context */}

                    {companies.additionalContext && (

                        <p
                            className="icp-card-body"
                            style={{
                                marginTop: "12px"
                            }}
                        >
                            {companies.additionalContext}
                        </p>

                    )}

                </div>


                {/* =================================================
                    DECISION MAKERS
                ================================================= */}

                <div className="icp-insight-card">

                    <span className="icp-card-label">
                        Decision Makers
                    </span>


                    {decisionMakers.length > 0 ? (

                        <ul className="icp-card-list">

                            {decisionMakers.map((dm, index) => (

                                <li key={`${dm}-${index}`}>
                                    {dm}
                                </li>

                            ))}

                        </ul>

                    ) : (

                        <p className="icp-card-body">
                            No decision maker information available.
                        </p>

                    )}

                </div>


                {/* =================================================
                    REGIONS
                ================================================= */}

                <div className="icp-insight-card">

                    <span className="icp-card-label">
                        Regions
                    </span>


                    {regions.length > 0 ? (

                        <ul className="icp-card-list">

                            {regions.map((region, index) => (

                                <li key={`${region}-${index}`}>
                                    {region}
                                </li>

                            ))}

                        </ul>

                    ) : (

                        <p className="icp-card-body">
                            No region information available.
                        </p>

                    )}

                </div>


                {/* =================================================
                    BUYING INTENT
                ================================================= */}

                <div className="icp-insight-card">

                    <span className="icp-card-label">
                        Buying Intent
                    </span>


                    <p className="icp-card-body">

                        {insight.buying_intent ||
                            "No buying intent information available."
                        }

                    </p>

                </div>

            </div>


            {/* ==================================================
                WHY
            ================================================== */}

            <div className="icp-why-panel">

                <span className="icp-card-label">
                    Why?
                </span>


                <p className="icp-card-body">

                    {insight.why ||
                        "No additional explanation available."
                    }

                </p>

            </div>


            {/* ==================================================
                ICP STATISTICS
            ================================================== */}

            <div className="icp-stats-row">


                <div className="icp-stat">

                    <span className="icp-stat-value">
                        {data?.total_matched_clients ?? 0}
                    </span>

                    <span className="icp-stat-label">
                        Similar Clients
                    </span>

                </div>


                <div className="icp-stat">

                    <span className="icp-stat-value">
                        {data?.total_campaigns ?? 0}
                    </span>

                    <span className="icp-stat-label">
                        Campaigns Analyzed
                    </span>

                </div>


                <div className="icp-stat">

                    <span className="icp-stat-value">
                        {data?.total_leads ?? 0}
                    </span>

                    <span className="icp-stat-label">
                        Qualified Leads
                    </span>

                </div>

            </div>


            {/* ==================================================
                DISCOVER BUYER GROUP BUTTON
            ================================================== */}

            <div
                style={{
                    display: "flex",
                    gap: "12px",
                    marginTop: "18px",
                    justifyContent: "flex-end"
                }}
            >

                <button
                    type="button"
                    className="icp-btn-primary"
                    onClick={onDiscoverBuyerGroup}
                    disabled={buyerGroupLoading}
                >

                    {buyerGroupLoading
                        ? "Building Buyer Group..."
                        : "Discover Buyer Group"
                    }

                </button>

            </div>


        </div>

    );
}


// ============================================================
// MAIN CREATE ICP COMPONENT
// ============================================================

export default function CreateICP({
    userId,
    onClose,

    // --------------------------------------------------------
    // Parent should provide this to open BuyerGroup component.
    //
    // Example:
    //
    // <CreateICP
    //     userId={userId}
    //     onDiscoverBuyerGroup={() => setInsight("buyer-group")}
    // />
    // --------------------------------------------------------

    onDiscoverBuyerGroup
}) {

    const [stage, setStage] =
        useState("init");


    const [product, setProduct] =
        useState(null);


    const [result, setResult] =
        useState(null);


    const [error, setError] =
        useState("");


    const [options, setOptions] =
        useState(null);


    const [buyerGroupLoading, setBuyerGroupLoading] =
        useState(false);


    // ========================================================
    // RUN ICP DISCOVERY
    // ========================================================

    const runDiscovery = async (selectedProduct) => {

        setProduct(selectedProduct);

        setStage("analyzing");

        setError("");


        try {

            const res =
                await axios.post(
                    `${API_BASE_URL}/mcp-icp/discover`,
                    {
                        user_id: userId
                    }
                );


            if (
                res.data?.data?.error ===
                "no_product_selected"
            ) {

                setError(
                    "No product or service has been selected yet. Choose one from the sidebar first."
                );

                setStage("error");

                return;
            }


            setResult(
                res.data?.data || null
            );


            setStage("result");


        } catch (err) {

            console.error(
                "ICP discovery failed:",
                err
            );


            setError(
                err.response?.data?.detail ||
                "Something went wrong while finding your ICP. Please try again."
            );


            setStage("error");

        }

    };


    // ========================================================
    // DISCOVER BUYER GROUP
    //
    // IMPORTANT:
    //
    // The backend already has:
    //
    // POST /buyer-group/discover
    //
    // So this button should call that endpoint.
    //
    // After successful discovery:
    //
    // 1. If parent supplied onDiscoverBuyerGroup(result)
    //    → parent can open BuyerGroup screen.
    //
    // 2. Otherwise we close this screen.
    // ========================================================

    const handleDiscoverBuyerGroup = async () => {

        if (buyerGroupLoading) {
            return;
        }


        setBuyerGroupLoading(true);

        setError("");


        try {

            const res =
                await axios.post(
                    `${API_BASE_URL}/buyer-group/discover`,
                    {
                        user_id: userId
                    }
                );


            console.log(
                "Buyer Group discovery response:",
                res.data
            );


            // ------------------------------------------------
            // Backend-level error
            // ------------------------------------------------

            if (
                res.data?.data?.error ===
                "no_product_selected"
            ) {

                setError(
                    "No product or service has been selected yet. Choose one from the sidebar first."
                );

                setBuyerGroupLoading(false);

                return;
            }


            // ------------------------------------------------
            // Successful Buyer Group discovery
            // ------------------------------------------------

            if (
                res.data?.status === "success" ||
                res.data?.data
            ) {

                const buyerGroupData =
                    res.data?.data;


                // --------------------------------------------
                // If parent has navigation callback,
                // send the complete result to parent.
                // --------------------------------------------

                if (
                    typeof onDiscoverBuyerGroup ===
                    "function"
                ) {

                    onDiscoverBuyerGroup(
                        buyerGroupData
                    );

                } else {

                    // ----------------------------------------
                    // Fallback:
                    // close ICP screen.
                    // Parent can then show BuyerGroup.
                    // ----------------------------------------

                    if (onClose) {
                        onClose();
                    }

                }

            }


        } catch (err) {

            console.error(
                "Discover Buyer Group failed:",
                err
            );


            setError(
                err.response?.data?.detail ||
                "Could not start Discover Buyer Group. Please try again."
            );

        } finally {

            setBuyerGroupLoading(false);

        }

    };


    // ========================================================
    // RESOLVE SAVED PRODUCT
    // ========================================================

    useEffect(() => {

        let cancelled = false;


        async function resolveSavedProduct() {

            try {

                const res =
                    await axios.get(
                        `${API_BASE_URL}/mcp-icp/product-options/${userId}`
                    );


                if (cancelled) {
                    return;
                }


                const opts =
                    Array.isArray(res.data?.options)
                        ? res.data.options
                        : [];


                const saved =
                    res.data?.selected_product;


                setOptions(opts);


                if (saved) {

                    runDiscovery(saved);

                } else {

                    setProduct(
                        opts[0] || null
                    );

                    setStage("select");

                }


            } catch (err) {

                if (!cancelled) {

                    console.error(
                        "Product resolution failed:",
                        err
                    );


                    setError(
                        err.response?.data?.detail ||
                        "Could not load your saved product/service. Please try again."
                    );


                    setStage("error");

                }

            }

        }


        resolveSavedProduct();


        return () => {

            cancelled = true;

        };

        // We intentionally only run this when userId changes.
        // eslint-disable-next-line react-hooks/exhaustive-deps

    }, [userId]);


    // ========================================================
    // RENDER
    // ========================================================

    return (

        <div className="icp-container">


            {/* =================================================
                BACK
            ================================================= */}

            {onClose && (

                <button
                    type="button"
                    className="icp-back-link"
                    onClick={onClose}
                >
                    ← Back
                </button>

            )}


            {/* =================================================
                INITIAL LOADING
            ================================================= */}

            {stage === "init" && (

                <div className="icp-loading-state">

                    <div className="icp-spin" />

                    <span>
                        Loading your ICP context...
                    </span>

                </div>

            )}


            {/* =================================================
                PRODUCT SELECTOR
            ================================================= */}

            {stage === "select" && (

                <ProductSelector
                    userId={userId}
                    initialOptions={options}
                    initialSelected={product}
                    onConfirm={runDiscovery}
                />

            )}


            {/* =================================================
                ICP ANALYZING
            ================================================= */}

            {stage === "analyzing" && (

                <AnalyzingState
                    product={product}
                />

            )}


            {/* =================================================
                ICP RESULT
            ================================================= */}

            {stage === "result" && (

                <ICPResult
                    product={product}
                    data={result}
                    onChangeProduct={() => {
                        setStage("select");
                    }}
                    onDiscoverBuyerGroup={
                        handleDiscoverBuyerGroup
                    }
                    buyerGroupLoading={
                        buyerGroupLoading
                    }
                />

            )}


            {/* =================================================
                ERROR
            ================================================= */}

            {stage === "error" && (

                <div className="icp-error-banner">

                    <div>
                        {error}
                    </div>


                    <button
                        type="button"
                        className="icp-retry-btn"
                        onClick={() => {

                            if (product) {

                                runDiscovery(product);

                            } else {

                                setStage("select");

                            }

                        }}
                    >
                        Try again
                    </button>

                </div>

            )}

        </div>

    );
}