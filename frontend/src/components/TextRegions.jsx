export default function TextRegions({ regions, onSelect }) {
  if (!regions?.length) return null
  return (
    <section className="card">
      <div className="card-header">
        <h3>Text Regions</h3>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Text</th>
              <th>Confidence</th>
              <th>BBox</th>
            </tr>
          </thead>
          <tbody>
            {regions.map((region, index) => (
              <tr
                key={index}
                className="clickable-row"
                onClick={() => onSelect?.(index)}
              >
                <td>{index + 1}</td>
                <td>{region.text}</td>
                <td>{(region.confidence * 100).toFixed(1)}%</td>
                <td className="mono small">[{region.bbox.join(', ')}]</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}