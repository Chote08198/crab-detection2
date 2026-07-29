import pathlib
import sys

# แก้ไขปัญหา PosixPath เฉพาะตอนรันบน Windows เท่านั้น
if sys.platform == 'win32':
    temp = pathlib.PosixPath
    pathlib.PosixPath = pathlib.WindowsPath

import cv2
import torch
import numpy as np
from flask import Flask, render_template_string, Response

# โหลดโมเดลแบบออฟไลน์
model = torch.hub.load('.', 'custom', path='best.pt', source='local')
model.eval()

app = Flask(__name__)
# ... (โค้ดส่วนที่เหลือคงเดิม)



# 3. หน้าเว็บไซต์พร้อมระบบเสียงเตือนอัตโนมัติ

HTML_TEMPLATE = """

<!DOCTYPE html>

<html lang="th">

<head>

    <meta charset="UTF-8">

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>ระบบตรวจสอบปูนา Real-Time AI</title>

    <style>

        body {

            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;

            background: linear-gradient(135deg, #74b9ff, #a29bfe);

            margin: 0;

            padding: 20px;

            display: flex;

            flex-direction: column;

            align-items: center;

            min-height: 100vh;

        }

        h1 {

            color: #ffffff;

            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);

            margin-bottom: 5px;

        }

        p {

            color: #f1f2f6;

            font-weight: 500;

        }

        .container {

            display: flex;

            flex-direction: row;

            background: rgba(255, 255, 255, 0.95);

            padding: 25px;

            border-radius: 16px;

            box-shadow: 0 10px 25px rgba(0,0,0,0.2);

            max-width: 950px;

            width: 100%;

            gap: 25px;

            margin-top: 20px;

            backdrop-filter: blur(10px);

        }

        .video-box {

            flex: 1.2;

            text-align: center;

        }

        .video-box h3 {

            color: #2d3436;

            margin-top: 0;

        }

        .video-box img {

            width: 100%;

            border-radius: 12px;

            border: 4px solid #0984e3;

            box-shadow: 0 4px 10px rgba(0,0,0,0.15);

        }

        .status-box {

            flex: 1;

            display: flex;

            flex-direction: column;

            justify-content: center;

            align-items: center;

            padding: 25px;

            background: #dfe6e9;

            border-radius: 12px;

            border: 2px dashed #b2bec3;

        }

        .status-title {

            font-size: 1.2rem;

            color: #636e72;

            font-weight: bold;

            margin-bottom: 15px;

            text-transform: uppercase;

            letter-spacing: 1px;

        }

        #status-text {

            font-size: 2rem;

            font-weight: bold;

            text-align: center;

            padding: 20px;

            border-radius: 12px;

            width: 85%;

            box-shadow: 0 4px 10px rgba(0,0,0,0.1);

            transition: all 0.3s ease;

        }

        #count-text {

            margin-top: 20px;

            color: #2d3436;

            font-size: 1.2rem;

            font-weight: 600;

            background: #ffffff;

            padding: 8px 16px;

            border-radius: 20px;

            box-shadow: 0 2px 5px rgba(0,0,0,0.05);

        }

        .status-none { background-color: #f1f2f6; color: #747d8c; border: 2px solid #ced6e0; }

        .status-normal { background-color: #2ed573; color: #ffffff; }

        .status-molting { background-color: #ff4757; color: #ffffff; animation: pulse 0.8s infinite; }



        @keyframes pulse {

            0% { transform: scale(1); }

            50% { transform: scale(1.05); }

            100% { transform: scale(1); }

        }

    </style>

</head>

<body>

    <h1>🦀 ระบบตรวจจับปูนาอัจฉริยะ (AI Monitoring)</h1>

    <p>ระบบประมวลผลและรายงานสถานะแบบเรียลไทม์ พร้อมระบบเสียงเตือน</p>



    <div class="container">

        <div class="video-box">

            <h3>🎥 ภาพสดจากกล้อง</h3>

            <img src="{{ url_for('video_feed') }}" alt="Video Stream">

        </div>

        <div class="status-box">

            <div class="status-title">สถานะระบบ</div>

            <div id="status-text" class="status-none">กำลังโหลด...</div>

            <div id="count-text">จำนวนที่ตรวจพบ: 0 ตัว</div>

        </div>

    </div>



    <script>

        // สร้างระบบเสียงเตือนด้วย Web Audio API (ไม่ต้องใช้ไฟล์เสียงภายนอก)

        let audioCtx = null;



        function playAlarmSound() {

            if (!audioCtx) {

                audioCtx = new (window.AudioContext || window.webkitAudioContext)();

            }

            if (audioCtx.state === 'suspended') {

                audioCtx.resume();

            }



            // สร้างเสียงปี๊บความถี่สูงดังชัดเจน

            let osc = audioCtx.createOscillator();

            let gainNode = audioCtx.createGain();



            osc.type = 'square'; // เสียงแบบปี๊บแหลมดังฟังชัด

            osc.frequency.setValueAtTime(800, audioCtx.currentTime); // ความถี่เสียง



            gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);

           

            osc.connect(gainNode);

            gainNode.connect(audioCtx.destination);



            osc.start();

            osc.stop(audioCtx.currentTime + 0.3); // ดังครั้งละ 0.3 วินาที

        }



        // เช็คสถานะทุกๆ 1 วินาที

        setInterval(function() {

            fetch('/status')

                .then(response => response.json())

                .then(data => {

                    const statusEl = document.getElementById('status-text');

                    const countEl = document.getElementById('count-text');

                   

                    statusEl.innerText = data.text;

                    countEl.innerText = "จำนวนที่ตรวจพบ: " + data.count + " ตัว";

                    statusEl.className = "status-" + data.type;



                    // ถ้าเจอสถานะลอกคราบ (2 ตัวขึ้นไป) ให้ส่งเสียงเตือนดังๆ

                    if (data.type === 'molting') {

                        playAlarmSound();

                    }

                });

        }, 1000);

    </script>

</body>

</html>

"""



latest_status = {"text": "ไม่เจอ", "count": 0, "type": "none"}



def generate_frames():

    global latest_status

    cap = cv2.VideoCapture(0)

   

    while cap.isOpened():

        success, frame = cap.read()

        if not success:

            break

           

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = model(img_rgb)

        df = results.pandas().xyxy[0]

       

        filtered_df = df[df['confidence'] > 0.4]

        count = len(filtered_df)

       

        if count == 0:

            latest_status = {"text": "ไม่เจอ", "count": 0, "type": "none"}

        elif count == 1:

            latest_status = {"text": "ปกติ", "count": 1, "type": "normal"}

        else:

            latest_status = {"text": "เจอปูนาลอกคราบ", "count": count, "type": "molting"}



        for i, row in filtered_df.iterrows():

            xmin, ymin, xmax, ymax = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])

            name = row['name']

            conf = row['confidence']

           

            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)

            cv2.putText(frame, f"{name} {conf:.2f}", (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)



        ret, buffer = cv2.imencode('.jpg', frame)

        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'

               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')



    cap.release()



@app.route('/')

def index():

    return render_template_string(HTML_TEMPLATE)



@app.route('/video_feed')

def video_feed():

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')



@app.route('/status')

def status():

    global latest_status

    return latest_status



if __name__ == '__main__':

    print("กำลังเปิดเว็บเซิร์ฟเวอร์... กรุณาเปิดเบราว์เซอร์ไปที่ http://127.0.0.1:5000")

    app.run(host='0.0.0.0', port=5000, debug=False) 

