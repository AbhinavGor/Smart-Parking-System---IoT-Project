import os
import time
import cv2, pandas

from helpers import get_config, get_now_string, pil_image_to_byte_array
from imutils import opencv2matplotlib
from imutils.video import VideoStream
from mqtt import get_mqtt_client
from PIL import Image
from datetime import datetime

CONFIG_FILE_PATH = os.getenv("MQTT_CAMERA_CONFIG", "./config/config.yml")
CONFIG = get_config(CONFIG_FILE_PATH)

MQTT_BROKER = CONFIG["mqtt"]["broker"]
MQTT_PORT = CONFIG["mqtt"]["port"]
MQTT_QOS = CONFIG["mqtt"]["QOS"]

MQTT_TOPIC_CAMERA = CONFIG["camera"]["mqtt_topic"]
VIDEO_SOURCE = CONFIG["camera"]["video_source"]
FPS = CONFIG["camera"]["fps"]


def main():
    client = get_mqtt_client()
    client.connect(MQTT_BROKER, port=MQTT_PORT)
    time.sleep(4)
    client.loop_start()

    # Open camera
    camera = VideoStream(src=VIDEO_SOURCE, framerate=FPS).start()
    time.sleep(2)  # Webcam light should come on if using one

    #Motion detection setup
    static_back = None
    motion_list = [None, None]

    times = []

    df = pandas.DataFrame(columns=["Start", "End"])

    while True:
        frame = camera.read()

        motion = False

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if static_back is None:
            static_back = gray
            continue

        diff_frame = cv2.absdiff(static_back, gray)

        thresh_frame = cv2.threshold(diff_frame, 60, 255, cv2.THRESH_BINARY)[1]
        thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

        cnts, _ = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in cnts:
            if cv2.contourArea(contour) < 1000:
                continue
            motion = True
            print("motion")
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            captureImage(frame, client)
            time.sleep(1)
        
        motion_list.append(motion)
        motion_list = motion_list[-2:]

        if motion_list[-1] == 1 and motion_list[-2] == 0:
            times.append(datetime.now())
  
        # Appending End time of motion
        if motion_list[-1] == 0 and motion_list[-2] == 1:
            times.append(datetime.now())
    
        # Displaying image in gray_scale
        cv2.imshow("Gray Frame", gray)
    
        # Displaying the difference in currentframe to
        # the staticframe(very first_frame)
        cv2.imshow("Difference Frame", diff_frame)
    
        # Displaying the black and white image in which if
        # intensity difference greater than 30 it will appear white
        cv2.imshow("Threshold Frame", thresh_frame)
    
        # Displaying color frame with contour of motion of object
        cv2.imshow("Color Frame", frame)

        # captureImage(frame, client)
        # time.sleep(4)

    
        key = cv2.waitKey(1)
        # if q entered whole process will stop
        if key == ord('q'):
            # if something is movingthen it append the end time of movement
            if motion == 1:
                times.append(datetime.now())
            break
  
    # Appending time of motion in DataFrame
    for i in range(0, len(time), 2):
        df = df.append({"Start":time[i], "End":time[i + 1]}, ignore_index = True)
    
    # Creating a CSV file in which time of movements will be saved
    df.to_csv("Time_of_movements.csv")
    
    camera.release()
    
    # Destroying all the windows
    cv2.destroyAllWindows()

def detectMotion(camera, static_back, client):
    frame = camera.read()

    motion = 0

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if static_back is None:
        static_back = gray
    
    diff_frame = cv2.absdiff(static_back, gray)
    thresh_frame = cv2.threshold(diff_frame, 30, 255, cv2.THRESH_BINARY)[1]
    thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

    cnts, _ = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in cnts:
        if cv2.contourArea(contour) < 10000:
            continue
        motion = 1

    if motion == 1:    
        captureImage(camera, client)

def captureImage(frame, client):
    # frame = camera.read()
    np_array_RGB = opencv2matplotlib(frame)  # Convert to RGB

    image = Image.fromarray(np_array_RGB)  #  PIL image
    byte_array = pil_image_to_byte_array(image)
    client.publish(MQTT_TOPIC_CAMERA, byte_array, qos=MQTT_QOS)
    now = get_now_string()
    print(f"published frame on topic: {MQTT_TOPIC_CAMERA} at {now}")
    # time.sleep(1 / FPS)

if __name__ == "__main__":
    main()
