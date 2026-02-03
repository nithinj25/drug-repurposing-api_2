import React from 'react';

function ResultCard({ title, metaItems }) {
  const renderValue = (value) => {
    // If value is already a React element, return it as is
    if (React.isValidElement(value)) {
      return value;
    }
    // If value is an object, convert to string
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value);
    }
    // Otherwise return as is
    return value;
  };

  return (
    <div className="result-card">
      <div className="result-card-header">
        <div className="result-card-title">{title}</div>
      </div>
      <div className="result-card-meta">
        {metaItems.map((item, idx) => (
          <div key={idx} className="meta-item">
            <strong>{item.label}:</strong> <span>{renderValue(item.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ResultCard;
