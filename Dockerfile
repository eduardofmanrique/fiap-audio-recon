FROM python:3.9

# Instala pacotes do sistema necessários
RUN apt-get update && apt-get install -y \
    espeak \
    ffmpeg \
    libespeak1 \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia os arquivos necessários para o contêiner
COPY . /app

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Exposição da porta do Flask
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "main:app"]

