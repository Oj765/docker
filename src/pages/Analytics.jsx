import React from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  AreaChart, Area, PieChart, Pie, Cell, Legend
} from 'recharts';
import { ChevronDown, TrendingUp, ArrowUpRight } from 'lucide-react';
import './Analytics.css';

const viralityData = [
  { time: '12 AM', predicted: 20, actual: 15 },
  { time: '04 AM', predicted: 35, actual: 28 },
  { time: '08 AM', predicted: 45, actual: 40 },
  { time: '12 PM', predicted: 80, actual: 55 },
  { time: '04 PM', predicted: 65, actual: 70 },
  { time: '08 PM', predicted: 90, actual: 85 },
];

const platformData = [
  { name: 'Twitter', value: 30, color: '#0088FE' },
  { name: 'Reddit', value: 25, color: '#FF4500' },
  { name: 'Telegram', value: 19, color: '#0088cc' },
  { name: 'Other', value: 17, color: '#94A3B8' },
];

const topClaims = [
  { text: 'Vaccines cause are microchipped...', risk: 'Critical', riskColor: 'critical', shares: '307', time: '2m ago' },
  { text: 'Vaccines cause are microchipped...', risk: 'High', riskColor: 'high', shares: '151', time: '15m ago' },
  { text: 'Vaccines cause are microchipped...', risk: 'Critical', riskColor: 'critical', shares: '76', time: '15m ago' },
  { text: 'Vaccines cause are microchipped...', risk: 'Critical', riskColor: 'critical', shares: '24', time: '15m ago' },
];

const Analytics = () => {
  return (
    <div className="analytics-container">
      <header className="analytics-header">
        <h1>Misinformation Analytics</h1>
        <div className="header-filters">
          <div className="filter-dropdown">
            <span>Time Range: 24h</span>
            <ChevronDown size={14} />
          </div>
          <div className="filter-dropdown">
            <span>Severity: All</span>
            <ChevronDown size={14} />
          </div>
        </div>
      </header>

      <div className="analytics-grid">
        {/* Virality Prediction Chart */}
        <div className="card chart-card">
          <div className="chart-header">
            <h3>Virality Prediction Chart</h3>
            <div className="chart-legend">
              <span className="legend-item"><span className="line predicted"></span> Predicted Spread</span>
              <span className="legend-item"><span className="line actual"></span> Actual Spread</span>
            </div>
          </div>
          <div className="chart-content">
            <p className="y-axis-label">Virality Reach</p>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={viralityData}>
                <defs>
                  <linearGradient id="colorPredictedAnalytics" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#107C7C" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#107C7C" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 12 }} />
                <YAxis hide />
                <Tooltip />
                <Area type="monotone" dataKey="predicted" stroke="#107C7C" strokeWidth={2} fillOpacity={1} fill="url(#colorPredictedAnalytics)" />
                <Area type="monotone" dataKey="actual" stroke="#4FB0AE" strokeDasharray="5 5" fill="transparent" />
              </AreaChart>
            </ResponsiveContainer>
            <p className="x-axis-label">Time</p>
          </div>
        </div>

        {/* Claim Lifecycle Timeline */}
        <div className="card lifecycle-card">
          <h3>Claim Lifecycle Timeline</h3>
          <div className="lifecycle-visual">
            <svg viewBox="0 0 500 200" className="lifecycle-svg">
              {/* Main Line */}
              <path d="M 50 100 Q 150 100, 200 80 T 350 50 T 450 100" fill="none" stroke="var(--primary)" strokeWidth="2" />
              
              {/* Nodes */}
              <circle cx="50" cy="100" r="5" fill="var(--primary)" />
              <circle cx="200" cy="80" r="5" fill="var(--primary)" />
              <circle cx="280" cy="85" r="5" fill="var(--primary)" />
              <circle cx="360" cy="55" r="8" fill="var(--accent-orange)" stroke="white" strokeWidth="2" />
              
              {/* Node Labels */}
              <text x="35" y="130" fontSize="12" className="svg-text">Original Claim</text>
              <text x="180" y="55" fontSize="12" className="svg-text">First Mutation</text>
              <text x="260" y="65" fontSize="12" className="svg-text">Second Mutation</text>
              <text x="340" y="35" fontSize="12" className="svg-text font-bold" fill="var(--primary-dark)">Peak Virality</text>
              
              {/* Arrows and Variants */}
              <path d="M 210 90 L 250 130" stroke="var(--primary-light)" strokeWidth="1" fill="none" markerEnd="url(#arrow)" />
              <text x="260" y="145" fontSize="11" fill="var(--text-muted)">Variant A</text>
              
              <path d="M 370 70 L 410 110" stroke="var(--primary-light)" strokeWidth="1" fill="none" />
              <text x="415" y="125" fontSize="11" fill="var(--text-muted)">Viral Memes</text>

              <defs>
                <marker id="arrow" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto" markerUnits="strokeWidth">
                  <path d="M0,0 L0,6 L9,3 z" fill="var(--primary-light)" />
                </marker>
              </defs>
            </svg>
            <div className="lifecycle-footer">Time</div>
          </div>
        </div>

        {/* Platform Distribution */}
        <div className="card distribution-card">
          <h3>Platform Distribution</h3>
          <div className="pie-container">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={platformData}
                  cx="40%"
                  cy="50%"
                  innerRadius={0}
                  outerRadius={100}
                  paddingAngle={0}
                  dataKey="value"
                >
                  {platformData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend layout="vertical" align="right" verticalAlign="middle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Viral Claims */}
        <div className="card viral-claims-card">
          <h3>Top Viral Claims</h3>
          <div className="table-wrapper">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Claim Text</th>
                  <th>Risk Score</th>
                  <th>Shares</th>
                  <th>Detection Time</th>
                </tr>
              </thead>
              <tbody>
                {topClaims.map((claim, idx) => (
                  <tr key={idx}>
                    <td className="claim-text-cell">{claim.text}</td>
                    <td><span className={`badge badge-${claim.riskColor}`}>{claim.risk}</span></td>
                    <td className="shares-cell"><ArrowUpRight size={14} /> {claim.shares}</td>
                    <td className="time-cell">{claim.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="view-analysis-btn">View Detailed Analysis</button>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
