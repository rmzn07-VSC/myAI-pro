import os
from flask import Flask, render_template, request # type: ignore
from markupsafe import Markup  # type: ignore # Değişiklik burada
import google.generativeai as genai # type: ignore
from dotenv import load_dotenv # type: ignore
import markdown2 # type: ignore
import bleach  # type: ignore # HTML temizleme için ekleyin (pip install bleach)
import time
from quest import Quest

load_dotenv()

app = Flask(__name__)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')
chat = model.start_chat(history=[])  # Create a persistent chat instance

sohbet_gecmisi = []  # SOHBET GEÇMİŞİNİ TUTACAK LİSTE (YENİ!)


@app.route('/', methods=['GET', 'POST'])
def index():
    global sohbet_gecmisi, chat
    
    if request.method == 'POST':
        if request.form.get('action') == 'clear':
            sohbet_gecmisi = []
            chat = model.start_chat(history=[])  # Reset chat history when clearing
            welcome_message = "Selam ben myAI 'ım!!! Nasılsın? Sana nasıl yardımcı olabilirim? 😊"
            sohbet_gecmisi.append({
                "rol": "ai",
                "icerik": welcome_message
            })
            return render_template('index.html', sohbet_gecmisi=sohbet_gecmisi)
            
        mesaj = request.form['mesaj']
        if mesaj.strip():  # Boş mesaj kontrolü
            quest = Quest(mesaj, time.time())
            sohbet_gecmisi.append({"rol": "user", "icerik": mesaj, "quest_id": quest.quest_id})
            
            # Use the chat instance to maintain conversation history
            response = chat.send_message(mesaj)
            
            # Markdown'ı güvenli bir şekilde HTML'e dönüştür
            html_content = markdown2.markdown(
                response.text,
                extras=['fenced-code-blocks', 'tables', 'break-on-newline']
            )
            
            # HTML'i temizle ve güvenli etiketlere izin ver
            cleaned_html = bleach.clean(
                html_content,
                tags=['p', 'strong', 'em', 'code', 'pre', 'br', 'a'],
                attributes={'a': ['href']},
                strip=True
            )
            
            sohbet_gecmisi.append({
                "rol": "ai", 
                "icerik": Markup(cleaned_html),
                "yeni_yanit": True  # Yeni yanıt flag'i
            })

    return render_template('index.html', sohbet_gecmisi=sohbet_gecmisi) # sohbet_gecmisi LİSTESİNİ HTML'E GÖNDERİYORUZ!


if __name__ == '__main__':
    app.run(debug=True)