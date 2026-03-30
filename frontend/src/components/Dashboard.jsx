import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Dashboard = () => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('QUEUED');
  const [runId, setRunId] = useState(null);

  const handleRunAnalysis = async () => {
    try {
      const response = await axios.post('http://localhost:8000/api/v1/pipeline/run', {
        building_id: 'example-building',
        latitude: 0,
        longitude: 0
      });
      setRunId(response.data.run_id);
      setStatus('RUNNING');
    } catch (error) {
      console.error('Error starting analysis:', error);
    }
  };

  useEffect(() => {
    if (runId) {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`http://localhost:8000/api/v1/pipeline/status/${runId}`);
          setProgress(response.data.progress);
          setStatus(response.data.status);
          if (response.data.status === 'COMPLETED' || response.data.status === 'FAILED') {
            clearInterval(interval);
          }
        } catch (error) {
          console.error('Error fetching status:', error);
        }
      }, 5000);

      return () => clearInterval(interval);
    }
  }, [runId]);

  return (
    <div>
      <h1 className="text-2xl mb-4">Dashboard</h1>
      <button onClick={handleRunAnalysis} className="bg-blue-500 text-white p-2 rounded">
        Run Analysis
      </button>
      <div className="mt-4">
        <p>Status: {status}</p>
        <p>Progress: {progress}%</p>
      </div>
    </div>
  );
};

export default Dashboard;