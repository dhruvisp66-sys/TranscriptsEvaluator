document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('evaluation-form');
    const inputSec = document.getElementById('input-section');
    const loadingSec = document.getElementById('loading-section');
    const resultsSec = document.getElementById('results-section');
    const errorSec = document.getElementById('error-section');
    
    // File drop zones init
    setupDropZone('audio');
    setupDropZone('transcript');

    // Reset UI bindings
    document.getElementById('reset-btn').addEventListener('click', resetApp);
    document.getElementById('error-reset-btn').addEventListener('click', resetApp);

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const audioFile = document.getElementById('audio-input').files[0];
        const transcriptFile = document.getElementById('transcript-input').files[0];
        
        if (!audioFile || !transcriptFile) {
            alert("Please upload both an audio file and a transcript file.");
            return;
        }

        inputSec.classList.add('hidden');
        errorSec.classList.add('hidden');
        loadingSec.classList.remove('hidden');

        const formData = new FormData();
        formData.append('audioFile', audioFile);
        formData.append('transcriptFile', transcriptFile);

        try {
            const response = await fetch('/api/evaluate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (data.error) {
                // If the entire orchestrator failed early
                throw new Error(data.error);
            }
            
            renderDualResults(data);
            
            loadingSec.classList.add('hidden');
            resultsSec.classList.remove('hidden');
            
            // Render circle immediately as it handles duration via js loop
            setTimeout(() => {
                const metaScore = data.meta && data.meta.consensus_score ? parseFloat(data.meta.consensus_score) : 0;
                animateScore(metaScore);
            }, 300);
            
        } catch (err) {
            console.error(err);
            loadingSec.classList.add('hidden');
            errorSec.classList.remove('hidden');
            document.getElementById('error-message').textContent = err.message || "Failed to process evaluation. Make sure API keys are valid.";
        }
    });
});

function setupDropZone(type) {
    const zone = document.getElementById(`drop-zone-${type}`);
    const input = document.getElementById(`${type}-input`);
    const display = document.getElementById(`${type}-filename`);

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.add('drag-over'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.remove('drag-over'), false);
    });

    zone.addEventListener('drop', (e) => {
        let dt = e.dataTransfer;
        let files = dt.files;
        if(files.length > 0) {
            input.files = files;
            updateFileDisplay();
        }
    }, false);

    input.addEventListener('change', updateFileDisplay);

    function updateFileDisplay() {
        if(input.files.length > 0) {
            zone.classList.add('has-file');
            display.textContent = input.files[0].name;
        } else {
            zone.classList.remove('has-file');
            display.textContent = '';
        }
    }
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function renderDualResults(data) {
    const defEmpty = ["None reported"];
    
    const gemini = data.gemini || {};
    const openai = data.openai || {};
    const meta = data.meta || {};

    // 1. Meta judge logic
    document.getElementById('meta-verdict-text').textContent = meta.error || meta.final_verdict || "Meta synthesis failed.";
    populateList('agreements-list', meta.agreements, defEmpty);
    populateList('discrepancies-list', meta.discrepancies, defEmpty);

    // 2. Individual Reports - Gemini
    document.getElementById('gemini-score').textContent = gemini.final_score || "Error";
    const gRisk = document.getElementById('gemini-risk');
    gRisk.textContent = gemini.risk_rate || "N/A";
    gRisk.dataset.risk = (gemini.risk_rate || "").toLowerCase();
    document.getElementById('gemini-analysis').textContent = gemini.detailed_analysis || gemini.error || "No response";
    populateList('gemini-missed', gemini.missed_information, defEmpty);
    populateList('gemini-incorrect', gemini.incorrect_information, defEmpty);

    // 3. Individual Reports - OpenAI
    document.getElementById('openai-score').textContent = openai.final_score || "Error";
    const oRisk = document.getElementById('openai-risk');
    oRisk.textContent = openai.risk_rate || "N/A";
    oRisk.dataset.risk = (openai.risk_rate || "").toLowerCase();
    document.getElementById('openai-analysis').textContent = openai.detailed_analysis || openai.error || "No response";
    populateList('openai-missed', openai.missed_information, defEmpty);
    populateList('openai-incorrect', openai.incorrect_information, defEmpty);

    // Score ring color based on Consensus
    const scoreVal = parseFloat(meta.consensus_score) || 0;
    const stroke = document.getElementById('score-stroke');
    if (scoreVal >= 90) stroke.style.stroke = "var(--success)";
    else if (scoreVal >= 70) stroke.style.stroke = "var(--warning)";
    else stroke.style.stroke = "var(--danger)";

    // Staggered list animations for cards
    const items = document.querySelectorAll('.result-item');
    items.forEach((item, index) => {
        item.style.animationDelay = `${0.12 * index}s`;
    });
}

function populateList(elementId, items, defaultIfEmpty) {
    const ul = document.getElementById(elementId);
    if (!ul) return;
    ul.innerHTML = '';
    
    // Check array type securely
    const arr = (Array.isArray(items) && items.length > 0) ? items : defaultIfEmpty;
    
    arr.forEach(text => {
        const li = document.createElement('li');
        li.textContent = text;
        ul.appendChild(li);
    });
}

function animateScore(targetScore) {
    const stroke = document.getElementById('score-stroke');
    const display = document.getElementById('consensus-score');
    
    stroke.setAttribute('stroke-dasharray', `${targetScore}, 100`);
    
    let currentScore = 0;
    const duration = 1500;
    const interval = 20; 
    const steps = duration / interval;
    const increment = targetScore / steps;
    
    const counter = setInterval(() => {
        currentScore += increment;
        if (currentScore >= targetScore) {
            currentScore = targetScore;
            clearInterval(counter);
        }
        display.textContent = Math.round(currentScore);
    }, interval);
}

function resetApp() {
    document.getElementById('results-section').classList.add('hidden');
    document.getElementById('error-section').classList.add('hidden');
    document.getElementById('loading-section').classList.add('hidden');
    document.getElementById('input-section').classList.remove('hidden');
}
