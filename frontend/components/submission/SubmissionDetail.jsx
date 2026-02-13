import { useState } from 'react';
import './SubmissionDetail.css';
import SubmissionTile from '../dashboard/SubmissionTile';

export default function SubmissionDetail({ submission, relatedSubmissions, onSelectRelated, onNext, onPrevious, onSave }) {
  const [mark, setMark] = useState(submission.mark ?? '');
  const [comment, setComment] = useState(submission.comment ?? '');
  const [error, setError] = useState('');
  const isTechnical = Boolean(submission.isTechnical);
  const maxPoints = submission.challengeValue || 100;  // Default to 100 if not provided

  const handleSave = async () => {
    if (isTechnical) {
      setError('Technical submissions are not manually marked.');
      return;
    }
    // Validate that mark is provided
    if (mark === '' || mark === null || mark === undefined) {
      setError(`Mark is required. Please enter a value between 0-${maxPoints}.`);
      return;
    }

    const markValue = Number(mark);
    if (isNaN(markValue) || markValue < 0 || markValue > maxPoints) {
      setError(`Mark must be a number between 0 and ${maxPoints}.`);
      return;
    }

    setError('');
    try {
      const result = await onSave(submission.id, markValue, comment, {
        wasUnmarked: submission.mark === null,
      });
      if (result?.showEmptyState) {
        return;
      }
      if (submission.mark === null) {
        onNext({ forceUnmarked: true });
      } else {
        onNext();
      }
    } catch {
      // errors handled upstream
    }
  };

  return (
    <div className="submission-detail">
      <div className="detail-header">
        <button className="nav-btn" onClick={onPrevious}>← Previous</button>
        <h2>{submission.name} ({submission.zid})</h2>
        <button className="nav-btn" onClick={onNext}>Next →</button>
      </div>

      <div className="challenge-section">
        <h3>Challenge: {submission.challenge}</h3>
        {isTechnical && (
          <div className="challenge-connection">
            <strong>Technical:</strong> This exercise is auto-assessed and is not manually marked.
          </div>
        )}
        {submission.challengeConnectionInfo && (
          <div className="challenge-connection">
            <strong>Connection:</strong> {submission.challengeConnectionInfo}
          </div>
        )}
        {submission.challengeHtml && (
          <div
            className="challenge-description"
            dangerouslySetInnerHTML={{ __html: submission.challengeHtml }}
          />
        )}
      </div>

      <div className="detail-content">
        <div className="submission-info">
          <h3>Submission Details</h3>
          <p><strong>Submitted:</strong> {submission.submittedAt}</p>
          <p><strong>Submission:</strong></p>
          {submission.flag && (
            <div className="submission-flag">
              <a href={submission.flag} target="_blank" rel="noopener noreferrer">
                {submission.flag}
              </a>
            </div>
          )}
        </div>

        <div className="marking-section">
          <h3>Marking</h3>
          
          {isTechnical ? (
            <div className="auto-marked-result">
              <h4>Auto-Marked Result</h4>
              <div className="result-box">
                <div className="result-line">
                  <strong>Correctness:</strong> {mark === maxPoints ? '✓ Correct' : '✗ Incorrect'}
                </div>
                <div className="result-line">
                  <strong>Mark:</strong> {mark} / {maxPoints} ({((mark / maxPoints) * 100).toFixed(1)}%)
                </div>
                <p style={{ fontSize: '0.9em', color: '#666', marginTop: '8px' }}>
                  This is an auto-assessed technical exercise. The mark is determined by the correctness of the submitted flag.
                </p>
              </div>
            </div>
          ) : (
            <>
              <div className="form-group">
                <label htmlFor="mark">Mark (out of {maxPoints}) *</label>
                <input
                  id="mark"
                  type="number"
                  min="0"
                  max={maxPoints}
                  value={mark}
                  onChange={(e) => setMark(e.target.value)}
                  placeholder={`Enter mark (0-${maxPoints})`}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="comment">Comment</label>
                <textarea
                  id="comment"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Enter feedback for the student..."
                  rows="8"
                />
              </div>

              {error && (
                <div className="error-message">
                  {error}
                </div>
              )}

              <button className="save-btn" onClick={handleSave}>
                Save Mark & Comment
              </button>
            </>
          )}
        </div>
      </div>

      {/* Related submissions hidden: only latest submission per student is shown */}
    </div>
  );
}