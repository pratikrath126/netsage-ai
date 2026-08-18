document.addEventListener('DOMContentLoaded', () => {
    
    // --- Helper: Toast Notification ---
    function showToast(message, icon = 'ℹ️') {
        const existing = document.querySelector('.toast-msg');
        if (existing) existing.remove();
        
        const toast = document.createElement('div');
        toast.className = 'toast-msg';
        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.5s ease';
            setTimeout(() => toast.remove(), 500);
        }, 3500);
    }

    // --- Dashboard Charts ---
    if (window.dashboardData) {
        const data = window.dashboardData;
        
        // Concept Chart
        const ctxConcept = document.getElementById('conceptChart');
        if (ctxConcept) {
            new Chart(ctxConcept, {
                type: 'bar',
                data: {
                    labels: Object.keys(data.concept_counts),
                    datasets: [{
                        label: 'Cases',
                        data: Object.values(data.concept_counts),
                        backgroundColor: '#2563eb',
                        borderRadius: 6
                    }]
                },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });
        }

        // Severity Chart
        const ctxSeverity = document.getElementById('severityChart');
        if (ctxSeverity) {
            new Chart(ctxSeverity, {
                type: 'pie',
                data: {
                    labels: ['High', 'Medium', 'Low'],
                    datasets: [{
                        data: [
                            data.severity_counts['High'] || 0,
                            data.severity_counts['Medium'] || 0,
                            data.severity_counts['Low'] || 0
                        ],
                        backgroundColor: ['#dc2626', '#d97706', '#16a34a']
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        // Status Chart
        const ctxStatus = document.getElementById('statusChart');
        if (ctxStatus) {
            new Chart(ctxStatus, {
                type: 'doughnut',
                data: {
                    labels: ['Accepted', 'Edited', 'Rejected', 'Pending'],
                    datasets: [{
                        data: [
                            data.review_status_counts['accepted'] || 0,
                            data.review_status_counts['edited'] || 0,
                            data.review_status_counts['rejected'] || 0,
                            data.review_status_counts['pending'] || 0
                        ],
                        backgroundColor: ['#16a34a', '#d97706', '#dc2626', '#cbd5e1']
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }
    }

    // --- Cases Page Filter & Expand ---
    const filterBtns = document.querySelectorAll('.filter-btn');
    const caseRows = document.querySelectorAll('.case-row');

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const filter = btn.getAttribute('data-filter');
            
            caseRows.forEach(row => {
                const concept = row.getAttribute('data-concept');
                const detailRow = row.nextElementSibling;
                
                if (filter === 'all' || filter === concept) {
                    row.style.display = '';
                    if (detailRow && detailRow.classList.contains('case-detail-row')) {
                        detailRow.style.display = 'none';
                    }
                } else {
                    row.style.display = 'none';
                    if (detailRow && detailRow.classList.contains('case-detail-row')) {
                        detailRow.style.display = 'none';
                    }
                }
            });
        });
    });

    caseRows.forEach(row => {
        row.addEventListener('click', () => {
            const detailRow = row.nextElementSibling;
            if (detailRow && detailRow.classList.contains('case-detail-row')) {
                detailRow.style.display = (detailRow.style.display === 'none') ? 'table-row' : 'none';
            }
        });
    });

    // --- Diagnose Page Dropdown ---
    const caseSelect = document.getElementById('caseSelect');
    if (caseSelect) {
        caseSelect.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val) {
                window.location.href = '/diagnose/' + val;
            }
        });
    }

    // --- Live AI Diagnosis Execution ---
    const btnRunDiagnosis = document.getElementById('btnRunDiagnosis');
    if (btnRunDiagnosis) {
        btnRunDiagnosis.addEventListener('click', async () => {
            const caseId = btnRunDiagnosis.getAttribute('data-case');
            const aiResponseContainer = document.getElementById('aiResponseContainer');
            const aiLoadingBox = document.getElementById('aiLoadingBox');
            const liveBadge = document.getElementById('liveBadge');
            const card = document.getElementById('aiDiagnosisCard');

            // 1. Show Loading State
            if (aiResponseContainer) aiResponseContainer.style.display = 'none';
            if (aiLoadingBox) aiLoadingBox.style.display = 'block';
            if (liveBadge) liveBadge.style.display = 'none';
            btnRunDiagnosis.disabled = true;
            btnRunDiagnosis.innerHTML = '<span>⏳ Analyzing with AI...</span>';

            try {
                const response = await fetch('/api/diagnose/' + caseId, {
                    method: 'POST'
                });
                const result = await response.json();

                if (result.error) {
                    alert('AI Error: ' + result.error);
                    if (aiResponseContainer) aiResponseContainer.style.display = 'block';
                    if (aiLoadingBox) aiLoadingBox.style.display = 'none';
                    btnRunDiagnosis.disabled = false;
                    btnRunDiagnosis.innerHTML = '<span>⚡ Run AI Diagnosis</span>';
                    return;
                }

                // 2. Render Formatted Output Dynamically
                const confClass = (result.confidence === 'high') ? 'badge-low' : (result.confidence === 'medium' ? 'badge-medium' : 'badge-high');
                const confTitle = (result.confidence || 'Medium').charAt(0).toUpperCase() + (result.confidence || 'Medium').slice(1);
                
                let fixStepsHtml = '<p class="text-muted">No fix steps provided.</p>';
                if (result.fix_steps && result.fix_steps.length > 0) {
                    fixStepsHtml = '<ol class="fix-steps-list">' + 
                        result.fix_steps.map(s => `<li><code>${s}</code></li>`).join('') + 
                        '</ol>';
                }

                const nextCmdHtml = result.next_command ? 
                    `<code class="command-inline">${result.next_command}</code>` : 
                    `<p class="text-muted">No additional commands needed.</p>`;

                const newHtml = `
                <div class="ai-result pulse-highlight" id="aiResultContent">
                    <div class="ai-field">
                        <h4>🔍 Root Cause</h4>
                        <p id="dispRootCause">${result.root_cause || 'No root cause identified.'}</p>
                    </div>

                    <div class="ai-field-row mt-10">
                        <div class="ai-field-small">
                            <h4>Confidence</h4>
                            <span id="dispConfidence" class="badge ${confClass}">${confTitle}</span>
                        </div>
                        <div class="ai-field-small">
                            <h4>OSI Layer</h4>
                            <span id="dispOsiLayer" class="badge badge-concept">${result.osi_layer || 'Unknown'}</span>
                        </div>
                    </div>

                    <div class="ai-field mt-10">
                        <h4>📋 Evidence</h4>
                        <p id="dispEvidence" class="evidence-text">${result.evidence || 'N/A'}</p>
                    </div>

                    <div class="ai-field mt-10">
                        <h4>▶ Next Command to Run</h4>
                        <div id="dispNextCommand">${nextCmdHtml}</div>
                    </div>

                    <div class="ai-field mt-10">
                        <h4>🔧 Fix Steps</h4>
                        <div id="dispFixSteps">${fixStepsHtml}</div>
                    </div>
                </div>
                `;

                if (aiResponseContainer) {
                    aiResponseContainer.innerHTML = newHtml;
                    aiResponseContainer.style.display = 'block';
                }
                if (aiLoadingBox) aiLoadingBox.style.display = 'none';

                // 3. Update Comparison Card
                const compRootCause = document.getElementById('aiRootCause');
                const compOsiLayer = document.getElementById('aiOsiLayer');
                if (compRootCause) compRootCause.innerText = result.root_cause || 'N/A';
                if (compOsiLayer) compOsiLayer.innerText = result.osi_layer || 'N/A';

                // 4. Show Live Badge & Toast Notification
                if (liveBadge) {
                    const now = new Date().toLocaleTimeString();
                    liveBadge.innerText = `✨ Diagnosed at ${now}`;
                    liveBadge.style.display = 'inline-block';
                }
                if (card) {
                    card.classList.remove('pulse-highlight');
                    void card.offsetWidth; // trigger reflow
                    card.classList.add('pulse-highlight');
                }

                showToast('AI Diagnosis updated successfully!', '🤖');

            } catch (err) {
                alert('Error running diagnosis: ' + err.message);
                if (aiResponseContainer) aiResponseContainer.style.display = 'block';
                if (aiLoadingBox) aiLoadingBox.style.display = 'none';
            } finally {
                btnRunDiagnosis.disabled = false;
                btnRunDiagnosis.innerHTML = '<span>⚡ Re-run AI Diagnosis</span>';
            }
        });
    }

});

// --- Review Page Functions ---
function toggleEdit(caseId) {
    const form = document.getElementById('edit-form-' + caseId);
    if (form) {
        form.style.display = (form.style.display === 'none' || form.style.display === '') ? 'block' : 'none';
    }
}

async function submitReview(caseId, status) {
    const payload = { status: status };
    
    if (status === 'edited') {
        const notesEl = document.getElementById('notes-' + caseId);
        const corrEl = document.getElementById('corrected-' + caseId);
        payload.reviewer_notes = notesEl ? notesEl.value : '';
        payload.corrected_diagnosis = corrEl ? corrEl.value : '';
    }

    try {
        const response = await fetch('/api/review/' + caseId, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            // Update the card UI in place
            const card = document.getElementById('review-card-' + caseId);
            if (card) {
                const statusBadge = card.querySelector('.badge-status');
                if (statusBadge) {
                    statusBadge.className = `badge badge-status badge-${status}`;
                    statusBadge.innerText = status.charAt(0).toUpperCase() + status.slice(1);
                }
                const editForm = document.getElementById('edit-form-' + caseId);
                if (editForm && status === 'edited') {
                    editForm.style.display = 'none';
                }
                card.classList.remove('pulse-highlight');
                void card.offsetWidth;
                card.classList.add('pulse-highlight');
            }

            const icon = (status === 'accepted') ? '✅' : (status === 'rejected' ? '❌' : '✏️');
            
            // Show toast
            const existing = document.querySelector('.toast-msg');
            if (existing) existing.remove();
            const toast = document.createElement('div');
            toast.className = 'toast-msg';
            toast.innerHTML = `<span>${icon}</span> <span>Case ${caseId} marked as <strong>${status.toUpperCase()}</strong></span>`;
            document.body.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.5s ease';
                setTimeout(() => toast.remove(), 500);
            }, 3000);

        } else {
            alert('Failed to submit review');
        }
    } catch (err) {
        alert('Error submitting review: ' + err.message);
    }
}
