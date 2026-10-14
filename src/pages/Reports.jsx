import { Download, FileSpreadsheet } from 'lucide-react';

export default function Reports() {
  return (
    <div>
      <div className="page-title">Reports</div>
      <div className="page-subtitle">Generate and export professional inspection reports</div>

      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>Solar Panel Inspection Report</div>
            <div className="text-muted text-sm">No project selected</div>
          </div>
          <div className="flex gap-3">
            <button className="btn btn-danger" disabled style={{ opacity: 0.4 }}><Download size={14} /> Export PDF</button>
            <button className="btn btn-success" disabled style={{ opacity: 0.4 }}><FileSpreadsheet size={14} /> Export Excel</button>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 300, color: '#334155', fontSize: 13, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 14 }}>📄</div>
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 8, color: '#64748b' }}>No Report Data Available</div>
          <div style={{ color: '#475569' }}>Complete an inspection analysis first to generate a report.</div>
        </div>
      </div>
    </div>
  );
}
