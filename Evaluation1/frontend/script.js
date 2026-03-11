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

    // Theme Toggle
    document.getElementById('theme-toggle').addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        const icon = document.querySelector('.theme-icon');
        icon.textContent = document.body.classList.contains('light-theme') ? '🌙' : '🔆';
    });

    // PDF Download
    document.getElementById('download-pdf-btn').addEventListener('click', () => window.print());

    // Transcript Download text
    document.getElementById('download-transcript-btn').addEventListener('click', () => {
        if(!window.currentTranscript || window.currentTranscript.length === 0) {
            return alert('No corrected transcript to download.');
        }
        let txt = "EvalAI Corrected Medical Transcript\n=================================\n\n";
        window.currentTranscript.forEach(t => {
            txt += `[${t.timestamp}] ${t.speaker}: ${t.text}\n`;
        });
        const blob = new Blob([txt], { type: 'text/plain' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `corrected_transcript_${Date.now()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    });

    let activeAudioFile = null;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const audioFile = document.getElementById('audio-input').files[0];
        activeAudioFile = audioFile;
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
            
            // Set up Audio player
            const audioUrl = URL.createObjectURL(activeAudioFile);
            document.getElementById('main-audio-player').src = audioUrl;

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

    // Chat Handler
    document.getElementById('chat-send-btn').addEventListener('click', async () => {
        const input = document.getElementById('chat-input');
        const q = input.value.trim();
        if(!q) return;

        const log = document.getElementById('chat-log');
        log.innerHTML += `<div class="chat-msg user-msg">${q}</div>`;
        input.value = "";
        log.scrollTop = log.scrollHeight;

        const formData = new FormData();
        formData.append('audioFile', activeAudioFile);
        formData.append('question', q);
        formData.append('modelProvider', document.getElementById('model-provider').value);

        try {
            log.innerHTML += `<div class="chat-msg bot-msg" id="chat-typing">Typing...</div>`;
            log.scrollTop = log.scrollHeight;
            const res = await fetch('/api/chat', { method: 'POST', body: formData });
            const j = await res.json();
            document.getElementById('chat-typing').remove();
            
            if(j.error) throw new Error(j.error);
            log.innerHTML += `<div class="chat-msg bot-msg">${j.chat_response}</div>`;
            log.scrollTop = log.scrollHeight;
        } catch(e) {
            document.getElementById('chat-typing')?.remove();
            log.innerHTML += `<div class="chat-msg bot-msg" style="color:red">Error: ${e.message}</div>`;
        }
    });

    // Snippet Translator Handler
    document.getElementById('snip-translate-btn').addEventListener('click', async () => {
        const start = document.getElementById('snip-start').value;
        const end = document.getElementById('snip-end').value;
        const out = document.getElementById('snip-output');
        
        if(!start || !end) return alert('Enter start and end times');
        
        out.classList.remove('hidden');
        out.textContent = "Translating...";
        
        const formData = new FormData();
        formData.append('audioFile', activeAudioFile);
        formData.append('startTime', start);
        formData.append('endTime', end);
        formData.append('modelProvider', document.getElementById('model-provider').value);

        try {
            const res = await fetch('/api/translate_snippet', { method: 'POST', body: formData });
            const j = await res.json();
            if(j.error) throw new Error(j.error);
            out.textContent = j.snippet_translation;
        } catch(e) {
            out.textContent = "Error: " + e.message;
        }
    });

    // Transcript Tabs Toggle
    document.getElementById('view-timeline-btn').addEventListener('click', (e) => {
        e.target.classList.add('active');
        document.getElementById('view-paragraph-btn').classList.remove('active');
        document.getElementById('transcript-content-container').classList.remove('paragraph-view');
        renderTranscriptView();
    });
    document.getElementById('view-paragraph-btn').addEventListener('click', (e) => {
        e.target.classList.add('active');
        document.getElementById('view-timeline-btn').classList.remove('active');
        document.getElementById('transcript-content-container').classList.add('paragraph-view');
        renderTranscriptView();
    });

    // NLP Insights toggle
    document.getElementById('nlp-insights-btn').addEventListener('click', () => {
        const box = document.getElementById('nlp-insights-box');
        box.classList.toggle('hidden');
        if(!box.classList.contains('hidden')) {
            const lang = document.getElementById('meta-lang').textContent || 'Unknown';
            document.getElementById('nlp-insights-text').textContent = `In ${lang}, evaluating ASR is complex because typical Word Error Rate (WER) doesn't apply cleanly to translation matrixes. Often, phonetic similarities or cultural idioms result in vastly different English structural sentences despite retaining 100% semantic clinical accuracy. The Hallucination score specifically filters for clinically dangerous insertions.`;
        }
    });

    // Show Corrected toggle
    document.getElementById('show-corrected-toggle').addEventListener('change', renderTranscriptView);
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
    
    // Meta Data Fill
    const audioMeta = data.audio_metadata || {};
    const dgMeta = data.deepgram_metadata || {};
    
    document.getElementById('meta-lang').textContent = audioMeta.primary_language_spoken || "-";
    document.getElementById('meta-speakers').textContent = audioMeta.number_of_speakers || dgMeta.deepgram_speakers || "-";
    document.getElementById('meta-genders').textContent = audioMeta.speaker_genders || "-";
    document.getElementById('meta-quality').textContent = audioMeta.audio_quality || "-";
    
    // Deepgram specifics
    document.getElementById('meta-duration').textContent = dgMeta.duration !== "N/A" && dgMeta.duration ? `${dgMeta.duration}s` : "Unknown";
    document.getElementById('meta-confidence').textContent = dgMeta.avg_confidence !== "N/A" && dgMeta.avg_confidence ? `${dgMeta.avg_confidence}%` : "Unknown";
    
    // Metrics Fill
    const metrics = data.metrics || {};
    
    document.getElementById('metric-semantic').textContent = `${metrics.semantic_accuracy_score || 0}%`;
    document.getElementById('metric-entity').textContent = `${metrics.entity_preservation_score || 0}%`;
    document.getElementById('metric-hallucination').textContent = `${metrics.hallucination_severity_score || 0}%`;
    document.getElementById('metric-fluency').textContent = `${metrics.translation_fluency_score || 0}%`;
    
    // Risk rate component styling
    const riskBadge = document.getElementById('risk-badge');
    const riskVal = String(data.risk_rate || "Unknown");
    riskBadge.textContent = riskVal;
    riskBadge.dataset.risk = riskVal.toLowerCase();

    // Diarization Insights
    if(data.diarization_insights) {
        document.getElementById('diarize-badge').textContent = data.diarization_insights.accuracy || 'Unknown';
        document.getElementById('diarize-insight').textContent = data.diarization_insights.insight || 'No insight provided';
    }

    // Medical Errors Specifics
    const medicalCtn = document.getElementById('medical-errors-list');
    medicalCtn.innerHTML = '';
    if (data.medical_errors && data.medical_errors.length > 0) {
        data.medical_errors.forEach(err => {
            medicalCtn.innerHTML += `<li><strong>[${err.error_type.toUpperCase()}]</strong> ${err.description}</li>`;
        });
    } else {
        medicalCtn.innerHTML = '<li>No critical medical errors detected.</li>';
    }

    // Named Entity Recognition (NER)
    window.currentNERData = data.named_entities || [];
    const nerContainer = document.getElementById('ner-bubble-container');
    nerContainer.innerHTML = '';
    document.getElementById('ner-count').textContent = `${window.currentNERData.length} Entities`;
    
    window.currentNERData.forEach(ner => {
        let cls = 'ner-pill-default';
        if(ner.type.toLowerCase().includes('med')) cls = 'ner-pill-medication';
        if(ner.type.toLowerCase().includes('diag')) cls = 'ner-pill-diagnosis';
        if(ner.type.toLowerCase().includes('symp')) cls = 'ner-pill-symptom';
        
        nerContainer.innerHTML += `<div class="ner-bubble ${cls}" title="${ner.status.toUpperCase()} usage">${ner.word}</div>`;
    });

    // Expand NER Detail
    document.getElementById('expand-ner-btn').onclick = () => {
        const detbox = document.getElementById('ner-detailed-view');
        detbox.classList.toggle('hidden');
        if(!detbox.classList.contains('hidden')) {
            detbox.innerHTML = '';
            window.currentNERData.forEach(ner => {
                const isErr = ner.status === 'incorrect';
                detbox.innerHTML += `
                    <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; border-left: 3px solid ${isErr ? 'var(--danger)' : 'var(--success)'}">
                        <div style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--accent-secondary);">${ner.timestamp}</div>
                        <div style="font-weight: bold; margin: 0.3rem 0;"><span style="color: var(--text-secondary)">Entity:</span> ${ner.word} <span style="font-size: 0.8rem; padding: 0.1rem 0.4rem; background: var(--bg-surface); border-radius: 4px;">${ner.type}</span></div>
                        <div style="font-style: italic; color: var(--text-secondary); font-size: 0.9rem;">"${ner.context_sentence}"</div>
                        ${isErr ? `<div style="color: #ef4444; font-weight: bold; margin-top: 0.5rem;">Suggested Correction: ${ner.correction}</div>` : ''}
                    </div>
                `;
            });
        }
    };

    // Stashing Transcripts for renderer
    window.currentTranscript = data.corrected_transcript || [];
    renderTranscriptView();
    
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

function renderTranscriptView() {
    const ctn = document.getElementById('transcript-content-container');
    if(!ctn || !window.currentTranscript) return;
    
    const showHighlight = document.getElementById('show-corrected-toggle').checked;
    const isParagraph = ctn.classList.contains('paragraph-view');
    ctn.innerHTML = '';

    if(isParagraph) {
        let pText = "";
        window.currentTranscript.forEach(t => {
            const css = (showHighlight && t.is_changed) ? 'class="highlight-diff"' : '';
            // Just assigning color based on speaker randomly for beauty
            const cColor = t.speaker.includes('1') ? 'var(--accent-primary)' : 'var(--accent-secondary)';
            pText += `<span style="color: ${cColor}; font-weight: bold;">[${t.speaker}]</span> <span ${css}>${t.text}</span> `;
        });
        ctn.innerHTML = `<p>${pText}</p>`;
    } else {
        window.currentTranscript.forEach(t => {
            const hClass = (showHighlight && t.is_changed) ? 't-changed' : '';
            ctn.innerHTML += `
               <div class="t-line ${hClass}">
                   <div class="t-time">${t.timestamp}</div>
                   <div>
                       <div class="t-speaker">${t.speaker}</div>
                       <div class="t-text">${t.text}</div>
                   </div>
               </div>
            `;
        });
    }
}

function resetApp() {
    document.getElementById('results-section').classList.add('hidden');
    document.getElementById('error-section').classList.add('hidden');
    document.getElementById('loading-section').classList.add('hidden');
    document.getElementById('input-section').classList.remove('hidden');
}
