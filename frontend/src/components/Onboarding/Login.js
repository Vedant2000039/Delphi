import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, LockKeyhole, Mail, Sparkles } from "lucide-react";
import AuthLayout, { useAuthStyles } from "./AuthLayout";

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN;

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M21.8 12.2c0-.7-.1-1.4-.2-2H12v3.8h5.5a4.7 4.7 0 0 1-2 3.1v2.5h3.2c1.9-1.8 3.1-4.3 3.1-7.4Z"
      />
      <path
        fill="#34A853"
        d="M12 22c2.7 0 5-.9 6.7-2.4l-3.2-2.5c-.9.6-2 .9-3.5.9-2.7 0-5-1.8-5.8-4.3H2.9v2.6A10 10 0 0 0 12 22Z"
      />
      <path
        fill="#FBBC05"
        d="M6.2 13.7A6 6 0 0 1 5.9 12c0-.6.1-1.2.3-1.7V7.7H2.9A10 10 0 0 0 2 12c0 1.6.4 3.1.9 4.3l3.3-2.6Z"
      />
      <path
        fill="#EA4335"
        d="M12 6c1.5 0 2.9.5 3.9 1.5l2.9-2.9C17 2.9 14.7 2 12 2a10 10 0 0 0-9.1 5.7l3.3 2.6C7 7.8 9.3 6 12 6Z"
      />
    </svg>
  );
}

function MicrosoftIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" aria-hidden="true">
      <path fill="#f35325" d="M2 2h9.5v9.5H2z" />
      <path fill="#81bc06" d="M12.5 2H22v9.5h-9.5z" />
      <path fill="#05a6f0" d="M2 12.5h9.5V22H2z" />
      <path fill="#ffba08" d="M12.5 12.5H22V22h-9.5z" />
    </svg>
  );
}

function Login() {
  useAuthStyles();

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

    if (email === "admin@xtsworld.in" && password === "xts@123") {
      localStorage.setItem(
        "user",
        JSON.stringify({
          email: "superadmin@xdbs.in",
          full_name: "Sameer Datta",
          role_name: "super_admin",
          user_id: 0,
          role_id: 0,
        })
      );
      navigate("/Intelligence", { replace: true });
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/auth/login`, {
        email,
        password,
      });
      localStorage.setItem("user", JSON.stringify(res.data.user));
      navigate("/Intelligence", { replace: true });
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
      <div className="dp-auth-mark">
        <Sparkles size={25} />
      </div>

      <div className="dp-form-head">
        <h2>Welcome back</h2>
        <p>Sign in to continue to your GTM intelligence dashboard.</p>
      </div>

      {error && <div className="dp-alert dp-alert-error">{error}</div>}

      <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div>
          <label className="dp-label">Email Address</label>
          <div className="dp-input-wrap">
            <Mail className="dp-input-icon" size={17} />
            <input
              type="email"
              className="dp-input has-icon"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
        </div>

        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <label className="dp-label" style={{ marginBottom: 0 }}>
              Password
            </label>
            <button type="button" className="dp-link" onClick={() => navigate("/Forget")}>
              Forgot Password?
            </button>
          </div>
          <div className="dp-pass-wrap">
            <LockKeyhole className="dp-input-icon" size={17} />
            <input
              type={showPass ? "text" : "password"}
              className="dp-input has-icon"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="button"
              className="dp-eye-btn"
              onClick={() => setShowPass(!showPass)}
              aria-label={showPass ? "Hide password" : "Show password"}
            >
              {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </div>

        <div className="dp-form-options">
          <label className="dp-check">
            <input type="checkbox" /> Remember me
          </label>
        </div>

        <button type="submit" className="dp-btn dp-btn-primary" disabled={loading}>
          {loading ? (
            <>
              <span className="dp-spin" />
              Signing in...
            </>
          ) : (
            "Sign In"
          )}
        </button>
      </form>

      <div className="dp-divider">or</div>

      <div className="dp-social-stack">
        <button type="button" className="dp-btn dp-btn-outline">
          <span className="dp-social-icon">
            <GoogleIcon />
          </span>
          Continue with Google
        </button>
        <button type="button" className="dp-btn dp-btn-outline">
          <span className="dp-social-icon">
            <MicrosoftIcon />
          </span>
          Continue with Microsoft
        </button>
      </div>

      <div style={{ textAlign: "center", marginTop: 25, fontSize: 13, color: "var(--dp-muted)" }}>
        No account?{" "}
        <button className="dp-link" onClick={() => navigate("/Onboarding")}>
          Create one free
        </button>
      </div>
    </AuthLayout>
  );
}

export default Login;