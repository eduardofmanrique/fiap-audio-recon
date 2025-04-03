
from flask import Flask, request, render_template, jsonify, make_response, url_for, redirect, session
import os
import uuid
import base64
from flask_socketio import SocketIO, emit
from rapidfuzz import fuzz
from num2words import num2words
import random
import requests
import azure.cognitiveservices.speech as speechsdk
from datetime import timedelta

SIMILARITY_THRESHOLD = 60  # Definir um mínimo de similaridade aceitável

options_dict = {
    1: {
        "1": "Consulta ao saldo da conta",
        "2": "Simulação de compra internacional",
        "3": "Falar com um atendente",
        "4": "Sair do atendimento",
        "5": "Opção 1",
        "6": "Opção 2",
        "7": "Opção 3",
        "8": "Opção 4",
        "9": "1",
        "10": "2",
        "11": "3",
        "12": "4",
        "13": "um",
        "14": "dois",
        "15": "três",
        "16": "quatro"
    },
    2: {
        "1": "Ouvir opções novamente",
        "2": "Sair do atendimento",
        "3": "Opção 1",
        "4": "Opção 2",
        "5": "1",
        "6": "2",
        "7": "Ouvir opções de novo",
        "8": "Sair"
    }
}

app = Flask(__name__)
socketio = SocketIO(app)

# Set a secret key for session management
app.secret_key = os.urandom(24)

# Set the session lifetime to 15 minutes (900 seconds)
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

def text_to_speech_bytes(text):
    speech_config = speechsdk.SpeechConfig(subscription=session.get('AZURE_SPEECH_KEY',None), region=session.get('AZURE_REGION',None))
    speech_config.speech_synthesis_voice_name = "pt-BR-FranciscaNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()
    return base64.b64encode(result.audio_data).decode("utf-8")

def recognize_speech(audio_bytes):
    speech_config = speechsdk.SpeechConfig(subscription=session.get('AZURE_SPEECH_KEY',None), region=session.get('AZURE_REGION',None))
    audio_config = speechsdk.audio.AudioConfig(filename=audio_bytes)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config, language="pt-BR")
    result = recognizer.recognize_once()
    return result.text if result.reason == speechsdk.ResultReason.RecognizedSpeech else ""

def route_by_similarity(user_input, option):
    options = options_dict[option]
    best_match = max(options.items(), key=lambda x: fuzz.ratio(user_input.lower(), x[1].lower()))
    similarity_score = fuzz.ratio(user_input.lower(), best_match[1].lower())
    print(f"Melhor correspondência: {best_match[1]} com {similarity_score}% de similaridade")
    if similarity_score >= SIMILARITY_THRESHOLD:
        if option == 1:
            if best_match[0] in ["1", "5", "9", "13"]:
                return account_balance()
            elif best_match[0] in ["2", "6", "10", "14"]:
                return international_simulation()
            elif best_match[0] in ["3", "7", "11", "15"]:
                return call_center_agent()
            elif best_match[0] in ["4", "8", "12", "16"]:
                return exit_options()
        elif option == 2:
            if best_match[0] in ["1", "3", "5", "7"]:
                return start_again()
            elif best_match[0] in ["2", "4", "6", "8"]:
                return exit_options()
    return error()

def account_balance():
    saldo = round(random.uniform(50, 5000000), 2)
    saldo_in_text = num2words(int(saldo), lang='pt_BR')
    socketio.emit('message_from_server', {'texto': f'Seu saldo é de {saldo_in_text} reais! Você deseja: Opção 1: Ouvir as opções novamente; Opção 2: Sair do atendimento', 'trigger_record': {"seconds": 4, "option": 2}})

