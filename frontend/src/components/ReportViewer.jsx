import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FileDown, ExternalLink, AlertCircle, RefreshCw } from 'lucide-react';

const ReportViewer = ({ runId }) => {
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchReport = async () => {
      if (!runId) {
        setLoading(false);
        return;
      }
      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`http://localhost:8000/api/v1/reports/${runId}`);
        setReportData(response.data);
      } catch (err) {
        console.error('Error fetching report:', err);
        setError('Failed to load report data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [runId]);

  const handleDownloadPDF = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/v1/reports/${runId}/pdf`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${runId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error('Error downloading PDF:', err);
    }
  };

  const handleOpenBrowser = () => {
    if (reportData && reportData.html_content) {
      const blob = new Blob([reportData.html_content], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  };

  if (!runId) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] text-slate-400">
        <AlertCircle className="w-16 h-16 mb-4 text-slate-600" />
        <h2 className="text-xl font-semibold text-slate-200">No Report Selected</h2>
        <p className="mt-2 text-slate-500">Run an analysis from the Dashboard or select one from History.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] text-slate-400">
        <RefreshCw className="w-12 h-12 mb-4 text-blue-500 animate-spin" />
        <h2 className="text-lg font-medium">Processing Report Document...</h2>
      </div>
    );
  }

  if (error || !reportData) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-center max-w-lg mx-auto mt-20">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-lg font-semibold text-red-400 mb-2">Error Loading Report</h2>
        <p className="text-slate-300">{error || 'Report data is unavailable.'}</p>
      </div>
    );
  }

  const generatedDate = new Date(reportData.generated_at).toLocaleString();

  return (
    <div className="h-full flex flex-col space-y-6">
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-lg flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-100">{reportData.building_id || 'Building Report'}</h1>
            <span className="px-3 py-1 bg-green-500/20 text-green-400 border border-green-500/50 rounded-full text-xs font-bold tracking-wider">
              {reportData.status || 'COMPLETED'}
            </span>
          </div>
          <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
            <p>Run ID: <span className="font-mono text-slate-300">{runId}</span></p>
            <span className="w-1 h-1 bg-slate-600 rounded-full"></span>
            <p>Generated: <span className="text-slate-300">{generatedDate}</span></p>
          </div>
        </div>
      </div>

      <div className="flex-1 bg-white rounded-xl overflow-hidden shadow-lg border border-slate-700 min-h-[500px]">
        <iframe
          srcDoc={reportData.html_content}
          title="Analysis Report"
          className="w-full h-full bg-white"
        />
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 shadow-lg flex justify-end gap-4">
        <button
          onClick={handleOpenBrowser}
          className="px-6 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors flex items-center gap-2 font-medium"
        >
          <ExternalLink className="w-4 h-4" />
          Open in Browser
        </button>
        <button
          onClick={handleDownloadPDF}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors shadow-lg shadow-blue-500/20 flex items-center gap-2 font-medium"
        >
          <FileDown className="w-4 h-4" />
          Download PDF
        </button>
      </div>
    </div>
  );
};

export default ReportViewer;