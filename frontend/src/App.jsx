import { useState, useEffect, useMemo, useCallback } from 'react';
import './App.css';
import SubmissionsList from '../components/dashboard/SubmissionsList';
import ExerciseList from '../components/dashboard/ExerciseList';
import SubmissionDetail from '../components/submission/SubmissionDetail';

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [csrfToken, setCsrfToken] = useState('');
  const [isTutor, setIsTutor] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [viewMode, setViewMode] = useState('submission');
  const [selectedExerciseId, setSelectedExerciseId] = useState(null);
  const [assignedUsers, setAssignedUsers] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showEmptyState, setShowEmptyState] = useState(false);
  const [deadlines, setDeadlines] = useState([]);
  const [unmarkedOnly, setUnmarkedOnly] = useState(false);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');

  // Fetch submissions from API on mount
  useEffect(() => {
    let isMounted = true;

    const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    if (isMounted) {
      setCsrfToken(token);
    }

    const init = async () => {
      setLoading(true);
      setAuthError(null);
      try {
        const meRes = await fetch('/api/v1/users/me', { credentials: 'same-origin' });
        if (!meRes.ok) {
          if (isMounted) {
            setCurrentUser(null);
          }
          return;
        }

        const mePayload = await meRes.json();
        const me = mePayload?.data;
        if (!mePayload?.success || !me) {
          if (isMounted) {
            setCurrentUser(null);
          }
          return;
        }

        if (isMounted) {
          setCurrentUser(me);
        }

        const tutorRes = await fetch('/api/marking_hub/tutors/me', {
          credentials: 'same-origin',
        });

        if (!tutorRes.ok) {
          throw new Error('Failed to check tutor permissions');
        }

        const tutorPayload = await tutorRes.json();
        const tutorFlag = Boolean(tutorPayload?.isTutor);
        const adminFlag = Boolean(tutorPayload?.isAdmin);

        if (isMounted) {
          setIsTutor(tutorFlag);
          setIsAdmin(adminFlag);
        }

        if (window.location.pathname === '/marking_hub/login') {
          window.location.replace('/marking_hub');
          return;
        }

        if (!adminFlag && !tutorFlag) {
          if (isMounted) {
            setAuthError('Tutor access is required to view assignments.');
          }
          return;
        }

        const [submissionsRes, assignmentsRes, deadlinesRes, categoriesRes] = await Promise.all([
          fetch('/api/marking_hub/submissions', { credentials: 'same-origin' }),
          fetch('/api/marking_hub/assignments/mine', { credentials: 'same-origin' }),
          fetch('/api/marking_hub/deadlines', { credentials: 'same-origin' }),
          fetch('/api/marking_hub/categories-with-counts', { credentials: 'same-origin' }),
        ]);

        if (!submissionsRes.ok) {
          throw new Error('Failed to fetch submissions');
        }

        const data = await submissionsRes.json();
        const assignments = await assignmentsRes.json().catch(() => []);
        const deadlinesData = await deadlinesRes.json().catch(() => []);
        const categoriesData = await categoriesRes.json().catch(() => { return { categories: [] }; });
        if (isMounted) {
          setSubmissions(data);
          setAssignedUsers(Array.isArray(assignments) ? assignments : []);
          setDeadlines(Array.isArray(deadlinesData) ? deadlinesData : []);
          setCategories(Array.isArray(categoriesData.categories) ? categoriesData.categories : []);
        }
      } catch (err) {
        console.error('Failed to initialize:', err);
        if (isMounted) {
          setAuthError('Failed to load tutor assignments.');
        }
      } finally {
        if (isMounted) {
          setAuthChecked(true);
          setLoading(false);
        }
      }
    };

    init();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleTileClick = (id) => {
    setSelectedSubmissionId(id);
  };

  const handleExerciseClick = (challengeId) => {
    setSelectedExerciseId(challengeId);
    const exerciseSubs = visibleSubmissions
      .filter(sub => sub.challengeId === challengeId)
      .sort((a, b) => {
        const aUnmarked = a.mark === null;
        const bUnmarked = b.mark === null;
        if (aUnmarked !== bUnmarked) {
          return aUnmarked ? -1 : 1;
        }
        return (b.submittedAt ?? '').localeCompare(a.submittedAt ?? '');
      });

    const firstSubmission = exerciseSubs[0];

    if (firstSubmission) {
      setSelectedSubmissionId(firstSubmission.id);
    }
  };

  const handleBack = () => {
    setSelectedSubmissionId(null);
    setShowEmptyState(false);
    setSelectedExerciseId(null);
  };

  const getGroupKey = (sub) => {
    const userKey = sub.userId ?? `unknown-user-${sub.id}`;
    const challengeKey = sub.challengeId ?? `unknown-challenge-${sub.id}`;
    return `${userKey}:${challengeKey}`;
  };

  const buildLatestSubmissions = useCallback((items) => {
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
  }, []);

  const visibleSubmissions = useMemo(() => {
    if (!currentUser) {
      return [];
    }

    if (isAdmin) {
      return submissions;
    }

    if (isTutor) {
      return submissions.filter(sub => sub.assignedTutorId === currentUser.id);
    }

    return [];
  }, [submissions, currentUser, isAdmin, isTutor]);

  const latestSubmissions = useMemo(() => {
    return buildLatestSubmissions(visibleSubmissions);
  }, [buildLatestSubmissions, visibleSubmissions]);

  const latestUnmarked = useMemo(() => {
    return latestSubmissions.filter(sub => sub.mark === null);
  }, [latestSubmissions]);

  const latestMarked = useMemo(() => {
    return latestSubmissions.filter(sub => sub.mark !== null);
  }, [latestSubmissions]);

  const filteredSubmissions = useMemo(() => {
    let result = latestSubmissions;
    
    // Filter by category if selected
    if (selectedCategory) {
      result = result.filter(sub => sub.category === selectedCategory);
    }
    
    // Filter unmarked only if toggled
    if (unmarkedOnly) {
      result = result.filter(sub => sub.mark === null);
    }
    
    return result;
  }, [latestSubmissions, selectedCategory, unmarkedOnly]);

  const selectedSubmission = visibleSubmissions.find(s => s.id === selectedSubmissionId);

  const relatedSubmissions = useMemo(() => {
    if (!selectedSubmission) {
      return [];
    }

    if (viewMode === 'exercise') {
      const exerciseId = selectedSubmission.challengeId ?? selectedExerciseId;
      return visibleSubmissions
        .filter(sub => sub.challengeId === exerciseId)
        .sort((a, b) => {
          const aUnmarked = a.mark === null;
          const bUnmarked = b.mark === null;
          if (aUnmarked !== bUnmarked) {
            return aUnmarked ? -1 : 1;
          }
          return (b.submittedAt ?? '').localeCompare(a.submittedAt ?? '');
        });
    }

    const key = getGroupKey(selectedSubmission);
    return visibleSubmissions
      .filter(sub => getGroupKey(sub) === key)
      .sort((a, b) => (b.submittedAt ?? '').localeCompare(a.submittedAt ?? ''));
  }, [visibleSubmissions, selectedSubmission, selectedExerciseId, viewMode]);

  const getNavigationIndex = (navList) => {
    if (!selectedSubmission) {
      return -1;
    }

    if (viewMode === 'exercise') {
      return navList.findIndex(sub => sub.id === selectedSubmission.id);
    }

    const latestForGroup = latestSubmissions.find(sub => getGroupKey(sub) === getGroupKey(selectedSubmission));
    if (!latestForGroup) {
      return -1;
    }

    return navList.findIndex(sub => sub.id === latestForGroup.id);
  };

  const getNavigationList = (options = {}) => {
    if (viewMode === 'exercise') {
      return relatedSubmissions;
    }
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

  const exerciseGroups = useMemo(() => {
    const groups = new Map();
    visibleSubmissions.forEach(sub => {
      const key = sub.challengeId ?? `unknown-challenge-${sub.id}`;
      if (!groups.has(key)) {
        groups.set(key, {
          challengeId: sub.challengeId,
          challenge: sub.challenge || 'Unknown',
          submissions: [],
        });
      }
      groups.get(key).submissions.push(sub);
    });

    return Array.from(groups.values())
      .map(group => {
        const sorted = group.submissions.sort((a, b) => (b.submittedAt ?? '').localeCompare(a.submittedAt ?? ''));
        const unmarkedCount = sorted.filter(sub => sub.mark === null).length;
        const markedCount = sorted.length - unmarkedCount;
        const submittedUserIds = new Set(sorted.map(sub => sub.userId));
        const missingUsers = assignedUsers.filter(user => !submittedUserIds.has(user.userId));
        return {
          challengeId: group.challengeId,
          challenge: group.challenge,
          submissions: group.submissions,
          unmarkedCount,
          markedCount,
          latestSubmittedAt: sorted[0]?.submittedAt ?? '',
          missingCount: missingUsers.length,
          missingInfo: missingUsers.map(user => {
            const name = user.userName || `User ${user.userId}`;
            const email = user.userEmail || 'No email';
            return `${name} (${email})`;
          }),
        };
      })
      .sort((a, b) => {
        const aHasUnmarked = a.unmarkedCount > 0;
        const bHasUnmarked = b.unmarkedCount > 0;
        if (aHasUnmarked !== bHasUnmarked) {
          return aHasUnmarked ? -1 : 1;
        }
        return (a.challenge || '').localeCompare(b.challenge || '');
      });
  }, [visibleSubmissions, assignedUsers]);

  const filteredExercises = useMemo(() => {
    let result = exerciseGroups;
    
    // Filter by category if selected
    if (selectedCategory) {
      result = result.map(group => {
        // Filter submissions in this group by category
        const filteredSubs = group.submissions.filter(sub => 
          (sub.category || 'Uncategorized') === selectedCategory
        );
        // Only include groups that have submissions after filtering
        if (filteredSubs.length === 0) {
          return null;
        }
        // Return group with filtered submissions
        return {
          ...group,
          submissions: filteredSubs,
          unmarkedCount: filteredSubs.filter(sub => sub.mark === null).length,
          markedCount: filteredSubs.filter(sub => sub.mark !== null).length,
          submittedUserIds: new Set(filteredSubs.map(sub => sub.userId))
        };
      }).filter(Boolean);
    }
    
    // Filter unmarked only if toggled
    if (unmarkedOnly) {
      result = result.filter(group => group.unmarkedCount > 0);
    }
    
    return result;
  }, [exerciseGroups, selectedCategory, unmarkedOnly]);

  const progressStats = useMemo(() => {
    const total = latestSubmissions.length;
    const marked = latestSubmissions.filter(sub => sub.mark !== null).length;
    const unmarked = total - marked;
    const percentage = total > 0 ? Math.round((marked / total) * 100) : 0;
    return { total, marked, unmarked, percentage };
  }, [latestSubmissions]);

  const handleSave = (id, mark, comment, options = {}) => {
    return fetch(`/api/marking_hub/submissions/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin',
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
    fetch('/api/marking_hub/sync', { method: 'POST', credentials: 'same-origin' })
      .then(res => res.json())
      .then(data => {
        alert(data.message);
        // Reload submissions
        return fetch('/api/marking_hub/submissions', { credentials: 'same-origin' });
      })
      .then(res => res.json())
      .then(data => {
        setSubmissions(data);
        setLoading(false);
      });
  };

  if (!authChecked) {
    return <div className="app-container"><h2>Checking session...</h2></div>;
  }

  if (!currentUser) {
    return (
      <div className="app-container">
        <div className="login-card">
          <h1>Marking Hub</h1>
          <h2>Tutor Login</h2>
          <form className="login-form" action="/login?next=/marking_hub" method="post">
            <label className="login-label" htmlFor="tutor-name">Username or Email</label>
            <input className="login-input" id="tutor-name" name="name" type="text" placeholder="name or email" required />
            <label className="login-label" htmlFor="tutor-password">Password</label>
            <input className="login-input" id="tutor-password" name="password" type="password" placeholder="password" required />
            <input type="hidden" name="nonce" value={csrfToken} />
            <button className="login-button" type="submit">Sign in</button>
          </form>
          <p className="login-help">Use your tutor/admin account to access assigned submissions.</p>
        </div>
      </div>
    );
  }

  if (currentUser && !isAdmin && !isTutor) {
    return (
      <div className="app-container">
        <div className="login-card">
          <h1>Marking Hub</h1>
          <h2>Account Not Authorized</h2>
          <p className="login-help">
            You are currently signed in as {currentUser.name}. Tutor access is required.
          </p>
          <a className="login-link" href="/logout?next=/marking_hub/login">Sign out and login as tutor</a>
        </div>
      </div>
    );
  }

  if (authError) {
    return (
      <div className="app-container">
        <div className="login-card">
          <h1>Marking Hub</h1>
          <h2>Access Error</h2>
          <p className="login-help">{authError}</p>
          <a className="login-link" href="/marking_hub/login">Go to tutor login</a>
        </div>
      </div>
    );
  }

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
            {isAdmin && (
              <button className="back-btn" onClick={handleSync}>Sync Submissions</button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <h1>1337 Marking Dashboard</h1>
      <h2>Marking Hub • {isAdmin ? 'Admin' : 'Tutor'}: {currentUser.name}</h2>
      
      {/* Progress Bar */}
      <div className="progress-section">
        <div className="progress-label">
          <span>Marking Progress</span>
          <span className="progress-stats">{progressStats.marked} / {progressStats.total} marked</span>
        </div>
        <div className="progress-bar-container">
          <div className="progress-bar-fill" style={{ width: `${progressStats.percentage}%` }}></div>
        </div>
        <div className="progress-percentage">{progressStats.percentage}% Complete</div>
      </div>

      <div className="view-toggle">
        <button
          className={`toggle-btn ${viewMode === 'submission' ? 'active' : ''}`}
          onClick={() => setViewMode('submission')}
        >
          By Submission
        </button>
        <button
          className={`toggle-btn ${viewMode === 'exercise' ? 'active' : ''}`}
          onClick={() => setViewMode('exercise')}
        >
          By Exercise
        </button>
        <label className="unmarked-only-toggle">
          <input
            type="checkbox"
            checked={unmarkedOnly}
            onChange={(e) => setUnmarkedOnly(e.target.checked)}
          />
          <span>Unmarked only</span>
        </label>
        <select
          className="category-filter"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat.category} value={cat.category}>
              {cat.category} ({cat.unmarkedCount} left)
            </option>
          ))}
        </select>
      </div>
      {isAdmin && (
        <button className="back-btn" onClick={handleSync}>Sync Submissions</button>
      )}
      {viewMode === 'submission' ? (
        <SubmissionsList submissions={filteredSubmissions} onTileClick={handleTileClick} />
      ) : (
        <ExerciseList exercises={filteredExercises} onExerciseClick={handleExerciseClick} deadlines={deadlines} />
      )}
    </div>
  );
}

export default App;
