"""
Class for training any Network with any dataset encoding (Tensorflow)
"""
import bz2
import csv
import glob
import os

import _pickle as cPickle
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

from .data_loader import MusicDatasetOneFile, ABCDataGenerator
from .vae import VAE

np.random.seed(42)  # keras seed fixing
tf.random.set_seed(42)  # tensorflow seed fixing


class Train:
    """Train a model"""

    encoding = ''
    encoder = None

    model = None

    results = {
        'acc': {},
        'loss': {}
    }

    def __init__(self, encoder, data_dir=None, kfolds=2):
        """Start Trainer"""
        self.encoder = encoder
        self.filename = encoder.get_name_to_extract()

        self.data_dir = '_datasets_encoded'
        if data_dir is not None:
            self.data_dir = data_dir

        if self.data_dir[-5:] == '.pbz2':
            with bz2.BZ2File(self.data_dir, "rb") as filepath:
                self.dataset = cPickle.load(filepath)

            if encoder.name == 'abc':
                self.training_dataset = ABCDataGenerator(encoder)
                self.test_dataset = ABCDataGenerator(encoder)
            else:
                self.training_dataset = MusicDatasetOneFile(encoder)
                self.test_dataset = MusicDatasetOneFile(encoder)
        else:
            raise Exception("Not implemented yet")

        self.output_dir = '_results'

    def get_traintest_dataset(self, train_ids, test_ids, model_type='vae', batch_size=64, seq_len=50, augmentations=None, augmentation_path=None, path_to_save=''):
        """
        GET train and test dataset for ids
        """
        train_augmentations = None
        if augmentation_path is not None:
            print('Loading augmentations...')
            with bz2.BZ2File(augmentation_path, "rb") as openfile:
                while True:
                    try:
                        saved_augmentation = cPickle.load(openfile)
                    except EOFError:
                        break
            train_augmentations = list(
                map(lambda i: saved_augmentation[i], train_ids))

        self.training_dataset.init_dataset(songs=list(
            map(lambda i: self.dataset[i], train_ids)),
            batch_size=batch_size, seq_len=seq_len, shuffle=True, drop_last=True, augmentation=augmentations,  # type: ignore
            saved_augmentations=train_augmentations, path=os.sep.join(path_to_save.split(os.sep)[:-1] + ['training_dataset_indexes.txt']),
            model_type=model_type)  # type: ignore

        self.test_dataset.init_dataset(songs=list(
            map(lambda i: self.dataset[i], test_ids)),
            batch_size=batch_size, seq_len=seq_len, shuffle=True, drop_last=True,
            path=os.sep.join(path_to_save.split(os.sep)[:-1] + ['test_dataset_indexes.txt']),
            model_type=model_type)  # type: ignore

    def load_model(self, run_name, model_type='lstm'):
        """Load model"""
        output_folder = os.sep.join(
            [self.output_dir, self.filename, 'models', f'run_{run_name}'])

        last_epoch = 0
        try:
            with open(os.sep.join([output_folder, 'logs.csv']), 'r', encoding='utf-8') as file:
                reader = csv.reader(file, delimiter="\n")
                last_epoch = int(list(reader)[-1][0].split(',')[0])
                file.close()

            models = glob.glob(os.sep.join([output_folder, '*.h5']))
            model_path = list(
                filter(lambda name: f'model-{last_epoch+1:03d}' in name, models))

            print(f'Loading MODEL: {model_path}\n')

            if len(model_path) > 0:
                self.model.load_model(model_path[0]) # type: ignore
                self.model._model.load_weights(model_path[0])  # type: ignore
                last_epoch += 1

        except Exception as exc:
            print(exc)
            last_epoch = 0

        return last_epoch

    def create_callbacks(self, run_name, model_type='vae'):
        """
        Create Callbacks
        """
        output_folder = os.sep.join(
            [self.output_dir, self.filename, 'models', f'run_{run_name}'])
        os.makedirs(output_folder, exist_ok=True)

        logdir = os.sep.join(
            [self.output_dir, self.filename, 'logs', f'run_{run_name}'])
        os.makedirs(logdir, exist_ok=True)

        filepath_save = os.path.abspath(
            output_folder + '/model-{epoch:03d}-{loss:.4f}-{val_loss:.4f}.h5')

        save_weights_only = False
        if model_type == 'vae':
            save_weights_only = True

        checkpoint = tf.keras.callbacks.ModelCheckpoint(
            filepath_save,
            save_weights_only=save_weights_only,
            save_freq='epoch',
            monitor='loss',
            verbose=2,
            save_best_only=False,
            mode='min'
        )

        # define callbacks
        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(monitor='loss', factor=0.1,
                                                         patience=10, min_lr=0.000001)  # type: ignore

        csvlog = tf.keras.callbacks.CSVLogger(
            output_folder + '/logs.csv', separator=",", append=True)

        tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=logdir,
                                                              histogram_freq=0)
        earlystop = tf.keras.callbacks.EarlyStopping(patience=10) # type: ignore
        callbacks_list = [checkpoint, csvlog, tensorboard_callback, earlystop]

        return callbacks_list, reduce_lr, filepath_save

    def start_training(self, run_name='01',
                       batch_size=64, epochs=1000,
                       learning_rate=0.001, dropout=0.2,
                       hidden_size=512, num_layers=1,
                       sequence_length=10, test_size=0.2,
                       augmentations=None,
                       latent_space=3,
                       model_type='vae'):
        """Start training"""

        if self.encoder is None:
            raise Exception('Encoder not defined')

        callbacks_list, _, saving_path = self.create_callbacks(
            run_name=run_name, model_type=model_type)

        train_ids_path = os.sep.join(saving_path.split(
            os.sep)[:-1] + ['training_indexes.npy'])
        test_ids_path = os.sep.join(saving_path.split(os.sep)[
                                    :-1] + ['test_indexes.npy'])

        if os.path.exists(train_ids_path) and os.path.exists(test_ids_path):
            print('LOADING IDS')
            train_ids = np.load(train_ids_path)
            test_ids = np.load(test_ids_path)
        else:
            print('GENERATING AND SAVING IDS')
            train_ids, test_ids = train_test_split(
                range(len(self.dataset)), test_size=test_size, random_state=25)

            train_ids = np.array(sorted(train_ids))
            test_ids = np.array(sorted(test_ids))

            np.save(train_ids_path, train_ids)
            np.save(test_ids_path, test_ids)

        augmentations_path = None
        if any(x in self.encoder.name for x in ['dft128', 'tonnetz', 'abc']):
            augmentations_path = self.data_dir[:-5] + '_augmented.pbz2'

        self.get_traintest_dataset(
            train_ids, test_ids, model_type=model_type, batch_size=batch_size, seq_len=sequence_length, augmentations=augmentations, augmentation_path=augmentations_path, path_to_save=saving_path)

        print('\n---START MODEL---')
        n_vocab, needs_embedding = self.encoder.get_vocab_size_and_embedding()  # type: ignore
        is_float = True if 'dft' in self.encoder.name else False  # type: ignore
        print(
            f'Encoding {self.encoder.name} uses {"float embeddings" if is_float else "many hot embeddings"}!')

        if model_type == 'vae':
            self.model = VAE(latent_space, n_vocab, lstm_no_enc=num_layers, lstm_no_dec=num_layers, lstm_size=hidden_size, dropout=dropout,
                             learning_rate=learning_rate, seq_len=sequence_length, batch_size=batch_size, needs_embedding=needs_embedding, is_float=is_float, is_pos=False)
        else:
            raise ValueError('Model type not recognized!')

        initial_epoch = self.load_model(run_name=run_name)
        self.model.plot_model(to_file=os.sep.join(saving_path.split(os.sep)[:-1] + ['model.png'])) # type: ignore

        print('STARTING TRAINING')
        self.model.fit(self.training_dataset, validation_data=self.test_dataset,
                       initial_epoch=initial_epoch, epochs=epochs, callbacks=callbacks_list, verbose="auto")
