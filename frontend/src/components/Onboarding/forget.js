// frontend/src/components/Onboarding/forget.js
import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import AuthLayout from "./AuthLayout";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN;

// Step 1 — Enter email
function StepEmail({ onNext, onBack }) {
    const [email, setEmail] = useState("");
    const [error, setError] = useState("");
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
            setError(err.response?.data?.detail || "Failed to send OTP. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <div className="dp-form-head dp-center">
                <div className="dp-icon-badge">
                    <i className="bi bi-key" />
                </div>
                <h2>Forgot password</h2>
                <p>Enter your email and we'll send you a reset code</p>
            </div>

            {error && <div className="dp-alert dp-alert-error">{error}</div>}

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                    <label className="dp-label">Email address</label>
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

            <div className="dp-center dp-mt-3">
                <button className="dp-link-muted" onClick={onBack}>
                    &larr; Back to Login
                </button>
            </div>
        </>
    );
}

// Step 2 — Enter OTP
function StepOtp({ email, onNext, onBack }) {
    const [otp, setOtp] = useState(["", "", "", "", "", ""]);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [resending, setResending] = useState(false);
    const [timer, setTimer] = useState(60);
    const inputsRef = useRef([]);

    useState(() => {
        const t = setInterval(() => {
            setTimer(prev => {
                if (prev <= 1) { clearInterval(t); return 0; }
                return prev - 1;
            });
        }, 1000);
        return () => clearInterval(t);
    }, []);

    const handleChange = (value, index) => {
        if (!/^\d?$/.test(value)) return;
        const newOtp = [...otp];
        newOtp[index] = value;
        setOtp(newOtp);
        if (value && index < 5) inputsRef.current[index + 1]?.focus();
    };

    const handleKeyDown = (e, index) => {
        if (e.key === "Backspace" && !otp[index] && index > 0) {
            inputsRef.current[index - 1]?.focus();
        }
    };

    const handlePaste = (e) => {
        const pasted = e.clipboardData.getData("text").slice(0, 6).split("");
        if (pasted.every(c => /\d/.test(c))) {
            const newOtp = [...otp];
            pasted.forEach((d, i) => { newOtp[i] = d; });
            setOtp(newOtp);
            inputsRef.current[Math.min(pasted.length, 5)]?.focus();
        }
    };

    const handleVerify = async () => {
        setError("");
        const code = otp.join("");
        if (code.length !== 6) { setError("Please enter the complete 6-digit OTP"); return; }

        setLoading(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/verify-forgot-otp`, {
                email,
                otp_code: code
            });
            onNext(code);
        } catch (err) {
            setError(err.response?.data?.detail || "Invalid OTP. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleResend = async () => {
        setResending(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/forgot-password`, { email });
            setTimer(60);
            setOtp(["", "", "", "", "", ""]);
            inputsRef.current[0]?.focus();
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to resend OTP.");
        } finally {
            setResending(false);
        }
    };

    return (
        <>
            <div className="dp-form-head dp-center">
                <div className="dp-icon-badge">
                    <i className="bi bi-shield-lock" />
                </div>
                <h2>Enter reset code</h2>
                <p>We sent a 6-digit code to <strong>{email}</strong></p>
            </div>

            {error && <div className="dp-alert dp-alert-error">{error}</div>}

            <div className="dp-otp-row" onPaste={handlePaste}>
                {otp.map((digit, i) => (
                    <input
                        key={i}
                        ref={el => inputsRef.current[i] = el}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        className="dp-otp-input"
                        value={digit}
                        onChange={(e) => handleChange(e.target.value, i)}
                        onKeyDown={(e) => handleKeyDown(e, i)}
                    />
                ))}
            </div>

            <button className="dp-btn dp-btn-primary" onClick={handleVerify} disabled={loading}>
                {loading ? <><div className="dp-spin" /> Verifying...</> : "Verify Code"}
            </button>

            <div className="dp-center dp-mt-3">
                {timer > 0 ? (
                    <p style={{ fontSize: 13, color: "var(--dp-muted)", margin: 0 }}>
                        Resend code in <strong>{timer}s</strong>
                    </p>
                ) : (
                    <button className="dp-link" onClick={handleResend} disabled={resending}>
                        {resending ? "Sending..." : "Resend code"}
                    </button>
                )}
            </div>

            <div className="dp-center dp-mt-3">
                <button className="dp-link-muted" onClick={onBack}>
                    &larr; Go Back
                </button>
            </div>
        </>
    );
}

