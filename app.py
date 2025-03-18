import cv2
import numpy as np
import time
import random
import threading
import os
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify
from werkzeug.utils import secure_filename

# =========== NEURAL NET INITIALIZATION ===========
print("[INITIALIZING] NightCity Security Protocol v2.077")

config_path = os.path.abspath("yolov3_testing.cfg")
weights_path = os.path.abspath("yolov3_training_2000.weights")

net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
classes = ["Threat-Object"]
output_layer_names = net.getUnconnectedOutLayersNames()

# Cyberpunk color scheme - neon colors
NEON_COLORS = [
    (0, 255, 255),    # Cyan
    (255, 0, 255),    # Magenta
    (0, 255, 0),      # Green
    (255, 191, 0),    # Yellow
    (0, 140, 255)     # Orange
]
colors = np.array(NEON_COLORS)

# Global variables
detection_active = False
scan_line_pos = 0
threat_count = 0
last_detection_time = 0
cap = None

# Fixed dimensions for video display
DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480

# Create Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'mp4', 'avi'}

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# =========== DETECTION ENGINE ===========
def detect_objects(image):
    global threat_count, last_detection_time, scan_line_pos
    
    # Resize image to fixed display size
    image = cv2.resize(image, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
    height, width, channels = image.shape
    original = image.copy()

    # Add cyberpunk overlay - grid lines
    for x in range(0, width, 50):
        cv2.line(image, (x, 0), (x, height), (20, 20, 20), 1)
    for y in range(0, height, 50):
        cv2.line(image, (0, y), (width, y), (20, 20, 20), 1)
    
    # Add scanning effect
    scan_line_pos = (scan_line_pos + 5) % height
    cv2.line(image, (0, scan_line_pos), (width, scan_line_pos), (0, 255, 255), 1)
    
    # Detecting objects
    blob = cv2.dnn.blobFromImage(original, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layer_names)

    # Information analysis
    class_ids = []
    confidences = []
    boxes = []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:
                # Object detected
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)

                # Rectangle coordinates
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    if len(indexes) > 0:
        threat_count += 1
        last_detection_time = time.time()
        print("[ALERT] Threat object detected | Confidence level: HIGH")
        
    # Draw current time
    current_time = datetime.now().strftime("%H:%M:%S")
    cv2.putText(image, f"TIME: {current_time}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    # Draw threat counter
    cv2.putText(image, f"THREATS IDENTIFIED: {threat_count}", (width - 280, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    # Draw targeting boxes
    font = cv2.FONT_HERSHEY_SIMPLEX
    for i in range(len(boxes)):
        if i in indexes:
            x, y, w, h = boxes[i]
            color_index = random.randint(0, len(NEON_COLORS)-1)
            color = NEON_COLORS[color_index]
            confidence_text = f"{confidences[i]:.2f}"
            
            # Draw main box with glitch effect
            cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            
            # Draw corner brackets
            bracket_length = 20
            # Top-left
            cv2.line(image, (x, y), (x + bracket_length, y), color, 2)
            cv2.line(image, (x, y), (x, y + bracket_length), color, 2)
            # Top-right
            cv2.line(image, (x + w, y), (x + w - bracket_length, y), color, 2)
            cv2.line(image, (x + w, y), (x + w, y + bracket_length), color, 2)
            # Bottom-left
            cv2.line(image, (x, y + h), (x + bracket_length, y + h), color, 2)
            cv2.line(image, (x, y + h), (x, y + h - bracket_length), color, 2)
            # Bottom-right
            cv2.line(image, (x + w, y + h), (x + w - bracket_length, y + h), color, 2)
            cv2.line(image, (x + w, y + h), (x + w, y + h - bracket_length), color, 2)
            
            # Add targeting data
            cv2.putText(image, f"THREAT", (x, y - 10), font, 0.7, color, 2)
            cv2.putText(image, f"CFD: {confidence_text}", (x, y + h + 25), font, 0.6, color, 2)
            
            # Add glitch effect near the detected object
            if random.random() < 0.2:  # 20% chance of glitch
                glitch_x = x + random.randint(-20, 20)
                glitch_y = y + random.randint(-20, 20)
                glitch_w = random.randint(5, 20)
                glitch_h = random.randint(5, 10)
                cv2.rectangle(image, (glitch_x, glitch_y), 
                             (glitch_x + glitch_w, glitch_y + glitch_h), 
                             color, -1)
    
    # Add threat warning
    if time.time() - last_detection_time < 3:  # Show warning for 3 seconds after detection
        warning_text = "! THREAT DETECTED !"
        text_size = cv2.getTextSize(warning_text, font, 1, 2)[0]
        text_x = (width - text_size[0]) // 2
        
        if random.random() < 0.5:  # Flashing effect
            cv2.putText(image, warning_text, (text_x, height - 50), 
                        font, 1, (0, 0, 255), 2)
            
            # Add semi-transparent red overlay
            overlay = image.copy()
            cv2.rectangle(overlay, (0, 0), (width, height), (40, 0, 0), -1)
            cv2.addWeighted(overlay, 0.2, image, 0.8, 0, image)
    
    return image

# =========== VIDEO STREAMING FUNCTIONS ===========
def gen_empty_frame():
    """Generate an empty initialization frame"""
    empty_image = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype=np.uint8)
    empty_image.fill(20)  # Dark gray
    
    # Add grid lines
    for x in range(0, DISPLAY_WIDTH, 50):
        cv2.line(empty_image, (x, 0), (x, DISPLAY_HEIGHT), (40, 40, 40), 1)
    for y in range(0, DISPLAY_HEIGHT, 50):
        cv2.line(empty_image, (0, y), (DISPLAY_WIDTH, y), (40, 40, 40), 1)
    
    # Add startup text
    cv2.putText(empty_image, "NEXUS-77 READY", (DISPLAY_WIDTH//2 - 100, DISPLAY_HEIGHT//2), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    
    ret, buffer = cv2.imencode('.jpg', empty_image)
    frame = buffer.tobytes()
    return (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def gen_camera_frames():
    """Generate camera frames for streaming"""
    global cap, detection_active
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    detection_active = True
    
    while detection_active:
        success, frame = cap.read()
        if not success:
            break
        else:
            # Process the frame
            processed_frame = detect_objects(frame)
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    # Clean up
    if cap is not None:
        cap.release()

def gen_video_frames(video_path):
    """Generate video frames for streaming from a file"""
    global cap, detection_active
    
    # Initialize video file
    cap = cv2.VideoCapture(video_path)
    detection_active = True
    
    while detection_active:
        success, frame = cap.read()
        if not success:
            # End of video
            detection_active = False
            break
        else:
            # Process the frame
            processed_frame = detect_objects(frame)
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.04)  # Control frame rate to roughly 25 fps
    
    # Clean up
    if cap is not None:
        cap.release()

def gen_image_frame(image_path):
    """Generate a single processed image frame"""
    global detection_active
    
    image = cv2.imread(image_path)
    if image is None:
        # Create an error frame
        image = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype=np.uint8)
        cv2.putText(image, "ERROR: CANNOT LOAD IMAGE", (DISPLAY_WIDTH//2 - 150, DISPLAY_HEIGHT//2), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    else:
        # Process the image
        image = detect_objects(image)
    
    ret, buffer = cv2.imencode('.jpg', image)
    frame = buffer.tobytes()
    return (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# =========== FLASK ROUTES ===========
@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route for the main feed"""
    return Response(gen_empty_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_camera')
def start_camera():
    """Start camera streaming"""
    # First ensure any existing stream is stopped
    stop_detection()
    return Response(gen_camera_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/upload_file', methods=['POST'])
def upload_file():
    """Handle file uploads (images or videos)"""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Determine if it's an image or video based on extension
        ext = filename.rsplit('.', 1)[1].lower()
        file_type = 'image' if ext in ['png', 'jpg', 'jpeg'] else 'video'
        
        return jsonify({
            'status': 'success', 
            'message': 'File uploaded successfully',
            'file_path': file_path,
            'file_type': file_type
        })
    
    return jsonify({'status': 'error', 'message': 'File type not allowed'})

@app.route('/process_image')
def process_image():
    """Process and stream a single image"""
    file_path = request.args.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return Response(gen_empty_frame(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    
    return Response(gen_image_frame(file_path),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/process_video')
def process_video():
    """Process and stream a video file"""
    # First ensure any existing stream is stopped
    stop_detection()
    
    file_path = request.args.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return Response(gen_empty_frame(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    
    return Response(gen_video_frames(file_path),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_detection')
def stop_detection():
    """Stop any active detection and release resources"""
    global detection_active, cap
    detection_active = False
    
    # Wait a bit to ensure the streaming loop has time to exit
    time.sleep(0.1)
    
    if cap is not None:
        cap.release()
        cap = None
    
    return jsonify({'status': 'success', 'message': 'Detection stopped'})

@app.route('/get_stats')
def get_stats():
    """Get current threat detection stats"""
    return jsonify({
        'threat_count': threat_count,
        'detection_active': detection_active,
        'time': datetime.now().strftime("%H:%M:%S")
    })

# HTML template in a string - will be saved to templates folder
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS-77 THREAT DETECTION SYSTEM</title>
    <style>
        body {
            background-color: #1a1a2e;
            color: #00ffff;
            font-family: 'Courier New', monospace;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        h1 {
            color: #ff00ff;
            text-align: center;
            margin-bottom: 20px;
        }
        
        .container {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
            max-width: 800px;
        }
        
        .video-container {
            border: 2px solid #00ffff;
            margin: 20px 0;
            position: relative;
            width: 640px;
            height: 480px;
            overflow: hidden;
        }
        
        .video-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .status-bar {
            background-color: rgba(0, 0, 0, 0.7);
            color: #00ffff;
            padding: 10px;
            margin: 10px 0;
            width: 100%;
            text-align: center;
            border: 1px solid #00ffff;
        }
        
        .button-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            margin: 20px 0;
        }
        
        .cyber-button {
            background-color: #0f0f1a;
            color: #00ffff;
            border: 1px solid #00ffff;
            padding: 10px 20px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .cyber-button:hover {
            background-color: #2d2d44;
            color: #ff00ff;
            box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
        }
        
        .terminate-button {
            background-color: #5a0000;
            color: #ff0000;
            border: 1px solid #ff0000;
            margin-top: 20px;
        }
        
        .terminate-button:hover {
            background-color: #8a0000;
            color: #ff3333;
            box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
        }
        
        .file-input {
            display: none;
        }
        
        .file-label {
            display: inline-block;
            padding: 10px 20px;
            background-color: #0f0f1a;
            color: #00ffff;
            border: 1px solid #00ffff;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .file-label:hover {
            background-color: #2d2d44;
            color: #ff00ff;
            box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
        }
        
        @keyframes scanline {
            0% {
                transform: translateY(0);
            }
            100% {
                transform: translateY(480px);
            }
        }
        
        .scanline {
            position: absolute;
            width: 100%;
            height: 2px;
            background-color: rgba(0, 255, 255, 0.5);
            animation: scanline 3s linear infinite;
            pointer-events: none;
        }
        
        .loading {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10;
            flex-direction: column;
        }
        
        .loading-text {
            color: #00ffff;
            margin-top: 20px;
            font-size: 18px;
        }
        
        .lds-ring {
            display: inline-block;
            position: relative;
            width: 80px;
            height: 80px;
        }
        
        .lds-ring div {
            box-sizing: border-box;
            display: block;
            position: absolute;
            width: 64px;
            height: 64px;
            margin: 8px;
            border: 8px solid #00ffff;
            border-radius: 50%;
            animation: lds-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
            border-color: #00ffff transparent transparent transparent;
        }
        
        .lds-ring div:nth-child(1) {
            animation-delay: -0.45s;
        }
        
        .lds-ring div:nth-child(2) {
            animation-delay: -0.3s;
        }
        
        .lds-ring div:nth-child(3) {
            animation-delay: -0.15s;
        }
        
        @keyframes lds-ring {
            0% {
                transform: rotate(0deg);
            }
            100% {
                transform: rotate(360deg);
            }
        }
        
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>NEXUS-77 THREAT DETECTION SYSTEM</h1>
        
        <div class="video-container">
            <img id="video-feed" src="{{ url_for('video_feed') }}" alt="Video Feed">
            <div class="scanline"></div>
            <div id="loading" class="loading hidden">
                <div class="lds-ring"><div></div><div></div><div></div><div></div></div>
                <div id="loading-text" class="loading-text">INITIALIZING...</div>
            </div>
        </div>
        
        <div id="status-bar" class="status-bar">[STANDBY] System ready</div>
        
        <div class="button-container">
            <input type="file" id="image-upload" class="file-input" accept="image/*">
            <label for="image-upload" class="file-label">SCAN IMAGE</label>
            
            <input type="file" id="video-upload" class="file-input" accept="video/*">
            <label for="video-upload" class="file-label">SCAN VIDEO</label>
            
            <button id="camera-button" class="cyber-button">LIVE SCAN</button>
            <button id="stop-button" class="cyber-button">STOP SCAN</button>
        </div>
        
        <button id="terminate-button" class="cyber-button terminate-button">TERMINATE SYSTEM</button>
    </div>
    
    <script>
        // Global variables
        let currentMode = 'standby';
        let stats = {
            threat_count: 0,
            detection_active: false
        };
        
        // Function to show loading state
        function showLoading(message) {
            document.getElementById('loading').classList.remove('hidden');
            document.getElementById('loading-text').textContent = message;
        }
        
        // Function to hide loading state
        function hideLoading() {
            document.getElementById('loading').classList.add('hidden');
        }
        
        // Function to update status bar
        function updateStatus(status) {
            document.getElementById('status-bar').textContent = status;
        }
        
        // Function to upload a file
        async function uploadFile(file, type) {
            const formData = new FormData();
            formData.append('file', file);
            
            showLoading(`UPLOADING ${type.toUpperCase()}...`);
            
            try {
                const response = await fetch('/upload_file', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    return data;
                } else {
                    throw new Error(data.message);
                }
            } catch (error) {
                updateStatus(`[ERROR] ${error.message}`);
                hideLoading();
                return null;
            }
        }
        
        // Initialize components
        document.addEventListener('DOMContentLoaded', function() {
            // Run startup sequence
            const startupMessages = [
                "[BOOT] NEXUS-77 Security Protocol...",
                "[INIT] Loading neural network...",
                "[LOAD] Calibrating optical sensors...",
                "[PING] Connecting to mainframe...",
                "[AUTH] Security clearance verified...",
                "[READY] Threat detection online."
            ];
            
            let messageIndex = 0;
            const statusInterval = setInterval(() => {
                updateStatus(startupMessages[messageIndex]);
                messageIndex++;
                
                if (messageIndex >= startupMessages.length) {
                    clearInterval(statusInterval);
                    setTimeout(() => {
                        updateStatus("[STANDBY] System ready");
                    }, 1000);
                }
            }, 500);
            
            // Image upload handler
            document.getElementById('image-upload').addEventListener('change', async function(event) {
                const file = event.target.files[0];
                if (!file) return;
                
                const result = await uploadFile(file, 'image');
                if (result) {
                    updateStatus("[SCANNING] Processing image...");
                    
                    // Update video source to processed image
                    const videoFeed = document.getElementById('video-feed');
                    videoFeed.src = `/process_image?file_path=${encodeURIComponent(result.file_path)}`;
                    
                    hideLoading();
                    setTimeout(() => {
                        updateStatus("[COMPLETE] Image analysis finished");
                    }, 1000);
                }
            });
            
            // Video upload handler
            document.getElementById('video-upload').addEventListener('change', async function(event) {
                const file = event.target.files[0];
                if (!file) return;
                
                const result = await uploadFile(file, 'video');
                if (result) {
                    updateStatus("[SCANNING] Processing video feed...");
                    
                    // Update video source to processed video
                    const videoFeed = document.getElementById('video-feed');
                    videoFeed.src = `/process_video?file_path=${encodeURIComponent(result.file_path)}`;
                    currentMode = 'video';
                    
                    hideLoading();
                }
            });
            
            // Camera button handler
            document.getElementById('camera-button').addEventListener('click', function() {
                showLoading("ACTIVATING OPTICAL SENSORS...");
                updateStatus("[LIVE] Activating optical sensors...");
                
                // Update video source to camera feed
                const videoFeed = document.getElementById('video-feed');
                videoFeed.src = '/start_camera';
                currentMode = 'camera';
                
                setTimeout(() => {
                    hideLoading();
                }, 1000);
            });
            
            // Stop button handler
            document.getElementById('stop-button').addEventListener('click', async function() {
                if (currentMode === 'standby') return;
                
                updateStatus("[STOPPING] Ending detection...");
                
                try {
                    await fetch('/stop_detection');
                    const videoFeed = document.getElementById('video-feed');
                    videoFeed.src = "{{ url_for('video_feed') }}";
                    currentMode = 'standby';
                    updateStatus("[STANDBY] System idle");
                } catch (error) {
                    updateStatus("[ERROR] Failed to stop detection");
                }
            });
            
            // Terminate button handler
            document.getElementById('terminate-button').addEventListener('click', async function() {
                if (currentMode !== 'standby') {
                    try {
                        await fetch('/stop_detection');
                    } catch (error) {
                        console.error("Failed to stop detection:", error);
                    }
                }
                
                updateStatus("[SHUTDOWN] Terminating system...");
                
                setTimeout(() => {
                    showLoading("SYSTEM TERMINATION IN PROGRESS...");
                    
                    setTimeout(() => {
                        window.location.href = "/";
                    }, 2000);
                }, 500);
            });
            
            // Periodic stats update
            setInterval(async () => {
                if (currentMode !== 'standby') {
                    try {
                        const response = await fetch('/get_stats');
                        stats = await response.json();
                    } catch (error) {
                        console.error("Failed to fetch stats:", error);
                    }
                }
            }, 1000);
        });
    </script>
</body>
</html>
"""

# Ensure the templates directory exists
os.makedirs('templates', exist_ok=True)

# Write the HTML template to a file
with open('templates/index.html', 'w') as f:
    f.write(HTML_TEMPLATE)

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)