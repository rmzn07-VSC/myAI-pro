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
