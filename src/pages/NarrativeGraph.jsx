import React, { useState, useEffect, useRef, useCallback } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
import NodeDetailPanel from '../components/NodeDetailPanel';

// ─── Rich demo data ───────────────────────────────────────────────────────────
const DEMO_DATA = {
  nodes: [
    // Accounts
    { id: 'acc_botnet_us',    label: '@AmericanTruth2024',   type: 'account', platform: 'twitter',  followers: 84000,  role: 'hub' },
    { id: 'acc_botnet_ru',    label: '@RealFactsDaily_RU',  type: 'account', platform: 'telegram', followers: 120000, role: 'hub' },
    { id: 'acc_influencer',   label: '@HealthFreedomNow',   type: 'account', platform: 'twitter',  followers: 230000, role: 'amplifier' },
    { id: 'acc_news_fake',    label: '@GlobalNewsUpdate24', type: 'account', platform: 'facebook', followers: 50000,  role: 'spreader' },
    { id: 'acc_anon',         label: '@anon_leaks_9x',      type: 'account', platform: 'reddit',   followers: 12000,  role: 'spreader' },
    { id: 'acc_disinfo_1',    label: '@VaccineInfoHub',     type: 'account', platform: 'telegram', followers: 67000,  role: 'spreader' },
    // Claims
    { id: 'claim_001', label: 'mRNA vaccines permanently alter your DNA',              type: 'claim', platform: 'twitter',  severity: 'CRITICAL', risk_score: 0.95, verdict: 'FALSE' },
    { id: 'claim_002', label: 'Election machines were hacked in 12 swing states',      type: 'claim', platform: 'facebook', severity: 'CRITICAL', risk_score: 0.91, verdict: 'FALSE' },
    { id: 'claim_003', label: '5G towers are causing bird deaths worldwide',            type: 'claim', platform: 'telegram', severity: 'HIGH',     risk_score: 0.78, verdict: 'FALSE' },
    { id: 'claim_004', label: 'WHO secretly approved population control vaccines',      type: 'claim', platform: 'twitter',  severity: 'CRITICAL', risk_score: 0.93, verdict: 'FALSE' },
    { id: 'claim_005', label: 'Microchips found in COVID vaccines under microscope',   type: 'claim', platform: 'reddit',   severity: 'HIGH',     risk_score: 0.82, verdict: 'FALSE' },
    { id: 'claim_006', label: 'Chemtrails contain mind-control nanobots',             type: 'claim', platform: 'facebook', severity: 'HIGH',     risk_score: 0.76, verdict: 'FALSE' },
    { id: 'claim_007', label: 'Climate data has been falsified by 130+ scientists',   type: 'claim', platform: 'twitter',  severity: 'MEDIUM',   risk_score: 0.61, verdict: 'MISLEADING' },
    { id: 'claim_008', label: 'Leaked emails show vote manipulation plans',            type: 'claim', platform: 'telegram', severity: 'CRITICAL', risk_score: 0.88, verdict: 'FALSE' },
    { id: 'claim_009', label: 'New study: wearing masks causes oxygen deprivation',    type: 'claim', platform: 'twitter',  severity: 'MEDIUM',   risk_score: 0.65, verdict: 'MISLEADING' },
    { id: 'claim_010', label: 'Mutation: mRNA vaccines cause fertility issues in men', type: 'claim', platform: 'twitter',  severity: 'HIGH',     risk_score: 0.80, verdict: 'FALSE' },
  ],
  links: [
    // Posted by
    { source: 'acc_botnet_ru',   target: 'claim_001', type: 'POSTED',   burst_detected: true  },
    { source: 'acc_botnet_us',   target: 'claim_002', type: 'POSTED',   burst_detected: true  },
    { source: 'acc_news_fake',   target: 'claim_003', type: 'POSTED',   burst_detected: false },
    { source: 'acc_botnet_ru',   target: 'claim_004', type: 'POSTED',   burst_detected: true  },
    { source: 'acc_anon',        target: 'claim_005', type: 'POSTED',   burst_detected: false },
    { source: 'acc_news_fake',   target: 'claim_006', type: 'POSTED',   burst_detected: false },
    { source: 'acc_botnet_us',   target: 'claim_007', type: 'POSTED',   burst_detected: false },
    { source: 'acc_disinfo_1',   target: 'claim_008', type: 'POSTED',   burst_detected: true  },
    { source: 'acc_anon',        target: 'claim_009', type: 'POSTED',   burst_detected: false },
    // Amplified
    { source: 'acc_influencer',  target: 'claim_001', type: 'AMPLIFIED', burst_detected: true },
    { source: 'acc_influencer',  target: 'claim_004', type: 'AMPLIFIED', burst_detected: true },
    { source: 'acc_botnet_us',   target: 'claim_003', type: 'AMPLIFIED', burst_detected: false },
    // Mutations (claim_001 mutated into claim_010)
    { source: 'claim_001', target: 'claim_010', type: 'MUTATION', burst_detected: false },
    { source: 'claim_002', target: 'claim_008', type: 'MUTATION', burst_detected: false },
  ],
};

