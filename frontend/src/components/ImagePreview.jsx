import { useEffect, useRef } from 'react'

export default function ImagePreview({ imageUrl, regions, showBoxes, selectedIndex, onSelect }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !imageUrl) return undefined
    const ctx = canvas.getContext('2d')
    const img = new Image()
    img.onload = () => {
      const maxWidth = 560
      const scale = Math.min(1, maxWidth / img.naturalWidth)
      canvas.width = Math.round(img.naturalWidth * scale)
      canvas.height = Math.round(img.naturalHeight * scale)
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      if (showBoxes && regions?.length) {
        regions.forEach((region, index) => {
          const [x0, y0, x1, y1] = region.bbox
          const isSelected = index === selectedIndex
          ctx.fillStyle = isSelected ? 'rgba(255, 90, 95, 0.14)' : 'rgba(34, 197, 94, 0.08)'
          ctx.fillRect(x0 * scale, y0 * scale, (x1 - x0) * scale, (y1 - y0) * scale)
          ctx.strokeStyle = isSelected ? '#ff5a5f' : '#22c55e'
          ctx.lineWidth = isSelected ? 3 : 1.5
          ctx.strokeRect(x0 * scale, y0 * scale, (x1 - x0) * scale, (y1 - y0) * scale)
        })
      }
    }
    img.src = imageUrl
    return undefined
  }, [imageUrl, regions, showBoxes, selectedIndex])

  const handleClick = (event) => {
    if (!showBoxes || !regions?.length || !onSelect) return
    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const x = (event.clientX - rect.left) * scaleX
    const y = (event.clientY - rect.top) * scaleY
    const hit = regions.findIndex(
      (r) => x >= r.bbox[0] && x <= r.bbox[2] && y >= r.bbox[1] && y <= r.bbox[3],
    )
    if (hit >= 0) onSelect(hit)
  }

  if (!imageUrl) return null
  return (
    <canvas
      ref={canvasRef}
      className={`image-preview-canvas ${showBoxes ? 'clickable' : ''}`}
      onClick={handleClick}
    />
  )
}