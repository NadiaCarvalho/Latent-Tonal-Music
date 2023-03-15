"""This module implements the class App"""
import json
import os

from .utils import run_name_to_dict
from .encodings.enc_factory import EncoderFactory


class App:
    """

    Attributes
    ----------

    Methods
    ----------

    """

    @staticmethod
    def run(mode='chorales', encoding='tonnetz', run_name='SEQ=10-AUG=TUPDW,OUD-BS=256-HD=1024-DP=0.3-LR=0.0001-NL=1-M=VAE-LS=256-V1', epochs=100):
        """
        X1
        """
        if mode == 'construct':
            App.test_chorales(encoding, mode='construct_dataset')
        elif mode == 'train':
            App.test_chorales(encoding, mode='', run_name=run_name)  # , dataset)
        elif mode == 'augment':
            App.test_chorales(encoding, mode='augment_dataset')
        elif mode == 'project':
            App.test_chorales(encoding, mode='project_latent_space', run_name=run_name)
        else:
            print(f"Mode {mode} was not implemented yet.")

    @classmethod
    def test_chorales(cls, encoding='all', mode='construct_dataset', run_name='SEQ=10-AUG=TUPDW,OUD-BS=256-HD=1024-DP=0.3-LR=0.0001-NL=1-M=VAE-LS=256-V1', epochs=100):

        encoder = EncoderFactory().get_encoder(encoding, data_path='music21_bach',
                                               data_name='BachChorales', transposition='C Major')
        if not encoder:
            return

        if mode == 'construct_dataset':
            encoder.start_process("_datasets_encoded", divide_parts=False)
        elif mode == 'test':
            App.test_one_chorale_construction(encoder, chorale_id=7)
        elif mode == 'augment_dataset':
            App.augment_chorales_dataset(encoding)
        elif mode == 'train':
            App.train_chorales(
                encoder, run_name=run_name, epochs=epochs)
        elif mode == 'project_latent_space':
            App.project_vae_latent_space_chorales(
                encoder, run_name=run_name, start_song=0, end_song=None)
        else:
            raise Exception(f"Mode {mode} was not implemented yet.")

    @classmethod
    def test_one_chorale_construction(cls, encoder, chorale_id=1):
        """Test one chorale construction, augmentation and decoding"""

        import music21
        import numpy as np
        np.set_printoptions(threshold=np.inf)  # type: ignore

        # for c in music21.corpus.chorales.Iterator():
        #     print(f'NAME: {c.metadata.movementName}, KEY: {c.analyze("key")}')

        m_choral = music21.corpus.chorales.Iterator(
            returnType='stream')[chorale_id]

        print(m_choral.metadata.title)

        # measure_1 = m_choral.chordify().getElementsByClass('Measure')[0]
        # m_choral.write('midi', f'_logs/choral_{chorale_id}.mid')

        rep = encoder.extract_representation(
            m_choral, transpose=False, divide_parts=False)

        round_rep = np.asarray(rep[:16], dtype=np.float32).round(3)

        print(round_rep)

        #rep2 = encoder.augment_song(rep, augmentation='UP10')

        stream = encoder.decode(rep[:16])
        stream.show()

    @classmethod
    def train_chorales(cls, encoder, epochs=55, test_size=0.4, run_name='SEQ=10-AUG=TUPDW,OUD-BS=64-HD=32-DP=0.3-LR=0.0001-NL=1-V3'):
        """Train Bach Chorales"""

        from .model_train.train import Train

        rn_dict = run_name_to_dict(run_name)
        if 'M' not in rn_dict:
            rn_dict['M'] = 'LSTM'

        train = Train(
            encoder, f'_datasets_encoded/BachChorales_{encoder.name}_res4_transpC-Major_all_songs.pbz2')
        train.start_training(run_name=run_name, dropout=float(rn_dict['DP']), batch_size=int(rn_dict['BS']),
                             epochs=epochs, sequence_length=int(rn_dict['SEQ']), hidden_size=int(rn_dict['HD']),
                             learning_rate=float(rn_dict['LR']), num_layers=int(rn_dict['NL']),
                             model_type=rn_dict['M'].lower(), latent_space=int(rn_dict.get('LS', 3)),
                             test_size=test_size, augmentations=['transpose-all-up-down', 'octave-up-down'])

    @classmethod
    def train_chorales_vae(cls, encoder, epochs=300, test_size=0.4, run_name='SEQ=10-AUG=TUPDW,OUD-BS=64-HD=32-DP=0.3-LR=0.0001-NL=1-M=VAE-V3'):
        """Train Bach Chorales"""

        from .model_train.train_vae import Train

        rn_dict = run_name_to_dict(run_name)
        if 'M' not in rn_dict:
            rn_dict['M'] = 'VAE'

        train = Train(
            encoder, f'_datasets_encoded/BachChorales_{encoder.name}_res4_transpC-Major_all_songs.pbz2')
        train.start_training(run_name=run_name, dropout=float(rn_dict.get('DP', 0.3)), batch_size=int(rn_dict.get('BS', 64)),
                             epochs=epochs, sequence_length=int(rn_dict.get('SEQ', 10)), hidden_size=int(rn_dict.get('HD', 32)),
                             learning_rate=float(rn_dict.get('LR', 0.0001)), num_layers=int(rn_dict.get('NL', 1)),
                             model_type=rn_dict.get('M', 'LSTM').lower(), latent_space=int(rn_dict.get('LS', 3)),
                             test_size=test_size, augmentations=['transpose-all-up-down', 'octave-up-down'])

    @classmethod
    def train_chorales_vae_snl(cls, encoder, epochs=300, test_size=0.4, run_name='SEQ=10-AUG=TUPDW,OUD-BS=64-HD=32-DP=0.3-LR=0.0001-NL=1-M=VAE-V3'):

        from .model_train.train_vae_snl import Train

        rn_dict = run_name_to_dict(run_name)
        if 'M' not in rn_dict:
            rn_dict['M'] = 'VAE'

        train = Train(
            encoder, f'_datasets_encoded/BachChorales_{encoder.name}_res4_transpC-Major_all_songs.pbz2')
        train.start_training(run_name=run_name, dropout=float(rn_dict.get('DP', 0.3)), batch_size=int(rn_dict.get('BS', 64)),
                             epochs=epochs, sequence_length=int(rn_dict.get('SEQ', 10)), hidden_size=int(rn_dict.get('HD', 32)),
                             learning_rate=float(rn_dict.get('LR', 0.0001)), num_layers=int(rn_dict.get('NL', 1)),
                             model_type=rn_dict.get('M', 'LSTM').lower(), latent_space=int(rn_dict.get('LS', 3)),
                             test_size=test_size, augmentations=['transpose-all-up-down', 'octave-up-down'])


    @classmethod
    def project_vae_latent_space_chorales(cls, encoder, run_name='SEQ=10-AUG=TUPDW,OUD-BS=64-HD=32-DP=0.3-LR=0.0001-NL=1-V3', start_song=0, end_song=None):
        """Generate Bach Chorales"""

        from .model_train.generator_vae import MusicGenerator

        music_generator = MusicGenerator(
            encoder, f'_generations/BachChorales_{encoder.name}_res4_transpC-Major',
            f'_datasets_encoded/BachChorales_{encoder.name}_res4_transpC-Major_all_songs.pbz2')

        import glob
        models = glob.glob(
            f'_results/BachChorales_{encoder.name}_res4_transpC-Major/models/run_{run_name}/*.h5')

        last_model = sorted(models)[-1]
        epoch = last_model.split(os.sep)[-1].split('-')[1]

        print('GENERATING LATENT SPACE FROM MODEL: ', last_model)

        import pandas as pd

        if end_song is None:
            import music21
            end_song = len(music21.corpus.chorales.Iterator(returnType='stream'))

        os.makedirs(f'_jsons/BachChorales_{encoder.name}_res4_transpC-Major', exist_ok=True)
        try:
            features = pd.read_csv(f'_jsons/BachChorales_{encoder.name}_res4_transpC-Major/latent_space_{run_name}_epoch_{epoch}.csv', index_col=0)
            start_song = int(list(features['song'])[-1]) + 1
        except Exception as e:
            print('NO FILE FOUND', e)
            features = pd.DataFrame({})

        end_song = 150

        for i in range(start_song, end_song, 1):
            print('GENERATING SONG: ', i)
            ret = music_generator.project_latent_space(path=last_model, songs=[i], dimensions_to_plot='calculate') # or calculate-plot
            if ret is not None:
                if i == 0:
                    features = ret
                else:
                    features = pd.concat([features, ret], ignore_index=True)

                if i % 10 == 0 or i == end_song - 1 or i == end_song:
                    features.to_csv(f'_jsons/BachChorales_{encoder.name}_res4_transpC-Major/latent_space_{run_name}_epoch_{epoch}.csv')


    @classmethod
    def augment_chorales_dataset(cls, encoding='dft128'):
        """Augment Dataset Already Created"""

        import bz2
        import time

        import _pickle as cPickle
        import progressbar

        encoder = EncoderFactory().get_encoder(encoding, data_path='music21_bach',
                                               data_name='BachChorales', transposition='C Major')

        with bz2.BZ2File(f'_datasets_encoded/BachChorales_{encoding}_res4_transpC-Major_all_songs.pbz2', "rb") as filepath:
            dataset = cPickle.load(filepath)

        augm_path = f'_datasets_encoded/BachChorales_{encoding}_res4_transpC-Major_all_songs_augmented.pbz2'
        augmented_songs = []

        try:
            with bz2.BZ2File(augm_path, "rb") as filepath:
                augmented_songs = cPickle.load(filepath)

            print('Augmenting dataset...')
            print('Dataset was already augmented with',
                  len(augmented_songs), 'songs')
        except FileNotFoundError:
            print('Augmenting dataset...')
            print('Dataset was not augmented yet')

        augmentations = ['OU', 'OD'] + [f'UP{i}' for i in range(1, 12)] + [f'DW{i}' for i in range(
            1, 12)] + [f'FU{i}' for i in range(1, 5)] + [f'FD{i}' for i in range(1, 5)]

        to_augment = len(dataset) - len(augmented_songs)
        with progressbar.ProgressBar(max_value=to_augment*len(augmentations)) as bar:
            for i, song in enumerate(dataset[len(augmented_songs):]):
                aug_t = {}

                for j, aug in enumerate(sorted(augmentations)):
                    aug_t[aug] = encoder.augment_song(  # type: ignore
                        song, aug)

                    bar.update(i * len(augmentations) + j)
                    time.sleep(0.01)

                augmented_songs.append(aug_t)

                if i % 50 == 0 or i == len(dataset)-1:
                    with bz2.BZ2File(augm_path, "wb") as filepath:
                        cPickle.dump(augmented_songs, filepath)
