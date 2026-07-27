// components/Sidebar.js

import React from "react";
import { useNavigate } from "react-router-dom";

const menuItems = [
  {
    title: "Propensity Scoring Configuration",
    subtitle: "Adjust propensity weights & scores",
    icon: "bi-sliders",
    path: "/ScoreConfiguration",
  },
  {
    title: "ICP Configuration",
    subtitle: "Adjust ICP weights & scores",
    icon: "bi-diagram-3",
    path: "/ICP",
  },
  {
    title: "Persona Configuration",
    subtitle: "Adjust Persona weights & scores",
    icon: "bi-people",
    path: "/Persona",
  },
];

export default function Sidebar({ isOpen, toggleSidebar }) {
  const navigate = useNavigate();

  const handleNavigate = (path) => {
    navigate(path);
    toggleSidebar();
  };

  const handleLogout = () => {
    localStorage.clear();
    toggleSidebar();
    navigate("/");
  };

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="position-fixed top-0 start-0 w-100 h-100"
          style={{
            zIndex: 1060,
            background: "rgba(15,23,42,0.25)",
            backdropFilter: "blur(4px)",
          }}
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar */}
      <aside
        className="position-fixed top-0 end-0 bg-white shadow-lg border-start d-flex flex-column"
        style={{
          width: "320px",
          height: "100vh",
          zIndex: 1070,
          transform: isOpen ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.35s ease",
          visibility: isOpen ? "visible" : "hidden",
        }}
      >
        {/* Header */}
        <div className="d-flex justify-content-between align-items-center p-4 border-bottom bg-light">
          <div>
            <h5 className="fw-bold mb-1">Control Panel</h5>
            <small className="text-muted">
              Manage application settings
            </small>
          </div>

          <button
            className="btn-close shadow-none"
            onClick={toggleSidebar}
          ></button>
        </div>

        {/* Navigation */}
        <div className="flex-grow-1 p-3">
          <div className="d-flex flex-column gap-3">
            {menuItems.map((item) => (
              <button
                key={item.path}
                onClick={() => handleNavigate(item.path)}
                className="sidebar-card border rounded-3 bg-white text-start p-3"
              >
                <div className="d-flex align-items-center gap-3">
                  <div className="sidebar-icon">
                    <i className={`bi ${item.icon}`}></i>
                  </div>

                  <div className="overflow-hidden">
                    <h6 className="mb-1 fw-semibold">
                      {item.title}
                    </h6>

                    <small className="text-muted">
                      {item.subtitle}
                    </small>
                  </div>
                </div>
              </button>
            ))}

            {/* Logout */}
            <button
              onClick={handleLogout}
              className="sidebar-card logout-card border border-danger rounded-3 text-start p-3 mt-3"
            >
              <div className="d-flex align-items-center gap-3">
                <div className="sidebar-icon bg-danger-subtle text-danger">
                  <i className="bi bi-box-arrow-right"></i>
                </div>

                <div>
                  <h6 className="mb-0 text-danger fw-semibold">
                    Sign Out
                  </h6>

                  <small className="text-danger opacity-75">
                    Logout from Delphi
                  </small>
                </div>
              </div>
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="border-top p-3 text-center">
          <small className="text-muted">
            DELPHI <strong>v1.0.5</strong>
          </small>
        </div>
      </aside>

      <style>{`
        .sidebar-card{
            transition:all .25s ease;
            cursor:pointer;
            background:#fff;
        }

        .sidebar-card:hover{
            transform:translateX(-4px);
            border-color:#6f42c1 !important;
            box-shadow:0 8px 20px rgba(111,66,193,.12);
            background:#faf9ff;
        }

        .sidebar-icon{
            width:42px;
            height:42px;
            border-radius:12px;
            background:#eef2ff;
            color:#6f42c1;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:18px;
            flex-shrink:0;
        }

        .logout-card:hover{
            background:#fff5f5 !important;
            border-color:#dc3545 !important;
            box-shadow:0 8px 20px rgba(220,53,69,.12);
        }

        .logout-card .sidebar-icon{
            background:#fdeaea;
            color:#dc3545;
        }
      `}</style>
    </>
  );
}