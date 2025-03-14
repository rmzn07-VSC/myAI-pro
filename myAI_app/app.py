import os
from flask import Flask, render_template, request, jsonify, Response, stream_with_context # type: ignore
from markupsafe import Markup  # type: ignore # Değişiklik burada
import google.generativeai as genai # type: ignore
from dotenv import load_dotenv # type: ignore
import markdown2 # type: ignore
import bleach  # type: ignore # HTML temizleme için ekleyin (pip install bleach)
import time
import json
from quest import Quest
from utils.title_manager import TitleManager

load_dotenv()

app = Flask(__name__)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')
chat = model.start_chat(history=[])  # Create a persistent chat instance

sohbet_gecmisi = []  # SOHBET GEÇMİŞİNİ TUTACAK LİSTE (YENİ!)
chat_histories = {}
current_chat_id = None
MAX_CHATS = 10  # Maksimum sohbet sayısı sabiti

def is_duplicate_message_across_chats(message):
    """Tüm sohbetlerde aynı mesajı kontrol et"""
    message = message.strip().lower()
    for chat_data in chat_histories.values():
        messages = chat_data["messages"]
        for msg in messages:
            if msg["rol"] == "user" and msg["icerik"].strip().lower() == message:
                return True
    return False

def get_last_messages():
    """Her sohbetteki en son kullanıcı mesajını al"""
    last_messages = []
    for chat_data in chat_histories.values():
        messages = chat_data["messages"]
        # Sondan başlayarak ilk kullanıcı mesajını bul
        for msg in reversed(messages):
            if msg["rol"] == "user":
                last_messages.append(msg["icerik"].strip().lower())
                break
    return last_messages

def is_duplicate_last_message(message):
    """Sadece son mesajları kontrol et"""
    message = message.strip().lower()
    last_messages = get_last_messages()
    return message in last_messages

def load_system_prompts():
    """İki sistem promptunu da yükle ve birleştir"""
    try:
        prompt1 = ""
        prompt2 = ""
        
        # İlk prompt'u yükle
        prompt_path1 = os.path.join('prompts', 'system_prompt.txt')
        with open(prompt_path1, 'r', encoding='utf-8') as file:
            prompt1 = file.read()
            
        # İkinci prompt'u yükle
        prompt_path2 = os.path.join('prompts', 'system_prompt2.txt')
        with open(prompt_path2, 'r', encoding='utf-8') as file:
            prompt2 = file.read()
            
        return prompt1 + "\n\n" + prompt2
    except FileNotFoundError:
        return "Sen ÖzGür.AI isimli bir yapay zeka asistanısın."

def create_new_chat_instance():
    """Yeni bir chat instance oluştur ve system promptları yükle"""
    chat = model.start_chat(history=[])
    # System promptları gönder ve yanıtı bekle
    system_prompt = load_system_prompts()
    chat.send_message(system_prompt)
    return chat

def send_ai_message(message, current_chat=None):
    """AI'ya mesaj gönder, eğer chat yoksa veya hata alırsan yeni chat başlat"""
    try:
        if current_chat is None:
            current_chat = create_new_chat_instance()
        return current_chat.send_message(message)
    except Exception as e:
        app.logger.error(f"Chat hatası, yeni instance oluşturuluyor: {str(e)}")
        current_chat = create_new_chat_instance()
        return current_chat.send_message(message)

