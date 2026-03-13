import React from 'react';
import { Search, Bell, User } from 'lucide-react';
import './Topbar.css';

const Topbar = () => {
  return (
    <header className="topbar glass">
      <div className="search-container">
        <Search className="search-icon" size={20} />
        <input type="text" placeholder="Search" className="search-input" />
        <button className="search-btn">Search</button>
      </div>
      
      <div className="topbar-actions">
        <div className="icon-badge-container">
          <Bell size={22} className="topbar-icon" />
          <span className="notification-dot"></span>
        </div>
        <div className="user-profile">
          <img 
            src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" 
            alt="User avatar" 
            className="avatar"
          />
        </div>
      </div>
    </header>
  );
};

export default Topbar;
