function addMessage(content, sender) {
    const chatBox = document.getElementById('chat-box');
    const message = document.createElement('div');
    message.classList.add('message', sender);

    const messageContent = document.createElement('div');
    messageContent.classList.add('content');
    messageContent.textContent = content;

    message.appendChild(messageContent);
    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;  // Auto-scroll to the bottom
}

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const userMessage = userInput.value.trim();

    if (userMessage) {
        addMessage(userMessage, 'user');
        userInput.value = '';

        // Send the message to the backend
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: userMessage }),
        });

        const data = await response.json();
        addMessage(data.answer, 'bot');
    }
}

document.getElementById('send-button').onclick = sendMessage;

document.getElementById('user-input').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
    }
});
