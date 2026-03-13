import React, { useState } from 'react';
import { 
  Slack, 
  Send, 
  Mail, 
  Bell, 
  ShieldAlert, 
  ChevronRight,
  RefreshCcw,
  Zap
} from 'lucide-react';
import './AlertConfiguration.css';

const AlertConfiguration = () => {
  const [threshold, setThreshold] = useState(75);
  const [categories, setCategories] = useState({
    medical: true,
    political: true,
    financial: false
  });
  const [channels, setChannels] = useState({
    slack: true,
    telegram: true,
    email: false,
    pagerduty: true
  });

  const handleToggleCategory = (cat) => {
    setCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
  };

  const handleToggleChannel = (channel) => {
    setChannels(prev => ({ ...prev, [channel]: !prev[channel] }));
  };

  return (
    <div className="alerts-container">
      <header className="alerts-header">
        <h1>Alert Configuration</h1>
      </header>

      <div className="alerts-grid">
        <div className="alerts-main-col">
          {/* Risk Threshold Section */}
          <section className="card config-card">
            <h3>Risk Threshold</h3>
            <div className="slider-container">
              <div className="slider-track">
                <div className="slider-progress" style={{ width: `${threshold}%` }}></div>
                <div className="slider-thumb" style={{ left: `${threshold}%` }}>
                  <span className="thumb-label">{threshold}%</span>
                </div>
              </div>
              <div className="slider-markers">
                <span>0<br/><small>Disabled</small></span>
                <span>25</span>
                <span>50</span>
                <span>75</span>
                <span>100</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={threshold} 
                onChange={(e) => setThreshold(e.target.value)}
                className="hidden-input"
              />
            </div>
            <p className="helper-text">Alerts trigger above selected risk level.</p>
          </section>

          {/* Alert Categories Section */}
          <section className="card config-card">
            <h3>Alert Categories</h3>
            <div className="checkbox-group">
              <label className="checkbox-item">
                <input 
                  type="checkbox" 
                  checked={categories.medical} 
                  onChange={() => handleToggleCategory('medical')} 
                />
                <span className="checkmark"></span>
                Medical misinformation
              </label>
              <label className="checkbox-item">
                <input 
                  type="checkbox" 
                  checked={categories.political} 
                  onChange={() => handleToggleCategory('political')} 
                />
                <span className="checkmark"></span>
                Political misinformation
              </label>
              <label className="checkbox-item">
                <input 
                  type="checkbox" 
                  checked={categories.financial} 
                  onChange={() => handleToggleCategory('financial')} 
                />
                <span className="checkmark"></span>
                Financial misinformation
              </label>
            </div>
          </section>

          {/* Test Alert Button Section */}
          <section className="card config-card">
            <h3>Test Alert Button</h3>
            <div className="button-row">
              <button className="btn-primary trigger-btn">
                Trigger Test Alert
              </button>
              <button className="btn-secondary">
                Reset Defaults
              </button>
            </div>
          </section>
        </div>

        <aside className="alerts-side-col">
          {/* Notification Channels Section */}
          <div className="card channels-card">
            <h3>Notification Channels</h3>
            <div className="channels-list">
              <div className="channel-item">
                <div className="channel-info">
                  <div className="channel-icon slack"><Slack size={18} /></div>
                  <span>Slack</span>
                </div>
                <label className="switch">
                  <input 
                    type="checkbox" 
                    checked={channels.slack} 
                    onChange={() => handleToggleChannel('slack')} 
                  />
                  <span className="slider round"></span>
                </label>
              </div>

              <div className="channel-item">
                <div className="channel-info">
                  <div className="channel-icon telegram"><Send size={18} /></div>
                  <span>Telegram</span>
                </div>
                <label className="switch">
                  <input 
                    type="checkbox" 
                    checked={channels.telegram} 
                    onChange={() => handleToggleChannel('telegram')} 
                  />
                  <span className="slider round"></span>
                </label>
              </div>

              <div className="channel-item">
                <div className="channel-info">
                  <div className="channel-icon email"><Mail size={18} /></div>
                  <span>Email</span>
                </div>
                <label className="switch">
                  <input 
                    type="checkbox" 
                    checked={channels.email} 
                    onChange={() => handleToggleChannel('email')} 
                  />
                  <span className="slider round"></span>
                </label>
              </div>

              <div className="channel-item">
                <div className="channel-info">
                  <div className="channel-icon pagerduty">P</div>
                  <span>PagerDuty</span>
                </div>
                <label className="switch">
                  <input 
                    type="checkbox" 
                    checked={channels.pagerduty} 
                    onChange={() => handleToggleChannel('pagerduty')} 
                  />
                  <span className="slider round"></span>
                </label>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default AlertConfiguration;
