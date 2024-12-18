import os
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn import preprocessing
import tensorflow as tf
from tensorflow.keras import backend as K
from tcn import TCN


# 通过openFace提取面部特征
def video_fp_feature(video_path, out_filename):
    print(f"video_feature: video_path:{video_path} ......")
    if os.name == "nt":
        feature_command = r"D:\Programs\OpenFace_2.2.0_win_x64\FeatureExtraction.exe"

    else:
        feature_command = "FeatureExtraction"

    args = [
        "-f",
        f"{video_path}",
        "-2Dfp",
        "-of",
        out_filename,
    ]

    # 执行exe程序并传递参数
    try:
        print(f"feature_command: {feature_command}, args: {args}")
        result = subprocess.run(
            [feature_command] + args, check=True, capture_output=True, text=True
        )
        # 打印输出结果
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        print(e.output)


# 提取HDR特征
def hdr(video_new_path, hdr_path):
    m = [10, 20, 30, 40, 50]
    df = pd.read_csv(video_new_path)
    x0 = 5
    y0 = 73
    l = []
    for i in range(4080):
        l.append(i)
    l = np.array(l).reshape((1, len(l)))
    df1 = pd.DataFrame(l)
    for i in range(0, df.shape[0] - 101, 10):  # 每一帧
        lines = []
        print(i)
        for j in range(len(m)):  # 每一个时间间隔
            for k in range(0, 68):  # 每一对(x,y)
                a, b = i + m[j], i
                r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12 = (
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                )
                num = 0
                while a <= i + 100:
                    x = float(df.iloc[a][x0 + k] - df.iloc[b][x0 + k])
                    y = float(df.iloc[a][y0 + k] - df.iloc[b][y0 + k])
                    b = b + 10
                    a = b + m[j]
                    if x < -20:
                        r1 = r1 + 1
                    elif x >= -20 and x < -10:
                        r2 = r2 + 1
                    elif x >= -10 and x < 0:
                        r3 = r3 + 1
                    elif x >= 0 and x < 10:
                        r4 = r4 + 1
                    elif x >= 10 and x < 20:
                        r5 = r5 + 1
                    else:
                        r6 = r6 + 1
                    if y < -20:
                        r7 = r7 + 1
                    elif y >= -20 and y < -10:
                        r8 = r8 + 1
                    elif y >= -10 and y < 0:
                        r9 = r9 + 1
                    elif y >= 0 and y < 10:
                        r10 = r10 + 1
                    elif y >= 10 and y < 20:
                        r11 = r11 + 1
                    else:
                        r12 = r12 + 1
                    num = num + 1
                r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12 = (
                    r1 / num,
                    r2 / num,
                    r3 / num,
                    r4 / num,
                    r5 / num,
                    r6 / num,
                    r7 / num,
                    r8 / num,
                    r9 / num,
                    r10 / num,
                    r11 / num,
                    r12 / num,
                )
                lines.append(r1)
                lines.append(r2)
                lines.append(r3)
                lines.append(r4)
                lines.append(r5)
                lines.append(r6)
                lines.append(r7)
                lines.append(r8)
                lines.append(r9)
                lines.append(r10)
                lines.append(r11)
                lines.append(r12)
        lines = np.array(lines).reshape((1, len(lines)))
        df2 = pd.DataFrame(lines)
        df1 = pd.concat([df1, df2], ignore_index=True)
    df1 = df1[1:]
    df1.to_csv(hdr_path)


# 提取HDR特征优化
def hdr_optimize(video_new_path, hdr_path):
    # 设定常量
    m = [10, 20, 30, 40, 50]
    x0, y0 = 5, 73

    # 读取CSV数据
    df = pd.read_csv(video_new_path)

    # 获取数据行数
    num_rows = df.shape[0]

    # 初始化结果容器
    results = []

    # 计算每个窗口的HDR特征
    for i in range(0, num_rows - 101, 10):
        print(f"i-------------------------------------------------{i}")
        # 记录每个窗口的特征
        window_features = []

        # 对每一个时间间隔进行遍历
        for j in m:
            # 对每一对(x, y)进行遍历
            for k in range(68):
                # 定义累计变量
                r1 = r2 = r3 = r4 = r5 = r6 = 0
                r7 = r8 = r9 = r10 = r11 = r12 = 0
                num = 0

                # 设置 a 和 b 的初始值
                a = i + j
                b = i

                # 遍历数据并计算每个时间点的x, y差异
                while a <= i + 100:
                    x = df.iloc[a, x0 + k] - df.iloc[b, x0 + k]
                    y = df.iloc[a, y0 + k] - df.iloc[b, y0 + k]
                    b += 10
                    a = b + j

                    # 累加x, y的分类计数
                    r1 += x < -20
                    r2 += -20 <= x < -10
                    r3 += -10 <= x < 0
                    r4 += 0 <= x < 10
                    r5 += 10 <= x < 20
                    r6 += x >= 20

                    r7 += y < -20
                    r8 += -20 <= y < -10
                    r9 += -10 <= y < 0
                    r10 += 0 <= y < 10
                    r11 += 10 <= y < 20
                    r12 += y >= 20

                    num += 1
                # 计算比例
                if num > 0:
                    window_features.extend(
                        [
                            r1 / num,
                            r2 / num,
                            r3 / num,
                            r4 / num,
                            r5 / num,
                            r6 / num,
                            r7 / num,
                            r8 / num,
                            r9 / num,
                            r10 / num,
                            r11 / num,
                            r12 / num,
                        ]
                    )

        results.append(window_features)
    df1 = pd.DataFrame(np.array(results))
    # 将最终结果保存到csv文件
    df1.to_csv(hdr_path)


# 将HDR特征送入模型中的出结果
def infer_video_model(hdr_path, model_class=None):
    K.clear_session()

    def rmse(y_pred, y_true):
        return K.sqrt(K.mean(K.square(y_pred - y_true)))

    if model_class:
        checkpoint_filepath = rf"weights/tcn_{model_class.lower()}.keras"
        custom_objects = {"TCN": TCN, "rmse": rmse}
    else:
        checkpoint_filepath = "weights/vidio_1.h5"
        custom_objects = {"TCN": TCN, "mse": "mse"}
    print(
        f"checkpoint_filepath: {checkpoint_filepath}, custom_objects: {custom_objects}"
    )
    tcn = tf.keras.models.load_model(checkpoint_filepath, custom_objects=custom_objects)
    df = pd.read_csv(hdr_path, index_col=0)
    time_step = 10

    x_Test = []
    j = 0
    while j + time_step < df.shape[0]:
        x_Test.append(df.iloc[j : j + time_step, :])
        j = j + time_step

    X_TEST = [x.values for x in x_Test]
    x_test = np.array(X_TEST)
    print(f"infer_video_model x_test shape: {x_test.shape}")
    # a,b,c = X_TEST.shape[0],X_TEST.shape[1],X_TEST.shape[2]
    # x_test_normal = X_TEST.reshape(-1,c)
    # min_max_scaler = preprocessing.MinMaxScaler(feature_range=(-1,1))
    # x_test_minmax=min_max_scaler.fit_transform(x_test_normal)
    # x_test = x_test_minmax.reshape(a,b,c)

    predict = tcn.predict(x_test)

    predict_list = []
    for i in range(len(predict)):
        predict_list.append(predict[i][0])
    min_x = np.min(predict)
    print(f"infer_video_model: min_x: {min_x}, predict_list: {predict_list}")
    return min_x, predict_list


if __name__ == "__main__":
    pass
