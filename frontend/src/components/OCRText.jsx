import { useState } from 'react'

export default function OCRText({ text }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  if (!text) {
    return <p className="muted">No text recognized in this image.</p>
  }
  return (
    <div className="ocr-text-wrapper">
      <button type="button" className="btn btn-small" onClick={handleCopy}>
        {copied ? 'Copied!' : 'Copy Text'}
      </button>
      <pre className="ocr-text">{text}</pre>
    </div>
  )
}