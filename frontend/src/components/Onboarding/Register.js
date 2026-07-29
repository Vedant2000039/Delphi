// frontend/src/components/Onboarding/Register.js
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import AuthLayout, { useAuthStyles } from "./AuthLayout";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN || "http://localhost:8000";

const getRegisterError = (err) => {
    const detail = err.response?.data?.detail;

    if (Array.isArray(detail)) {
        return detail.map((item) => item.msg).filter(Boolean).join(", ");
    }

    if (typeof detail === "string") return detail;
    if (err.response?.data?.message) return err.response.data.message;
    if (err.response?.status) return `Registration failed (${err.response.status}). Please try again.`;
    if (err.request) return "Could not reach the API server. Make sure the backend is running on http://localhost:8000.";

    return "Registration failed. Please try again.";
};

export default function Register() {
    useAuthStyles();
    const navigate = useNavigate();

    const [firstName,   setFirstName]   = useState("");
    const [lastName,    setLastName]    = useState("");
    const [companyName, setCompanyName] = useState("");
    const [email,       setEmail]       = useState("");
    const [password,    setPassword]    = useState("");
    const [confirmPwd,  setConfirmPwd]  = useState("");

    const [errors,   setErrors]   = useState({});
    const [loading,  setLoading]  = useState(false);
    const [apiError, setApiError] = useState("");
    const [showPass,    setShowPass]    = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    const clearErr = (key) => setErrors((prev) => ({ ...prev, [key]: "" }));

    const validate = () => {
        const e = {};
        if (!firstName.trim())   e.firstName   = "Required";
        if (!lastName.trim())    e.lastName    = "Required";
        if (!companyName.trim()) e.companyName = "Required";
        if (!email.trim())       e.email       = "Required";
        if (!password)           e.password    = "Required";
        if (password.length < 6) e.password    = "Min. 6 characters";
        if (password !== confirmPwd) e.confirmPwd = "Passwords do not match";
        setErrors(e);
        return Object.keys(e).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setApiError("");
        if (!validate()) return;
        setLoading(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/register`, {
                first_name:   firstName.trim(),
                last_name:    lastName.trim(),
                company_name: companyName.trim(),
                email:        email.trim(),
                password,
            });
            navigate("/Otp", { state: { email: email.trim() } });
        } catch (err) {
            setApiError(getRegisterError(err));
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthLayout page="register">
            <div className="dp-form-head">
                <h2>Create account</h2>
                <p>Set up your account</p>
            </div>

            {apiError && <div className="dp-alert dp-alert-error">{apiError}</div>}

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>

                {/* Name row */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                    <div>
                        <label className="dp-label">First Name</label>
                        <input
                            type="text"
                            className={`dp-input${errors.firstName ? " err" : ""}`}
                            placeholder="John"
                            value={firstName}
                            onChange={(e) => { setFirstName(e.target.value); clearErr("firstName"); }}
                        />
                        {errors.firstName && <div className="dp-field-error">{errors.firstName}</div>}
                    </div>
                    <div>
                        <label className="dp-label">Last Name</label>
                        <input
                            type="text"
                            className={`dp-input${errors.lastName ? " err" : ""}`}
                            placeholder="Doe"
                            value={lastName}
                            onChange={(e) => { setLastName(e.target.value); clearErr("lastName"); }}
                        />
                        {errors.lastName && <div className="dp-field-error">{errors.lastName}</div>}
                    </div>
                </div>

                <div>
                    <label className="dp-label">Company Name</label>
                    <input
                        type="text"
                        className={`dp-input${errors.companyName ? " err" : ""}`}
                        placeholder="XTS World Pvt Ltd"
                        value={companyName}
                        onChange={(e) => { setCompanyName(e.target.value); clearErr("companyName"); }}
                    />
                    {errors.companyName && <div className="dp-field-error">{errors.companyName}</div>}
                </div>

                <div>
                    <label className="dp-label">Work Email</label>
                    <input
                        type="email"
                        className={`dp-input${errors.email ? " err" : ""}`}
                        placeholder="john@company.com"
                        value={email}
                        onChange={(e) => { setEmail(e.target.value); clearErr("email"); }}
                    />
                    {errors.email && <div className="dp-field-error">{errors.email}</div>}
                </div>

                <div>
                    <label className="dp-label">Password</label>
                    <div className="dp-pass-wrap">
                        <input
                            type={showPass ? "text" : "password"}
                            className={`dp-input${errors.password ? " err" : ""}`}
                            placeholder="Min. 6 characters"
                            value={password}
                            onChange={(e) => { setPassword(e.target.value); clearErr("password"); }}
                        />
                        <button type="button" className="dp-eye-btn" onClick={() => setShowPass(!showPass)} tabIndex={-1}>
                            {showPass ? "●" : "○"}
                        </button>
                    </div>
                    {errors.password && <div className="dp-field-error">{errors.password}</div>}
                </div>

                <div>
                    <label className="dp-label">Confirm Password</label>
                    <div className="dp-pass-wrap">
                        <input
                            type={showConfirm ? "text" : "password"}
                            className={`dp-input${errors.confirmPwd ? " err" : ""}`}
                            placeholder="Re-enter password"
                            value={confirmPwd}
                            onChange={(e) => { setConfirmPwd(e.target.value); clearErr("confirmPwd"); }}
                        />
                        <button type="button" className="dp-eye-btn" onClick={() => setShowConfirm(!showConfirm)} tabIndex={-1}>
                            {showConfirm ? "●" : "○"}
                        </button>
                    </div>
                    {errors.confirmPwd && <div className="dp-field-error">{errors.confirmPwd}</div>}
                </div>

                <button type="submit" className="dp-btn dp-btn-primary" disabled={loading} style={{ marginTop: 4 }}>
                    {loading ? <><div className="dp-spin" /> Creating account...</> : "Create Account & Send OTP"}
                </button>
            </form>

            <div className="dp-divider">already a member?</div>

            <div style={{ textAlign: "center", fontSize: 14, color: "var(--dp-muted)" }}>
                <button className="dp-link" onClick={() => navigate("/")}>Sign in to your account</button>
            </div>
        </AuthLayout>
    );
}
