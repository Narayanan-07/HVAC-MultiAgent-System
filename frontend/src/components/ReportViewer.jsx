import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ReportViewer = ({ runId }) => {
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const response = await axios.get(`http://localhost:8000/api/v1/reports/${runId}`);
        setReportData(response.data);
      } catch (error) {
        console.error('Error fetching report:', error);
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
    } catch (error) {
      console.error('Error downloading PDF:', error);
    }
  };

  if (loading) {
    return <div className="text-slate-400">Loading report...</div>;
  }

  if (!reportData) {
    return <div className="text-red-500">Failed to load report.</div>;
  }

  return (
    <div className="bg-slate-900 text-slate-100 p-4">
      <h1 className="text-2xl mb-4">Report Viewer</h1>
      <div className="mb-4">
        <p><strong>Building ID:</strong> {reportData.building_id}</p>
        <p><strong>Generated At:</strong> {reportData.generated_at}</p>
        <p><strong>Status:</strong> {reportData.status}</p>
      </div>
      <iframe
        srcDoc={reportData.html_content}
        title="Report"
        className="w-full h-96 border border-slate-700"
      ></iframe>
      <button
        onClick={handleDownloadPDF}
        className="mt-4 bg-blue-500 text-white p-2 rounded"
      >
        Download PDF
      </button>
    </div>
  );
};

export default ReportViewer;