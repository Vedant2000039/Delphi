import { useEffect, useRef } from "react";
import { BrainCircuit, BellRing, Building2, Sparkles } from "lucide-react";

const GLOBAL_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* {
  box-sizing: border-box;
}

:root {
  --dp-primary: #5b5ceb;
  --dp-secondary: #7c3aed;
  --dp-green: #22c55e;
  --dp-text: #111827;
  --dp-muted: #64748b;
  --dp-border: #e5e7eb;
  --dp-bg: #f8fafc;
  --dp-surface: #fff;
  --f-body: Inter, ui-sans-serif, system-ui, sans-serif;
}

html, body, #root {
  min-height: 100%;
}

body {
  margin: 0;
}

/* Layout shell */
.dp-root {
  display: flex;
  min-height: 100vh;
  background: var(--dp-bg);
  color: var(--dp-text);
  font-family: var(--f-body);
}

/* Left brand panel */
.dp-brand {
  position: relative;
  flex: 0 0 52%;
  min-height: 100vh;
  overflow: hidden;
  padding: 48px clamp(42px, 5.2vw, 76px) 38px;
  background: linear-gradient(135deg, #f8faff 0%, #f7f8ff 46%, #f8fbfa 100%);
  display: flex;
  flex-direction: column;
}

.dp-brand-noise {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 13% 17%, rgba(124, 58, 237, .13), transparent 24%),
    radial-gradient(circle at 81% 13%, rgba(91, 92, 235, .12), transparent 28%),
    radial-gradient(circle at 70% 83%, rgba(34, 197, 94, .10), transparent 31%);
}

.dp-brand-lines {
  position: absolute;
  width: 380px;
  height: 380px;
  right: -130px;
  top: 220px;
  opacity: .38;
  background-image: radial-gradient(rgba(91, 92, 235, .32) 1.1px, transparent 1.1px);
  background-size: 14px 14px;
  mask-image: radial-gradient(circle, black 12%, transparent 70%);
}

.dp-brand-stripe {
  position: absolute;
  width: 320px;
  height: 320px;
  left: -200px;
  bottom: -210px;
  border: 1px solid rgba(91, 92, 235, .14);
  border-radius: 50%;
  box-shadow:
    0 0 0 34px rgba(91, 92, 235, .035),
    0 0 0 70px rgba(34, 197, 94, .025);
}

.dp-brand-inner,
.dp-brand-meta {
  position: relative;
  z-index: 1;
}

/* Logo */
.dp-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 76px;
  font-size: 22px;
  line-height: 1;
  font-weight: 800;
  letter-spacing: -.06em;
}

.dp-logo-mark,
.dp-auth-mark {
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #6d5df4, #7c3aed);
  color: #fff;
  box-shadow: 0 10px 24px rgba(91, 92, 235, .25);
}

.dp-logo-mark {
  width: 32px;
  height: 32px;
  border-radius: 10px;
}

.dp-logo-delphi {
  letter-spacing: -.05em;
}

.dp-logo-dot {
  color: var(--dp-primary);
  font-size: 27px;
  line-height: 0;
  margin-left: -8px;
  margin-top: -8px;
}

/* Tagline chip */
.dp-tagline-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  width: max-content;
  padding: 7px 11px;
  margin-bottom: 20px;
  border: 1px solid rgba(34, 197, 94, .22);
  border-radius: 999px;
  color: #168a42;
  background: rgba(240, 253, 244, .82);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .09em;
}

.dp-tagline-chip::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--dp-green);
  box-shadow: 0 0 0 4px rgba(34, 197, 94, .12);
}

/* Headline / copy */
.dp-headline {
  max-width: 620px;
  margin: 0 0 20px;
  font-size: clamp(44px, 4.1vw, 64px);
  letter-spacing: -.06em;
  line-height: 1.04;
  font-weight: 800;
}

.dp-headline em {
  font-style: normal;
  background: linear-gradient(100deg, #4f72f0, #7c3aed);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.dp-desc {
  max-width: 595px;
  margin: 0 0 31px;
  color: var(--dp-muted);
  font-size: 15px;
  line-height: 1.72;
}

/* Feature cards */
.dp-features {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  max-width: 690px;
}

.dp-feat {
  min-height: 168px;
  padding: 16px;
  border: 1px solid rgba(229, 231, 235, .92);
  border-radius: 16px;
  background: rgba(255, 255, 255, .76);
  box-shadow: 0 10px 28px rgba(15, 23, 42, .045);
}

.dp-feat-line {
  display: none;
}

.dp-feature-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  margin-bottom: 14px;
  border-radius: 10px;
}