// ─── Colors ───────────────────────────────────────────────────────────────────
const SEVERITY_COLOR = {
  CRITICAL: '#ef4444',
  HIGH:     '#f87171',
  MEDIUM:   '#4ade80',
  LOW:      '#22c55e',
  default:  '#888',
};
const LINK_COLOR = {
  POSTED:    '#22c55e',
  AMPLIFIED: '#ef4444',
  MUTATION:  '#b91c1c',
};
const ACC_COLOR  = '#16a34a';

function severityColor(s) { return SEVERITY_COLOR[s?.toUpperCase()] || SEVERITY_COLOR.default; }

// ─── Stats sidebar ────────────────────────────────────────────────────────────
function StatsPanel({ data }) {
  const claims   = data.nodes.filter(n => n.type === 'claim');
  const accounts = data.nodes.filter(n => n.type === 'account');
  const critical = claims.filter(n => n.severity === 'CRITICAL').length;
  const high     = claims.filter(n => n.severity === 'HIGH').length;
  const medium   = claims.filter(n => n.severity === 'MEDIUM').length;
  const bursts   = data.links.filter(l => l.burst_detected).length;

  const row = (color, label, val) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
        <div style={{ width: 9, height: 9, borderRadius: '50%', background: color, boxShadow: `0 0 6px ${color}88` }} />
        <span style={{ fontSize: 12, color: '#475569' }}>{label}</span>
      </div>
      <span style={{ fontSize: 13, fontWeight: 700, color: '#1e293b' }}>{val}</span>
    </div>
  );

  return (
    <div style={{
      position: 'absolute', top: 80, right: 16, zIndex: 20, width: 200,
      background: 'rgba(255,255,255,0.88)', border: '1px solid rgba(0,0,0,0.1)',
      borderRadius: 12, padding: '14px 16px', backdropFilter: 'blur(14px)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#ef4444', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 12 }}>Graph Stats</div>
      {row('#94a3b8',   'Total Nodes',   data.nodes.length)}
      {row(ACC_COLOR,   'Accounts',      accounts.length)}
      {row(LINK_COLOR.POSTED,   'Claims',        claims.length)}
      {row(SEVERITY_COLOR.CRITICAL, 'Critical',  critical)}
      {row(SEVERITY_COLOR.HIGH,     'High Risk', high)}
      {row(SEVERITY_COLOR.MEDIUM,   'Medium',    medium)}
      {row(LINK_COLOR.AMPLIFIED,  'Burst Links',  bursts)}
      <div style={{ borderTop: '1px solid rgba(0,0,0,0.08)', marginTop: 10, paddingTop: 10 }}>
        {row(LINK_COLOR.POSTED,    'Posted',    data.links.filter(l=>l.type==='POSTED').length)}
        {row(LINK_COLOR.AMPLIFIED, 'Amplified', data.links.filter(l=>l.type==='AMPLIFIED').length)}
        {row(LINK_COLOR.MUTATION,  'Mutation',  data.links.filter(l=>l.type==='MUTATION').length)}
      </div>
    </div>
  );
}

