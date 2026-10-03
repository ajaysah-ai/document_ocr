export default function Confidence({ value }) {
  const percent = Math.round((value || 0) * 1000) / 10
  return (
    <div className="confidence">
      <span className="label">Confidence</span>
      <div className="confidence-bar">
        <div
          className="confidence-fill"
          style={{ width: `${Math.min(100, percent)}%` }}
        />
      </div>
      <span className="value">{percent}%</span>
    </div>
  )
}