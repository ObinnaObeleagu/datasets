import keras
from keras.layers import *
from keras.models import *
from keras.preprocessing.image import ImageDataGenerator
from keras.callbacks import LearningRateScheduler
import os
from keras.callbacks import ModelCheckpoint
from keras.optimizers import Adam

#The Linear Bottleneck increases the number of channels going into the depthwise convs
def LinearBottleNeck(x,in_channels,out_channels,stride,expansion):

    #Expand the input channels
    out = Conv2D(in_channels*expansion,kernel_size=1,strides=1,padding="same",use_bias=False)(x)
    out = BatchNormalization()(out)
    out = Activation(relu6)(out)

    #perform 3 x 3 depthwise conv
    out = DepthwiseConv2D(kernel_size=3,strides=stride,padding="same",use_bias=False)(out)
    out = BatchNormalization()(out)
    out = Activation(relu6)(out)

    #Reduce the output channels to conserve computation
    out = Conv2D(out_channels,kernel_size=1,strides=1,padding="same",use_bias=False)(out)
    out = BatchNormalization()(out)

    #Perform resnet-like addition if input image and output image are same dimesions
    if stride == 1 and in_channels == out_channels:
        out = add([out,x])
    return out





    #Relu6 is the standard relu with the maximum thresholded to 6
def relu6(x):
    return K.relu(x,max_value=6)


def MobileNetV2(input_shape,num_classes=2,multiplier=1.0):

    images = Input(shape=input_shape)

    net = Conv2D(int(32*multiplier),kernel_size=3,strides=2,padding="same",use_bias=False)(images)
    net = BatchNormalization()(net)
    net = Activation("relu")(net)

    #First block with 16 * multplier output with stride of 1
    net = LinearBottleNeck(net, in_channels=int(32 * multiplier), out_channels=int(16 * multiplier), stride=1, expansion=1)

    #Second block with 24 * multplier output with first stride of 2
    net = LinearBottleNeck(net, in_channels=int(32 * multiplier), out_channels=int(24 * multiplier), stride=2, expansion=6)
    net = LinearBottleNeck(net, in_channels=int(24 * multiplier), out_channels=int(24 * multiplier), stride=1, expansion=6)

    #Third block with 32 * multplier output with first stride of 2
    net = LinearBottleNeck(net, in_channels=int(24 * multiplier), out_channels=int(32 * multiplier), stride=2, expansion=6)
    net = LinearBottleNeck(net, in_channels=int(32 * multiplier), out_channels=int(32 * multiplier), stride=1, expansion=6)
    net = LinearBottleNeck(net, in_channels=int(32 * multiplier), out_channels=int(32 * multiplier), stride=1, expansion=6)

    #Fourth block with 64 * multplier output with first stride of 2
    net = LinearBottleNeck(net, in_channels=int(32 * multiplier), out_channels=int(64 * multiplier), stride=2, expansion=6)
    net = LinearBottleNeck(net, in_channels=int(64 * multiplier), out_channels=int(64 * multiplier), stride=1, expansion=6)
    net = LinearBottleNeck(net, in_channels=int(64 * multiplier), out_channels=int(64 * multiplier), stride=1, expansion=6)
    net = LinearBottleNeck(net, in_channels=int(64 * multiplier), out_channels=int(64 * multiplier), stride=1, expansion=6)

    #Fifth block with 96 * multplier output with first stride of 1
    net = LinearBottleNeck(net, in_channels=int(64 * multiplier), out_channels=int(96 * multiplier), stride=1, expansion=6)
    net = LinearBottleNeck(net, in_channels=int(96 * multiplier), out_channels=int(96 * multiplier), stride=1, expansion=6)
    net = LinearBottleNeck(net, in_channels=int(96 * multiplier), out_channels=int(96 * multiplier), stride=1, expansion=6)

    #Sixth block with 160 * multplier output with first stride of 2
    net = LinearBottleNeck(net, in_channels=int(96 * multiplier), out_channels=int(160 * multiplier), stride=2, expansion=6)
    net = LinearBottleNeck(net, in_channels=int(160 * multiplier), out_channels=int(160 * multiplier), stride=1, expansion=6)
    net = LinearBottleNeck(net, in_channels=int(160 * multiplier), out_channels=int(160 * multiplier), stride=1, expansion=6)

    #Seventh block with 320 * multplier output with stride of 1
    net = LinearBottleNeck(net, in_channels=int(160 * multiplier), out_channels=int(320 * multiplier), stride=1, expansion=6)


    #Final number of channels must be at least 1280

    if multiplier > 1.0:
        final_channels = int(1280 * multiplier)
    else:
        final_channels = 1280

    #Expand the output channels
    net = Conv2D(final_channels,kernel_size=1,padding="same",use_bias=False)(net)
    net = BatchNormalization()(net)
    net = Activation(relu6)(net)
    net = Dropout(0.3)(net)

    #Final Classification is by 1 x 1 Conv
    net = AveragePooling2D(pool_size=(7,7))(net)
    net = Conv2D(num_classes,kernel_size=1,use_bias=False)(net)
    net = Flatten()(net)
    net = Activation("softmax")(net)

    return Model(inputs=images,outputs=net)



##Training on Custom Image Dataset


# Directory in which to create models
save_direc = os.path.join(os.getcwd(), 'oranges_models')

# Name of model files
model_name = 'oranges_weight_model.{epoch:03d}-{val_acc}.h5'

# Create Directory if it doesn't exist
if not os.path.isdir(save_direc):
    os.makedirs(save_direc)

# Join the directory with the model file
modelpath = os.path.join(save_direc, model_name)

# Checkpoint to save best model
checkpoint = ModelCheckpoint(filepath=modelpath,
                             monitor='val_acc',
                             verbose=1,
                             save_best_only=True,
                             save_weights_only=True,
                             period=1)


# Function for adjusting learning rate
def lr_schedule(epoch):
    """
    Learning Rate Schedule
    """
   
    lr = 0.001
    if epoch > 30:
        lr = lr / 100
    elif epoch > 20:
        lr = lr / 50
    elif epoch > 10:
        lr = lr / 10

    print('Learning rate: ', lr)
    return lr


#learning rate schedule callback
lr_scheduler = LearningRateScheduler(lr_schedule)


optimizer = Adam(lr=0.001, decay=0.0005)
BATCH_SIZE = 32
NUM_CLASSES = 2
EPOCHS = 50

model = MobileNetV2(input_shape=(224, 224, 3), num_classes=NUM_CLASSES)
model.compile(loss="categorical_crossentropy", optimizer=optimizer, metrics=["accuracy"])
model.summary()

#Data augmentation
train_datagen = ImageDataGenerator(
    rescale=1. / 255,
    horizontal_flip=True)

test_datagen = ImageDataGenerator(
    rescale=1. / 255)

train_generator = train_datagen.flow_from_directory("Oranges2/train", target_size=(224, 224),
                                                    batch_size=BATCH_SIZE, class_mode="categorical")
test_generator = test_datagen.flow_from_directory("Oranges2/test", target_size=(224, 224), batch_size=BATCH_SIZE,
                                                    class_mode="categorical")

model.fit_generator(train_generator, steps_per_epoch=int(600 / BATCH_SIZE), epochs=EPOCHS,
                    validation_data=test_generator,
                    validation_steps=int(200 / BATCH_SIZE), callbacks=[checkpoint, lr_scheduler])
