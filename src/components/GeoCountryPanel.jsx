// frontend/src/components/GeoCountryPanel.jsx
// Slide-in panel shown when user clicks a country on the heatmap
// Deps: recharts

import { useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import { useCountryDetail } from '../hooks/useGeo';

const COLORS = {
  risk:       '#C0395A',
  multiplier: '#534AB7',
  bar:        '#1D9E75',
  election:   '#534AB7',
  conflict:   '#BA7517',
  health:     '#1D9E75',
};

const ALIGNMENT_COLORS = {
  left:                   '#378ADD',
  'center-left':          '#85B7EB',
  center:                 '#888780',
  'center-right':         '#EF9F27',
  right:                  '#E24B4A',
  nationalist:            '#A32D2D',
  populist:               '#D85A30',
  'religious-conservative':'#854F0B',
  libertarian:            '#639922',
  authoritarian:          '#3C3489',
};

const VERDICT_COLORS = {
  FALSE:       '#C0395A',
  MISLEADING:  '#BA7517',
  UNVERIFIED:  '#888780',
  TRUE:        '#1D9E75',
};

export default function GeoCountryPanel({ countryCode, onClose }) {
  const [days, setDays] = useState(7);
  const { data: res, isLoading } = useCountryDetail(countryCode, days);

  const detail = res?.data || res;

  const s = {
    panel: {
      position: 'fixed', right: 0, top: 0, bottom: 0, width: 420,
      background: 'var(--color-background-primary)',
      borderLeft: '1px solid var(--color-border-secondary)',
      overflowY: 'auto', zIndex: 100, padding: '24px 20px',
      display: 'flex', flexDirection: 'column', gap: 20,
    },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
    title: { fontSize: 22, fontWeight: 500, color: 'var(--color-text-primary)' },
    close: {
      cursor: 'pointer', fontSize: 18, color: 'var(--color-text-secondary)',
      background: 'none', border: 'none', padding: '4px 8px',
    },
    section: {
      background: 'var(--color-background-secondary)',
      borderRadius: 8, padding: '14px 16px',
    },
    sectionTitle: {
      fontSize: 11, fontWeight: 500, letterSpacing: '0.08em',
      color: 'var(--color-text-tertiary)', textTransform: 'uppercase', marginBottom: 12,
    },
    dayToggle: { display: 'flex', gap: 4, marginBottom: 12 },
    dayBtn: (active) => ({
      padding: '3px 10px', borderRadius: 4, fontSize: 12, cursor: 'pointer',
      border: '1px solid var(--color-border-secondary)',
      background: active ? '#C0395A' : 'transparent',
      color: active ? '#fff' : 'var(--color-text-secondary)',
    }),
    claimCard: {
      padding: '10px 12px', borderRadius: 6, marginBottom: 8,
      background: 'var(--color-background-primary)',
      border: '1px solid var(--color-border-tertiary)',
    },
    claimText: {
      fontSize: 12, color: 'var(--color-text-primary)',
      lineHeight: 1.5, marginBottom: 6,
      display: '-webkit-box', WebkitLineClamp: 2,
      WebkitBoxOrient: 'vertical', overflow: 'hidden',
    },
    badge: (color) => ({
      display: 'inline-block', padding: '2px 8px', borderRadius: 4,
      fontSize: 10, fontWeight: 500, background: color + '22', color,
    }),
    electionCard: {
      padding: '8px 12px', borderRadius: 6, marginBottom: 8,
      background: '#EEEDFE', border: '1px solid #AFA9EC',
    },
  };

  return (
    <div style={s.panel}>
      <div style={s.header}>
        <span style={s.title}>{countryCode}</span>
        <button style={s.close} onClick={onClose}>✕</button>
      </div>

      {isLoading ? (
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 13 }}>Loading...</div>
      ) : !detail ? (
        <div style={{ color: 'var(--color-text-tertiary)', fontSize: 13 }}>No data available</div>
      ) : (
        <>
          {/* Election alerts */}
          {detail.active_elections?.length > 0 && (
            <div style={s.section}>
              <div style={s.sectionTitle}>Election proximity</div>
              {detail.active_elections.map((e, i) => (
                <div key={i} style={s.electionCard}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 12, fontWeight: 500, color: '#3C3489' }}>
                      {e.country_code} election
                    </span>
                    <span style={{ fontSize: 12, color: '#534AB7' }}>
                      {e.days_away}d away
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: '#534AB7', marginTop: 2 }}>
                    {e.election_date}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Risk timeline */}
          <div style={s.section}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={s.sectionTitle}>Risk timeline</div>
              <div style={s.dayToggle}>
                {[7, 14, 30].map(d => (
                  <button key={d} style={s.dayBtn(days === d)} onClick={() => setDays(d)}>
                    {d}d
                  </button>
                ))}
              </div>
            </div>
            {detail.timeline?.length > 0 ? (
              <ResponsiveContainer width="100%" height={140}>
                <AreaChart data={detail.timeline.map(t => ({
                  date: t.bucket?.slice(0, 10),
                  risk: parseFloat((t.avg_risk * 100).toFixed(1)),
                  claims: t.claim_count,
                }))}>
                  <defs>
                    <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={COLORS.risk} stopOpacity={0.25} />
                      <stop offset="95%" stopColor={COLORS.risk} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-tertiary)" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} />
                  <YAxis tick={{ fontSize: 10 }} tickLine={false} domain={[0, 100]} unit="%" />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid var(--color-border-secondary)' }}
                    formatter={(v, n) => [n === 'risk' ? v + '%' : v, n === 'risk' ? 'Avg risk' : 'Claims']}
                  />
                  <Area type="monotone" dataKey="risk" stroke={COLORS.risk} strokeWidth={1.5} fill="url(#riskGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>No timeline data</div>
            )}
          </div>

          {/* Political alignment */}
          {detail.alignment_breakdown?.length > 0 && (
            <div style={s.section}>
              <div style={s.sectionTitle}>Political alignment</div>
              <ResponsiveContainer width="100%" height={120}>
                <BarChart data={detail.alignment_breakdown} layout="vertical">
                  <XAxis type="number" tick={{ fontSize: 10 }} tickLine={false} />
                  <YAxis type="category" dataKey="political_alignment" tick={{ fontSize: 10 }} width={110} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 6 }}
                    formatter={(v) => [v, 'Claims']}
                  />
                  <Bar dataKey="count" radius={[0, 3, 3, 0]}
                    fill={COLORS.bar}
                    label={{ position: 'right', fontSize: 10 }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Recent claims */}
          {detail.recent_claims?.length > 0 && (
            <div style={s.section}>
              <div style={s.sectionTitle}>Recent claims ({detail.recent_claims.length})</div>
              {detail.recent_claims.map((c, i) => (
                <div key={i} style={s.claimCard}>
                  <div style={s.claimText}>
                    {c.original_text}
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <span style={s.badge(VERDICT_COLORS[c.verdict?.label] || '#888780')}>
                      {c.verdict?.label || 'UNKNOWN'}
                    </span>
                    <span style={s.badge('#888780')}>
                      {c.geo_metadata?.political_alignment || '—'}
                    </span>
                    {c.geo_metadata?.conflict_zone_overlap && (
                      <span style={s.badge(COLORS.conflict)}>conflict zone</span>
                    )}
                    {c.geo_metadata?.health_emergency_overlap && (
                      <span style={s.badge(COLORS.health)}>health alert</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
