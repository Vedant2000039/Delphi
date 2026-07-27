import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import AuthLayout, { useAuthStyles } from "./AuthLayout";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN;

// ── Step 1 ────────────────────────────────────────────────────────────────────
function StepEmail({ onNext }) {
    const [email,   setEmail]   = useState("");
    const [error,   setError]   = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        if (!email) { setError("Email is required"); return; }
        setLoading(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/forgot-password`, { email });
            onNext(email);
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to send code. Please try again.");
        } finally { setLoading(false); }
    };

    return (
        <>
            <div className="dp-form-head">
                <h2>Forgot password?</h2>
                <p>Enter your registered email and we'll send a reset code</p>
            </div>
            {error && <div className="dp-alert dp-alert-error">{error}</div>}
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <div>
                    <label className="dp-label">Email Address</label>
                    <input
                        type="email"
                        className="dp-input"
                        placeholder="Enter your registered email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                </div>
                <button type="submit" className="dp-btn dp-btn-primary" disabled={loading}>
                    {loading ? <><div className="dp-spin" /> Sending...</> : "Send Reset Code"}
                </button>
            </form>
        </>
    );
}

// ── Step 2 ────────────────────────────────────────────────────────────────────
function StepOtp({ email, onNext }) {
    const [otp,       setOtp]       = useState(["", "", "", "", "", ""]);
    const [error,     setError]     = useState("");
    const [loading,   setLoading]   = useState(false);
    const [resending, setResending] = useState(false);
    const [timer,     setTimer]     = useState(60);
    const inputsRef = useRef([]);

    useState(() => {
        const t = setInterval(() => setTimer(p => { if (p <= 1) { clearInterval(t); return 0; } return p - 1; }), 1000);
        return () => clearInterval(t);
    }, []);

    const handleChange = (value, index) => {
        if (!/^\d?$/.test(value)) return;
        const next = [...otp]; next[index] = value; setOtp(next);
        if (value && index < 5) inputsRef.current[index + 1]?.focus();
    };
    const handleKeyDown = (e, index) => {
        if (e.key === "Backspace" && !otp[index] && index > 0) inputsRef.current[index - 1]?.focus();
    };
    const handlePaste = (e) => {
        const p = e.clipboardData.getData("text").slice(0, 6).split("");
        if (p.every(c => /\d/.test(c))) {
            const next = [...otp]; p.forEach((d, i) => { next[i] = d; }); setOtp(next);
            inputsRef.current[Math.min(p.length, 5)]?.focus();
        }
    };
    const handleVerify = async () => {
        setError("");
        const code = otp.join("");
        if (code.length !== 6) { setError("Please enter all 6 digits"); return; }
        setLoading(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/verify-forgot-otp`, { email, otp_code: code });
            onNext(code);
        } catch (err) { setError(err.response?.data?.detail || "Invalid code."); }
        finally { setLoading(false); }
    };
    const handleResend = async () => {
        setResending(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/forgot-password`, { email });
            setTimer(60); setOtp(["", "", "", "", "", ""]); inputsRef.current[0]?.focus();
        } catch (err) { setError(err.response?.data?.detail || "Failed to resend."); }
        finally { setResending(false); }
    };

    return (
        <>
            <div className="dp-form-head" style={{ textAlign: "center" }}>
                <h2>Enter reset code</h2>
                <p>Sent to <span style={{ color: "var(--dp-cyan)", fontWeight: 500 }}>{email}</span></p>
            </div>
            {error && <div className="dp-alert dp-alert-error">{error}</div>}
            <div className="dp-otp-row" onPaste={handlePaste}>
                {otp.map((digit, i) => (
                    <input key={i} ref={el => inputsRef.current[i] = el}
                        type="text" inputMode="numeric" maxLength={1}
                        className="dp-otp-cell" value={digit}
                        onChange={(e) => handleChange(e.target.value, i)}
                        onKeyDown={(e) => handleKeyDown(e, i)}
                    />
                ))}
            </div>
            <button className="dp-btn dp-btn-primary" onClick={handleVerify} disabled={loading}>
                {loading ? <><div className="dp-spin" /> Verifying...</> : "Verify Code"}
            </button>
            <div style={{ textAlign: "center", marginTop: 18, fontSize: 13.5, color: "var(--dp-muted)" }}>
                {timer > 0
                    ? <>Resend in <strong style={{ color: "var(--dp-text)" }}>{timer}s</strong></>
                    : <button className="dp-link" onClick={handleResend} disabled={resending}>{resending ? "Sending..." : "Resend code"}</button>
                }
            </div>
        </>
    );
}

// ── Step 3 ────────────────────────────────────────────────────────────────────
function StepReset({ email, otpCode, onSuccess }) {
    const [password,     setPassword]     = useState("");
    const [confirmPwd,   setConfirmPwd]   = useState("");
    const [error,        setError]        = useState("");
    const [loading,      setLoading]      = useState(false);
    const [showPass,     setShowPass]     = useState(false);
    const [showConfirm,  setShowConfirm]  = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        if (password.length < 6) { setError("Minimum 6 characters"); return; }
        if (password !== confirmPwd) { setError("Passwords do not match"); return; }
        setLoading(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/reset-password`, { email, otp_code: otpCode, new_password: password });
            onSuccess();
        } catch (err) { setError(err.response?.data?.detail || "Reset failed. Please try again."); }
        finally { setLoading(false); }
    };

    return (
        <>
            <div className="dp-form-head">
                <h2>Set new password</h2>
                <p>Choose a strong password for your account</p>
            </div>
            {error && <div className="dp-alert dp-alert-error">{error}</div>}
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <div>
                    <label className="dp-label">New Password</label>
                    <div className="dp-pass-wrap">
                        <input type={showPass ? "text" : "password"} className="dp-input"
                            placeholder="Min. 6 characters" value={password}
                            onChange={(e) => setPassword(e.target.value)} required />
                        <button type="button" className="dp-eye-btn" onClick={() => setShowPass(!showPass)} tabIndex={-1}>
                            {showPass ? "●" : "○"}
                        </button>
                    </div>
                </div>
                <div>
                    <label className="dp-label">Confirm Password</label>
                    <div className="dp-pass-wrap">
                        <input type={showConfirm ? "text" : "password"} className="dp-input"
                            placeholder="Re-enter password" value={confirmPwd}
                            onChange={(e) => setConfirmPwd(e.target.value)} required />
                        <button type="button" className="dp-eye-btn" onClick={() => setShowConfirm(!showConfirm)} tabIndex={-1}>
                            {showConfirm ? "●" : "○"}
                        </button>
                    </div>
                </div>
                <button type="submit" className="dp-btn dp-btn-primary" disabled={loading} style={{ marginTop: 4 }}>
                    {loading ? <><div className="dp-spin" /> Resetting...</> : "Reset Password"}
                </button>
            </form>
        </>
    );
}

