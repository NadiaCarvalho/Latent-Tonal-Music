"""
Class for generating songs from any Network (Tensorflow) to any encoder
"""
import bz2
import os
import random
import sys
import time

import _pickle as cPickle
import matplotlib.pyplot as plt
import music21
import numpy as np
import progressbar
import tensorflow as tf

from ..utils import run_name_to_dict
from .circular_statistics import circ_cor
from .models.vae import VAE

np.random.seed(42)  # keras seed fixing
tf.random.set_seed(42)  # tensorflow seed fixing

np.set_printoptions(threshold=sys.maxsize)


def color_variant(hex_color, brightness_offset=1):
    """ takes a color like #87c95f and produces a lighter or darker variant """
    if len(hex_color) != 7:
        raise Exception(
            "Passed %s into color_variant(), needs to be in #87c95f format." % hex_color)

    rgb_hex = [hex_color[x:x+2] for x in [1, 3, 5]]
    new_rgb_int = [int(hex_value, 16) +
                   brightness_offset for hex_value in rgb_hex]
    new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]
    # make sure new values are between 0 and 255

    new_hex_color = "#" + \
        "".join([code if len(code) == 2 else '0' +
                code for code in [hex(i)[2:] for i in new_rgb_int]])

    return new_hex_color


def cart_to_pool(array):
    """Convert cartesian to polar coordinates"""
    if isinstance(array, tuple):
        return np.arctan2(array[1], array[0])
    return np.arctan2(np.asarray(array[:, 1]), np.asarray(array[:, 0]))


