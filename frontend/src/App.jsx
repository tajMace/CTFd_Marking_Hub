import { useState, useEffect, useMemo } from 'react';
import './App.css';
import SubmissionsList from '../components/dashboard/SubmissionsList';
import SubmissionDetail from '../components/submission/SubmissionDetail';

function App() {
  const [submissions, setSubmissions] = useState([]);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showEmptyState, setShowEmptyState] = useState(false);

  // Fetch submissions from API on mount
  useEffect(() => {
    fetch('/api/marking_hub/submissions')
      .then(res => res.json())
      .then(data => {
        setSubmissions(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch submissions:', err);
        setLoading(false);
      });
  }, []);

  const handleTileClick = (id) => {
    setSelectedSubmissionId(id);
  };

  const handleBack = () => {
    setSelectedSubmissionId(null);
    setShowEmptyState(false);
  };

  const getGroupKey = (sub) => {
    const userKey = sub.userId ?? `unknown-user-${sub.id}`;
    const challengeKey = sub.challengeId ?? `unknown-challenge-${sub.id}`;
    return `${userKey}:${challengeKey}`;
  };

  const buildLatestSubmissions = (items) => {
    const groups = new Map();

    items.forEach(sub => {
      const key = getGroupKey(sub);
      const existing = groups.get(key);
      if (!existing) {
        groups.set(key, sub);
        return;
      }

      const currentDate = sub.submittedAt ?? '';
      const existingDate = existing.submittedAt ?? '';
      if (currentDate > existingDate) {
        groups.set(key, sub);
      }
    });

    return Array.from(groups.values()).sort((a, b) => {
      return (b.submittedAt ?? '').localeCompare(a.submittedAt ?? '');
    });
  };

  const latestSubmissions = useMemo(() => {
    return buildLatestSubmissions(submissions);
  }, [submissions]);

  const latestUnmarked = useMemo(() => {
    return latestSubmissions.filter(sub => sub.mark === null);
  }, [latestSubmissions]);

  const latestMarked = useMemo(() => {
    return latestSubmissions.filter(sub => sub.mark !== null);
  }, [latestSubmissions]);

  const selectedSubmission = submissions.find(s => s.id === selectedSubmissionId);

  const relatedSubmissions = useMemo(() => {
    if (!selectedSubmission) {
      return [];
    }

    const key = getGroupKey(selectedSubmission);
    return submissions
      .filter(sub => getGroupKey(sub) === key)
      .sort((a, b) => (b.submittedAt ?? '').localeCompare(a.submittedAt ?? ''));
  }, [submissions, selectedSubmission]);

  const getNavigationIndex = (navList) => {
    if (!selectedSubmission) {
      return -1;
    }

    const latestForGroup = latestSubmissions.find(sub => getGroupKey(sub) === getGroupKey(selectedSubmission));
    if (!latestForGroup) {
      return -1;
    }

    return navList.findIndex(sub => sub.id === latestForGroup.id);
  };

  const getNavigationList = (options = {}) => {
    if (options.forceUnmarked) {
      return latestUnmarked;
    }
    if (options.forceMarked) {
      return latestMarked;
    }
    if (selectedSubmission?.mark === null) {
      return latestUnmarked;
    }
    return latestMarked;
  };

  const handleNext = (options = {}) => {
    const navList = getNavigationList(options);
    const currentIndex = getNavigationIndex(navList);
    if (currentIndex > -1 && currentIndex < navList.length - 1) {
      setSelectedSubmissionId(navList[currentIndex + 1].id);
    } else if (options.forceUnmarked && navList.length === 0) {
      setSelectedSubmissionId(null);
    }
  };

  const handlePrevious = (options = {}) => {
    const navList = getNavigationList(options);
    const currentIndex = getNavigationIndex(navList);
    if (currentIndex > 0) {
      setSelectedSubmissionId(navList[currentIndex - 1].id);
    }
  };

  const handleSave = (id, mark, comment) => {
    return fetch(`/api/marking_hub/submissions/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ mark, comment }),
    })
      .then(res => res.json())
      .then(updatedSubmission => {
        // Update local state
        const nextSubmissions = submissions.map(s =>
          s.id === id ? updatedSubmission : s
        );
        setSubmissions(nextSubmissions);
        alert('Saved successfully!');
        return updatedSubmission;
        if (options.wasUnmarked) {
          const latest = buildLatestSubmissions(nextSubmissions);
          const unmarked = latest.filter(sub => sub.mark === null);
          if (unmarked.length === 0) {
            setSelectedSubmissionId(null);
            setShowEmptyState(true);
            return { updatedSubmission, showEmptyState: true };
          }
        }

        return { updatedSubmission, showEmptyState: false };
      })
      .catch(err => {
        console.error('Failed to save:', err);
        alert('Failed to save!');
        throw err;
      });
  };

  const handleSync = () => {
    setLoading(true);
    setShowEmptyState(false);
    fetch('/api/marking_hub/sync', { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        alert(data.message);
        // Reload submissions
        return fetch('/api/marking_hub/submissions');
      })
      .then(res => res.json())
      .then(data => {
        setSubmissions(data);
        setLoading(false);
      });
  };

  if (loading) {
    return <div className="app-container"><h2>Loading...</h2></div>;
  }

  if (selectedSubmission) {
    return (
      <div className="app-container">
        <button className="back-btn" onClick={handleBack}>← Back to Dashboard</button>
        <SubmissionDetail
          key={selectedSubmission.id}
          submission={selectedSubmission}
          relatedSubmissions={relatedSubmissions}
          onSelectRelated={handleTileClick}
          onNext={handleNext}
          onPrevious={handlePrevious}
          onSave={handleSave}
        />
      </div>
    );
  }

  if (showEmptyState) {
    return (
      <div className="app-container">
        <h1>1337 Marking Dashboard</h1>
        <div className="empty-state">
          <h2>Nothing left to mark, yay!</h2>
          <div className="empty-state-buttons">
            <button className="back-btn" onClick={() => setShowEmptyState(false)}>Return to Dashboard</button>
            <button className="back-btn" onClick={handleSync}>Sync Submissions</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <h1>1337 Marking Dashboard</h1>
      <h2>Marking Hub</h2>
      <button className="back-btn" onClick={handleSync}>Sync Submissions</button>
      <SubmissionsList submissions={latestSubmissions} onTileClick={handleTileClick} />
    </div>
  );
}

export default App;
