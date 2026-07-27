import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { useNavigate } from "react-router-dom";

import {
  ArrowRight,
  Bot,
  Building2,
  Compass,
  Crosshair,
  Layers3,
  MapPin,
  Send,
  Sparkles,
  Target,
  UsersRound,
  WandSparkles,
} from "lucide-react";

import "./intellegence.css";

const API_BASE = "http://127.0.0.1:8000";
const SESSION_ID = `user_${Math.random().toString(36).slice(2, 9)}`;

/* -------------------------------------------------------------------------- */
/*                                  Sidebar                                   */
/* -------------------------------------------------------------------------- */

const primary = [
  ["Create ICP", Compass],
  ["Discover Buyer Groups", UsersRound],
  ["Discover Industries", Building2],
  ["Create TAL", Target],
];

const deepDive = [
  ["Buyer Persona", UsersRound],
  ["Geo Persona Signal", MapPin],
  ["Prioritize Accounts", Layers3],
  ["Refine ICP", Crosshair],
  ["Refine TAL", Target],
];

/* -------------------------------------------------------------------------- */
/*                                Action Cards                                */
/* -------------------------------------------------------------------------- */

const actions = [
  [
    "Create ICP",
    "Build a high-confidence ideal customer profile using your data.",
    Crosshair,
    "violet",
  ],
  [
    "Discover Buyer Groups",
    "Identify the stakeholders and buying committees that matter.",
    UsersRound,
    "blue",
  ],
  [
    "Discover Industries",
    "Find the segments with the strongest market fit and intent.",
    Building2,
    "green",
  ],
  [
    "Create TAL",
    "Generate a focused target account list for your next motion.",
    Target,
    "orange",
  ],
];

/* -------------------------------------------------------------------------- */
/*                               Main Component                               */
/* -------------------------------------------------------------------------- */

export default function Intelligence() {
  const navigate = useNavigate();

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeItem, setActiveItem] = useState("Create ICP");

  const textareaRef = useRef(null);
  const sessionRef = useRef(SESSION_ID);

  /* ------------------------------------------------------------------------ */
  /*                                User Data                                 */
  /* ------------------------------------------------------------------------ */

  const user = (() => {
    try {
      return JSON.parse(localStorage.getItem("user")) || {};
    } catch {
      return {};
    }
  })();

  const name = user.full_name || "Sameer Datta";

  const initials = name
    .split(" ")
    .map((x) => x[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  /* ------------------------------------------------------------------------ */
  /*                           Auto Resize Textarea                           */
  /* ------------------------------------------------------------------------ */

  useEffect(() => {
    const el = textareaRef.current;

    if (!el) return;

    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [input]);

  /* ------------------------------------------------------------------------ */
  /*                             Send Message API                             */
  /* ------------------------------------------------------------------------ */

  const send = useCallback(
    async (question) => {
      const text = (question || input).trim();

      if (!text || loading) return;

      setMessages((prev) => [
        ...prev,
        {
          role: "user",
          text,
        },
      ]);

      setInput("");
      setLoading(true);

      try {
        const res = await fetch(`${API_BASE}/context/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_id: sessionRef.current,
            message: text,
          }),
        });

        const data = await res.json();

        setMessages((prev) => [
          ...prev,
          {
            role: "bot",
            text:
              data.response ||
              "I'm ready to help you explore that insight.",
          },
        ]);
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            role: "bot",
            text:
              "I couldn't reach the intelligence service. Please try again.",
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [input, loading]
  );

  /* ------------------------------------------------------------------------ */
  /*                             Sidebar Navigation                           */
  /* ------------------------------------------------------------------------ */

  const navItem = ([label, Icon]) => (
    <button
      key={label}
      className={`delphi-nav-item ${
        activeItem === label ? "active" : ""
      }`}
      onClick={() => {
        setActiveItem(label);

        if (label !== "Create ICP") {
          navigate("/Intelligence");
        }
      }}
    >
      <Icon size={17} />
      <span>{label}</span>
    </button>
  );

  /* ------------------------------------------------------------------------ */
  /*                                  Render                                  */
  /* ------------------------------------------------------------------------ */

  return (
    <div className="delphi-intelligence">
      {/* ================= Sidebar ================= */}

      <aside className="delphi-side">
        <div className="nav-group">
          <span className="nav-caption">Primary</span>

          {primary.map(navItem)}
        </div>

        <div className="nav-rule" />

        <div className="nav-group">
          <span className="nav-caption">Deep Dive</span>

          {deepDive.map(navItem)}
        </div>

        <div className="side-ai-card">
          <div className="side-ai-icon">
            <WandSparkles size={19} />
          </div>

          <div>
            <b>AI Powered</b>
            <span>GTM Intelligence Platform</span>
          </div>

          <Sparkles
            className="side-sparkle"
            size={17}
          />
        </div>
      </aside>

      {/* ================= Main ================= */}

      <main className="intelligence-main">
        <div className="intelligence-glow" />
        <div className="intelligence-dots" />

        {messages.length === 0 ? (
          <section className="intelligence-hero">
            <div className="hero-kicker">
              <span />
              DELPHI INTELLIGENCE
            </div>

            <h1>
              Good morning,
              <br />
              I'm <em>Delphi</em> — your
              <em> AI Go-To-Market</em>
              <br />
              Intelligence Consultant.
            </h1>

            <p>
              I analyze campaign, CRM, intent data and market
              signals to generate actionable GTM insights.
            </p>

            <div className="hero-divider" />

            <h2>Where would you like to start?</h2>

            <div className="action-grid">
              {actions.map(
                ([title, description, Icon, color]) => (
                  <button
                    key={title}
                    className="action-card"
                    onClick={() => send(title)}
                  >
                    <div
                      className={`action-icon ${color}`}
                    >
                      <Icon size={23} />
                    </div>

                    <div>
                      <strong>{title}</strong>

                      <p>{description}</p>
                    </div>

                    <span className="action-arrow">
                      <ArrowRight size={18} />
                    </span>
                  </button>
                )
              )}
            </div>
          </section>
        ) : (
          <section className="chat-thread">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`chat-message ${message.role}`}
              >
                <div className="chat-bubble">
                  {message.role === "bot" && (
                    <Bot size={17} />
                  )}

                  <span>{message.text}</span>
                </div>
              </div>
            ))}

            {loading && (
              <div className="chat-message bot">
                <div className="chat-bubble">
                  <Bot size={17} />

                  <span className="typing">
                    Delphi is thinking...
                  </span>
                </div>
              </div>
            )}
          </section>
        )}

        {/* ================= Chat Input ================= */}

        <div className="delphi-chat">
          <div className="chat-ai">
            <Sparkles size={19} />
          </div>

          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            placeholder="Ask Delphi anything, or select an insight above..."
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />

          <button
            aria-label="Send Message"
            onClick={() => send()}
            disabled={!input.trim() || loading}
          >
            <Send size={18} />
          </button>
        </div>
      </main>
    </div>
  );
}