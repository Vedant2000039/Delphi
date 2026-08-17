// frontend/src/components/Onboarding/AuthLayout.js
//
// Shared visual shell for the entire onboarding flow (Login, Register, OTP,
// Forgot Password, Company Enrichment). Gives every screen in the flow the
// same split layout, typography, spacing and color system so the experience
// reads as one continuous, professional product rather than five different
// screens that happen to be reachable from each other.
import { useEffect } from "react";

const FEATURES = [
    {
        title: "Unified lead intelligence",
        body: "One workspace for company, contact and intent data across every campaign.",
    },
    {
        title: "AI-guided targeting",
        body: "Delphi builds your ideal customer profile as you describe your business.",
    },
    {
        title: "Enterprise-grade security",
        body: "Your data is encrypted in transit and at rest, always.",
    },
];

const STEP_LABELS = {
    register: "Create account",
    otp: "Verify email",
    enrichment: "Company profile",
    extraction: "Detect",
    login: "Sign in",
    forgot: "Reset password",
};

const ONBOARDING_STEPS = ["register", "otp", "enrichment", "extraction"];

/**
 * AuthLayout — wraps every screen in the onboarding flow.
 *
 * @param {"login"|"register"|"otp"|"enrichment"|"forgot"} page
 * @param {React.ReactNode} children
 */