class MusicGenerator:
    """"""

    model = None

    def __init__(self, encoder, data_dir=None, dataset_dir=None) -> None:
        self.encoder = encoder
        self.dataset_dir = dataset_dir
        self.dataset = None
        self.filename = encoder.get_name_to_extract()

    def load_model(self, model_path, latent_dim=256):
        """Load a Model with tensorflow backend"""
        run_name = model_path.split('/')[-2][4:]
        rn_dict = run_name_to_dict(run_name)
        n_vocab, needs_embedding = self.encoder.get_vocab_size_and_embedding()  # type: ignore

        self.model = VAE(latent_dim, n_vocab=n_vocab,
                         lstm_no_enc=1, lstm_no_dec=1,
                         lstm_size=int(rn_dict.get('HD', 32)),
                         dropout=float(rn_dict.get('DP', 0.3)),
                         learning_rate=float(rn_dict.get('LR', 0.001)),
                         seq_len=int(rn_dict.get('SEQ', 32)),
                         batch_size=int(rn_dict.get('BS', 64)),
                         needs_embedding=needs_embedding, verbose=False)
        self.model._model.load_weights(model_path)  # type: ignore

        self.latent_dim = latent_dim
        self.current_epoch = int(model_path.split(os.sep)[-1].split('-')[1])
        self.model._model.layers[0].trainable=False # type: ignore

    def get_x_dataset_inputs(self, seq_len, path=None, number_inputs=10) -> list:  # type: ignore
        """Generate x random inputs"""
        if path is not None:
            # print('Loading Dataset')
            with bz2.BZ2File(path, "rb") as filepath:
                self.dataset = cPickle.load(filepath)

            # print('Sampling Songs')
            rand_songs = random.sample(self.dataset, number_inputs)

            to_return = []
            with progressbar.ProgressBar(max_value=len(rand_songs)) as bar:
                for i, rand_song in enumerate(rand_songs):

                    number_samples = rand_song.shape[0] // seq_len

                    for s in range(number_samples-1):

                        song = rand_song[s*seq_len:(s+1)*seq_len]

                        stream = self.encoder.decode(song)
                        analysis = {}

                        try:
                            p = music21.analysis.discrete.KrumhanslSchmuckler(
                                stream)
                            sol = p.getSolution(stream)
                            analysis["mode"] = sol.mode
                        except:
                            analysis["mode"] = "Not Conclusive"

                        if self.encoder.name == 'polymidi':
                            song_x = song.reshape(1, seq_len, 1)
                        else:
                            song_x = song.reshape(
                                1, seq_len, rand_song.shape[1])

                        to_return.append((tf.convert_to_tensor(
                            song_x, dtype=tf.float32), analysis))

                    bar.update(i)
                    time.sleep(0.01)

            return to_return

    def get_specific_songs_in_all_12_keys(self, songs, path=None, seq_len=10):

        if path is not None:
            # print('Loading Dataset')
            if self.dataset is None:
                with bz2.BZ2File(path, "rb") as filepath:
                    self.dataset = cPickle.load(filepath)

            augmentations = [f'UP{i}' for i in range(1, 12)]

            samples_to_return = []

            for i, song in enumerate(songs):

                sample = self.dataset[song]
                sample_set = []

                try:
                    stream = self.encoder.decode(sample)
                    p = music21.analysis.discrete.KrumhanslSchmuckler(stream)
                except Exception:
                    print('Error on Decoding song: ', i, ' Getting original choral')
                    stream = list(music21.corpus.chorales.Iterator())[i]
                    p = music21.analysis.discrete.KrumhanslSchmuckler(stream)

                try:
                    sol = p.getSolution(stream)
                    sol_key = f'{sol.tonic} {sol.mode}'
                except:
                    sol = 'NOT CONCLUSIVE'
                    sol_key = sol
                sample_set.append((sample, {'key': sol_key}))

                # print('Calculating Augmentations for Song: ', i, ' - ', sol)
                for aug in augmentations:
                    aug_sample = self.encoder.augment_song(sample, aug)
                    if not isinstance(sol, str):
                        new_key = sol.transpose(int(aug[2:]))
                        sample_set.append(
                            (aug_sample, {'key': f'{new_key.tonic} {new_key.mode}'}))
                    else:
                        sample_set.append(
                            (aug_sample, {'key': f'NOT CONCLUSIVE + {aug}'}))

                # print('Extracting Samples')
                with progressbar.ProgressBar(max_value=len(sample_set)) as bar:
                    for j, samp in enumerate(sample_set):
                        if self.encoder.name == 'abc':
                            samp = ('\n'.join(samp[0].split('\n')[7:]), samp[1])
                            number_samples = len(samp[0]) // seq_len
                        else:
                            number_samples = samp[0].shape[0] // seq_len

                        for s in range(number_samples-1):
                            song = samp[0][s*seq_len:(s+1)*seq_len]
                            if self.encoder.name == 'abc':
                                dictionary = self.encoder.get_dictionary_of_notes()
                                song = np.asarray(tf.one_hot([dictionary.index(i) for i in song], len(dictionary), dtype=tf.int32))
                                song_x = song.reshape(1, seq_len, song.shape[1])
                            else:
                                song_x = song.reshape( # type: ignore
                                    1, seq_len, samp[0].shape[1]) # type: ignore

                            samples_to_return.append((tf.convert_to_tensor(
                                song_x, dtype=tf.float32), samp[1]))

                        bar.update(j)
                        time.sleep(0.01)

            return samples_to_return
        return []

    def project_latent_space(self, path, songs=[1], dimensions_to_plot='all', dimensionality_reduction='pca'):
        """Project the latent space"""

        if self.model is None:
            self.load_model(path, latent_dim=int(
                path.split('LS=')[1].split('-')[0]))
        self.model._model.layers[0].trainable = False  # type: ignore

        # print('GENERATING INPUT')
        if self.model is None:
            raise ValueError('Model not loaded')

        first_seq_len = self.model._model.layers[0].input_shape[0][1]

        if songs == 'random':
            _input = self.get_x_dataset_inputs(
                seq_len=first_seq_len, path=self.dataset_dir, number_inputs=20)

        _input = self.get_specific_songs_in_all_12_keys(
            songs=songs, seq_len=first_seq_len, path=self.dataset_dir)

        info = 'key'

        # from collections import Counter
        # #print(Counter([samp[1][info] for samp in _input]))  # type: ignore

        # print('PREDICTING LATENT SPACE')
        set_info = []
        predictions = []
        with progressbar.ProgressBar(max_value=len(_input)) as bar:
            for i, net_input in enumerate(_input):
                pred = self.model.check_model_at_layer(  # type: ignore
                    input=net_input[0], layer=4)
                if net_input[1][info] not in set_info:
                    set_info.append(net_input[1][info].capitalize())

                predictions.append((pred, net_input[1][info].capitalize()))
                bar.update(i)
                time.sleep(0.01)

        # print('PLOTTING LATENT SPACE')

        if dimensions_to_plot != 'calculate':
            self.plotting_methods(songs, dimensions_to_plot,
                                  set_info, predictions, dimensionality_reduction)

        if 'calculate' in dimensions_to_plot:
            # print('Calculate Clusttering')
            return self.get_cluster_measures(set_info, predictions, song=songs[0])

    def plotting_methods(self, songs, dimensions_to_plot, set_info, predictions, dimensionality_reduction='pca'):
        """Plot the latent space"""
        if isinstance(dimensions_to_plot, str):
            # print('2D MAP PLOT')
            if dimensionality_reduction == 'mds':
                red_predictions = self.get_mds_predictions(predictions)
            else:
                red_predictions = self.get_pca_predictions(predictions)

            os.makedirs(
                f'_figures/{self.encoder.name}-ls{self.latent_dim}-e{self.current_epoch}/', exist_ok=True)
            self.plot_2d_latent_space(
                set_info, red_predictions, dimensions=[0, 1], name=f'_figures/{self.encoder.name}-ls{self.latent_dim}-e{self.current_epoch}/latent_space_{dimensionality_reduction}_song_{", ".join([str(s) for s in songs])}.png')
        elif len(dimensions_to_plot) == 2:
            # print('2D PLOT')
            self.plot_2d_latent_space(
                set_info, predictions, dimensions=dimensions_to_plot, name=None)  # type: ignore
        elif len(dimensions_to_plot) == 3:
            # print('3D PLOT')
            self.plot_3d_latent_space(
                set_info, predictions, dimensions=dimensions_to_plot)
        else:
            raise ValueError('Only 2D and 3D plots are supported')

    def get_cluster_measures(self, set_info, predictions, use_dimensionality_reduction=True, song=0):
        """Get the cluster measures"""
        labels = list(set(set_info))
        if len(labels) == 0 or labels is None:
            raise ValueError('No labels found')

        colors = self.get_camelot_wheel_colors()

        if use_dimensionality_reduction:
            predictions_to_use = self.get_pca_predictions(predictions)
        else:
            predictions_to_use = predictions

        label_predictions = {}

        for label in sorted(labels, key=lambda x: int(colors[x.lower()][0][:-1])):
            if colors[label.lower()][0] not in label_predictions:
                label_predictions[colors[label.lower()][0]] = []
            label_predictions[colors[label.lower()][0]].extend([p for p, pred in enumerate(
                predictions_to_use) if pred[1] == label])

        clusters = {label: np.squeeze(np.asarray(
            [predictions_to_use[pred][0] for pred in label_predictions[label]])) for label in label_predictions}

        if use_dimensionality_reduction:
            circular_tau1, circular_tau2 = self.centroid_circular_correlation(
                set_info, predictions, clusters, song)
        else:
            circular_tau1, circular_tau2 = None, None

        X_label = [label for label, cluster in clusters.items()
                   for _ in cluster]
        X = [cl for cluster in clusters.values() for cl in cluster]

        from sklearn import metrics

        euclidean_distances = metrics.pairwise.euclidean_distances(X)

        from .utils import CLUSTER_DISTANCE_METHODS, DIAMETER_METHODS, dunn
        import pandas as pd

        # print('Calculating Cluster Measures')
        to_return = {
            'song': int(song),
            # Scores around zero indicate overlapping clusters
            'Silhouette Score': metrics.silhouette_score(X, X_label, metric='euclidean'),
            'Davies Bouldin Score': metrics.davies_bouldin_score(X, X_label),
            'Calinski Harabasz Score': metrics.calinski_harabasz_score(X, X_label),
        }
        for diameter_method in DIAMETER_METHODS:
            for cdist_method in CLUSTER_DISTANCE_METHODS:
                to_return[f'Dunn Score ({diameter_method}, {cdist_method})'] = dunn(
                    X_label, euclidean_distances, diameter_method, cdist_method)

        if circular_tau1 is not None and circular_tau2 is not None:
            to_return['Circular Tau 1'] = circular_tau1['val']
            to_return['Circular Tau 2'] = circular_tau2['val']

        return pd.DataFrame({}).from_dict(to_return, orient='index').T

    def centroid_circular_correlation(self, set_info, predictions, clusters, song=0):
        """
        Calculate the correlation between the centroid of the cluster and the default position of the key
        """
        cluster_centroids = {label: (np.mean(cluster[:, 0]), np.mean(
            cluster[:, 1])) for label, cluster in clusters.items()}
        cluster_centroids_pool = {label: cart_to_pool(
            cluster_c) for label, cluster_c in cluster_centroids.items()}

        angles = np.deg2rad([i*30 for i in range(7)] +
                            [(5-i)*-30 for i in range(5)])
        default_coordinates = {
            label: angles[int(''.join(label[:-1]))-1] for label in clusters.keys()}

        # for label, cluster_c in cluster_centroids.items():
        #     #print(label, cluster_c,
        #           cluster_centroids_pool[label], default_coordinates[label])

        to_correlate = [[pool, default_coordinates[label]]
                        for label, pool in cluster_centroids_pool.items()]

        # #print(self.plot_2d_latent_space(set_info, self.get_mds_predictions(
        #     predictions), name=f'latent_space_mds_song_{song}.png'))
        # #print(self.plot_2d_latent_space(set_info, self.get_pca_predictions(
        #     predictions), name=f'latent_space_pca_song_{song}.png'))

        # #print()
        return circ_cor(np.asarray(to_correlate), type='tau1'), circ_cor(np.asarray(to_correlate), type='tau2')

    def get_mds_predictions(self, predictions):
        """Get the MDS predictions"""
        from sklearn.manifold import MDS
        from sklearn.preprocessing import StandardScaler

        mds = MDS(n_components=2, random_state=0, normalized_stress="auto")
        mds_predictions = mds.fit_transform(
            StandardScaler().fit_transform([pred[0][0] for pred in predictions]))

        if mds_predictions is None:
            raise ValueError('MDS predictions is None')

        return [[m_p, predictions[i][1]] for i, m_p in enumerate(mds_predictions)]

    def get_pca_predictions(self, predictions):
        """Get the PCA predictions"""
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler

        pca = PCA(n_components=2)
        pca_predictions = pca.fit_transform(
            StandardScaler().fit_transform([pred[0][0] for pred in predictions]))

        return [[m_p, predictions[i][1]] for i, m_p in enumerate(pca_predictions)]

    def get_camelot_wheel_colors(self):
        return {
            **dict.fromkeys(['a- minor', 'g# minor'], ('1A', '#56f1da', color_variant('#56f1da', -10))),
            **dict.fromkeys(['e- minor', 'd# minor'], ('2A', '#7df2aa', color_variant('#7df2aa', -10))),
            **dict.fromkeys(['b- minor', 'a# minor'], ('3A', '#aef589', color_variant('#aef589', -10))),
            **dict.fromkeys(['f minor'], ('4A', '#e8daa1', color_variant('#e8daa1', -10))),
            **dict.fromkeys(['c minor'], ('5A', '#fdbfa7', color_variant('#fdbfa7', -10))),
            **dict.fromkeys(['g minor'], ('6A', '#fdafb7', color_variant('#fdafb7', -10))),
            **dict.fromkeys(['d minor'], ('7A', '#fdaacc', color_variant('#fdaacc', -10))),
            **dict.fromkeys(['a minor'], ('8A', '#f2abe4', color_variant('#f2abe4', -10))),
            **dict.fromkeys(['e minor'], ('9A', '#ddb4fd', color_variant('#ddb4fd', -10))),
            **dict.fromkeys(['b minor'], ('10A', '#becdfd', color_variant('#becdfd', -10))),
            **dict.fromkeys(['f# minor', 'g- minor'], ('11A', '#8ee4f9', color_variant('#8ee4f9', -10))),
            **dict.fromkeys(['d- minor', 'c# minor'], ('12A', '#55f0f0', color_variant('#55f0f0', -10))),

            **dict.fromkeys(['b major'], ('1B', '#01edca', color_variant('#01edca', -10))),
            **dict.fromkeys(['f# major', 'g- major'], ('2B', '#3cee81', color_variant('#3cee81', -10))),
            **dict.fromkeys(['d- major', 'c# major'], ('3B', '#86f24f', color_variant('#86f24f', -10))),
            **dict.fromkeys(['a- major', 'g# major'], ('4B', '#dfca73', color_variant('#dfca73', -10))),
            **dict.fromkeys(['e- major', 'd# major'], ('5B', '#ffa07c', color_variant('#ffa07c', -10))),
            **dict.fromkeys(['b- major', 'a# major'], ('6B', '#fdafb7', color_variant('#fdafb7', -10))),
            **dict.fromkeys(['f major'], ('7B', '#ff81b4', color_variant('#ff81b4', -10))),
            **dict.fromkeys(['c major'], ('8B', '#ee82d9', color_variant('#ee82d9', -10))),
            **dict.fromkeys(['g major'], ('9B', '#ce8fff', color_variant('#ce8fff', -10))),
            **dict.fromkeys(['d major'], ('10B', '#9fb6ff', color_variant('#9fb6ff', -10))),
            **dict.fromkeys(['a major'], ('11B', '#56d9f9', color_variant('#56d9f9', -10))),
            **dict.fromkeys(['e major'], ('12B', '#00ebeb', color_variant('#00ebeb', -10)))
        }

    def plot_2d_latent_space(self, set_info, predictions, dimensions=[0, 1], name=None):
        """2D plot of the latent space"""

        fig = plt.figure()
        ax = fig.add_subplot(111)

        labels = list(set(set_info))
        colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'w'][:len(labels)]
        if all(['minor' in l or 'major' in l for l in labels]):
            # Camelot Wheel Colors
            colors = self.get_camelot_wheel_colors()

        for i, label in enumerate(sorted(labels, key=lambda x: int(colors[x.lower()][0][:-1]))):
            label_predictions = [p for p, pred in enumerate(
                predictions) if pred[1] == label]

            if len(predictions[0][0]) == 2:
                predict_x = [predictions[pred][0][dimensions[0]]
                             for pred in label_predictions]
                predict_y = [predictions[pred][0][dimensions[1]]
                             for pred in label_predictions]
            else:
                predict_x = [predictions[pred][0][0, dimensions[0]]
                             for pred in label_predictions]
                predict_y = [predictions[pred][0][0, dimensions[1]]
                             for pred in label_predictions]

            centroid = np.mean(np.array([predict_x, predict_y]), axis=1)

            if isinstance(colors, list):
                ax.scatter(predict_x, predict_y,
                           c=colors[i], label=label, zorder=-1)
                ax.scatter(centroid[0], centroid[1], c=colors[i],
                           marker='*', edgecolors='black', s=100, zorder=1)  # type: ignore
            else:
                ax.scatter(predict_x, predict_y, c=colors[label.lower(
                )][1], label=colors[label.lower()][0], zorder=-1)
                ax.scatter(centroid[0], centroid[1], c=colors[label.lower(
                )][2], marker='*', edgecolors='black', s=100, zorder=1)  # type: ignore

        ax.legend()
        if name is not None:
            plt.savefig(name, dpi=300)
            plt.close()
        else:
            plt.show()

    def plot_3d_latent_space(self, set_info, predictions, dimensions=[0, 1, 2]):
        """3D plot of the latent space"""

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        labels = list(set(set_info))

        colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'w'][:len(labels)]
        if all(['minor' in l or 'major' in l for l in labels]):
            # Camelot Wheel Colors
            colors = self.get_camelot_wheel_colors()

        for i, label in enumerate(sorted(labels, key=lambda x: int(colors[x.lower()][0][:-1]))):
            label_predictions = [p for p, pred in enumerate(
                predictions) if pred[1] == label]

            predict_x = [predictions[pred][0][0, dimensions[0]]
                         for pred in label_predictions]
            predict_y = [predictions[pred][0][0, dimensions[1]]
                         for pred in label_predictions]
            predict_z = [predictions[pred][0][0, dimensions[2]]
                         for pred in label_predictions]

            if isinstance(colors, list):
                _ = ax.scatter(predict_x, predict_y, predict_z,
                               color=colors[i], label=label)
            else:
                _ = ax.scatter(predict_x, predict_y, predict_z,
                               color=colors[label.lower()][1], label=colors[label.lower()][0])

            plt.legend(loc=2, bbox_to_anchor=(1.05, 1))

        plt.show()
