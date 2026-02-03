import React from 'react';

function ReasoningBox({ reasoning }) {
  const formatDimensionName = (dim) => {
    return dim
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="reasoning-box result-card">
      <div className="reasoning-title">🧠 AI Reasoning Analysis</div>
      <div className="reasoning-content">
        {/* Hypotheses */}
        {reasoning.hypotheses && Array.isArray(reasoning.hypotheses) && reasoning.hypotheses.length > 0 && (
          <div>
            <h4 style={{ marginTop: '1rem', marginBottom: '0.5rem' }}>Hypotheses:</h4>
            <ul style={{ marginLeft: '1.5rem' }}>
              {reasoning.hypotheses.slice(0, 3).map((h, idx) => {
                // Handle both string and object hypotheses
                const hypothesisText = typeof h === 'string' ? h : (h.explanation || JSON.stringify(h));
                return <li key={idx}>{hypothesisText}</li>;
              })}
              {reasoning.hypotheses.length > 3 && (
                <li><em>+{reasoning.hypotheses.length - 3} more hypotheses</em></li>
              )}
            </ul>
          </div>
        )}

        {/* Dimension Scores */}
        {reasoning.dimension_scores && typeof reasoning.dimension_scores === 'object' && (
          <div className="dimensions-grid" style={{ marginTop: '1rem' }}>
            {Object.entries(reasoning.dimension_scores).map(([dim, score]) => {
              // Handle both numeric and object scores
              const scoreValue = typeof score === 'number' ? score : (score.score || 0);
              return (
                <div key={dim} className="dimension-item">
                  <div className="dimension-label">{formatDimensionName(dim)}</div>
                  <div className="dimension-score">{(scoreValue * 100).toFixed(0)}%</div>
                </div>
              );
            })}
          </div>
        )}

        {/* Processing Time */}
        {reasoning.processing_time_ms && (
          <div style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#64748b' }}>
            Processing time: {reasoning.processing_time_ms}ms
          </div>
        )}
      </div>
    </div>
  );
}

export default ReasoningBox;
