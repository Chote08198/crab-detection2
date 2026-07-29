from flask import Flask, render_template_string, request, jsonify
import cv2
import numpy as np
import torch

app = Flask(__name__)

# โหลดโมเดล YOLOv5 (ปรับ path ตามโครงสร้างของคุณ)
model = torch.hub.load('.', 'custom', path='best.pt', source='local')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ระบบตรวจจับปูนาอัจฉริยะ</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; text-align: center; padding: 20px; }
        .container { background: white; padding: 20px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        video, canvas { width: 100%; max-width: 640px; border-radius: 8px; border: 1px solid #ddd; }
        .status { margin-top: 10px; font-weight: bold; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🦀 ระบบตรวจจับปูนาอัจฉริยะ (AI Monitoring)</h2>
        <p>ระบบประมวลผลและรายงานสถานะแบบเรียลไทม์</p>
        
        <!-- แท็กวิดีโอสำหรับแสดงภาพกล้องจากเครื่องผู้ใช้ -->
        <div>
            <video id="webcam" autoplay playsinline muted></video>
            <canvas id="canvas" style="display:none;"></canvas>
        </div>
        
        <div class="status">สถานะระบบ: <span id="status-text">กำลังขออนุญาตเปิดกล้อง...</span></div>
        <div>จำนวนที่ตรวจพบ: <span id="count">0</span> ตัว</div>
    </div>

    <script>
        const video = document.getElementById('webcam');
        const canvas = document.getElementById('canvas');
        const context = canvas.getContext('2d');
        const statusText = document.getElementById('status-text');
        const countText = document.getElementById('count');

        // 1. เปิดกล้องจากอุปกรณ์ของผู้ใช้งานผ่านเบราว์เซอร์
        navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false })
            .then((stream) => {
                video.srcObject = stream;
                statusText.innerText = "กล้องพร้อมใช้งาน";
                // เริ่มส่งภาพไปประมวลผลทุกๆ 1 วินาที
                setInterval(captureAndSend, 1000);
            })
            .catch((err) => {
                console.error("Error accessing webcam: ", err);
                statusText.innerText = "ไม่พบกล้องหรือไม่อนุญาตให้เข้าถึง";
            });

        // 2. ฟังก์ชันแคปเจอร์ภาพจากหน้าเว็บส่งไปให้ Flask (Python) ประมวลผล
        function captureAndSend() {
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                // แปลงภาพเป็น Base64
                const imageData = canvas.toDataURL('image/jpeg');

                // ส่งภาพไปที่ Backend
                fetch('/process_frame', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: imageData })
                })
                .then(response => response.json())
                .then(data => {
                    countText.innerText = data.count;
                })
                .catch(err => console.error("Error sending frame: ", err));
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.json
        image_data = data['image']
        
        # แปลง Base64 เป็นภาพ OpenCV
        import base64
        encoded_data = image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # นำภาพเข้าโมเดล YOLOv5 เพื่อตรวจจับ
        results = model(img)
        detections = results.pandas().xyxy[0]
        
        # กรองเฉพาะปูนาที่ตรวจพบ (สมมติว่า Class ชื่อ crab หรือปรับตามโมเดลของคุณ)
        crab_count = len(detections)

        return jsonify({'status': 'success', 'count': crab_count})
    except Exception as e:
        print("Error:", e)
        return jsonify({'status': 'error', 'count': 0})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