def international_simulation():
    try:
        response = requests.get("https://economia.awesomeapi.com.br/json/last/USD-BRL", timeout=1)
        data = response.json()
        texto_dolar = f'Última cotação disponível para o dólar é de {num2words(float(data["USDBRL"]["bid"]), lang="pt_BR")} reais'
    except Exception as e:
        print(f"Erro ao obter a cotação do dólar: {e}")
        texto_dolar = "Última cotação disponível para o dólar é de 5.5 reais"
    socketio.emit('message_from_server', {'texto': f'{texto_dolar}. Você pode realizar suas compras internacionais agora mesmo com base nessa cotação! Basta utilizar nosso cartão Quantum Global. Você deseja: Opção 1: Ouvir as opções novamente; Opção 2: Sair do atendimento', 'trigger_record': {"seconds": 4, "option": 2}})

def call_center_agent():
    socketio.emit('message_from_server', {'texto': 'Infelizmente, nenhum atendente está disponível no momento! Pedimos desculpas pelo ocorrido... Você deseja: Opção 1: Ouvir as opções novamente; Opção 2: Sair do atendimento', 'trigger_record': {"seconds": 4, "option": 2}})

def exit_options():
    socketio.emit('message_from_server', {'texto': 'A Quantum Finance agradece seu contato! Até logo', 'trigger_record': {"seconds": 0, "option": 1}})

def error():
    socketio.emit('message_from_server', {'texto': 'Não identifiquei nenhuma opção! Você deseja: Opção 1: Ouvir as opções novamente, Opção 2: Sair do atendimento', 'trigger_record': {"seconds": 4, "option": 2}})

def start_again():
    socketio.emit('message_from_server', {'texto': 'Escolha uma das opções: (1) Consulta ao saldo da conta; (2) Simulação de compra internacional; (3) Falar com um atendente; (4) Sair do atendimento', 'trigger_record': {"seconds": 4, "option": 1}})



@app.route('/')
def index():
    return render_template("index.html")

@app.route('/speak', methods=['POST'])
def speak():
    data = request.get_json()
    texto = data.get("texto", "")
    trigger_record = data.get("trigger_record", {"seconds": 0, "option": 1})
    audio_base64 = text_to_speech_bytes(texto)
    return jsonify({"audio_bytes": audio_base64, "trigger_record": trigger_record})

@app.route('/recognize', methods=['POST'])
def recognize():
    data = request.get_json()
    audio_base64 = data.get("audio_bytes", "")
    option = data.get("option", 1)

    if not audio_base64:
        return jsonify({"error": "Nenhum áudio recebido"}), 400

    audio_bytes = base64.b64decode(audio_base64)
    temp_file = f'temp/{uuid.uuid4()}.wav'
    os.makedirs('temp', exist_ok=True)

    with open(temp_file, 'wb') as f:
        f.write(audio_bytes)
    text = recognize_speech(temp_file)
    os.remove(temp_file)
    route_by_similarity(text, option)
    return jsonify({"texto": text})

def validate_azure_credentials(key, region):
    try:
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_synthesis_voice_name = "pt-BR-FranciscaNeural"
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        result = synthesizer.speak_text_async('Olá mundo! isso é uma verificação').get()
        if len(result.audio_data) <= 0:
            return False
        else:
            return True
    except Exception as e:
        print(f"Erro na validação das credenciais: {e}")
        return False


@app.before_request
def check_credentials():

    if request.endpoint == 'login' or request.path.startswith('/static'):
        return None

    AZURE_SPEECH_KEY = session.get('AZURE_SPEECH_KEY', None)
    AZURE_REGION = session.get('AZURE_REGION', None)

    if not AZURE_SPEECH_KEY or not AZURE_REGION:
        # If credentials are not in the cookies, redirect to the login page
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        azure_speech_key = request.form.get('AZURE_SPEECH_KEY')
        azure_region = request.form.get('AZURE_REGION')

        if validate_azure_credentials(azure_speech_key, azure_region):
            session['AZURE_SPEECH_KEY'] = azure_speech_key
            session['AZURE_REGION'] = azure_region
            return redirect(url_for('index'))
        else:
            session['AZURE_SPEECH_KEY'] = None
            session['AZURE_REGION'] = None
            return 'Credenciais inválidas!'
    else:
        return render_template('login.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
