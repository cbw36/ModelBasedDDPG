import tensorflow as tf

from tensorflow.python.layers import base


class AddCoords(base.Layer):
    """Add coords to a tensor"""
    def __init__(self, x_dim=64, y_dim=64, with_r=False):
        super(AddCoords, self).__init__()
        self.x_dim = x_dim
        self.y_dim = y_dim
        self.with_r = with_r

    def call(self, input_tensor, **kwargs):
        """
        input_tensor: (batch, x_dim, y_dim, c)
        """
        batch_size_tensor = tf.shape(input_tensor)[0]
        xx_ones = tf.ones([batch_size_tensor, self.x_dim], dtype=tf.int32)
        xx_ones = tf.expand_dims(xx_ones, -1)
        xx_range = tf.tile(tf.expand_dims(tf.range(self.y_dim), 0),
                          [batch_size_tensor, 1])
        xx_range = tf.expand_dims(xx_range, 1)
        xx_channel = tf.matmul(xx_ones, xx_range)
        xx_channel = tf.expand_dims(xx_channel, -1)
        yy_ones = tf.ones([batch_size_tensor, self.y_dim], dtype=tf.int32)
        yy_ones = tf.expand_dims(yy_ones, 1)
        yy_range = tf.tile(tf.expand_dims(tf.range(self.x_dim), 0),
                          [batch_size_tensor, 1])
        yy_range = tf.expand_dims(yy_range, -1)
        yy_channel = tf.matmul(yy_range, yy_ones)
        yy_channel = tf.expand_dims(yy_channel, -1)
        xx_channel = tf.cast(xx_channel, 'float32') / (self.x_dim - 1)
        yy_channel = tf.cast(yy_channel, 'float32') / (self.y_dim - 1)
        xx_channel = xx_channel*2 - 1
        yy_channel = yy_channel*2 - 1
        ret = tf.concat([input_tensor, xx_channel, yy_channel], axis=-1)
        if self.with_r:
            rr = tf.sqrt(tf.square(xx_channel) + tf.square(yy_channel))
            ret = tf.concat([ret, rr], axis=-1)
        return ret


class CoordConv(base.Layer):
    """CoordConv layer as in the paper."""
    def __init__(self, x_dim, y_dim, with_r, *args, **kwargs):
        super(CoordConv, self).__init__()
        self.addcoords = AddCoords(x_dim=x_dim,
                               y_dim=y_dim,
                               with_r=with_r)
        self.conv = tf.layers.Conv2D(*args, **kwargs)

    def call(self, input_tensor, **kwargs):
        ret = self.addcoords(input_tensor)
        ret = self.conv(ret)
        return ret


def coord_conv(x_dim, y_dim, with_r, inputs, *args, **kwargs):
    layer = CoordConv(x_dim, y_dim, with_r, *args, **kwargs)
    return layer.apply(inputs)


class DqnModel:
    def __init__(self, prefix):
        self.prefix = '{}_dqn'.format(prefix)

    def predict(self, workspace_image, reuse_flag):
        conv1 = coord_conv(55, 111, False, workspace_image, 32, 8, 4, padding='same', activation=tf.nn.relu, use_bias=True,
                           name='{}_conv1'.format(self.prefix), _reuse=reuse_flag)
        conv2 = tf.layers.conv2d(conv1, 64, 4, 2, padding='same', activation=tf.nn.relu, use_bias=True,
                                 name='{}_conv2'.format(self.prefix), reuse=reuse_flag)
        # conv3 = tf.layers.conv2d(conv2, 64, 3, 1, padding='same', activation=tf.nn.relu, use_bias=True)
        # flat = tf.layers.flatten(conv3)
        flat = tf.layers.flatten(conv2, name='{}_flat'.format(self.prefix))
        dense1 = tf.layers.dense(flat, 512, activation=tf.nn.relu, name='{}_dense1'.format(self.prefix),
                                 reuse=reuse_flag)
        dense2 = tf.layers.dense(dense1, 512, activation=None, name='{}_dense2'.format(self.prefix), reuse=reuse_flag)
        return dense2

