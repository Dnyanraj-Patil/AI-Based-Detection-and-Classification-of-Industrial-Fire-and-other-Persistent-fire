import { BrowserRouter, Routes, Route } from "react-router-dom";

import DashboardLayout from "./layouts/DashboardLayout";
import Dashboard from "./pages/Dashboard";
import Events from "./pages/Events";
import Facilities from "./pages/Facilities";
import RiskAnalysis from "./pages/RiskAnalysis";
import EventDetailsPage from "./pages/EventDetailsPage";

import "./styles/dashboard.css";

function App() {
  return (
    <BrowserRouter>
      <DashboardLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/events" element={<Events />} />
          <Route path="/risk" element={<RiskAnalysis />} />
          <Route path="/facilities" element={<Facilities />} />
          <Route
            path="/events/:eventId"
            element={<EventDetailsPage />}
          />
        </Routes>
      </DashboardLayout>
    </BrowserRouter>
  );
}

export default App;