import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import ReportViewer from './components/ReportViewer';
import History from './components/History';

const App = () => {
  const [activeTab, setActiveTab] = useState('Dashboard');

  const renderTab = () => {
    switch (activeTab) {
      case 'Dashboard':
        return <Dashboard />;
      case 'Report':
        return <ReportViewer />;
      case 'History':
        return <History />;
      default:
        return null;
    }
  };

  return (
    <div className="bg-slate-900 text-slate-100 min-h-screen flex">
      <nav className="w-64 bg-slate-800 p-4">
        <ul>
          <li className="mb-4">
            <button
              className={`w-full text-left p-2 rounded ${activeTab === 'Dashboard' ? 'bg-blue-500' : ''}`}
              onClick={() => setActiveTab('Dashboard')}
            >
              Dashboard
            </button>
          </li>
          <li className="mb-4">
            <button
              className={`w-full text-left p-2 rounded ${activeTab === 'Report' ? 'bg-blue-500' : ''}`}
              onClick={() => setActiveTab('Report')}
            >
              Report
            </button>
          </li>
          <li>
            <button
              className={`w-full text-left p-2 rounded ${activeTab === 'History' ? 'bg-blue-500' : ''}`}
              onClick={() => setActiveTab('History')}
            >
              History
            </button>
          </li>
        </ul>
      </nav>
      <main className="flex-1 p-4">{renderTab()}</main>
    </div>
  );
};

export default App;