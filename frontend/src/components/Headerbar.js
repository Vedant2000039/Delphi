// components/GlassNavigation.js

import React from "react";
import { useNavigate, useLocation } from "react-router-dom";

const navigationTabs = [
  {
    label: "Propensity Scoring",
    icon: "bi-graph-up-arrow",
    path: "/leadscoring",
  },
  {
    label: "ICP",
    icon: "bi-dice-6",
    path: "/ICP/CreateIdealTAL",
  },
  {
    label: "Create Persona",
    icon: "bi-person-badge",
    path: "/Persona/CreatePersona",
  },
  {
    label: "Intelligence",
    icon: "bi-lightbulb",
    path: "/Intelligence",
  },
];

export default function GlassNavigation() {
  const navigate = useNavigate();
  const location = useLocation();

  // Hide navigation on Login page
  if (["/", "/login"].includes(location.pathname)) {
    return null;
  }

  return (
    <>
      <div
        className="glass-nav-wrapper d-flex justify-content-center w-100"
        style={{
          zIndex: 1030,
          pointerEvents: "none",
        }}
      >
        <div
          className="glass-dock d-flex align-items-center rounded-pill shadow-lg"
          style={{
            pointerEvents: "auto",
          }}
        >
          {navigationTabs.map((tab) => {
            const active = location.pathname === tab.path;

            return (
              <button
                key={tab.path}
                onClick={() => navigate(tab.path)}
                className={`nav-pill ${
                  active ? "nav-pill-active" : ""
                }`}
              >
                <i className={`bi ${tab.icon}`}></i>

                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <style>{`
        .glass-dock{
            display:flex;
            align-items:center;
            gap:8px;
            padding:8px;
            max-width:95vw;
            overflow-x:auto;
            white-space:nowrap;

            background:rgba(255,255,255,.12);
            backdrop-filter:blur(18px);
            border:1px solid rgba(255,255,255,.35);

            scrollbar-width:none;
            -ms-overflow-style:none;
        }

        .glass-dock::-webkit-scrollbar{
            display:none;
        }

        .nav-pill{
            display:flex;
            align-items:center;
            gap:8px;

            padding:10px 20px;
            border:none;
            border-radius:999px;

            background:transparent;
            color:#6c757d;
            font-size:14px;
            font-weight:600;

            transition:all .25s ease;
            cursor:pointer;
            flex-shrink:0;
        }

        .nav-pill i{
            font-size:15px;
        }

        .nav-pill:hover{
            background:rgba(13,110,253,.10);
            color:#0d6efd;
            transform:translateY(-2px);
        }

        .nav-pill-active{
            background:#0d6efd;
            color:#fff;
            box-shadow:0 8px 20px rgba(13,110,253,.30);
        }

        .nav-pill-active:hover{
            color:#fff;
            transform:none;
        }

        @media (max-width:768px){

            .glass-dock{
                width:100%;
                justify-content:flex-start;
                border-radius:20px;
            }

            .nav-pill{
                padding:10px 16px;
                font-size:13px;
            }
        }
      `}</style>
    </>
  );
}