@app.route('/', methods=['GET', 'POST'])
def index():
    global sohbet_gecmisi, chat, current_chat_id
    
    # Yeniden yükleme sırasında mevcut sohbeti koru
    if not current_chat_id:
        if chat_histories:
            # En son sohbeti yükle
            current_chat_id = next(iter(chat_histories))
            sohbet_gecmisi = chat_histories[current_chat_id]["messages"].copy()
            chat = create_new_chat_instance()  # Değişiklik burada
        else:
            # İlk defa açılıyorsa yeni sohbet başlat
            current_chat_id = str(time.time())
            welcome_message = "Selam ben ÖzGür.AI 'ım!!! Nasılsın? Sana nasıl yardımcı olabilirim? 😊"
            sohbet_gecmisi = [{
                "rol": "ai",
                "icerik": welcome_message
            }]
            chat_histories[current_chat_id] = {
                "messages": sohbet_gecmisi.copy(),
                "title": "Yeni Sohbet",
                "timestamp": time.time()
            }
    
    if request.method == 'POST':
        if request.form.get('action') == 'clear':
            # Mevcut sohbeti sıfırla ama ID'yi koru
            old_chat_id = current_chat_id
            sohbet_gecmisi = []
            chat = model.start_chat(history=[])
            # Sistem promptunu gönder
            chat.send_message(load_system_prompts())
            welcome_message = "Selam ben ÖzGür.AI 'ım!!! Nasılsın? Sana nasıl yardımcı olabilirim? 😊"
            sohbet_gecmisi.append({
                "rol": "ai",
                "icerik": welcome_message
            })
            
            # Aynı ID ile yeni sohbeti kaydet
            chat_histories[old_chat_id] = {
                "messages": sohbet_gecmisi.copy(),
                "title": "Yeni Sohbet",
                "timestamp": time.time()
            }
            
            return render_template('index.html', 
                                sohbet_gecmisi=sohbet_gecmisi, 
                                chat_histories=chat_histories,
                                current_chat_id=old_chat_id)
        
        elif request.form.get('action') == 'send' and request.form.get('mesaj', '').strip():
            mesaj = request.form['mesaj'].strip()
            
            # İlk mesaj kontrolü
            quest = Quest(mesaj, time.time())
            if quest.check_for_first_message_request(mesaj):
                response_text = quest.get_response_for_first_message(sohbet_gecmisi)
                sohbet_gecmisi.append({
                    "rol": "user",
                    "icerik": mesaj,
                    "quest_id": quest.quest_id
                })
                sohbet_gecmisi.append({
                    "rol": "ai",
                    "icerik": response_text,
                    "yeni_yanit": True
                })
                
                if current_chat_id:
                    chat_histories[current_chat_id] = {
                        "messages": sohbet_gecmisi.copy(),
                        "title": get_chat_title(sohbet_gecmisi),
                        "timestamp": time.time()
                    }
                
                return render_template('index.html',
                                    sohbet_gecmisi=sohbet_gecmisi,
                                    chat_histories=chat_histories,
                                    current_chat_id=current_chat_id)
            
            # Sadece son mesajlarda duplicate kontrolü
            if is_duplicate_last_message(mesaj):
                return render_template('index.html', 
                                    sohbet_gecmisi=sohbet_gecmisi, 
                                    chat_histories=chat_histories,
                                    current_chat_id=current_chat_id)

            # Duplicate kontrolü
            if not any(m.get("icerik") == mesaj for m in sohbet_gecmisi[-2:]):
                quest = Quest(mesaj, time.time())
                sohbet_gecmisi.append({"rol": "user", "icerik": mesaj, "quest_id": quest.quest_id})
                
                # AI yanıtı - Değişiklik burada
                response = send_ai_message(mesaj, chat)
                
                # Markdown ve HTML işlemleri
                html_content = markdown2.markdown(
                    response.text,
                    extras=['fenced-code-blocks', 'tables', 'break-on-newline']
                )
                
                cleaned_html = bleach.clean(
                    html_content,
                    tags=['p', 'strong', 'em', 'code', 'pre', 'br', 'a'],
                    attributes={'a': ['href']},
                    strip=True
                )
                
                sohbet_gecmisi.append({
                    "rol": "ai", 
                    "icerik": Markup(cleaned_html),
                    "yeni_yanit": True
                })
                
                # Sohbeti kaydet
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
        # Mevcut sohbet sayısını kontrol et
        if len(chat_histories) >= MAX_CHATS:
            return jsonify({
                "status": "error",
                "message": "Artık sohbetleri temizleyerek kullanın, performans ve veri güvenliği için önemlidir."
            })
            
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
        chat = create_new_chat_instance()  # Değişiklik burada
        
        # Hoşgeldin mesajı
        welcome_message = "Selam ben ÖzGür.AI 'ım!!! Nasılsın? Sana nasıl yardımcı olabilirim? 😊"
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
        })

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
            chat = create_new_chat_instance()  # Değişiklik burada
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

@app.route('/stream', methods=['POST'])
def stream():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400
        
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"error": "Message required"}), 400

    def generate():
        try:
            # AI yanıtını al
            response = send_ai_message(message, chat)
            text = response.text
            
            # Markdown dönüşümü
            html_content = markdown2.markdown(
                text,
                extras=['fenced-code-blocks', 'tables', 'break-on-newline']
            )
            
            # HTML temizleme
            cleaned_html = bleach.clean(
                html_content,
                tags=['p', 'strong', 'em', 'code', 'pre', 'br', 'a'],
                attributes={'a': ['href']},
                strip=True
            )
            
            # Her karakteri tek tek gönder
            for char in cleaned_html:
                data = {
                    'char': char,
                    'type': 'char'
                }
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(0.02)  # 20ms gecikme
            
            # Yanıt bitti işareti
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
        except Exception as e:
            error_data = {
                'error': str(e),
                'type': 'error'
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

def get_chat_title(messages):
    return TitleManager.get_chat_title(messages)

if __name__ == '__main__':
    app.run(debug=True)