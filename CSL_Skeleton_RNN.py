import os
import sys
from datetime import datetime
import logging
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torch.utils.tensorboard import SummaryWriter
from models.RNN import LSTM, GRU
from dataset import CSL_Skeleton
from train import train_epoch
from validation import val_epoch

# Path setting
data_path = "/home/haodong/Data/CSL_Isolated/xf500_body_depth_txt"
label_path = "/home/haodong/Data/CSL_Isolated/dictionary.txt"
model_path = "/home/haodong/Data/skeleton_models"
log_path = "log/skeleton_{:%Y-%m-%d_%H-%M-%S}.log".format(datetime.now())
sum_path = "runs/slr_skeleton_{:%Y-%m-%d_%H-%M-%S}".format(datetime.now())

# Log to file & tensorboard writer
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.FileHandler(log_path), logging.StreamHandler()])
logger = logging.getLogger('SLR')
logger.info('Logging to file...')
writer = SummaryWriter(sum_path)

# Use specific gpus
os.environ["CUDA_VISIBLE_DEVICES"]="1"
# Device setting
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Hyperparams
epochs = 500
batch_size = 32
learning_rate = 1e-5
log_interval = 20
num_classes = 100
sample_duration = 16
selected_joints = ['HANDLEFT', 'HANDRIGHT', 'ELBOWLEFT', 'ELBOWRIGHT']
input_size = len(selected_joints)*2
hidden_size = 512
num_layers = 1
hidden1 = 512
drop_p = 0.0

# Train with Skeleton+RNN
if __name__ == '__main__':
    # Load data
    transform = None # TODO
    train_set = CSL_Skeleton(data_path=data_path, label_path=label_path, frames=sample_duration,
        num_classes=num_classes, selected_joints=selected_joints, train=True, transform=transform)
    val_set = CSL_Skeleton(data_path=data_path, label_path=label_path, frames=sample_duration,
        num_classes=num_classes, selected_joints=selected_joints, train=False, transform=transform)
    logger.info("Dataset samples: {}".format(len(train_set)+len(val_set)))
    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    # Create model
    # model = LSTM(lstm_input_size=input_size, lstm_hidden_size=hidden_size, lstm_num_layers=num_layers,
    #     num_classes=num_classes, hidden1=hidden1, drop_p=drop_p).to(device)
    model = GRU(gru_input_size=input_size, gru_hidden_size=hidden_size, gru_num_layers=num_layers,
        num_classes=num_classes, hidden1=hidden1, drop_p=drop_p).to(device)
    # Run the model parallelly
    if torch.cuda.device_count() > 1:
        logger.info("Using {} GPUs".format(torch.cuda.device_count()))
        model = nn.DataParallel(model)
    # Create loss criterion & optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # Start training
    logger.info("Training Started".center(60, '#'))
    for epoch in range(epochs):
        # Train the model
        train_epoch(model, criterion, optimizer, train_loader, device, epoch, logger, log_interval, writer)

        # Validate the model
        val_epoch(model, criterion, val_loader, device, epoch, logger, writer)

        # Save model
        torch.save(model.state_dict(), os.path.join(model_path, "slr_skeleton_epoch{:03d}.pth".format(epoch+1)))
        logger.info("Epoch {} Model Saved".format(epoch+1).center(60, '#'))

    logger.info("Training Finished".center(60, '#'))
