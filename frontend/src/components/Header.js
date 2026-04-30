import React from 'react';
import './Header.css';
 
export default function Header() {
  return (
    <header className="header">
      <div className="header-left">
        <div className="logo">
          <span className="logo-icon">⚕</span>
          <span className="logo-text">HCP<span>CRM</span></span>
        </div>
        <span className="breadcrumb">Log Interaction</span>
      </div>
      <div className="header-right">
        <span className="status-badge">
          <span className="status-dot" />
          AI Active
        </span>
      </div>
    </header>
  );
}