import React, { useState, useEffect } from 'react';
import axios from 'axios';

const History = () => {
  const [historyData, setHistoryData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await axios.get('http://localhost:8000/api/v1/history');
        setHistoryData(response.data);
      } catch (error) {
        console.error('Error fetching history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  if (loading) {
    return <div className="text-slate-400">Loading history...</div>;
  }

  if (historyData.length === 0) {
    return <div className="text-slate-400">No history available.</div>;
  }

  return (
    <div className="bg-slate-900 text-slate-100 p-4">
      <h1 className="text-2xl mb-4">History</h1>
      <table className="w-full border-collapse border border-slate-700">
        <thead>
          <tr className="bg-slate-800">
            <th className="border border-slate-700 p-2">Run ID</th>
            <th className="border border-slate-700 p-2">Building</th>
            <th className="border border-slate-700 p-2">Date</th>
            <th className="border border-slate-700 p-2">Status</th>
            <th className="border border-slate-700 p-2">Duration</th>
            <th className="border border-slate-700 p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {historyData.map((item) => (
            <tr key={item.run_id} className="hover:bg-slate-800">
              <td className="border border-slate-700 p-2">{item.run_id}</td>
              <td className="border border-slate-700 p-2">{item.building}</td>
              <td className="border border-slate-700 p-2">{item.date}</td>
              <td className="border border-slate-700 p-2">{item.status}</td>
              <td className="border border-slate-700 p-2">{item.duration}</td>
              <td className="border border-slate-700 p-2">
                <button className="bg-blue-500 text-white p-2 rounded">
                  View Report
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default History;