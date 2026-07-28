import pathlib
import platform
import cv2
from flask import Flask, Response, render_template_string
import torch

import sys

if platform.system() == "Windows":
    pathlib.PosixPath = pathlib.WindowsPath
else:
    pathlib.WindowsPath = pathlib.PosixPath

# โหลดโมเดล AI
import torch

# โหลดโมเดล YOLOv5 จาก PyTorch Hub แบบออฟไลน์/ออนไลน์ที่เสถียร
model = torch.hub.load('ultralytics/yolov5:v7.0', 'custom', path='best.pt', force_reload=True)
model.conf = 0.5  # ค่าความมั่นใจในการตรวจจับ (ปรับขึ้นลงได้ตามต้องการ)

app = Flask(__name__)
cap = cv2.VideoCapture(0)  # ถ้ากล้องไม่ขึ้น ให้เปลี่ยนเป็น 1

# ตัวแปรนับจำนวนปูที่กำลังลอกคราบ
molting_count = 0

# หน้าเว็บระบบตรวจจับและแจ้งเตือนตามจำนวนปู
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ระบบตรวจจับการลอกคราบปูนา</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background-color: #121212; color: #fff; padding: 20px; }
        h1 { color: #00d2ff; }
        
        .alert-box {
            padding: 15px;
            margin: 15px auto;
            width: 65%;
            border-radius: 10px;
            font-size: 22px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        /* สถานะไม่พบการลอกคราบ */
        .status-none { background-color: #333333; color: #aaaaaa; }
        /* สถานะพบ 1 ตัว (สีเขียว) */
        .status-one { background-color: #2e7d32; color: #ffffff; }
        /* สถานะพบ 2 ตัวขึ้นไป (สีแดงกระพริบ) */
        .status-many { background-color: #d32f2f; color: #ffffff; animation: blink 0.8s infinite; }
        
        @keyframes blink {
            0% { opacity: 1.0; }
            50% { opacity: 0.3; }
            100% { opacity: 1.0; }
        }

        .video-container { display: inline-block; background: #1e1e1e; padding: 15px; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.5); }
        img { border-radius: 8px; width: 640px; height: 480px; object-fit: cover; }
    </style>
</head>
<body>
    <h1>🦀 ระบบตรวจจับและแจ้งเตือนการลอกคราบปูนา</h1>
    
    <div id="alertBanner" class="alert-box status-none">
        สถานะ: ไม่พบปูนาที่กำลังลอกคราบ
    </div>

    <div class="video-container">
        <img src="{{ url_for('video_feed') }}">
    </div>

    <audio id="alarmSound" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>

    <script>
        setInterval(function() {
            fetch('/check_status')
                .then(response => response.json())
                .then(data => {
                    const banner = document.getElementById('alertBanner');
                    const sound = document.getElementById('alarmSound');
                    
                    if (data.count === 0) {
                        banner.className = 'alert-box status-none';
                        banner.innerText = 'สถานะ: ปกติ (ไม่พบปูนาที่กำลังลอกคราบ)';
                    } else if (data.count === 1) {
                        banner.className = 'alert-box status-one';
                        banner.innerText = '✅ ตรวจพบปูนากำลังลอกคราบจำนวน 1 ตัว';
                    } else if (data.count >= 2) {
                        banner.className = 'alert-box status-many';
                        banner.innerText = '🚨 เตือนภัยด่วน! ตรวจพบปูนากำลังลอกคราบ ' + data.count + ' ตัว!';
                        sound.play().catch(e => console.log("คลิกที่หน้าเว็บ 1 ครั้งเพื่ออนุญาตให้ส่งเสียง"));
                    }
                });
        }, 800);
    </script>
</body>
</html>
"""


def generate_frames():
  global molting_count
  while True:
    success, frame = cap.read()
    if not success:
      break
    else:
      results = model(frame)

      # ดึงชื่อคลาสทั้งหมดที่ AI ตรวจจับได้ในเฟรมนี้
      labels = results.pandas().xyxy[0]["name"].tolist()

      # นับทั้ง crab, molt หรือวัตถุทั้งหมดที่ AI ตรวจจับได้
      count = sum(
          1
          for label in labels
          if "crab" in label.lower()
          or "molt" in label.lower()
          or "ลอกคราบ" in label.lower()
      )

      molting_count = count

      rendered_frame = results.render()[0]
      ret, buffer = cv2.imencode(".jpg", rendered_frame)
      frame_bytes = buffer.tobytes()

      yield (
          b"--frame\r\n"
          b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
      )

      yield (
          b"--frame\r\n"
          b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
      )


@app.route("/")
def index():
  return render_template_string(HTML_TEMPLATE)


@app.route("/video_feed")
def video_feed():
  return Response(
      generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
  )


@app.route("/check_status")
def check_status():
  return {"count": molting_count}


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)