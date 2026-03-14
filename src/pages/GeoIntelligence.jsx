import { useState, useEffect, useRef } from 'react';
import * as THREE from 'three';
import GeoSummaryCards from '../components/GeoSummaryCards';
import GeoCountryPanel from '../components/GeoCountryPanel';

// Demo country data with lat/lng
const DEMO_GEO = [
  { country_code:'US', avg_risk:0.82, total_claims:1240, conflict_claims:2,  health_claims:5,  lat:37.09,  lng:-95.71 },
  { country_code:'RU', avg_risk:0.91, total_claims:890,  conflict_claims:12, health_claims:1,  lat:61.52,  lng:105.32 },
  { country_code:'CN', avg_risk:0.75, total_claims:670,  conflict_claims:3,  health_claims:2,  lat:35.86,  lng:104.19 },
  { country_code:'IN', avg_risk:0.68, total_claims:530,  conflict_claims:1,  health_claims:8,  lat:20.59,  lng:78.96  },
  { country_code:'BR', avg_risk:0.72, total_claims:410,  conflict_claims:0,  health_claims:4,  lat:-14.23, lng:-51.93 },
  { country_code:'GB', avg_risk:0.55, total_claims:310,  conflict_claims:0,  health_claims:2,  lat:55.38,  lng:-3.44  },
  { country_code:'DE', avg_risk:0.48, total_claims:280,  conflict_claims:0,  health_claims:1,  lat:51.17,  lng:10.45  },
  { country_code:'UA', avg_risk:0.95, total_claims:760,  conflict_claims:18, health_claims:0,  lat:48.38,  lng:31.17  },
  { country_code:'SY', avg_risk:0.89, total_claims:340,  conflict_claims:14, health_claims:0,  lat:34.80,  lng:38.99  },
  { country_code:'PK', avg_risk:0.71, total_claims:290,  conflict_claims:4,  health_claims:6,  lat:30.38,  lng:69.35  },
  { country_code:'NG', avg_risk:0.64, total_claims:180,  conflict_claims:3,  health_claims:9,  lat:9.08,   lng:8.68   },
  { country_code:'FR', avg_risk:0.52, total_claims:250,  conflict_claims:0,  health_claims:2,  lat:46.23,  lng:2.21   },
  { country_code:'MX', avg_risk:0.60, total_claims:195,  conflict_claims:2,  health_claims:3,  lat:23.63,  lng:-102.55},
  { country_code:'IR', avg_risk:0.86, total_claims:450,  conflict_claims:9,  health_claims:1,  lat:32.43,  lng:53.69  },
  { country_code:'TR', avg_risk:0.66, total_claims:220,  conflict_claims:2,  health_claims:0,  lat:38.96,  lng:35.24  },
  { country_code:'PH', avg_risk:0.60, total_claims:175,  conflict_claims:1,  health_claims:4,  lat:12.88,  lng:121.77 },
  { country_code:'MM', avg_risk:0.84, total_claims:310,  conflict_claims:8,  health_claims:0,  lat:21.92,  lng:95.96  },
  { country_code:'ZW', avg_risk:0.59, total_claims:120,  conflict_claims:1,  health_claims:5,  lat:-20.0,  lng:30.0   },
];

function riskColor(risk) {
  if (risk >= 0.85) return new THREE.Color('#ff2244');
  if (risk >= 0.65) return new THREE.Color('#ff8800');
  if (risk >= 0.45) return new THREE.Color('#ffd700');
  return new THREE.Color('#22c97c');
}

function riskHex(risk) {
  if (risk >= 0.85) return '#ff2244';
  if (risk >= 0.65) return '#ff8800';
  if (risk >= 0.45) return '#ffd700';
  return '#22c97c';
}

function latLngToXYZ(lat, lng, radius) {
  const phi   = (90 - lat)  * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
     radius * Math.cos(phi),
     radius * Math.sin(phi) * Math.sin(theta)
  );
}

const HOUR_OPTIONS = [6, 12, 24, 48, 168];