.dp-feature-icon.purple {
  color: #7c3aed;
  background: #f3e8ff;
}

.dp-feature-icon.blue {
  color: #4f73ea;
  background: #eaf0ff;
}

.dp-feature-icon.green {
  color: #169b4b;
  background: #e8faee;
}

.dp-feat-title {
  margin-bottom: 7px;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.3;
}

.dp-feat-body {
  color: var(--dp-muted);
  font-size: 11.5px;
  line-height: 1.55;
}

/* Bottom brand meta */
.dp-brand-meta {
  margin-top: auto;
  padding-top: 30px;
}

.dp-brand-pill {
  display: block;
  margin-bottom: 13px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.dp-company-row {
  display: flex;
  align-items: center;
  gap: 26px;
  color: #748096;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -.04em;
  opacity: .85;
}

.dp-company-row span:nth-child(2) {
  font-weight: 600;
}

.dp-company-row span:nth-child(3) {
  font-weight: 700;
}

.dp-company-row span:nth-child(4) {
  font-size: 14px;
  font-weight: 800;
}

/* Right form panel */
.dp-form-panel {
  position: relative;
  flex: 1;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 40px;
  background: rgba(255, 255, 255, .72);
}

.dp-form-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(circle at 92% 8%, rgba(124, 58, 237, .06), transparent 27%);
}

.dp-form-inner {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 416px;
}

.dp-auth-mark {
  width: 56px;
  height: 56px;
  margin: 0 auto 22px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ede9fe, #ede9fe);
  color: #6754dc;
  box-shadow: 0 12px 30px rgba(91, 92, 235, .13);
}

.dp-form-head {
  margin-bottom: 27px;
  text-align: center;
}

.dp-form-head h2 {
  margin: 0 0 10px;
  font-size: 34px;
  font-weight: 800;
  letter-spacing: -.045em;
}

.dp-form-head p {
  margin: 0;
  color: var(--dp-muted);
  font-size: 14px;
  line-height: 1.55;
}

/* Form fields */
.dp-label {
  display: block;
  margin-bottom: 8px;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
}

.dp-input-wrap,
.dp-pass-wrap {
  position: relative;
}

.dp-input-icon {
  position: absolute;
  top: 50%;
  left: 15px;
  color: #94a3b8;
  transform: translateY(-50%);
  pointer-events: none;
}

.dp-input {
  display: block;
  width: 100%;
  height: 48px;
  padding: 0 15px;
  border: 1px solid var(--dp-border);
  border-radius: 12px;
  outline: 0;
  background: #fff;
  color: var(--dp-text);
  font: 400 14px var(--f-body);
  transition: .18s ease;
}

.dp-input.has-icon {
  padding-left: 43px;
}

.dp-pass-wrap .dp-input {
  padding-right: 45px;
}

.dp-input::placeholder {
  color: #a5afbd;
}

.dp-input:focus {
  border-color: #8b8cf6;
  box-shadow: 0 0 0 4px rgba(91, 92, 235, .11);
}

.dp-input.err {
  border-color: #ef4444;
}

.dp-eye-btn {
  position: absolute;
  top: 50%;
  right: 10px;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #8b95a5;
  cursor: pointer;
  transform: translateY(-50%);
}

.dp-eye-btn:hover {
  color: var(--dp-primary);
  background: #f5f3ff;
}

.dp-form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: -2px;
}

.dp-check {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--dp-muted);
  font-size: 12.5px;
  cursor: pointer;
}

.dp-check input {
  width: 15px;
  height: 15px;
  margin: 0;
  accent-color: var(--dp-primary);
}

/* Buttons */
.dp-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  width: 100%;
  height: 50px;
  border-radius: 12px;
  border: 0;
  cursor: pointer;
  font: 600 15px var(--f-body);
  transition: transform .18s ease, box-shadow .18s ease;
}

.dp-btn-primary {
  color: white;
  background: linear-gradient(105deg, #5b5ceb, #7c3aed);
  box-shadow: 0 12px 22px rgba(91, 92, 235, .23);
}

.dp-btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 16px 28px rgba(91, 92, 235, .32);
}

.dp-btn:disabled {
  opacity: .65;
  cursor: not-allowed;
}