// ─── Legend ───────────────────────────────────────────────────────────────────
function Legend() {
  const s = { display: 'flex', alignItems: 'center', gap: 7, marginBottom: 7 };
  const dot = (color, shape) => (
    <div style={{
      width: shape === 'diamond' ? 10 : 10, height: 10,
      background: color,
      borderRadius: shape === 'circle' ? '50%' : shape === 'diamond' ? 2 : 2,
      transform: shape === 'diamond' ? 'rotate(45deg)' : 'none',
      boxShadow: `0 0 8px ${color}aa`,
      flexShrink: 0,
    }} />
  );
  return (
    <div style={{
      position: 'absolute', bottom: 16, left: 16, zIndex: 20,
      background: 'rgba(255,255,255,0.88)', border: '1px solid rgba(0,0,0,0.1)',
      borderRadius: 10, padding: '12px 16px', backdropFilter: 'blur(12px)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#ef4444', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 10 }}>Legend</div>
      <div style={s}>{dot(ACC_COLOR, 'circle')}<span style={{fontSize:11,color:'#475569'}}>Account Node</span></div>
      <div style={s}>{dot(SEVERITY_COLOR.CRITICAL,'diamond')}<span style={{fontSize:11,color:'#475569'}}>CRITICAL Claim</span></div>
      <div style={s}>{dot(SEVERITY_COLOR.HIGH,'diamond')}<span style={{fontSize:11,color:'#475569'}}>HIGH Claim</span></div>
      <div style={s}>{dot(SEVERITY_COLOR.MEDIUM,'diamond')}<span style={{fontSize:11,color:'#475569'}}>MEDIUM Claim</span></div>
      <div style={{ borderTop:'1px solid rgba(0,0,0,0.08)', margin:'8px 0' }} />
      <div style={s}><div style={{width:22,height:2,background:LINK_COLOR.POSTED,borderRadius:1}}/><span style={{fontSize:11,color:'#475569'}}>Posted</span></div>
      <div style={s}><div style={{width:22,height:2,background:LINK_COLOR.AMPLIFIED,borderRadius:1}}/><span style={{fontSize:11,color:'#475569'}}>Amplified</span></div>
      <div style={s}><div style={{width:22,height:2,background:LINK_COLOR.MUTATION,borderRadius:1}}/><span style={{fontSize:11,color:'#475569'}}>Mutation</span></div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function NarrativeGraph3D() {
  const fgRef = useRef();
  const [graphData, setGraphData] = useState(DEMO_DATA);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({ timeRange: '24h', platform: 'all', severity: 'all' });

  // Fetch real data, keep demo as fallback
  const fetchGraph = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams(filters).toString();
      const res = await fetch(`http://localhost:8000/graph?${params}`);
      const json = await res.json();
      if (json.success && json.data?.nodes?.length > 2) {
        setGraphData(json.data);
      }
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchGraph(); }, [filters]);

  // Start autorotate after mount
  useEffect(() => {
    const t = setTimeout(() => {
      if (fgRef.current) {
        fgRef.current.controls().autoRotate = true;
        fgRef.current.controls().autoRotateSpeed = 0.6;
      }
    }, 600);
    return () => clearTimeout(t);
  }, []);

  // Node 3D object
  const nodeThreeObject = useCallback((node) => {
    const color = node.type === 'account' ? ACC_COLOR : severityColor(node.severity);
    const size  = node.type === 'account'
      ? Math.max(5, Math.sqrt(node.followers || 5000) / 20 + 4)
      : 6 + (node.risk_score || 0.5) * 8;

    let geo;
    if (node.type === 'account') {
      if (node.role === 'hub') geo = new THREE.BoxGeometry(size, size, size);
      else geo = new THREE.SphereGeometry(size, 16, 16);
    } else {
      geo = new THREE.OctahedronGeometry(size);
    }

    // Glow material
    const mat = new THREE.MeshPhongMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.6,
      transparent: true,
      opacity: 0.92,
      shininess: 80,
    });

    const mesh = new THREE.Mesh(geo, mat);

    // Outer glow halo
    const haloGeo = node.type === 'account'
      ? new THREE.SphereGeometry(size * 1.6, 12, 12)
      : new THREE.SphereGeometry(size * 1.5, 12, 12);
    const haloMat = new THREE.MeshBasicMaterial({
      color, transparent: true, opacity: 0.09, side: THREE.BackSide,
    });
    const halo = new THREE.Mesh(haloGeo, haloMat);
    mesh.add(halo);

    return mesh;
  }, []);

  const nodeLabel = useCallback((node) => {
    if (node.type === 'account') {
      return `<div style="background:rgba(255,255,255,0.92);padding:8px 12px;border-radius:6px;border:1px solid ${ACC_COLOR};font-family:sans-serif;box-shadow:0 2px 8px rgba(0,0,0,0.1)">
        <b style="color:${ACC_COLOR}">${node.label}</b><br/>
        <span style="color:#64748b;font-size:11px">Platform: ${node.platform} &nbsp;|&nbsp; Role: ${node.role}</span><br/>
        <span style="color:#475569;font-size:11px">Followers: ${(node.followers||0).toLocaleString()}</span>
      </div>`;
    }
    const c = severityColor(node.severity);
    return `<div style="background:rgba(255,255,255,0.92);padding:8px 12px;border-radius:6px;border:1px solid ${c};font-family:sans-serif;max-width:220px;box-shadow:0 2px 8px rgba(0,0,0,0.1)">
      <b style="color:${c}">${node.severity} CLAIM</b><br/>
      <span style="color:#1e293b;font-size:12px;line-height:1.4">${node.label}</span><br/>
      <span style="color:#64748b;font-size:11px;margin-top:4px;display:block">Verdict: ${node.verdict||'UNVERIFIED'} &nbsp;|&nbsp; Risk: ${((node.risk_score||0)*100).toFixed(0)}%</span>
    </div>`;
  }, []);

  const filterSel = { background: '#ffffff', color: '#1e293b', border: '1px solid rgba(0,0,0,0.15)', padding: '5px 10px', borderRadius: 6, outline: 'none', fontSize: 12, cursor: 'pointer' };
  const optStyle  = { background: '#ffffff', color: '#1e293b' };

  return (
    <div style={{ position: 'relative', width: '100%', height: 'calc(100vh - 56px)', overflow: 'hidden', background: '#f8fafc' }}>
      
      {/* Light theme faint background texture/blobs */}
      <div style={{ position:'absolute', width:500, height:500, borderRadius:'50%', background:'radial-gradient(circle, rgba(34,197,94,0.06) 0%, transparent 70%)', top:'10%', left:'20%', pointerEvents:'none' }}/>
      <div style={{ position:'absolute', width:400, height:400, borderRadius:'50%', background:'radial-gradient(circle, rgba(239,68,68,0.06) 0%, transparent 70%)', bottom:'10%', right:'25%', pointerEvents:'none' }}/>
      <div style={{ position:'absolute', width:300, height:300, borderRadius:'50%', background:'radial-gradient(circle, rgba(248,113,113,0.05) 0%, transparent 70%)', top:'30%', right:'10%', pointerEvents:'none' }}/>

      {/* Top bar */}
      <div style={{
        position:'absolute', top:0, left:0, right:0, zIndex:30,
        background:'rgba(255,255,255,0.9)', borderBottom:'1px solid rgba(0,0,0,0.08)',
        backdropFilter:'blur(16px)', padding:'10px 20px',
        display:'flex', alignItems:'center', gap:16,
      }}>
        <div style={{ marginRight:'auto' }}>
          <span style={{ fontWeight:700, fontSize:15, color:'#1e293b', letterSpacing:'0.02em' }}>🕸 Narrative Propagation Graph</span>
          <span style={{ fontSize:11, color:'#64748b', marginLeft:12 }}>
            {graphData.nodes.length} nodes · {graphData.links.length} links
            {loading && ' · updating...'}
          </span>
        </div>

        <select value={filters.timeRange} onChange={e=>setFilters(f=>({...f,timeRange:e.target.value}))} style={filterSel}>
          {[['1h','1h'],['6h','6h'],['24h','24h'],['7d','7d']].map(([v,l])=><option key={v} value={v} style={optStyle}>{l}</option>)}
        </select>
        <select value={filters.platform} onChange={e=>setFilters(f=>({...f,platform:e.target.value}))} style={filterSel}>
          {[['all','All Platforms'],['twitter','Twitter'],['telegram','Telegram'],['facebook','Facebook'],['reddit','Reddit']].map(([v,l])=><option key={v} value={v} style={optStyle}>{l}</option>)}
        </select>
        <select value={filters.severity} onChange={e=>setFilters(f=>({...f,severity:e.target.value}))} style={filterSel}>
          {[['all','All Severity'],['critical','Critical'],['high','High'],['medium','Medium'],['low','Low']].map(([v,l])=><option key={v} value={v} style={optStyle}>{l}</option>)}
        </select>
      </div>

      {/* 3D Graph */}
      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        nodeLabel={nodeLabel}
        nodeThreeObject={nodeThreeObject}
        nodeThreeObjectExtend={false}
        linkColor={link => LINK_COLOR[link.type] || '#888'}
        linkWidth={link => link.type === 'MUTATION' ? 2.5 : link.type === 'AMPLIFIED' ? 2 : 1.5}
        linkOpacity={0.9}
        linkDirectionalParticles={link => link.burst_detected ? 5 : link.type === 'MUTATION' ? 2 : 0}
        linkDirectionalParticleWidth={3}
        linkDirectionalParticleSpeed={0.006}
        linkDirectionalParticleColor={link => link.burst_detected ? '#b91c1c' : LINK_COLOR[link.type] || '#555'}
        backgroundColor="rgba(0,0,0,0)"
        onNodeClick={node => {
          fgRef.current?.cameraPosition(
            { x: node.x * 1.6, y: node.y * 1.6, z: node.z * 1.6 },
            node, 1000
          );
          setSelectedNode(node);
        }}
        onBackgroundClick={() => setSelectedNode(null)}
        width={window.innerWidth}
        height={window.innerHeight - 56}
      />

      {/* Stats panel */}
      <StatsPanel data={graphData} />

      {/* Legend */}
      <Legend />

      {/* Selected node detail */}
      {selectedNode && (
        <NodeDetailPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          isMobile={false}
        />
      )}

      {/* Title watermark */}
      <div style={{
        position:'absolute', bottom:16, right:16, zIndex:20,
        fontSize:11, color:'rgba(0,0,0,0.3)', fontWeight:600, letterSpacing:'0.15em', textTransform:'uppercase',
      }}>
        Misinfo Shield · Narrative Engine
      </div>
    </div>
  );
}