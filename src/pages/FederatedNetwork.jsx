import React, { useState, useEffect } from 'react';
import { Network, Activity, Users, ShieldCheck } from 'lucide-react';
import './Dashboard.css'; // Reuse dashboard styles for cards

const FederatedNetwork = () => {
  const [health, setHealth] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [healthRes, nodesRes] = await Promise.all([
          fetch('http://localhost:8000/fednet/fednet/v1/health').catch(() => null),
          fetch('http://localhost:8000/fednet/fednet/v1/nodes').catch(() => null)
        ]);

        if (healthRes && healthRes.ok) {
          const healthData = await healthRes.json();
          setHealth(healthData);
        }

        if (nodesRes && nodesRes.ok) {
          const nodesData = await nodesRes.json();
          setNodes(nodesData.nodes || []);
        }
      } catch (error) {
        console.error('Error fetching federated network data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000); // 30s polling
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="dashboard-content" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <h2>Loading Federated Network Data...</h2>
      </div>
    );
  }

  return (
    <div className="dashboard-content">
      <div className="dashboard-header">
        <h1>Federated Mesh Network</h1>
        <button className="btn-primary" style={{ backgroundColor: health?.status === 'ok' ? '#2cf3e0' : '#ff3d71' }}>
          <Network size={18} />
          {health?.status === 'ok' ? 'Network Active' : 'Network Offline'}
        </button>
      </div>

      <div className="stats-grid">
        <div className="card stat-card">
          <p className="stat-label">Local Node ID</p>
          <h2 className="stat-value" style={{ fontSize: '1.5rem', color: '#2cf3e0' }}>{health?.node_id || 'Unknown'}</h2>
        </div>
        <div className="card stat-card">
          <p className="stat-label">Organization Type</p>
          <h2 className="stat-value">{health?.org_type || 'Unknown'}</h2>
        </div>
        <div className="card stat-card">
          <p className="stat-label">Active Mesh Nodes</p>
          <h2 className="stat-value">{health?.mesh_nodes ?? nodes.length}</h2>
        </div>
        <div className="card stat-card">
          <p className="stat-label">Mesh Health</p>
          <h2 className="stat-value" style={{ color: health?.status === 'ok' ? '#00e096' : '#ff3d71' }}>
            {health?.status ? health.status.toUpperCase() : 'OFFLINE'}
          </h2>
        </div>
      </div>

      <div className="charts-row" style={{ marginTop: '24px' }}>
        <div className="card feed-card" style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Users size={20} color="#2cf3e0" />
            <h3 style={{ margin: 0 }}>Registered Peer Nodes</h3>
          </div>
          <div className="feed-table-container">
            <table className="feed-table">
              <thead>
                <tr>
                  <th>Node ID</th>
                  <th>Display Name</th>
                  <th>Org Type</th>
                  <th>Region</th>
                  <th>Trust Level</th>
                </tr>
              </thead>
              <tbody>
                {nodes.length > 0 ? nodes.map((n, idx) => (
                  <tr key={idx}>
                    <td style={{ color: '#ccc' }}>{n.node_id}</td>
                    <td style={{ color: '#fff', fontWeight: 'bold' }}>{n.display_name}</td>
                    <td><span className="badge" style={{ background: 'rgba(44, 243, 224, 0.2)', color: '#2cf3e0' }}>{n.org_type || 'NGO'}</span></td>
                    <td style={{ color: '#aaa' }}>{n.region || 'Global'}</td>
                    <td><span className="badge badge-high">Trusted</span></td>
                  </tr>
                )) : <tr><td colSpan="5" style={{ textAlign: 'center', padding: '20px', color: '#888' }}>No peer nodes found in the mesh.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FederatedNetwork;
