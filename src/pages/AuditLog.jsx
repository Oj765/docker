import React, { useState } from 'react';
import { 
  Search, 
  ChevronDown, 
  Download, 
  Calendar,
  ChevronRight,
  Filter
} from 'lucide-react';
import './AuditLog.css';

const logEntries = [
  {
    timestamp: '2026-03-13 14:32:01',
    actionType: 'AI Verdict',
    claimId: 'CLM-0123-A',
    reviewer: 'Automated System',
    result: 'False',
    notes: 'Confidence: 95%, Risk: Critical'
  },
  {
    timestamp: '2026-03-13 14:32:01',
    actionType: 'Human Review',
    claimId: 'CLM-0123-A',
    reviewer: 'Sarah Chen (Analyst)',
    result: 'Misleading',
    notes: 'Verified, added context'
  },
  {
    timestamp: '2026-03-13 13:15:22',
    actionType: 'Human Review',
    claimId: 'CLM-0123-A',
    reviewer: 'Automated System',
    result: 'Misleading',
    notes: 'Verified, added context'
  },
  {
    timestamp: '2026-03-13 11:05:00',
    actionType: 'Alert Trigger',
    claimId: 'CLM-0123-B',
    reviewer: 'Automated System',
    result: 'Slack, Telegram',
    notes: 'Threshold met'
  },
  {
    timestamp: '2026-03-12 16:22:11',
    actionType: 'Configuration Change',
    claimId: 'N/A',
    reviewer: 'Admin User',
    result: 'Alert Threshold',
    notes: 'Changed from 80% to 75%'
  }
];

const AuditLog = () => {
  const [actionType, setActionType] = useState('AI Verdict');

  return (
    <div className="audit-container">
      <header className="audit-header">
        <h1>Audit Log</h1>
      </header>

      <div className="audit-card card">
        <div className="audit-filters">
          <div className="filter-item action-type-filter">
            <label>Action Type</label>
            <div className="select-wrapper">
              <select 
                value={actionType} 
                onChange={(e) => setActionType(e.target.value)}
              >
                <option>AI Verdict</option>
                <option>Human Review</option>
                <option>Alert Trigger</option>
                <option>Configuration Change</option>
              </select>
              <ChevronDown size={16} className="select-icon" />
            </div>
          </div>

          <div className="filter-item date-range-filter">
            <label>Date Range</label>
            <div className="date-inputs">
              <div className="date-input-box">
                <Calendar size={16} />
                <input type="text" defaultValue="2026-03-01" />
              </div>
              <span className="to-text">to</span>
              <div className="date-input-box">
                <Calendar size={16} />
                <input type="text" defaultValue="2026-03-13" />
              </div>
            </div>
          </div>

          <div className="filter-item search-claim-filter">
            <label>Search Claim ID</label>
            <div className="search-input-box">
              <input type="text" placeholder="Search Claim ID" />
            </div>
          </div>

          <button className="export-btn">
            Export CSV
          </button>
        </div>

        <div className="audit-table-container">
          <table className="audit-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action Type</th>
                <th>Claim ID</th>
                <th>Reviewer</th>
                <th>Result</th>
                <th className="notes-header">Notes</th>
                <th className="empty-header"></th>
              </tr>
            </thead>
            <tbody>
              {logEntries.map((entry, idx) => (
                <tr key={idx}>
                  <td className="time-cell">{entry.timestamp}</td>
                  <td>
                    <span className={`action-type-tag ${entry.actionType.toLowerCase().replace(' ', '-')}`}>
                      {entry.actionType}
                    </span>
                  </td>
                  <td className="id-cell">{entry.claimId}</td>
                  <td className="reviewer-cell">{entry.reviewer}</td>
                  <td className="result-cell">{entry.result}</td>
                  <td className="notes-cell">{entry.notes}</td>
                  <td className="chevron-cell"><ChevronRight size={18} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AuditLog;
