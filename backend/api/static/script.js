const uploadForm = document.getElementById('upload-form');
const promptForm = document.getElementById('prompt-form');
const clipList = document.getElementById('clip-list');
const uploadStatus = document.getElementById('upload-status');
const renderStatus = document.getElementById('render-status');
const planPreview = document.getElementById('plan-preview');
const downloadButton = document.getElementById('download-button');
const promptText = document.getElementById('prompt-text');

const apiRequest = async (url, options = {}) => {
    const response = await fetch(url, options);
    const contentType = response.headers.get('content-type') || '';
    if (!response.ok) {
        const error = contentType.includes('application/json') ? await response.json() : await response.text();
        throw new Error(error.detail || error.message || JSON.stringify(error));
    }
    return contentType.includes('application/json') ? response.json() : response.text();
};

const refreshStatus = async () => {
    try {
        const data = await apiRequest('/api/status');
        clipList.innerHTML = data.clips.length
            ? data.clips.map((name) => `<span>🎬 ${name}</span>`).join('')
            : '<span>No clips uploaded yet.</span>';
        downloadButton.disabled = !data.output_exists;
        uploadStatus.textContent = `${data.clips.length} uploaded clip(s).`;
        if (data.output_exists) {
            renderStatus.textContent = 'Final output is ready. Click download below.';
        }
    } catch (error) {
        uploadStatus.textContent = `Unable to refresh status: ${error.message}`;
    }
};

uploadForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const filesInput = document.getElementById('clip-upload');
    const files = Array.from(filesInput.files);
    if (!files.length) {
        uploadStatus.textContent = 'Select one or more clips before uploading.';
        return;
    }

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    uploadStatus.textContent = 'Uploading clips...';
    try {
        const result = await apiRequest('/api/upload', {
            method: 'POST',
            body: formData,
        });
        uploadStatus.textContent = result.message || 'Upload successful.';
        filesInput.value = '';
        await refreshStatus();
    } catch (error) {
        uploadStatus.textContent = `Upload failed: ${error.message}`;
    }
});

promptForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const promptValue = promptText.value.trim();
    if (!promptValue) {
        renderStatus.textContent = 'Enter an edit prompt before rendering.';
        return;
    }

    const useResolve = document.getElementById('use-resolve').checked;
    renderStatus.textContent = `Generating edit plan and rendering video${useResolve ? ' with DaVinci Resolve' : ''}… This may take a few minutes.`;
    planPreview.textContent = '';
    downloadButton.disabled = true;

    try {
        const response = await apiRequest('/api/render', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ 
                prompt: promptValue,
                use_resolve: useResolve 
            }),
        });
        renderStatus.textContent = 'Render complete. Download is ready.';
        planPreview.textContent = JSON.stringify(response.plan, null, 2);
        downloadButton.disabled = false;
    } catch (error) {
        renderStatus.textContent = `Render failed: ${error.message}`;
    }
});

downloadButton.addEventListener('click', () => {
    window.location.href = '/api/download/output';
});

refreshStatus();
