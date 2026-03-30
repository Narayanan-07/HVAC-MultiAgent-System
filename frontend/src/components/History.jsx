import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { History as HistoryIcon, Search, Eye, RefreshCw, Inbox } from 'lucide-react';

const History = ({ onViewReport }) => {
  const [historyData, setHistoryData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await axios.get('http://localhost:8000/api/v1/history');
      setHistoryData(response.data);
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      COMPLETED: 'bg-green-500/20 text-green-400 border-green-500/50',
      FAILED: 'bg-red-500/20 text-red-400 border-red-500/50',
      RUNNING: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
    };
    const currentStyle = styles[status] || 'bg-slate-500/20 text-slate-400 border-slate-500/50';

    return (
      <span className={`px-2.5 py-1 rounded-full text-xs font-bold tracking-wider border ${currentStyle}`}>
        {status}
      </span>
    );
  };

  const filteredData = historyData.filter(item =>
    item.building?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.run_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Analysis History</h1>
          <p className="text-slate-400 mt-2">View and manage past optimization runs</p>
        </div>

        <div className="relative">
          <Search className="w-5 h-5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by ID or building..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full sm:w-64 transition-all shadow-lg"
          />
        </div>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl shadow-lg overflow-hidden">
        {loading ? (
          <div className="p-12 flex justify-center text-slate-400">
            <RefreshCw className="w-8 h-8 animate-spin" />
          </div>
        ) : historyData.length === 0 ? (
          <div className="p-16 flex flex-col items-center justify-center text-center">
            <Inbox className="w-16 h-16 text-slate-600 mb-4" />
            <h3 className="text-xl font-semibold text-slate-200 mb-2">No analysis runs yet</h3>
            <p className="text-slate-500 max-w-sm">
              Your history is empty. Go to the dashboard to run your first HVAC optimization analysis.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900/50 border-b border-slate-700">
                  <th className="p-4 text-sm font-semibold text-slate-300">Run ID</th>
                  <th className="p-4 text-sm font-semibold text-slate-300">Building</th>
                  <th className="p-4 text-sm font-semibold text-slate-300">Date</th>
                  <th className="p-4 text-sm font-semibold text-slate-300">Duration</th>
                  <th className="p-4 text-sm font-semibold text-slate-300">Status</th>
                  <th className="p-4 text-sm font-semibold text-slate-300 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {filteredData.map((item, index) => (
                  <tr
                    key={item.run_id}
                    className={`hover:bg-slate-700/30 transition-colors ${index % 2 === 0 ? 'bg-transparent' : 'bg-slate-900/20'}`}
                  >
                    <td className="p-4">
                      <span className="font-mono text-xs px-2 py-1 bg-slate-900 rounded text-slate-400 border border-slate-700">
                        {item.run_id}
                      </span>
                    </td>
                    <td className="p-4 font-medium text-slate-200">{item.building}</td>
                    <td className="p-4 text-slate-400 text-sm">{item.date}</td>
                    <td className="p-4 text-slate-400 text-sm">{item.duration}</td>
                    <td className="p-4">
                      {getStatusBadge(item.status)}
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => onViewReport(item.run_id)}
                        disabled={item.status !== 'COMPLETED'}
                        className="inline-flex items-center gap-2 px-3 py-1.5 border border-blue-500 text-blue-400 hover:bg-blue-500 hover:text-white rounded-lg transition-all text-sm font-medium disabled:opacity-50 disabled:border-slate-600 disabled:text-slate-500 disabled:hover:bg-transparent"
                      >
                        <Eye className="w-4 h-4" />
                        View Report
                      </button>
                    </td>
                  </tr>
                ))}
                {filteredData.length === 0 && historyData.length > 0 && (
                  <tr>
                    <td colSpan="6" className="p-8 text-center text-slate-500">
                      No results found for "{searchTerm}"
                    </td>
                  </tr>
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