import React from 'react';

function DetailsModal({ agent, onClose }) {
  const formatAgentName = (name) => {
    return name
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getTitle = () => {
    if (agent.type === 'raw') {
      return 'Raw JSON Response (Advanced)';
    }
    return `${formatAgentName(agent.agentName)} - Full Analysis`;
  };

  const formatObject = (obj, depth = 0) => {
    if (typeof obj === 'string') {
      return obj;
    }
    if (typeof obj === 'number' || typeof obj === 'boolean') {
      return obj.toString();
    }
    if (Array.isArray(obj)) {
      return (
        <ul style={{ marginLeft: '1.5rem', marginTop: '0.5rem' }}>
          {obj.map((item, idx) => (
            <li key={idx} style={{ marginBottom: '0.5rem' }}>
              {formatObject(item, depth + 1)}
            </li>
          ))}
        </ul>
      );
    }
    if (typeof obj === 'object' && obj !== null) {
      return (
        <div style={{ marginLeft: '1rem', marginTop: '0.5rem' }}>
          {Object.entries(obj).map(([key, value]) => (
            <div key={key} style={{ marginBottom: '1rem' }}>
              <strong style={{ color: '#6366f1' }}>{formatAgentName(key)}:</strong>
              <div style={{ marginLeft: '0.5rem', marginTop: '0.25rem' }}>
                {formatObject(value, depth + 1)}
              </div>
            </div>
          ))}
        </div>
      );
    }
    return 'N/A';
  };

  const getContent = () => {
    if (agent.type === 'raw') {
      return formatObject(agent.data);
    }
    return formatObject(agent.result);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{getTitle()}</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body" style={{ fontSize: '0.95rem', lineHeight: '1.6' }}>
          {typeof getContent() === 'string' ? (
            <p>{getContent()}</p>
          ) : (
            getContent()
          )}
        </div>
      </div>
    </div>
  );
}

export default DetailsModal;
