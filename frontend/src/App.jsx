import React, { useState } from 'react';
import { Cpu, LayoutDashboard, FileText, History as HistoryIcon } from 'lucide-react';
import Dashboard from './components/Dashboard';
import ReportViewer from './components/ReportViewer';
import History from './components/History';
import { T } from './theme';

const App = () => {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [runId, setRunId] = useState(null);

  const renderTab = () => {
    switch (activeTab) {
      case 'Dashboard': return <Dashboard setActiveTab={setActiveTab} setGlobalRunId={setRunId} />;
      case 'Report':    return <ReportViewer runId={runId} />;
      case 'History':   return <History onViewReport={(id) => { setRunId(id); setActiveTab('Report'); }} />;
      default:          return null;
    }
  };

  const navItems = [
    { id: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'Report',    label: 'Report',    icon: FileText },
    { id: 'History',   label: 'History',   icon: HistoryIcon },
  ];

  const NavButton = ({ item, mobile }) => {
    const active = activeTab === item.id;
    const Icon = item.icon;
    return (
      <button
        onClick={() => setActiveTab(item.id)}
        className={`flex items-center gap-3 rounded-xl font-medium transition-all duration-200 ${mobile ? 'flex-col gap-1 flex-1 py-2 text-[11px]' : 'w-full px-4 py-2.5 text-sm'}`}
        style={active
          ? { background: T.kiwi, color: '#000', boxShadow: '0 4px 16px rgba(44,255,5,0.25)' }
          : { color: T.muted, background: 'transparent', border: '1px solid transparent' }}
        onMouseEnter={e => { if (!active) { e.currentTarget.style.background = T.surface2; e.currentTarget.style.color = T.text; } }}
        onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = T.muted; } }}
      >
        <Icon className={mobile ? 'w-5 h-5' : 'w-4 h-4 flex-none'} />
        {item.label}
      </button>
    );
  };

  return (
    <div className="min-h-screen flex" style={{ background: T.bg, color: T.text }}>

      {/* ── Desktop sidebar ── */}
      <nav className="hidden md:flex w-60 flex-none flex-col" style={{ background: '#050505', borderRight: `1px solid ${T.border}` }}>
        <div className="px-5 py-5 flex items-center gap-3" style={{ borderBottom: `1px solid ${T.border}` }}>
          <div className="flex items-center justify-center w-9 h-9 rounded-xl anim-pop" style={{ background: T.kiwi, boxShadow: '0 0 20px rgba(44,255,5,0.35)' }}>
            <Cpu className="w-5 h-5" style={{ color: '#000' }} />
          </div>
          <div>
            <div className="text-base font-bold tracking-tight" style={{ color: T.kiwi }}>HVAC AI</div>
            <div className="text-xs" style={{ color: T.muted }}>Intelligence Platform</div>
          </div>
        </div>

        <ul className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item, i) => (
            <li key={item.id} className="anim-rise" style={{ animationDelay: `${i * 60}ms` }}>
              <NavButton item={item} />
            </li>
          ))}
        </ul>

        <div className="px-4 py-4" style={{ borderTop: `1px solid ${T.border}` }}>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: T.surface2 }}>
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ background: T.kiwi }}></span>
              <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: T.kiwi }}></span>
            </span>
            <span className="text-xs font-medium" style={{ color: T.kiwi }}>Systems Online</span>
          </div>
        </div>
      </nav>

      {/* ── Mobile top brand bar ── */}
      <div className="md:hidden fixed top-0 inset-x-0 z-40 flex items-center gap-2.5 px-4 py-3"
           style={{ background: 'rgba(5,5,5,0.92)', backdropFilter: 'blur(8px)', borderBottom: `1px solid ${T.border}` }}>
        <div className="flex items-center justify-center w-7 h-7 rounded-lg" style={{ background: T.kiwi }}>
          <Cpu className="w-4 h-4" style={{ color: '#000' }} />
        </div>
        <span className="text-sm font-bold tracking-tight" style={{ color: T.kiwi }}>HVAC AI</span>
      </div>

      {/* ── Main content ── */}
      <main className="flex-1 overflow-y-auto" style={{ background: T.bg }}>
        <div key={activeTab} className="anim-fade max-w-7xl mx-auto px-4 md:px-8 pt-16 pb-24 md:py-8">
          {renderTab()}
        </div>
      </main>

      {/* ── Mobile bottom nav ── */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 flex items-stretch gap-1 px-2 py-1.5"
           style={{ background: 'rgba(5,5,5,0.95)', backdropFilter: 'blur(8px)', borderTop: `1px solid ${T.border}` }}>
        {navItems.map(item => <NavButton key={item.id} item={item} mobile />)}
      </nav>
    </div>
  );
};

export default App;
