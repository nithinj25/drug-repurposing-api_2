import React from 'react';
import ResultCard from './ResultCard';
import ReasoningBox from './ReasoningBox';
import AgentGrid from './AgentGrid';

function ResultsDisplay({ results, onAgentClick }) {
  const agentIcons = {
    'literature_agent': '📚',
    'clinical_agent': '🏥',
    'safety_agent': '⚠️',
    'molecular_agent': '🧬',
    'patent_agent': '📋',
    'market_agent': '💼'
  };

  // Extract the actual data from the nested response structure
  const jobData = results.data || results;

  return (
    <div className="results-display">
      {/* Job Summary */}
      <ResultCard
        title={`${jobData.drug_name} - ${jobData.indication}`}
        metaItems={[
          { label: 'Job ID', value: jobData.job_id },
          { label: 'Status', value: <span className="badge badge-success">{jobData.status}</span> },
          { label: 'Query', value: jobData.query || 'N/A' }
        ]}
      />

      {/* Agent Results */}
      {jobData.tasks && (
        <div className="result-card">
          <h3 style={{ marginBottom: '1.5rem' }}>Agent Analysis</h3>
          <AgentGrid 
            tasks={jobData.tasks}
            agentIcons={agentIcons}
            onAgentClick={onAgentClick}
          />
        </div>
      )}

      {/* Reasoning Section */}
      {jobData.reasoning_result && (
        <ReasoningBox reasoning={jobData.reasoning_result} />
      )}

      {/* Task Summary */}
      {jobData.task_summary && (
        <div className="result-card" style={{ backgroundColor: '#f0fdf4', borderLeft: '4px solid #10b981' }}>
          <h3 style={{ marginBottom: '1rem', color: '#065f46' }}>Task Summary</h3>
          <div style={{ color: '#1e293b', lineHeight: '1.8' }}>
            {typeof jobData.task_summary === 'string' ? (
              <p>{jobData.task_summary}</p>
            ) : (
              <pre style={{ backgroundColor: 'white', padding: '1rem', borderRadius: '6px', overflow: 'auto', fontSize: '0.9rem' }}>
                {JSON.stringify(jobData.task_summary, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* Raw JSON Button */}
      <button 
        className="btn btn-secondary"
        onClick={() => onAgentClick({ type: 'raw', data: jobData })}
        style={{ marginTop: '1.5rem', width: '100%' }}
      >
        📊 View Raw JSON (Advanced)
      </button>
    </div>
  );
}

export default ResultsDisplay;
