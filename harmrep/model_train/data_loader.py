"""
Dataset for Tensorflow Dataloader
"""
import ast
import os
import random
import sys

import numpy as np
import tensorflow as tf

from ..encodings.enc_int import EncoderInterface
from .utils import normalize

class MusicDatasetOneFile(tf.keras.utils.Sequence):
    """Load Dataset for any encoding - Songs in one file"""

    def __init__(self, encoder: EncoderInterface, sample_len=1, ids=None) -> None:
        self.encoder = encoder
        self.index_mapper = []

        if ids is not None and len(ids) > 0:
            self.init_dataset(ids, seq_len=sample_len)

    def init_dataset(self, songs, batch_size=64, seq_len=50, shuffle=True, drop_last=True, augmentation=None, saved_augmentations=None, path=None, model_type='lstm'):
        """
        Sets up an array containing a pd index (the song name), index of start sample, and the number of samples,
        ie. [(0, "Song:1", 10, N)]
        for use in indexing a specific section

        augmentation: list of augmentation methods to apply to the dataset
        possible values:
            'octave-up': transpose the song by upping an octave (OU)
            'octave-down': transpose the song by downing an octave (OD)
            'octave-up-down': transpose the song by upping and downing an octave (OUD)
            'fifth-up': transpose the song by upping a fifth (FUx)
            'fifth-down': transpose the song by downing a fifth (FDx)
            'fifth-up-down': transpose the song by upping and downing a fifth (FOU)
            'fifth-random-(x)': transpose the song by randomly transposing the song x times in fifths (FRx)
            'transpose-all-up': transpose the song by all possible transpositions (UP)
            'transpose-all-down': transpose the song by all possible transpositions (DW)
            'transpose-all-up-down': transpose the song by all possible transpositions (TUPDW)
        """
        self.index_mapper = []
        self.data = songs
        self.saved_augmentations = saved_augmentations
        self.sample_len = seq_len
        self.model = model_type

        self.batch_size = batch_size
        self.shuffle = shuffle
        self.drop_last = drop_last

        if path:
            if os.path.exists(path):
                self.load_state(path)
                return

        if augmentation is None:
            augmentation = []

        fifth_random_samples = []
        if any('fifth-random' in x for x in augmentation):
            augm_type = [x for x in augmentation if 'fifth-random' in x][0]
            number_times = augm_type.split('-')[2]
            fifth_random_samples = random.sample(
                [*range(-5, -1, 1), *range(1, 5, 1)], int(number_times))

        num_sample = 0
        for num, file in enumerate(self.data):
            if file is not None:
                if self.encoder.name == 'abc':
                    self.data[num] = '\n'.join(file.split('\n')[7:])
                    file = self.data[num]

                old = self.encoder.sample_file(file, num, self.sample_len)
                if old is not None:
                    song_tuple = (num_sample, old[0], old[1], 'N')
                    self.index_mapper.append(song_tuple)
                    num_sample += old[1]

                    if len(augmentation) > 0:
                        if self.encoder.name != 'abc':
                            augms = self.create_augmentations(
                                song_tuple, augmentation, fifth_random_samples)
                            self.index_mapper.extend(augms)
                            num_sample += old[1] * len(augms)
                        else:
                            if self.saved_augmentations is None:
                                raise Exception(
                                    'Saved augmentations is None, but augmentation is not None')
                            for key, aug in self.saved_augmentations[num].items():
                                aug = '\n'.join(aug.split('\n')[7:])
                                self.saved_augmentations[num][key] = aug
                                old_aug = self.encoder.sample_file(
                                    aug, num, self.sample_len)
                                if old_aug is not None:
                                    aug_tuple = (
                                        num_sample, old_aug[0], old_aug[1], key)
                                    self.index_mapper.append(aug_tuple)
                                    num_sample += old_aug[1]

        if path:
            self.save_state(path)

    def create_augmentations(self, song_tuple, augmentation_list, fifth_random_samples=None):
        """Creates a list of augmented song indexes from a song tuple and a list of augmentation types"""

        num_sample = song_tuple[0]

        augmented_tuples = []
        for augm_type in augmentation_list:
            num_sample += song_tuple[2]

            if augm_type == 'octave-up':
                augmented_tuples.append(
                    (num_sample, song_tuple[1], song_tuple[2], 'OU'))
            elif augm_type == 'octave-down':
                augmented_tuples.append(
                    (num_sample, song_tuple[1], song_tuple[2], 'OD'))
            elif augm_type == 'octave-up-down':
                augmented_tuples.append(
                    (num_sample, song_tuple[1], song_tuple[2], 'OU'))
                augmented_tuples.append(
                    (num_sample + song_tuple[2], song_tuple[1], song_tuple[2], 'OD'))
                num_sample += song_tuple[2]
            elif augm_type == 'fifth-up':
                augmented_tuples.append(
                    (num_sample, song_tuple[1], song_tuple[2], 'FU'))
            elif augm_type == 'fifth-down':
                augmented_tuples.append(
                    (num_sample, song_tuple[1], song_tuple[2], 'FD'))
            elif augm_type == 'fifth-up-down':
                augmented_tuples.append(
                    (num_sample, song_tuple[1], song_tuple[2], 'FU'))
                augmented_tuples.append(
                    (num_sample + song_tuple[2], song_tuple[1], song_tuple[2], 'FD'))
                num_sample += song_tuple[2]
            elif 'fifth-random' in augm_type:
                if fifth_random_samples is None:
                    number_times = augm_type.split('-')[2]
                    fifth_random_samples = random.sample(
                        [*range(-5, -1, 1), *range(1, 5, 1)], int(number_times))

                for i, f_t in enumerate(fifth_random_samples):
                    augmented_tuples.append(
                        (num_sample + (i*song_tuple[2]), song_tuple[1], song_tuple[2],
                         f'F{"D" if f_t < 0 else "U"}{abs(f_t) if f_t > 1 or f_t < -1 else ""}'))

                num_sample += (len(fifth_random_samples)-1)*song_tuple[2]
            elif augm_type == 'transpose-all-up':
                augmented_tuples.extend(
                    [(num_sample + ((i-1)*song_tuple[2]), song_tuple[1], song_tuple[2], f'UP{i}')
                     for i in range(1, 12)])
                num_sample += 11*song_tuple[2]

            elif augm_type == 'transpose-all-down':
                augmented_tuples.extend(
                    [(num_sample + ((i-1)*song_tuple[2]), song_tuple[1], song_tuple[2], f'DW{i}')
                        for i in range(1, 12)])
                num_sample += 11*song_tuple[2]

            elif augm_type == 'transpose-all-up-down':
                augmented_tuples.extend(
                    [(num_sample + ((i-1)*song_tuple[2]), song_tuple[1], song_tuple[2], f'UP{i}')
                        for i in range(1, 12)])
                num_sample += 11*song_tuple[2]

                augmented_tuples.extend([(num_sample + ((i-1)*song_tuple[2]), song_tuple[1], song_tuple[2], f'DW{i}')
                                         for i in range(1, 12)])
                num_sample += 10*song_tuple[2]

        return augmented_tuples

    def __getitem__(self, idx):
        """
        __getitem__ should return a complete batch
        """
        if (self.index_mapper is None or len(self.index_mapper) == 0):
            raise Exception("Trying to get item on empty dataset")

        if idx >= len(self):
            raise Exception("Trying to get non-existent item")

        batch = [self.__getsingleitem__(id) for id in range(
            self.batch_size * idx, self.batch_size*(idx+1))]
        batch_x = np.asarray([b[0] for b in batch])

        if self.model.lower() == 'vae':
            return batch_x, batch_x
        else:
            raise Exception("Model not supported yet")

    def __getsingleitem__(self, idx):
        song_id, ind_start, ind_end, augmentation = self.__fetchitem__(idx)

        song = self.data[int(song_id)]
        if augmentation != 'N':
            if any(x in self.encoder.name for x in ['dft128', 'tonnetz']) and self.saved_augmentations:
                song = self.saved_augmentations[int(song_id)][augmentation]
            else:
                song = self.encoder.augment_song(song, augmentation)

        try:
            dtype = tf.float32 if 'dft' in self.encoder.name else tf.int32
            song_x = tf.convert_to_tensor(
                song[ind_start:ind_end], dtype=dtype)
            song_y = tf.convert_to_tensor(song[ind_end], dtype=dtype)
            return song_x, song_y
        except Exception as exc:
            print(f'Error on song {song_id} with augmentation {augmentation}')
            print(exc)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[  # type: ignore
                1]
            print(exc_type, fname, exc_tb.tb_lineno)  # type: ignore
            return [], []

    def __fetchitem__(self, idx):
        item = min(self.index_mapper, key=lambda x: idx -
                   x[0] if idx-x[0] >= 0 else np.inf)

        song_id = item[1].split('Song:')[1]
        item_start = idx - item[0]
        item_end = item_start + self.sample_len

        return song_id, item_start, item_end, item[3]

    def __len__(self):
        return int(sum(item[2] for item in self.index_mapper) / self.batch_size)

    def on_epoch_end(self):
        """Shuffle Samples on Epoch End"""
        if self.shuffle is True:
            np.random.shuffle(self.index_mapper)

    def save_state(self, file_name):
        """Save the current state of the dataset"""
        with open(file_name, "w", encoding="utf-8") as file:
            for index_value in self.index_mapper:
                file.write(str(index_value) + "\n")

    def load_state(self, file_name):
        """Load the current state of the dataset"""
        with open(file_name, "r", encoding="utf-8") as file:
            self.index_mapper = []
            for line in file:
                self.index_mapper.append(ast.literal_eval(line.strip()))