// ── Step 4 ────────────────────────────────────────────────────────────────────
function StepSuccess({ navigate }) {
    return (
        <div style={{ textAlign: "center", padding: "20px 0" }}>
            <div style={{
                width: 72, height: 72, borderRadius: "50%",
                background: "rgba(104,211,145,0.1)",
                border: "1px solid rgba(104,211,145,0.3)",
                display: "flex", alignItems: "center", justifyContent: "center",
                margin: "0 auto 20px",
                fontFamily: "var(--f-display)", fontSize: 32, fontWeight: 900,
                color: "var(--dp-success)",
            }}>✓</div>
            <h2 style={{ fontFamily: "var(--f-display)", fontSize: 28, fontWeight: 900, color: "var(--dp-text)", marginBottom: 8 }}>
                Password reset!
            </h2>
            <p style={{ fontSize: 14, color: "var(--dp-muted)", marginBottom: 32, lineHeight: 1.6 }}>
                Your password has been reset successfully.<br />Sign in with your new credentials.
            </p>
            <button className="dp-btn dp-btn-primary" onClick={() => navigate("/")}>
                Go to Sign In
            </button>
        </div>
    );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function Forget() {
    useAuthStyles();
    const navigate = useNavigate();
    const [step,    setStep]    = useState(1);
    const [email,   setEmail]   = useState("");
    const [otpCode, setOtpCode] = useState("");

    return (
        <AuthLayout page="forgot">
            {step < 4 && (
                <div className="dp-step-dots" style={{ marginBottom: 30 }}>
                    {[1, 2, 3].map(s => (
                        <div key={s} className={`dp-dot ${s < step ? "dp-dot-done" : s === step ? "dp-dot-active" : "dp-dot-pending"}`} />
                    ))}
                </div>
            )}

            {step === 1 && <StepEmail onNext={(e) => { setEmail(e); setStep(2); }} />}
            {step === 2 && <StepOtp email={email} onNext={(code) => { setOtpCode(code); setStep(3); }} />}
            {step === 3 && <StepReset email={email} otpCode={otpCode} onSuccess={() => setStep(4)} />}
            {step === 4 && <StepSuccess navigate={navigate} />}

            {step < 4 && (
                <div style={{ textAlign: "center", marginTop: 24 }}>
                    <button className="dp-link" style={{ color: "var(--dp-muted)", fontSize: 13 }}
                        onClick={() => step === 1 ? navigate("/") : setStep(step - 1)}>
                        {step === 1 ? "Back to Sign In" : "Go back"}
                    </button>
                </div>
            )}
        </AuthLayout>
    );
}