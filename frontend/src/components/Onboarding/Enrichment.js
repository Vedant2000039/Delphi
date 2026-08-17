// // frontend/src/components/Onboarding/Enrichment.js
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Search,
    Loader2,
    Save,
    CheckCircle,
    AlertCircle,
    X,
    Plus,
} from "lucide-react";
import axios from "axios";
import AuthLayout from "./AuthLayout";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN;

const INDUSTRY_OPTIONS = [
    "Agriculture & Mining",
    "Airlines & Aviation",
    "Banking",
    "Biotechnology",
    "Business Services",
    "Chemicals",
    "Computers & Electronics",
    "Consulting",
    "Consumer Services",
    "Defense & Space",
    "Education - Higher Education",
    "Education - Primary & Secondary",
    "Energy & Utilities",
    "Financial",
    "Food & Beverages",
    "Government - Federal / National",
    "Government - Local",
    "Government - State / Provincial",
    "Healthcare",
    "High Tech",
    "Insurance",
    "Life Sciences",
    "Manufacturing",
    "Marketing & Advertising",
    "Media & Entertainment",
    "Nonprofit",
    "Real Estate & Construction",
    "Retail",
    "Software & Internet",
    "Telecommunications",
    "Transportation & Storage",
    "Travel, Recreation & Leisure",
    "Wholesale & Distribution",
    "Education",
    "Accounting",
    "Financial Services",
];

//────────────────────────────────────────────────────────────

