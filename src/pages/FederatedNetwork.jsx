import React, { useState, useEffect } from 'react';
import { Network, Activity, Users, ShieldCheck, Globe, Zap, Radio, CheckCircle } from 'lucide-react';

const DEMO_NODES = [
  { node_id: 'node-in-01', display_name: 'Times Fact Lab (India)', org_type: 'Media', region: 'South Asia', trust: 0.95, detections: 1240, last_sync: '2m ago', status: 'online' },
  { node_id: 'node-eu-02', display_name: 'EU DisinfoWatch', org_type: 'NGO', region: 'Europe', trust: 0.98, detections: 890, last_sync: '5m ago', status: 'online' },
  { node_id: 'node-us-03', display_name: 'Stanford Internet Observatory', org_type: 'Research', region: 'North America', trust: 0.99, detections: 2103, last_sync: '1m ago', status: 'online' },
  { node_id: 'node-af-04', display_name: 'Africa Check Network', org_type: 'NGO', region: 'Africa', trust: 0.91, detections: 430, last_sync: '8m ago', status: 'online' },
  { node_id: 'node-ap-05', display_name: 'APTO Verification Hub', org_type: 'Media', region: 'Asia Pacific', trust: 0.87, detections: 610, last_sync: '12m ago', status: 'syncing' },
  { node_id: 'node-me-06', display_name: 'MENA Fact Alliance', org_type: 'NGO', region: 'Middle East', trust: 0.82, detections: 280, last_sync: '30m ago', status: 'online' },
  { node_id: 'node-la-07', display_name: 'Lupa Brasil', org_type: 'Media', region: 'Latin America', trust: 0.90, detections: 520, last_sync: '6m ago', status: 'online' },
];

const DEMO_HEALTH = { node_id: 'node-local', org_type: 'Research', status: 'ok', mesh_nodes: 7, detections_shared: 6073, uptime: '99.4%' };

const PULSE_EVENTS = [
  { time: '05:31', msg: 'node-us-03 shared 14 new HIGH risk detections', type: 'alert' },
  { time: '05:29', msg: 'Federated consensus reached on claim #api-9f3bc2 → FALSE', type: 'consensus' },
  { time: '05:27', msg: 'node-eu-02 synced 32 embeddings with local node', type: 'sync' },
  { time: '05:24', msg: 'node-in-01 published detection: election misinformation campaign', type: 'alert' },
  { time: '05:21', msg: 'node-af-04 joined mesh — trust verified via key exchange', type: 'join' },
  { time: '05:18', msg: 'Cross-node deduplication: 9 claims collapsed across 3 nodes', type: 'dedup' },
];

const eventColor = { alert: '#ff6b8a', consensus: '#22c97c', sync: '#60a5fa', join: '#c084fc', dedup: '#ffd700' };

