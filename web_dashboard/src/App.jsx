import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ControlCenter from './pages/ControlCenter';
import ScanResults from './pages/ScanResults';

import DataIngestPage from './pages/DataIngest';

import ChartPage from './pages/ChartPage';

import Login from './components/Login';

function App() {
  const [token, setToken] = React.useState(localStorage.getItem('admin_key'));

  if (!token) {
    return <Login onLogin={() => setToken(localStorage.getItem('admin_key'))} />;
  }

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<ControlCenter />} />
          <Route path="/charts" element={<ChartPage />} />
          <Route path="/scan" element={<ScanResults />} />
          <Route path="/ingest" element={<DataIngestPage />} />
          {/* Stubs for other routes redirect to Scan for now */}
          <Route path="/swing" element={<Navigate to="/scan" />} />
          <Route path="/breakouts" element={<Navigate to="/scan" />} />
          <Route path="/options" element={<Navigate to="/scan" />} />
          <Route path="/settings" element={<div className="p-6">Settings Coming Soon</div>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
