import './App.css'

import SubmissionTile from '../components/dashboard/SubmissionTile'

function App() {
  return (
    <div className="app-container">
      <h1>1337 Marking Dashboard</h1>
      <h2>Marking Hub</h2>
      <SubmissionTile
        name="Example Submission"
        zid="z5691836"
        submittedAt="2024-06-01 12:00:00"
        mark={85}
      />
    </div>
  );
}

export default App
