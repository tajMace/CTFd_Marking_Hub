import { useState } from 'react';
import './SubmissionDetail.css';
import SubmissionTile from '../dashboard/SubmissionTile';

export default function SubmissionDetail({ submission, relatedSubmissions, onSelectRelated, onNext, onPrevious, onSave }) {
  const [mark, setMark] = useState(submission.mark ?? '');
  const [comment, setComment] = useState(submission.comment ?? '');

  const handleSave = async () => {
    try {
      const result = await onSave(submission.id, mark, comment, {
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
          
          <div className="form-group">
            <label htmlFor="mark">Mark</label>
            <input
              id="mark"
              type="number"
              min="0"
              max="100"
              value={mark}
              onChange={(e) => setMark(e.target.value)}
              placeholder="Enter mark (0-100)"
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

          <button className="save-btn" onClick={handleSave}>
            Save Mark & Comment
          </button>
        </div>
      </div>

      {relatedSubmissions?.length > 0 && (
        <div className="related-submissions">
          <h3>All Submissions for this Challenge</h3>
          <div className="related-list">
            {relatedSubmissions.map(sub => (
              <div
                key={sub.id}
                className={`related-tile ${sub.id === submission.id ? 'active' : ''}`}
                onClick={() => onSelectRelated(sub.id)}
              >
                <SubmissionTile
                  name={sub.name}
                  zid={sub.zid}
                  submittedAt={sub.submittedAt}
                  mark={sub.mark}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}