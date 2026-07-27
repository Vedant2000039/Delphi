import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Loader2, Save, CheckCircle, AlertCircle, X, Plus } from "lucide-react";
import axios from "axios";
import AuthLayout, { useAuthStyles } from "./AuthLayout";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN;

const INDUSTRY_OPTIONS = [
    "Agriculture & Mining","Airlines & Aviation","Banking","Biotechnology",
    "Business Services","Chemicals","Computers & Electronics","Consulting",
    "Consumer Services","Defense & Space","Education - Higher Education",
    "Education - Primary & Secondary","Energy & Utilities","Financial",
    "Food & Beverages","Government - Federal / National","Government - Local",
    "Government - State / Provincial","Healthcare","High Tech","Insurance",
    "Life Sciences","Manufacturing","Marketing & Advertising","Media & Entertainment",
    "Nonprofit","Real Estate & Construction","Retail","Software & Internet",
    "Telecommunications","Transportation & Storage","Travel, Recreation & Leisure",
    "Wholesale & Distribution","Education","Accounting","Financial Services",
];

function StepIndicator({ step }) {
    return (
        <div className="dp-steps">
            <div className={`dp-step-node ${step > 1 ? "done" : "active"}`}>{step > 1 ? "✓" : "1"}</div>
            <div className={`dp-step-bar ${step > 1 ? "done" : "pending"}`} />
            <div className={`dp-step-node ${step === 2 ? "active" : "pending"}`}>2</div>
        </div>
    );
}

function TagSection({ label, items, emptyText, onRemove, inputValue, onInputChange, onAdd, placeholder }) {
    return (
        <div style={{ marginBottom: 20 }}>
            <label className="dp-label">
                {label}
                <span style={{ fontWeight: 400, color: "var(--dp-dim)", textTransform: "none", letterSpacing: 0, marginLeft: 6 }}>
                    — edit or add more
                </span>
            </label>
            <div className="dp-tag-area">
                {items.length === 0
                    ? <span style={{ color: "var(--dp-dim)", fontSize: 13, alignSelf: "center" }}>{emptyText}</span>
                    : items.map(item => (
                        <span key={item} className="dp-tag">
                            {item}
                            <button className="dp-tag-x" onClick={() => onRemove(item)}>×</button>
                        </span>
                    ))
                }
            </div>
            <div style={{ display: "flex", gap: 8 }}>
                <input
                    className="dp-input"
                    style={{ flex: 1, fontSize: 13 }}
                    placeholder={placeholder}
                    value={inputValue}
                    onChange={(e) => onInputChange(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), onAdd())}
                />
                <button
                    className="dp-btn dp-btn-outline"
                    style={{ width: "auto", padding: "0 16px", gap: 4, fontSize: 13, whiteSpace: "nowrap" }}
                    onClick={onAdd}
                >
                    + Add
                </button>
            </div>
        </div>
    );
}

// Field wrapper — must be outside Enrichment to avoid remount on every keystroke
function F({ label, name, req, errors, children }) {
    return (
        <div>
            <label className="dp-label">
                {label}{req && <span style={{ color: "var(--dp-error)", marginLeft: 2 }}>*</span>}
            </label>
            {children}
            {errors?.[name] && <div className="dp-field-error">{errors[name]}</div>}
        </div>
    );
}

