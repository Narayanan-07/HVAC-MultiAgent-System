import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Building, Activity, ShieldCheck, FileText, UploadCloud, Play, Loader2, CheckCircle2, Circle } from 'lucide-react';

const StatCard = ({ title, value, icon: Icon, colorClass }) => (
  <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-lg flex items-center gap-4 transition-all hover:bg-slate-800/80">
    <div className={`p-3 rounded-lg ${colorClass}`}>
      <Icon className="w-6 h-6 text-white" />
    </div>
    <div>
      <h3 className="text-slate-400 text-sm font-medium">{title}</h3>
      <p className="text-2xl font-bold text-slate-100">{value}</p>
    </div>
  </div>
);

const FileUpload = ({ label, onChange, fileName }) => (
  <label className="border-2 border-dashed border-slate-600 bg-slate-900/50 rounded-xl p-6 flex flex-col items-center justify-center text-center hover:border-blue-500 hover:bg-slate-900 transition-colors cursor-pointer group">
    <input type="file" accept=".csv" onChange={onChange} className="hidden" />
    <UploadCloud className="w-8 h-8 text-slate-400 group-hover:text-blue-500 mb-2 transition-colors" />
    <p className="text-sm font-medium text-slate-300">{label}</p>
    <p className="text-xs text-slate-500 mt-1">
      {fileName ? fileName : 'Drag & drop or click'}
    </p>
  </label>
);

const PipelineStep = ({ title, desc, status, isLast }) => {
  let indicator = null;
  if (status === 'completed') {
    indicator = <CheckCircle2 className="w-6 h-6 text-green-500 z-10 bg-slate-800 rounded-full" />;
  } else if (status === 'current') {
    indicator = (
      <div className="relative z-10 flex items-center justify-center w-6 h-6 bg-slate-800 rounded-full">
        <span className="absolute w-4 h-4 bg-blue-500 rounded-full animate-ping opacity-75"></span>
        <span className="relative w-3 h-3 bg-blue-500 rounded-full"></span>
      </div>
    );
  } else {
    indicator = <Circle className="w-6 h-6 text-slate-600 z-10 bg-slate-800 rounded-full" />;
  }

  return (
    <div className="flex gap-4 relative">
      {!isLast && (
        <div className={`absolute left-3 top-6 bottom-[-24px] w-0.5 ${status === 'completed' ? 'bg-green-500' : 'bg-slate-700'}`}></div>
      )}
      <div className="flex-none mt-1">{indicator}</div>
      <div className="pb-8">
        <h4 className={`font-medium ${status === 'pending' ? 'text-slate-400' : 'text-slate-100'}`}>{title}</h4>
        <p className="text-sm text-slate-500 mt-1">{desc}</p>
      </div>
    </div>
  );
};

