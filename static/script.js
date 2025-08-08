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

func