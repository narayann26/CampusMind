window.onload = function() {
    const username = localStorage.getItem('username');
    if (!username) {
        window.location.href = 'login.html';
    } else {
        document.getElementById('user-display').innerText = username.charAt(0).toUpperCase() + username.slice(1);
    }
};

async function sendMessage() {
    const input = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');
    const query = input.value.trim();

    if (!query) return;

    // User Message
    chatBox.innerHTML += `<div class="message user-msg">${query}</div>`;
    input.value = '';
    chatBox.scrollTop = chatBox.scrollHeight;

    // Bot Thinking Placeholder
    const botMsgId = 'bot-' + Date.now();
    chatBox.innerHTML += `<div class="message bot-msg" id="${botMsgId}">Typing...</div>`;
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch('http://127.0.0.1:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });

        const data = await response.json();
        document.getElementById(botMsgId).innerText = data.response;
    } catch (err) {
        document.getElementById(botMsgId).innerText = "Error: System is offline. Please check terminal.";
    }
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function refreshKnowledge() {
    if(!confirm("Update AI knowledge with new PDFs in 'documents' folder?")) return;
    
    const refreshBtn = document.querySelector('.refresh-btn');
    refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    refreshBtn.disabled = true;

    try {
        const response = await fetch('http://127.0.0.1:8000/refresh_data', { method: 'POST' });
        const data = await response.json();
        alert(data.message);
    } catch (err) {
        alert("Error updating knowledge base.");
    } finally {
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Data';
        refreshBtn.disabled = false;
    }
}