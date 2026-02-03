import React, { useState } from 'react';

function InputForm({ onAnalyze, loading, apiUrl, onApiUrlChange }) {
  const [drugName, setDrugName] = useState('');
  const [indication, setIndication] = useState('');
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!drugName.trim() || !indication.trim()) {
      alert('Please fill in all required fields');
      return;
    }

    onAnalyze(drugName, indication, query);
    setDrugName('');
    setIndication('');
    setQuery('');
  };

  return (
    <div className="input-card">
      <h2>Analysis Input</h2>

      <form onSubmit={handleSubmit} className="form">
        <div className="form-group">
          <label htmlFor="drugName">Drug Name *</label>
          <input
            type="text"
            id="drugName"
            placeholder="e.g., Aspirin, Metformin, Ibuprofen"
            value={drugName}
            onChange={(e) => setDrugName(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="indication">Disease/Indication *</label>
          <input
            type="text"
            id="indication"
            placeholder="e.g., Alzheimer's Disease, Diabetes, Cancer"
            value={indication}
            onChange={(e) => setIndication(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="query">Research Query (Optional)</label>
          <textarea
            id="query"
            placeholder="Provide additional research context or specific questions..."
            rows="4"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div className="form-section">
          <h3>API Configuration</h3>
          <div className="form-group">
            <label htmlFor="apiUrl">API Endpoint</label>
            <input
              type="text"
              id="apiUrl"
              value={apiUrl}
              onChange={(e) => onApiUrlChange(e.target.value)}
              placeholder="http://localhost:8000"
            />
            <small style={{ color: '#64748b', marginTop: '0.25rem' }}>Default: http://localhost:8000</small>
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? (
            <>
              <span className="btn-spinner">⏳</span>
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <span>Analyze Drug</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}

export default InputForm;
