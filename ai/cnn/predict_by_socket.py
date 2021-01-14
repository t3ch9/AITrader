
import socket
import pandas as pd
import numpy as np
import tensorflow as tf
import re
import os
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from operator import itemgetter
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras import backend as K
from tensorflow.keras.utils import get_custom_objects
from tensorflow.keras.models import Sequential,  Model
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.layers import Conv2D, MaxPool2D, Flatten, LeakyReLU
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau, CSVLogger, Callback
from tensorflow.keras import optimizers
from tensorflow.keras.models import load_model
from tensorflow.keras import regularizers
from sklearn.metrics import f1_score
from sklearn.metrics import confusion_matrix, roc_auc_score, cohen_kappa_score
from numpy import save,load
import joblib

# Együttműködik az MT5 Script folder-ben található Getdata script-tel. Ha abban az IsSocketSending=true, akkor a script küldi ennek a megfelelő socket-et
metatrader_dir="C:\\Users\\melgibson\\AppData\Roaming\\MetaQuotes\\Terminal\\6E837615CE50F086D7E2801AA8E2160A\\MQL5\\Files\\"

class socketserver:
    def __init__(self, address = 'localhost', port = 9090):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = address
        self.port = port
        self.sock.bind((self.address, self.port))
        self.cummdata = ''
        
    def recvmsg(self):
        self.sock.listen(1)
        self.conn, self.addr = self.sock.accept()
        print('connected to', self.addr)
        self.cummdata = ''

        while True:
            data = self.conn.recv(10000)
            self.cummdata+=data.decode("utf-8")
            if not data:
                break    
            self.conn.send(bytes(start_prediction(self.cummdata), "utf-8"))
            return self.cummdata
            
    def __del__(self):
        self.sock.close()
        
def calcregr(msg = ''):
    # print(msg)
    msg_parts=msg.split('|')
    columns=msg_parts[0]
    columns = columns.split(',')
    del columns[0]
    date_string=msg_parts[1].split(',')[0]
    features=np.array(msg_parts[1].split(',')[1:])
    data = np.array([features]).astype(np.float)
    # print(date_string)
    # print(columns)
    # print(data)
    df = pd.DataFrame(data, columns=[columns])
    # print(df.head(2))
    # chartdata = np.fromstring(msg, dtype=float, sep= ',')
    # Y = np.array(chartdata).reshape(-1,1)
    # X = np.array(np.arange(len(chartdata))).reshape(-1,1)
    #
    # lr = LinearRegression()
    # lr.fit(X, Y)
    # Y_pred = lr.predict(X)
    #
    # P = Y_pred.astype(str).item(-1) + ' ' + Y_pred.astype(str).item(0)
    # print(P)
    return str("OK")

def f1_metric(y_true, y_pred):
    """
    this calculates precision & recall
    """

    def recall(y_true, y_pred):
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))  # mistake: y_pred of 0.3 is also considered 1
        possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
        recall = true_positives / (possible_positives + K.epsilon())
        return recall

    def precision(y_true, y_pred):
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
        precision = true_positives / (predicted_positives + K.epsilon())
        return precision

    precision = precision(y_true, y_pred)
    recall = recall(y_true, y_pred)
    # y_true_class = tf.math.argmax(y_true, axis=1, output_type=tf.dtypes.int32)
    # y_pred_class = tf.math.argmax(y_pred, axis=1, output_type=tf.dtypes.int32)
    # conf_mat = tf.math.confusion_matrix(y_true_class, y_pred_class)
    # tf.Print(conf_mat, [conf_mat], "confusion_matrix")

    return 2 * ((precision * recall) / (precision + recall + K.epsilon()))

def reshape_as_image(x, img_width, img_height):
    x_temp = np.zeros((len(x), img_height, img_width))
    for i in range(x.shape[0]):
        # print(type(x), type(x_temp), x.shape)
        x_temp[i] = np.reshape(x[i], (img_height, img_width))

    return x_temp

def start_prediction(msg = ''):
    print(msg)
    msg_parts=msg.split('|')
    columns=msg_parts[0]
    columns = columns.split(',')
    del columns[0]
    date_string=msg_parts[1].split(',')[0]
    features=np.array(msg_parts[1].split(',')[1:])
    data = np.array([features]).astype(np.float)
    df = pd.DataFrame(data, columns=columns)

    np.random.seed(2)
    tf.random.set_seed(2)
    best_model_path = os.path.join('.', 'best_models', 'EURUSD1')

    colums_needed = list(pd.read_csv(os.path.join(best_model_path, 'columns_needed.csv'), header=None).T.values[0])
    df = df[colums_needed]
    x_test = df.to_numpy()
    # print(1,x_test)

    my_imputer = SimpleImputer()
    x_test = my_imputer.fit_transform(x_test)
    # print(2, x_test)


    # mm_scaler = MinMaxScaler(feature_range=(0, 1))  # or StandardScaler?
    mm_scaler = joblib.load(os.path.join(best_model_path, 'mm_scaler.joblib'))
    x_test = mm_scaler.transform(x_test)
    # print(3, x_test)

    dim = int(np.sqrt(196))
    x_test = reshape_as_image(x_test, dim, dim)
    # print(4, x_test)
    x_test = np.stack((x_test,) * 3, axis=-1)
    # print(5, x_test)


    model = load_model(best_model_path, custom_objects={"f1_metric": f1_metric})
    pred = model.predict(x_test)
    prob = np.max(pred, axis=1)
    pred_classes = np.argmax(pred, axis=1)

    print(prob)
    print('------------')
    print(pred_classes)




    return str("OK")

serv = socketserver('127.0.0.1', 9090)

while True:  
    msg = serv.recvmsg()



    
