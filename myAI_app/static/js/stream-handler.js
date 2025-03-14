class StreamHandler {
    constructor() {
        this.chatForm = document.getElementById('chat-form');
        this.chatContainer = document.getElementById('chat-container');
        this.messageInput = document.getElementById('mesaj');
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.chatForm.addEventListener('submit', async (e) => {
            if (e.submitter.value === 'send') {
                e.preventDefault();
                await this.handleSubmit(e);
            }
        });
    }

    async handleSubmit(_e) {
        const message = this.messageInput.value.trim();
        if (!message) return;

        // Kullanıcı mesajını ekle
        this.appendUserMessage(message);
        
        // Sohbet başlığını güncelle (ilk mesaj ise)
        this.updateChatTitle(message);

        // AI mesaj container'ını oluştur
        const aiMessageContainer = this.createAIMessageContainer();
        const aiResponseDiv = aiMessageContainer.querySelector('.ai-response');

        // Input'u temizle
        this.messageInput.value = '';

        try {
            const response = await fetch('/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.type === 'error') {
                            aiResponseDiv.innerHTML = `<p class="error">Hata: ${data.error}</p>`;
                            break;
                        }
                        
                        if (data.type === 'end') {
                            // Mesaj tamamlandı, kod bloklarına copy button ekle
                            if (aiMessageContainer.querySelector('pre')) {
                                addCopyButtonToMessage(aiMessageContainer);
                            }
                            break;
                        }
                        
                        // Karakteri ekle ve scroll
                        buffer += data.char;
                        aiResponseDiv.innerHTML = buffer;
                        this.scrollToBottom();
                    }
                }
            }
        } catch{
           
        }
    }

    updateChatTitle(message) {
        const activeChat = document.querySelector('.history-item.active');
        if (!activeChat) return;

        const titleSpan = activeChat.querySelector('span');
        if (titleSpan && titleSpan.textContent.trim() === 'Yeni Sohbet') {
            // Mesajı max 10 karaktere kısalt
            let title = message.slice(0, 10);
            // Eğer kelime ortasında kesildiyse, son kelimeyi kaldır
            if (message.length > 10) {
                title = title.slice(0, title.lastIndexOf(' '));
            }
            // Boş kontrolü
            title = title.trim() || message.slice(0, 10);
            titleSpan.textContent = title + '...';
        }
    }

    appendUserMessage(message) {
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user-message';
        userMessageDiv.innerHTML = `
            <div class="message-content">
                <h2>Sen:</h2>
                <p>${message}</p>
            </div>
        `;
        this.chatContainer.appendChild(userMessageDiv);
    }

    createAIMessageContainer() {
        const aiMessageDiv = document.createElement('div');
        aiMessageDiv.className = 'message ai-message';
        aiMessageDiv.innerHTML = `
            <div class="message-content">
                <h2>ÖzGür.AI Cevabı:</h2>
                <div class="ai-response"></div>
            </div>
        `;
        this.chatContainer.appendChild(aiMessageDiv);
        return aiMessageDiv;
    }

    scrollToBottom() {
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }
}
