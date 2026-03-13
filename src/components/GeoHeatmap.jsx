// frontend/src/components/GeoHeatmap.jsx
// Full-page world choropleth heatmap
// Deps: d3, topojson-client  (npm install d3 topojson-client)
// All inline styles — no Tailwind

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';
import { useHeatmap } from '../hooks/useGeo';

// Risk color scale: teal (low) → amber → pink (high)
const RISK_COLOR = d3.scaleSequential()
  .domain([0, 1])
  .interpolator(d3.interpolateRgbBasis(['#E1F5EE', '#FAC775', '#C0395A']));

const CONFLICT_HATCH = '#BA7517';
const ELECTION_PULSE = '#534AB7';

export default function GeoHeatmap({ hours = 24, onCountryClick }) {
  const svgRef   = useRef(null);
  const wrapRef  = useRef(null);
  const [tooltip, setTooltip] = useState(null);    // {x, y, data}
  const [selected, setSelected] = useState(null);

  const { data: heatmapRes, isLoading } = useHeatmap(hours);
  const countryData = heatmapRes?.data || [];

  // Build lookup: ISO alpha-2 → stats
  const statsMap = {};
  for (const d of countryData) statsMap[d.country_code] = d;

  useEffect(() => {
    if (!svgRef.current || !wrapRef.current) return;

    const width  = wrapRef.current.clientWidth  || 800;
    const height = Math.round(width * 0.52);

    const svg = d3.select(svgRef.current)
      .attr('width',  width)
      .attr('height', height)
      .style('background', 'transparent');

    svg.selectAll('*').remove();

    const projection = d3.geoNaturalEarth1()
      .scale(width / 6.3)
      .translate([width / 2, height / 2]);

    const path = d3.geoPath().projection(projection);

    // Load world topojson
    d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
      .then(world => {
        const countries = topojson.feature(world, world.objects.countries);

        // Country name → ISO alpha-2 mapping via a small lookup
        // We use d3-geo-projection's internal id which is ISO numeric
        // We'll use a fetch to a public API once, then cache
        const numericToA2 = getNumericToA2Cache();

        const g = svg.append('g');

        // Graticule
        const graticule = d3.geoGraticule();
        g.append('path')
          .datum(graticule())
          .attr('d', path)
          .attr('fill', 'none')
          .attr('stroke', 'var(--color-border-tertiary)')
          .attr('stroke-width', 0.3);

        // Countries
        g.selectAll('.country')
          .data(countries.features)
          .join('path')
          .attr('class', 'country')
          .attr('d', path)
          .attr('fill', d => {
            const a2 = numericToA2[d.id];
            const stats = a2 ? statsMap[a2] : null;
            if (!stats) return 'var(--color-background-secondary)';
            return RISK_COLOR(stats.avg_risk);
          })
          .attr('stroke', d => {
            const a2 = numericToA2[d.id];
            const stats = a2 ? statsMap[a2] : null;
            if (stats?.conflict_claims > 0) return CONFLICT_HATCH;
            return 'var(--color-border-tertiary)';
          })
          .attr('stroke-width', d => {
            const a2 = numericToA2[d.id];
            const stats = a2 ? statsMap[a2] : null;
            return stats?.conflict_claims > 0 ? 1.2 : 0.4;
          })
          .style('cursor', d => {
            const a2 = numericToA2[d.id];
            return statsMap[a2] ? 'pointer' : 'default';
          })
          .on('mouseenter', function(event, d) {
            const a2 = numericToA2[d.id];
            const stats = a2 ? statsMap[a2] : null;
            if (!stats) return;
            d3.select(this).attr('stroke-width', 1.5).attr('stroke', '#C0395A');
            const [mx, my] = d3.pointer(event, wrapRef.current);
            setTooltip({ x: mx, y: my, code: a2, stats });
          })
          .on('mouseleave', function(event, d) {
            const a2 = numericToA2[d.id];
            const stats = a2 ? statsMap[a2] : null;
            d3.select(this)
              .attr('stroke-width', stats?.conflict_claims > 0 ? 1.2 : 0.4)
              .attr('stroke', stats?.conflict_claims > 0 ? CONFLICT_HATCH : 'var(--color-border-tertiary)');
            setTooltip(null);
          })
          .on('click', function(event, d) {
            const a2 = numericToA2[d.id];
            if (!statsMap[a2]) return;
            setSelected(a2);
            onCountryClick?.(a2);
          });

        // Sphere outline
        g.append('path')
          .datum({ type: 'Sphere' })
          .attr('d', path)
          .attr('fill', 'none')
          .attr('stroke', 'var(--color-border-secondary)')
          .attr('stroke-width', 0.5);

        // Zoom
        svg.call(d3.zoom()
          .scaleExtent([1, 8])
          .on('zoom', (event) => g.attr('transform', event.transform))
        );
      });
  }, [countryData, hours]);

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      {isLoading && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          background: 'var(--color-background-secondary)',
          borderRadius: 8, zIndex: 2
        }}>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 13 }}>
            Loading heatmap...
          </span>
        </div>
      )}
      <svg ref={svgRef} style={{ width: '100%', display: 'block', borderRadius: 8 }} />

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position: 'absolute',
          left:  tooltip.x + 12,
          top:   tooltip.y - 10,
          background: 'var(--color-background-primary)',
          border: '1px solid var(--color-border-primary)',
          borderRadius: 8,
          padding: '10px 14px',
          pointerEvents: 'none',
          zIndex: 10,
          minWidth: 180,
          boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
        }}>
          <div style={{ fontWeight: 500, fontSize: 13, color: 'var(--color-text-primary)', marginBottom: 6 }}>
            {tooltip.code}
          </div>
          <TooltipRow label="Claims (24h)"   value={tooltip.stats.total_claims} />
          <TooltipRow label="Avg risk"        value={(tooltip.stats.avg_risk * 100).toFixed(1) + '%'} color={RISK_COLOR(tooltip.stats.avg_risk)} />
          <TooltipRow label="Max risk"        value={(tooltip.stats.max_risk  * 100).toFixed(1) + '%'} />
          {tooltip.stats.conflict_claims > 0 && (
            <TooltipRow label="Conflict claims" value={tooltip.stats.conflict_claims} color={CONFLICT_HATCH} />
          )}
          {tooltip.stats.health_claims > 0 && (
            <TooltipRow label="Health overlap"  value={tooltip.stats.health_claims} color="#1D9E75" />
          )}
        </div>
      )}

      {/* Legend */}
      <GeoLegend />
    </div>
  );
}

