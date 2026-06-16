import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Eye, RefreshCw, Inbox, Trash2, Copy, CheckCheck } from 'lucide-react';
import { T, card } from '../theme';

const API = 'http://localhost:8000';

const StatusBadge = ({ status }) => {
  const cfg = {
    COMPLETED: { color: T.kiwi, bg: 'rgba(44,255,5,0.12)',  border: 'rgba(44,255,5,0.4)' },
    FAILED:    { color: T.red,  bg: 'rgba(255,93,93,0.12)',  border: 'rgba(255,93,93,0.4)' },
    RUNNING:   { color: T.kiwi2, bg: 'rgba(191,0,255,0.12)', border: 'rgba(191,0,255,0.4)' },
  }[status] || { color: T.soft, bg: 'rgba(120,120,120,0.12)', border: 'rgba(120,120,120,0.3)' };
  return (
    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold tracking-wide"
          style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}` }}>
      {status}
    </span>
  );
};

const History = ({ onViewReport }) => {
  const [historyData, setHistoryData] = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [searchTerm,  setSearchTerm]  = useState('');
  const [clearing,    setClearing]    = useState(false);
  const [copiedId,    setCopiedId]    = useState(null);
  const [toast,       setToast]       = useState(null);

  const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast(null), 3000); };

  const fetchHistory = async () => {
    try { setLoading(true); const r = await axios.get(`${API}/api/v1/history`); setHistoryData(r.data); }
    catch { showToast('Could not load history', 'error'); }
    finally { setLoading(false); }
  };
  useEffect(() => { fetchHistory(); }, []);

  const handleClearHistory = async () => {
    if (!window.confirm('Delete all pipeline history and report files? This cannot be undone.')) return;
    try { setClearing(true); await axios.delete(`${API}/api/v1/history`); setHistoryData([]); showToast('History cleared successfully'); }
    catch { showToast('Failed to clear history', 'error'); }
    finally { setClearing(false); }
  };

  const copyRunId = (id) => navigator.clipboard.writeText(id).then(() => { setCopiedId(id); setTimeout(() => setCopiedId(null), 1800); });
  const fmt = (iso) => iso ? new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'n/a';
  const dur = (s) => s ? (s >= 60 ? `${Math.floor(s / 60)}m ${Math.round(s % 60)}s` : `${Math.round(s)}s`) : 'n/a';
  const pretty = (id) => (id || '').replace(/_/g, ' ');

  const filtered = historyData.filter(r =>
    r.building_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.run_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 anim-fade">

      {toast && (
        <div className="fixed top-4 right-4 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl text-sm font-medium anim-pop"
             style={{ background: '#0a0a0a', border: `1px solid ${toast.type === 'error' ? '#5b1d1d' : T.borderHi}`, color: toast.type === 'error' ? T.red : T.kiwi }}>
          {toast.type === 'error' ? '✕' : '✓'} {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight" style={{ color: T.text }}>Analysis History</h1>
          <p className="text-sm mt-1" style={{ color: T.muted }}>{historyData.length} run{historyData.length !== 1 ? 's' : ''} recorded</p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:flex-none">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: T.muted }} />
            <input type="text" placeholder="Search runs" value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-2 text-sm rounded-lg w-full sm:w-52"
              style={{ background: T.surface, border: `1px solid ${T.border}`, color: T.text, outline: 'none', transition: 'border-color .15s' }}
              onFocus={e => { e.target.style.borderColor = T.kiwi; e.target.style.boxShadow = '0 0 0 2px rgba(44,255,5,0.14)'; }}
              onBlur={e => { e.target.style.borderColor = T.border; e.target.style.boxShadow = 'none'; }} />
          </div>
          <button onClick={fetchHistory} className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all"
            style={{ background: T.surface, border: `1px solid ${T.border}`, color: T.soft }}
            onMouseEnter={e => e.currentTarget.style.color = T.kiwi} onMouseLeave={e => e.currentTarget.style.color = T.soft}>
            <RefreshCw className="w-4 h-4" />
          </button>
          {historyData.length > 0 && (
            <button onClick={handleClearHistory} disabled={clearing}
              className="flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all"
              style={{ background: 'rgba(255,93,93,0.1)', border: '1px solid rgba(255,93,93,0.3)', color: T.red, cursor: clearing ? 'not-allowed' : 'pointer' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,93,93,0.2)'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,93,93,0.1)'}>
              {clearing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              <span className="hidden sm:inline">Clear History</span>
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl overflow-hidden" style={card}>
        {loading ? (
          <div className="p-16 flex flex-col items-center gap-3" style={{ color: T.muted }}>
            <RefreshCw className="w-7 h-7 animate-spin" style={{ color: T.kiwi }} /><span className="text-sm">Loading history</span>
          </div>
        ) : historyData.length === 0 ? (
          <div className="p-16 md:p-20 flex flex-col items-center justify-center text-center">
            <Inbox className="w-14 h-14 mb-4" style={{ color: '#3a3a3a' }} />
            <h3 className="text-base font-semibold mb-1" style={{ color: T.soft }}>No runs yet</h3>
            <p className="text-sm" style={{ color: T.muted }}>Go to the Dashboard and run your first analysis.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left" style={{ borderCollapse: 'collapse', minWidth: 560 }}>
              <thead>
                <tr style={{ background: '#050505', borderBottom: `1px solid ${T.border}` }}>
                  {['Run ID', 'Building', 'Started', 'Duration', 'Status', ''].map((h, i) => (
                    <th key={h || i} className={`px-4 py-3 text-xs font-bold tracking-wider uppercase ${i === 2 || i === 3 ? 'hidden md:table-cell' : ''}`} style={{ color: T.kiwi }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((item, idx) => (
                  <tr key={item.run_id} style={{ borderBottom: '1px solid #151515', background: idx % 2 === 0 ? 'transparent' : '#070707', transition: 'background .15s' }}
                      onMouseEnter={e => e.currentTarget.style.background = T.surface2}
                      onMouseLeave={e => e.currentTarget.style.background = idx % 2 === 0 ? 'transparent' : '#070707'}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <code className="text-xs px-2 py-0.5 rounded" style={{ background: T.surface2, border: `1px solid ${T.border}`, color: T.kiwi }}>{item.run_id.slice(0, 18)}…</code>
                        <button onClick={() => copyRunId(item.run_id)} title="Copy Run ID" style={{ color: copiedId === item.run_id ? T.kiwi : '#3a3a3a', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                          {copiedId === item.run_id ? <CheckCheck className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-medium text-sm" style={{ color: T.text }}>{pretty(item.building_id)}</td>
                    <td className="px-4 py-3 text-xs hidden md:table-cell" style={{ color: T.muted }}>{fmt(item.created_at)}</td>
                    <td className="px-4 py-3 text-xs hidden md:table-cell" style={{ color: T.muted }}>{dur(item.duration_s)}</td>
                    <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => onViewReport(item.run_id)} disabled={item.status !== 'COMPLETED'}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                        style={item.status === 'COMPLETED'
                          ? { border: `1px solid ${T.borderHi}`, color: T.kiwi, background: 'rgba(44,255,5,0.08)', cursor: 'pointer' }
                          : { border: `1px solid ${T.border}`, color: '#3a3a3a', background: 'transparent', cursor: 'not-allowed' }}
                        onMouseEnter={e => { if (item.status === 'COMPLETED') e.currentTarget.style.background = 'rgba(44,255,5,0.18)'; }}
                        onMouseLeave={e => { if (item.status === 'COMPLETED') e.currentTarget.style.background = 'rgba(44,255,5,0.08)'; }}>
                        <Eye className="w-3.5 h-3.5" /> <span className="hidden sm:inline">View Report</span>
                      </button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && historyData.length > 0 && (
                  <tr><td colSpan="6" className="p-10 text-center text-sm" style={{ color: T.muted }}>No results for "{searchTerm}"</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default History;