// Step 3 — Set new password
function StepReset({ email, otpCode, onSuccess, onBack }) {
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [showPass, setShowPass] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");

        if (password.length < 6) {
            setError("Password must be at least 6 characters.");
            return;
        }
        if (password !== confirmPassword) {
            setError("Passwords do not match.");
            return;
        }

        setLoading(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/reset-password`, {
                email,
                otp_code: otpCode,
                new_password: password
            });
            onSuccess();
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to reset password. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <div className="dp-form-head dp-center">
                <div className="dp-icon-badge">
                    <i className="bi bi-lock" />
                </div>
                <h2>Set new password</h2>
                <p>Choose a strong password for your account</p>
            </div>

            {error && <div className="dp-alert dp-alert-error">{error}</div>}

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                    <label className="dp-label">New password</label>
                    <div className="dp-pass-wrap">
                        <input
                            type={showPass ? "text" : "password"}
                            className="dp-input"
                            placeholder="Min. 6 characters"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                        <button type="button" className="dp-eye-btn" onClick={() => setShowPass(!showPass)} tabIndex={-1}>
                            {showPass ? "●" : "○"}
                        </button>
                    </div>
                </div>

                <div>
                    <label className="dp-label">Confirm password</label>
                    <div className="dp-pass-wrap">
                        <input
                            type={showConfirm ? "text" : "password"}
                            className="dp-input"
                            placeholder="Re-enter password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                        />
                        <button type="button" className="dp-eye-btn" onClick={() => setShowConfirm(!showConfirm)} tabIndex={-1}>
                            {showConfirm ? "●" : "○"}
                        </button>
                    </div>
                </div>

                <button type="submit" className="dp-btn dp-btn-primary" disabled={loading}>
                    {loading ? <><div className="dp-spin" /> Resetting...</> : "Reset Password"}
                </button>
            </form>

            <div className="dp-center dp-mt-3">
                <button className="dp-link-muted" onClick={onBack}>
                    &larr; Go Back
                </button>
            </div>
        </>
    );
}

// Step 4 — Success
function StepSuccess({ navigate }) {
    return (
        <div className="dp-center">
            <div className="dp-icon-badge" style={{ width: 64, height: 64, fontSize: 26 }}>
                <i className="bi bi-check-lg" />
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 8px 0" }}>Password reset</h2>
            <p style={{ fontSize: 14, color: "var(--dp-muted)", marginBottom: 22, lineHeight: 1.5 }}>
                Your password has been reset successfully.<br />
                You can now sign in with your new password.
            </p>
            <button className="dp-btn dp-btn-primary" onClick={() => navigate("/")}>
                Go to Login
            </button>
        </div>
    );
}

// Main Forget component — controls steps
export default function Forget() {
    const navigate = useNavigate();
    const [step, setStep] = useState(1); // 1=email, 2=otp, 3=reset, 4=success
    const [email, setEmail] = useState("");
    const [otpCode, setOtpCode] = useState("");

    return (
        <AuthLayout page="forgot">
            {step < 4 && (
                <div className="dp-progress-dots">
                    {[1, 2, 3].map(s => (
                        <span key={s} className={s <= step ? "active" : ""} />
                    ))}
                </div>
            )}

            {step === 1 && (
                <StepEmail
                    onNext={(e) => { setEmail(e); setStep(2); }}
                    onBack={() => navigate("/")}
                />
            )}

            {step === 2 && (
                <StepOtp
                    email={email}
                    onNext={(code) => { setOtpCode(code); setStep(3); }}
                    onBack={() => setStep(1)}
                />
            )}

            {step === 3 && (
                <StepReset
                    email={email}
                    otpCode={otpCode}
                    onSuccess={() => setStep(4)}
                    onBack={() => setStep(2)}
                />
            )}

            {step === 4 && (
                <StepSuccess navigate={navigate} />
            )}
        </AuthLayout>
    );
}