function TooltipRow({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 3 }}>
      <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{label}</span>
      <span style={{ fontSize: 12, fontWeight: 500, color: color || 'var(--color-text-primary)' }}>{value}</span>
    </div>
  );
}

function GeoLegend() {
  const stops = [0, 0.25, 0.5, 0.75, 1.0];
  return (
    <div style={{
      position: 'absolute', bottom: 14, left: 14,
      background: 'var(--color-background-primary)',
      border: '1px solid var(--color-border-tertiary)',
      borderRadius: 6, padding: '8px 12px',
      display: 'flex', flexDirection: 'column', gap: 6
    }}>
      <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginBottom: 2 }}>
        avg risk score
      </span>
      <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
        {stops.map(s => (
          <div key={s} style={{ width: 28, height: 10, borderRadius: 2, background: RISK_COLOR(s) }} />
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>low</span>
        <span style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>high</span>
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 2, background: CONFLICT_HATCH }} />
          <span style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>conflict zone</span>
        </div>
      </div>
    </div>
  );
}

// ISO numeric → alpha-2 lookup (static, cached)
function getNumericToA2Cache() {
  return {
    4:"AF",8:"AL",12:"DZ",24:"AO",32:"AR",36:"AU",40:"AT",50:"BD",56:"BE",
    64:"BT",68:"BO",76:"BR",100:"BG",116:"KH",120:"CM",124:"CA",152:"CL",
    156:"CN",170:"CO",180:"CD",188:"CR",192:"CU",196:"CY",203:"CZ",208:"DK",
    214:"DO",218:"EC",818:"EG",231:"ET",246:"FI",250:"FR",276:"DE",288:"GH",
    300:"GR",320:"GT",332:"HT",340:"HN",348:"HU",356:"IN",360:"ID",364:"IR",
    368:"IQ",372:"IE",376:"IL",380:"IT",388:"JM",392:"JP",400:"JO",398:"KZ",
    404:"KE",408:"KP",410:"KR",414:"KW",418:"LA",422:"LB",434:"LY",484:"MX",
    104:"MM",504:"MA",508:"MZ",516:"NA",524:"NP",528:"NL",554:"NZ",558:"NI",
    566:"NG",578:"NO",586:"PK",591:"PA",600:"PY",604:"PE",608:"PH",616:"PL",
    620:"PT",630:"PR",634:"QA",642:"RO",643:"RU",646:"RW",682:"SA",686:"SN",
    694:"SL",706:"SO",710:"ZA",724:"ES",144:"LK",729:"SD",752:"SE",756:"CH",
    760:"SY",764:"TH",792:"TR",800:"UG",804:"UA",784:"AE",826:"GB",840:"US",
    858:"UY",860:"UZ",862:"VE",704:"VN",887:"YE",894:"ZM",716:"ZW",
    191:"HR",703:"SK",705:"SI",233:"EE",428:"LV",440:"LT",112:"BY",498:"MD",
    688:"RS",807:"MK",70:"BA",499:"ME",8:"AL",887:"YE",275:"PS",
  };
}
