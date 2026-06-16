import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FileDown, ExternalLink, AlertCircle, RefreshCw, FileText, Clock, Building } from 'lucide-react';
import { T, card, cta } from '../theme';

const API = 'http://localhost:8000';

const ReportViewer = ({ runId }) => {
  const [reportData, setReportData] = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [dlLoading,  setDlLoading]  = useState(false);

  useEffect(() => {
    const fetchReport = async () => {
      if (!runId) { setLoading(false); return; }
      try { setLoading(true); setError(null); const r = await axios.get(`${API}/api/v1/reports/${runId}`); setReportData(r.data); }
      catch { setError('Failed to load report. Please try again.'); }
      finally { setLoading(false); }
    };
    fetchReport();
  }, [runId]);

  const handleDownloadPDF = async () => {
    try {
      setDlLoading(true);
      const r = await axios.get(`${API}/api/v1/reports/${runId}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([r.data]));
      const link = document.createElement('a');
      link.href = url; link.setAttribute('download', `hvac_report_${runId}.pdf`);
      document.body.appendChild(link); link.click(); link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch { alert('PDF not available for this run yet.'); }
    finally { setDlLoading(false); }
  };

  const handleOpenBrowser = () => {
    if (!reportData?.html_content) return;
    const blob = new Blob([reportData.html_content], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    document.body.appendChild(link); link.click(); document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const pretty = (id) => (id || '').replace(/_/g, ' ');

  if (!runId) return (
    <div className="flex flex-col items-center justify-center h-[70vh] gap-4 anim-fade">
      <div className="p-5 rounded-2xl" style={card}><FileText className="w-10 h-10" style={{ color: '#3a3a3a' }} /></div>
      <h2 className="text-lg font-semibold" style={{ color: T.soft }}>No Report Selected</h2>
      <p className="text-sm text-center max-w-xs" style={{ color: T.muted }}>Run an analysis from the Dashboard or pick one from History.</p>
    </div>
  );

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-[70vh] gap-4 anim-fade">
      <RefreshCw className="w-10 h-10 animate-spin" style={{ color: T.kiwi }} />
      <p className="text-sm font-medium" style={{ color: T.muted }}>Loading report</p>
    </div>
  );

  if (error || !reportData) return (
    <div className="max-w-md mx-auto mt-24 p-8 rounded-2xl text-center anim-pop" style={{ background: '#1a0808', border: '1px solid #5b1d1d' }}>
      <AlertCircle className="w-10 h-10 mx-auto mb-4" style={{ color: T.red }} />
      <h2 className="font-semibold mb-2" style={{ color: T.red }}>Error Loading Report</h2>
      <p className="text-sm" style={{ color: T.soft }}>{error || 'Report data unavailable.'}</p>
    </div>
  );

  const generatedAt = reportData.created_at ? new Date(reportData.created_at).toLocaleString() : 'Just now';

  return (
    <div className="flex flex-col gap-5 h-full anim-fade">

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 p-5 rounded-xl" style={card}>
        <div className="flex items-start gap-4">
          <div className="p-2.5 rounded-xl flex-none" style={{ background: 'rgba(44,255,5,0.14)', border: `1px solid ${T.borderHi}` }}>
            <FileText className="w-5 h-5" style={{ color: T.kiwi }} />
          </div>
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-lg font-bold" style={{ color: T.text }}>{pretty(reportData.building_id) || 'Building Report'}</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold tracking-wide" style={{ background: 'rgba(44,255,5,0.12)', color: T.kiwi, border: `1px solid ${T.borderHi}` }}>
                {reportData.status || 'COMPLETED'}
              </span>
            </div>
            <div className="flex flex-wrap gap-4 mt-1.5 text-xs" style={{ color: T.muted }}>
              <span className="flex items-center gap-1.5"><Building className="w-3.5 h-3.5" /><code style={{ color: T.kiwi }}>{runId?.slice(0, 24)}…</code></span>
              <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" />{generatedAt}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-none w-full sm:w-auto">
          <button onClick={handleOpenBrowser}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all"
            style={{ background: T.surface2, border: `1px solid ${T.border}`, color: T.soft }}
            onMouseEnter={e => { e.currentTarget.style.color = T.text; e.currentTarget.style.borderColor = '#3a3a3a'; }}
            onMouseLeave={e => { e.currentTarget.style.color = T.soft; e.currentTarget.style.borderColor = T.border; }}>
            <ExternalLink className="w-4 h-4" /> Open in Browser
          </button>
          <button onClick={handleDownloadPDF} disabled={dlLoading}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold"
            style={{ ...cta, opacity: dlLoading ? 0.7 : 1, cursor: dlLoading ? 'not-allowed' : 'pointer' }}
            onMouseEnter={e => { if (!dlLoading) e.currentTarget.style.background = T.kiwi2; }}
            onMouseLeave={e => { if (!dlLoading) e.currentTarget.style.background = T.kiwi; }}>
            {dlLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
            {dlLoading ? 'Preparing' : 'Download PDF'}
          </button>
        </div>
      </div>

      {/* Report iframe (kept white, the printed report is intentionally light) */}
      <div className="flex-1 rounded-xl overflow-hidden" style={{ border: `1px solid ${T.border}`, minHeight: 520 }}>
        {reportData.html_content ? (
          <iframe srcDoc={reportData.html_content} title="HVAC Analysis Report" className="w-full h-full" style={{ minHeight: 520, border: 'none', background: '#fff' }} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3 p-12" style={{ color: T.muted }}>
            <AlertCircle className="w-10 h-10" style={{ color: '#3a3a3a' }} />
            <p className="text-sm">HTML report not available. The pipeline may still be generating it.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportViewer;
