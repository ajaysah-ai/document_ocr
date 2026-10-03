export default function Loading({ stages, current }) {
  return (
    <section className="card loading-card">
      <div className="spinner" />
      <ul className="stages">
        {stages.map((stage, index) => (
          <li
            key={stage}
            className={
              index < current ? 'stage-done' : index === current ? 'stage-active' : ''
            }
          >
            {stage}
          </li>
        ))}
      </ul>
    </section>
  )
}