export default function AuthLayout({ page = "login", children }) {
    useAuthStyles();

    const stepIndex = ONBOARDING_STEPS.indexOf(page);
    const isOnboardingStep = stepIndex !== -1;

    return (
        <div className="dp-shell">
            {/* Left brand panel — hidden on small screens */}
            <div className="dp-panel">
                <div className="dp-panel-inner">
                    <div className="dp-brand">
                        <div className="dp-brand-mark">D</div>
                        <span className="dp-brand-name">DELPHI</span>
                    </div>

                    <h1 className="dp-panel-headline">
                        Delphi Intelligence,
                        <br />
                        Best for your product campaign.
                    </h1>
                    <p className="dp-panel-sub">
                        Set up your workspace in a few steps and start surfacing
                        qualified accounts today.
                    </p>

                    <ul className="dp-feature-list">
                        {FEATURES.map((f) => (
                            <li key={f.title}>
                                <span className="dp-feature-dot" />
                                <div>
                                    <div className="dp-feature-title">{f.title}</div>
                                    <div className="dp-feature-body">{f.body}</div>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="dp-panel-footer">
                    &copy; {new Date().getFullYear()} Delphi AI. All rights reserved.
                </div>
            </div>

            {/* Right content panel */}
            <div className="dp-content">
                <div className={`dp-content-inner${["enrichment", "extraction"].includes(page) ? " dp-content-inner-wide" : ""}`}>
                    {/* Mobile-only brand mark */}
                    <div className="dp-brand dp-brand-mobile">
                        <div className="dp-brand-mark">D</div>
                        <span className="dp-brand-name">DELPHI</span>
                    </div>

                    {isOnboardingStep && (
                        <div className="dp-steps">
                            {ONBOARDING_STEPS.map((step, i) => (
                                <div
                                    key={step}
                                    className={`dp-step${i === stepIndex ? " dp-step-active" : ""}${
                                        i < stepIndex ? " dp-step-done" : ""
                                    }`}
                                >
                                    <span className="dp-step-dot">
                                        {i < stepIndex ? "\u2713" : i + 1}
                                    </span>
                                    <span className="dp-step-label">{STEP_LABELS[step]}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="dp-card">{children}</div>
                </div>
            </div>
        </div>
    );
}

/**
 * useAuthStyles — injects the shared onboarding design-system stylesheet
 * into <head> exactly once, regardless of how many onboarding screens are
 * mounted. Keeps every screen visually identical without needing a bundler
 * CSS import per file.
 */
export function useAuthStyles() {
    useEffect(() => {
        if (document.getElementById("dp-auth-styles")) return;
        const style = document.createElement("style");
        style.id = "dp-auth-styles";
        style.textContent = AUTH_CSS;
        document.head.appendChild(style);
    }, []);
}

const AUTH_CSS = `
:root {
  --dp-primary: #4f46e5;
  --dp-primary-dark: #4338ca;
  --dp-primary-light: #eef2ff;
  --dp-ink: #111827;
  --dp-muted: #6b7280;
  --dp-border: #e5e7eb;
  --dp-border-soft: #f1f2f4;
  --dp-danger: #b91c1c;
  --dp-danger-bg: #fef2f2;
  --dp-danger-border: #fecaca;
  --dp-success: #15803d;
  --dp-success-bg: #f0fdf4;
  --dp-success-border: #bbf7d0;
  --dp-warning: #b45309;
  --dp-warning-bg: #fffbeb;
  --dp-warning-border: #fde68a;
  --dp-radius: 14px;
  --dp-font: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.dp-shell {
  min-height: 100vh;
  display: flex;
  font-family: var(--dp-font);
  background: #ffffff;
  color: var(--dp-ink);
}

/* Left brand panel */
.dp-panel {
  flex: 0 0 42%;
  max-width: 560px;
  background: linear-gradient(160deg, #1e1b4b 0%, #312e81 45%, #4338ca 100%);
  color: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 48px 56px;
}

.dp-panel-inner { display: flex; flex-direction: column; gap: 32px; }

.dp-brand { display: flex; align-items: center; gap: 10px; }

.dp-brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 15px;
  letter-spacing: 0.5px;
}

.dp-brand-name {
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 3px;
  color: #ffffff;
}

.dp-brand-mobile { display: none; margin-bottom: 28px; }
.dp-brand-mobile .dp-brand-mark { background: var(--dp-primary-light); color: var(--dp-primary); border: none; }
.dp-brand-mobile .dp-brand-name { color: var(--dp-ink); }

.dp-panel-headline {
  font-size: 30px;
  font-weight: 700;
  line-height: 1.3;
  margin: 0;
  letter-spacing: -0.3px;
}

.dp-panel-sub {
  font-size: 15px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.75);
  margin: 0;
  max-width: 400px;
}

.dp-feature-list {
  list-style: none;
  margin: 8px 0 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dp-feature-list li {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.dp-feature-dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: #a5b4fc;
  flex-shrink: 0;
}

.dp-feature-title { font-size: 14px; font-weight: 600; color: #ffffff; }
.dp-feature-body { font-size: 13px; color: rgba(255, 255, 255, 0.65); line-height: 1.5; margin-top: 2px; }

.dp-panel-footer {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

/* Right content panel */
.dp-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  background: #fafafb;
}

.dp-content-inner { width: 100%; max-width: 440px; }
.dp-content-inner-wide { max-width: 720px; }

/* Onboarding step tracker */
.dp-steps {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 28px;
}

.dp-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: #b0b4bb;
}

.dp-step:not(:last-child)::after {
  content: "";
  width: 20px;
  height: 1px;
  background: var(--dp-border);
  margin: 0 2px;
}

.dp-step-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--dp-border-soft);
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11.5px;
  font-weight: 700;
}

.dp-step-active { color: var(--dp-ink); }
.dp-step-active .dp-step-dot { background: var(--dp-primary-light); color: var(--dp-primary); box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12); }
.dp-step-done .dp-step-dot { background: var(--dp-primary); color: #fff; }
.dp-step-label { display: none; }
@media (min-width: 860px) { .dp-step-label { display: inline; } }

/* Card */
.dp-card {
  background: #ffffff;
  border: 1px solid var(--dp-border-soft);
  border-radius: var(--dp-radius);
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.05);
  padding: 36px;
  animation: dp-fade-in 0.25s ease;
}

@keyframes dp-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.dp-form-head { margin-bottom: 24px; }
.dp-form-head h2 { font-size: 22px; font-weight: 700; color: var(--dp-ink); margin: 0 0 6px 0; }
.dp-form-head p { font-size: 14px; color: var(--dp-muted); margin: 0; line-height: 1.5; }

/* Alerts */
.dp-alert {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  border-radius: 10px;
  padding: 11px 13px;
  font-size: 13.5px;
  margin-bottom: 18px;
  line-height: 1.4;
}
.dp-alert-error   { background: var(--dp-danger-bg);  border: 1px solid var(--dp-danger-border);  color: var(--dp-danger); }
.dp-alert-success { background: var(--dp-success-bg); border: 1px solid var(--dp-success-border); color: var(--dp-success); }
.dp-alert-warning { background: var(--dp-warning-bg); border: 1px solid var(--dp-warning-border); color: var(--dp-warning); }

/* Fields */
.dp-label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; }

.dp-input {
  width: 100%;
  font-family: var(--dp-font);
  font-size: 14px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1.5px solid var(--dp-border);
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  background: #ffffff;
  color: var(--dp-ink);
  box-sizing: border-box;
}
.dp-input::placeholder { color: #9ca3af; }
.dp-input:focus { border-color: var(--dp-primary); box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1); }
.dp-input.err { border-color: #fca5a5; }

.dp-field-error { font-size: 12px; color: var(--dp-danger); margin-top: 5px; }

.dp-pass-wrap { position: relative; display: flex; align-items: center; }
.dp-pass-wrap .dp-input { padding-right: 40px; }
.dp-eye-btn {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  cursor: pointer;
  color: #9ca3af;
  font-size: 15px;
  line-height: 1;
  padding: 4px;
}
.dp-eye-btn:hover { color: var(--dp-muted); }

/* Buttons */
.dp-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  font-family: var(--dp-font);
  font-size: 14px;
  font-weight: 600;
  padding: 11px 20px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease;
  box-sizing: border-box;
}
.dp-btn:disabled { opacity: 0.55; cursor: not-allowed; }

.dp-btn-primary { background: var(--dp-primary); color: #ffffff; }
.dp-btn-primary:hover:not(:disabled) { background: var(--dp-primary-dark); }

.dp-btn-secondary { background: #ffffff; color: #374151; border: 1.5px solid var(--dp-border); }
.dp-btn-secondary:hover:not(:disabled) { background: #f9fafb; }

.dp-btn-row { display: flex; gap: 10px; }
.dp-btn-row .dp-btn { width: auto; flex: 1; }

.dp-spin {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #ffffff;
  animation: dp-spin 0.7s linear infinite;
  display: inline-block;
}
@keyframes dp-spin { to { transform: rotate(360deg); } }

.dp-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 22px 0 16px 0;
  font-size: 12px;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.dp-divider::before, .dp-divider::after { content: ""; flex: 1; height: 1px; background: var(--dp-border-soft); }

.dp-link { background: none; border: none; color: var(--dp-primary); font-weight: 600; font-size: 13.5px; cursor: pointer; padding: 0; }
.dp-link:hover { color: var(--dp-primary-dark); text-decoration: underline; }
.dp-link-muted { background: none; border: none; color: var(--dp-muted); font-weight: 500; font-size: 13px; cursor: pointer; padding: 0; }
.dp-link-muted:hover { color: #374151; }

/* OTP digit inputs */
.dp-otp-row { display: flex; justify-content: center; gap: 10px; margin: 22px 0; }
.dp-otp-input {
  width: 46px;
  height: 54px;
  text-align: center;
  font-size: 20px;
  font-weight: 700;
  border-radius: 10px;
  border: 1.5px solid var(--dp-border);
  outline: none;
  color: var(--dp-ink);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.dp-otp-input:focus { border-color: var(--dp-primary); box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1); }

/* Icon badge used at the top of single-purpose cards (OTP / reset / success) */
.dp-icon-badge {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px auto;
  background: var(--dp-primary-light);
  color: var(--dp-primary);
  font-size: 22px;
}

.dp-center { text-align: center; }
.dp-mt-3 { margin-top: 14px; }
.dp-mt-4 { margin-top: 20px; }

/* Progress dots (Forgot Password flow) */
.dp-progress-dots { display: flex; justify-content: center; gap: 8px; margin-bottom: 24px; }
.dp-progress-dots span {
  width: 30px;
  height: 4px;
  border-radius: 2px;
  background: var(--dp-border-soft);
}
.dp-progress-dots span.active { background: var(--dp-primary); }

@media (max-width: 900px) {
  .dp-panel { display: none; }
  .dp-brand-mobile { display: flex; }
  .dp-content { padding: 32px 20px; background: #ffffff; }
}

@media (max-width: 480px) {
  .dp-card { padding: 26px 20px; }
  .dp-otp-input { width: 40px; height: 48px; font-size: 18px; }
}
`;