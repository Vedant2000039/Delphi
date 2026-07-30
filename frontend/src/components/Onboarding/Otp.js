// frontend/src/components/Onboarding/Otp.js
import { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import AuthLayout from "./AuthLayout";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN;

export default function Otp() {
    const navigate = useNavigate();
    const location = useLocation();
    const email = location.state?.email || "";

    const [otp, setOtp] = useState(["", "", "", "", "", ""]);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [loading, setLoading] = useState(false);
    const [resending, setResending] = useState(false);
    const [timer, setTimer] = useState(60);

    const inputsRef = useRef([]);

    // Countdown for resend button
    useEffect(() => {
        if (timer <= 0) return;
        const t = setTimeout(() => setTimer(timer - 1), 1000);
        return () => clearTimeout(t);
    }, [timer]);

    // Guard — must have email from Register page
    useEffect(() => {
        if (!email) navigate("/Onboarding");
    }, [email, navigate]);

    const handleChange = (value, index) => {
        if (!/^\d?$/.test(value)) return;
        const newOtp = [...otp];
        newOtp[index] = value;
        setOtp(newOtp);
        if (value && index < 5) inputsRef.current[index + 1]?.focus();
    };

    const handleKeyDown = (e, index) => {
        if (e.key === "Backspace" && !otp[index] && index > 0)
            inputsRef.current[index - 1]?.focus();
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
        if (code.length !== 6) {
            setError("Please enter the complete 6-digit OTP");
            return;
        }

        setLoading(true);
        try {
            // Step 1: Verify OTP
            await axios.post(`${API_BASE_URL}/auth/verify-otp`, {
                email,
                otp_code: code,
            });

            // Step 2: Fetch full user by email to get user_id
            let userData = {};
            try {
                const userRes = await axios.get(
                    `${API_BASE_URL}/auth/user-by-email?email=${encodeURIComponent(email)}`
                );
                userData = userRes.data.user;
            } catch {
                userData = { email };
            }

            // Step 3: Store in localStorage
            localStorage.setItem("user", JSON.stringify({
                user_id: userData.user_id || null,
                email: userData.email || email,
                full_name: userData.user_first_name
                    ? `${userData.user_first_name} ${userData.user_last_name}`
                    : "",
                role_name: userData.role_name || "User",
                company_name: userData.company_name || "",
            }));

            setSuccess("Email verified! Redirecting...");
            setTimeout(() => navigate("/Enrichment"), 1500);

        } catch (err) {
            const isOtpError = err.config?.url?.includes("verify-otp");
            if (isOtpError) {
                setError(err.response?.data?.detail || "Invalid or expired OTP. Please try again.");
            } else {
                setSuccess("Email verified! Redirecting...");
                setTimeout(() => navigate("/Enrichment"), 1500);
            }
        } finally {
            setLoading(false);
        }
    };

    const handleResend = async () => {
        setError("");
        setResending(true);
        try {
            await axios.post(`${API_BASE_URL}/auth/resend-otp`, { email });
            setTimer(60);
            setOtp(["", "", "", "", "", ""]);
            inputsRef.current[0]?.focus();
            setSuccess("New OTP sent to your email.");
            setTimeout(() => setSuccess(""), 3000);
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to resend OTP.");
        } finally {
            setResending(false);
        }
    };

    return (
        <AuthLayout page="otp">
            <div className="dp-form-head dp-center">
                <div className="dp-icon-badge">
                    <i className="bi bi-envelope-check" />
                </div>
                <h2>Verify your email</h2>
                <p>We sent a 6-digit code to <strong>{email}</strong></p>
            </div>

            {error && <div className="dp-alert dp-alert-error">{error}</div>}
            {success && <div className="dp-alert dp-alert-success">{success}</div>}

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
                {loading ? <><div className="dp-spin" /> Verifying...</> : "Verify OTP"}
            </button>

            <div className="dp-center dp-mt-3">
                {timer > 0 ? (
                    <p style={{ fontSize: 13, color: "var(--dp-muted)", margin: 0 }}>
                        Resend code in <strong>{timer}s</strong>
                    </p>
                ) : (
                    <button className="dp-link" onClick={handleResend} disabled={resending}>
                        {resending ? "Sending..." : "Resend OTP"}
                    </button>
                )}
            </div>

            <div className="dp-center dp-mt-3">
                <button className="dp-link-muted" onClick={() => navigate("/Onboarding")}>
                    Back to Register
                </button>
            </div>
        </AuthLayout>
    );
}