export default function Enrichment() {

    const navigate = useNavigate();

    const [step, setStep] = useState(1);

    // STEP 1

    const [form, setForm] = useState({
        company_name: "",
        industry: "",
        linkedin_url: "",
        company_size: "",
        headquarters: "",
        type: "",
        company_type: "",
        founded: "",
        revenue_size: "",
        specialties: "",
    });

    const [formErrors, setFormErrors] = useState({});

    // STEP 2

    const [websiteInput, setWebsiteInput] = useState("");

    const [isEnriching, setIsEnriching] = useState(false);

    const [enriched, setEnriched] = useState(false);

    const [scrapedOk, setScrapedOk] = useState(false);

    const [websiteUrl, setWebsiteUrl] = useState("");

    const [brands, setBrands] = useState([]);

    const [services, setServices] = useState([]);

    const [brandInput, setBrandInput] = useState("");

    const [serviceInput, setServiceInput] = useState("");

    const [enrichError, setEnrichError] = useState("");

    // STEP 3

    const [isSaving, setIsSaving] = useState(false);

    const [saveError, setSaveError] = useState("");

    const isServiceCompany =
        form.company_type.includes("Service");

    //────────────────────────────────────────────

    const getUserId = () => {

        try {

            const user = JSON.parse(localStorage.getItem("user") || "{}");

            const id = parseInt(user.user_id);

            return !isNaN(id) && id > 0 ? id : null;

        } catch {

            return null;

        }
    };

    //────────────────────────────────────────────

    const validateForm = () => {

        const e = {};

        if (!form.company_name.trim())
            e.company_name = "Required";

        if (!form.industry.trim())
            e.industry = "Required";

        if (!form.company_size.trim())
            e.company_size = "Required";

        if (!form.headquarters.trim())
            e.headquarters = "Required";

        if (!form.type.trim())
            e.type = "Required";

        if (!form.company_type.trim())
            e.company_type = "Required";

        if (!form.revenue_size.trim())
            e.revenue_size = "Required";

        setFormErrors(e);

        return Object.keys(e).length === 0;
    };

    const handleNextStep = () => {

        if (validateForm())

            setStep(2);

    };

    //────────────────────────────────────────────

    const handleEnrich = async () => {

        if (!websiteInput.trim()) return;

        setEnrichError("");

        setScrapedOk(false);

        setIsEnriching(true);

        setEnriched(false);

        setBrands([]);

        setServices([]);

        try {

            const res = await axios.post(
                `${API_BASE_URL}/onboarding/enrich`,
                {
                    website_url: websiteInput.trim(),
                    user_id: getUserId() ?? 0,
                    company_type: form.company_type,
                }
            );

            const { scraped, message, data } = res.data;

            setWebsiteUrl(data.website || websiteInput.trim());

            setScrapedOk(scraped);

            if (scraped && data.brands) {

                setBrands(
                    data.brands
                        .split(",")
                        .map((x) => x.trim())
                        .filter(Boolean)
                );

            }

            if (scraped && data.services) {

                setServices(
                    data.services
                        .split(",")
                        .map((x) => x.trim())
                        .filter(Boolean)
                );

            }

            if (!scraped && message)

                setEnrichError(message);

            setEnriched(true);

        } catch (err) {

            setEnrichError(
                err.response?.data?.detail ||
                "Could not fetch website. You can add items manually."
            );

            setWebsiteUrl(websiteInput.trim());

            setEnriched(true);

        } finally {

            setIsEnriching(false);

        }

    };

    //────────────────────────────────────────────

    const addBrand = () => {

        const b = brandInput.trim();

        if (b && !brands.includes(b))

            setBrands([...brands, b]);

        setBrandInput("");

    };

    const removeBrand = (b) => {

        setBrands(brands.filter((x) => x !== b));

    };

    const addService = () => {

        const s = serviceInput.trim();

        if (s && !services.includes(s))

            setServices([...services, s]);

        setServiceInput("");

    };

    const removeService = (s) => {

        setServices(services.filter((x) => x !== s));

    };

    //────────────────────────────────────────────

    const handleSave = async () => {

        setSaveError("");

        const userId = getUserId();

        if (!userId) {

            setSaveError(
                "Session expired. Please register again."
            );

            setTimeout(() => navigate("/Onboarding"), 2500);

            return;

        }

        setIsSaving(true);

        try {

            await axios.post(
                `${API_BASE_URL}/onboarding/save-profile`,
                {
                    user_id: userId,
                    company_name: form.company_name,
                    industry: form.industry,
                    linkedin_url: form.linkedin_url,
                    company_size: form.company_size,
                    headquarters: form.headquarters,
                    type: form.type,
                    company_type: form.company_type,
                    founded: form.founded,
                    revenue_size: form.revenue_size,
                    specialties: form.specialties,
                    website: websiteUrl,

                    brands: isServiceCompany
                        ? ""
                        : brands.join(", "),

                    services: isServiceCompany
                        ? services.join(", ")
                        : "",
                }
            );

            navigate("/Intelligence");

        } catch (err) {

            setSaveError(
                err.response?.data?.detail ||
                "Failed to save. Please try again."
            );

        } finally {

            setIsSaving(false);

        }

    };

    //────────────────────────────────────────────

    return (
        <AuthLayout page={step === 2 ? "extraction" : "enrichment"}>
            {step === 1 && (
                        <>
                            <div className="dp-form-head">
                                <h2>Company details</h2>
                                <p>Tell us a little about your company to get started.</p>
                            </div>

                            <div className="row g-3">
                                <div className="col-12">
                                    <label className="form-label fw-semibold small">
                                        Company Name <span className="text-danger">*</span>
                                    </label>
                                    <input
                                        className={`form-control ${formErrors.company_name ? "is-invalid" : ""}`}
                                        placeholder="e.g. XTS World"
                                        value={form.company_name}
                                        onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                                    />
                                    {formErrors.company_name && <div className="invalid-feedback">{formErrors.company_name}</div>}
                                </div>

                                <div className="col-12">
                                    <label className="form-label fw-semibold small">
                                        Industry <span className="text-danger">*</span>
                                    </label>
                                    <select
                                        className={`form-select ${formErrors.industry ? "is-invalid" : ""}`}
                                        value={form.industry}
                                        onChange={(e) => setForm({ ...form, industry: e.target.value })}
                                    >
                                        <option value="">Select Industry</option>
                                        {INDUSTRY_OPTIONS.map((item) => (
                                            <option key={item} value={item}>
                                                {item}
                                            </option>
                                        ))}
                                    </select>
                                    {formErrors.industry && <div className="invalid-feedback">{formErrors.industry}</div>}
                                </div>

                                <div className="col-md-6">
                                    <label className="form-label fw-semibold small">
                                        Company Size <span className="text-danger">*</span>
                                    </label>
                                    <select
                                        className={`form-select ${formErrors.company_size ? "is-invalid" : ""}`}
                                        value={form.company_size}
                                        onChange={(e) => setForm({ ...form, company_size: e.target.value })}
                                    >
                                        <option value="">Select size</option>
                                        <option>1–10 employees</option>
                                        <option>11–50 employees</option>
                                        <option>51–200 employees</option>
                                        <option>201–500 employees</option>
                                        <option>501–1000 employees</option>
                                        <option>1001–5000 employees</option>
                                        <option>5000+ employees</option>
                                    </select>
                                    {formErrors.company_size && <div className="invalid-feedback">{formErrors.company_size}</div>}
                                </div>

                                <div className="col-md-6">
                                    <label className="form-label fw-semibold small">
                                        Revenue Size <span className="text-danger">*</span>
                                    </label>
                                    <select
                                        className={`form-select ${formErrors.revenue_size ? "is-invalid" : ""}`}
                                        value={form.revenue_size}
                                        onChange={(e) => setForm({ ...form, revenue_size: e.target.value })}
                                    >
                                        <option value="">Select revenue</option>
                                        <option>Under $1M</option>
                                        <option>$1M – $10M</option>
                                        <option>$10M – $50M</option>
                                        <option>$50M – $100M</option>
                                        <option>$100M – $500M</option>
                                        <option>$500M – $1B</option>
                                        <option>Over $1B</option>
                                    </select>
                                    {formErrors.revenue_size && <div className="invalid-feedback">{formErrors.revenue_size}</div>}
                                </div>

                                <div className="col-md-6">
                                    <label className="form-label fw-semibold small">
                                        Headquarters <span className="text-danger">*</span>
                                    </label>
                                    <input
                                        className={`form-control ${formErrors.headquarters ? "is-invalid" : ""}`}
                                        placeholder="e.g. Pune, India"
                                        value={form.headquarters}
                                        onChange={(e) => setForm({ ...form, headquarters: e.target.value })}
                                    />
                                    {formErrors.headquarters && <div className="invalid-feedback">{formErrors.headquarters}</div>}
                                </div>

                                <div className="col-md-6">
                                    <label className="form-label fw-semibold small">
                                        Type <span className="text-danger">*</span>
                                    </label>
                                    <select
                                        className={`form-select ${formErrors.type ? "is-invalid" : ""}`}
                                        value={form.type}
                                        onChange={(e) => setForm({ ...form, type: e.target.value })}
                                    >
                                        <option value="">Select type</option>
                                        <option>Privately Held</option>
                                        <option>Public Company</option>
                                        <option>Self Employed</option>
                                        <option>Government Agency</option>
                                        <option>Nonprofit</option>
                                        <option>Partnership</option>
                                        <option>Sole Proprietorship</option>
                                    </select>
                                    {formErrors.type && <div className="invalid-feedback">{formErrors.type}</div>}
                                </div>

                                <div className="col-md-6">
                                    <label className="form-label fw-semibold small">Company Type <span className="text-danger">*</span></label>
                                    <select
                                        className={`form-select ${formErrors.company_type ? "is-invalid" : ""}`}
                                        value={form.company_type}
                                        onChange={(e) => setForm({ ...form, company_type: e.target.value })}
                                    >
                                        <option value="">Select type</option>
                                        <option>Product Based Company</option>
                                        <option>Service Based Company</option>
                                    </select>
                                    {formErrors.company_type && <div className="invalid-feedback">{formErrors.company_type}</div>}
                                </div>

                                <div className="col-md-6">
                                    <label className="form-label fw-semibold small">Founded</label>
                                    <input
                                        className="form-control"
                                        placeholder="e.g. 2010"
                                        value={form.founded}
                                        onChange={(e) => setForm({ ...form, founded: e.target.value })}
                                    />
                                </div>

                                <div className="col-12">
                                    <label className="form-label fw-semibold small">LinkedIn URL</label>
                                    <input
                                        type="url"
                                        className="form-control"
                                        placeholder="https://www.linkedin.com/company/..."
                                        value={form.linkedin_url}
                                        onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })}
                                    />
                                </div>

                                <div className="col-12">
                                    <label className="form-label fw-semibold small">Specialties</label>
                                    <input
                                        className="form-control"
                                        placeholder="e.g. Healthcare, AI, SaaS"
                                        value={form.specialties}
                                        onChange={(e) => setForm({ ...form, specialties: e.target.value })}
                                    />
                                </div>
                            </div>

                            <button className="dp-btn dp-btn-primary" style={{ marginTop: 24 }} onClick={handleNextStep}>
                                Next: Add Company Website →
                            </button>
                        </>
                    )}

                    {step === 2 && (
                        <>
                            <div className="dp-form-head">
                                <h2>{isServiceCompany ? "Detect services" : "Detect brands & products"}</h2>
                                <p>
                                    Enter your company website URL — we'll automatically detect{" "}
                                    {isServiceCompany ? "your services and solutions." : "your brands, models and products."}
                                </p>
                            </div>

                            <div className="d-flex gap-2 mb-3">
                                <div className="input-group">
                                    <span className="input-group-text bg-light">
                                        <Search size={15} className="text-muted" />
                                    </span>
                                    <input
                                        type="text"
                                        className="form-control"
                                        placeholder="e.g. https://xtsworld.com/"
                                        value={websiteInput}
                                        onChange={(e) => setWebsiteInput(e.target.value)}
                                        onKeyDown={(e) => e.key === "Enter" && handleEnrich()}
                                    />
                                </div>
                                <button
                                    className="dp-btn dp-btn-primary"
                                    onClick={handleEnrich}
                                    disabled={!websiteInput.trim() || isEnriching}
                                    style={{ whiteSpace: "nowrap", width: "auto", padding: "10px 24px" }}
                                >
                                    {isEnriching ? "Detecting..." : "Detect"}
                                </button>
                            </div>

                            {isEnriching && (
                                <div className="text-center text-muted py-3">
                                    <Loader2 size={26} className="mb-2" style={{ animation: "spin 1s linear infinite" }} />
                                    <p className="small mb-0">
                                        Scanning website for {isServiceCompany ? "services..." : "brands & products..."}
                                    </p>
                                </div>
                            )}

                            {scrapedOk && enriched && !isEnriching && (
                                <div className="alert alert-success py-2 small mb-3 d-flex align-items-center gap-2">
                                    <CheckCircle size={15} />
                                    <span>
                                        {isServiceCompany
                                            ? `${services.length} service${services.length !== 1 ? "s" : ""} detected. Review and edit below.`
                                            : `${brands.length} brand${brands.length !== 1 ? "s" : ""} detected. Review and edit below.`}
                                    </span>
                                </div>
                            )}

                            {enrichError && (
                                <div className="alert alert-warning py-2 small mb-3 d-flex align-items-start gap-2">
                                    <AlertCircle size={15} className="mt-1 flex-shrink-0" />
                                    <span>
                                        {enrichError} You can add {isServiceCompany ? "services" : "brands"} manually below.
                                    </span>
                                </div>
                            )}

                            {enriched && !isEnriching && (
                                <>
                                    {!isServiceCompany && (
                                        <div className="mb-3">
                                            <label className="form-label fw-semibold small" htmlFor="brand-input">
                                                Brands / Models / Products{" "}
                                                <span className="text-muted fw-normal ms-1">(edit or add more)</span>
                                            </label>
                                            <div className="d-flex flex-wrap gap-2 mb-2 p-2 border rounded" style={{ minHeight: 48, background: "#f8fafc" }}>
                                                {brands.length === 0 && (
                                                    <span className="text-muted small align-self-center">
                                                        No brands detected — add manually below
                                                    </span>
                                                )}
                                                {brands.map((b) => (
                                                    <span key={b} className="badge d-flex align-items-center gap-1 px-2 py-1" style={{ background: "#dbeafe", color: "#1d4ed8", fontSize: 12, fontWeight: 500 }}>
                                                        {b}
                                                        <button className="btn p-0 border-0 bg-transparent ms-1" style={{ lineHeight: 1 }} onClick={() => removeBrand(b)}>
                                                            <X size={11} color="#1d4ed8" />
                                                        </button>
                                                    </span>
                                                ))}
                                            </div>
                                            <div className="input-group">
                                                <input
                                                    id="brand-input"
                                                    className="form-control"
                                                    placeholder="Add brand/model manually"
                                                    value={brandInput}
                                                    onChange={(e) => setBrandInput(e.target.value)}
                                                    onKeyDown={(e) => e.key === "Enter" && addBrand()}
                                                />
                                                <button className="btn btn-outline-primary d-flex align-items-center gap-1" onClick={addBrand}>
                                                    <Plus size={14} /> Add
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {isServiceCompany && (
                                        <div className="mb-3">
                                            <label className="form-label fw-semibold small" htmlFor="service-input">
                                                Services / Solutions{" "}
                                                <span className="text-muted fw-normal ms-1">(edit or add more)</span>
                                            </label>
                                            <div className="d-flex flex-wrap gap-2 mb-2 p-2 border rounded" style={{ minHeight: 48, background: "#f8fafc" }}>
                                                {services.length === 0 && (
                                                    <span className="text-muted small align-self-center">
                                                        No services detected — add manually below
                                                    </span>
                                                )}
                                                {services.map((s) => (
                                                    <span key={s} className="badge d-flex align-items-center gap-1 px-2 py-1" style={{ background: "#dbeafe", color: "#1d4ed8", fontSize: 12, fontWeight: 500 }}>
                                                        {s}
                                                        <button className="btn p-0 border-0 bg-transparent ms-1" style={{ lineHeight: 1 }} onClick={() => removeService(s)}>
                                                            <X size={11} color="#1d4ed8" />
                                                        </button>
                                                    </span>
                                                ))}
                                            </div>
                                            <div className="input-group">
                                                <input
                                                    id="service-input"
                                                    className="form-control"
                                                    placeholder="Add service manually"
                                                    value={serviceInput}
                                                    onChange={(e) => setServiceInput(e.target.value)}
                                                    onKeyDown={(e) => e.key === "Enter" && addService()}
                                                />
                                                <button className="btn btn-outline-primary d-flex align-items-center gap-1" onClick={addService}>
                                                    <Plus size={14} /> Add
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {saveError && (
                                        <div className="dp-alert dp-alert-error">{saveError}</div>
                                    )}

                                    <div className="dp-btn-row" style={{ marginTop: 18 }}>
                                        <button className="dp-btn dp-btn-secondary" onClick={() => setStep(1)}>
                                            ← Back
                                        </button>
                                        <button className="dp-btn dp-btn-primary" onClick={handleSave} disabled={isSaving}>
                                            {isSaving ? <div className="dp-spin" /> : <Save size={15} />}
                                            {isSaving ? "Saving..." : "Save"}
                                        </button>
                                    </div>
                                </>
                            )}

                            {!enriched && !isEnriching && (
                                <div className="dp-btn-row" style={{ marginTop: 10 }}>
                                    <button className="dp-btn dp-btn-secondary" onClick={() => setStep(1)}>
                                        ← Back
                                    </button>
                                    <button
                                        className="dp-btn dp-btn-secondary"
                                        style={{ color: "var(--dp-primary)", borderColor: "var(--dp-primary-light)" }}
                                        disabled={!websiteInput.trim()}
                                        onClick={() => {
                                            setWebsiteUrl(websiteInput.trim());
                                            setEnriched(true);
                                        }}
                                    >
                                        Skip detection, add {isServiceCompany ? "services" : "brands"} manually →
                                    </button>
                                </div>
                            )}
                        </>
                    )}

            {/* <div className="dp-center dp-mt-3">
                <button className="dp-link-muted" onClick={() => navigate("/Dashboard")}>
                    Skip for now →
                </button>
            </div> */}
        </AuthLayout>
    );
}