.dp-btn-outline {
  height: 46px;
  border: 1px solid var(--dp-border);
  background: white;
  color: #374151;
  font-size: 14px;
}

.dp-btn-outline:hover {
  background: #fafafa;
  border-color: #cbd5e1;
}

.dp-social-stack {
  display: grid;
  gap: 10px;
}

.dp-social-icon {
  display: flex;
  width: 18px;
  justify-content: center;
}

/* Divider / alerts */
.dp-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 23px 0;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.dp-divider::before,
.dp-divider::after {
  content: '';
  height: 1px;
  flex: 1;
  background: var(--dp-border);
}

.dp-alert {
  margin-bottom: 18px;
  padding: 11px 13px;
  border-radius: 10px;
  font-size: 13px;
}

.dp-alert-error {
  color: #b91c1c;
  border: 1px solid #fecaca;
  background: #fef2f2;
}

.dp-spin {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, .45);
  border-top-color: #fff;
  border-radius: 50%;
  animation: dp-rotate .8s linear infinite;
}

@keyframes dp-rotate {
  to {
    transform: rotate(360deg);
  }
}

.dp-field-error {
  margin-top: 5px;
  color: #dc2626;
  font-size: 11.5px;
}

/* Grid / OTP / steps / tags */
.dp-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.dp-full {
  grid-column: 1 / -1;
}

.dp-otp-row {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin: 24px 0;
}

.dp-otp-cell {
  width: 50px;
  height: 58px;
  border: 1px solid var(--dp-border);
  border-radius: 12px;
  text-align: center;
  font: 700 23px var(--f-body);
  outline: 0;
}

.dp-otp-cell:focus {
  border-color: #8b8cf6;
  box-shadow: 0 0 0 4px rgba(91, 92, 235, .11);
}

.dp-step-dots,
.dp-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 28px;
}

.dp-dot {
  height: 4px;
  border-radius: 4px;
}

.dp-dot-active {
  width: 30px;
  background: var(--dp-primary);
}

.dp-dot-done {
  width: 14px;
  background: #bfc0fb;
}

.dp-dot-pending {
  width: 14px;
  background: #e5e7eb;
}

.dp-step-node {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--dp-border);
  border-radius: 50%;
  font-size: 13px;
  font-weight: 700;
}

.dp-step-node.active {
  color: #fff;
  border: 0;
  background: var(--dp-primary);
}

.dp-step-node.done {
  color: var(--dp-primary);
  border-color: #c7c7ff;
  background: #f1f0ff;
}

.dp-step-bar {
  width: 48px;
  height: 2px;
  background: var(--dp-border);
}

.dp-step-bar.done {
  background: #c7c7ff;
}

.dp-tag-area {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 52px;
  padding: 10px;
  border: 1px solid var(--dp-border);
  border-radius: 12px;
}

.dp-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  border-radius: 999px;
  color: #584bc4;
  background: #f0efff;
  font-size: 12px;
}

.dp-tag-x {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  cursor: pointer;
}

/* Responsive */
@media (max-width: 1050px) {
  .dp-brand {
    padding: 42px;
  }
  .dp-features {
    grid-template-columns: 1fr;
    max-width: 440px;
  }
  .dp-feat {
    min-height: auto;
    display: grid;
    grid-template-columns: 34px 1fr;
    column-gap: 12px;
  }
  .dp-feature-icon {
    grid-row: span 2;
    margin: 0;
  }
  .dp-feat-title {
    margin-top: 1px;
  }
  .dp-company-row {
    gap: 15px;
  }
}

