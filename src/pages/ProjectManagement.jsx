import { useState } from 'react';
import { Plus, Trash2, Search } from 'lucide-react';

export default function ProjectManagement() {
  const [projects, setProjects] = useState([]);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newLocation, setNewLocation] = useState('');

  const filtered = projects.filter(p => p.name.toLowerCase().includes(search.toLowerCase()));

  const addProject = () => {
    if (!newName.trim()) return;
    setProjects(prev => [...prev, {
      id: Date.now(),
      name: newName,
      location: newLocation || '—',
      images: 0,
      panels: 0,
      defective: 0,
      date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
      status: 'Processing',
    }]);
    setNewName('');
    setNewLocation('');
    setShowForm(false);
  };

  const deleteProject = id => setProjects(prev => prev.filter(p => p.id !== id));

  return (
    <div>
      <div className="flex justify-between items-center mb-5">
        <div>
          <div className="page-title">Project Management</div>
          <div className="page-subtitle">Manage all your solar inspection projects</div>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          <Plus size={14} /> New Project
        </button>
      </div>

      {showForm && (
        <div className="card mb-5">
          <div className="section-title mb-4">Create New Project</div>
          <div className="flex gap-3">
            <input className="form-input" placeholder="Project name" value={newName} onChange={e => setNewName(e.target.value)} style={{ flex: 1 }} />
            <input className="form-input" placeholder="Location" value={newLocation} onChange={e => setNewLocation(e.target.value)} style={{ flex: 1 }} />
            <button className="btn btn-primary" onClick={addProject}>Create</button>
            <button className="btn btn-outline" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
            <input className="form-input" placeholder="Search projects..." value={search} onChange={e => setSearch(e.target.value)} style={{ paddingLeft: 36 }} />
          </div>
        </div>

        {filtered.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 200, color: '#334155', fontSize: 13, textAlign: 'center' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>📁</div>
            <div style={{ fontWeight: 600, fontSize: 14, color: '#64748b', marginBottom: 8 }}>No Projects Found</div>
            <div style={{ color: '#475569' }}>Click "New Project" to create your first inspection project.</div>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Project Name</th>
                <th>Location</th>
                <th>Images</th>
                <th>Panels</th>
                <th>Defective</th>
                <th>Date</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p, i) => (
                <tr key={p.id}>
                  <td className="text-muted">{i + 1}</td>
                  <td style={{ fontWeight: 600 }}>{p.name}</td>
                  <td className="text-muted">{p.location}</td>
                  <td>{p.images}</td>
                  <td>{p.panels}</td>
                  <td className="text-danger">{p.defective}</td>
                  <td className="text-muted">{p.date}</td>
                  <td><span className={`badge ${p.status === 'Completed' ? 'badge-success' : 'badge-warning'}`}>{p.status}</span></td>
                  <td>
                    <button className="btn btn-outline" style={{ padding: '4px 8px', color: '#ef4444', borderColor: '#ef4444' }} onClick={() => deleteProject(p.id)}>
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
