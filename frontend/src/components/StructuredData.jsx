const LABELS = {
  pan_number: 'PAN Number',
  name: 'Name',
  fathers_name: "Father's Name",
  date_of_birth: 'Date of Birth',
  aadhaar_number: 'Aadhaar Number',
  gender: 'Gender',
  passport_number: 'Passport Number',
  surname: 'Surname',
  given_names: 'Given Names',
  nationality: 'Nationality',
  date_of_expiry: 'Date of Expiry',
  dl_number: 'DL Number',
  validity: 'Validity',
  epic_number: 'EPIC Number',
  invoice_number: 'Invoice Number',
  invoice_date: 'Invoice Date',
  total_amount: 'Total Amount',
  gstin: 'GSTIN',
  vendor: 'Vendor',
}

export default function StructuredData({ data, documentType }) {
  const entries = Object.entries(data || {})
  return (
    <section className="card">
      <div className="card-header">
        <h3>Structured Data</h3>
        {documentType && <span className="chip">{documentType}</span>}
      </div>
      {entries.length === 0 ? (
        <p className="muted">
          No structured fields for this document type. Raw OCR text is still available above.
        </p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Value</th>
              <th>Confidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([key, field]) => (
              <tr key={key} className={field.needs_review ? 'needs-review' : ''}>
                <td>{LABELS[key] || key}</td>
                <td className="mono">{field.value}</td>
                <td>{(field.confidence * 100).toFixed(1)}%</td>
                <td>
                  {field.needs_review
                    ? '⚠ needs review'
                    : field.validated
                      ? '✓ format valid'
                      : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}