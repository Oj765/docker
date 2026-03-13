import React from 'react';
import { X, User, FileText, BarChart, ExternalLink, ShieldCheck } from 'lucide-react';

const NodeDetailPanel = ({ node, onClose, isMobile }) => {
    if (!node) return null;

    const panelStyle = isMobile ? {
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: '60vh',
        background: '#16161c',
        borderTop: '2px solid #2cf3e0',
        zIndex: 1000,
        padding: '24px',
        borderTopLeftRadius: '24px',
        borderTopRightRadius: '24px',
        boxShadow: '0 -10px 30px rgba(0,0,0,0.5)',
        overflowY: 'auto'
    } : {
        position: 'absolute',
        top: '20px',
        right: '20px',
        bottom: '20px',
        width: '350px',
        background: 'rgba(22, 22, 28, 0.9)',
        backdropFilter: 'blur(15px)',
        border: '1px solid rgba(44, 243, 224, 0.3)',
        zIndex: 100,
        borderRadius: '16px',
        padding: '24px',
        color: 'white',
        boxShadow: '0 0 40px rgba(0,0,0,0.4)',
        overflowY: 'auto'
    };

    return (
        <div style={panelStyle} className="node-detail-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {node.type === 'account' ? <User size={20} color="#2cf3e0" /> : <FileText size={20} color="#ff3d71" />}
                    <h2 style={{ fontSize: '1.2rem', fontWeight: '600', margin: 0 }}>
                        {node.type === 'account' ? 'Entity Profile' : 'Claim Details'}
                    </h2>
                </div>
                <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer' }}>
                    <X size={24} />
                </button>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px', marginBottom: '20px' }}>
                <h3 style={{ fontSize: '1.4rem', color: node.type === 'account' ? '#2cf3e0' : 'white', margin: '0 0 8px 0' }}>
                    {node.label}
                </h3>
                {node.type === 'account' && (
                    <div style={{ display: 'flex', gap: '12px', color: '#ccc', fontSize: '0.9rem' }}>
                        <span>{node.platform?.toUpperCase()}</span>
                        <span>•</span>
                        <span>{node.followers?.toLocaleString()} Followers</span>
                    </div>
                )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '24px' }}>
                <div className="stat-box">
                    <span className="stat-label">Credibility</span>
                    <span className="stat-value" style={{ color: node.credibility > 70 ? '#00e096' : '#ff3d71' }}>
                        {node.credibility || '--'}%
                    </span>
                </div>
                <div className="stat-box">
                    <span className="stat-label">Platform</span>
                    <span className="stat-value" style={{ color: '#2cf3e0' }}>
                        {node.platform || 'Cross-Platform'}
                    </span>
                </div>
            </div>

            {node.type === 'account' ? (
                <>
                    <p style={{ color: '#aaa', fontSize: '0.95rem', lineHeight: '1.6', marginBottom: '24px' }}>
                        This account has been identified as a <strong>{node.role}</strong> in several misinformation campaigns. 
                        Coordinated posting patterns suggest automated behavior.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <button className="panel-btn primary">
                            <ShieldCheck size={18} /> Send for Human Review
                        </button>
                        <button className="panel-btn secondary">
                            <BarChart size={18} /> View Narrative History
                        </button>
                    </div>
                </>
            ) : (
                <>
                    <div style={{ marginBottom: '20px' }}>
                        <span className="badge" style={{ background: '#ff3d71' }}>VERDICT: {node.verdict || 'FALSE'}</span>
                        <span className="badge" style={{ background: '#ffa500', marginLeft: '8px' }}>SEVERITY: {node.severity?.toUpperCase()}</span>
                    </div>
                    <p style={{ color: '#aaa', fontSize: '0.95rem', lineHeight: '1.6', marginBottom: '24px' }}>
                        Narrative spread detected across multiple platforms. Coordinated burst detected in last 2 hours.
                    </p>
                    <button className="panel-btn primary">
                         Investigate Source <ExternalLink size={18} style={{ marginLeft: '8px' }} />
                    </button>
                </>
            )}

            <style>{`
                .stat-box {
                    background: rgba(255,255,255,0.03);
                    padding: 12px;
                    border-radius: 8px;
                    display: flex;
                    flex-direction: column;
                }
                .stat-label {
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    color: #777;
                    margin-bottom: 4px;
                }
                .stat-value {
                    font-size: 1.1rem;
                    font-weight: bold;
                }
                .panel-btn {
                    padding: 12px;
                    border-radius: 8px;
                    border: none;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                    font-weight: 600;
                    transition: 0.2s;
                }
                .panel-btn.primary {
                    background: #2cf3e0;
                    color: #000;
                }
                .panel-btn.primary:hover {
                    background: #1dc5b5;
                }
                .panel-btn.secondary {
                    background: rgba(44, 243, 224, 0.1);
                    color: #2cf3e0;
                    border: 1px solid rgba(44, 243, 224, 0.2);
                }
                .panel-btn.secondary:hover {
                    background: rgba(44, 243, 224, 0.2);
                }
                .badge {
                    font-size: 0.7rem;
                    padding: 4px 8px;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                }
            `}</style>
        </div>
    );
};

export default NodeDetailPanel;