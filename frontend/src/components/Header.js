
import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Nav_Sidebar from "./Headerbar"; // Your updated dock

export default function Header() {
    const navigate = useNavigate();
    const location = useLocation();
    const [isSettingsOpen, setSettingsOpen] = useState(false);

    // HIDE IF: On Login page OR No User Session
    const isAuthenticated = localStorage.getItem("token") && localStorage.getItem("user");
    if (location.pathname === "/" || location.pathname === "/login" ) return null;

    return (
        <>
            <Sidebar isOpen={isSettingsOpen} toggleSidebar={() => setSettingsOpen(false)} />
            
            {/* Main Wrapper: Balanced Fixed Header */}
            <nav
  className="navbar bg-white border-bottom px-4 py-2 shadow-sm  shadow-lg border" style={{position: "fixed",left: "50%",transform: "translateX(-50%)",width: "100%",zIndex: 1050}}>
                <div className="container-fluid d-flex align-items-center justify-content-between ">
                    
                    {/* LEFT: Branding - Fixed Width to prevent jumping */}
<div 
    className="d-flex align-items-center gap-3" 
    style={{ zIndex: 1040, cursor: 'pointer', minWidth: '180px' }}
    onClick={() => navigate("/Dashboard")}
>
    {/* Enhanced Typography Logo */}
    {/* <h5 className="mb-0 delphi-logo-text">
        DELPHI
    </h5> */}
    <img src="/delphi.png" className="img-fluid" style={{width: '50px'}} alt="Delphi logo" />

    <style>{`
        .delphi-logo-text {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 1.2rem;
            letter-spacing: 3px;
            background: linear-gradient(90deg, #212529 0%, #0d6efd 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            position: relative;
            transition: all 0.3s ease;
        }
        .delphi-logo-text:hover {
            letter-spacing: 5px;
            opacity: 0.8;
        }
    `}</style>
</div>

                    {/* CENTER: The Navigation Dock (Integrated) */}
                    <div className="flex-grow-1 d-flex justify-content-center">
                        <Nav_Sidebar />
                    </div>

                    {/* RIGHT: Settings - Fixed Width to match left side balance */}
                    <div className="d-flex justify-content-end" style={{ minWidth: '180px' }}>
                        <button 
                            className="btn btn-light shadow-sm rounded-circle border p-0 d-flex align-items-center justify-content-center"
                            style={{ width: 38, height: 38, transition: 'all 0.2s' }}
                            onClick={() => setSettingsOpen(true)}
                        >
                            <i className="bi bi-gear-wide-connected text-dark fs-5"></i>
                        </button>
                    </div>
                </div>
            </nav>
            
            {/* Spacer for App.js content since Header is fixed */}
            <div style={{ height: '0px' }}></div>
        </>
    );
}