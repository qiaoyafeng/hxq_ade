from pathlib import Path

import numpy as np
import pandas as pd
import torch

from common.constants import DEPRESSED_STATE_DICT
from config import Config

from models.convlstm import ConvLSTMVisual
from models.evaluator import Evaluator

TEMP_PATH = Config.get_temp_path()


class InferenceService:
    def __init__(self, weights_path):
        self.visual_net = ConvLSTMVisual(
            input_dim=3,
            output_dim=256,
            conv_hidden=256,
            lstm_hidden=256,
            num_layers=4,
            activation="relu",
            norm="bn",
            dropout=0.5,
        )

        self.evaluator = Evaluator(
            feature_dim=256, output_dim=2, predict_type="phq-binary", num_subscores=8
        )
        self.weights_path = weights_path
        self.checkpoint = torch.load(weights_path)
        self.visual_net.load_state_dict(self.checkpoint["visual_net"], strict=False)
        self.evaluator.load_state_dict(self.checkpoint['evaluator'], strict=False)
        self.visual_net.eval()
        self.evaluator.eval()
        torch.set_grad_enabled(False)

    def pre_check(self, data_df):
        data_df = data_df.apply(pd.to_numeric, errors="coerce")
        data_np = data_df.to_numpy()
        data_min = data_np[np.where(~(np.isnan(data_np[:, 2:])))].min()
        data_df.where(~(np.isnan(data_df)), data_min, inplace=True)
        return data_df

    def load_all_feature(self, feature):
        all_feature_df = self.pre_check(feature)
        return all_feature_df

    def min_max_scaler(self, data):
        """recale the data, which is a 2D matrix, to 0-1"""
        return (data - data.min()) / (data.max() - data.min())

    def normalize(self, data):
        mean = np.mean(data)
        std = np.std(data)
        return (data - mean) / std

    def load_gaze(self, all_feature):
        gaze_coor = (
            all_feature.iloc[:, 2:8].to_numpy().reshape(len(all_feature), 2, 3)
        )  # 4 gaze vectors, 3 axes
        return gaze_coor

    def load_keypoints(self, all_feature):
        # process into format TxVxC
        x_coor = self.min_max_scaler(
            all_feature[all_feature.columns[298:366]].to_numpy()
        )
        y_coor = self.min_max_scaler(
            all_feature[all_feature.columns[366:434]].to_numpy()
        )
        z_coor = self.min_max_scaler(
            all_feature[all_feature.columns[434:502]].to_numpy()
        )
        fkps_coor = np.stack([x_coor, y_coor, z_coor], axis=-1)
        return fkps_coor

    async def get_visual_data(self, batch_feature):
        all_feature = self.load_all_feature(batch_feature)
        gaze = self.load_gaze(all_feature)
        fkps = self.load_keypoints(all_feature)
        return fkps, gaze

    async def visual_padding(self, data, pad_size=1800):
        if data.shape[0] != pad_size:
            size = tuple()
            size = size + (pad_size,) + data.shape[1:]
            padded_data = np.zeros(size)
            padded_data[: data.shape[0]] = data
        else:
            padded_data = data

        return padded_data

    async def visual_inference(self, visual_input):
        visual_input = torch.from_numpy(visual_input).type(torch.FloatTensor)
        print(f"visual_inference visual_input shape: {visual_input.shape}")
        visual_input = visual_input.permute(0, 3, 2, 1).contiguous()
        print(f"visual_inference visual_input permute shape: {visual_input.shape}")
        with torch.no_grad():
            visual_features = self.visual_net(visual_input)
            predictions = self.evaluator(visual_features)
        print(f"visual_inference predictions: {predictions}")
        depressed_index = predictions[0][1].item()
        score_pred = predictions.argmax(dim=-1)
        binary_pred = score_pred[0].item()
        # binary_pred 0: 正常，1：抑郁
        print(f"binary_pred: {binary_pred}")
        return {
            "depressed_id": binary_pred,
            "depressed_state": DEPRESSED_STATE_DICT[binary_pred],
            "depressed_index": depressed_index,
        }


inference_service = InferenceService(
    weights_path="weights/V+Conv2D-BiLSTM+PHQ-Binary_2024-09-23_105353_acc-82.3529.pt"
)