export default function GeoIntelligence() {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const [selected, setSelected]     = useState(null);
  const [hovered,  setHovered]      = useState(null);
  const [mousePos, setMousePos]     = useState({ x: 0, y: 0 });
  const [hours,    setHours]        = useState(24);
  const [geoData,  setGeoData]      = useState(DEMO_GEO);

  // Fetch real data, fallback to demo
  useEffect(() => {
    fetch(`http://localhost:8000/geo/heatmap?hours=${hours}`)
      .then(r => r.json())
      .then(res => { if (res?.data?.length > 0) setGeoData(res.data); })
      .catch(() => {});
  }, [hours]);

  // Three.js globe
  useEffect(() => {
    if (!mountRef.current) return;

    const w = mountRef.current.clientWidth;
    const h = mountRef.current.clientHeight;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(window.devicePixelRatio);
    mountRef.current.appendChild(renderer.domElement);

    // Scene + camera
    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
    camera.position.set(0, 0, 2.8);

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const sun = new THREE.DirectionalLight(0xffffff, 1.2);
    sun.position.set(5, 3, 5);
    scene.add(sun);
    const rim = new THREE.PointLight(0x7c3aed, 1.8, 20);
    rim.position.set(-4, 2, -4);
    scene.add(rim);

    // Stars background
    const starGeo = new THREE.BufferGeometry();
    const starVerts = [];
    for (let i = 0; i < 2000; i++) {
      starVerts.push((Math.random()-0.5)*200, (Math.random()-0.5)*200, (Math.random()-0.5)*200);
    }
    starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starVerts, 3));
    scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.1, sizeAttenuation: true })));

    // Globe — dark ocean texture loaded from CDN
    const GLOBE_R = 1;
    const globeGeo = new THREE.SphereGeometry(GLOBE_R, 64, 64);
    const globeMat = new THREE.MeshPhongMaterial({
      color: 0x0a1628,
      emissive: 0x040c1c,
      shininess: 30,
      specular: 0x223355,
    });
    const globe = new THREE.Mesh(globeGeo, globeMat);

    // Load earth texture (night lights)
    new THREE.TextureLoader().load(
      'https://unpkg.com/three-globe/example/img/earth-night.jpg',
      tex => { globeMat.map = tex; globeMat.needsUpdate = true; },
      undefined, () => {}  // fallback if CDN fails — dark globe still looks great
    );
    scene.add(globe);

    // Atmosphere glow
    const atmGeo = new THREE.SphereGeometry(GLOBE_R * 1.06, 64, 64);
    const atmMat = new THREE.MeshPhongMaterial({
      color: 0x7c3aed, transparent: true, opacity: 0.12,
      side: THREE.FrontSide,
    });
    scene.add(new THREE.Mesh(atmGeo, atmMat));

    // Risk point markers
    const markers = [];
    const raycaster = new THREE.Raycaster();
    const markerObjects = [];

    geoData.forEach(d => {
      const pos  = latLngToXYZ(d.lat, d.lng, GLOBE_R + 0.01);
      const size = Math.max(0.018, d.avg_risk * 0.055 + 0.015);

      // Spike / cylinder pointing outward
      const spikeGeo = new THREE.CylinderGeometry(size, size * 0.5, size * 3, 8);
      const spikeMat = new THREE.MeshPhongMaterial({
        color: riskColor(d.avg_risk),
        emissive: riskColor(d.avg_risk),
        emissiveIntensity: 0.7,
        transparent: true, opacity: 0.92,
      });
      const spike = new THREE.Mesh(spikeGeo, spikeMat);
      spike.position.copy(pos);
      spike.lookAt(0, 0, 0);
      spike.rotateX(Math.PI / 2);
      spike.userData = d;

      // Glow halo
      const haloGeo = new THREE.SphereGeometry(size * 2.5, 12, 12);
      const haloMat = new THREE.MeshBasicMaterial({ color: riskColor(d.avg_risk), transparent: true, opacity: 0.12, side: THREE.BackSide });
      const halo = new THREE.Mesh(haloGeo, haloMat);
      halo.position.copy(pos);

      scene.add(spike);
      scene.add(halo);
      markerObjects.push(spike);
      markers.push({ spike, halo, data: d });
    });

    sceneRef.current = { scene, camera, renderer, markers, markerObjects };

    // Mouse interaction
    let isDragging = false, prevMouse = { x: 0, y: 0 };
    const euler = new THREE.Euler(0, 0, 0, 'YXZ');
    const rotSpeed = 0.005;

    const onMouseDown = e => { isDragging = true; prevMouse = { x: e.clientX, y: e.clientY }; };
    const onMouseUp   = () => { isDragging = false; };
    const onMouseMove = e => {
      const rect = renderer.domElement.getBoundingClientRect();
      const mx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const my = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      setMousePos({ x: e.clientX, y: e.clientY });

      // Raycasting hover
      raycaster.setFromCamera({ x: mx, y: my }, camera);
      const hits = raycaster.intersectObjects(markerObjects);
      if (hits.length > 0) {
        setHovered(hits[0].object.userData);
        renderer.domElement.style.cursor = 'pointer';
      } else {
        setHovered(null);
        renderer.domElement.style.cursor = 'grab';
      }

      if (!isDragging) return;
      const dx = e.clientX - prevMouse.x;
      const dy = e.clientY - prevMouse.y;
      euler.y += dx * rotSpeed;
      euler.x += dy * rotSpeed;
      euler.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, euler.x));
      globe.rotation.set(euler.x, euler.y, 0);
      markers.forEach(({ spike, halo }) => {
        spike.position.applyEuler(new THREE.Euler(0,0,0));
      });
      prevMouse = { x: e.clientX, y: e.clientY };
    };

    const onClick = e => {
      const rect = renderer.domElement.getBoundingClientRect();
      const mx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const my = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera({ x: mx, y: my }, camera);
      const hits = raycaster.intersectObjects(markerObjects);
      if (hits.length > 0) setSelected(hits[0].object.userData.country_code);
    };

    renderer.domElement.addEventListener('mousedown', onMouseDown);
    renderer.domElement.addEventListener('mouseup',   onMouseUp);
    renderer.domElement.addEventListener('mousemove', onMouseMove);
    renderer.domElement.addEventListener('click',     onClick);

    // Auto-rotate
    let autoRotY = 0;
    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      if (!isDragging) {
        autoRotY += 0.002;
        globe.rotation.y = autoRotY;
        markers.forEach(({ spike, halo, data }) => {
          const p = latLngToXYZ(data.lat, data.lng, GLOBE_R + 0.02);
          const rot = new THREE.Matrix4().makeRotationY(autoRotY);
          p.applyMatrix4(rot);
          spike.position.copy(p);
          halo.position.copy(p);
          spike.lookAt(0, 0, 0);
          spike.rotateX(Math.PI / 2);
        });
      }
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      renderer.domElement.removeEventListener('mousedown', onMouseDown);
      renderer.domElement.removeEventListener('mouseup',   onMouseUp);
      renderer.domElement.removeEventListener('mousemove', onMouseMove);
      renderer.domElement.removeEventListener('click',     onClick);
      renderer.dispose();
      if (mountRef.current) mountRef.current.innerHTML = '';
    };
  }, [geoData]);

  const accent = '#7c3aed';

  return (
    <div style={{ padding:'20px 28px', minHeight:'100vh', background:'var(--color-background-primary)' }}>
      {/* Header */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:16 }}>
        <div>
          <h1 style={{ fontSize:22, fontWeight:700, color:'#c084fc', margin:0 }}>
            🌐 Geopolitical Intelligence — 3D Threat Globe
          </h1>
          <p style={{ fontSize:13, color:'var(--color-text-secondary)', marginTop:4, margin:0 }}>
            Real-time misinfo campaign heatmap · hover over spikes for detail
          </p>
        </div>
        <div style={{ display:'flex', gap:6, alignItems:'center' }}>
          <span style={{ fontSize:12, color:'var(--color-text-tertiary)' }}>Lookback:</span>
          {HOUR_OPTIONS.map(h => (
            <button key={h} onClick={() => setHours(h)} style={{
              padding:'4px 11px', borderRadius:6, fontSize:12, cursor:'pointer',
              border:`1px solid rgba(124,58,237,0.4)`,
              background: hours === h ? accent : 'transparent',
              color: hours === h ? '#fff' : 'var(--color-text-secondary)',
            }}>
              {h < 24 ? `${h}h` : `${h/24}d`}
            </button>
          ))}
        </div>
      </div>

      <GeoSummaryCards />

      {/* Globe container */}
      <div style={{
        marginTop:16, borderRadius:16, overflow:'hidden',
        background:'radial-gradient(ellipse at center, #0d0d2b 0%, #050510 100%)',
        border:'1px solid rgba(124,58,237,0.3)',
        boxShadow:'0 0 60px rgba(124,58,237,0.15)',
        height:500, position:'relative',
      }}>
        <div ref={mountRef} style={{ width:'100%', height:'100%' }} />

        {/* Hover tooltip */}
        {hovered && (
          <div style={{
            position:'fixed', left: mousePos.x + 16, top: mousePos.y - 10,
            background:'rgba(8,8,24,0.95)', border:`1px solid ${riskHex(hovered.avg_risk)}55`,
            borderRadius:10, padding:'12px 16px', pointerEvents:'none', zIndex:50,
            backdropFilter:'blur(12px)', minWidth:180,
            boxShadow:`0 0 20px ${riskHex(hovered.avg_risk)}33`,
          }}>
            <div style={{ fontWeight:700, fontSize:15, color:'#c084fc', marginBottom:8 }}>
              🏳 {hovered.country_code}
            </div>
            <TRow label="Avg Risk"      value={`${((hovered.avg_risk||0)*100).toFixed(1)}%`} color={riskHex(hovered.avg_risk)} />
            <TRow label="Total Claims"  value={hovered.total_claims} />
            {hovered.conflict_claims > 0 && <TRow label="Conflict Claims" value={hovered.conflict_claims} color="#ff8800" />}
            {hovered.health_claims  > 0 && <TRow label="Health Overlap"  value={hovered.health_claims}  color="#22c97c" />}
          </div>
        )}

        {/* Legend */}
        <div style={{
          position:'absolute', bottom:16, left:16,
          background:'rgba(8,8,24,0.88)', border:'1px solid rgba(124,58,237,0.3)',
          borderRadius:10, padding:'10px 14px', backdropFilter:'blur(10px)',
        }}>
          <div style={{ fontSize:11, color:'#666', marginBottom:6 }}>Risk Level</div>
          {[['#22c97c','Low (< 45%)'],['#ffd700','Medium (45–65%)'],['#ff8800','High (65–85%)'],['#ff2244','Critical (> 85%)']].map(([c,l])=>(
            <div key={c} style={{ display:'flex', alignItems:'center', gap:6, marginBottom:4 }}>
              <div style={{ width:10, height:10, borderRadius:'50%', background:c, boxShadow:`0 0 6px ${c}` }} />
              <span style={{ fontSize:11, color:'#bbb' }}>{l}</span>
            </div>
          ))}
        </div>

        {/* Drag hint */}
        <div style={{
          position:'absolute', top:12, right:12, fontSize:11, color:'rgba(192,132,252,0.5)',
          background:'rgba(8,8,24,0.6)', borderRadius:6, padding:'4px 8px',
        }}>
          🖱 Drag to rotate
        </div>
      </div>

      {selected && <GeoCountryPanel countryCode={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function TRow({ label, value, color }) {
  return (
    <div style={{ display:'flex', justifyContent:'space-between', gap:16, marginBottom:4 }}>
      <span style={{ fontSize:12, color:'#888' }}>{label}</span>
      <span style={{ fontSize:12, fontWeight:600, color: color || '#e2e8f0' }}>{value}</span>
    </div>
  );
}
