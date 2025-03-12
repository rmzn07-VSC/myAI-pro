import os
from flask import Flask, render_template, request, jsonify
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
chat_histories = {}
current_chat_id = None


@app.route('/', methods=['GET', 'POST'])
def index():
    global sohbet_gecmisi, chat, current_chat_id
    
    # Hiç sohbet yoksa veya yeni başlatılıyorsa
    if not current_chat_id:
        current_chat_id = str(time.time())
    
    if request.method == 'POST':
        if request.form.get('action') == 'clear':
            sohbet_gecmisi = []
            chat = model.start_chat(history=[])  # Reset chat history when clearing
            welcome_message = "Selam ben myAI 'ım!!! Nasılsın? Sana nasıl yardımcı olabilirim? 😊"
            sohbet_gecmisi.append({
                "rol": "ai",
                "icerik": welcome_message
            })
            
            # Yeni sohbet oluşturulduğunda
            if current_chat_id:
                chat_histories[current_chat_id] = {
                    "messages": sohbet_gecmisi.copy(),
                    "title": "Yeni Sohbet",
                    "timestamp": time.time()
                }
            
            return render_template('index.html', sohbet_gecmisi=sohbet_gecmisi, chat_histories=chat_histories)
            
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
        
        # Sohbeti geçmişe kaydet
        if current_chat_id:
            chat_histories[current_chat_id] = {
                "messages": sohbet_gecmisi.copy(),
                "title": get_chat_title(sohbet_gecmisi),
                "timestamp": time.time()
            }
    
    # Sohbet geçmişini tarihe göre sırala
    sorted_histories = dict(sorted(
        chat_histories.items(),
        key=lambda x: x[1]['timestamp'],
        reverse=True
    ))
    
    return render_template('index.html', 
                         sohbet_gecmisi=sohbet_gecmisi, 
                         chat_histories=sorted_histories,
                         current_chat_id=current_chat_id)


@app.route('/new_chat', methods=['POST'])
def new_chat():
    global sohbet_gecmisi, chat, current_chat_id
    
    app.logger.info("Yeni sohbet isteği alındı")
    
    try:
        # Yeni benzersiz ID oluştur
        new_chat_id = str(time.time())
        app.logger.info(f"Yeni sohbet ID: {new_chat_id}")
        
        # Eski sohbeti kaydet (eğer varsa)
        if current_chat_id and sohbet_gecmisi:
            app.logger.info(f"Eski sohbet kaydediliyor: {current_chat_id}")
            chat_histories[current_chat_id] = {
                "messages": sohbet_gecmisi.copy(),
                "title": get_chat_title(sohbet_gecmisi),
                "timestamp": time.time()
            }
        
        # Yeni sohbet başlat
        sohbet_gecmisi = []
        chat = model.start_chat(history=[])
        
        # Hoşgeldin mesajı
        welcome_message = "Selam ben myAI 'ım!!! Nasılsın? Sana nasıl yardımcı olabilirim? 😊"
        sohbet_gecmisi = [{
            "rol": "ai",
            "icerik": welcome_message
        }]
        
        # Yeni sohbeti geçmişe ekle
        chat_histories[new_chat_id] = {
            "messages": sohbet_gecmisi.copy(),
            "title": "Yeni Sohbet",
            "timestamp": time.time()
        }
        
        # Current chat ID'yi güncelle
        current_chat_id = new_chat_id
        
        app.logger.info(f"Yeni sohbet başarıyla oluşturuldu: {new_chat_id}")
        
        response_data = {
            "status": "success",
            "chat_id": new_chat_id,
            "messages": sohbet_gecmisi,
            "title": "Yeni Sohbet"
        }
        
        app.logger.info(f"Yanıt gönderiliyor: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        app.logger.error(f"Hata oluştu: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/load_chat/<chat_id>', methods=['GET'])
def load_chat(chat_id):
    global sohbet_gecmisi, chat, current_chat_id
    
    app.logger.info(f"Sohbet yükleme isteği alındı: {chat_id}")
    
    try:
        if chat_id in chat_histories:
            # Mevcut sohbeti kaydet
            if current_chat_id and sohbet_gecmisi:
                chat_histories[current_chat_id] = {
                    "messages": sohbet_gecmisi.copy(),
                    "title": get_chat_title(sohbet_gecmisi),
                    "timestamp": time.time()
                }
            
            # Yeni sohbeti yükle
            sohbet_gecmisi = chat_histories[chat_id]["messages"].copy()
            chat = model.start_chat(history=[])  # Yeni chat instance
            current_chat_id = chat_id
            
            app.logger.info(f"Sohbet başarıyla yüklendi: {chat_id}")
            
            return jsonify({
                "status": "success",
                "messages": sohbet_gecmisi,
                "current_chat_id": current_chat_id
            })
            
        app.logger.error(f"Sohbet bulunamadı: {chat_id}")
        return jsonify({
            "status": "error",
            "message": "Sohbet bulunamadı"
        }), 404
        
    except Exception as e:
        app.logger.error(f"Sohbet yükleme hatası: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def get_chat_title(messages):
    """İlk kullanıcı mesajını başlık olarak kullan"""
    for message in messages:
        if message["rol"] == "user":
            title = message["icerik"][:30]  # İlk 30 karakter
            return title + "..." if len(title) >= 30 else title
    return "Yeni Sohbet"


if __name__ == '__main__':
    app.run(debug=True)