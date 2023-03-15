"""
Defining Tensorflow VAE Model
"""
import sys

import numpy as np

import tensorflow as tf
from keras import backend as K

sys.setrecursionlimit(10000)


def compute_loss(x, x_decoded, z_mean, z_log_sigma):
    """Compute VAE Loss"""
    x_reconst_loss = tf.keras.losses.categorical_crossentropy(x, x_decoded)
    kl_div = -0.5 * tf.reduce_mean(1 + z_log_sigma - tf.square(z_mean) - tf.exp(z_log_sigma))
    return x_reconst_loss + kl_div

def compute_loss_3(x, x_decoded, z_mean, z_log_sigma):
    """Compute VAE Loss"""
    x_reconst_loss = tf.keras.losses.binary_crossentropy(x, x_decoded)
    kl_div = -0.5 * tf.reduce_mean(1 + z_log_sigma - tf.square(z_mean) - tf.exp(z_log_sigma))
    return x_reconst_loss + kl_div

def compute_loss_2(inputs, decoded, z_mean, z_log_sigma):
    """ This computes the loss of the VAE """
    # KL divergence
    kl_div = - 0.5 * tf.reduce_sum(1 + z_log_sigma -
                                   tf.math.pow(z_mean, 2) - tf.math.exp(z_log_sigma))
    def mse(x, y):
        """ This computes the mean squared error between two tensors """
        return tf.reduce_mean(tf.square(x - y))
    # Reconstruction loss
    x_reconst_loss = mse(decoded, inputs)
    return x_reconst_loss + kl_div


class VAE():
    """
    VAE Model Implementation using Tensorflow
    - Learn Latent Space Representation of Music
    - Generate Music from Latent Space
    """

    def __init__(self, latent_dim, n_vocab, lstm_no_enc=1, lstm_no_dec=1, lstm_size=512, dropout=0.3, learning_rate=0.00001, seq_len=100, batch_size=64, needs_embedding=False, is_float=False, is_pos=False, verbose=True) -> None:
        """Initialize VAE Model"""

        self.latent_dim = latent_dim

        K.clear_session()

        _input, z_mean, z_log_sigma, z_value = self.define_encoder_network(n_vocab, lstm_no_enc, lstm_size,
                                                                           False, dropout, seq_len, needs_embedding)
        output = self.define_decoder_network(z_value, n_vocab, lstm_no_dec, lstm_size,
                                             False, dropout, seq_len, needs_embedding)

        self._model = tf.keras.Model(_input, output, name="vae")

        if needs_embedding:
            self._model.add_loss(compute_loss(_input, output, z_mean, z_log_sigma))
            self._model.compile(optimizer=tf.keras.optimizers.legacy.Adam(
                learning_rate=learning_rate), metrics=['accuracy', 'mse', 'kullback_leibler_divergence'])
        else:
            self._model.add_loss(compute_loss_2(_input, output, z_mean, z_log_sigma))
            self._model.compile(optimizer=tf.keras.optimizers.legacy.Adam(
                learning_rate=learning_rate), metrics=['accuracy', 'mse', 'kullback_leibler_divergence'])

        if verbose:
            self._model.summary()

    def define_encoder_network(self, n_vocab, lstm_no, lstm_size, is_float, dropout, seq_len, needs_embedding):
        """Define Encoder Network"""
        inputs = tf.keras.layers.Input(
            shape=(seq_len, n_vocab), name='input_layer_without_embedding')
        # intermediate dimension
        encoded = tf.keras.layers.LSTM(
            lstm_size, activation='relu', dropout=dropout, return_sequences=False, name='lstm_encoder')(inputs)

        # z_layer
        z_mean = tf.keras.layers.Dense(
            self.latent_dim, name='dense_z_mean')(encoded)
        z_log_sigma = tf.keras.layers.Dense(
            self.latent_dim,  name='dense_z_log_sigma')(encoded)

        def sampling(args):
            """Sampling Function"""
            z_mean, z_log_sigma = args
            epsilon = K.random_normal(
                shape=(K.shape(z_mean)[0], self.latent_dim), mean=0., stddev=1.)
            return z_mean + K.exp(z_log_sigma * 0.5) * epsilon

        z_value = tf.keras.layers.Lambda(sampling, name='lambda_encoder', output_shape=(
            self.latent_dim,))([z_mean, z_log_sigma])

        return inputs, z_mean, z_log_sigma, z_value

    def define_decoder_network(self, z_value, n_vocab, lstm_no, lstm_size, is_float, dropout, seq_len, needs_embedding):
        """Define Decoder Network"""

        # Reconstruction decoder
        latent_inputs = tf.keras.layers.RepeatVector(
            seq_len, name='repeat_vector_decoder')(z_value)

        if lstm_no <= 0:
            raise Exception('LSTM No. must be greater than 0')

        # Add LSTM layers
        for i in range(lstm_no):
            decoded = tf.keras.layers.LSTM(
                lstm_size, activation='relu', dropout=dropout, return_sequences=True, name=f'lstm_decoder_{i}')(latent_inputs if i == 0 else decoded) # type: ignore

        # Output layer
        activation = 'softmax'
        if not needs_embedding:
            activation = 'linear'

        return tf.keras.layers.TimeDistributed(
            tf.keras.layers.Dense(n_vocab, activation=activation, name='dense_decoder'))(decoded) # type: ignore

    def get_config(self):
        """Get Model Config"""
        if self._model is None:
            raise Exception('Model is not loaded yet')

        config = self._model.get_config()
        return config

    def fit(self, x, y=None, initial_epoch=0, validation_data=None, epochs=10, batch_size=64, callbacks=None, verbose="auto"):
        """Fit VAE to data"""
        if self._model is None:
            raise Exception('Model is not loaded yet')

        if y is None:
            if validation_data is None:
                validation_data = x

            self._model.fit(x,
                            validation_data=validation_data,
                            initial_epoch=initial_epoch,
                            epochs=epochs,
                            batch_size=batch_size,
                            callbacks=callbacks,
                            verbose=verbose)
        else:
            if validation_data is None:
                validation_data = (x, y)

            self._model.fit(x, y,
                            validation_data=validation_data,
                            initial_epoch=initial_epoch,
                            epochs=epochs,
                            batch_size=batch_size,
                            callbacks=callbacks,
                            verbose=verbose)

    def check_model_at_layer(self, input, layer=0):
        """Check the model at a specific layer"""
        if self._model is None:
            raise Exception('Model is not loaded yet')

        get_x_layer_output = K.function([self._model.layers[0].input],
                                        [self._model.layers[layer].output])
        return get_x_layer_output([input])[0]

    def check_all_layers(self, input):
        """Check all layers of the model"""
        if self._model is None:
            raise Exception('Model is not loaded yet')

        for i, layer in enumerate(self._model.layers):
            pred = self.check_model_at_layer(input, i)

            if isinstance(pred, np.ndarray):
                print(f'Layer {i}: {layer.name}, pred shape: {pred.shape}')
            else:
                print(f'Layer {i}: {layer.name}, Normal Layer')

    def load_model(self, model_path):
        """Load a Model with tensorflow backend"""
        self._model.load_weights(model_path)
        self._model.layers[0].trainable = True

    def plot_model(self, show_shapes=False, to_file='vae.png'):
        """Plot the model"""
        tf.keras.utils.plot_model(self._model, to_file, show_shapes=show_shapes)
