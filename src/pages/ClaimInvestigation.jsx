import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Twitter, 
  Clock,
  ShieldCheck,
  MoreVertical,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Users,
  Zap,
  ExternalLink,
  Globe
} from 'lucide-react';
import './ClaimInvestigation.css';

const ClaimInvestigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [openStep, setOpenStep] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [analysis, setAnalysis] = useState(null);
  const [toast, setToast] = useState(null);
  const hasFetched = React.useRef(false);
  
  const claim = location.state?.claim;

  useEffect(() => {
    if (!claim) {
      navigate('/live-feed');
      return;
    }
    
    if (hasFetched.current) return;
    hasFetched.current = true;

    const fetchAnalysis = async () => {
      try {
        // First check MongoDB for an existing cached result
        const claimId = claim.id || claim.claim_id;
        if (claimId) {
          const cached = await fetch(`http://localhost:8000/analyze/claim/${claimId}`);
          if (cached.ok) {
            const cachedData = await cached.json();
            if (cachedData.success && cachedData.data?.verdict?.label) {
              const d = cachedData.data;
              setAnalysis({
                label:           d.verdict?.label,
                confidence:      d.verdict?.confidence,
                risk_score:      d.risk_score,
                reasoning_chain: d.verdict?.reasoning_chain || [],
                evidence_sources:d.verdict?.evidence_sources || [],
                mutation_of:     d.parent_claim_id,
                geo_info:        d.geo_info || {},
              });
              setIsLoading(false);
              return;
            }
          }
        }

        // Run the full ML pipeline
        const response = await fetch('http://localhost:8000/analyze/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text:     claim.claim,
            platform: claim.platform || 'manual',
            account_id: claim.source_org || 'stream_user',
            post_url: claim.fact_check_url || 'https://manual.entry',
          })
        });
        const data = await response.json();
        if (data.success && data.data) {
          setAnalysis(data.data);
        } else {
          console.error('Analysis failed:', data);
        }
      } catch (err) {
        console.error('Error fetching analysis:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalysis();
  }, [claim, navigate]);

  const handleAction = (type) => {
    setToast({
      message: `${type} successful!`,
      type: 'success'
    });
    setTimeout(() => setToast(null), 3000);
  };

  if (!claim) return null;

  // Process data for UI — ML returns risk_score and confidence as 0.0-1.0 floats
  const rawRiskScore = analysis ? (analysis.risk_score || 0) : 0;
  const riskScore = Math.round(rawRiskScore * 100); // scale to 0-100 for display
  const rawConfidence = analysis ? (analysis.confidence || 0) : 0;
  const confidence = Math.round(rawConfidence * 100); // scale to 0-100 for display
  
  const getRiskClass = (score) => {
    // score here is 0-100
    if (score >= 80) return 'critical';
    if (score >= 60) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
  };
  const riskClass = getRiskClass(riskScore);
  const isFalse = analysis?.label?.toLowerCase().includes('false') || analysis?.label?.toLowerCase().includes('misleading');
  const label = analysis?.label || 'Pending Analysis';

  // Process reasoning chain
  let reasoningSteps = [];
  if (analysis?.reasoning_chain && Array.isArray(analysis.reasoning_chain)) {
    reasoningSteps = analysis.reasoning_chain.map((step, idx) => ({
      id: idx + 1,
      title: typeof step === 'string' ? `Step ${idx + 1}` : (step.step || `Step ${idx + 1}`),
      desc: typeof step === 'string' ? step : (step.explanation || step.content || JSON.stringify(step))
    }));
  } else {
    reasoningSteps = [{ id: 1, title: 'Extracting Claim', desc: 'Analyzing the text to form a reasoning chain...' }];
  }

  // Process evidence
  let evidenceSources = [];
  if (analysis?.evidence_sources && Array.isArray(analysis.evidence_sources)) {
    evidenceSources = analysis.evidence_sources.map((src, idx) => ({
      title: src.title || src.source_name || `Source ${idx + 1}`,
      // credibility_score is 0.0-1.0 from ML, scale to 0-100
      credibility: src.credibility_score != null ? Math.round(src.credibility_score * 100) : (src.credibility || 50),
      source: src.domain || src.source_type || src.source || 'Unknown',
      snippet: src.excerpt || src.snippet || src.summary || src.content || 'Content not available',
      url: src.url || src.link || '#'
    }));
  }

  // Process mutation history
  let mutationHistory = [];
  if (analysis?.mutation_of) {
    mutationHistory = [
      { event: 'Original Claim', date: claim.published || 'Previously', desc: `Mutated from prior claim: ${analysis.mutation_of}` },
      { event: 'Current Variant', date: 'Now', desc: 'Current analyzed text.' }
    ];
  } else {
    mutationHistory = [
      { event: 'Original Claim', date: claim.published || 'Just now', desc: 'First appearance detected by system.' }
    ];
  }

  return (
    <div className="investigation-page">
      <div className="investigation-header-nav">
        <button className="back-btn" onClick={() => navigate('/live-feed')}>
          <ArrowLeft size={16} /> Back to Live Feed
        </button>
        <button className="menu-btn">
          <MoreVertical size={20} />
        </button>
      </div>

      <div className="investigation-main-header">
        <div className="header-top-row">
          <h1>"{claim.claim}"</h1>
          {!isLoading && (
            <div className={`header-risk-badge badge-${riskClass}`}>
              <span className="badge-dot"></span>
              {riskScore} - {riskClass.charAt(0).toUpperCase() + riskClass.slice(1)} Risk
            </div>
          )}
        </div>
        
        <div className="header-meta-stats">
          <div className="meta-stat">
            <Twitter size={16} color="#1DA1F2" fill="#1DA1F2" />
            <span>{claim.platform || 'General'} Source</span>
          </div>
          <div className="meta-stat">
            <Clock size={16} />
            <span>{analysis?.geo_info?.time_context ? `Context: ${analysis.geo_info.time_context}` : 'Detected recently'}</span>
          </div>
          <div className="meta-stat">
            <Globe size={16} />
            <span>{analysis?.geo_info?.predicted_region || 'Global'}</span>
          </div>
          {analysis?.geo_info?.topic_tags?.slice(0, 2).map(tag => (
            <div key={tag} className="meta-stat" style={{ textTransform: 'capitalize' }}>
              <Zap size={16} />
              <span>{tag}</span>
            </div>
          ))}
          {!isLoading && (
            <div className="meta-stat">
              <ShieldCheck size={16} color="#107C7C" />
              <span>{confidence}% Confidence</span>
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="investigation-loading" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <Zap size={48} className="pulse-anim" style={{ color: '#107C7C', marginBottom: '20px' }} />
          <h2>Running ML Analysis...</h2>
          <p style={{ color: '#6b7280', marginTop: '10px' }}>Analyzing claim text, translating, extracting entities, fetching evidence vectors, evaluating reasoning chain, and computing risk score.</p>
        </div>
      ) : (
      <div className="investigation-grid">
        <div className="grid-left">
          <section className="investigation-section ai-verdict">
            <h2 className="section-title">AI Verdict</h2>
            <div className="verdict-card card">
               <div className="verdict-main">
                  <div className={`verdict-type ${isFalse ? 'false' : 'true'}`}>
                    {isFalse ? <AlertTriangle size={32} /> : <CheckCircle2 size={32} />}
                    <div>
                      <p className="verdict-label">{label}</p>
                      <p className="verdict-subtext">The claim has been evaluated against multiple indexed sources.</p>
                    </div>
                  </div>
                  <div className="verdict-stats">
                    <div className="v-stat">
                       <span className="v-val">{confidence}%</span>
                       <span className="v-lab">Confidence Level</span>
                    </div>
                    <div className="v-divider"></div>
                    <div className="v-stat">
                       <span className="v-val">{riskScore}</span>
                       <span className="v-lab">Risk Score</span>
                    </div>
                  </div>
               </div>
            </div>
          </section>

          <section className="investigation-section">
            <h2 className="section-title">Reasoning Chain</h2>
            <div className="accordion-container card">
              {reasoningSteps.map((step) => (
                <div key={step.id} className={`accordion-item ${openStep === step.id ? 'open' : ''}`}>
                  <div className="accordion-header" onClick={() => setOpenStep(openStep === step.id ? null : step.id)}>
                    <div className="step-count">{step.id}</div>
                    <span className="step-title">{step.title}</span>
                    {openStep === step.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                  </div>
                  {openStep === step.id && (
                    <div className="accordion-content">
                      <p>{step.desc}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          <section className="investigation-section">
            <h2 className="section-title">Evidence Sources</h2>
            <div className="evidence-list">
               {evidenceSources.length > 0 ? evidenceSources.map((source, idx) => (
                 <div key={idx} className="evidence-card card">
                    <div className="evidence-header">
                       <div className="evidence-meta">
                          <h3>{source.title}</h3>
                          <span className="source-label">{source.source}</span>
                       </div>
                       <div className="credibility-score">
                          <span className="score-val">{source.credibility}%</span>
                          <span className="score-lab">Credibility</span>
                       </div>
                    </div>
                    <p className="evidence-snippet">"{source.snippet}"</p>
                    <a href={source.url} target="_blank" rel="noopener noreferrer" className="source-link">
                      <ExternalLink size={14} /> View Original Source
                    </a>
                 </div>
               )) : (
                 <p style={{ color: '#6b7280', padding: '10px' }}>No specific evidence sources matched this claim.</p>
               )}
            </div>
          </section>
        </div>

        <div className="grid-right">
          <section className="investigation-section">
            <h2 className="section-title">Mutation History</h2>
            <div className="timeline-container card">
              {mutationHistory.map((item, idx) => (
                <div key={idx} className="timeline-item">
                  <div className="timeline-marker"></div>
                  <div className="timeline-content">
                    <p className="timeline-date">{item.date}</p>
                    <p className="timeline-event">{item.event}</p>
                    <p className="timeline-desc">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="investigation-section sticky-actions">
            <h2 className="section-title">Action Buttons</h2>
            <div className="action-card card">
               <button className="action-btn approve" onClick={() => handleAction('Approval')}>
                 <CheckCircle2 size={18} /> Approve Response
               </button>
               <button className="action-btn review" onClick={() => handleAction('Review Request')}>
                 <Users size={18} /> Send for Human Review
               </button>
               <button className="action-btn override" onClick={() => handleAction('Override')}>
                 <Zap size={18} /> Override Verdict
               </button>
            </div>
          </section>
        </div>
      </div>
      )}
      
      {toast && (
        <div className={`toast ${toast.type}`}>
          <CheckCircle2 size={18} />
          {toast.message}
        </div>
      )}
    </div>
  );
};

export default ClaimInvestigation;
