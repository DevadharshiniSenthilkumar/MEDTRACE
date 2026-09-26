import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import LandingPage from "./pages/LandingPage";
import DashboardPage from "./pages/DashboardPage";
import RescueQueuePage from "./pages/RescueQueuePage";
import CaseDetailPage from "./pages/CaseDetailPage";
import TransferPage from "./pages/TransferPage";
import SimulatorPage from "./pages/SimulatorPage";
import FacilityDetailPage from "./pages/FacilityDetailPage";
import SurplusExplorerPage from "./pages/SurplusExplorerPage";
import RootCausesPage from "./pages/RootCausesPage";
import HistoryPage from "./pages/HistoryPage";

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/rescue-queue" element={<RescueQueuePage />} />
          <Route path="/cases/:caseId" element={<CaseDetailPage />} />
          <Route path="/cases/:caseId/transfer" element={<TransferPage />} />
          <Route path="/cases/:caseId/simulate" element={<SimulatorPage />} />
          <Route path="/facilities/:facilityId" element={<FacilityDetailPage />} />
          <Route path="/surplus" element={<SurplusExplorerPage />} />
          <Route path="/root-causes" element={<RootCausesPage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </main>
    </div>
  );
}
