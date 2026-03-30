import React, { useState } from 'react';
import { Cpu, LayoutDashboard, FileText, History as HistoryIcon } from 'lucide-react';
import Dashboard from './components/Dashboard';
import ReportViewer from './components/ReportViewer';
import History from './components/History';

const App = () => {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [runId, setRunId] = useState(null);

  const renderTab = () => {
    switch (activeTab) {
      case 'Dashboard':
        return <Dashboard setActiveTab={setActiveTab} setGlobalRunId={setRunId} />;
      case 'Report':
        return <ReportViewer runId={runId} />;
      case 'History':
        return <History onViewReport={(id) => { setRunId(id); setActiveTab('Report'); }} />;
      default:
        return null;
    }
  };

  const navItems = [
    { id: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'Report', label: 'Report', icon: FileText },
    { id: 'History', label: 'History', icon: HistoryIcon },
  ];

  return (
    <div className="bg-slate-950 text-slate-100 min-h-screen flex font-sans">
      {/* Sidebar */}
      <nav className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col transition-all duration-300">
        <div className="p-6 flex items-center gap-3 border-b border-slate-800">
          <div className="bg-blue-500/10 p-2 rounded-lg">
            <Cpu className="text-blue-500 w-6 h-6" />
          </div>
          <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">HVAC AI</span>
        </div>
        <ul className="flex-1 px-4 py-6 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <li key={item.id}>
                <button
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                    isActive 
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' 
                      : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span className="font-medium">{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Main Content */}
      <main className="flex-1 h-screen overflow-y-auto bg-slate-950">
        <div className="p-8 max-w-7xl mx-auto transition-opacity duration-500">
          {renderTab()}
        </div>
      </main>
    </div>
  );
};

export default App;