@media (max-width: 760px) {
  .dp-brand {
    display: none;
  }
  .dp-form-panel {
    padding: 40px 22px;
  }
  .dp-grid-2 {
    grid-template-columns: 1fr;
  }
  .dp-full {
    grid-column: auto;
  }
}
`;

const PAGE_META = {
  login: {
    chip: "AI-POWERED GTM PLATFORM",
    headline: (
      <>
        Turn market signals
        <br />
        into <em>closed deals</em>
      </>
    ),
    desc: "Delphi AI helps revenue teams discover high-intent accounts, buyer groups, competitive insights, and account intelligence using AI-powered market signals.",
    feats: [
      {
        icon: BrainCircuit,
        tone: "purple",
        t: "Smart Lead Scoring",
        b: "Rank prospects based on buying intent and conversion probability.",
      },
      {
        icon: BellRing,
        tone: "blue",
        t: "Buying Signal Alerts",
        b: "Receive real-time intent signals before competitors.",
      },
      {
        icon: Building2,
        tone: "green",
        t: "Automated Company Intelligence",
        b: "Enrich companies using CRM, intent data, technographics and firmographics.",
      },
    ],
    pill: "Trusted by enterprise teams",
  },

  register: {
    chip: "GET STARTED FREE",
    headline: (
      <>
        Turn market signals
        <br />
        into <em>closed deals</em>
      </>
    ),
    desc: "Delphi AI gives your sales team the intelligence to find and convert their best opportunities.",
    feats: [
      {
        icon: BrainCircuit,
        tone: "purple",
        t: "Smart Lead Scoring",
        b: "Identify high-value leads automatically with AI.",
      },
      {
        icon: BellRing,
        tone: "blue",
        t: "Buying Signal Alerts",
        b: "Get notified when prospects show buying intent.",
      },
      {
        icon: Building2,
        tone: "green",
        t: "Automated Enrichment",
        b: "Keep company data current automatically.",
      },
    ],
    pill: "Trusted by enterprise teams",
  },

  otp: {
    chip: "SECURE VERIFICATION",
    headline: (
      <>
        One step to
        <br />
        <em>unlock access</em>
      </>
    ),
    desc: "Multi-factor email verification keeps your account and intelligence data safe.",
    feats: [
      {
        icon: Sparkles,
        tone: "purple",
        t: "Enterprise security",
        b: "Your account is protected at every step.",
      },
    ],
    pill: "Enterprise-ready security",
  },

  forgot: {
    chip: "ACCOUNT RECOVERY",
    headline: (
      <>
        Back on track
        <br />
        in <em>minutes</em>
      </>
    ),
    desc: "We'll send a reset code to your registered email so you can regain access securely.",
    feats: [
      {
        icon: Sparkles,
        tone: "purple",
        t: "Secure reset",
        b: "A simple and protected way back in.",
      },
    ],
    pill: "Secure recovery",
  },

  enrichment: {
    chip: "ONBOARDING",
    headline: (
      <>
        Power your
        <br />
        <em>intelligence engine</em>
      </>
    ),
    desc: "Tell us about your company so Delphi can surface relevant leads, competitors, and market signals.",
    feats: [
      {
        icon: BrainCircuit,
        tone: "purple",
        t: "Personalized signals",
        b: "Insights tailored to your market.",
      },
    ],
    pill: "Setup in two quick steps",
  },
};

export function useAuthStyles() {
  const done = useRef(false);

  useEffect(() => {
    if (done.current) return;
    done.current = true;

    if (!document.getElementById("dp-global-css")) {
      const el = document.createElement("style");
      el.id = "dp-global-css";
      el.textContent = GLOBAL_CSS;
      document.head.appendChild(el);
    }
  }, []);
}

export default function AuthLayout({ page = "login", children }) {
  useAuthStyles();
  const meta = PAGE_META[page] || PAGE_META.login;

  return (
    <div className="dp-root">
      <aside className="dp-brand">
        <div className="dp-brand-noise" />
        <div className="dp-brand-lines" />
        <div className="dp-brand-stripe" />

        <div className="dp-brand-inner">
          <div className="dp-logo">
            <span className="dp-logo-mark">
              <Sparkles size={18} />
            </span>
            <span className="dp-logo-delphi">DELPHI</span>
            <span className="dp-logo-dot">.</span>
          </div>

          <div className="dp-tagline-chip">{meta.chip}</div>

          <h1 className="dp-headline">{meta.headline}</h1>
          <p className="dp-desc">{meta.desc}</p>

          <div className="dp-features">
            {meta.feats.map((f, i) => {
              const Icon = f.icon;
              return (
                <div key={i} className="dp-feat">
                  <div className={`dp-feature-icon ${f.tone}`}>
                    <Icon size={18} />
                  </div>
                  <div>
                    <div className="dp-feat-title">{f.t}</div>
                    <div className="dp-feat-body">{f.b}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="dp-brand-meta">
          <span className="dp-brand-pill">{meta.pill}</span>
          <div className="dp-company-row">
            <span>HubSpot</span>
            <span>slack</span>
            <span>zoom</span>
            <span>salesforce</span>
          </div>
        </div>
      </aside>

      <main className="dp-form-panel">
        <div className="dp-form-inner">{children}</div>
      </main>
    </div>
  );
}
