const userInput = document.getElementById("userInput");
const chatBox = document.getElementById("chat-box");
const systemInfo = document.getElementById("system-info");

// Track conversation state
let conversationActive = false;

function appendMessage(sender, message, isError = false) {
    const msgDiv = document.createElement("div");
    msgDiv.className = sender === "You" ? "user-msg" : "bot-msg";
    
    if (isError) {
        msgDiv.classList.add("error-msg");
    }
    
    // Format message with better HTML handling
    const formattedMessage = message.replace(/\n/g, '<br>');
    msgDiv.innerHTML = `<strong>${sender}:</strong> ${formattedMessage}`;
    
    chatBox.appendChild(msgDiv);
    
    // Auto-scroll with smooth behavior
    setTimeout(() => {
        chatBox.scrollTop = chatBox.scrollHeight;
    }, 100);
}

function displaySystemInfo(message, type = 'info') {
    systemInfo.textContent = message;
    systemInfo.className = `system-info ${type}`;
    systemInfo.style.display = 'block';
    
    // Auto-hide after 7 seconds for success messages, 10 seconds for errors
    const timeout = type === 'error' ? 10000 : 7000;
    setTimeout(() => {
        systemInfo.style.display = 'none';
        systemInfo.textContent = '';
        systemInfo.className = 'system-info';
    }, timeout);
}

function setInputState(disabled) {
    userInput.disabled = disabled;
    const sendButton = document.querySelector('.input-container button');
    sendButton.disabled = disabled;
    
    if (disabled) {
        sendButton.textContent = 'Sending...';
        sendButton.style.opacity = '0.7';
    } else {
        sendButton.textContent = 'Send';
        sendButton.style.opacity = '1';
    }
}

function showTypingIndicator() {
    const thinkingMsg = document.createElement("div");
    thinkingMsg.className = "bot-msg typing-indicator";
    thinkingMsg.innerHTML = `
        <strong>Bot:</strong> 
        <span class="typing-dots">
            <span class="dot">.</span>
            <span class="dot">.</span>
            <span class="dot">.</span>
        </span>
        <span class="typing-text">Thinking...</span>
    `;
    thinkingMsg.id = "typing-indicator";
    chatBox.appendChild(thinkingMsg);
    chatBox.scrollTop = chatBox.scrollHeight;
    return thinkingMsg;
}

function removeTypingIndicator() {
    const typingIndicator = document.getElementById("typing-indicator");
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message || conversationActive) {
        return; // Don't send empty messages or multiple requests
    }

    conversationActive = true;
    setInputState(true);
    
    // Add user message
    appendMessage("You", message);
    userInput.value = "";

    // Show typing indicator
    const typingIndicator = showTypingIndicator();

    try {
        // Add timeout to the fetch request
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 45000); // 45 second timeout

        const res = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ message: message }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!res.ok) {
            throw new Error(`Server error: ${res.status} ${res.statusText}`);
        }

        const data = await res.json();
        
        // Remove typing indicator
        removeTypingIndicator();
        
        // Display bot response
        appendMessage("Bot", data.reply);

        // Handle ticket creation
        if (data.ticket_created && data.ticket) {
            displaySystemInfo(
                `🎫 Support Ticket #${data.ticket.id} created successfully! Our team will review your query and get back to you soon.`,
                'success'
            );
            
            // Optional: Play notification sound
            playNotificationSound();
        }

    } catch (error) {
        removeTypingIndicator();
        
        let errorMessage = "❌ Sorry, I couldn't process your request. ";
        
        if (error.name === 'AbortError') {
            errorMessage += "The request timed out. Please try again.";
        } else if (error.message.includes('Failed to fetch')) {
            errorMessage += "Please check your internet connection.";
        } else {
            errorMessage += "Please try again or contact support.";
        }
        
        console.error("Error sending message:", error);
        appendMessage("Bot", errorMessage, true);
        displaySystemInfo("Connection error occurred. Please try again.", 'error');
        
    } finally {
        conversationActive = false;
        setInputState(false);
        userInput.focus(); // Refocus on input
    }
}

function playNotificationSound() {
    // Create a simple notification sound using Web Audio API
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
    } catch (e) {
        // Ignore audio errors
    }
}

function showWelcomeMessage() {
    const welcomeMessages = [
        "Hello! 👋 I'm your APIhub Assistant. How can I help you today?",
        "Welcome to APIhub Support! 🚀 Ask me anything about our APIs, authentication, pricing, or features.",
        "Hi there! 🤖 I'm here to help you with APIhub. What would you like to know?"
    ];
    
    const randomMessage = welcomeMessages[Math.floor(Math.random() * welcomeMessages.length)];
    appendMessage('Bot', randomMessage);
}

function addQuickActions() {
    const quickActionsDiv = document.createElement('div');
    quickActionsDiv.className = 'quick-actions';
    quickActionsDiv.innerHTML = `
        <div class="quick-actions-title">Quick Help:</div>
        <button class="quick-btn" onclick="sendQuickMessage('How do I get an API key?')">🔑 API Key</button>
        <button class="quick-btn" onclick="sendQuickMessage('What are the pricing plans?')">💰 Pricing</button>
        <button class="quick-btn" onclick="sendQuickMessage('Show me available APIs')">📚 APIs</button>
        <button class="quick-btn" onclick="sendQuickMessage('Rate limits information')">⏱️ Rate Limits</button>
    `;
    
    const inputContainer = document.querySelector('.input-container');
    inputContainer.parentNode.insertBefore(quickActionsDiv, inputContainer);
}

function sendQuickMessage(message) {
    userInput.value = message;
    sendMessage();
}

// Event Listeners
userInput.addEventListener("keypress", function(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

// Auto-resize input based on content
userInput.addEventListener("input", function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    showWelcomeMessage();
    addQuickActions();
    userInput.focus();
    
    // Check server health on load
    fetch('/health')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'degraded') {
                displaySystemInfo('⚠️ AI service is currently unavailable. I\'ll create support tickets for your queries.', 'warning');
            }
        })
        .catch(() => {
            // Ignore health check errors
        });
});

// Add window focus handler to refocus input
window.addEventListener('focus', () => {
    if (!conversationActive) {
        userInput.focus();
    }
});