import { useRef, useState } from 'react'

const ACCEPTED = '.jpg,.jpeg,.png,.bmp,.webp,.tif,.tiff'

export default function UploadBox({ onFile, file, disabled }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    if (disabled) return
    const dropped = e.dataTransfer?.files?.[0]
    if (dropped) onFile(dropped)
  }

  const formatSize = (bytes) =>
    bytes > 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`

  return (
    <section
      className={`card upload-box ${dragging ? 'dragging' : ''}`}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <div className="upload-inner">
        <p className="upload-title">Upload Document</p>
        <p className="upload-hint">Drag &amp; drop an image here</p>
        <button
          type="button"
          className="btn"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          Select Image
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          hidden
          onChange={(e) => {
            const selected = e.target.files?.[0]
            if (selected) onFile(selected)
            e.target.value = ''
          }}
        />
        <p className="upload-meta">
          Supported: JPG, PNG, BMP, WEBP, TIFF &middot; Max 10 MB
          {file && <span className="file-chip">{file.name} ({formatSize(file.size)})</span>}
        </p>
      </div>
    </section>
  )
}