class ABCDataGenerator(MusicDatasetOneFile):
    """Data Generator for ABC Dataset"""

    def __init__(self, encoder: EncoderInterface, sample_len=1, ids=None):
        return super().__init__(encoder, sample_len, ids)

    def init_dataset(self, songs, batch_size=64, seq_len=50, shuffle=True, drop_last=True, augmentation=None, saved_augmentations=None, path=None, model_type='lstm'):
        super().init_dataset(songs, batch_size, seq_len, shuffle, drop_last,
                             augmentation, saved_augmentations, path, model_type)

        dictionary = self.encoder.get_dictionary_of_notes()

        def get_data(song, dictionary):
            if 'X' in song:
                song = '\n'.join(song.split('\n')[7:])
            return tf.convert_to_tensor(tf.one_hot([dictionary.index(i) for i in song], len(dictionary), dtype=tf.int32), dtype=tf.int32)

        self.dataset = [
            get_data(song, dictionary) for song in self.data  # type: ignore
        ]
        if self.saved_augmentations is not None:
            self.saved_augmentations_dataset = [
                {key: get_data(song, dictionary)
                 for key, song in aug.items()}  # type: ignore
                for aug in self.saved_augmentations
            ]

    def __getsingleitem__(self, idx):
        song_id, ind_start, ind_end, augmentation = self.__fetchitem__(idx)

        dataset = self.dataset

        if augmentation == 'N':
            song = dataset[int(song_id)]
        else:
            saved_augmentations_dataset = self.saved_augmentations_dataset
            song = saved_augmentations_dataset[int(song_id)][augmentation]

        try:
            song_x = tf.slice(song, [ind_start, 0], [ind_end - ind_start, -1])
            song_y = tf.slice(song, [ind_end, 0], [1, -1])
            return song_x, song_y
        except Exception as exc:
            print(f'Error on song {song_id} with augmentation {augmentation}')
            print(exc)
            exc_type, _, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1] # type: ignore
            print(exc_type, fname, exc_tb.tb_lineno) # type: ignore

    def __getitem__(self, idx):
        """
        __getitem__ should return a complete batch
        """
        if (self.index_mapper is None or len(self.index_mapper) == 0):
            raise Exception("Trying to get item on empty dataset")

        if idx >= len(self):
            raise Exception("Trying to get non-existent item")

        start_idx = self.batch_size * idx
        end_idx = self.batch_size * (idx + 1)
        batch = [self.__getsingleitem__(i) for i in range(start_idx, end_idx)]
        batch_x = np.asarray([b[0] for b in batch]) # type: ignore

        if self.model.lower() == 'vae':
            return batch_x, batch_x
        batch_y = np.asarray([b[1] for b in batch]) # type: ignore
        return batch_x, batch_y
