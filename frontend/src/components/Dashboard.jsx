import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Building, Activity, ShieldCheck, FileText, Database,
  Play, Loader2, CheckCircle2, Circle, Zap, TrendingUp, Clock,
  Search, ChevronDown, MapPin, Maximize2,
} from 'lucide-react';
import { T, card, input, cta } from '../theme';

const API = 'http://localhost:8000';

const StatCard = ({ title, value, icon: Icon, accent }) => (
  <div className="flex items-center gap-3 p-3.5 rounded-xl lift" style={card}>
    <div className="p-2 rounded-lg flex-none" style={{ background: `${accent}1f`, border: `1px solid ${accent}55` }}>
      <Icon className="w-4 h-4" style={{ color: accent }} />
    </div>
    <div>
      <p className="text-xs font-medium mb-0.5" style={{ color: T.muted }}>{title}</p>
      <p className="text-xl font-bold" style={{ color: T.text }}>{value}</p>
    </div>
  </div>
);

const PipelineStep = ({ title, desc, status, isLast }) => {
  const isDone = status === 'completed';
  const isCurrent = status === 'current';
  const indicator = isDone
    ? <CheckCircle2 className="w-5 h-5 z-10" style={{ color: T.kiwi, background: T.bg, borderRadius: '50%' }} />
    : isCurrent
      ? <div className="relative z-10 w-5 h-5 flex items-center justify-center" style={{ background: T.bg, borderRadius: '50%' }}>
          <span className="absolute w-4 h-4 rounded-full animate-ping opacity-70" style={{ background: T.kiwi }}></span>
          <span className="relative w-2.5 h-2.5 rounded-full" style={{ background: T.kiwi }}></span>
        </div>
      : <Circle className="w-5 h-5 z-10" style={{ color: '#3a3a3a', background: T.bg, borderRadius: '50%' }} />;
  return (
    <div className="flex gap-3 relative">
      {!isLast && <div className="absolute left-2.5 top-5 bottom-[-14px] w-px" style={{ background: isDone ? T.kiwi : T.border }} />}
      <div className="flex-none mt-0.5">{indicator}</div>
      <div className="pb-3.5">
        <p className="text-sm font-medium leading-tight" style={{ color: isDone || isCurrent ? T.text : T.muted }}>{title}</p>
        <p className="text-xs mt-0.5" style={{ color: T.muted }}>{desc}</p>
      </div>
    </div>
  );
};

