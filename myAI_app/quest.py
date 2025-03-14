class Quest:
    def __init__(self, content, timestamp):
        self.content = content
        self.timestamp = timestamp
        self.quest_id = hash(content + str(timestamp))
    
    def __eq__(self, other):
        if not isinstance(other, Quest):
            return False
        return self.content.lower().strip() == other.content.lower().strip()

    def to_dict(self):
        return {
            "content": self.content,
            "timestamp": self.timestamp,
            "quest_id": self.quest_id
        }

    def check_for_first_message_request(self, content):
        """Mesajın ilk mesaj isteği olup olmadığını kontrol et"""
        keywords = [
            "ilk mesaj",
            "önceki mesaj",
            "son mesaj",
            "ne dedim",
            "ne söyledim",
            "ilk ne dedin",
            "ilk sözün"
        ]
        content = content.lower().strip()
        return any(keyword in content for keyword in keywords)

    def get_response_for_first_message(self, messages):
        """İlk mesaj sorusuna cevap hazırla"""
        if len(messages) >= 2:
            # İlk AI mesajını atla, ikinci mesajı al
            for idx, msg in enumerate(messages[1:], 1):  # 1'den başla
                if msg["rol"] == "user":
                    if len(messages) > idx + 1:  # Bir sonraki mesaj var mı kontrol et
                        ai_response = messages[idx + 1]
                        if ai_response["rol"] == "ai":
                            return f"İlk konuşmamızda sen '{msg['icerik']}' dedin, ben de '{ai_response['icerik']}' diye cevap verdim. 😊"
            return "İlk konuşmamızı hatırlayamıyorum. 🤔"
        return "Henüz bir konuşma başlatmadık. 😊"
