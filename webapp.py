import base64
import cv2
import numpy as np
import pathlib
import platform
import torch
from flask import Flask, jsonify, request, render_template_string

# จัดการ PosixPath สำหรับ Linux บน Render
if platform.system() != 'Windows':
    pathlib.WindowsPath = pathlib.PosixPath

app = Flask(__name__)

# แก้ไขจาก 'ultralytics/yolov5' เป็น '.' และใส่ source='local'
model = torch.hub.load('.', 'custom', path='best.pt', source='local')
model.conf = 0.5  # ตั้งค่า Threshold ความมั่นใจ

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ระบบตรวจจับการลอกคราบปูนา Real-time</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            text-align: center;
            background-color: #121212;
            color: #ffffff;
            margin: 0;
            padding: 20px;
        }
        h1 { color: #00d2ff; }
        .status-box {
            padding: 15px;
            margin: 15px auto;
            width: 80%;
            max-width: 500px;
            border-radius: 10px;
            background-color: #222;
            font-size: 1.2rem;
            font-weight: bold;
            border: 1px solid #444;
        }
        .container {
            position: relative;
            display: inline-block;
            max-width: 100%;
        }
        video, canvas {
            width: 100%;
            max-width: 640px;
            border-radius: 10px;
            border: 2px solid #00d2ff;
        }
        canvas {
            position: absolute;
            top: 0;
            left: 0;
        }
    </style>
</head>
<body>
    <h1>🦀 ระบบตรวจจับการลอกคราบปูนา (Real-time)</h1>
    <div class="status-box" id="statusBox">กำลังโหลดกล้อง...</div>
    
    <div class="container">
        <video id="webcam" autoplay playsinline muted></video>
        <canvas id="outputCanvas"></canvas>
    </div>

    <script>
        const video = document.getElementById('webcam');
        const canvas = document.getElementById('outputCanvas');
        const ctx = canvas.getContext('2d');
        const statusBox = document.getElementById('statusBox');

        navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
            .then(stream => {
                video.srcObject = stream;
                video.onloadedmetadata = () => {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    statusBox.innerText = "สถานะ: กำลังสแกน...";
                    startDetection();
                };
            })
            .catch(err => {
                statusBox.innerText = "ไม่สามารถเปิดกล้องได้: " + err;
                statusBox.style.color = "#ff4d4d";
            });

        function startDetection() {
            const tempCanvas = document.createElement('canvas');
            const tempCtx = tempCanvas.getContext('2d');

            setInterval(() => {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    tempCanvas.width = video.videoWidth;
                    tempCanvas.height = video.videoHeight;
                    tempCtx.drawImage(video, 0, 0);

                    const imageData = tempCanvas.toDataURL('image/jpeg', 0.5);

                    fetch('/detect', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: imageData })
                    })
                    .then(res => res.json())
                    .then(data => {
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        
                        if (data.boxes && data.boxes.length > 0) {
                            statusBox.innerText = `⚠️ พบปูนาลอกคราบ! (${data.boxes.length} ตัว)`;
                            statusBox.style.color = "#ff4d4d";

                            data.boxes.forEach(box => {
                                ctx.strokeStyle = "#00ff00";
                                ctx.lineWidth = 3;
                                ctx.strokeRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1);
                                
                                ctx.fillStyle = "#00ff00";
                                ctx.font = "16px Arial";
                                ctx.fillText(`${box.label} (${Math.round(box.confidence * 100)}%)`, box.x1, box.y1 > 20 ? box.y1 - 5 : 20);
                            });
                        } else {
                            statusBox.innerText = "สถานะ: ปกติ (ไม่พบปูนาที่กำลังลอกคราบ)";
                            statusBox.style.color = "#00d2ff";
                        }
                    })
                    .catch(err => console.error(err));
                }
            }, 300);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/detect', methods=['POST'])
def detect():
    try:
        data = request.get_json()
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # ประมวลผลด้วยโมเดล YOLOv5
        results = model(img)
        df = results.pandas().xyxy[0]
        
        boxes = []
        for _, row in df.iterrows():
            boxes.append({
                'x1': int(row['xmin']),
                'y1': int(row['ymin']),
                'x2': int(row['xmax']),
                'y2': int(row['ymax']),
                'confidence': float(row['confidence']),
                'label': str(row['name'])
            })

        return jsonify({'boxes': boxes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)