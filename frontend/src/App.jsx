import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import Overview from "./pages/Overview.jsx";
import UniverseList from "./pages/UniverseList.jsx";
import UniverseDetail from "./pages/UniverseDetail.jsx";
import NetworkGraph from "./pages/NetworkGraph.jsx";
import Autopsy from "./pages/Autopsy.jsx";
import Recommendations from "./pages/Recommendations.jsx";
import Mutations from "./pages/Mutations.jsx";
import SimulationLive from "./pages/SimulationLive.jsx";
import Backtesting from "./pages/Backtesting.jsx";
import SAR from "./pages/SAR.jsx";
import Chat from "./pages/Chat.jsx";
import Explainability from "./pages/Explainability.jsx";
import Cases from "./pages/Cases.jsx";
import DriftMonitor from "./pages/DriftMonitor.jsx";
import ParetoFrontier from "./pages/ParetoFrontier.jsx";
import ThresholdSimulator from "./pages/ThresholdSimulator.jsx";
import EntityResolution from "./pages/EntityResolution.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-surface">
          <Routes>
            <Route path="/"                element={<Navigate to="/overview" replace />} />
            <Route path="/overview"        element={<Overview />} />
            <Route path="/universes"       element={<UniverseList />} />
            <Route path="/universes/:id"   element={<UniverseDetail />} />
            <Route path="/network"             element={<NetworkGraph />} />
            <Route path="/graph"               element={<NetworkGraph />} />
            <Route path="/pareto"              element={<ParetoFrontier />} />
            <Route path="/autopsy"             element={<Autopsy />} />
            <Route path="/cases"               element={<Cases />} />
            <Route path="/sar"                 element={<SAR />} />
            <Route path="/recommendations"     element={<Recommendations />} />
            <Route path="/entity"              element={<EntityResolution />} />
            <Route path="/entity-resolution"   element={<EntityResolution />} />
            <Route path="/explainability"      element={<Explainability />} />
            <Route path="/drift"               element={<DriftMonitor />} />
            <Route path="/threshold"           element={<ThresholdSimulator />} />
            <Route path="/thresholds"          element={<ThresholdSimulator />} />
            <Route path="/live"            element={<SimulationLive />} />
            <Route path="/backtesting"     element={<Backtesting />} />
            <Route path="/mutations"       element={<Mutations />} />
            <Route path="/chat"            element={<Chat />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