export default function Enrichment() {
    useAuthStyles();
    const navigate = useNavigate();

    useEffect(() => {
        if (!document.getElementById("dp-enrich-spin")) {
            const s = document.createElement("style");
            s.id = "dp-enrich-spin";
            s.textContent = `@keyframes dp-enrich-spin { to { transform: rotate(360deg); } }`;
            document.head.appendChild(s);
        }
    }, []);

    const [step, setStep] = useState(1);

    // ── Individual state vars to avoid re-render/focus loss ──
    const [companyName,  setCompanyName]  = useState("");
    const [industry,     setIndustry]     = useState("");
    const [linkedinUrl,  setLinkedinUrl]  = useState("");
    const [companySize,  setCompanySize]  = useState("");
    const [headquarters, setHeadquarters] = useState("");
    const [type,         setType]         = useState("");
    const [companyType,  setCompanyType]  = useState("");
    const [founded,      setFounded]      = useState("");
    const [revenueSize,  setRevenueSize]  = useState("");
    const [specialties,  setSpecialties]  = useState("");

    const [formErrors,   setFormErrors]   = useState({});
    const [industryOpen, setIndustryOpen] = useState(false);

    const [websiteInput, setWebsiteInput] = useState("");
    const [isEnriching,  setIsEnriching]  = useState(false);
    const [enriched,     setEnriched]     = useState(false);
    const [scrapedOk,    setScrapedOk]    = useState(false);
    const [websiteUrl,   setWebsiteUrl]   = useState("");
    const [brands,       setBrands]       = useState([]);
    const [services,     setServices]     = useState([]);
    const [brandInput,   setBrandInput]   = useState("");
    const [serviceInput, setServiceInput] = useState("");
    const [enrichError,  setEnrichError]  = useState("");
    const [isSaving,     setIsSaving]     = useState(false);
    const [saveError,    setSaveError]    = useState("");

    const isServiceCompany = companyType.includes("Service");

    const getUserId = () => {
        try {
            const u  = JSON.parse(localStorage.getItem("user") || "{}");
            const id = parseInt(u.user_id);
            return (!isNaN(id) && id > 0) ? id : null;
        } catch { return null; }
    };

    const validateForm = () => {
        const e = {};
        if (!companyName.trim())  e.companyName  = "Required";
        if (!industry.trim())     e.industry     = "Required";
        if (!companySize.trim())  e.companySize  = "Required";
        if (!headquarters.trim()) e.headquarters = "Required";
        if (!type.trim())         e.type         = "Required";
        if (!companyType.trim())  e.companyType  = "Required";
        if (!revenueSize.trim())  e.revenueSize  = "Required";
        setFormErrors(e);
        return Object.keys(e).length === 0;
    };

    const handleNextStep = () => { if (validateForm()) setStep(2); };

    const handleEnrich = async () => {
        if (!websiteInput.trim()) return;
        setEnrichError(""); setScrapedOk(false); setIsEnriching(true); setEnriched(false);
        setBrands([]); setServices([]);
        try {
            const res = await axios.post(`${API_BASE_URL}/onboarding/enrich`, {
                website_url: websiteInput.trim(), user_id: getUserId() ?? 0, company_type: companyType,
            });
            const { scraped, message, data: d } = res.data;
            setWebsiteUrl(d.website || websiteInput.trim()); setScrapedOk(scraped);
            if (scraped && d.brands)   setBrands(d.brands.split(",").map(b => b.trim()).filter(Boolean));
            if (scraped && d.services) setServices(d.services.split(",").map(s => s.trim()).filter(Boolean));
            if (!scraped && message)   setEnrichError(message);
            setEnriched(true);
        } catch (err) {
            setEnrichError(err.response?.data?.detail || "Could not fetch website. Add items manually.");
            setWebsiteUrl(websiteInput.trim()); setEnriched(true);
        } finally { setIsEnriching(false); }
    };

    const addBrand   = () => { const b = brandInput.trim();   if (b && !brands.includes(b))   setBrands([...brands, b]);     setBrandInput(""); };
    const addService = () => { const s = serviceInput.trim(); if (s && !services.includes(s)) setServices([...services, s]); setServiceInput(""); };

    const handleSave = async () => {
        setSaveError("");
        const userId = getUserId();
        if (!userId) { setSaveError("Session expired. Please register again."); setTimeout(() => navigate("/Onboarding"), 2500); return; }
        setIsSaving(true);
        try {
            await axios.post(`${API_BASE_URL}/onboarding/save-profile`, {
                user_id: userId, company_name: companyName, industry, linkedin_url: linkedinUrl,
                company_size: companySize, headquarters, type, company_type: companyType,
                founded, revenue_size: revenueSize, specialties, website: websiteUrl,
                brands:   isServiceCompany ? "" : brands.join(", "),
                services: isServiceCompany ? services.join(", ") : "",
            });
            navigate("/Intelligence");
        } catch (err) { setSaveError(err.response?.data?.detail || "Failed to save. Please try again."); }
        finally { setIsSaving(false); }
    };



    return (
        <AuthLayout page="enrichment">
            <StepIndicator step={step} />

            {/* ── STEP 1 ─────────────────────────────────────────── */}
            {step === 1 && (
                <>
                    <div className="dp-form-head">
                        <h2>Company Details</h2>
                        <p>Tell us about your organization so we can personalize your intelligence feed</p>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

                        <F errors={formErrors} label="Company Name" name="companyName" req>
                            <input
                                className={`dp-input${formErrors.companyName ? " err" : ""}`}
                                placeholder="e.g. XTS World"
                                value={companyName}
                                onChange={(e) => setCompanyName(e.target.value)}
                            />
                        </F>

                        {/* Industry dropdown */}
                        <F errors={formErrors} label="Industry" name="industry" req>
                            <div
                                style={{ position: "relative" }}
                                onBlur={() => setTimeout(() => setIndustryOpen(false), 120)}
                            >
                                <button
                                    type="button"
                                    className={`dp-input${formErrors.industry ? " err" : ""}`}
                                    style={{
                                        width: "100%", textAlign: "left", cursor: "pointer",
                                        color: industry ? "var(--dp-text)" : "var(--dp-dim)",
                                        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%235a6a85' d='M6 8L0 0h12z'/%3E%3C/svg%3E")`,
                                        backgroundRepeat: "no-repeat",
                                        backgroundPosition: "right 14px center",
                                        paddingRight: 38,
                                    }}
                                    onClick={() => setIndustryOpen(o => !o)}
                                >
                                    {industry || "Select industry"}
                                </button>
                                {industryOpen && (
                                    <div style={{
                                        position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0,
                                        background: "#fdfdfd", border: "1px solid var(--dp-border)",
                                        borderRadius: 8, maxHeight: 220, overflowY: "auto",
                                        zIndex: 3000, boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
                                    }}>
                                        {INDUSTRY_OPTIONS.map(ind => (
                                            <button
                                                key={ind}
                                                type="button"
                                                onMouseDown={(e) => e.preventDefault()}
                                                onClick={() => { setIndustry(ind); setIndustryOpen(false); }}
                                                style={{
                                                    display: "block", width: "100%", textAlign: "left",
                                                    padding: "9px 14px", fontSize: 13.5,
                                                    fontFamily: "var(--f-body)", border: "none", cursor: "pointer",
                                                    background: industry === ind ? "rgba(99,179,237,0.1)" : "transparent",
                                                    color: industry === ind ? "var(--dp-cyan)" : "var(--dp-muted)",
                                                }}
                                                onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.04)"}
                                                onMouseLeave={e => e.currentTarget.style.background = industry === ind ? "rgba(99,179,237,0.1)" : "transparent"}
                                            >
                                                {ind}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </F>

                        <div className="dp-grid-2">
                            <F errors={formErrors} label="Company Size" name="companySize" req>
                                <select
                                    className={`dp-input${formErrors.companySize ? " err" : ""}`}
                                    value={companySize}
                                    onChange={(e) => setCompanySize(e.target.value)}
                                >
                                    <option value="">Select size</option>
                                    {["1–10 employees","11–50 employees","51–200 employees","201–500 employees","501–1000 employees","1001–5000 employees","5000+ employees"].map(o => <option key={o}>{o}</option>)}
                                </select>
                            </F>

                            <F errors={formErrors} label="Revenue Size" name="revenueSize" req>
                                <select
                                    className={`dp-input${formErrors.revenueSize ? " err" : ""}`}
                                    value={revenueSize}
                                    onChange={(e) => setRevenueSize(e.target.value)}
                                >
                                    <option value="">Select revenue</option>
                                    {["Under $1M","$1M – $10M","$10M – $50M","$50M – $100M","$100M – $500M","$500M – $1B","Over $1B"].map(o => <option key={o}>{o}</option>)}
                                </select>
                            </F>

                            <F errors={formErrors} label="Headquarters" name="headquarters" req>
                                <input
                                    className={`dp-input${formErrors.headquarters ? " err" : ""}`}
                                    placeholder="e.g. Pune, India"
                                    value={headquarters}
                                    onChange={(e) => setHeadquarters(e.target.value)}
                                />
                            </F>

                            <F errors={formErrors} label="Type" name="type" req>
                                <select
                                    className={`dp-input${formErrors.type ? " err" : ""}`}
                                    value={type}
                                    onChange={(e) => setType(e.target.value)}
                                >
                                    <option value="">Select type</option>
                                    {["Privately Held","Public Company","Self Employed","Government Agency","Nonprofit","Partnership","Sole Proprietorship"].map(o => <option key={o}>{o}</option>)}
                                </select>
                            </F>

                            <F errors={formErrors} label="Company Type" name="companyType" req>
                                <select
                                    className={`dp-input${formErrors.companyType ? " err" : ""}`}
                                    value={companyType}
                                    onChange={(e) => setCompanyType(e.target.value)}
                                >
                                    <option value="">Select type</option>
                                    <option>Product Based Company</option>
                                    <option>Service Based Company</option>
                                </select>
                            </F>

                            <F errors={formErrors} label="Founded" name="founded">
                                <input
                                    className="dp-input"
                                    placeholder="e.g. 2010"
                                    value={founded}
                                    onChange={(e) => setFounded(e.target.value)}
                                />
                            </F>
                        </div>

                        <F errors={formErrors} label="LinkedIn URL" name="linkedinUrl">
                            <input
                                type="url"
                                className="dp-input"
                                placeholder="https://www.linkedin.com/company/..."
                                value={linkedinUrl}
                                onChange={(e) => setLinkedinUrl(e.target.value)}
                            />
                        </F>

                        <F errors={formErrors} label="Specialties" name="specialties">
                            <input
                                className="dp-input"
                                placeholder="e.g. Healthcare, AI, SaaS"
                                value={specialties}
                                onChange={(e) => setSpecialties(e.target.value)}
                            />
                        </F>
                    </div>

                    <button className="dp-btn dp-btn-primary" onClick={handleNextStep} style={{ marginTop: 24 }}>
                        Next: Add Company Website →
                    </button>
                </>
            )}

            {/* ── STEP 2 ─────────────────────────────────────────── */}
            {step === 2 && (
                <>
                    <div className="dp-form-head">
                        <h2>{isServiceCompany ? "Detect Services" : "Detect Brands"}</h2>
                        <p>
                            Enter your website — we'll detect{" "}
                            {isServiceCompany ? "your services and solutions." : "your brands, models and products."}
                        </p>
                    </div>

                    <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
                        <input
                            type="text"
                            className="dp-input"
                            style={{ flex: 1 }}
                            placeholder="e.g. https://xtsworld.com/"
                            value={websiteInput}
                            onChange={(e) => setWebsiteInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleEnrich()}
                        />
                        <button
                            className="dp-btn dp-btn-primary"
                            style={{ width: "auto", padding: "0 20px", whiteSpace: "nowrap" }}
                            onClick={handleEnrich}
                            disabled={!websiteInput.trim() || isEnriching}
                        >
                            {isEnriching
                                ? <Loader2 size={14} style={{ animation: "dp-enrich-spin 1s linear infinite" }} />
                                : "Detect"
                            }
                        </button>
                    </div>

                    {isEnriching && (
                        <div style={{ textAlign: "center", padding: "24px 0", color: "var(--dp-muted)" }}>
                            <Loader2 size={26} style={{ animation: "dp-enrich-spin 1s linear infinite", color: "var(--dp-cyan)", marginBottom: 10 }} />
                            <p style={{ fontSize: 13 }}>Scanning website...</p>
                        </div>
                    )}

                    {scrapedOk && enriched && !isEnriching && (
                        <div className="dp-alert dp-alert-success" style={{ marginBottom: 16 }}>
                            {isServiceCompany
                                ? `${services.length} service${services.length !== 1 ? "s" : ""} detected.`
                                : `${brands.length} brand${brands.length !== 1 ? "s" : ""} detected.`
                            } Review and edit below.
                        </div>
                    )}

                    {enrichError && (
                        <div className="dp-alert dp-alert-warn" style={{ marginBottom: 16 }}>
                            {enrichError} Add {isServiceCompany ? "services" : "brands"} manually below.
                        </div>
                    )}

                    {enriched && !isEnriching && (
                        <>
                            {!isServiceCompany && (
                                <TagSection
                                    label="Brands / Models / Products"
                                    items={brands}
                                    emptyText="No brands detected — add manually"
                                    onRemove={(b) => setBrands(brands.filter(x => x !== b))}
                                    inputValue={brandInput}
                                    onInputChange={setBrandInput}
                                    onAdd={addBrand}
                                    placeholder="Add brand e.g. Delphi AI"
                                />
                            )}
                            {isServiceCompany && (
                                <TagSection
                                    label="Services / Solutions"
                                    items={services}
                                    emptyText="No services detected — add manually"
                                    onRemove={(s) => setServices(services.filter(x => x !== s))}
                                    inputValue={serviceInput}
                                    onInputChange={setServiceInput}
                                    onAdd={addService}
                                    placeholder="Add service e.g. Cloud Consulting"
                                />
                            )}

                            {saveError && <div className="dp-alert dp-alert-error">{saveError}</div>}

                            <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
                                <button
                                    className="dp-btn dp-btn-outline"
                                    style={{ width: "auto", padding: "0 18px" }}
                                    onClick={() => setStep(1)}
                                >
                                    ← Back
                                </button>
                                <button
                                    className="dp-btn dp-btn-primary"
                                    style={{ flex: 1 }}
                                    onClick={handleSave}
                                    disabled={isSaving}
                                >
                                    {isSaving
                                        ? <><div className="dp-spin" /> Saving...</>
                                        : "Save & Go to Dashboard"
                                    }
                                </button>
                            </div>
                        </>
                    )}

                    {!enriched && !isEnriching && (
                        <div style={{ display: "flex", gap: 10 }}>
                            <button
                                className="dp-btn dp-btn-outline"
                                style={{ width: "auto", padding: "0 18px" }}
                                onClick={() => setStep(1)}
                            >
                                ← Back
                            </button>
                            <button
                                className="dp-btn dp-btn-outline"
                                style={{
                                    flex: 1,
                                    borderColor: "rgba(99,179,237,0.35)",
                                    color: "var(--dp-cyan)",
                                }}
                                onClick={() => { setWebsiteUrl(websiteInput.trim()); setEnriched(true); }}
                                disabled={!websiteInput.trim()}
                            >
                                Skip — add {isServiceCompany ? "services" : "brands"} manually →
                            </button>
                        </div>
                    )}
                </>
            )}
        </AuthLayout>
    );
}