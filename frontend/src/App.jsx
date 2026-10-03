import { useCallback, useEffect, useState } from 'react'
import UploadBox from './components/UploadBox'
import ImagePreview from './components/ImagePreview'
import OCRText from './components/OCRText'
import StructuredData from './components/StructuredData'
import Confidence from './components/Confidence'
import TextRegions from './components/TextRegions'
import Loading from './components/Loading'
import { getHealth, uploadDocument } from './services/api'

const STAGES = [
  'Uploading...',
  'Analyzing image...',
  'Correcting document...',
  'Detecting text...',
  'Recognizing text...',
  'Structuring data...',
]

const MAX_CLIENT_MB = 10
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/bmp', 'image/webp', 'image/tiff']

function friendlyError(err, detail) {
  if (err.code === 'ERR_NETWORK' || !err.response) {
    return {
      title: 'Backend unavailable',
      reasons: [
        'The OCR server is not reachable.',
        'Start it with: uvicorn backend.main:app --reload (port 8000).',
      ],
    }
  }
  if (err.response?.status === 413) {
    return { title: 'File too large', reasons: ['Maximum upload size is 10 MB.'] }
  }
  if (err.response?.status === 400) {
    return {
      title: 'Unable to process this image.',
      reasons: [detail || 'Unsupported or corrupted image file.'],
    }
  }
  if (err.response?.status === 503) {
    return {
      title: 'OCR service unavailable',
      reasons: [detail || 'The OCR engine failed to start. Check backend logs.'],
    }
  }
  return {
    title: 'Unable to process this image.',
    reasons: [
      detail || 'Image is too blurry',
      'Document is cropped',
      'Unsupported image format',
      'OCR service unavailable',
    ],
  }
}

function downloadBlob(content, mimeType, filename) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [stage, setStage] = useState(0)
  const [showBoxes, setShowBoxes] = useState(false)
  const [selectedRegion, setSelectedRegion] = useState(null)

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: 'error', ocr: 'unavailable' }))
  }, [])

  // Animated stage messages while the request is in flight (UI never freezes).
  useEffect(() => {
    if (!isProcessing) return undefined
    setStage(0)
    const timer = setInterval(
      () => setStage((s) => Math.min(s + 1, STAGES.length - 1)),
      1400,
    )
    return () => clearInterval(timer)
  }, [isProcessing])

  const reset = useCallback(() => {
    setFile(null)
    setPreviewUrl(null)
    setResult(null)
    setError(null)
    setSelectedRegion(null)
    setShowBoxes(false)
    setIsProcessing(false)
  }, [])

  const handleFile = useCallback(async (selected) => {
    setError(null)
    setResult(null)
    setSelectedRegion(null)
    if (!selected) return
    if (!ACCEPTED_TYPES.includes(selected.type)) {
      setError({
        title: 'Unsupported file type',
        reasons: ['Please upload a JPG, PNG, BMP, WEBP or TIFF image.'],
      })
      return
    }
    if (selected.size > MAX_CLIENT_MB * 1024 * 1024) {
      setError({
        title: 'File too large',
        reasons: [`Maximum size is ${MAX_CLIENT_MB} MB.`],
      })
      return
    }
    setFile(selected)
    setPreviewUrl(URL.createObjectURL(selected))
    setIsProcessing(true)
    try {
      const data = await uploadDocument(selected)
      setResult(data)
    } catch (err) {
      setError(friendlyError(err, err?.response?.data?.detail))
    } finally {
      setIsProcessing(false)
    }
  }, [])

  const overlayUrl = result?.processed_image_b64
    ? `data:image/jpeg;base64,${result.processed_image_b64}`
    : previewUrl

  const averageConfidence = result?.regions?.length
    ? result.regions.reduce((sum, r) => sum + r.confidence, 0) / result.regions.length
    : 0

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Document OCR</h1>
          <p className="subtitle">Extract text from document images</p>
        </div>
        <div className={`health-badge health-${health?.ocr === 'ready' ? 'ok' : 'bad'}`}>
          {health ? `OCR ${health.ocr}` : 'checking...'}
        </div>
      </header>

      <main>
        <UploadBox onFile={handleFile} file={file} disabled={isProcessing} />

        {error && (
          <section className="card error-card">
            <h3>{error.title}</h3>
            <ul>
              {error.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </section>
        )}

        {isProcessing && <Loading stages={STAGES} current={stage} />}

        {result && (
          <>
            <section className="card results-summary">
              <div>
                <span className="label">Document Type</span>
                <span className="value doc-type">{result.document_type}</span>
              </div>
              <Confidence value={result.document_confidence || averageConfidence} />
              <div>
                <span className="label">Processing Time</span>
                <span className="value">{result.processing_time_ms} ms</span>
              </div>
              <div>
                <span className="label">Regions</span>
                <span className="value">{result.regions.length}</span>
              </div>
            </section>

            {result.quality?.warnings?.length > 0 && (
              <section className="card warnings-card">
                <h3>Quality Warnings</h3>
                <ul>
                  {result.quality.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </section>
            )}

            <section className="results-grid">
              <div className="card">
                <div className="card-header">
                  <h3>Image</h3>
                  <label className="toggle">
                    <input
                      type="checkbox"
                      checked={showBoxes}
                      onChange={(e) => {
                        setShowBoxes(e.target.checked)
                        setSelectedRegion(null)
                      }}
                    />
                    Show OCR Boxes
                  </label>
                </div>
                <ImagePreview
                  imageUrl={overlayUrl}
                  regions={result.regions}
                  showBoxes={showBoxes}
                  selectedIndex={selectedRegion}
                  onSelect={setSelectedRegion}
                />
                {showBoxes && selectedRegion !== null && result.regions[selectedRegion] && (
                  <div className="region-detail">
                    <span className="label">Text</span>
                    <p>{result.regions[selectedRegion].text}</p>
                    <span className="label">Confidence</span>
                    <p>{(result.regions[selectedRegion].confidence * 100).toFixed(1)}%</p>
                  </div>
                )}
              </div>

              <div className="card">
                <div className="card-header">
                  <h3>Extracted Text</h3>
                </div>
                <OCRText text={result.text} />
              </div>
            </section>

            <StructuredData data={result.structured_data} documentType={result.document_type} />

            <TextRegions regions={result.regions} onSelect={(i) => { setShowBoxes(true); setSelectedRegion(i) }} />

            <div className="actions">
              <button
                className="btn"
                onClick={() => navigator.clipboard.writeText(result.text)}
              >
                Copy Text
              </button>
              <button
                className="btn"
                onClick={() =>
                  downloadBlob(result.text, 'text/plain', `${result.document_type}.txt`)
                }
              >
                Download TXT
              </button>
              <button
                className="btn"
                onClick={() =>
                  downloadBlob(
                    JSON.stringify(result, null, 2),
                    'application/json',
                    `${result.document_type}.json`,
                  )
                }
              >
                Download JSON
              </button>
              <button className="btn btn-secondary" onClick={reset}>
                Clear / New Document
              </button>
            </div>

            <p className="disclaimer">{result.disclaimer}</p>
          </>
        )}
      </main>
    </div>
  )
}