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
        const modelProvider = document.getElementById('model-provider').value;
        
        if (!audioFile || !transcriptFile) {
            alert("Please upload both an audio file and a transcript file.");
            return;
        }

        // Show loading state
        inputSec.classList.add('hidden');
        errorSec.classList.add('hidden');
        loadingSec.classList.remove('hidden');

        const formData = new FormData();
        formData.append('audioFile', audioFile);
        formData.append('transcriptFile', transcriptFile);
        formData.append('modelProvider', modelProvider);

        try {
            const response = await fetch('/api/evaluate', {
                method: 'POST',
                body: formData
            });

            const rawData = await response.json();
            
            if (rawData.error) {
                throw new Error(rawData.error);
            }
            
            // Prevent type errors if API didn't parse clean JSON
            const data = (typeof rawData === 'string') ? JSON.parse(rawData) : rawData;

            renderResults(data);
            
            loadingSec.classList.add('hidden');
            resultsSec.classList.remove('hidden');
            
            // Delay ring animation so page transitions firmly
            setTimeout(() => {
                animateScore(parseFloat(data.final_score) || 0);
            }, 300);
            
        } catch (err) {
            console.error(err);
            loadingSec.classList.add('hidden');
            errorSec.classList.remove('hidden');
            document.getElementById('error-message').textContent = err.message || "Failed to process evaluation.";
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

function renderResults(data) {
    const defEmpty = ["No significant notes"];
    
    // Fill text components
    document.getElementById('detailed-analysis-text').textContent = data.detailed_analysis || "No detailed analysis provided.";
    
    // Risk rate component styling
    const riskBadge = document.getElementById('risk-badge');
    const riskVal = String(data.risk_rate || "Unknown");
    riskBadge.textContent = riskVal;
    riskBadge.dataset.risk = riskVal.toLowerCase();
    
    // Score ring logic prep
    document.getElementById('final-score').textContent = "0";
    document.getElementById('score-stroke').setAttribute('stroke-dasharray', `0, 100`);
    
    const scoreVal = parseFloat(data.final_score) || 0;
    const stroke = document.getElementById('score-stroke');
    if (scoreVal >= 90) stroke.style.stroke = "var(--success)";
    else if (scoreVal >= 70) stroke.style.stroke = "var(--warning)";
    else stroke.style.stroke = "var(--danger)";

    // List populations
    populateList('assumptions-list', data.assumptions, defEmpty);
    populateList('missed-info-list', data.missed_information, defEmpty);
    populateList('incorrect-info-list', data.incorrect_information, defEmpty);
    populateList('grammar-error-list', data.punctuation_and_grammar_errors, defEmpty);
    
    // Staggered list item animations
    const items = document.querySelectorAll('.result-item');
    items.forEach((item, index) => {
        item.style.animationDelay = `${0.12 * index}s`;
    });
}

function populateList(elementId, items, defaultIfEmpty) {
    const ul = document.getElementById(elementId);
    ul.innerHTML = '';
    
    // Validate arrays
    const arr = (Array.isArray(items) && items.length > 0) ? items : defaultIfEmpty;
    
    arr.forEach(text => {
        const li = document.createElement('li');
        li.textContent = text;
        ul.appendChild(li);
    });
}

function animateScore(targetScore) {
    const stroke = document.getElementById('score-stroke');
    const display = document.getElementById('final-score');
    
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
