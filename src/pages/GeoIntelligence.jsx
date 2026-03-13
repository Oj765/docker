// frontend/src/pages/GeoIntelligence.jsx
// Full page — drop into your React Router config:
// <Route path="/geo" element={<GeoIntelligence />} />

import { useState } from 'react';
import GeoSummaryCards from '../components/GeoSummaryCards';
import GeoHeatmap      from '../components/GeoHeatmap';
import GeoCountryPanel from '../components/GeoCountryPanel';
import GeoThreatTable  from '../components/GeoThreatTable';

const HOUR_OPTIONS = [6, 12, 24, 48, 72, 168];

export default function GeoIntelligence() {
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [hours, setHours]                     = useState(24);
  const [tab, setTab]                         = useState('map'); // 'map' | 'table'

  const s = {
    page: { padding: '24px 28px', minHeight: '100vh', maxWidth: 1400 },
    pageHeader: {
      display: 'flex', justifyContent: 'space-between',
      alignItems: 'flex-start', marginBottom: 20,
    },
    titleBlock: {},
    title: { fontSize: 22, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 4 },
    subtitle: { fontSize: 13, color: 'var(--color-text-secondary)' },
    controls: { display: 'flex', gap: 8, alignItems: 'center' },
    hourBtn: (active) => ({
      padding: '5px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
      border: '1px solid var(--color-border-secondary)',
      background: active ? '#C0395A' : 'transparent',
      color: active ? '#fff' : 'var(--color-text-secondary)',
    }),
    tabs: { display: 'flex', gap: 0, marginBottom: 16, borderBottom: '1px solid var(--color-border-tertiary)' },
    tab: (active) => ({
      padding: '8px 20px', fontSize: 13, cursor: 'pointer',
      border: 'none', background: 'none',
      color: active ? '#C0395A' : 'var(--color-text-secondary)',
      borderBottom: active ? '2px solid #C0395A' : '2px solid transparent',
      marginBottom: -1,
    }),
    heatmapWrap: {
      background: 'var(--color-background-secondary)',
      borderRadius: 8, padding: 16, marginBottom: 20,
    },
  };

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.pageHeader}>
        <div style={s.titleBlock}>
          <div style={s.title}>Geopolitical intelligence</div>
          <div style={s.subtitle}>
            World heatmap of active misinfo campaigns — click any country for detail
          </div>
        </div>
        <div style={s.controls}>
          <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>Lookback:</span>
          {HOUR_OPTIONS.map(h => (
            <button key={h} style={s.hourBtn(hours === h)} onClick={() => setHours(h)}>
              {h < 24 ? `${h}h` : `${h / 24}d`}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      <GeoSummaryCards />

      {/* Tabs */}
      <div style={s.tabs}>
        <button style={s.tab(tab === 'map')}   onClick={() => setTab('map')}>World map</button>
        <button style={s.tab(tab === 'table')} onClick={() => setTab('table')}>Threat table</button>
      </div>

      {tab === 'map' ? (
        <div style={s.heatmapWrap}>
          <GeoHeatmap hours={hours} onCountryClick={setSelectedCountry} />
        </div>
      ) : (
        <GeoThreatTable />
      )}

      {/* Country detail panel */}
      {selectedCountry && (
        <GeoCountryPanel
          countryCode={selectedCountry}
          onClose={() => setSelectedCountry(null)}
        />
      )}
    </div>
  );
}
