let selectedProjectId = null;

function fetchProjects() {
    fetch("/history")
      .then(res => res.json())
      .then(data => {
          const list = document.getElementById("projectList");
          list.innerHTML = "";
          if (data.length === 0) {
              document.getElementById("emptyProjects").style.display = "block";
              return;
          }
          document.getElementById("emptyProjects").style.display = "none";
          data.forEach(project => {
              const li = document.createElement("li");
              li.textContent = project.topic;
              li.className = "history-item";
              li.onclick = () => selectProject(project.id);
              list.appendChild(li);
          });
      });
}

function selectProject(projectId) {
    selectedProjectId = projectId;
    fetchChatHistory();
}

function sendMessage(message) {
    if (!selectedProjectId || !message) return;
    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, project_id: selectedProjectId })
    })
    .then(res => res.json())
    .then(data => {
        renderChatHistory(data.history);
        document.getElementById("messageInput").value = "";
    });
}

function fetchChatHistory() {
    if (!selectedProjectId) return;
    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, project_id: selectedProjectId })
    })
    .then(res => res.json())
    .then(data => renderChatHistory(data.history));
}

function renderChatHistory(history) {
    const chatDiv = document.getElementById("chatHistory");
    chatDiv.innerHTML = "";
    history.forEach(msg => {
        const bubble = document.createElement("div");
        bubble.className = "message mb-2 " + (msg.role === "user" ? "bg-primary text-white" : "bg-light text-dark");
        bubble.innerHTML = `
            <div class="message-header">
                <span>${msg.role === "user" ? "You" : "assistant"}</span>
                <span class="timestamp">${msg.timestamp}</span>
            </div>
            <div class="message-content">${msg.content}</div>
        `;
        chatDiv.appendChild(bubble);
    });
    chatDiv.scrollTop = chatDiv.scrollHeight;
}

document.getElementById("newProjectBtn").onclick = () => {
    document.getElementById("newProjectModal").style.display = "block";
};
document.getElementById("closeProjectModal").onclick = () => {
    document.getElementById("newProjectModal").style.display = "none";
};
document.getElementById("newProjectForm").onsubmit = function(e) {
    e.preventDefault();
    const title = document.getElementById("newProjectTitle").value;
    const desc = document.getElementById("newProjectDesc").value;
    fetch("/create_project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: title, content: desc })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("newProjectModal").style.display = "none";
        fetchProjects();
        selectProject(data.id);
    });
};
document.getElementById("chatForm").onsubmit = function(e) {
    e.preventDefault();
    const msg = document.getElementById("messageInput").value.trim();
    if (msg) sendMessage(msg);
};

window.onload = fetchProjects;
