import SubmissionTile from "./SubmissionTile";

export default function SubmissionsList({ submissions, onTileClick }) {
  const unmarked = submissions.filter(s => s.mark === null);
  const marked = submissions.filter(s => s.mark !== null);

  const groupByChallenge = (items) => {
    return items.reduce((acc, sub) => {
      const challenge = sub.challenge || "Unknown";
      if (!acc[challenge]) {
        acc[challenge] = [];
      }
      acc[challenge].push(sub);
      return acc;
    }, {});
  };

  const renderGrouped = (items) => {
    const groups = groupByChallenge(items);
    const groupNames = Object.keys(groups).sort((a, b) => a.localeCompare(b));

    return groupNames.map((challenge) => (
      <div key={challenge} className="section">
        <h4 className="section-subtitle">{challenge} ({groups[challenge].length})</h4>
        {groups[challenge].map(sub => (
          <div key={sub.id} onClick={() => onTileClick(sub.id)}>
            <SubmissionTile
              name={sub.name}
              zid={sub.zid}
              submittedAt={sub.submittedAt}
              mark={sub.mark}
            />
          </div>
        ))}
      </div>
    ));
  };

  return (
    <div className="submissions-list">
      {unmarked.length > 0 && (
        <div className="section">
          <h3 className="section-title">Unmarked ({unmarked.length})</h3>
          {renderGrouped(unmarked)}
        </div>
      )}

      {marked.length > 0 && (
        <div className="section">
          <h3 className="section-title">Marked ({marked.length})</h3>
          {renderGrouped(marked)}
        </div>
      )}
    </div>
  );
}