let selectedProjectId = null;
const msgInput = $("messageInput");
if (msgInput) {
    msgInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            const msg = msgInput.value.trim();
            if (msg) sendMessage(msg);
        }
    });
}

function $(id) {
    return document.getElementById(id);
}

function on(id, event, handler) {
    const el = $(id);
    if (el) el.addEventListener(event, handler);
}

function showToast(message, category = "danger") {
    const container = document.querySelector(".toast-container");
    if (!container) {
        alert(message);
        return;
    }

    const wrapper = document.createElement("div");
    wrapper.className = `toast align-items-center text-bg-${category} border-0 show`;
    wrapper.setAttribute("role", "alert");
    wrapper.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    container.appendChild(wrapper);
    setTimeout(() => wrapper.remove(), 4000);
}

function safeFetch(url, opts) {
    return fetch(url, opts).then(async (res) => {
        if (!res.ok) {
            let detail = "";
            try { detail = (await res.json()).error || await res.text(); } catch{}
            throw new Error(detail || `HTTP ${res.status}`);
        }
        const ct = res.headers.get("content-type") || "";
        if (ct.includes("application/json")) return res.json();
        return res.text();
    });
}

function fetchProjects() {
    if (!$("projectList")) return;

    safeFetch("/history")
    .then((data) => {
        const list = $("projectList");
        list.innerHTML = "";
        if (!Array.isArray(data) || data.length === 0) {
            if ($("emptyProjects")) $("emptyProjects").style.display = "block";
            return;
        }
        if ($("emptyProjects")) $("emptyProjects").style.display = "none";
        data.forEach((project) => {
            const li = document.createElement("li");
            li.className = "history-item d-flex justify-content-between align-items-center";
            li.innerHTML = `
                <span class="flex-grow-1">${project.topic}</span>
                <button class="btn btn-sm btn-outline-light me-1 rename-btn" data-id="${project.public_id}">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${project.public_id}">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            li.querySelector("span").onclick = () => selectProject(project.public_id);
            list.appendChild(li);
        });

        if (!selectedProjectId && data[0]?.public_id) {
            selectProject(data[0].public_id);
        }
    })
    .catch((err) => {
        showToast(`Failed to load projects: ${err.message}`, "warning");
    });
}

function selectProject(publicId) {
    selectedProjectId = publicId;
    fetchChathistory();
    const input = $("messageInput");
    if (input) input.focus();
}

function sendMessage(message) {
    if (!selectedProjectId || !message) return;

    const btn = $("sendBtn");
    const spinner = $("loadingSpinner");
    if (btn) btn.disabled = true;
    if (spinner) spinner.style.display = "inline-block";

    safeFetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, project_id: selectedProjectId }),
    })
    .then((data) => {
        renderChatHistory(data.history);
        if ($("messageInput")) $("messageInput").value = "";
    })
    .catch((err) => showToast(`Failed to send: ${err.message}`))
    .finally(() => {
        if (btn) btn.disabled = false;
        if (spinner) spinner.style.display = "none";
    });
}

function fetchChathistory() {
    if (!selectedProjectId) return;
    safeFetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "", project_id: selectedProjectId }),
    })
    .then((data) => {
        if (data?.history) renderChatHistory(data.history);
    })
    .catch((err) => showToast(`Failed to load chat: ${err.message}`));
}

function renderChatHistory(history) {
    const chatDiv = $("chatHistory");
    if (!chatDiv) return;
    chatDiv.innerHTML = "";
    history.forEach((msg) => {
        const bubble = document.createElement("div");
        const userClass = msg.role === "user" ? "user-message" : "ai-message";
        bubble.className = "message mb-2 " + userClass;

        let formattedContent = msg.content;
        if (msg.role === "assistant") {
            try {
                formattedContent = marked.parse(msg.content);
                setTimeout(() => {
                    document.querySelectorAll("pre code").forEach((block) => {
                        hljs.highlightElement(block);
                    });
                }, 0);
            } catch {
                formattedContent = msg.content;
            }
        }

        bubble.innerHTML = `
            <div class="message-header">
                <span>${msg.role === "user" ? "You" : "AI Mentor"}</span>
                <span class="timestamp">${msg.timestamp || ""}</span>
            </div>
            <div class="message-content">${formattedContent}</div>
        `;
        chatDiv.appendChild(bubble);
    });
    chatDiv.scrollTop = chatDiv.scrollHeight;
}

on("newProjectBtn", "click", () => {
    if ($("newProjectModal")) $("newProjectModal").style.display = "block";
});

on("closeProjectModal", "click", () => {
    if ($("newProjectModal")) $("newProjectModal").style.display = "none";
});

on("closeRenameModal", "click", () => {
    if ($("renameProjectModal")) $("renameProjectModal").style.display = "none";
})

on("newProjectForm", "submit", (e) => {
    e.preventDefault();
    const title = $("newProjectTitle")?.value?.trim();
    const desc = $("newProjectDesc")?.value?.trim() || "";
    if (!title) return showToast("Please provide a project title", "warning");
    safeFetch("/create_project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: title, content: desc }),
    })
    .then((data) => {
        if ($("newProjectModal")) $("newProjectModal").style.display = "none";
        fetchProjects();
        if (data?.public_id) selectProject(data.public_id);
    })
    .catch((err) => showToast(`Failed to create project: ${err.message}`));
});

on("chatForm", "submit", (e) => {
    e.preventDefault();
    const msg = $("messageInput")?.value?.trim();
    if (msg) sendMessage(msg);
});

on("renameProjectForm", "submit", (e) => {
    e.preventDefault();
    const title = $("renameProjectTitle")?.value?.trim();
    if (!title || !selectedProjectId) return;
    safeFetch("/rename_project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: selectedProjectId, topic: title }),
    })
    .then(() => {
        $("renameProjectModal").style.display = "none";
        fetchProjects();
    })
    .catch((err) => showToast(`Failed to rename: ${err.message}`));
});

document.addEventListener("click", (e) => {
    if (e.target.closest(".rename-btn")) {
        selectedProjectId = e.target.closest(".rename-btn").dataset.id;
        $("renameProjectModal").style.display = "block";
    }
    if (e.target.closest(".delete-btn")) {
        const id = e.target.closest(".delete-btn").dataset.id;
        safeFetch("/delete_project", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ project_id: id }),
        })
        .then(() => {
            fetchProjects();
            const chatDiv = $("chatHistory");
            if (chatDiv) {
                chatDiv.innerHTML = `<p class="text-gray-500">Select a project to start chatting.</p>`;
            }
            if (selectedProjectId == id) {
                selectedProjectId = null;
            }
        })
        .catch((err) => showToast(`Failed to delete: ${err.message}`));
    }
});

window.addEventListener("load", () => {
    if ($("projectList")) fetchProjects();
})