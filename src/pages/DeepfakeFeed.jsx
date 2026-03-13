import React, { useState, useEffect } from 'react';
import { Camera, AlertTriangle, ShieldAlert, Cpu } from 'lucide-react';
import './Dashboard.css'; // Reusing dashboard styles

const DeepfakeFeed = () => {
  const [flaggedClaims, setFlaggedClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDeepfakes = async () => {
      try {
        const res = await fetch('http://localhost:8000/deepfake/flagged?limit=50');
        if (res.ok) {
          const data = await res.json();
          setFlaggedClaims(data.data || []);
        }
      } catch (error) {
        console.error('Error fetching deepfakes:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchDeepfakes();
    const interval = setInterval(fetchDeepfakes, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="dashboard-content" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <h2>Loading Deepfake Radar...</h2>
      </div>
    );
  }

  return (
    <div className="dashboard-content">
      <div className="dashboard-header">
        <h1>Deepfake & Synthetic Media Radar</h1>
        <button className="btn-primary" style={{ backgroundColor: '#ff3d71' }}>
          <AlertTriangle size={18} />
          {flaggedClaims.length} Threats Detected
        </button>
      </div>

      <div className="stats-grid">
        <div className="card stat-card border-accent" style={{ borderLeft: '4px solid #ff3d71' }}>
          <p className="stat-label">Total Flagged Media</p>
          <h2 className="stat-value">{flaggedClaims.length}</h2>
        </div>
        <div className="card stat-card">
          <p className="stat-label">Critical Confidence</p>
          <h2 className="stat-value">
            {flaggedClaims.filter(c => c.media?.deepfake_score > 0.9).length}
          </h2>
        </div>
        <div className="card stat-card">
          <p className="stat-label">Model in Use</p>
          <h2 className="stat-value" style={{ fontSize: '1.2rem' }}>EfficientNet-B4 (FF++)</h2>
        </div>
      </div>

      <div className="charts-row" style={{ marginTop: '24px' }}>
        <div className="card feed-card" style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Camera size={20} color="#ff3d71" />
            <h3 style={{ margin: 0 }}>Recent Deepfake Detections</h3>
          </div>
          
          <div className="feed-table-container">
            <table className="feed-table">
              <thead>
                <tr>
                  <th>Media Context</th>
                  <th>Source Platform</th>
                  <th>Detection Score</th>
                  <th>AI Model</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {flaggedClaims.length > 0 ? flaggedClaims.map((claim, idx) => (
                  <tr key={idx}>
                    <td>
                      <div className="claim-info">
                        <Cpu size={16} color="#aaa" />
                        <div className="claim-text">
                          <p className="claim-desc" style={{ maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {claim.original_text || "Visual Media Only"}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span style={{ textTransform: 'capitalize', color: '#2cf3e0' }}>
                        {claim.source?.platform || 'Unknown'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '60px', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${claim.media?.deepfake_score * 100}%`, height: '100%', background: claim.media?.deepfake_score > 0.85 ? '#ff3d71' : '#ffa500' }}></div>
                        </div>
                        <span style={{ fontSize: '0.85rem' }}>{(claim.media?.deepfake_score * 100).toFixed(1)}%</span>
                      </div>
                    </td>
                    <td><span className="badge" style={{ background: 'rgba(255, 255, 255, 0.1)', color: '#ccc' }}>{claim.media?.deepfake_model || 'Unknown'}</span></td>
                    <td>
                      <span className="badge" style={{ background: 'rgba(255, 61, 113, 0.2)', color: '#ff3d71' }}>
                        <ShieldAlert size={12} style={{ marginRight: '4px' }} />
                        Synthetic
                      </span>
                    </td>
                  </tr>
                )) : <tr><td colSpan="5" style={{ textAlign: 'center', padding: '20px', color: '#888' }}>No synthetic media detected recently.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeepfakeFeed;
