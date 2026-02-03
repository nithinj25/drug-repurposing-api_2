// ============================================
// DRUG REPURPOSING ASSISTANT - SCRIPT
// ============================================

class DrugRepurposingUI {
    constructor() {
        this.apiUrl = document.getElementById('apiUrl').value;
        this.jobId = null;
        this.pollInterval = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadSavedApiUrl();
    }

    setupEventListeners() {
        document.getElementById('analysisForm').addEventListener('submit', (e) => this.handleSubmit(e));
        document.getElementById('apiUrl').addEventListener('change', (e) => this.saveApiUrl(e.target.value));
        
        const closeBtn = document.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeModal());
        }

        document.getElementById('detailsModal').addEventListener('click', (e) => {
            if (e.target.id === 'detailsModal') {
                this.closeModal();
            }
        });
    }

    loadSavedApiUrl() {
        const saved = localStorage.getItem('apiUrl');
        if (saved) {
            document.getElementById('apiUrl').value = saved;
            this.apiUrl = saved;
        }
    }

    saveApiUrl(url) {
        localStorage.setItem('apiUrl', url);
        this.apiUrl = url;
    }

    async handleSubmit(e) {
        e.preventDefault();

        const drugName = document.getElementById('drugName').value.trim();
        const indication = document.getElementById('indication').value.trim();
        const query = document.getElementById('query').value.trim();

        if (!drugName || !indication) {
            this.showStatus('Please fill in all required fields', 'error');
            return;
        }

        await this.submitAnalysis(drugName, indication, query);
    }

    async submitAnalysis(drugName, indication, query) {
        const submitBtn = document.getElementById('analyzeBtn');
        const btnText = submitBtn.querySelector('.btn-text');
        const btnSpinner = submitBtn.querySelector('.btn-spinner');

        submitBtn.disabled = true;
        btnText.style.display = 'none';
        btnSpinner.style.display = 'inline-block';

        try {
            // Submit analysis
            this.showLoading(true);
            const payload = {
                drug_name: drugName,
                indication: indication,
                ...(query && { query: query })
            };

            const response = await fetch(`${this.apiUrl}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to submit analysis');
            }

            const data = await response.json();
            this.jobId = data.job_id;

            this.showStatus(`Analysis submitted! Job ID: ${this.jobId}`, 'info');
            this.pollForResults();

        } catch (error) {
            console.error('Error:', error);
            this.showStatus(`Error: ${error.message}`, 'error');
            this.showLoading(false);
        } finally {
            submitBtn.disabled = false;
            btnText.style.display = 'inline-flex';
            btnSpinner.style.display = 'none';
        }
    }

    pollForResults() {
        let pollCount = 0;
        const maxPolls = 120; // 2 minutes with 1-second intervals

        this.pollInterval = setInterval(async () => {
            pollCount++;

            try {
                const response = await fetch(`${this.apiUrl}/jobs/${this.jobId}`);
                if (!response.ok) {
                    throw new Error('Failed to fetch job status');
                }

                const data = await response.json();

                if (data.status === 'completed') {
                    clearInterval(this.pollInterval);
                    this.showLoading(false);
                    this.displayResults(data);
                    this.showStatus('Analysis complete!', 'success');
                } else if (data.status === 'failed') {
                    clearInterval(this.pollInterval);
                    this.showLoading(false);
                    this.showStatus(`Analysis failed: ${data.error || 'Unknown error'}`, 'error');
                }
            } catch (error) {
                console.error('Poll error:', error);
                if (pollCount >= maxPolls) {
                    clearInterval(this.pollInterval);
                    this.showLoading(false);
                    this.showStatus('Analysis timeout - please check job status later', 'error');
                }
            }
        }, 1000);
    }

    displayResults(data) {
        const container = document.getElementById('resultsContainer');
        container.innerHTML = '';

        // Job Summary Card
        const summaryCard = this.createResultCard(
            `${data.drug_name} - ${data.indication}`,
            [
                { label: 'Job ID', value: data.job_id },
                { label: 'Status', value: `<span class="badge badge-success">${data.status}</span>` },
                { label: 'Query', value: data.query || 'N/A' }
            ]
        );
        container.appendChild(summaryCard);

        // Agents Results Grid
        if (data.tasks) {
            const agentsSection = document.createElement('div');
            agentsSection.className = 'result-card';
            agentsSection.innerHTML = '<h3 style="margin-bottom: 1.5rem;">Agent Analysis</h3>';

            const agentsGrid = document.createElement('div');
            agentsGrid.className = 'agents-grid';

            const agentIcons = {
                'literature_agent': '📚',
                'clinical_agent': '🏥',
                'safety_agent': '⚠️',
                'molecular_agent': '🧬',
                'patent_agent': '📋',
                'market_agent': '💼'
            };

            for (const [taskId, task] of Object.entries(data.tasks)) {
                const agentName = task.agent_name || taskId;
                const icon = agentIcons[agentName] || '🔬';
                const result = typeof task.result === 'string' ? task.result : JSON.stringify(task.result, null, 2);

                const agentCard = document.createElement('div');
                agentCard.className = 'agent-card';
                agentCard.innerHTML = `
                    <div class="agent-card-icon">${icon}</div>
                    <div class="agent-card-name">${this.formatAgentName(agentName)}</div>
                    <div class="agent-card-status">${task.status || 'completed'}</div>
                    <div class="agent-card-result">${this.truncateText(result, 150)}</div>
                    <button class="btn btn-secondary" style="width: 100%; margin-top: 1rem;" 
                            onclick="drugsUI.showAgentDetails('${agentName}', '${btoa(result)}')">
                        View Details
                    </button>
                `;
                agentsGrid.appendChild(agentCard);
            }

            agentsSection.appendChild(agentsGrid);
            container.appendChild(agentsSection);
        }

        // Reasoning Section
        if (data.reasoning_result) {
            const reasoningBox = this.createReasoningBox(data.reasoning_result);
            container.appendChild(reasoningBox);
        }

        // Raw JSON Button
        const rawButton = document.createElement('button');
        rawButton.className = 'btn btn-secondary';
        rawButton.style.marginTop = '1.5rem';
        rawButton.innerHTML = '📊 View Raw JSON Response';
        rawButton.onclick = () => this.showRawJSON(data);
        container.appendChild(rawButton);
    }

    createResultCard(title, metaItems) {
        const card = document.createElement('div');
        card.className = 'result-card';

        let metaHtml = '<div class="result-card-meta">';
        metaItems.forEach(item => {
            metaHtml += `<div class="meta-item"><strong>${item.label}:</strong> <span>${item.value}</span></div>`;
        });
        metaHtml += '</div>';

        card.innerHTML = `
            <div class="result-card-header">
                <div class="result-card-title">${title}</div>
            </div>
            ${metaHtml}
        `;

        return card;
    }

    createReasoningBox(reasoningResult) {
        const box = document.createElement('div');
        box.className = 'reasoning-box result-card';

        let reasoningHtml = '<div class="reasoning-title">🧠 AI Reasoning Analysis</div><div class="reasoning-content">';

        // Hypotheses
        if (reasoningResult.hypotheses && reasoningResult.hypotheses.length > 0) {
            reasoningHtml += '<h4 style="margin-top: 1rem; margin-bottom: 0.5rem;">Hypotheses:</h4><ul style="margin-left: 1.5rem;">';
            reasoningResult.hypotheses.slice(0, 3).forEach(h => {
                reasoningHtml += `<li>${this.escapeHtml(h)}</li>`;
            });
            if (reasoningResult.hypotheses.length > 3) {
                reasoningHtml += `<li><em>+${reasoningResult.hypotheses.length - 3} more hypotheses</em></li>`;
            }
            reasoningHtml += '</ul>';
        }

        // Dimension Scores
        if (reasoningResult.dimension_scores) {
            reasoningHtml += '<div class="dimensions-grid" style="margin-top: 1rem;">';
            for (const [dim, score] of Object.entries(reasoningResult.dimension_scores)) {
                reasoningHtml += `
                    <div class="dimension-item">
                        <div class="dimension-label">${this.formatDimensionName(dim)}</div>
                        <div class="dimension-score">${(score * 100).toFixed(0)}%</div>
                    </div>
                `;
            }
            reasoningHtml += '</div>';
        }

        // Summary stats
        if (reasoningResult.processing_time_ms) {
            reasoningHtml += `<div style="margin-top: 1rem; font-size: 0.9rem; color: var(--text-light);">Processing time: ${reasoningResult.processing_time_ms}ms</div>`;
        }

        reasoningHtml += '</div>';
        box.innerHTML = reasoningHtml;
        return box;
    }

    showAgentDetails(agentName, encodedResult) {
        const result = atob(encodedResult);
        const modal = document.getElementById('detailsModal');
        document.getElementById('modalTitle').textContent = `${this.formatAgentName(agentName)} - Full Details`;
        document.getElementById('modalBody').innerHTML = `<pre style="background: #f1f5f9; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: 0.85rem;">${this.escapeHtml(result)}</pre>`;
        modal.style.display = 'flex';
    }

    showRawJSON(data) {
        const modal = document.getElementById('detailsModal');
        document.getElementById('modalTitle').textContent = 'Raw JSON Response';
        const json = JSON.stringify(data, null, 2);
        document.getElementById('modalBody').innerHTML = `<pre style="background: #f1f5f9; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: 0.85rem; max-height: 500px; overflow-y: auto;">${this.escapeHtml(json)}</pre>`;
        modal.style.display = 'flex';
    }

    closeModal() {
        document.getElementById('detailsModal').style.display = 'none';
    }

    showLoading(show) {
        const skeleton = document.getElementById('loadingSkeleton');
        const container = document.getElementById('resultsContainer');
        
        if (show) {
            container.style.display = 'none';
            skeleton.style.display = 'block';
        } else {
            skeleton.style.display = 'none';
            container.style.display = 'flex';
        }
    }

    showStatus(message, type) {
        const statusEl = document.getElementById('statusMessage');
        statusEl.textContent = message;
        statusEl.className = `status-message ${type}`;
        statusEl.style.display = 'block';

        if (type === 'success') {
            setTimeout(() => {
                statusEl.style.display = 'none';
            }, 5000);
        }
    }

    formatAgentName(name) {
        return name
            .replace(/_/g, ' ')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    formatDimensionName(dim) {
        return this.formatAgentName(dim);
    }

    truncateText(text, maxLength) {
        if (text.length > maxLength) {
            return this.escapeHtml(text.substring(0, maxLength)) + '...';
        }
        return this.escapeHtml(text);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize on page load
let drugsUI;
document.addEventListener('DOMContentLoaded', () => {
    drugsUI = new DrugRepurposingUI();
});
