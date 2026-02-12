export default function ExerciseList({ exercises, onExerciseClick, deadlines }) {
  const getDeadlineForChallenge = (challengeId) => {
    return deadlines?.find(d => d.challengeId === challengeId);
  };

  const isOverdue = (deadline) => {
    if (!deadline || !deadline.dueDate) return false;
    const dueDate = new Date(deadline.dueDate);
    return dueDate < new Date();
  };

  if (!exercises || exercises.length === 0) {
    return (
      <div className="empty-state">
        <h2>No submissions available</h2>
      </div>
    );
  }

  return (
    <div className="submissions-list">
      {exercises.map((exercise) => {
        const deadline = getDeadlineForChallenge(exercise.challengeId);
        const overdue = isOverdue(deadline);
        
        return (
          <div
            key={exercise.challengeId}
            onClick={() => onExerciseClick(exercise.challengeId)}
          >
            <div className={`submission-tile ${overdue ? 'overdue' : ''}`}>
              <div className="tile-left">
                <div className="tile-name">{exercise.challenge}</div>
                <div className="tile-meta">{exercise.challengeId ?? ""}</div>
                {deadline && (
                  <div className={`tile-deadline ${overdue ? 'overdue-text' : ''}`}>
                    📅 Due: {deadline.dueDate}
                  </div>
                )}
              </div>
              <div className="tile-center">
                <div className="tile-label">Latest Submission</div>
                <div className="tile-value">{exercise.latestSubmittedAt ?? ""}</div>
              </div>
              <div className="tile-right">
                <div className="marking-stats">
                  <div className="stat-group">
                    <div className="tile-label">Unmarked</div>
                    <div className="tile-value">{exercise.unmarkedCount}</div>
                  </div>
                  <div className="stat-group">
                    <div className="tile-label">Marked</div>
                    <div className="tile-value">{exercise.markedCount}</div>
                  </div>
                </div>
                <div className="tile-missing">
                  <span className="tile-label">Not Submitted ({exercise.missingCount})</span>
                  <span
                    className="info-dot"
                    data-tooltip={exercise.missingInfo && exercise.missingInfo.length > 0 ? exercise.missingInfo.join("\n") : "No missing submissions"}
                    aria-label="Missing submissions"
                  >
                    i
                  </span>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
