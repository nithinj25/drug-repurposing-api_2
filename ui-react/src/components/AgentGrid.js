import React from 'react';

function AgentGrid({ tasks, agentIcons, onAgentClick }) {
  const formatAgentName = (name) => {
    return name
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const truncateText = (text, maxLength) => {
    let str = text;
    if (typeof text === 'object' && text !== null) {
      // Extract meaningful text from objects
      if (text.summary) str = text.summary;
      else if (text.result) str = text.result;
      else if (text.description) str = text.description;
      else str = JSON.stringify(text, null, 2);
    }
    
    if (str.length > maxLength) {
      return str.substring(0, maxLength) + '...';
    }
    return str;
  };

  const getSummaryFromResult = (result) => {
    if (typeof result === 'string') {
      return result;
    }
    if (typeof result === 'object' && result !== null) {
      if (result.summary) return result.summary;
      if (result.result) return result.result;
      if (result.description) return result.description;
      if (result.findings) return result.findings;
      if (result.analysis) return result.analysis;
      
      // Try to find any text field
      for (let key in result) {
        if (typeof result[key] === 'string' && result[key].length > 20) {
          return result[key];
        }
      }
    }
    return 'Analysis complete';
  };

  return (
    <div className="agents-grid">
      {Object.entries(tasks).map(([taskId, task]) => {
        const agentName = task.agent_name || taskId;
        const icon = agentIcons[agentName] || '🔬';
        const result = task.result;
        const summary = getSummaryFromResult(result);

        return (
          <div key={taskId} className="agent-card">
            <div className="agent-card-icon">{icon}</div>
            <div className="agent-card-name">{formatAgentName(agentName)}</div>
            <div className="agent-card-status">{task.status || 'completed'}</div>
            <div className="agent-card-result">{truncateText(summary, 150)}</div>
            <button
              className="btn btn-secondary"
              onClick={() => onAgentClick({ type: 'agent', agentName, result })}
              style={{ width: '100%', marginTop: '1rem', fontSize: '0.9rem' }}
            >
              View Full Details
            </button>
          </div>
        );
      })}
    </div>
  );
}

export default AgentGrid;
