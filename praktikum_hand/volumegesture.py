import cv2
import mediapipe as mp
import math
import numpy as np
#Import untuk pengontrol audio Windows tingkat rendah
import comtypes
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL, GUID
from pycaw.pycaw import IAudioEndpointVolume, IMMDeviceEnumerator

#fungsi hitung sudut jari
def calculate_angle(a, b, c):
    radians = math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(a[1] - b[1], a[0] - b[0])
    angle = abs(radians * 180.0 / math.pi)
    if angle > 180.0:
        angle = 360.0 - angle
    return angle

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7, 
    min_tracking_confidence=0.5
)

#INISIALISASI VOLUME WINDOWS TINGKAT RENDAH 
CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
deviceEnumerator = comtypes.CoCreateInstance(
    CLSID_MMDeviceEnumerator,
    IMMDeviceEnumerator, 
    comtypes.CLSCTX_INPROC_SERVER
)
speakers = deviceEnumerator.GetDefaultAudioEndpoint(0, 1)
interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))

#Rentang Volume 
volRange = volume.GetVolumeRange()
minVol, maxVol = volRange[0], volRange[1]
volBar, volPer = 400, 0

cap = cv2.VideoCapture(0)

print("SISTEM KONTROL GESTUR + TUGAS MODUL AKTIF!")

while cap.isOpened():
    success, frame = cap.read()
    if not success: 
        break
        
    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    results = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            lm = hand_landmarks.landmark
            
            #HITUNG SUDUT JARI TELUNJUK
            #Mengambil koordinat titik 5 (MCP), 6 (PIP), dan 8 (TIP)
            pt5 = (int(lm[5].x * w), int(lm[5].y * h))
            pt6 = (int(lm[6].x * w), int(lm[6].y * h))
            pt8 = (int(lm[8].x * w), int(lm[8].y * h))
            
            #Hitung sudut menggunakan fungsi calculate_angle
            index_angle = calculate_angle(pt5, pt6, pt8)
            
            #Tampilkan nilai sudut telunjuk ke layar utama
            cv2.putText(frame, f"Sudut Telunjuk: {int(index_angle)} deg", (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            #LOGIKA UTAMA: JARAK JEMPOL & TELUNJUK (CUBITAN)
            x1, y1 = int(lm[4].x * w), int(lm[4].y * h)
            x2, y2 = int(lm[8].x * w), int(lm[8].y * h)
            jarak = int(math.hypot(x2 - x1, y2 - y1))
            
            #GESTUR MUTE OTOMATIS (KELINGKING LURUS)
            #Cek jika ujung kelingking (20) lebih tinggi dari sendi tengahnya (18)
            kelingking_lurus = lm[20].y < lm[18].y
            
            if kelingking_lurus:
                #Set volume Windows ke minimum secara paksa
                volume.SetMasterVolumeLevel(minVol, None)
                volBar = 400
                volPer = 0
                cv2.putText(frame, "STATUS: MUTE (KELINGKING LURUS)", (20, 130),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                #Jika kelingking normal, kontrol volume kembali menggunakan cubitan jempol-telunjuk
                vol = np.interp(jarak, [20, 150], [minVol, maxVol])
                volBar = np.interp(jarak, [20, 150], [400, 150])
                volPer = np.interp(jarak, [20, 150], [0, 100])
                volume.SetMasterVolumeLevel(vol, None)
            
            #Visualisasi jari
            cv2.circle(frame, (x1, y1), 8, (255, 0, 255), cv2.FILLED)
            cv2.circle(frame, (x2, y2), 8, (255, 0, 255), cv2.FILLED)
            cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)
            
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            if jarak < 30 and not kelingking_lurus: 
                cv2.circle(frame, (cx, cy), 10, (0, 255, 0), cv2.FILLED)
                
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
    #Menampilkan UI Bar Volume 
    cv2.putText(frame, "PROJECT: fahri", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.rectangle(frame, (50, 150), (85, 400), (0, 255, 0), 3)
    cv2.rectangle(frame, (50, int(volBar)), (85, 400), (0, 255, 0), cv2.FILLED)
    cv2.putText(frame, f"{int(volPer)} %", (40, 440), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    
    cv2.imshow('project fahri Hand Gesture Interface', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()