const Dashboard = ({ setActiveTab, setGlobalRunId }) => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('IDLE');
  const [runId, setRunId] = useState(null);

  const [buildingId, setBuildingId] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');

  const [energyFile, setEnergyFile] = useState(null);
  const [weatherFile, setWeatherFile] = useState(null);
  const [metaFile, setMetaFile] = useState(null);

  const [stats, setStats] = useState({
    buildingsAnalyzed: 0,
    successRate: 0,
    reportsGenerated: 0,
  });

  const currentDate = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get('http://localhost:8000/api/v1/pipeline/stats');
        setStats({
          buildingsAnalyzed: response.data.buildings_analyzed,
          successRate: response.data.success_rate,
          reportsGenerated: response.data.reports_generated,
        });
      } catch (err) {
        console.error('Error fetching dashboard stats:', err);
      }
    };
    fetchStats();
  }, [status]);

  const handleRunAnalysis = async () => {
    try {
      setStatus('QUEUED');
      const response = await axios.post('http://localhost:8000/api/v1/pipeline/run', {
        building_id: buildingId || 'BLDG-001',
        latitude: parseFloat(lat) || 40.7128,
        longitude: parseFloat(lon) || -74.0060
      });
      setRunId(response.data.run_id);
      setGlobalRunId(response.data.run_id);
      setStatus('RUNNING');
      setProgress(10);
    } catch (error) {
      console.error('Error starting analysis:', error);
      setStatus('FAILED');
    }
  };

  useEffect(() => {
    if (runId) {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`http://localhost:8000/api/v1/pipeline/status/${runId}`);
          setProgress(response.data.progress || 0);
          setStatus(response.data.status || 'RUNNING');

          if (response.data.status === 'COMPLETED') {
            clearInterval(interval);
            setTimeout(() => {
              setActiveTab('Report');
            }, 1500);
          } else if (response.data.status === 'FAILED') {
            clearInterval(interval);
          }
        } catch (error) {
          console.error('Error fetching status:', error);
        }
      }, 3000);

      return () => clearInterval(interval);
    }
  }, [runId, setActiveTab]);

  const steps = [
    { title: 'Data Ingestion', desc: 'Loading and preprocessing datasets' },
    { title: 'Performance Analysis', desc: 'Detecting anomalies and inefficiencies' },
    { title: 'Forecasting', desc: 'Predicting 24h-168h energy demand' },
    { title: 'Optimization', desc: 'Generating recommendations' },
    { title: 'Report Generation', desc: 'Creating decision report' },
  ];

  const getStepStatus = (index) => {
    if (status === 'IDLE' || status === 'QUEUED') return 'pending';
    if (status === 'COMPLETED') return 'completed';
    if (status === 'FAILED') {
      const currentStepIdx = Math.floor((progress / 100) * steps.length);
      if (index < currentStepIdx) return 'completed';
      return 'pending';
    }

    const currentStepIdx = Math.min(Math.floor((progress / 100) * steps.length), steps.length - 1);
    if (index < currentStepIdx) return 'completed';
    if (index === currentStepIdx) return 'current';
    return 'pending';
  };

  const statusBadge = {
    IDLE: { color: 'bg-slate-600 text-slate-200', text: 'READY' },
    QUEUED: { color: 'bg-slate-600 text-slate-200', text: 'QUEUED' },
    RUNNING: { color: 'bg-blue-500/20 text-blue-400 border border-blue-500/50', text: 'RUNNING' },
    COMPLETED: { color: 'bg-green-500/20 text-green-400 border border-green-500/50', text: 'COMPLETED' },
    FAILED: { color: 'bg-red-500/20 text-red-400 border border-red-500/50', text: 'FAILED' }
  }[status] || { color: 'bg-slate-600 text-slate-200', text: status };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">HVAC Optimization Dashboard</h1>
          <p className="text-slate-400 mt-2">{currentDate}</p>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Buildings Analyzed" value={stats.buildingsAnalyzed.toString()} icon={Building} colorClass="bg-blue-500" />
        <StatCard title="Last Run Status" value={status === 'RUNNING' ? 'Running' : (status === 'QUEUED' ? 'Queued' : status)} icon={Activity} colorClass="bg-green-500" />
        <StatCard title="Success Rate" value={`${stats.successRate}%`} icon={ShieldCheck} colorClass="bg-indigo-500" />
        <StatCard title="Reports Generated" value={stats.reportsGenerated.toString()} icon={FileText} colorClass="bg-purple-500" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Configure Analysis */}
        <div className="xl:col-span-2 bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-lg">
          <h2 className="text-xl font-semibold text-slate-100 mb-6">Configure Analysis</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <FileUpload label="Historical Data (CSV)" onChange={(e) => setEnergyFile(e.target.files[0])} fileName={energyFile?.name} />
            <FileUpload label="Weather Forecast (CSV)" onChange={(e) => setWeatherFile(e.target.files[0])} fileName={weatherFile?.name} />
            <FileUpload label="Building Metadata (CSV)" onChange={(e) => setMetaFile(e.target.files[0])} fileName={metaFile?.name} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-400">Building ID</label>
              <input
                type="text"
                value={buildingId}
                onChange={(e) => setBuildingId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2.5 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="e.g. BLDG-001"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-400">Latitude</label>
                <input
                  type="text"
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                  placeholder="40.7128"
                  className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2.5 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-400">Longitude</label>
                <input
                  type="text"
                  value={lon}
                  onChange={(e) => setLon(e.target.value)}
                  placeholder="-74.0060"
                  className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2.5 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>
            </div>
          </div>

          <button
            onClick={handleRunAnalysis}
            disabled={status === 'RUNNING' || status === 'QUEUED'}
            className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold py-4 px-6 rounded-xl shadow-lg shadow-blue-500/30 flex items-center justify-center gap-3 transition-all transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {status === 'RUNNING' || status === 'QUEUED' ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Play className="w-5 h-5 fill-current" />
            )}
            {status === 'RUNNING' || status === 'QUEUED' ? 'Analysis in Progress...' : 'Run Analysis Pipeline'}
          </button>
        </div>

        {/* Pipeline Execution */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-lg flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold text-slate-100">Pipeline Execution</h2>
            <div className={`px-3 py-1 rounded-full text-xs font-bold tracking-wider border ${statusBadge.color}`}>
              {statusBadge.text}
              {status === 'RUNNING' && <Loader2 className="w-3 h-3 inline-block ml-2 animate-spin" />}
            </div>
          </div>

          <div className="flex-1 mt-4 ml-2">
            {steps.map((step, idx) => (
              <PipelineStep
                key={idx}
                title={step.title}
                desc={step.desc}
                status={getStepStatus(idx)}
                isLast={idx === steps.length - 1}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;