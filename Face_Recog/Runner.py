# Importing essential files from the program
from Face_Recog import Main_Model
from Face_Recog.commons import functions
import realtime
# Flask is used for webstreaming
from flask import Response
from flask import Flask
from flask import render_template
import threading
# Fancy Progress Bars
from tqdm import tqdm
import os
import pandas as pd
from OpenSSL import SSL
'''PLEASE NOTE ---------------------------------------------
    The min_detection_confidence in Mediapipe
    And 
    The  if w > 0 (line 73- realtime) - Need to be modified according to the hardware used.
'''
outputFrame = None

# Needed to ensure streaming works on multiple devices
lock = threading.Lock()
app = Flask(__name__)

# Initializing Necessary model for recognition/detection
# Using "Facenet" and "Mediapipe" recommended
model_name = 'Facenet'

db_path = r"./images"
detector_backend = 'mediapipe'
''' Options-'opencv',
         'ssd' ,
         'dlib',
         'mtcnn',
         'retinaface',
         'mediapipe'
'''
# distance_metric - used to judge distance between video_feed and database image
distance_metric = 'cosine'
input_shape = (224, 224)


# Embedding Images to dataframe
def embed(model_name, db_path, detector_backend, distance_metric):
    employees = []
    # check passed db folder exists
    if os.path.isdir(db_path):
        for r, d, f in os.walk(db_path):  # r=root, d=directories, f = files
            for file in f:
                if '.jpg' in file:
                    # exact_path = os.path.join(r, file)
                    exact_path = r + "/" + file
                    employees.append(exact_path)
    if len(employees) == 0:
        print("WARNING: There is no image in this path ( ", db_path, ") . Face recognition will not be performed.")
    if len(employees) > 0:
        model = Main_Model.build_model(model_name)
        print(model_name, " is built")
    pbar = tqdm(range(0, len(employees)), desc='Finding embeddings')
    input_shape = functions.find_input_shape(model)
    input_shape_x = input_shape[0];
    input_shape_y = input_shape[1]

    embeddings = []
    # for employee in employees:
    for index in pbar:
        employee = employees[index]
        pbar.set_description("Finding embedding for %s" % (employee.split("/")[-1]))
        embedding = []

        # preprocess_face returns single face. this is expected for source images in db.
        img = functions.preprocess_face(img=employee, target_size=(input_shape_y, input_shape_x),
                                        enforce_detection=False, detector_backend=detector_backend)
        img_representation = model.predict(img)[0, :]

        embedding.append(employee)
        embedding.append(img_representation)
        embeddings.append(embedding)

    df = pd.DataFrame(embeddings, columns=['employee', 'embedding'])
    df['distance_metric'] = distance_metric
    # returns dataframe with employee, embedding and distance_metric information
    return df


@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")


@app.route('/video')
def video():
    return Response(
        realtime.analysis(db_path, detector_backend=detector_backend, df=df, model_name=model_name, time_threshold=3,
                          frame_threshold=3),
        mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == '__main__':
    # start a thread that will perform web stream
    df = embed(model_name, db_path, detector_backend, distance_metric)
    t = threading.Thread()
    t.daemon = True
    print("System Running Succesfully")
    t.start()
    # start the flask app
    app.jinja_env.cache = {}
    app.run(host='0.0.0.0', port='8001', debug=True,
            use_reloader=False, ssl_context='adhoc')
