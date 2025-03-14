from bs4 import BeautifulSoup # type: ignore
import re
import html

class TitleManager:
    @staticmethod
    def clean_html_content(content):
        """HTML içeriğini temizle ve düz metne çevir"""
        try:
            # HTML entities'leri decode et
            decoded_content = html.unescape(str(content))
            # HTML'i temizle
            soup = BeautifulSoup(decoded_content, 'html.parser')
            # Tüm script ve style elementlerini kaldır
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text(strip=True)
        except Exception:
            return str(content)

    @staticmethod
    def clean_title(text):
        """Başlık metnini temizle ve düzenle"""
        # Özel karakterleri ve emojileri temizle
        clean_text = re.sub(r'[^\w\s\-]+', '', text, flags=re.UNICODE)
        # Fazla boşlukları temizle
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Minimum 3 karakter olsun
        if len(clean_text) < 3:
            return "Yeni"
            
        # Maksimum 10 karakter al
        if len(clean_text) > 10:
            # Son kelimeyi kırpmamak için son boşluğa kadar al
            clean_text = clean_text[:10].rsplit(' ', 1)[0]
        
        return clean_text

    @staticmethod
    def get_chat_title(messages):
        """Sohbet başlığı oluştur"""
        try:
            if not messages:
                return "Yeni Sohbet"

            # İlk kullanıcı mesajını bul
            for message in messages:
                if message.get("rol") == "user":
                    content = message.get("icerik", "")
                    if content:
                        clean_content = TitleManager.clean_html_content(content)
                        title = TitleManager.clean_title(clean_content)
                        return f"{title}..." if title else "Yeni Sohbet"

        except Exception as e:
            print(f"Başlık oluşturma hatası: {str(e)}")
            
        return "Yeni Sohbet"
