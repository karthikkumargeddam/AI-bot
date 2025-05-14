from flask import Flask, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import ollama

app = Flask(__name__, static_folder='.', static_url_path='')
app.config['UPLOAD_FOLDER'] = 'Uploads'
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg'}
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)  # Enable CORS for REST API

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# API health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "API is running"}), 200

# API chat endpoint
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"error": "Missing 'prompt' in request body"}), 400

    user_message = data['prompt'].strip()
    max_tokens = data.get('max_tokens', 256)
    temperature = data.get('temperature', 0.7)

    if not user_message:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    try:
        prompt = f"You are AI Assistant, a helpful assistant with expertise in digital marketing, digital analytics, and Adobe Analytics. Provide concise, accurate, and friendly responses.\nUser: {user_message}"
        response = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': prompt}],
            options={'max_tokens': max_tokens, 'temperature': temperature}
        )
        bot_response = response['message']['content'].strip()
        return jsonify({"response": bot_response}), 200
    except Exception as e:
        return jsonify({"error": f"Error communicating with Ollama: {str(e)}"}), 500

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(data):
    print("Received data:", data)
    user_message = data.get('text', '').strip()
    file_data = data.get('file', None)

    if user_message:
        try:
            prompt = f"You are AI Assistant, a helpful assistant with expertise in digital marketing, digital analytics, and Adobe Analytics. Provide concise, accurate, and friendly responses.\nUser: {user_message}"
            response = ollama.chat(
                model='llama3.2',
                messages=[{'role': 'user', 'content': prompt}]
            )
            bot_response = response['message']['content'].strip()
            print("Sending response:", bot_response)
            emit('response', {'message': bot_response, 'type': 'text'})
        except Exception as e:
            print(f"Error communicating with Ollama: {e}")
            emit('response', {'message': "Error talking to model. Is Ollama running?", 'type': 'text'})

    elif file_data:
        filename = file_data['name']
        if allowed_file(filename):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                with open(file_path, 'wb') as f:
                    f.write(file_data['content'].encode('latin1'))
                if filename.endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    emit('response', {'message': f"Received text file: {filename}. Content: {content}", 'type': 'file'})
                else:
                    emit('response', {'message': f"Received file: {filename}. Stored successfully.", 'type': 'file'})
            except Exception as e:
                print(f"Error handling file: {e}")
                emit('response', {'message': f"Error processing file: {str(e)}", 'type': 'file'})
        else:
            emit('response', {'message': f"Unsupported file type: {filename}. Try txt, pdf, png, jpg, or jpeg.", 'type': 'file'})
    else:
        emit('response', {'message': "Please send a message or upload a file.", 'type': 'text'})

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)