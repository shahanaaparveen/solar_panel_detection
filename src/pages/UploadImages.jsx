import { useRef, useState } from 'react';
import { FolderOpen, CheckCircle, X, Image } from 'lucide-react';

function UploadSection({ type, files, setFiles }) {
  const inputRef = useRef();
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [done, setDone] = useState(false);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (fileList) => {
    const accepted = Array.from(fileList).filter(f =>
      /\.(jpg|jpeg|png|tif|tiff)$/i.test(f.name)
    );
    if (accepted.length === 0) return;
    setFiles(accepted);
    setDone(false);
    setProgress(0);
    simulateUpload(accepted.length);
  };

  const simulateUpload = (count) => {
    setUploading(true);
    let p = 0;
    const step = Math.max(2, Math.round(100 / (count * 2)));
    const iv = setInterval(() => {
      p = Math.min(100, p + step);
      setProgress(p);
      if (p >= 100) { clearInterval(iv); setUploading(false); setDone(true); }
    }, 80);
  };

  const removeFile = (idx) => {
    const updated = files.filter((_, i) => i !== idx);
    setFiles(updated);
    if (updated.length === 0) { setDone(false); setProgress(0); }
  };

  const clearAll = () => { setFiles([]); setDone(false); setProgress(0); setUploading(false); };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="card">
      <div className="section-title mb-4">Upload {type}</div>

      <div
        className="upload-zone"
        style={{ borderColor: dragging ? '#6366f1' : undefined, background: dragging ? 'rgba(99,102,241,0.05)' : undefined }}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current.click()}
      >
        <p style={{ fontWeight: 600, marginBottom: 6, color: '#e2e8f0' }}>
          Drag & Drop your {type.toLowerCase()} here
        </p>
        <p className="text-muted text-sm" style={{ marginBottom: 16 }}>or</p>
        <button
          className="btn btn-primary"
          style={{ margin: '0 auto' }}
          onClick={e => { e.stopPropagation(); inputRef.current.click(); }}
        >
          <FolderOpen size={15} /> Browse Files
        </button>
        <p className="text-muted text-xs" style={{ marginTop: 12 }}>
          Supported formats: .jpg, .jpeg, .png, .tif
        </p>
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".jpg,.jpeg,.png,.tif,.tiff"
        style={{ display: 'none' }}
        onChange={e => handleFiles(e.target.files)}
      />

      {(uploading || done) && files.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="flex justify-between text-sm mb-3">
            <span>
              {done
                ? <span className="flex items-center gap-2 text-success"><CheckCircle size={14} /> Upload Complete</span>
                : `Uploading... (${Math.round(progress / 100 * files.length)}/${files.length})`}
            </span>
            <span>{progress}%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {files.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="flex justify-between items-center mb-3">
            <span style={{ fontSize: 12, color: '#94a3b8' }}>{files.length} file{files.length > 1 ? 's' : ''} selected</span>
            <button className="btn btn-outline" style={{ padding: '3px 10px', fontSize: 11, color: '#ef4444', borderColor: '#ef4444' }} onClick={clearAll}>
              Clear All
            </button>
          </div>
          <div style={{ maxHeight: 180, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {files.map((f, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px', background: '#0b1120', borderRadius: 7, fontSize: 12 }}>
                <Image size={13} color="#6366f1" style={{ flexShrink: 0 }} />
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#cbd5e1' }}>{f.name}</span>
                <span style={{ color: '#64748b', flexShrink: 0 }}>{(f.size / 1024).toFixed(0)} KB</span>
                <button onClick={() => removeFile(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: 0, display: 'flex' }}>
                  <X size={13} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function UploadImages({ onStartAnalysis }) {
  const [thermalFiles, setThermalFiles] = useState([]);
  const [rgbFiles, setRgbFiles] = useState([]);

  const canStart = thermalFiles.length > 0 || rgbFiles.length > 0;

  return (
    <div>
      <div className="page-title">Upload Images</div>
      <div className="page-subtitle">Upload drone-captured thermal and RGB images for analysis</div>

      <div className="grid-2">
        <UploadSection type="Thermal Images" files={thermalFiles} setFiles={setThermalFiles} />
        <UploadSection type="RGB Images" files={rgbFiles} setFiles={setRgbFiles} />
      </div>

      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <button
          className="btn btn-success"
          style={{ padding: '12px 40px', fontSize: 15, opacity: canStart ? 1 : 0.4, cursor: canStart ? 'pointer' : 'not-allowed' }}
          disabled={!canStart}
          onClick={() => onStartAnalysis(thermalFiles, rgbFiles)}
        >
          🚀 Start Analysis
        </button>
        {!canStart && <p className="text-muted text-xs" style={{ marginTop: 8 }}>Upload at least one image to start analysis</p>}
      </div>
    </div>
  );
}
