import { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import AuthLayout, { useAuthStyles } from "./AuthLayout";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN;

export default function Otp() {
    useAuthStyles();
    const navigate  = useNavigate();
    const location  = useLocation();
    const email     = location.state?.email || "";

    const [otp,       setOtp]       = useState(["", "", "", "", "", ""]);
    const [error,     setError]     = useState("");
    const [success,   setSuccess]   = useState("");
    const [loading,   setLoading]   = useState(false);
    const [resending, setResending] = useState(false);
    const [timer,     setTimer]     = useState(60);
    const inputsRef = useRef([]);

    useEffect(() => {
        if (!email) navigate("/Onboarding");
        else inputsRef.current[0]?.focus();
    }, [email, navigate]);

    useEffect(() => {
        if (timer <= 0) return;
        const t = setTimeout(() => setTimer(timer - 1), 1000);
        return () => clearTimeout(t);
    }, [timer]);

    const handleChange = (value, index) => {
        if (!/^\d?$/.test(value)) return;
        const next = [...otp]; next[index] = value; setOtp(next);
        if (value && index < 5) inputsRef.current[index + 1]?.focus();
    };
    const handleKeyDown = (e, index) => {
        if (e.key === "Backspace" && !otp[index] && index > 0)
            inputsRef.current[index - 1]?.focus();
    };
    const handlePaste = (e) => {
        const pasted = e.clipboardData.getData("text").slice(0, 6).split("");
        if (pasted.every(c => /\d/.test(c))) {
            const next = [...otp]; pasted.forEach((d, i) => { next[i] = d; }); setOtp(next);
            inputsRef.current[Math.min(pasted.length, 5)]?.focus();
        }
    };

    const handleVerify = async () => {
        setError("");
        const code = otp.join("");
        if (code.length !== 6) { setError("Please enter all 6 digits"); return; }
        setLoading(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/verify-otp`, { email, otp_code: code });
            let userData = {};
            try {
                const r = await axios.get(`${API_BASE_URL}/auth/user-by-email?email=${encodeURIComponent(email)}`);
                userData = r.data.user;
            } catch { userData = { email }; }
            localStorage.setItem("user", JSON.stringify({
                user_id:      userData.user_id      || null,
                email:        userData.email        || email,
                full_name:    userData.user_first_name ? `${userData.user_first_name} ${userData.user_last_name}` : "",
                role_name:    userData.role_name    || "User",
                company_name: userData.company_name || "",
            }));
            setSuccess("Verified! Redirecting...");
            setTimeout(() => navigate("/Enrichment"), 1500);
        } catch (err) {
            const isOtpErr = err.config?.url?.includes("verify-otp");
            if (isOtpErr) setError(err.response?.data?.detail || "Invalid or expired OTP.");
            else { setSuccess("Verified! Redirecting..."); setTimeout(() => navigate("/Enrichment"), 1500); }
        } finally { setLoading(false); }
    };

    const handleResend = async () => {
        setError(""); setResending(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/resend-otp`, { email });
            setTimer(60); setOtp(["", "", "", "", "", ""]);
            inputsRef.current[0]?.focus();
            setSuccess("New OTP sent."); setTimeout(() => setSuccess(""), 3000);
        } catch (err) { setError(err.response?.data?.detail || "Failed to resend."); }
        finally { setResending(false); }
    };

    return (
        <AuthLayout page="otp">
            <div className="dp-form-head" style={{ textAlign: "center" }}>
                <h2>Verify email</h2>
                <p>
                    6-digit code sent to{" "}
                    <span style={{ color: "var(--dp-cyan)", fontWeight: 500 }}>{email}</span>
                </p>
            </div>

            {error   && <div className="dp-alert dp-alert-error">{error}</div>}
            {success && <div className="dp-alert dp-alert-success">{success}</div>}

            <div className="dp-otp-row" onPaste={handlePaste}>
                {otp.map((digit, i) => (
                    <input
                        key={i}
                        ref={el => inputsRef.current[i] = el}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        className="dp-otp-cell"
                        value={digit}
                        onChange={(e) => handleChange(e.target.value, i)}
                        onKeyDown={(e) => handleKeyDown(e, i)}
                    />
                ))}
            </div>

            <button className="dp-btn dp-btn-primary" onClick={handleVerify} disabled={loading}>
                {loading ? <><div className="dp-spin" /> Verifying...</> : "Verify OTP"}
            </button>

            <div style={{ textAlign: "center", marginTop: 20, fontSize: 13.5, color: "var(--dp-muted)" }}>
                {timer > 0 ? (
                    <>Resend in <strong style={{ color: "var(--dp-text)" }}>{timer}s</strong></>
                ) : (
                    <button className="dp-link" onClick={handleResend} disabled={resending}>
                        {resending ? "Sending..." : "Resend OTP"}
                    </button>
                )}
            </div>

            <div style={{ textAlign: "center", marginTop: 14 }}>
                <button className="dp-link" style={{ color: "var(--dp-muted)", fontSize: 13 }} onClick={() => navigate("/Onboarding")}>
                    Back to Register
                </button>
            </div>
        </AuthLayout>
    );
}