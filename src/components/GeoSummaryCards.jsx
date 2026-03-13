// frontend/src/components/GeoSummaryCards.jsx
// 5 summary stat cards shown above the heatmap

import { useGeoSummary } from '../hooks/useGeo';

export default function GeoSummaryCards() {
  const { data: res, isLoading } = useGeoSummary();
  const d = res?.data || {};

  const cards = [
    {
      label:  'Countries affected',
      value:  d.countries_affected ?? '—',
      sub:    'last 24 hours',
      color:  '#534AB7',
      bg:     '#EEEDFE',
    },
    {
      label:  'Total claims',
      value:  d.total_claims_24h ?? '—',
      sub:    'flagged globally',
      color:  '#C0395A',
      bg:     '#FBEAF0',
    },
    {
      label:  'Highest risk',
      value:  d.highest_risk_country ?? '—',
      sub:    d.highest_risk_score != null
                ? `${(d.highest_risk_score * 100).toFixed(0)}% avg risk`
                : '—',
      color:  '#993556',
      bg:     '#F4C0D1',
    },
    {
      label:  'Conflict zones',
      value:  d.conflict_countries?.length ?? '—',
      sub:    d.conflict_countries?.slice(0, 3).join(', ') || 'none',
      color:  '#BA7517',
      bg:     '#FAEEDA',
    },
    {
      label:  'Health overlaps',
      value:  d.health_countries?.length ?? '—',
      sub:    d.health_countries?.slice(0, 3).join(', ') || 'none',
      color:  '#0F6E56',
      bg:     '#E1F5EE',
    },
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(5, 1fr)',
      gap: 12,
      marginBottom: 20,
    }}>
      {cards.map((card, i) => (
        <div key={i} style={{
          background: card.bg,
          borderRadius: 8,
          padding: '14px 16px',
          border: `1px solid ${card.color}44`,
          opacity: isLoading ? 0.5 : 1,
          transition: 'opacity 0.2s',
        }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: card.color, marginBottom: 6, letterSpacing: '0.05em' }}>
            {card.label.toUpperCase()}
          </div>
          <div style={{ fontSize: 28, fontWeight: 500, color: card.color, lineHeight: 1 }}>
            {isLoading ? '...' : card.value}
          </div>
          <div style={{ fontSize: 11, color: card.color + 'BB', marginTop: 4 }}>
            {card.sub}
          </div>
        </div>
      ))}
    </div>
  );
}
