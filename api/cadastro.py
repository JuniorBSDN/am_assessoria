from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

if not firebase_admin._apps:
    try:
        firebase_json = os.environ.get("FIREBASE_CREDENTIALS")
        if firebase_json:
            cred_dict = json.loads(firebase_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase conectado com sucesso")
        else:
            print("❌ A variável de ambiente FIREBASE_CREDENTIALS não está definida.")
    except Exception as e:
        print("❌ Erro ao inicializar Firebase:", e)

db = firestore.client()
colecao = 'contatos'

def enviar_email_cadastro(dados_cadastro):
    sender_email = os.environ.get("EMAIL_USER")
    sender_password = os.environ.get("EMAIL_PASS")
    receiver_email = os.environ.get("EMAIL_RECEIVER")

    if not all([sender_email, sender_password, receiver_email]):
        print("❌ Variáveis de ambiente de e-mail não definidas (EMAIL_USER, EMAIL_PASS, EMAIL_RECEIVER).")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "Novo Cadastro Recebido!"

    body = f"""
    Um novo cadastro foi registrado no sistema.

    Detalhes do CLIENTE:
    --------------------
    """
    for key, value in dados_cadastro.items():
        # A correção está aqui: firestore.SERVER_TIMESTAMP é um valor, não um tipo.
        # Deve-se comparar com '==' em vez de usar isinstance().
        if key == 'dataEnvio' and value == firestore.SERVER_TIMESTAMP:
            body += f"{key}: (Definido pelo Servidor Firestore)\n"
        else:
            body += f"{key}: {value}\n"

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print("✅ E-mail de cadastro enviado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail de cadastro: {e}")
        return False

@app.route("/api/cadastro", methods=["POST"])
def receber_cadastro():
    try:
        dados = request.json
        if not dados:
            return jsonify({"status": "erro", "mensagem": "Nenhum dado JSON fornecido"}), 400

        dados['dataEnvio'] = firestore.SERVER_TIMESTAMP
        doc_ref = db.collection(colecao).add(dados)
        enviar_email_cadastro(dados.copy())

        return jsonify({"status": "sucesso", "id": doc_ref[1].id}), 201
    except Exception as e:
        print("❌ Erro ao salvar cadastro:", e)
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
