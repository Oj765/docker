import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  ChevronDown, 
  RefreshCcw, 
  Twitter, 
  ChevronRight,
  Activity
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './LiveFeed.css';

// Custom Reddit Icon for better accuracy
const RedditIcon = ({ size = 24, color = "#FF4500" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
    <path d="M12 0c-6.627 0-12 5.373-12 12s5.373 12 12 12 12-5.373 12-12-5.373-12-12-12zm3.328 17.135c-1.336 0-2.433-.243-3.328-.243-.896 0-1.992.243-3.328.243-1.638 0-2.964-1.326-2.964-2.964 0-1.285.823-2.384 1.968-2.791-.122-.442-.187-.904-.187-1.379 0-2.618 2.308-4.735 5.151-4.735s5.151 2.117 5.151 4.735c0 .475-.065.937-.187 1.379 1.145.407 1.968 1.506 1.968 2.791 0 1.638-1.326 2.964-2.964 2.964zm-3.328-11.233c-.707 0-1.281.574-1.281 1.281 0 .707.574 1.281 1.281 1.281s1.281-.574 1.281-1.281c0-.707-.574-1.281-1.281-1.281zm0 5.487c-1.408 0-2.738.318-3.793.874-.183-.497-.279-1.028-.279-1.578 0-1.919 1.706-3.473 3.804-3.473s3.804 1.554 3.804 3.473c0 .55-.096 1.081-.279 1.578-1.055-.556-2.385-.874-3.793-.874zm4.846 3.125c0 .707-.574 1.281-1.281 1.281s-1.281-.574-1.281-1.281.574-1.281 1.281-1.281 1.281.574 1.281 1.281zm-9.692 0c0-.707.574-1.281 1.281-1.281s1.281.574 1.281 1.281-.574 1.281-1.281 1.281-1.281-.574-1.281-1.281z"/>
  </svg>
);

const LiveFeed = () => {
  const navigate = useNavigate();
  const [claims, setClaims] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    // Connect to WebSocket — server sends cached claims on connect + live stream
    connectWebSocket();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    ws.current = new WebSocket('ws://localhost:8000/ws/live-claims');

    ws.current.onopen = () => {
      setIsConnected(true);
      console.log('Connected to Live Claims WebSocket');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Ignore server keepalive pings
      if (data.type === 'ping') return;
      // Prepend the new claim, keeping only the latest 50
      setClaims(prev => [data, ...prev].slice(0, 50));
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected. Reconnecting in 5s...');
      setTimeout(connectWebSocket, 5000);
    };
  };

  const getRiskClass = (level) => {
    switch(level?.toLowerCase()) {
      case 'critical': return 'badge-critical';
      case 'high': return 'badge-high';
      case 'medium': return 'badge-medium';
      default: return 'badge-low';
    }
  };

  const timeAgo = (isoString) => {
    if (!isoString) return '';
    // Handle legacy "Xm ago" strings that are not ISO format
    if (!isoString.includes('T')) return isoString;
    const diff = Math.floor((Date.now() - new Date(isoString)) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  };

  return (
    <div className="live-feed-container">
      <div className="main-feed-column">
        <header className="feed-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h1>Live Claim Monitoring</h1>
            <div style={{ 
              display: 'flex', alignItems: 'center', gap: '6px', 
              fontSize: '12px', fontWeight: 'bold', 
              color: isConnected ? '#22c55e' : '#f59e0b',
              backgroundColor: isConnected ? '#f0fdf4' : '#fef3c7',
              padding: '4px 10px', borderRadius: '12px', border: `1px solid ${isConnected ? '#bbf7d0' : '#fde68a'}`
            }}>
              <Activity size={14} className={isConnected ? "pulse-anim" : ""} />
              {isConnected ? 'LIVE STREAM CONNECTED' : 'CONNECTING...'}
            </div>
          </div>
          <div className="filter-bar">
            {/* Filter controls remain purely visual for now */}
            <div className="filter-group">
              <label>Platform</label>
              <div className="platform-selector">
                <Twitter size={18} />
                <span>All Sources</span>
                <ChevronDown size={14} />
              </div>
            </div>

            <div className="filter-group">
              <label>Risk Level</label>
              <div className="risk-filters">
                <div className="risk-dot critical"></div>
                <div className="risk-dot high"></div>
                <div className="risk-dot medium"></div>
                <div className="risk-dot low"></div>
                <span>All Levels</span>
                <ChevronDown size={14} />
              </div>
            </div>

            <div className="filter-group search-box">
              <label>Search Live Stream</label>
              <input type="text" placeholder="Keywords..." />
            </div>
          </div>
        </header>

        <div className="claims-list">
          {claims.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
              <RefreshCcw className={!isConnected ? "spin-anim" : ""} size={32} style={{ marginBottom: '16px' }} />
              <p>Waiting for data stream...</p>
            </div>
          ) : (
            claims.map((claim) => (
              <div key={claim.id} className="claim-card fade-in">
                <div className="platform-icon-box">
                  {claim.platform?.toLowerCase() === 'twitter' ? (
                    <Twitter size={36} color="#48A1E6" fill="#48A1E6" strokeWidth={1} />
                  ) : claim.platform?.toLowerCase() === 'reddit' ? (
                    <RedditIcon size={36} />
                  ) : (
                    <div style={{ width: 36, height: 36, borderRadius: '50%', backgroundColor: '#e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: '#6b7280'}}>
                      {claim.platform?.substring(0, 1).toUpperCase() || 'W'}
                    </div>
                  )}
                </div>
                <div className="claim-content">
                  <p className="claim-text">
                    <strong>Claim:</strong> {claim.claim}
                  </p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                    {claim.source_org && (
                      <span style={{
                        fontSize: '11px', fontWeight: '700', padding: '2px 8px',
                        borderRadius: '4px', backgroundColor: '#eff6ff',
                        color: '#1d4ed8', border: '1px solid #bfdbfe', letterSpacing: '0.05em'
                      }}>
                        {claim.source_org}
                      </span>
                    )}
                    {claim.fact_check_url && (
                      <a href={claim.fact_check_url} target="_blank" rel="noopener noreferrer"
                        style={{ fontSize: '11px', color: '#6b7280', textDecoration: 'underline' }}>
                        View Fact-Check →
                      </a>
                    )}
                  </div>
                </div>
                <div className="claim-data">
                  <div className="data-top">
                    {claim.risk_level === 'pending' || !claim.risk_score ? (
                      <span style={{
                        padding: '6px 14px', borderRadius: '20px', fontSize: '12px',
                        fontWeight: '700', backgroundColor: '#f3f4f6', color: '#6b7280',
                        border: '1px dashed #d1d5db', whiteSpace: 'nowrap'
                      }}>
                        ⏳ Pending ML Analysis
                      </span>
                    ) : (
                      <span className={`risk-pill ${getRiskClass(claim.risk_level)}`}>
                        {claim.risk_score} — {claim.risk_level?.toUpperCase()}
                      </span>
                    )}
                    <div className="meta-stack">
                      {claim.confidence && (
                        <span className="conf-text">{(claim.confidence * 100).toFixed(0)}% Conf.</span>
                      )}
                      <span className="time-text">{timeAgo(claim.timestamp)}</span>
                    </div>
                  </div>
                  <div className="data-bottom">
                    {claim.estimated_impressions
                      ? <span>Est. {claim.estimated_impressions.toLocaleString()} impressions</span>
                      : <span style={{ color: '#9ca3af', fontSize: '12px' }}>Impressions: awaiting model</span>
                    }
                  </div>
                </div>
                <div className="action-box">
                  <button 
                    className="view-details-btn"
                    onClick={() => navigate('/investigation', { state: { claim } })}
                  >
                    View Details
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <aside className="insights-sidebar">
        <h2>Quick Statistics & Insights</h2>
        
        <div className="card insight-card">
          <h3>Stream Status</h3>
          <p className="insight-subtitle">Messages flowing per minute</p>
          <p className="stat-large">{isConnected ? '20+' : '0'}</p>
          
          <div className="divider"></div>
          
          <h3>Highest Risk Claim (Active)</h3>
          <p className="claim-snippet">
            {claims.length > 0 ? claims.reduce((prev, current) => (prev.risk_score > current.risk_score) ? prev : current).claim : 'Awaiting data...'}
          </p>
        </div>

        <div className="card insight-card">
          <h3>Trending Topics</h3>
          <ul className="trending-list">
            <li><a href="#">#Vaccines</a></li>
            <li><a href="#">#Elections</a></li>
            <li><a href="#">#Conspiracy</a></li>
            <li><a href="#">#5GTowers</a></li>
            <li><a href="#">#FakeNewsNet</a></li>
          </ul>
        </div>

        <div className="card insight-card">
          <h3>Risk Color Badges (Key)</h3>
          <div className="risk-key-grid">
            <div className="key-item">
              <span className="dot dot-critical"></span>
              <span className="badge badge-critical">Critical</span>
            </div>
            <div className="key-item">
              <span className="dot dot-high"></span>
              <span className="badge badge-high">High</span>
            </div>
            <div className="key-item">
              <span className="dot dot-medium"></span>
              <span className="badge badge-medium">Medium</span>
            </div>
            <div className="key-item">
              <span className="dot dot-low"></span>
              <span className="badge badge-low">Low</span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
};

export default LiveFeed;
