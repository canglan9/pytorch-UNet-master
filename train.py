import os
import torch.nn as nn
import torch.optim as optim
import torch
from functools import partial
from argparse import ArgumentParser

from unet.unet import UNet2D
from unet.model import Model
from unet.utils import MetricList
from unet.metrics import jaccard_index, f1_score, LogNLLLoss
from unet.dataset import JointTransform2D, ImageToImage2D, Image2D

class DiceLoss(nn.Module):
    def __init__(self):
        super(DiceLoss, self).__init__()

    def forward(self, inputs, targets):
        # inputs: model output, targets: true masks
        inputs = torch.sigmoid(inputs).flatten(1)
        targets = targets.flatten(1)

        intersection = (inputs * targets).sum()
        dice = (2. * intersection ) / (inputs.sum() + targets.sum() )
        return 1 - dice

parser = ArgumentParser()
parser.add_argument('--train_dataset',default='docs/training_set',  type=str)
parser.add_argument('--val_dataset', default='docs/val_set',type=str)
parser.add_argument('--checkpoint_path', default='docs/personal_result', type=str)
parser.add_argument('--device', default='cpu', type=str)
parser.add_argument('--in_channels', default=3, type=int)
parser.add_argument('--out_channels', default=1, type=int)
parser.add_argument('--depth', default=5, type=int)
parser.add_argument('--width', default=32, type=int)
parser.add_argument('--epochs', default=40, type=int)
parser.add_argument('--batch_size', default=1, type=int)
parser.add_argument('--save_freq', default=1, type=int)
parser.add_argument('--save_model', default=1, type=int)
parser.add_argument('--model_name', type=str, default='model')
parser.add_argument('--learning_rate', type=float, default=1e-3)
parser.add_argument('--crop', type=int, default=None)
args = parser.parse_args()

if args.crop is not None:
    crop = (args.crop, args.crop)
else:
    crop = None

tf_train = JointTransform2D(crop=crop, p_flip=0.5, color_jitter_params=None, long_mask=True)
tf_val = JointTransform2D(crop=crop, p_flip=0, color_jitter_params=None, long_mask=True)
train_dataset = ImageToImage2D(args.train_dataset, tf_val)
val_dataset = ImageToImage2D(args.val_dataset, tf_val)
predict_dataset = Image2D(args.val_dataset)

conv_depths = [int(args.width*(2**k)) for k in range(args.depth)]
unet = UNet2D(args.in_channels, args.out_channels, conv_depths)

#loss = torch.nn.BCEWithLogitsLoss()
loss = DiceLoss()
optimizer = optim.Adam(unet.parameters(), lr=args.learning_rate)

results_folder = os.path.join(args.checkpoint_path, args.model_name)
if not os.path.exists(results_folder):
    os.makedirs(results_folder)

metric_list = MetricList({'jaccard': partial(jaccard_index),
                          'f1': partial(f1_score)})

model = Model(unet, loss, optimizer, results_folder, device=args.device)

model.fit_dataset(train_dataset, n_epochs=args.epochs, n_batch=args.batch_size,
                  shuffle=True, val_dataset=val_dataset, save_freq=args.save_freq,
                  save_model=args.save_model, predict_dataset=predict_dataset,
                  metric_list=metric_list, verbose=True)
