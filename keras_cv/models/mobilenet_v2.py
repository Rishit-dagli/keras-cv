# Copyright 2022 The KerasCV Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""MobileNet v2 models for Keras.

MobileNetV2 is a general architecture and can be used for multiple use cases.
Depending on the use case, it can use different input layer size and
different width factors. This allows different width models to reduce
the number of multiply-adds and thereby
reduce inference cost on mobile devices.
MobileNetV2 is very similar to the original MobileNet,
except that it uses inverted residual blocks with
bottlenecking features. It has a drastically lower
parameter count than the original MobileNet.
MobileNets support any input size greater
than 32 x 32, with larger image sizes
offering better performance.
The number of parameters and number of multiply-adds
can be modified by using the `alpha` parameter,
which increases/decreases the number of filters in each layer.
By altering the image size and `alpha` parameter,
all 22 models from the paper can be built, with ImageNet weights provided.
The paper demonstrates the performance of MobileNets using `alpha` values of
1.0 (also called 100 % MobileNet), 0.35, 0.5, 0.75, 1.0, 1.3, and 1.4
For each of these `alpha` values, weights for 5 different input image sizes
are provided (224, 192, 160, 128, and 96).
The following table describes the performance of
MobileNet on various input sizes:
------------------------------------------------------------------------
MACs stands for Multiply Adds
 Classification Checkpoint|MACs (M)|Parameters (M)|Top 1 Accuracy|Top 5 Accuracy
--------------------------|------------|---------------|---------|----|---------
| [mobilenet_v2_1.4_224]  | 582 | 6.06 |          75.0 | 92.5 |
| [mobilenet_v2_1.3_224]  | 509 | 5.34 |          74.4 | 92.1 |
| [mobilenet_v2_1.0_224]  | 300 | 3.47 |          71.8 | 91.0 |
| [mobilenet_v2_1.0_192]  | 221 | 3.47 |          70.7 | 90.1 |
| [mobilenet_v2_1.0_160]  | 154 | 3.47 |          68.8 | 89.0 |
| [mobilenet_v2_1.0_128]  | 99  | 3.47 |          65.3 | 86.9 |
| [mobilenet_v2_1.0_96]   | 56  | 3.47 |          60.3 | 83.2 |
| [mobilenet_v2_0.75_224] | 209 | 2.61 |          69.8 | 89.6 |
| [mobilenet_v2_0.75_192] | 153 | 2.61 |          68.7 | 88.9 |
| [mobilenet_v2_0.75_160] | 107 | 2.61 |          66.4 | 87.3 |
| [mobilenet_v2_0.75_128] | 69  | 2.61 |          63.2 | 85.3 |
| [mobilenet_v2_0.75_96]  | 39  | 2.61 |          58.8 | 81.6 |
| [mobilenet_v2_0.5_224]  | 97  | 1.95 |          65.4 | 86.4 |
| [mobilenet_v2_0.5_192]  | 71  | 1.95 |          63.9 | 85.4 |
| [mobilenet_v2_0.5_160]  | 50  | 1.95 |          61.0 | 83.2 |
| [mobilenet_v2_0.5_128]  | 32  | 1.95 |          57.7 | 80.8 |
| [mobilenet_v2_0.5_96]   | 18  | 1.95 |          51.2 | 75.8 |
| [mobilenet_v2_0.35_224] | 59  | 1.66 |          60.3 | 82.9 |
| [mobilenet_v2_0.35_192] | 43  | 1.66 |          58.2 | 81.2 |
| [mobilenet_v2_0.35_160] | 30  | 1.66 |          55.7 | 79.1 |
| [mobilenet_v2_0.35_128] | 20  | 1.66 |          50.8 | 75.0 |
| [mobilenet_v2_0.35_96]  | 11  | 1.66 |          45.5 | 70.4 |

