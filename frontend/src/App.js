// // // frontend/src/App.js
import { BrowserRouter as Router, Routes, Route, useLocation } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import Login from "./components/Onboarding/Login";
import Onboarding from "./components/Onboarding/Register";
import Enrichment from "./components/Onboarding/Enrichment";
import Otp from "./components/Onboarding/Otp";
import Forget from "./components/Onboarding/forget";
import ProtectedRoute from "./components/ProtectedRoute";

import Dashboard from "./components/Dashboard/Dashboard";
import CampaignDetails from "./components/CampaignDetails";
import CompanyDetails from "./components/CompanyDetails";
import Header from "./components/Header";
import LeadScoring from "./components/LeadScoring/LeadScoring";
import LeadDetail from "./components/LeadScoring/LeadDetail";
import ScoreConfiguration from "./components/LeadScoring/ScoreConfiguration";
import ScoreValuesConfig from "./components/LeadScoring/ScoreValuesConfig";
import ICPScoringConfig from "./components/ICP/ScoringConfig/ICPScoringConfig";
import ICPScoringConfigList from "./components/ICP/ScoringConfig/ICPScoringConfigList";
import GenerateICP from "./components/ICP/GenerateICP";
import CreateIdealTAL from "./components/ICP/CreateIdealTAL";
import ICPLeadAnalysis from "./components/ICP/ICPLeadAnalysis";
import CreatePersona from "./components/Persona/CreatePersona";
import PersonaScoringConfig from "./components/Persona/ScoringConfig/PersonaScoringConfig";
import PersonaScoringConfigList from "./components/Persona/ScoringConfig/PersonaScoringConfigList";
import Nav_Sidebar from "./components/Headerbar";
import PersonaReportPage from "./components/Persona/PersonaReportPage";
import Intellegence from "./components/Intelligence/intellegence";

import ContextBuilder from "./components/Onboarding/context_builder";

function Layout() {
  const location = useLocation();

  const hideLayoutRoutes = ["/", "/Onboarding", "/Enrichment", "/Otp", "/Forget", "/context-builder"];

  const isKnownPublicRoute = hideLayoutRoutes.includes(location.pathname);

  // A user is only "authenticated" if we actually have a session in storage.
  // NOTE: Login.js / Otp.js currently only ever call
  // localStorage.setItem("user", ...) — there is no "token" key being set
  // anywhere in the onboarding flow. Checking for a token here would mean
  // this is *always* false, hiding the header even for logged-in users.
  // If/when a real auth token is introduced, add it back into this check:
  //   Boolean(localStorage.getItem("token") && localStorage.getItem("user"))
  const isAuthenticated = Boolean(localStorage.getItem("user"));

  const shouldHideLayout = isKnownPublicRoute || !isAuthenticated;

  return (
    <>
      <ToastContainer position="top-right" autoClose={3000} />
      {!shouldHideLayout && <Header />}

      <div className="app-layout">
        <div className="app-content">
          <Routes>

            {/* PUBLIC */}
            <Route path="/"           element={<Login />} />
            <Route path="/Onboarding" element={<Onboarding />} />
            <Route path="/Enrichment" element={<Enrichment />} />
            <Route path="/Otp"        element={<Otp />} />
            <Route path="/Forget"     element={<Forget />} />

            {/* PROTECTED */}
            <Route path="/Dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/LeadScoring" element={<ProtectedRoute><LeadScoring /></ProtectedRoute>} />
            <Route path="/ScoreConfiguration" element={<ProtectedRoute><ScoreConfiguration /></ProtectedRoute>} />
            <Route path="/ScoreConfiguration/values/:parameterId" element={<ProtectedRoute><ScoreValuesConfig /></ProtectedRoute>} />
            <Route path="/ICP/GenerateICP" element={<ProtectedRoute><GenerateICP /></ProtectedRoute>} />
            <Route path="/ICP/CreateIdealTAL" element={<ProtectedRoute><CreateIdealTAL /></ProtectedRoute>} />
            <Route path="/ICP" element={<ProtectedRoute><ICPScoringConfigList /></ProtectedRoute>} />
            <Route path="/ICP/values/:parameterId" element={<ProtectedRoute><ICPScoringConfig /></ProtectedRoute>} />
            <Route path="/Persona/CreatePersona" element={<ProtectedRoute><CreatePersona /></ProtectedRoute>} />
            <Route path="/Persona" element={<ProtectedRoute><PersonaScoringConfigList /></ProtectedRoute>} />
            <Route path="/persona/values/:parameterId" element={<ProtectedRoute><PersonaScoringConfig /></ProtectedRoute>} />
            <Route path="/campaigns/:campaignId" element={<ProtectedRoute><CampaignDetails /></ProtectedRoute>} />
            <Route path="/campaigns/:campaignId/companies/:companyId" element={<ProtectedRoute><CompanyDetails /></ProtectedRoute>} />
            <Route path="/leads/:leadId" element={<ProtectedRoute><LeadDetail /></ProtectedRoute>} />
            <Route path="/icp/leads/:leadId" element={<ProtectedRoute><ICPLeadAnalysis /></ProtectedRoute>} />
            <Route path="/persona-report"element={<ProtectedRoute><PersonaReportPage /></ProtectedRoute>}/>
            <Route path="/Intelligence" element={<ProtectedRoute><Intellegence /></ProtectedRoute>} />
            <Route path="/context-builder" element={<ProtectedRoute><ContextBuilder /></ProtectedRoute>} />
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