export default function FederatedNetwork() {
  const [health, setHealth] = useState(DEMO_HEALTH);
  const [nodes, setNodes] = useState(DEMO_NODES);
  const [pulseIdx, setPulseIdx] = useState(0);

  useEffect(() => {
    const iv = setInterval(() => setPulseIdx(i => (i + 1) % PULSE_EVENTS.length), 3000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    Promise.all([
      fetch('http://localhost:8000/fednet/fednet/v1/health').catch(() => null),
      fetch('http://localhost:8000/fednet/fednet/v1/nodes').catch(() => null),
    ]).then(async ([hr, nr]) => {
      if (hr?.ok) { const d = await hr.json(); setHealth(prev => ({ ...DEMO_HEALTH, ...d })); }
      if (nr?.ok) { const d = await nr.json(); if (d.nodes?.length) setNodes(d.nodes); }
    });
  }, []);

  const online = nodes.filter(n => n.status !== 'offline').length;

  return (
    <div style={{ padding: '24px 28px', minHeight: '100vh', background: 'var(--color-background-primary)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: '#60a5fa' }}>
            🔗 Federated Mesh Network
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--color-text-secondary)' }}>
            Privacy-preserving cross-node misinformation detection — {online} nodes online
          </p>
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px',
          borderRadius: 24, background: 'rgba(34,201,124,0.12)',
          border: '1px solid rgba(34,201,124,0.3)', color: '#22c97c', fontWeight: 600, fontSize: 13,
        }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c97c', animation: 'pulse 1.5s infinite', display: 'inline-block' }} />
          Mesh Active — {online}/{nodes.length} Nodes
        </div>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {[
          { icon: <Globe size={20}/>, label: 'Local Node', value: health.node_id, color: '#60a5fa', bg: 'rgba(96,165,250,0.1)', border: 'rgba(96,165,250,0.25)' },
          { icon: <Users size={20}/>, label: 'Mesh Nodes', value: health.mesh_nodes ?? nodes.length, color: '#22c97c', bg: 'rgba(34,201,124,0.1)', border: 'rgba(34,201,124,0.25)' },
          { icon: <Zap size={20}/>, label: 'Detections Shared', value: (health.detections_shared || 6073).toLocaleString(), color: '#c084fc', bg: 'rgba(192,132,252,0.1)', border: 'rgba(192,132,252,0.25)' },
          { icon: <Activity size={20}/>, label: 'Mesh Uptime', value: health.uptime || '99.4%', color: '#ffd700', bg: 'rgba(255,215,0,0.1)', border: 'rgba(255,215,0,0.25)' },
        ].map((s, i) => (
          <div key={i} style={{ background: s.bg, border: `1px solid ${s.border}`, borderRadius: 12, padding: '16px 20px', display: 'flex', gap: 14, alignItems: 'center' }}>
            <div style={{ color: s.color }}>{s.icon}</div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: s.color }}>{s.value}</div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
        {/* Node table */}
        <div style={{ background: 'var(--color-background-secondary)', borderRadius: 12, border: '1px solid rgba(96,165,250,0.15)', overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(96,165,250,0.1)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Users size={16} color="#60a5fa" />
            <span style={{ fontWeight: 600, fontSize: 14, color: '#60a5fa' }}>Registered Peer Nodes</span>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'rgba(96,165,250,0.05)' }}>
                {['Node', 'Org Type', 'Region', 'Trust', 'Detections', 'Status'].map(h => (
                  <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontSize: 11, color: 'var(--color-text-tertiary)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {nodes.map((n, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.2s' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(96,165,250,0.05)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#e2e8f0' }}>{n.display_name}</div>
                    <div style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginTop: 2 }}>{n.node_id}</div>
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <span style={{ padding: '3px 8px', borderRadius: 8, fontSize: 11, fontWeight: 600, background: 'rgba(96,165,250,0.15)', color: '#60a5fa' }}>{n.org_type}</span>
                  </td>
                  <td style={{ padding: '10px 14px', fontSize: 12, color: '#aaa' }}>{n.region}</td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ width: 40, height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2 }}>
                        <div style={{ width: `${(n.trust || 0.9) * 100}%`, height: '100%', background: '#22c97c', borderRadius: 2 }} />
                      </div>
                      <span style={{ fontSize: 12, color: '#22c97c', fontWeight: 600 }}>{((n.trust || 0.9) * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px', fontSize: 13, fontWeight: 600, color: '#c084fc' }}>{(n.detections || 0).toLocaleString()}</td>
                  <td style={{ padding: '10px 14px' }}>
                    <span style={{ padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600, background: n.status === 'online' ? 'rgba(34,201,124,0.15)' : 'rgba(255,215,0,0.15)', color: n.status === 'online' ? '#22c97c' : '#ffd700' }}>
                      {n.status === 'online' ? <CheckCircle size={10} style={{ marginRight: 4, verticalAlign: 'middle' }} /> : <Radio size={10} style={{ marginRight: 4, verticalAlign: 'middle' }} />}
                      {n.status || 'online'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Live event log */}
        <div style={{ background: 'var(--color-background-secondary)', borderRadius: 12, border: '1px solid rgba(96,165,250,0.15)', overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(96,165,250,0.1)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={16} color="#60a5fa" />
            <span style={{ fontWeight: 600, fontSize: 14, color: '#60a5fa' }}>Live Mesh Events</span>
            <span style={{ marginLeft: 'auto', width: 8, height: 8, borderRadius: '50%', background: '#22c97c', animation: 'pulse 1.5s infinite' }} />
          </div>
          <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {PULSE_EVENTS.map((ev, i) => (
              <div key={i} style={{
                padding: '10px 12px', borderRadius: 8,
                background: i === pulseIdx % PULSE_EVENTS.length ? `${eventColor[ev.type]}18` : 'rgba(255,255,255,0.02)',
                border: `1px solid ${i === pulseIdx % PULSE_EVENTS.length ? eventColor[ev.type] + '55' : 'rgba(255,255,255,0.04)'}`,
                transition: 'all 0.5s',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 10, color: eventColor[ev.type], fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{ev.type}</span>
                  <span style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>{ev.time}</span>
                </div>
                <p style={{ margin: 0, fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>{ev.msg}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
