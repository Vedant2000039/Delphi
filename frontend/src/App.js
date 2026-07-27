// // // frontend/src/App.js
import { BrowserRouter as Router, Navigate, Routes, Route, useLocation } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import Login from "./components/Onboarding/Login";
import Onboarding from "./components/Onboarding/Register";
import Enrichment from "./components/Onboarding/Enrichment";
import Otp from "./components/Onboarding/Otp";
import Forget from "./components/Onboarding/forget";
import ProtectedRoute from "./components/ProtectedRoute";

import CampaignDetails from "./components/CampaignDetails";
import CompanyDetails from "./components/CompanyDetails";
import Header from "./components/Header";
import Intellegence from "./components/Intelligence/intellegence";

function Layout() {
  const location = useLocation();

  const hideLayoutRoutes = ["/", "/Onboarding", "/Enrichment", "/Otp", "/Forget"];

  const shouldHideLayout = hideLayoutRoutes.includes(location.pathname);

  return (
    <>
      <ToastContainer position="top-right" autoClose={3000} />
      {!shouldHideLayout && <Header />}

      <div className="app-layout">
        <div className="flex-grow-1">
          <Routes>

            {/* PUBLIC */}
            <Route path="/"           element={<Login />} />
            <Route path="/Onboarding" element={<Onboarding />} />
            <Route path="/Enrichment" element={<Enrichment />} />
            <Route path="/Otp"        element={<Otp />} />
            <Route path="/Forget"     element={<Forget />} />

            {/* PROTECTED */}
            <Route path="/Dashboard" element={<Navigate to="/Intelligence" replace />} />
            <Route path="/LeadScoring" element={<Navigate to="/Intelligence" replace />} />
            <Route path="/ScoreConfiguration" element={<Navigate to="/Intelligence" replace />} />
            <Route path="/ScoreConfiguration/values/:parameterId" element={<Navigate to="/Intelligence" replace />} />
            <Route path="/Persona/CreatePersona" element={<Navigate to="/Intelligence" replace />} />
            <Route path="/Persona" element={<Navigate to="/Intelligence" replace />} />
            <Route path="/persona/values/:parameterId" element={<Navigate to="/Intelligence" replace />} />
            <Route path="/campaigns/:campaignId" element={<ProtectedRoute><CampaignDetails /></ProtectedRoute>} />
            <Route path="/campaigns/:campaignId/companies/:companyId" element={<ProtectedRoute><CompanyDetails /></ProtectedRoute>} />
            <Route path="/leads/:leadId" element={<Navigate to="/Intelligence" replace />} />
            <Route path="/persona-report" element={<Navigate to="/Intelligence" replace />} />
            <Route path="/Intelligence" element={<ProtectedRoute><Intellegence /></ProtectedRoute>} />

            {/* FALLBACK */}
            <Route path="*" element={<Login />} />

          </Routes>
        </div>
      </div>
    </>
  );
}

function App() {
  return (
    <Router>
      <Layout />
    </Router>
  );
}

export default App;
