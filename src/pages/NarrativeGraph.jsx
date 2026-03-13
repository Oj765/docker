import React, { useState, useEffect, useRef, useMemo } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
import NodeDetailPanel from '../components/NodeDetailPanel';

const NarrativeGraph3D = () => {
    const fgRef = useRef();
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [selectedNode, setSelectedNode] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        timeRange: '24h',
        platform: 'all',
        severity: 'all'
    });

    const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const fetchGraphData = async () => {
        setLoading(true);
        try {
            const queryParams = new URLSearchParams(filters).toString();
            const response = await fetch(`http://localhost:8000/graph?${queryParams}`);
            const result = await response.json();
            if (result.success) {
                setGraphData(result.data);
            }
        } catch (error) {
            console.error("Error fetching graph data:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchGraphData();
    }, [filters]);

    // Auto-rotate camera
    useEffect(() => {
        if (fgRef.current) {
            fgRef.current.controls().autoRotate = true;
            fgRef.current.controls().autoRotateSpeed = 0.5;
        }
    }, [fgRef.current]);

    const getSeverityColor = (severity) => {
        switch (severity?.toLowerCase()) {
            case 'critical': return '#ff0000';
            case 'high': return '#ff8c00';
            case 'medium': return '#ffd700';
            case 'low': return '#00ff00';
            default: return '#888888';
        }
    };

    const nodeLabel = (node) => {
        if (node.type === 'account') {
            return `<div style="background: rgba(0,0,0,0.8); padding: 8px; border-radius: 4px; border: 1px solid #2cf3e0">
                <strong style="color: #2cf3e0">${node.label}</strong><br/>
                Followers: ${node.followers.toLocaleString()}<br/>
                Credibility: ${node.credibility}%
            </div>`;
        }
        return `<div style="background: rgba(0,0,0,0.8); padding: 8px; border-radius: 4px; border: 1px solid ${getSeverityColor(node.severity)}">
            <strong style="color: ${getSeverityColor(node.severity)}">${node.severity.toUpperCase()} CLAIM</strong><br/>
            ${node.label}
        </div>`;
    };

    return (
        <div style={{ position: 'relative', width: '100%', height: 'calc(100vh - 100px)', background: '#0a0a12', borderRadius: '12px', overflow: 'hidden' }}>
            {/* Filter Bar */}
            <div style={{ 
                position: 'absolute', top: '20px', left: '20px', zIndex: 10,
                background: 'rgba(16, 16, 28, 0.8)', padding: '12px', borderRadius: '8px', 
                backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.1)',
                display: 'flex', gap: '10px'
            }}>
                <select value={filters.timeRange} onChange={e => setFilters({...filters, timeRange: e.target.value})} className="graph-filter">
                    <option value="24h">24h</option>
                    <option value="7d">7d</option>
                    <option value="30d">30d</option>
                </select>
                <select value={filters.platform} onChange={e => setFilters({...filters, platform: e.target.value})} className="graph-filter">
                    <option value="all">All Platforms</option>
                    <option value="twitter">X (Twitter)</option>
                    <option value="reddit">Reddit</option>
                    <option value="telegram">Telegram</option>
                </select>
                <select value={filters.severity} onChange={e => setFilters({...filters, severity: e.target.value})} className="graph-filter">
                    <option value="all">All Severities</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                </select>
            </div>

            {loading && (
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#2cf3e0', zIndex: 20 }}>
                    Initializing Narrative Engine...
                </div>
            )}

            <ForceGraph3D
                ref={fgRef}
                graphData={graphData}
                nodeLabel={nodeLabel}
                nodeColor={node => node.type === 'account' ? '#2cf3e0' : getSeverityColor(node.severity)}
                nodeThreeObject={node => {
                    if (node.type === 'claim') {
                        // Octahedron for Claims
                        return new THREE.Mesh(
                            new THREE.OctahedronGeometry(Math.sqrt(node.followers || 100) / 10 + 5),
                            new THREE.MeshLambertMaterial({ color: getSeverityColor(node.severity), transparent: true, opacity: 0.9 })
                        );
                    } else {
                        // Cubes for Hubs, Spheres for Amplifiers
                        if (node.role === 'hub') {
                            return new THREE.Mesh(
                                new THREE.BoxGeometry(10, 10, 10),
                                new THREE.MeshLambertMaterial({ color: '#2cf3e0' })
                            );
                        }
                        return new THREE.Mesh(
                            new THREE.SphereGeometry(Math.sqrt(node.followers || 100) / 20 + 2),
                            new THREE.MeshLambertMaterial({ color: '#2cf3e0' })
                        );
                    }
                }}
                linkWidth={link => link.sync_score * 3}
                linkColor={link => link.burst_detected ? '#ff0000' : '#444444'}
                linkDirectionalParticles={link => link.burst_detected ? 4 : 0}
                linkDirectionalParticleSpeed={0.01}
                linkDirectionalParticleColor={() => '#ff0000'}
                onNodeClick={node => {
                    fgRef.current.cameraPosition(
                        { x: node.x * 1.5, y: node.y * 1.5, z: node.z * 1.5 },
                        node,
                        1000
                    );
                    setSelectedNode(node);
                }}
                backgroundColor="#0a0a12"
            />

            {selectedNode && (
                <NodeDetailPanel 
                    node={selectedNode} 
                    onClose={() => setSelectedNode(null)} 
                    isMobile={isMobile}
                />
            )}

            <style>{`
                .graph-filter {
                    background: transparent;
                    color: white;
                    border: 1px solid rgba(255,255,255,0.2);
                    padding: 4px 8px;
                    border-radius: 4px;
                    outline: none;
                }
                .graph-filter option {
                    background: #10101c;
                }
            `}</style>
        </div>
    );
};

export default NarrativeGraph3D;