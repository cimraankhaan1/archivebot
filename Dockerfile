# Isticmaal Python nooc fudud si uusan culeys u yeelan
FROM python:3.11-slim

# Samee galka shaqada ee server-ka dhexdiisa
WORKDIR /app

# Soo koobiyeey file-ka requirements-ka
COPY requirements.txt .

# Install garee libraries-ka aan u baahanahay
RUN pip install --no-cache-dir -r requirements.txt

# Soo koobiyeey code-ka bot-ka (app.py)
COPY app.py .

# Amarka ugu dambeeya ee lagu kicinayo Bot-ka
CMD ["python", "app.py"]
