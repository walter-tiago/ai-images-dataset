# -*- coding: utf-8 -*-
"""image-classification-train.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1yygxaD0oaT-pXeWUBfsZfebk5uz8gru2
"""

!pip install tensorflow_addons

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import pathlib as pl
import tensorflow as tf
import datetime
import shutil
import pickle
import tensorflow_addons as tfa
import tensorflow.keras as tfk
import keras
import sklearn
from sklearn.metrics import confusion_matrix, auc, roc_curve

def timestamp():
  return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

"""Os diretórios abaixo são mutáveis para testar outros datasets, lembre-se que o diretório do dataset deve ser uma pasta com as imagens .png, a separação em subpastas para as classes é realizada no próprio código"""

!git clone https://github.com/walter-tiago/ai-images-dataset.git

dataset_dir = pl.Path("/content/ai-images-dataset/dataset")
temp_dir = pl.Path("/content/ai-images-dataset/temporary")
model_dir = temp_dir / "models"
train_dir = temp_dir / "train"
log_dir = temp_dir / "logs"
csv_dir = temp_dir / "csv-files"

dataset_dir.mkdir(parents = True, exist_ok = True)
model_dir.mkdir(parents = True, exist_ok = True)
train_dir.mkdir(parents = True, exist_ok = True)
log_dir.mkdir(parents = True, exist_ok = True)
csv_dir.mkdir(parents = True, exist_ok = True)

"""Os valores de input abaixo são mutáveis, contudo sua modificação pode ocasionar underfitting ou overfitting. **OBS.:** para um treino rápido, o melhor seria diminuir as épocas (epochs)"""

# Input values:
image_size = (50, 50)
classes = ["soil", "tree"]
batch_size = 128
epochs = 256
learning_rate = 0.001
regularization_rate = 0.01
num_ref_layer = 3 # number of (2D Conv layers) and (Dense layers)
dropout_rate = 0.5
validation_split = 0.3

class_mode = "categorical"
num_classes = len(classes)
channels = 3  # RGB
image_shape = image_size + (channels,)

# Class folders:
for class_name in classes:
  class_dir = train_dir / class_name
  class_dir.mkdir(parents=True, exist_ok=True)
  for local_file in dataset_dir.iterdir():
    local_file_name = local_file.name
    if local_file.is_file() and class_name in local_file_name:
      shutil.copy(local_file, class_dir / local_file.name)
  print(f'{class_name.title()}: {len(list(class_dir.iterdir()))} samples.')

# Preprocessing Data generator:

datagen = tfk.preprocessing.image.ImageDataGenerator(
    preprocessing_function = tfk.applications.vgg19.preprocess_input,
    width_shift_range = 0.2,
    height_shift_range = 0.2,
    zoom_range = 0.1,
    validation_split = validation_split
    )

train_generator = datagen.flow_from_directory(
    train_dir,
    target_size = image_size,
    batch_size = batch_size,
    class_mode = class_mode,
    subset='training'
    )

validation_generator = datagen.flow_from_directory(
    train_dir,
    target_size = image_size,
    batch_size = batch_size,
    class_mode = class_mode,
    subset='validation',
    shuffle=False
    )

class_weights = sklearn.utils.class_weight.compute_class_weight(
                'balanced', 
                classes = np.unique(train_generator.classes), 
                y = train_generator.classes
                )

print(f"\nClass weights: {classes} = {class_weights}")

"""Este modelo sequencial de rede neural pode ser modificado para testes, novamente fique atento ao under ou overfitting"""

# Base model:

base_model = tfk.applications.vgg19.VGG19(
    weights = "imagenet", 
    include_top = False, 
    input_shape = image_shape
    )

base_model.trainable = False

model = tfk.models.Sequential()

model.add(base_model)

counter_layer = 0
while counter_layer < num_ref_layer:
  
  model.add(
      tfk.layers.Conv2D(
          filters = batch_size / 2**(num_ref_layer - counter_layer),
          kernel_size = (3, 3), 
          activation='relu', 
          padding='same',
          input_shape = image_shape,))
   
  model.add(
      tfk.layers.Conv2D(
          filters = batch_size / 2**(num_ref_layer - counter_layer),
          kernel_size = (3, 3), 
          activation='relu', 
          padding='same',
          input_shape = image_shape,))
  
  model.add(
    tfk.layers.Conv2D(
        filters = batch_size / 2**(num_ref_layer - counter_layer),
        kernel_size = (3, 3), 
        activation='relu', 
        padding='same',
        input_shape = image_shape,))
   
  model.add(
      tfk.layers.MaxPooling2D(
          pool_size = (2, 2),
          padding='same',
          ))

  counter_layer += 1

model.add(tfk.layers.Dropout(dropout_rate / 2))

model.add(tfk.layers.Flatten())

counter_layer = 0
while counter_layer < num_ref_layer - 1:
  model.add(
      tfk.layers.Dense(
          batch_size / 2**counter_layer, 
          activation='relu', 
          activity_regularizer = tfk.regularizers.l2(regularization_rate)
          ))
    
  model.add(
        tfk.layers.Dropout(dropout_rate)
        )
  
  counter_layer += 1

if num_classes <= 2:
  model.add(
      tfk.layers.Dense(num_classes, activation='sigmoid')
      )
  
else:
  model.add(
      tfk.layers.Dense(num_classes, activation='softmax')
      )

# Model compiler:
optimizer = tfk.optimizers.Adam(learning_rate=learning_rate)
metrics = [
    'Accuracy',
    'AUC',
    'Precision',
    'Recall',
    tfa.metrics.F1Score(num_classes=num_classes, average='micro'),
]

model.compile(
    optimizer=optimizer,
    loss=class_mode + '_crossentropy',
    metrics=metrics,
)

tensorboard_callback = tfk.callbacks.TensorBoard(log_dir=log_dir, write_graph=True)

# Model Training:

history = model.fit(
            train_generator,
            epochs = epochs,
            steps_per_epoch = train_generator.samples // batch_size,
            validation_data = validation_generator,
            validation_steps = validation_generator.samples // batch_size,
            class_weight = dict(enumerate(class_weights)),
            callbacks = [tensorboard_callback]
            )

local_time = timestamp()
local_model = model_dir / f"model_{local_time}.h5"
local_weight_model = model_dir / f"model_{local_time}_weights.h5"

model.save(local_model)
model.save_weights(local_weight_model)