const Dashboard = ({ setActiveTab, setGlobalRunId }) => {
  const [progress, setProgress] = useState(0);
  const [status,   setStatus]   = useState('IDLE');
  const [runId,    setRunId]    = useState(null);
  const [buildings, setBuildings] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query,    setQuery]    = useState('');
  const [open,     setOpen]     = useState(false);
  const [stats,    setStats]    = useState({ buildingsAnalyzed: 0, successRate: 0, reportsGenerated: 0 });
  const [toast,    setToast]    = useState(null);

  const showToast = (msg, type = 'success') => { setToast({ msg, type }); setTimeout(() => setToast(null), 3500); };

  const fetchStats = async () => {
    try {
      const r = await axios.get(`${API}/api/v1/pipeline/stats`);
      setStats({ buildingsAnalyzed: r.data.buildings_analyzed, successRate: r.data.success_rate, reportsGenerated: r.data.reports_generated });
    } catch {}
  };
  useEffect(() => { fetchStats(); }, [status]);

  useEffect(() => {
    axios.get(`${API}/api/v1/buildings`).then(r => setBuildings(r.data)).catch(() => showToast('Could not load building list', 'error'));
  }, []);

  const prettyName = (id) => (id || '').replace(/_/g, ' ');
  // Only buildings with iKW_TR (chilled-water) data can produce a full
  // efficiency + anomaly report, so the picker offers just those.
  const analyzable = buildings.filter(b => b.has_efficiency);
  const filtered = (query ? analyzable.filter(b => b.building_id.toLowerCase().includes(query.toLowerCase())) : analyzable).slice(0, 50);

  const handleRunAnalysis = async () => {
    if (!selected) { showToast('Please select a building first', 'error'); return; }
    try {
      setStatus('QUEUED');
      const r = await axios.post(`${API}/api/v1/pipeline/run`, {
        building_id: selected.building_id,
        latitude:  selected.lat ?? null,
        longitude: selected.lng ?? null,
      });
      setRunId(r.data.run_id);
      setGlobalRunId(r.data.run_id);
      setStatus('RUNNING');
      setProgress(10);
      showToast(`Pipeline started for ${prettyName(selected.building_id)}`);
    } catch {
      setStatus('FAILED');
      showToast('Failed to start pipeline. Is the backend running?', 'error');
    }
  };

  useEffect(() => {
    if (!runId) return;
    const iv = setInterval(async () => {
      try {
        const r = await axios.get(`${API}/api/v1/pipeline/status/${runId}`);
        setProgress(r.data.progress || 0);
        setStatus(r.data.status || 'RUNNING');
        if (r.data.status === 'COMPLETED') {
          clearInterval(iv);
          showToast('Analysis complete. Loading report');
          setTimeout(() => setActiveTab('Report'), 1600);
        } else if (r.data.status === 'FAILED') {
          clearInterval(iv);
          showToast('Pipeline failed. Check backend logs.', 'error');
        }
      } catch {}
    }, 3000);
    return () => clearInterval(iv);
  }, [runId]);

  const steps = [
    { title: 'Data Ingestion',       desc: 'Loading the selected building dataset' },
    { title: 'Performance Analysis', desc: 'Isolation Forest anomaly detection' },
    { title: 'Energy Forecasting',   desc: 'Prophet and XGBoost demand prediction' },
    { title: 'Optimization',         desc: 'Setpoints, sequencing, load shifting' },
    { title: 'Report Generation',    desc: 'HTML and PDF decision report' },
  ];

  const getStepStatus = (i) => {
    if (status === 'IDLE' || status === 'QUEUED') return 'pending';
    if (status === 'COMPLETED') return 'completed';
    if (status === 'FAILED') { const cur = Math.floor((progress / 100) * steps.length); return i < cur ? 'completed' : 'pending'; }
    const cur = Math.min(Math.floor((progress / 100) * steps.length), steps.length - 1);
    if (i < cur) return 'completed';
    if (i === cur) return 'current';
    return 'pending';
  };

  const statusCfg = {
    IDLE:      { color: T.muted, bg: 'rgba(107,107,107,0.12)', label: 'READY' },
    QUEUED:    { color: T.muted, bg: 'rgba(107,107,107,0.12)', label: 'QUEUED' },
    RUNNING:   { color: T.kiwi,  bg: 'rgba(44,255,5,0.12)',   label: 'RUNNING' },
    COMPLETED: { color: T.kiwi,  bg: 'rgba(44,255,5,0.12)',   label: 'DONE' },
    FAILED:    { color: T.red,   bg: 'rgba(255,93,93,0.12)',   label: 'FAILED' },
  }[status] || { color: T.muted, bg: 'rgba(107,107,107,0.12)', label: status };

  const isRunning = status === 'RUNNING' || status === 'QUEUED';
  const onFocus = e => { e.target.style.borderColor = T.kiwi; e.target.style.boxShadow = '0 0 0 2px rgba(44,255,5,0.18)'; };
  const onBlur  = e => { e.target.style.borderColor = T.border; e.target.style.boxShadow = 'none'; };
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <div className="space-y-4 anim-fade">

      {toast && (
        <div className="fixed top-4 right-4 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl text-sm font-medium anim-pop"
             style={{ background: '#0a0a0a', border: `1px solid ${toast.type === 'error' ? '#5b1d1d' : T.borderHi}`, color: toast.type === 'error' ? T.red : T.kiwi }}>
          {toast.type === 'error' ? '✕' : '✓'} {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-end gap-3 flex-wrap">
        <div>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight" style={{ color: T.text }}>HVAC Optimization Dashboard</h1>
          <p className="text-xs mt-0.5" style={{ color: T.muted }}>{today}</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full"
             style={{ background: statusCfg.bg, color: statusCfg.color, border: `1px solid ${statusCfg.color}55` }}>
          {isRunning && <Loader2 className="w-3 h-3 animate-spin" />}
          {statusCfg.label}
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Buildings Analyzed" value={stats.buildingsAnalyzed} icon={Building}    accent={T.kiwi} />
        <StatCard title="Success Rate"        value={`${stats.successRate}%`}  icon={ShieldCheck} accent={T.kiwi2} />
        <StatCard title="Reports Generated"  value={stats.reportsGenerated}   icon={FileText}    accent={T.yellow} />
        <StatCard title="Current Status"     value={isRunning ? `${progress}%` : statusCfg.label} icon={Activity} accent={statusCfg.color} />
      </div>

      {/* Progress */}
      {isRunning && (
        <div className="rounded-xl p-4 anim-rise" style={card}>
          <div className="flex justify-between text-xs mb-2" style={{ color: T.muted }}>
            <span>Pipeline progress</span><span style={{ color: T.kiwi }}>{progress}%</span>
          </div>
          <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: T.surface3 }}>
            <div className="h-full rounded-full kiwi-shimmer transition-all duration-700" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Body */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">

        {/* Configure */}
        <div className="xl:col-span-2 rounded-xl p-5" style={card}>
          <h2 className="text-base font-semibold mb-4" style={{ color: T.text }}>Configure Analysis</h2>

          <div className="flex items-start gap-3 p-3 rounded-xl mb-4" style={{ background: T.surface2, border: `1px solid ${T.border}` }}>
            <Database className="w-4 h-4 mt-0.5 flex-none" style={{ color: T.kiwi }} />
            <div>
              <p className="text-xs font-semibold" style={{ color: T.text }}>{analyzable.length} analyzable buildings</p>
              <p className="text-xs mt-0.5" style={{ color: T.muted }}>
                Only buildings with chilled water (iKW-TR) data are listed. The analysis
                runs on that building's data only, with its location detected automatically.
              </p>
            </div>
          </div>

          {/* Building picker */}
          <div className="mb-4">
            <label className="block text-xs font-medium mb-1.5" style={{ color: T.muted }}>Building *</label>
            <div style={{ position: 'relative' }}>
              <button type="button" onClick={() => setOpen(o => !o)}
                className="w-full flex items-center justify-between gap-2 rounded-lg text-left transition-all"
                style={{ background: T.surface2, border: `1px solid ${open ? T.kiwi : T.border}`, color: selected ? T.text : T.muted, padding: '11px 14px', fontSize: 13, cursor: 'pointer' }}>
                <span className="flex items-center gap-2 truncate">
                  <Building className="w-4 h-4 flex-none" style={{ color: selected ? T.kiwi : '#4a4a4a' }} />
                  <span className="truncate">{selected ? prettyName(selected.building_id) : 'Select a building'}</span>
                </span>
                <ChevronDown className="w-4 h-4 flex-none" style={{ color: T.muted, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .15s' }} />
              </button>

              {open && (
                <div className="anim-pop" style={{ position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 30, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, boxShadow: '0 16px 48px rgba(0,0,0,0.6)', overflow: 'hidden' }}>
                  <div style={{ position: 'relative', padding: 8, borderBottom: `1px solid ${T.border}` }}>
                    <Search className="w-4 h-4" style={{ position: 'absolute', left: 18, top: '50%', transform: 'translateY(-50%)', color: '#4a4a4a' }} />
                    <input autoFocus placeholder="Search buildings" value={query} onChange={e => setQuery(e.target.value)}
                      style={{ width: '100%', background: T.bg, border: `1px solid ${T.border}`, borderRadius: 7, color: T.text, outline: 'none', padding: '8px 8px 8px 32px', fontSize: 13 }} />
                  </div>
                  <div style={{ maxHeight: 240, overflowY: 'auto' }}>
                    {filtered.length === 0 && <div style={{ padding: 16, textAlign: 'center', color: T.muted, fontSize: 12 }}>No matches</div>}
                    {filtered.map(b => (
                      <button key={b.building_id} type="button"
                        onClick={() => { setSelected(b); setOpen(false); setQuery(''); }}
                        className="w-full flex items-center justify-between gap-3 text-left"
                        style={{ padding: '9px 14px', background: selected?.building_id === b.building_id ? 'rgba(44,255,5,0.1)' : 'transparent', border: 'none', cursor: 'pointer' }}
                        onMouseEnter={e => e.currentTarget.style.background = T.surface2}
                        onMouseLeave={e => e.currentTarget.style.background = selected?.building_id === b.building_id ? 'rgba(44,255,5,0.1)' : 'transparent'}>
                        <span className="truncate" style={{ color: T.text, fontSize: 13 }}>{prettyName(b.building_id)}</span>
                        <span className="flex-none capitalize" style={{ color: T.muted, fontSize: 11 }}>{b.usage || b.type || ''}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {selected && (
              <div className="flex flex-wrap gap-2 mt-3 anim-fade">
                {selected.usage && (
                  <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs" style={{ background: T.surface2, color: T.soft, border: `1px solid ${T.border}` }}>
                    <Building className="w-3 h-3" /> {selected.usage}
                  </span>
                )}
                {selected.sqm && (
                  <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs" style={{ background: T.surface2, color: T.soft, border: `1px solid ${T.border}` }}>
                    <Maximize2 className="w-3 h-3" /> {selected.sqm.toLocaleString()} m²
                  </span>
                )}
                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs" style={{ background: T.surface2, color: selected.lat ? T.kiwi : T.soft, border: `1px solid ${T.border}` }}>
                  <MapPin className="w-3 h-3" /> {selected.lat ? `${selected.lat.toFixed(2)}, ${selected.lng.toFixed(2)}` : 'Location auto detected'}
                </span>
              </div>
            )}
          </div>

          <button onClick={handleRunAnalysis} disabled={isRunning}
            className="w-full flex items-center justify-center gap-2.5 py-3 px-6 rounded-xl font-semibold text-sm"
            style={isRunning
              ? { background: T.surface2, color: '#4a4a4a', cursor: 'not-allowed', border: `1px solid ${T.border}` }
              : cta}
            onMouseDown={e => { if (!isRunning) e.currentTarget.style.transform = 'scale(0.98)'; }}
            onMouseUp={e => { if (!isRunning) e.currentTarget.style.transform = 'scale(1)'; }}
            onMouseEnter={e => { if (!isRunning) e.currentTarget.style.background = T.kiwi2; }}
            onMouseLeave={e => { if (!isRunning) { e.currentTarget.style.background = T.kiwi; e.currentTarget.style.transform = 'scale(1)'; } }}>
            {isRunning ? <><Loader2 className="w-4 h-4 animate-spin" />Analysis in Progress</> : <><Play className="w-4 h-4 fill-current" />Run Analysis Pipeline</>}
          </button>
        </div>

        {/* Pipeline steps */}
        <div className="rounded-xl p-5 flex flex-col" style={card}>
          <h2 className="text-base font-semibold mb-4" style={{ color: T.text }}>Pipeline Execution</h2>
          <div className="flex-1 ml-1">
            {steps.map((s, i) => <PipelineStep key={i} title={s.title} desc={s.desc} status={getStepStatus(i)} isLast={i === steps.length - 1} />)}
          </div>
        </div>
      </div>

      {/* Info strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { icon: Zap,        label: 'LLM Primary',     value: 'Groq · Llama 3.3 70B', accent: T.kiwi },
          { icon: TrendingUp, label: 'Forecast Models', value: 'Prophet and XGBoost',  accent: T.kiwi2 },
          { icon: Clock,      label: 'Avg Run Time',    value: '5 to 7 minutes',        accent: T.yellow },
        ].map(({ icon: Icon, label, value, accent }) => (
          <div key={label} className="flex items-center gap-3 px-4 py-2.5 rounded-xl lift" style={card}>
            <Icon className="w-4 h-4 flex-none" style={{ color: accent }} />
            <div>
              <p className="text-xs" style={{ color: T.muted }}>{label}</p>
              <p className="text-xs font-semibold" style={{ color: T.soft }}>{value}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;
