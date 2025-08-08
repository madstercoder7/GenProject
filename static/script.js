document.addEventListener('DOMContentLoaded', () => {
    // Sidebar toggle
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebarToggle');
    if (sidebar && toggle) {
        if (window.innerWidth <= 992 && localStorage.getItem('sidebarCollapsed') === 'true') {
            sidebar.classList.add('collapsed');
        }
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        });
    }

    // Form input animations
    const inputs = document.querySelectorAll('.auth-form .form-control');
    inputs.forEach(input => {
        input.addEventListener('focus', () => {
            input.parentElement.classList.add('focused');
        });
        input.addEventListener('blur', () => {
            if (!input.value) {
                input.parentElement.classList.remove('focused');
            }
        });
    });
});

document.addEventListener('DOMContentLoaded', function () {
    const toastElList = [].slice.call(document.querySelectorAll('.toast'));
    toastElList.forEach(function (toastEl) {
        new bootstrap.Toast(toastEl, { delay: 4000 }).show();
    });
});

let timer;
function resetTimer() {
    clearTimeout(timer);
    timer = setTimeout(() => {
        window.location.href = "/logout";
    }, 600000);
}

['mousemove', 'keypress', 'click'].forEach(evt =>
    document.addEventListener(evt, resetTimer)
);

resetTimer();


const socket = io();
const sessionId = "{{ session_id }}";
const userId = "{{ user.id }}";

const messagesContiner = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const typingIndicator = document.getElementById("typingIndicator");
const connectionStatus = document.getElementById("connectionStatus");
const charCount = document.querySelector(".char-count");

socket.on("connect", () => {
    updateConnectionStatus("connect", "Connected");
    socket.emit("join_chat", { sessionId: sessionId });
});

socket.on("disconnect", () => {
    updateConnectionStatus("disconnected", "Disconnected");
});

socket.on("connected", () => {
    console.log("Connected", data.message);
});

socket.on("chat_history", (data) => {
    const welcomeMsg = document.querySelector(".welcome-message").parentElement;
    messagesContiner.innerHTML = "";
    messagesContiner.appendChild(welcomeMsg);

    data.messages.forEach(msg => {
        addMessage(msg.type, msg.content, false, msg.timestamp);
    });
    scorllToBottom();
})

socket.on("message_confirmed", (data) => {
    console.log("Message confirmed");
});

socket.on("bot_response", (data) => {
    hideTyping();
    addMessage("bot", data.content, data.error, data.timestamp, data.regenerated);
    scorllToBottom();
});

socket.on("bot_typing", (data) => {
    if (data.typing) {
        showTyping();
    } else {
        hideTyping();
    }
});

socket.on("error", () => {
    hideTyping();
    addMessage("bot", data.message, true);
    scorllToBottom();
})

function sendMessage() {
    const message = messageInput.value.trim();
    if (message && message.length <= 500) {
        addMessage("user", message);
        socket.emit("user_message", {
            sessionId: sessionId,
            userId: userId,
            message: message
        });

        messageInput.value = "";
        updateCharCount();
        autoResize();
        scorllToBottom();
    }
}

function sendSuggestion(suggestion) {
    messageInput.value = suggestion;
    sendMessage();
}

function formatMessage(content) {
    return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/```([\s\S]*?)```/g, '<pre class="code-block"><code>$1</code></pre>')
        .replace(/`(.*?)`/g, '<code class="inline-code">$1</code>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/^(.*)$/, '<p>$1</p>');
}

function updateConnectionStatus(status, text) {
    connectionStatus.className = `connection-status status-${status}`;
    connectionStatus.innerHTML = `<i class="fas fa-circle"></i> ${text}`;
}

function addMessage(type, content, isError = false, timestamp = null, isRegenerated = false) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${type}-message`;

    const time = timestamp ? new Data(timestamp) : new Date();
    const timeString = time.toLocateTimeString([], {hour: '2-digit', minute: '2-digit'});
    const formattedContent = formatMessage(content);

    let actionsHtml = "";
    if (type === "bot" && !isError) {
        actionsHtml = `
        <div class="message-actions">
            <button class="btn-action" onclick="regenerateResponse('${content}')">
                <i class="fas fa-redo"></i> Regenrate
            </button>
            <button class="btn-action" onclick="copyToClipboard(\`${escapeHtml(content)}\`)
                <i class="fas fa-copy"></i> Copy
            </button>
        </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-bubble ${isError ? 'error-message' : ''}">
            ${formattedContent}
            <div class="message-time">${timeString}${isRegenerated ? ' (regenerated)' : ''}</div>
            ${actionsHtml}
        </div>
    `;

    messagesContiner.appendChild(messageDiv);
    scorllToBottom();
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/`/g, '\\`');
}

function regenerateResponse(originalContent) {
    const userMessages = document.querySelectorAll('.user-message');
    if (userMessages.length > 0) {
        const lastUserMessage = userMessages[userMessages.length - 1];
        const topic = lastUserMessage.querySelector('.message-bubble').textContent.trim();

        socket.emit("regenerate_response", {
            sessionId: sessionId,
            topic: topic
        });
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast("Copied to clipboard!", "success");
    }).catch(() => {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
        showToast("Copies to clipborad", "success");
    });
}

function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container');
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0 show`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 3000);
}

function loadProject(topic, projectId) {
    messageInput.value = `Tell me more about: ${topic}`;
    messageInput.focus();
}

function toggleSidebar() {
    const sidebar = document.getElementById('chatSidebar');
    sidebar.classList.toggle('show');
}

function updateConnectionStatus(status, text) {
    connectionStatus.className = `connection-status status-${status}`;
    connectionStatus.innerHTML = `<i class="fas fa-circle"></i> ${text}`;
}

function showTyping() {
    typingIndicator.style.display = 'flex';
    scrollToBottom();
}

function hideTyping() {
    typingIndicator.style.display = 'none';
}

function scrollToBottom() {
    setTimeout(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 100);
}

function updateCharCount() {
    const count = messageInput.value.length;
    charCount.textContent = `${count}/500`;
    charCount.style.color = count > 450 ? '#dc3545' : '#6c757d';
    
    sendButton.disabled = count === 0 || count > 500;
}

function autoResize() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
}

messageInput.addEventListener('input', () => {
    updateCharCount();
    autoResize();
});

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendButton.addEventListener('click', sendMessage);

updateCharCount();
scrollToBottom();

document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('chatSidebar');
    const toggleBtn = document.querySelector('.sidebar-toggle');
    
    if (sidebar.classList.contains('show') && 
        !sidebar.contains(e.target) && 
        !toggleBtn.contains(e.target)) {
        sidebar.classList.remove('show');
    }
});