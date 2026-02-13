export default function SubmissionTile({ name, zid, submittedAt, mark }) {
    return (
        <div className="submission-tile">
            <div className="tile-left">
                <div className="tile-name">{name}</div>
                <div className="tile-meta">{zid}</div>
            </div>
            <div className="tile-center">
                <div className="tile-label">Submitted</div>
                <div className="tile-value">{submittedAt}</div>
            </div>
            <div className="tile-right">
                <div className="tile-label">Mark</div>
                <div className="tile-value">{mark ?? "--"}</div>
            </div>
        </div>
    )
}