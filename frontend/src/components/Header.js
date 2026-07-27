// components/Header.js

import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";

const profileMenu = [
  {
    label: "Profile",
    path: "/Dashboard",
  },
  {
    label: "Settings",
    path: "/ScoreConfiguration",
  },
];

export default function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const profileRef = useRef(null);

  const [profileOpen, setProfileOpen] = useState(false);

  // -----------------------------
  // User Information
  // -----------------------------
  const user = (() => {
    try {
      return JSON.parse(localStorage.getItem("user")) || {};
    } catch {
      return {};
    }
  })();

  const userName =
    user.full_name || user.email || "Delphi User";

  const userEmail =
    user.email || "delphi@delphi.ai";

  const initials = (
    user.full_name
      ? user.full_name
          .split(" ")
          .map((word) => word[0])
          .join("")
      : user.email?.charAt(0) || "D"
  )
    .slice(0, 2)
    .toUpperCase();

  // -----------------------------
  // Close dropdown when clicking outside
  // -----------------------------
  useEffect(() => {
    function handleOutsideClick(e) {
      if (
        profileRef.current &&
        !profileRef.current.contains(e.target)
      ) {
        setProfileOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleOutsideClick
    );

    return () =>
      document.removeEventListener(
        "mousedown",
        handleOutsideClick
      );
  }, []);

  // -----------------------------
  // Hide Header on Login Screen
  // Keep this after all hooks so hooks are always called in the same order.
  // -----------------------------
  if (["/", "/login"].includes(location.pathname)) {
    return null;
  }

  // -----------------------------
  // Logout
  // -----------------------------
  const logout = () => {
    localStorage.clear();
    navigate("/");
  };

  return (
    <>
      <header className="delphi-header">

        {/* Logo */}

        <div className="header-logo" onClick={() => navigate("/Intelligence")}>
          <span className="header-logo-mark">✦</span><span>DELPHI</span><i>.</i>
        </div>

        {/* Profile */}

        <div
          className="profile-wrapper"
          ref={profileRef}
        >
          <button
            className="profile-button"
            onClick={() =>
              setProfileOpen(!profileOpen)
            }
          >
            <div className="profile-avatar">{initials}<span className="online-dot" /></div>
            <span className="profile-summary"><b>{userName}</b><small>Sales Director</small></span><span className="profile-chevron">⌄</span>
          </button>

          {profileOpen && (
            <div className="profile-dropdown">

              <div className="profile-info">
                <div className="profile-avatar large">
                  {initials}
                </div>

                <div>
                  <h6>{userName}</h6>
                  <small>{userEmail}</small>
                </div>
              </div>

              <hr />

              {profileMenu.map((item) => (
                <button
                  key={item.label}
                  className="dropdown-item"
                  onClick={() => {
                    navigate(item.path);
                    setProfileOpen(false);
                  }}
                >
                  {item.label}
                </button>
              ))}

              <hr />

              <button
                className="dropdown-item logout"
                onClick={logout}
              >
                Logout
              </button>
            </div>
          )}
        </div>

      </header>

      <style>{`

      .delphi-header{

          position:fixed;
          top:0;
          left:0;
          right:0;

          height:72px;

          display:flex;
          align-items:center;
          justify-content:space-between;

          padding:0 34px;

          background:#fff;

          border-bottom:1px solid #E5E7EB;

          box-shadow:0 3px 14px rgba(15,23,42,.025);

          z-index:1050;

      }

      .header-logo{

          display:flex;
          align-items:center;
          gap:9px;
          font-family:Inter, sans-serif;
          font-size:18px;
          font-weight:800;
          letter-spacing:-.06em;

          cursor:pointer;

          color:#111827;

      }

      .header-logo i{color:#6C4CF6;font-size:23px;font-style:normal;margin-left:-8px;margin-top:-8px}
      .header-logo-mark{display:grid;place-items:center;width:31px;height:31px;border-radius:10px;color:#fff;background:linear-gradient(135deg,#6C4CF6,#8b5cf6);box-shadow:0 7px 16px rgba(108,76,246,.25);font-size:18px}

      .profile-wrapper{

          position:relative;

      }

      .profile-button{

          border:none;

          background:transparent;

          display:flex;
          align-items:center;
          gap:10px;
          padding:6px 8px;

          border-radius:12px;

          cursor:pointer;

          transition:.25s;

      }

      .profile-summary{text-align:left;display:grid;gap:2px}.profile-summary b{font-size:13px;line-height:1.1}.profile-summary small{font-size:11px;color:#64748B}.profile-chevron{font-size:17px;color:#94A3B8}.online-dot{position:absolute;right:-1px;bottom:1px;width:10px;height:10px;border:2px solid #fff;border-radius:50%;background:#7ED957}

      .profile-button:hover{

          background:#F3F4F6;

      }

      .profile-avatar{

          width:38px;
          height:38px;

          border-radius:50%;

          display:flex;
          align-items:center;
          justify-content:center;

          font-size:14px;
          font-weight:700;

          color:#fff;

          background:linear-gradient(135deg,#4F6BFF,#7C3AED);

          position:relative;

      }

      .profile-avatar.large{

          width:48px;
          height:48px;

      }

      .profile-dropdown{

          position:absolute;

          right:0;
          top:52px;

          width:240px;

          background:#fff;

          border:1px solid #E5E7EB;

          border-radius:14px;

          overflow:hidden;

          box-shadow:0 20px 40px rgba(0,0,0,.10);

      }

      .profile-info{

          display:flex;

          gap:14px;

          align-items:center;

          padding:18px;

      }

      .profile-info h6{

          margin:0;

          font-size:15px;

          font-weight:600;

      }

      .profile-info small{

          color:#6B7280;

      }

      .dropdown-item{

          width:100%;

          border:none;

          background:#fff;

          text-align:left;

          padding:13px 18px;

          cursor:pointer;

          transition:.2s;

      }

      .dropdown-item:hover{

          background:#F9FAFB;

      }

      .logout{

          color:#DC2626;

      }

      .logout:hover{

          background:#FEF2F2;

      }

      hr{

          margin:0;

          border:none;

          border-top:1px solid #E5E7EB;

      }

      `}</style>
    </>
  );
}
