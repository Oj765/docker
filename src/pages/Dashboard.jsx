import React, { useState, useEffect } from 'react';
import { Download, Twitter, Send, Globe } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  AreaChart, Area
} from 'recharts';
import './Dashboard.css';

const Dashboard = () => {
  const [statCards, setStatCards] = useState([
    { label: 'Total Claims Detected', value: '-', trend: null },
    { label: 'High-Risk Claims', value: '-', trend: null },
    { label: 'Active Campaigns', value: '-', trend: null },
    { label: 'Claims Verified Today', value: '-', trend: null },
  ]);
  const [riskData, setRiskData] = useState([]);
  const [activityFeed, setActivityFeed] = useState([]);
  const [trendData, setTrendData] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('http://localhost:8000/analytics/dashboard');
        const result = await response.json();
        if (result.success && result.data) {
          setStatCards(result.data.statCards);
          setRiskData(result.data.riskData);
          setActivityFeed(result.data.activityFeed);
          setTrendData(result.data.trendData);
        }
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      }
    };
    fetchData();
    // Refresh data periodically
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  const getPlatformIcon = (platform) => {
    const p = String(platform).toLowerCase();
    if (p.includes('twitter') || p.includes('x')) return <Twitter size={16} fill="#1DA1F2" color="#1DA1F2" />;
    if (p.includes('telegram')) return <Send size={16} color="#0088cc" />;
    return <Globe size={16} color="#FF4500" />;
  };

  return (
    <div className="dashboard-content">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <button className="btn-primary">
          <Download size={18} />
          Export Data
        </button>
      </div>

      <div className="stats-grid">
        {statCards.map((stat, idx) => (
          <div key={idx} className="card stat-card">
            <p className="stat-label">{stat.label}</p>
            <h2 className="stat-value">{stat.value}</h2>
          </div>
        ))}
      </div>

      <div className="charts-row">
        <div className="card chart-card flex-2">
          <h3>Risk Distribution Chart</h3>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={riskData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748B' }} />
                <YAxis hide />
                <Tooltip cursor={{ fill: 'transparent' }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={60}>
                  {riskData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="chart-legend">
              {riskData.map((item, idx) => (
                <div key={idx} className="legend-item">
                  <span className="legend-color" style={{ backgroundColor: item.color }}></span>
                  <span className="legend-label">{item.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="card feed-card flex-3">
          <h3>Real-Time Activity Feed</h3>
          <div className="feed-table-container">
            <table className="feed-table">
              <thead>
                <tr>
                  <th>Latest flagged Claim</th>
                  <th>Risk Score</th>
                  <th>Time Detected</th>
                </tr>
              </thead>
              <tbody>
                {activityFeed.map((item, idx) => (
                  <tr key={idx}>
                    <td>
                      <div className="claim-info">
                        <span className="platform-icon">{getPlatformIcon(item.platform)}</span>
                        <div className="claim-text">
                          <p className="platform-name">{item.platform}</p>
                          <p className="claim-desc">{item.claim}</p>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`badge badge-${item.status}`}>
                        {item.score}
                      </span>
                    </td>
                    <td>
                      <p className="time-text">Time Detected</p>
                      <p className="time-value">{item.time}</p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="card trend-card">
        <div className="trend-header">
           <h3>Virality Trend Chart</h3>
           <div className="trend-legend">
             <div className="legend-item"><span className="line predicted"></span> Predicted Spread</div>
             <div className="legend-item"><span className="line actual"></span> Actual Spread</div>
           </div>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={trendData}>
              <defs>
                <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.1}/>
                  <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
              <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748B' }} />
              <YAxis hide />
              <Tooltip />
              <Area type="monotone" dataKey="predicted" stroke="var(--primary)" strokeWidth={2} fillOpacity={1} fill="url(#colorPredicted)" />
              <Area type="monotone" dataKey="actual" stroke="var(--primary-light)" strokeDasharray="5 5" fill="transparent" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
