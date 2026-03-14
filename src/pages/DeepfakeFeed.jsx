import React, { useState, useEffect } from 'react';
import { Camera, AlertTriangle, ShieldAlert, Cpu, Eye, TrendingUp } from 'lucide-react';

// Demo data — shown while/if real API has no flagged claims yet
const DEMO_DEEPFAKES = [
  { id: 1, original_text: 'World leader announcing resignation in video address', source: { platform: 'twitter' }, media: { deepfake_score: 0.97, deepfake_model: 'EfficientNet-B4', type: 'video' }, verdict: { risk_score: 0.94 }, created_at: new Date(Date.now() - 120000).toISOString() },
  { id: 2, original_text: 'Celebrity endorsing cryptocurrency scheme in viral clip', source: { platform: 'youtube' }, media: { deepfake_score: 0.91, deepfake_model: 'XceptionNet', type: 'video' }, verdict: { risk_score: 0.88 }, created_at: new Date(Date.now() - 400000).toISOString() },
  { id: 3, original_text: 'Politician confession audio leaked to media organizations', source: { platform: 'telegram' }, media: { deepfake_score: 0.85, deepfake_model: 'WavLM-Audio', type: 'audio' }, verdict: { risk_score: 0.82 }, created_at: new Date(Date.now() - 900000).toISOString() },
  { id: 4, original_text: 'Scientist denying climate change findings in interview', source: { platform: 'facebook' }, media: { deepfake_score: 0.78, deepfake_model: 'EfficientNet-B4', type: 'video' }, verdict: { risk_score: 0.74 }, created_at: new Date(Date.now() - 1800000).toISOString() },
  { id: 5, original_text: 'Breaking: Fabricated attack footage shared across networks', source: { platform: 'reddit' }, media: { deepfake_score: 0.93, deepfake_model: 'XceptionNet', type: 'video' }, verdict: { risk_score: 0.91 }, created_at: new Date(Date.now() - 3600000).toISOString() },
  { id: 6, original_text: 'Synthetic news anchor reporting false emergency alert', source: { platform: 'youtube' }, media: { deepfake_score: 0.88, deepfake_model: 'FaceForensics++', type: 'video' }, verdict: { risk_score: 0.85 }, created_at: new Date(Date.now() - 7200000).toISOString() },
];

function timeAgo(iso) {
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

const scoreColor = s => s > 0.9 ? '#ff2244' : s > 0.75 ? '#ff8800' : '#ffd700';
const platformColor = { twitter: '#1DA1F2', youtube: '#FF0000', telegram: '#229ED9', facebook: '#1877F2', reddit: '#FF4500' };

const DeepfakeFeed = () => {
  const [flaggedClaims, setFlaggedClaims] = useState(DEMO_DEEPFAKES);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchDeepfakes = async () => {
      try {
        const res = await fetch('http://localhost:8000/deepfake/flagged?limit=50');
        if (res.ok) {
          const data = await res.json();
          if (data.data?.length > 0) setFlaggedClaims(data.data);
        }
      } catch {}
    };
    fetchDeepfakes();
    const iv = setInterval(fetchDeepfakes, 30000);
    return () => clearInterval(iv);
  }, []);

  const critical = flaggedClaims.filter(c => (c.media?.deepfake_score || 0) > 0.9).length;
  const avgScore = flaggedClaims.length ? (flaggedClaims.reduce((a, c) => a + (c.media?.deepfake_score || 0), 0) / flaggedClaims.length * 100).toFixed(1) : 0;

  return (
    <div style={{ padding: '24px 28px', minHeight: '100vh', background: 'var(--color-background-primary)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: '#ff6b8a' }}>
            🎭 Deepfake & Synthetic Media Radar
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--color-text-secondary)' }}>
            AI-powered detection of manipulated video, audio, and imagery
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderRadius: 24, background: 'rgba(255,34,68,0.12)', border: '1px solid rgba(255,34,68,0.3)', color: '#ff6b8a', fontWeight: 600, fontSize: 13 }}>
          <AlertTriangle size={16} />
          {flaggedClaims.length} Synthetic Threats Active
        </div>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {[
          { icon: <Camera size={20}/>, label: 'Total Flagged', value: flaggedClaims.length, color: '#ff6b8a', bg: 'rgba(255,107,138,0.1)', border: 'rgba(255,107,138,0.25)' },
          { icon: <ShieldAlert size={20}/>, label: 'Critical (>90%)', value: critical, color: '#ff2244', bg: 'rgba(255,34,68,0.1)', border: 'rgba(255,34,68,0.25)' },
          { icon: <TrendingUp size={20}/>, label: 'Avg AI Score', value: `${avgScore}%`, color: '#ff8800', bg: 'rgba(255,136,0,0.1)', border: 'rgba(255,136,0,0.25)' },
          { icon: <Cpu size={20}/>, label: 'Model', value: 'EfficientNet-B4', color: '#c084fc', bg: 'rgba(192,132,252,0.1)', border: 'rgba(192,132,252,0.25)' },
        ].map((s, i) => (
          <div key={i} style={{ background: s.bg, border: `1px solid ${s.border}`, borderRadius: 12, padding: '16px 20px', display: 'flex', gap: 14, alignItems: 'center' }}>
            <div style={{ color: s.color }}>{s.icon}</div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Threat Feed Table */}
      <div style={{ background: 'var(--color-background-secondary)', borderRadius: 12, border: '1px solid rgba(255,107,138,0.15)', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,107,138,0.1)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Eye size={18} color="#ff6b8a" />
          <span style={{ fontWeight: 600, fontSize: 15, color: '#ff6b8a' }}>Live Synthetic Media Feed</span>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'rgba(255,107,138,0.06)' }}>
              {['Claim / Content', 'Platform', 'AI Detection Score', 'Model Used', 'Media Type', 'Time'].map(h => (
                <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, color: 'var(--color-text-tertiary)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {flaggedClaims.map((claim, idx) => {
              const score = claim.media?.deepfake_score || 0;
              const plat = claim.source?.platform || 'unknown';
              return (
                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.2s' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,107,138,0.05)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={{ padding: '12px 16px', maxWidth: 280 }}>
                    <span style={{ fontSize: 13, color: 'var(--color-text-primary)', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {claim.original_text || 'Visual/Audio Media'}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600, background: `${platformColor[plat] || '#888'}22`, color: platformColor[plat] || '#aaa', textTransform: 'capitalize' }}>
                      {plat}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ width: 70, height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden', flexShrink: 0 }}>
                        <div style={{ width: `${score * 100}%`, height: '100%', background: scoreColor(score), borderRadius: 3, transition: 'width 0.5s' }} />
                      </div>
                      <span style={{ fontSize: 13, fontWeight: 700, color: scoreColor(score) }}>{(score * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ fontSize: 12, color: '#c084fc', background: 'rgba(192,132,252,0.1)', padding: '3px 8px', borderRadius: 6 }}>
                      {claim.media?.deepfake_model || 'EfficientNet-B4'}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600, background: 'rgba(255,34,68,0.15)', color: '#ff6b8a' }}>
                      <ShieldAlert size={10} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                      {claim.media?.type || 'Video'}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--color-text-tertiary)' }}>
                    {timeAgo(claim.created_at)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DeepfakeFeed;
