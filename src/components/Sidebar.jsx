import React from 'react';
import { 
  LayoutDashboard, 
  Rss, 
  GitBranch, 
  BarChart3, 
  BellRing, 
  History, 
  Settings,
  ShieldCheck,
  ShieldAlert,
  Globe,
  Network,
  Camera
} from 'lucide-react';
import { NavLink } from 'react-router-dom';
import './Sidebar.css';

const Sidebar = () => {
  const menuItems = [
    { icon: <LayoutDashboard size={20} />, label: 'Dashboard', path: '/' },
    { icon: <Rss size={20} />, label: 'Live Feed', path: '/live-feed' },
    { icon: <ShieldAlert size={20} />, label: 'Investigation', path: '/investigation' },
    { icon: <GitBranch size={20} />, label: 'Narrative Graph', path: '/narrative' },
    { icon: <BarChart3 size={20} />, label: 'Analytics', path: '/analytics' },
    { icon: <BellRing size={20} />, label: 'Alert Configuration', path: '/alerts' },
    { icon: <History size={20} />, label: 'Audit Log', path: '/audit' },
    { icon: <Globe size={20} />, label: 'Geo Intelligence', path: '/geo' },
    { icon: <Camera size={20} />, label: 'Deepfake Radar', path: '/deepfake' },
    { icon: <Network size={20} />, label: 'Federated Network', path: '/federated' },
    { icon: <Settings size={20} />, label: 'Settings', path: '/settings' },
  ];

  return (
    <div className="sidebar">
      <div className="logo-container">
        <ShieldCheck className="logo-icon" size={32} fill="var(--primary)" color="white" />
        <span className="logo-text">Misinfo Shield</span>
      </div>
      
      <nav className="sidebar-nav">
        {menuItems.map((item, idx) => (
          <NavLink 
            key={idx} 
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
};

export default Sidebar;
