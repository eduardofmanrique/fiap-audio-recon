from flask import Flask, request, render_template, jsonify
import pyttsx3
import os
import uuid
import speech_recognition as sr
import base64
from flask_socketio import SocketIO, emit
from rapidfuzz import fuzz
from num2words import num2words
import random
import requests

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
socketio = SocketIO(app)  # Inicializa o SocketIO com o app Flask


def text_to_speech_bytes(text):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        if "brazil" in voice.id.lower() or "portuguese" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    temp_file = f'temp/{uuid.uuid4()}.wav'
    os.makedirs('temp', exist_ok=True)
    engine.save_to_file(text, temp_file)
    engine.runAndWait()

    with open(temp_file, 'rb') as f:
        audio_bytes = f.read()
    if os.path.exists(temp_file):
        os.remove(temp_file)
    return base64.b64encode(audio_bytes).decode('utf-8')

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
    socketio.emit('message_from_server', {'texto': f'Seu saldo é de {saldo_in_text} reais! Você deseja? Opção 1: Ouvir as opções novamente, Opção 2: Sair do atendimento', 'trigger_record': {"seconds": 4, "option": 2}})

def international_simulation():

    try:
        response = requests.get("https://economia.awesomeapi.com.br/json/last/USD-BRL", timeout=1)
        data = response.json()
        texto_dolar = f'Última cotação disponível para o dólar é de {num2words(float(data["USDBRL"]["bid"]), lang="pt_BR")} reais'
    except Exception as e:
        print(f"Erro ao obter a cotação do dólar: {e}")
        texto_dolar = "Última cotação disponível para o dólar é de 5.5 reais"
    socketio.emit('message_from_server', {'texto': f'{texto_dolar}. Você pode realizar suas compras internacionais agora mesmo com base nessa cotação! Basta utilizar nosso cartão Quantum Global. Você deseja? Opção 1: Ouvir as opções novamente, Opção 2: Sair do atendimento', 'trigger_record': {"seconds": 4, "option": 2}})

def call_center_agent():
    socketio.emit('message_from_server', {'texto': 'Infelizmente, nenhum atendente está disponível no momento! Pedimos desculpas pelo ocorrido... Você deseja? Opção 1: Ouvir as opções novamente, Opção 2: Sair do atendimento', 'trigger_record': {"seconds": 4, "option": 2}})

def exit_options():
    socketio.emit('message_from_server', {'texto': 'A Quantum Finance agradece seu contato! Até logo', 'trigger_record': {"seconds": 0, "option": 1}})

def error():
    socketio.emit('message_from_server', {'texto': 'Não identifiquei nenhuma opção! Você deseja? Opção 1: Ouvir as opções novamente, Opção 2: Sair do atendimento', 'trigger_record': {"seconds": 4, "option": 2}})

def start_again():
    socketio.emit('message_from_server', {'texto': 'Escolha uma das opções: (1) Consulta ao saldo da conta, (2) Simulação de compra internacional, (3) Falar com um atendente, (4) Sair do atendimento', 'trigger_record': {"seconds": 4, "option": 1}})



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

    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="pt-BR")

        # Após a transcrição, enviar o texto para o WebSocket
        route_by_similarity(text, option)

        os.remove(temp_file)
        return jsonify({"texto": text})

    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)

        error()

        return jsonify({"error": "Falha ao transcrever áudio", "detalhes": str(e)}), 500


# Evento WebSocket para quando um cliente se conecta
@socketio.on('connect')
def handle_connect():
    print("Cliente conectado via WebSocket")


if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
