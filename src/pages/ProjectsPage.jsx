import { useState } from 'react';
import { LogOut, FolderOpen, FileText, Plus, Trash2, AlertTriangle, X } from 'lucide-react';
import BrandLogo from '../components/BrandLogo';

export default function ProjectsPage({ projects, onNewProject, onOpenProject, onViewReports, onLogout, onDeleteProject }) {
  const [projectToDelete, setProjectToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  const confirmDelete = async () => {
    if (!projectToDelete) return;
    setIsDeleting(true);
    try {
      if (onDeleteProject) {
        await onDeleteProject(projectToDelete._id || projectToDelete.id);
      }
    } finally {
      setIsDeleting(false);
      setProjectToDelete(null);
    }
  };

  return (
    <div style={s.page}>
      {/* Top bar */}
      <div style={s.topbar}>
        <div style={s.logo}>
          <BrandLogo compact size={0.75} style={{ maxHeight: '32px', width: 'auto' }} />
        </div>
        <div style={s.topRight}>
          <button style={s.btnOutline} onClick={onViewReports}><FileText size={14} /> View Reports</button>
          <button style={s.btnPrimary} onClick={onNewProject}><Plus size={14} /> New Project</button>
          <button style={s.btnIcon} onClick={onLogout} title="Logout"><LogOut size={16} color="#ef4444" /></button>
        </div>
      </div>

      {/* Content */}
      <div style={s.content}>
        <div style={s.heading}>Recent Projects</div>
        <div style={s.sub}>All your solar inspection projects</div>

        <div style={s.tableWrap}>
          {projects.length === 0 ? (
            <div style={s.empty}>
              <FolderOpen size={48} color="#334155" />
              <div style={{ marginTop: 12, color: '#64748b', fontSize: 14 }}>No projects yet.</div>
              <button style={{ ...s.btnPrimary, marginTop: 16 }} onClick={onNewProject}><Plus size={14} /> Create First Project</button>
            </div>
          ) : (
            <table style={s.table}>
              <thead>
                <tr>
                  {['S.No', 'Project Name', 'Company', 'Location', 'Status', 'Date', 'Actions'].map(h => (
                    <th key={h} style={s.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {projects.map((p, i) => (
                  <tr key={p._id || p.id || i} style={s.tr} onClick={() => onOpenProject(p)}>
                    <td style={s.td}>{i + 1}</td>
                    <td style={{ ...s.td, fontWeight: 600, color: '#0a2545' }}>{p.projectName}</td>
                    <td style={s.td}>{p.companyName}</td>
                    <td style={s.td}>{p.location}</td>
                    <td style={s.td}>
                      <span style={{ ...s.badge, ...(p.status === 'Completed' ? s.badgeGreen : p.status === 'In Progress' ? s.badgeBlue : s.badgeAmber) }}>
                        {p.status}
                      </span>
                    </td>
                    <td style={{ ...s.td, color: '#475569', fontSize: 13, whiteSpace: 'nowrap' }}>
                      {formatDate(p.createdAt || p.date)}
                    </td>
                    <td style={s.td} onClick={e => e.stopPropagation()}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                        <button style={s.btnSm} onClick={() => onOpenProject(p)} title="Open Project">
                          Open →
                        </button>
                        <button
                          style={s.btnDelete}
                          title="Delete Project"
                          onClick={(e) => {
                            e.stopPropagation();
                            setProjectToDelete(p);
                          }}
                        >
                          <Trash2 size={13} />
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Confirmation Modal */}
      {projectToDelete && (
        <div style={s.modalOverlay} onClick={() => !isDeleting && setProjectToDelete(null)}>
          <div style={s.modalBox} onClick={e => e.stopPropagation()}>
            <div style={s.modalHeader}>
              <div style={s.modalIconWrap}>
                <AlertTriangle size={20} color="#dc2626" />
              </div>
              <div style={{ flex: 1 }}>
                <div style={s.modalTitle}>Delete Project Confirmation</div>
                <div style={s.modalSub}>Are you sure you want to delete this project?</div>
              </div>
              <button
                style={s.modalCloseBtn}
                onClick={() => !isDeleting && setProjectToDelete(null)}
                disabled={isDeleting}
              >
                <X size={16} color="#64748b" />
              </button>
            </div>

            <div style={s.modalBody}>
              <p style={{ margin: 0, color: '#334155', fontSize: 13.5, lineHeight: 1.5 }}>
                Do you really want to delete <strong>"{projectToDelete.projectName || 'Unnamed Project'}"</strong>?
              </p>
              <div style={s.projectDetailsBox}>
                <div style={{ fontSize: 12, color: '#64748b' }}>
                  <strong>Company:</strong> {projectToDelete.companyName || '—'}
                </div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                  <strong>Location:</strong> {projectToDelete.location || '—'}
                </div>
              </div>
              <p style={{ margin: '14px 0 0', color: '#e11d48', fontSize: 12, fontWeight: 500 }}>
                ⚠️ This action cannot be undone. All associated image detections and reports will be removed.
              </p>
            </div>

            <div style={s.modalFooter}>
              <button
                style={s.modalBtnNo}
                onClick={() => setProjectToDelete(null)}
                disabled={isDeleting}
              >
                No
              </button>
              <button
                style={s.modalBtnYes}
                onClick={confirmDelete}
                disabled={isDeleting}
              >
                <Trash2 size={14} />
                {isDeleting ? 'Deleting...' : 'Yes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const s = {
  page: { minHeight: '100vh', background: '#ffffff', color: '#0a2545', fontFamily: "'Segoe UI',sans-serif", display: 'flex', flexDirection: 'column' },
  topbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 28px', minHeight: '48px', background: '#ffffff', borderBottom: '1px solid #d9e2f0' },
  logo: { display: 'flex', alignItems: 'center', gap: 10, maxHeight: '34px' },
  topRight: { display: 'flex', alignItems: 'center', gap: 10 },
  btnPrimary: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', background: '#0a2545', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  btnOutline: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 13px', background: 'transparent', color: '#0a2545', border: '1px solid #d9e2f0', borderRadius: 6, fontSize: 13, cursor: 'pointer' },
  btnIcon: { display: 'inline-flex', alignItems: 'center', padding: '6px', background: 'transparent', border: '1px solid #d9e2f0', borderRadius: 6, cursor: 'pointer' },
  btnSm: { padding: '5px 12px', background: '#0a2545', color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer' },
  btnDelete: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '5px 10px', background: '#fff1f2', color: '#e11d48', border: '1px solid #fecdd3', borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s ease' },
  content: { flex: 1, padding: '28px 40px', background: '#ffffff' },
  heading: { fontSize: 22, fontWeight: 700, marginBottom: 4, color: '#0a2545' },
  sub: { fontSize: 13, color: '#55657f', marginBottom: 24 },
  tableWrap: { background: '#ffffff', borderRadius: 12, border: '1px solid #d9e2f0', overflow: 'hidden', boxShadow: '0 2px 8px rgba(10,37,69,0.04)' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { padding: '11px 16px', textAlign: 'left', fontSize: 11, color: '#55657f', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, borderBottom: '1px solid #d9e2f0', background: '#f8fafc' },
  tr: { cursor: 'pointer', transition: 'background 0.15s' },
  td: { padding: '12px 16px', fontSize: 13, color: '#0a2545', borderBottom: '1px solid #eef3fa' },
  empty: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '80px 0', color: '#55657f' },
  badge: { display: 'inline-block', padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600 },
  badgeGreen: { background: '#eefdf5', color: '#0a2545', border: '1px solid #b7d7c7' },
  badgeBlue: { background: '#ecf3ff', color: '#0a2545', border: '1px solid #b8cce9' },
  badgeAmber: { background: '#fff5ef', color: '#b91c1c', border: '1px solid #f4c7b5' },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(10, 37, 69, 0.45)',
    backdropFilter: 'blur(3px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
    padding: 20,
  },
  modalBox: {
    background: '#ffffff',
    borderRadius: 14,
    width: '100%',
    maxWidth: 440,
    boxShadow: '0 20px 40px rgba(10,37,69,0.18), 0 2px 10px rgba(0,0,0,0.06)',
    border: '1px solid #e2e8f0',
    overflow: 'hidden',
  },
  modalHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '16px 20px',
    borderBottom: '1px solid #f1f5f9',
    background: '#fff8f8',
  },
  modalIconWrap: {
    width: 36,
    height: 36,
    borderRadius: '50%',
    background: '#fee2e2',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  modalTitle: {
    fontSize: 15,
    fontWeight: 700,
    color: '#0a2545',
  },
  modalSub: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 2,
  },
  modalCloseBtn: {
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    padding: 4,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 6,
  },
  modalBody: {
    padding: '18px 20px',
  },
  projectDetailsBox: {
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    padding: '10px 14px',
    marginTop: 12,
  },
  modalFooter: {
    padding: '12px 20px',
    background: '#f8fafc',
    borderTop: '1px solid #f1f5f9',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 10,
  },
  modalBtnNo: {
    padding: '7px 18px',
    background: '#ffffff',
    color: '#334155',
    border: '1px solid #cbd5e1',
    borderRadius: 6,
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
  },
  modalBtnYes: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '7px 18px',
    background: '#dc2626',
    color: '#ffffff',
    border: 'none',
    borderRadius: 6,
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    boxShadow: '0 2px 6px rgba(220,38,38,0.25)',
  },
};
