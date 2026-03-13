// frontend/src/components/GeoThreatTable.jsx
// Filterable table of claims by geo criteria

import { useState } from 'react';
import { useGeoFilter } from '../hooks/useGeo';

const ALIGNMENTS = [
  '', 'left', 'center-left', 'center', 'center-right', 'right',
  'nationalist', 'populist', 'religious-conservative', 'libertarian', 'authoritarian'
];

const VERDICT_COLOR = {
  FALSE:      '#C0395A',
  MISLEADING: '#BA7517',
  UNVERIFIED: '#888780',
  TRUE:       '#1D9E75',
};

export default function GeoThreatTable() {
  const [filters, setFilters] = useState({
    country_code:       '',
    political_alignment: '',
    conflict_only:       false,
    election_window:     null,
    health_only:         false,
    limit:               20,
    skip:                0,
  });

  const { mutate: runFilter, data: res, isPending } = useGeoFilter();

  const results = res?.data || [];
  const total   = res?.total || 0;

  const apply = (patch) => {
    const next = { ...filters, ...patch, skip: 0 };
    setFilters(next);
    runFilter(next);
  };

  const s = {
    wrap: { background: 'var(--color-background-secondary)', borderRadius: 8, padding: '16px 20px' },
    filterRow: { display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16, alignItems: 'center' },
    input: {
      padding: '6px 10px', borderRadius: 6, fontSize: 12,
      border: '1px solid var(--color-border-secondary)',
      background: 'var(--color-background-primary)',
      color: 'var(--color-text-primary)',
      outline: 'none',
    },
    toggle: (active, color) => ({
      padding: '5px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
      border: `1px solid ${active ? color : 'var(--color-border-secondary)'}`,
      background: active ? color + '22' : 'transparent',
      color: active ? color : 'var(--color-text-secondary)',
    }),
    btn: {
      padding: '6px 14px', borderRadius: 6, fontSize: 12,
      background: '#C0395A', color: '#fff', cursor: 'pointer',
      border: 'none',
    },
    table: { width: '100%', borderCollapse: 'collapse' },
    th: {
      fontSize: 11, fontWeight: 500, color: 'var(--color-text-tertiary)',
      padding: '8px 10px', textAlign: 'left', letterSpacing: '0.05em',
      borderBottom: '1px solid var(--color-border-tertiary)',
    },
    td: {
      fontSize: 12, color: 'var(--color-text-primary)',
      padding: '10px 10px', borderBottom: '1px solid var(--color-border-tertiary)',
      verticalAlign: 'top',
    },
    badge: (color) => ({
      display: 'inline-block', padding: '2px 7px', borderRadius: 4,
      fontSize: 10, fontWeight: 500, background: color + '22', color, marginRight: 4,
    }),
  };

  return (
    <div style={s.wrap}>
      {/* Filters */}
      <div style={s.filterRow}>
        <input
          style={{ ...s.input, width: 90 }}
          placeholder="Country (US)"
          value={filters.country_code}
          onChange={e => setFilters(f => ({ ...f, country_code: e.target.value.toUpperCase() }))}
        />
        <select
          style={{ ...s.input, width: 160 }}
          value={filters.political_alignment}
          onChange={e => setFilters(f => ({ ...f, political_alignment: e.target.value }))}
        >
          {ALIGNMENTS.map(a => <option key={a} value={a}>{a || 'All alignments'}</option>)}
        </select>
        <button
          style={s.toggle(filters.conflict_only, '#BA7517')}
          onClick={() => setFilters(f => ({ ...f, conflict_only: !f.conflict_only }))}
        >
          Conflict zones
        </button>
        <button
          style={s.toggle(filters.health_only, '#1D9E75')}
          onClick={() => setFilters(f => ({ ...f, health_only: !f.health_only }))}
        >
          Health overlap
        </button>
        <button
          style={s.toggle(filters.election_window === 30, '#534AB7')}
          onClick={() => setFilters(f => ({ ...f, election_window: f.election_window === 30 ? null : 30 }))}
        >
          Election ≤ 30d
        </button>
        <button style={s.btn} onClick={() => apply({})}>
          Apply filters
        </button>
        {total > 0 && (
          <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginLeft: 'auto' }}>
            {total} results
          </span>
        )}
      </div>

      {/* Table */}
      {isPending ? (
        <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', padding: '20px 0' }}>
          Filtering...
        </div>
      ) : results.length === 0 ? (
        <div style={{ fontSize: 13, color: 'var(--color-text-tertiary)', padding: '20px 0' }}>
          Apply filters to query claims
        </div>
      ) : (
        <table style={s.table}>
          <thead>
            <tr>
              {['Claim', 'Verdict', 'Regions', 'Alignment', 'Risk', 'Flags'].map(h => (
                <th key={h} style={s.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.map((c, i) => {
              const geo = c.geo_metadata || {};
              const riskPct = ((c.verdict?.risk_score || 0) * 100).toFixed(0);
              const riskColor = c.verdict?.risk_score > 0.85 ? '#C0395A'
                              : c.verdict?.risk_score > 0.6  ? '#BA7517' : '#1D9E75';
              return (
                <tr key={i} style={{ cursor: 'default' }}>
                  <td style={{ ...s.td, maxWidth: 220 }}>
                    <div style={{
                      overflow: 'hidden', textOverflow: 'ellipsis',
                      display: '-webkit-box', WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      lineHeight: 1.5,
                    }}>
                      {c.original_text}
                    </div>
                  </td>
                  <td style={s.td}>
                    <span style={s.badge(VERDICT_COLOR[c.verdict?.label] || '#888')}>
                      {c.verdict?.label || '—'}
                    </span>
                  </td>
                  <td style={s.td}>
                    <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                      {(geo.affected_regions || []).map(r => (
                        <span key={r} style={{ ...s.badge('#534AB7'), fontSize: 10 }}>{r}</span>
                      ))}
                    </div>
                  </td>
                  <td style={s.td}>
                    <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                      {geo.political_alignment || '—'}
                    </span>
                  </td>
                  <td style={s.td}>
                    <span style={{ fontWeight: 500, color: riskColor, fontSize: 13 }}>
                      {riskPct}%
                    </span>
                  </td>
                  <td style={s.td}>
                    {geo.conflict_zone_overlap   && <span style={s.badge('#BA7517')}>conflict</span>}
                    {geo.health_emergency_overlap && <span style={s.badge('#1D9E75')}>health</span>}
                    {geo.election_proximity?.length > 0 && <span style={s.badge('#534AB7')}>election</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
