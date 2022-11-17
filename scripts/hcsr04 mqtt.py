import os, datetime, time, firebase_admin, cv2, pytesseract
from helpers import get_config, get_now_string, pil_image_to_byte_array
from imutils import opencv2matplotlib
from imutils.video import VideoStream
from PIL import Image
from mqtt import get_mqtt_client
from firebase_admin import db, storage

cred_obj = firebase_admin.credentials.Certificate('..\Database Module\smart-parking-iot-project-firebase-adminsdk-7gndh-8734cddb25.json')
default_app = firebase_admin.initialize_app(cred_obj, {
    'databaseURL': 'https://smart-parking-iot-project-default-rtdb.asia-southeast1.firebasedatabase.app/',
    'storageBucket': 'smart-parking-iot-project.appspot.com'
})

ref = db.reference("/vehicles")
bucket = storage.bucket()

camera = cv2.VideoCapture(0)
pytesseract.pytesseract.tesseract_cmd = "C:/Program Files/Tesseract-OCR/tesseract.exe"

MQTT_BROKER = "192.168.91.98"
MQTT_PORT = 1883

HCSR04_TOPIC = "esp/hcsr04/distance"
SERVO_GATE_TOPIC = "esp/servo/gate"
DISPLAY_TOPIC = "esp/oled/display"

def on_message(client, userdata, msg):
    now = datetime.datetime.now()
    print("Message on " + str(msg.topic) + f" at {now}.")

    try:
        distance = msg.payload
        print("Distance is ", distance)

        if(int(distance) <= 10):
            # return_val, image = camera.read()
            # file_name = "num_plate" + str(time.time()) + ".png"
            # cv2.imwrite(file_name, image)
            file_name = "test2.jpg"
            upload_start_time = time.time()
            print("Uploading number plate image " + file_name + " to cloud storage....")
            blob = bucket.blob(file_name)
            blob.upload_from_filename(file_name)
            print("File uploaded in " + str(time.time() - upload_start_time) + "!")

            blob.make_public()
            img = cv2.imread("D:/Code/MQTT-Project/scripts/" + file_name)

            # Convert the image to gray scale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Performing OTSU threshold
            ret, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)
            
            # Specify structure shape and kernel size.
            # Kernel size increases or decreases the area
            # of the rectangle to be detected.
            # A smaller value like (10, 10) will detect
            # each word instead of a sentence.
            rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))
            
            # Applying dilation on the threshold image
            dilation = cv2.dilate(thresh1, rect_kernel, iterations = 1)
            
            # Finding contours
            contours, hierarchy = cv2.findContours(dilation, cv2.RETR_EXTERNAL,
                                                            cv2.CHAIN_APPROX_NONE)
            
            # Creating a copy of image
            im2 = img.copy()
            # Looping through the identified contours
            # Then rectangular part is cropped and passed on
            # to pytesseract for extracting text from it
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                
                # Drawing a rectangle on copied image
                rect = cv2.rectangle(im2, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Cropping the text block for giving input to OCR
                cropped = im2[y:y + h, x:x + w]

                text = pytesseract.image_to_string(cropped)
                text = text.strip("\n")

                if len(text) > 0:
                    print("Vehicle detected: ", text, ".")
                    snapshot = ref.order_by_child('number_plate').equal_to(text).get()
                # print(snapshot)
                    plate_ref = None

                    if(snapshot.items()):
                        latest_key = next(reversed(snapshot))
                        plate_ref = ref.child(latest_key)
                    else:
                        ref.push({"number_plate": text, "in_time": str(datetime.datetime.now()), "out_time": "", "num_plate_image": blob.public_url})
                        text = "Number plate detected: " + text
                        client.publish(DISPLAY_TOPIC, text, qos=2)
                        
                    if(plate_ref.child("out_time").get() == ""):
                        plate_ref.update({"out_time": str(datetime.datetime.now())})
                        text = "Number plate detected: " + text + "\nParking Fee: Rs 142\n"
                        client.publish(DISPLAY_TOPIC, text, qos=2)
                    else:
                        ref.push({"number_plate": text, "in_time": str(datetime.datetime.now()), "out_time": "", "num_plate_image": blob.public_url})
                        text = "Number plate detected: " + text + "\nOpening Gate...."
                        client.publish(DISPLAY_TOPIC, text, qos=2)

                    snapshot = None
                else:
                    continue
                
            print("Opening Gate...")
            client.publish(SERVO_GATE_TOPIC, 0, qos=2)
        else:
            client.publish(DISPLAY_TOPIC, "Come close for detecting your number plate", qos=2)
    except Exception as exc:
        print(exc)

def main():
    client = get_mqtt_client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, port=MQTT_PORT)
    client.subscribe(HCSR04_TOPIC)

    time.sleep(4)
    client.loop_forever()

if __name__ == "__main__":
    main()