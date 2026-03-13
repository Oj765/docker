import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import Dashboard from './pages/Dashboard';
import LiveFeed from './pages/LiveFeed';
import ClaimInvestigation from './pages/ClaimInvestigation';
import NarrativeGraph from './pages/NarrativeGraph';
import Analytics from './pages/Analytics';
import AlertConfiguration from './pages/AlertConfiguration';
import AuditLog from './pages/AuditLog';
import GeoIntelligence from './pages/GeoIntelligence';
import FederatedNetwork from './pages/FederatedNetwork';
import DeepfakeFeed from './pages/DeepfakeFeed';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app-layout">
        <Sidebar />
        <main className="main-container">
          <Topbar />
          <div className="page-content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/live-feed" element={<LiveFeed />} />
              <Route path="/investigation" element={<ClaimInvestigation />} />
              <Route path="/narrative" element={<NarrativeGraph />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/geo" element={<GeoIntelligence />} />
              <Route path="/federated" element={<FederatedNetwork />} />
              <Route path="/deepfake" element={<DeepfakeFeed />} />
              <Route path="/alerts" element={<AlertConfiguration />} />
              <Route path="/audit" element={<AuditLog />} />
              <Route path="/settings" element={<div className="p-32"><h1>Settings Page</h1></div>} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  );
}

export default App;
