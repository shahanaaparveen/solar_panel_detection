import { LayoutDashboard, Upload, Cpu, GitMerge, FileText, BarChart2, Eye, FolderOpen, Settings, HelpCircle, LogOut } from 'lucide-react';
import BrandLogo from './BrandLogo';

const navItems = [
  { id: 'dashboard', label: 'Dashboard',      icon: LayoutDashboard },
  { id: 'upload',    label: 'Upload Images',   icon: Upload },
  { id: 'analysis',  label: 'Image Analysis',  icon: Cpu },
  { id: 'mapping',   label: 'Panel Mapping',   icon: GitMerge },
  { id: 'reports',   label: 'Reports',         icon: FileText },
  { id: 'summary',   label: 'Defect Summary',  icon: BarChart2 },
  { id: 'preview',   label: 'Report Preview',  icon: Eye },
  { id: 'projects',  label: 'Projects',        icon: FolderOpen },
  { id: 'settings',  label: 'Settings',        icon: Settings },
];

export default function Sidebar({ activePage, onNavigate, onLogout }) {
  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <BrandLogo compact />
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`nav-item ${activePage === id ? 'active' : ''}`}
            onClick={() => onNavigate(id)}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <button className="nav-item">
          <HelpCircle size={15} /> Help & Support
        </button>
        <button className="nav-item" onClick={onLogout} style={{ color: '#ef4444' }}>
          <LogOut size={15} /> Logout
        </button>
      </div>
    </div>
  );
}
