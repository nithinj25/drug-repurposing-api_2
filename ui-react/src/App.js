import React, { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import InputForm from './components/InputForm';
import ResultsDisplay from './components/ResultsDisplay';
import DetailsModal from './components/DetailsModal';

function App() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [apiUrl, setApiUrl] = useState(() => {
    return localStorage.getItem('apiUrl') || 'http://localhost:8000';
  });
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [pollInterval, setPollInterval] = useState(null);

  // Save API URL to localStorage
  useEffect(() => {
    localStorage.setItem('apiUrl', apiUrl);
  }, [apiUrl]);

  // Cleanup poll interval on unmount
  useEffect(() => {
    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [pollInterval]);

  const showStatus = (message, type) => {
    setStatus({ message, type });
    if (type === 'success') {
      setTimeout(() => setStatus(null), 5000);
    }
  };

  const handleAnalyze = async (drugName, indication, query) => {
    setLoading(true);
    setResults(null);

    try {
      const payload = {
        drug_name: drugName,
        indication: indication,
        ...(query && { query: query })
      };

      const response = await fetch(`${apiUrl}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to submit analysis');
      }

      const data = await response.json();
      setJobId(data.job_id);
      showStatus(`Analysis submitted! Job ID: ${data.job_id}`, 'info');

      // Start polling for results
      pollResults(data.job_id);

    } catch (error) {
      console.error('Error:', error);
      showStatus(`Error: ${error.message}`, 'error');
      setLoading(false);
    }
  };

  const pollResults = (id) => {
    let pollCount = 0;
    const maxPolls = 120; // 2 minutes

    const interval = setInterval(async () => {
      pollCount++;

      try {
        const response = await fetch(`${apiUrl}/jobs/${id}`);
        if (!response.ok) {
          throw new Error('Failed to fetch job status');
        }

        const data = await response.json();

        if (data.status === 'completed') {
          clearInterval(interval);
          setPollInterval(null);
          setResults(data);
          setLoading(false);
          showStatus('Analysis complete!', 'success');
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setPollInterval(null);
          setLoading(false);
          showStatus(`Analysis failed: ${data.error || 'Unknown error'}`, 'error');
        }
      } catch (error) {
        console.error('Poll error:', error);
        if (pollCount >= maxPolls) {
          clearInterval(interval);
          setPollInterval(null);
          setLoading(false);
          showStatus('Analysis timeout - please check job status later', 'error');
        }
      }
    }, 1000);

    setPollInterval(interval);
  };

  return (
    <div className="app">
      <Header />
      
      <main className="main-content">
        <div className="input-section">
          <InputForm 
            onAnalyze={handleAnalyze} 
            loading={loading}
            apiUrl={apiUrl}
            onApiUrlChange={setApiUrl}
          />
          {status && (
            <div className={`status-message ${status.type}`}>
              {status.message}
            </div>
          )}
        </div>

        <div className="results-section">
          {loading ? (
            <LoadingSkeleton />
          ) : results ? (
            <ResultsDisplay 
              results={results}
              onAgentClick={setSelectedAgent}
            />
          ) : (
            <EmptyState />
          )}
        </div>
      </main>

      {selectedAgent && (
        <DetailsModal 
          agent={selectedAgent}
          onClose={() => setSelectedAgent(null)}
        />
      )}
    </div>
  );
}

const EmptyState = () => (
  <div className="empty-state">
    <p>👉 Enter a drug name and indication to begin analysis</p>
  </div>
);

const LoadingSkeleton = () => (
  <div className="loading-skeleton">
    {[1, 2, 3].map(i => (
      <div key={i} className="skeleton-card">
        <div className="skeleton-title"></div>
        <div className="skeleton-line"></div>
        <div className="skeleton-line"></div>
      </div>
    ))}
  </div>
);

export default App;