References:
    - [MobileNetV2: Inverted Residuals and Linear Bottlenecks](
        https://arxiv.org/abs/1801.04381) (CVPR 2018)
    - [Based on the Original keras.applications MobileNetv2](
        https://github.com/keras-team/keras/blob/master/keras/applications/mobilenet_v2.py)
"""

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import backend
from tensorflow.keras import layers


def CorrectPad(kernel_size, name=None):
    """Zero-padding for 2D convolution with downsampling.

    Args:
        kernel_size: an integer or tuple/list of 2 integers.
        name: string, layer label.

    Returns:
        a function that takes an input Tensor representing a CorrectPad.
    """
    if name is None:
        name = f"correct_pad_{backend.get_uid('correct_pad')}"

    def apply(x):
        img_dim = 1
        input_size = backend.int_shape(x)[img_dim : (img_dim + 2)]

        if isinstance(kernel_size, int):
            kernel_size = (kernel_size, kernel_size)

        if input_size[0] is None:
            adjust = (1, 1)
        else:
            adjust = (1 - input_size[0] % 2, 1 - input_size[1] % 2)
        correct = (kernel_size[0] // 2, kernel_size[1] // 2)
        return (
            (correct[0] - adjust[0], correct[0]),
            (correct[1] - adjust[1], correct[1]),
        )

    return apply



def Depth(divisor=8, min_value=None, name=None):
    """Ensure that all layers have a channel number that is divisble by the `divisor`.

    Args:
        divisor: integer, the value by which a channel number should be divisble,
            defaults to 8.
        min_value: float, minimum value for the new tensor.
        name: string, layer label.

    Returns:
        a function that takes an input Tensor representing a Depth layer.
    """
    if name is None:
        name = f"depth_{backend.get_uid('depth')}"

    if min_value is None:
        min_value = divisor

    def apply(x):
        new_x = max(min_value, int(x + divisor / 2) // divisor * divisor)

        # Make sure that round down does not go down by more than 10%.
        if new_x < 0.9 * x:
            new_x += divisor
        return new_x

    return apply

def InvertedResBlock(expansion, stride, alpha, filters, block_id, name=None):
    if name is None:
        name = f"inverted_res_block_{backend.get_uid('inverted_res_block')}"

    prefix = "block_{}_".format(block_id)

    pointwise_conv_filters = int(filters * alpha)
    # Ensure the number of filters on the last 1x1 convolution is divisible by
    # 8.
    pointwise_filters = Depth(pointwise_conv_filters, 8)

    batch_norm_1 = layers.BatchNormalization(
        axis=-1,
        epsilon=1e-3,
        momentum=0.999,
        name=prefix + "expand_BN",
    )
    correct_pad = CorrectPad(3)
    activation_1 = layers.ReLU(6.0, name=prefix + "expand_relu")
    depthwise_conv2d_1 = layers.DepthwiseConv2D(
        kernel_size=3,
        strides=stride,
        activation=None,
        use_bias=False,
        padding="same" if stride == 1 else "valid",
        name=prefix + "depthwise",
    )
    batch_norm_2 = layers.BatchNormalization(
        axis=-1,
        epsilon=1e-3,
        momentum=0.999,
        name=prefix + "depthwise_BN",
    )
    activation_2 = layers.ReLU(6.0, name=prefix + "depthwise_relu")
    conv2d_1 = layers.Conv2D(
        pointwise_filters,
        kernel_size=1,
        padding="same",
        use_bias=False,
        activation=None,
        name=prefix + "project",
    )
    batch_norm_3 = layers.BatchNormalization(
        axis=-1,
        epsilon=1e-3,
        momentum=0.999,
        name=prefix + "project_BN",
    )
    add = layers.Add(name=prefix + "add")

    def apply(inputs):
        in_channels = backend.int_shape(inputs)[-1]

        x = inputs

        if block_id:
            # Expand with a pointwise 1x1 convolution.
            x = layers.Conv2D(
                expansion * in_channels,
                kernel_size=1,
                padding="same",
                use_bias=False,
                activation=None,
                name=prefix + "expand",
            )(x)
            x = batch_norm_1(x)
            x = activation_1(x)
        else:
            prefix = "expanded_conv_"

        # Depthwise 3x3 convolution.
        if stride == 2:
            x = layers.ZeroPadding2D(padding=correct_pad(x), name=prefix + "pad")(x)

        x = depthwise_conv2d_1(x)
        x = batch_norm_2(x)

        x = activation_2(x)

        # Project with a pointwise 1x1 convolution.
        x = conv2d_1(x)
        x = batch_norm_3(x)

        if in_channels == pointwise_filters and stride == 1:
            return add([inputs, x])

        return x

    return apply
