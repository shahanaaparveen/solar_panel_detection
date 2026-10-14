import { useState } from 'react';
import { ZoomIn, ZoomOut, Printer, Download, ChevronLeft, ChevronRight } from 'lucide-react';

export default function ReportPreview() {
  const [zoom, setZoom] = useState(90);

  return (
    <div>
      <div className="page-title">Report Preview</div>
      <div className="page-subtitle">Review the generated report before downloading</div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {/* Toolbar */}
        <div className="flex items-center justify-between" style={{ padding: '12px 20px', borderBottom: '1px solid #1e2d45', background: '#111827' }}>
          <div className="flex items-center gap-3">
            <button className="btn btn-outline" style={{ padding: '6px 10px' }} disabled><ChevronLeft size={14} /></button>
            <span className="text-sm text-muted">— / —</span>
            <button className="btn btn-outline" style={{ padding: '6px 10px' }} disabled><ChevronRight size={14} /></button>
          </div>
          <div className="flex items-center gap-3">
            <button className="btn btn-outline" style={{ padding: '6px 10px' }} onClick={() => setZoom(z => Math.max(50, z - 10))}><ZoomOut size={14} /></button>
            <span className="text-sm">{zoom}%</span>
            <button className="btn btn-outline" style={{ padding: '6px 10px' }} onClick={() => setZoom(z => Math.min(150, z + 10))}><ZoomIn size={14} /></button>
            <button className="btn btn-outline" style={{ padding: '6px 10px' }} disabled><Printer size={14} /></button>
            <button className="btn btn-primary" style={{ padding: '6px 14px' }} disabled><Download size={14} /></button>
          </div>
        </div>

        {/* Empty state */}
        <div style={{ padding: 24, background: '#1e2d45', minHeight: 460, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center', color: '#475569' }}>
            <div style={{ fontSize: 56, marginBottom: 16 }}>📋</div>
            <div style={{ fontWeight: 700, fontSize: 16, color: '#64748b', marginBottom: 8 }}>No Report Generated Yet</div>
            <div style={{ fontSize: 13 }}>Complete an inspection and generate a report to preview it here.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
