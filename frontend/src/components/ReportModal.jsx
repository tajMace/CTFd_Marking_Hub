import { useState } from 'react';
import './ReportModal.css';

function ReportModal({ isOpen, onClose, isAdmin }) {
  const [activeTab, setActiveTab] = useState('trigger');
  const [reportHistory, setReportHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSendWeekly = async () => {
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch('/api/marking_hub/reports/send-weekly', {
        method: 'POST',
        credentials: 'same-origin',
      });
      const data = await res.json();
      if (data.success) {
        setMessage(`✓ ${data.message}`);
        loadReportHistory();
      } else {
        setMessage(`✗ ${data.message}`);
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadReportHistory = async () => {
    try {
      const res = await fetch('/api/marking_hub/reports', {
        credentials: 'same-origin',
      });
      const data = await res.json();
      setReportHistory(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load report history:', err);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === 'history') {
      loadReportHistory();
    }
  };

  const handleSendStudentReport = async (userId, category) => {
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch(`/api/marking_hub/reports/send/${userId}?category=${encodeURIComponent(category)}`, {
        method: 'POST',
        credentials: 'same-origin',
      });
      const data = await res.json();
      if (data.success) {
        setMessage(`✓ ${data.message}`);
        loadReportHistory();
      } else {
        setMessage(`✗ ${data.message}`);
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !isAdmin) {
    return null;
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Student Reports</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-tabs">
          <button
            className={`modal-tab ${activeTab === 'trigger' ? 'active' : ''}`}
            onClick={() => handleTabChange('trigger')}
          >
            Send Reports
          </button>
          <button
            className={`modal-tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => handleTabChange('history')}
          >
            History
          </button>
        </div>

        <div className="modal-body">
          {activeTab === 'trigger' && (
            <div className="trigger-section">
              <h3>Send Weekly Student Reports</h3>
              <p>Generates and emails performance reports to all students with marked submissions.</p>
              
              <button
                className="send-button"
                onClick={handleSendWeekly}
                disabled={loading}
              >
                {loading ? 'Sending...' : 'Send Weekly Reports'}
              </button>

              {message && (
                <div className={`message ${message.startsWith('✓') ? 'success' : 'error'}`}>
                  {message}
                </div>
              )}
            </div>
          )}

          {activeTab === 'history' && (
            <div className="history-section">
              <h3>Report Send History</h3>
              {reportHistory.length === 0 ? (
                <p className="empty-history">No reports sent yet.</p>
              ) : (
                <div className="history-table">
                  <div className="table-header">
                    <div className="col-student">Student</div>
                    <div className="col-date">Sent</div>
                    <div className="col-count">Submissions</div>
                    <div className="col-marked">Marked</div>
                  </div>
                  {reportHistory.slice(0, 20).map((report) => (
                    <div key={report.id} className="table-row">
                      <div className="col-student">
                        <strong>{report.userName}</strong>
                        <br />
                        <small>{report.userEmail}</small>
                      </div>
                      <div className="col-date">{report.sentAt}</div>
                      <div className="col-count">{report.submissionCount}</div>
                      <div className="col-marked">{report.markedCount}</div>
                      <div className="col-action">
                        <input
                          type="text"
                          placeholder="Category"
                          style={{ marginRight: '8px', padding: '4px' }}
                          id={`category-input-${report.id}`}
                        />
                        <button
                          className="send-button"
                          onClick={() => {
                            const category = document.getElementById(`category-input-${report.id}`).value;
                            handleSendStudentReport(report.userId, category);
                          }}
                          disabled={loading}
                        >
                          Send Report
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ReportModal;
