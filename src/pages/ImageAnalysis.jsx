import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export default function ImageAnalysis({ thermalFiles }) {
  const [idx, setIdx] = useState(0);
  const [urls, setUrls] = useState([]);

  // Create object URLs for the File objects
  useEffect(() => {
    const created = thermalFiles.map(f => URL.createObjectURL(f));
    setUrls(created);
    setIdx(0);
    return () => created.forEach(u => URL.revokeObjectURL(u));
  }, [thermalFiles]);

  const hasImages = urls.length > 0;

  return (
    <div>
      <div className="topbar">
        <div>
          <div className="page-title">Image Analysis <span style={{ color: '#6366f1' }}>(AI Detection)</span></div>
          <div className="page-subtitle">Thermal image analysis with automatic defect detection and annotation</div>
        </div>
        {hasImages && (
          <div style={{ fontSize: 13, color: '#94a3b8' }}>
            {urls.length} thermal image{urls.length > 1 ? 's' : ''} loaded
          </div>
        )}
      </div>

      <div className="grid-2">
        {/* Image viewer */}
        <div className="card" style={{ padding: 14 }}>
          <div className="flex justify-between items-center mb-3">
            <button
              className="btn btn-outline"
              style={{ padding: '5px 10px', fontSize: 12 }}
              disabled={!hasImages || idx === 0}
              onClick={() => setIdx(i => i - 1)}
            >
              <ChevronLeft size={13} /> Previous
            </button>
            <span style={{ fontWeight: 600, fontSize: 13, color: hasImages ? '#e2e8f0' : '#64748b' }}>
              {hasImages ? thermalFiles[idx].name : 'No image loaded'}
            </span>
            <button
              className="btn btn-outline"
              style={{ padding: '5px 10px', fontSize: 12 }}
              disabled={!hasImages || idx === urls.length - 1}
              onClick={() => setIdx(i => i + 1)}
            >
              Next <ChevronRight size={13} />
            </button>
          </div>

          {hasImages ? (
            <div style={{ position: 'relative', width: '100%', borderRadius: 8, overflow: 'hidden', background: '#000' }}>
              <img
                src={urls[idx]}
                alt={thermalFiles[idx].name}
                style={{ width: '100%', maxHeight: 320, objectFit: 'contain', display: 'block', borderRadius: 8 }}
              />
            </div>
          ) : (
            <div style={{ width: '100%', height: 280, background: '#0b1120', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px dashed #1e2d45' }}>
              <div style={{ textAlign: 'center', color: '#334155' }}>
                <div style={{ fontSize: 40, marginBottom: 10 }}>🌡️</div>
                <div style={{ fontSize: 13 }}>No thermal image uploaded yet.</div>
              </div>
            </div>
          )}

          {hasImages && (
            <div className="flex justify-between items-center mt-3" style={{ fontSize: 12, color: '#64748b' }}>
              <span>Image {idx + 1} of {urls.length}</span>
              <span>{(thermalFiles[idx].size / 1024).toFixed(0)} KB</span>
            </div>
          )}
        </div>

        {/* Detected defects panel */}
        <div className="card" style={{ padding: 14 }}>
          <div className="section-title mb-3">Detected Defects</div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 200, color: '#334155', fontSize: 13, textAlign: 'center' }}>
            <div style={{ fontSize: 36, marginBottom: 10 }}>🔍</div>
            {hasImages
              ? 'AI analysis not yet run.\nDefects will appear here after processing.'
              : 'No defects detected yet.\nUpload thermal images and run analysis.'}
          </div>

          <div style={{ marginTop: 16, padding: '12px 14px', background: '#0b1120', borderRadius: 8, fontSize: 13 }}>
            <div className="flex justify-between mb-3">
              <span className="text-muted">Total Images</span>
              <span className="font-bold">{hasImages ? urls.length : '—'}</span>
            </div>
            <div className="flex justify-between mb-3">
              <span className="text-muted">Total Defects Found</span>
              <span className="font-bold">—</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Confidence (avg)</span>
              <span className="font-bold text-muted">—</span>
            </div>
          </div>

          <button className="btn btn-primary w-full mt-4" style={{ justifyContent: 'center' }} disabled={!hasImages}>
            View All Detections
          </button>
        </div>
      </div>
    </div>
  );
}
