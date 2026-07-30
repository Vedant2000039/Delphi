// frontend/src/components/Onboarding/Login.js
import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import AuthLayout from "./AuthLayout";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN;

function Login() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [showPass, setShowPass] = useState(false);
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        setError("");

        if (!email || !password) {
            setError("Email and password are required");
            return;
        }

        // Static Super Admin Bypass
        if (email === "admin@xtsworld.in" && password === "xts@123") {
            localStorage.setItem("user", JSON.stringify({
                email: "superadmin@xdbs.in",
                full_name: "Sameer Datta",
                role_name: "super_admin",
                user_id: 0,
                role_id: 0
            }));
            navigate("/Intelligence", { replace: true });
            return;
        }

        setLoading(true);
        try {
            const res = await axios.post(`${API_BASE_URL}/auth/login`, {
                email,
                password
            });

            const user = res.data.user;
            localStorage.setItem("user", JSON.stringify(user));

            switch (user.role_name) {
                case "Admin":
                    navigate("/Intelligence", { replace: true });
                    break;
                default:
                    navigate("/Intelligence", { replace: true });
            }

        } catch (err) {
            const msg = err.response?.data?.detail || "Invalid email or password";
            if (msg.includes("not verified")) {
                navigate("/Otp", { state: { email } });
            } else {
                setError(msg);
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthLayout page="login">
            <div className="dp-form-head">
                <h2>Welcome back</h2>
                <p>Sign in to your Delphi workspace</p>
            </div>

            {error && <div className="dp-alert dp-alert-error">{error}</div>}

            <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                    <label className="dp-label">Email</label>
                    <input
                        type="email"
                        className="dp-input"
                        placeholder="you@company.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                </div>

                <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                        <label className="dp-label" style={{ marginBottom: 0 }}>Password</label>
                        <button
                            type="button"
                            className="dp-link"
                            style={{ fontSize: 12.5 }}
                            onClick={() => navigate("/Forget")}
                        >
                            Forgot password?
                        </button>
                    </div>
                    <div className="dp-pass-wrap">
                        <input
                            type={showPass ? "text" : "password"}
                            className="dp-input"
                            placeholder="Enter your password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                        <button
                            type="button"
                            className="dp-eye-btn"
                            onClick={() => setShowPass(!showPass)}
                            tabIndex={-1}
                        >
                            {showPass ? "●" : "○"}
                        </button>
                    </div>
                </div>

                <button type="submit" className="dp-btn dp-btn-primary" disabled={loading} style={{ marginTop: 4 }}>
                    {loading ? <><div className="dp-spin" /> Signing in...</> : "Sign In"}
                </button>
            </form>

            <div className="dp-divider">new to delphi?</div>

            <div style={{ textAlign: "center", fontSize: 14, color: "var(--dp-muted)" }}>
                <button className="dp-link" onClick={() => navigate("/Onboarding")}>
                    Create an account
                </button>
            </div>
        </AuthLayout>
    );
}

export default Login;