const uploadForm = document.getElementById('upload-form');
const promptForm = document.getElementById('prompt-form');
const clipList = document.getElementById('clip-list');
const uploadStatus = document.getElementById('upload-status');
const renderStatus = document.getElementById('render-status');
const planPreview = document.getElementById('plan-preview');
const downloadButton = document.getElementById('download-button');
const promptText = document.getElementById('prompt-text');

// Auth elements
const authModal = document.getElementById('auth-modal');
const authForm = document.getElementById('auth-form');
const modalTitle = document.getElementById('modal-title');
const modalClose = document.getElementById('modal-close');
const authError = document.getElementById('auth-error');
const authUsername = document.getElementById('auth-username');
const authPassword = document.getElementById('auth-password');
const authSubmitBtn = document.getElementById('auth-submit-btn');
const switchPrompt = document.getElementById('switch-prompt');
const switchLink = document.getElementById('switch-link');
const btnOpenLogin = document.getElementById('btn-open-login');
const btnOpenRegister = document.getElementById('btn-open-register');
const btnLogout = document.getElementById('btn-logout');
const authLoggedOut = document.getElementById('auth-logged-out');
const authLoggedIn = document.getElementById('auth-logged-in');
const usernameDisplay = document.getElementById('username-display');

let isRegisterMode = false;
let currentUser = null;

const apiRequest = async (url, options = {}) => {
    // Ensure cookies are included with requests
    options.credentials = 'same-origin';
    const response = await fetch(url, options);
    const contentType = response.headers.get('content-type') || '';

    if (response.status === 401) {
        currentUser = null;
        updateAuthUI(null);
        openAuthModal(false, 'Please sign in to perform this action.');
        throw new Error('Authentication required (401).');
    }

    if (!response.ok) {
        const error = contentType.includes('application/json') ? await response.json() : await response.text();
        throw new Error(error.detail || error.message || JSON.stringify(error));
    }
    return contentType.includes('application/json') ? response.json() : response.text();
};

const updateAuthUI = (user) => {
    currentUser = user;
    if (user && user.username) {
        authLoggedOut.style.display = 'none';
        authLoggedIn.style.display = 'flex';
        usernameDisplay.textContent = user.username;
    } else {
        authLoggedOut.style.display = 'flex';
        authLoggedIn.style.display = 'none';
        usernameDisplay.textContent = 'User';
    }
};

const checkAuth = async () => {
    try {
        const data = await apiRequest('/api/auth/me');
        if (data.authenticated && data.user) {
            updateAuthUI(data.user);
        } else {
            updateAuthUI(null);
        }
    } catch (err) {
        updateAuthUI(null);
    }
};

const openAuthModal = (registerMode = false, errorMsg = '') => {
    isRegisterMode = registerMode;
    authModal.style.display = 'flex';
    authUsername.value = '';
    authPassword.value = '';
    authError.style.display = errorMsg ? 'block' : 'none';
    authError.textContent = errorMsg;

    if (isRegisterMode) {
        modalTitle.textContent = 'Create Account';
        authSubmitBtn.textContent = 'Register';
        switchPrompt.textContent = 'Already have an account?';
        switchLink.textContent = 'Sign In';
    } else {
        modalTitle.textContent = 'Sign In';
        authSubmitBtn.textContent = 'Sign In';
        switchPrompt.textContent = "Don't have an account?";
        switchLink.textContent = 'Create one';
    }
    authUsername.focus();
};

const closeAuthModal = () => {
    authModal.style.display = 'none';
    authError.style.display = 'none';
};

switchLink.addEventListener('click', (e) => {
    e.preventDefault();
    openAuthModal(!isRegisterMode);
});

btnOpenLogin.addEventListener('click', () => openAuthModal(false));
btnOpenRegister.addEventListener('click', () => openAuthModal(true));
modalClose.addEventListener('click', closeAuthModal);

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = authUsername.value.trim();
    const password = authPassword.value;
    if (!username || !password) return;

    authError.style.display = 'none';
    const endpoint = isRegisterMode ? '/api/auth/register' : '/api/auth/login';

    try {
        const res = await apiRequest(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        updateAuthUI(res.user);
        closeAuthModal();
        await refreshStatus();
    } catch (err) {
        authError.textContent = err.message;
        authError.style.display = 'block';
    }
});

btnLogout.addEventListener('click', async () => {
    try {
        await apiRequest('/api/auth/logout', { method: 'POST' });
    } catch (e) {
        // ignore
    }
    updateAuthUI(null);
    await refreshStatus();
});

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
        if (data.authenticated && data.user) {
            updateAuthUI(data.user);
        }
    } catch (error) {
        uploadStatus.textContent = `Unable to refresh status: ${error.message}`;
    }
};

uploadForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!currentUser) {
        openAuthModal(false, 'Please sign in before uploading clips.');
        return;
    }

    const filesInput = document.getElementById('clip-upload');
    const files = Array.from(filesInput.files);
    if (!files.length) {
        uploadStatus.textContent = 'Select one or more clips before uploading.';
        return;
    }

    const CHUNK_SIZE = 20 * 1024 * 1024; // 20 MB chunks to safely stay under Cloud Run's 32 MB limit

    uploadStatus.textContent = 'Preparing upload...';
    try {
        let totalUploaded = 0;
        for (const file of files) {
            const totalChunks = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));
            for (let i = 0; i < totalChunks; i++) {
                const start = i * CHUNK_SIZE;
                const end = Math.min(start + CHUNK_SIZE, file.size);
                const chunk = file.slice(start, end);

                const formData = new FormData();
                formData.append('file', chunk, file.name);
                formData.append('filename', file.name);
                formData.append('chunk_index', i);
                formData.append('total_chunks', totalChunks);

                if (totalChunks > 1) {
                    const percent = Math.round(((i + 1) / totalChunks) * 100);
                    uploadStatus.textContent = `Uploading ${file.name}: part ${i + 1}/${totalChunks} (${percent}%)...`;
                } else {
                    uploadStatus.textContent = `Uploading ${file.name}...`;
                }

                await apiRequest('/api/upload/chunk', {
                    method: 'POST',
                    body: formData,
                });
            }
            totalUploaded++;
        }
        uploadStatus.textContent = `Upload successful! ${totalUploaded} file(s) saved.`;
        filesInput.value = '';
        await refreshStatus();
    } catch (error) {
        uploadStatus.textContent = `Upload failed: ${error.message}`;
    }
});

promptForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!currentUser) {
        openAuthModal(false, 'Please sign in before generating and rendering.');
        return;
    }

    const promptValue = promptText.value.trim();
    if (!promptValue) {
        renderStatus.textContent = 'Enter an edit prompt before rendering.';
        return;
    }

    const useResolve = document.getElementById('use-resolve').checked;
    renderStatus.textContent = `Generating edit plan with Gemini & rendering video${useResolve ? ' with DaVinci Resolve' : ''}…`;
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

// Initialize on page load
checkAuth().then(refreshStatus);
