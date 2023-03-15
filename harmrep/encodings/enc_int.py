"""This module implements the encoder interface class"""

import abc
import bz2
import glob
import os
import time

import _pickle as cPickle
import music21
import numpy as np
import progressbar

from .utils import increment_filename, transpose_notes


class EncoderInterface:
    """
    Interface for Encoders

    Attributes
    ----------
    name : str
        Name of the encoder
    bad_files : list
        List of bad files
    dataset : dict
        Dictionary with the dataset path and name
    saving_path : str
        Path to save the encoded dataset
    transposition : str
        Transposition to apply to the dataset
    resolution : int
        Resolution of the encoding

    Methods
    ----------
    start_process(save_folder, one_file=True, divide_parts=True)
        Start the encoding process
    extract_representation(song)
        Extract the representation of the song
    get_name_to_extract()
        Get the name of the song to extract
    save_representation(representation, i, name)
        Save the representation of the song
    save_as_one_file(representation, name)
        Save the representation of the song as one file
    retrieve_single_representation(name, save_folder)
        Retrieve the representation of the song
    retrieve_all_representations(save_folder)
        Retrieve all the representations of the songs

    """

    __metaclass__ = abc.ABCMeta

    name = ""
    bad_files = []
    dataset = {}
    saving_path = ""
    transposition = "C Major"

    resolution = 8

    @classmethod
    def __subclasshook__(cls, subclass):
        """subhook class method"""
        return (
            hasattr(subclass, "extract_representation")
            and hasattr(subclass, "get_name_to_extract")
            and callable(subclass.extract_text)
        )

    def start_process(self, save_folder, one_file=True, divide_parts=True):
        """Overrides EncoderInterface.start_process()"""

        if 'music21' not in self.dataset["path"]:
            songs = glob.glob(os.sep.join([self.dataset["path"], '*']))
        else:
            songs = music21.corpus.chorales.Iterator()

        if not save_folder:
            save_folder = "datasets_encoded"
        self.saving_path = os.sep.join(
            [save_folder, f'{self.get_name_to_extract()}{"_divided" if divide_parts else ""}{"_all_songs" if one_file else ""}'])
        print(self.saving_path)

        for filename in increment_filename(self.saving_path):
            if not os.path.exists(f'{filename}{".pbz2" if one_file else ""}'):
                self.saving_path = filename
                break

        if not one_file:
            os.makedirs(self.saving_path)

        songs_to_save = []
        with progressbar.ProgressBar(max_value=len(songs)) as p_bar:
            for i, song in enumerate(songs):
                exct = self.extract_representation(
                    song, divide_parts=divide_parts, index=i)

                if not one_file:
                    self.save_representation(i, exct)
                else:
                    songs_to_save.append(exct)
                    if i % int(len(songs) / 10) == 0.0:
                        self.save_as_one_file(songs_to_save)

                time.sleep(0.05)
                p_bar.update(i)

        print(f'Saved songs to path: "{self.saving_path}"')

        if len(self.bad_files) > 0:
            print("Couldn't parse the following files: ")
            _ = [print(f"- {path}") for path in self.bad_files]

    def save_representation(self, i, song):
        """Save representation to read in the model"""
        # print(f'Saving to path: "{self.saving_path}"')
        with bz2.BZ2File(f"{self.saving_path}/song_{i}.pbz2", "w") as filepath:
            cPickle.dump(song, filepath)

    def save_as_one_file(self, all_songs):
        """Save representation to read in the model as one file"""
        with bz2.BZ2File(f"{self.saving_path}.pbz2", "w") as filepath:
            cPickle.dump(all_songs, filepath)

    def retrieve_single_representation(self, song=None, save_folder="datasets_encoded"):
        """Retrieve saved song representation to read in the model"""
        self.saving_path = os.sep.join(
            [save_folder, self.get_name_to_extract()])
        if song is not None:
            song_path = f"{self.saving_path}/song_{song}.pbz2"
            if os.path.exists(song_path):
                with bz2.BZ2File(song_path, "rb") as filepath:
                    return cPickle.load(filepath)
            else:
                print(f"No song available with the name {song_path}!")
                return []

    def retrieve_folder_representation(self, save_folder="datasets_encoded", songs_filter=None):
        """Retrieve saved song representations saved in folder to read in the model"""
        songs = songs_filter

        if not songs_filter or len(songs_filter) == 0:
            self.saving_path = os.sep.join(
                [save_folder, self.get_name_to_extract()])
            if os.path.exists(os.sep.join([self.saving_path, ''])):
                songs = glob.glob(f"{self.saving_path}/*.pbz2")
            else:
                print(
                    f"No dataset available with the name {self.saving_path}!")
                return

        if not songs:
            print("No dataset to retrieve!")
            return

        songs.sort() # type: ignore
        for song in songs:
            with bz2.BZ2File(song, "rb") as filepath:
                yield song.split(os.sep)[-1].replace('song_', '').replace('.pbz2', ''), cPickle.load(filepath)

    def retrieve_single_rep_all(self, song=None, save_folder="datasets_encoded"):
        """Retrieve saved song representation (aggregated) to read in the model"""
        self.saving_path = os.sep.join(
            [save_folder, self.get_name_to_extract()])
        if song is not None:
            pass

    def get_name_to_extract(self):
        """Get Name for Extracted Dataset File"""
        transp = self.transposition.replace(" ", "-")
        res = str(self.resolution)
        name = self.dataset["name"]

        return f"{name}_{self.name}_res{res}_transp{transp}"

    def save_list(self, notes_list):
        """Return list with representation"""
        rep = notes_list
        if isinstance(notes_list, list):
            rep = np.array(notes_list, dtype=type(notes_list[0]))
        return rep

    def save_dict(self, notes_dict):
        """Return dict with representation"""
        rep = notes_dict
        for part, notes_list in notes_dict.items():
            if isinstance(notes_list, list):
                rep[part] = np.array(notes_list, dtype=type(notes_list[0]))
        return rep

    def to_one_hot(self, use_dict=None, n_vocab=130, encoded=None):
        """transform a vector(iterable) of midi notes in a one-hot representation"""
        one_hot_rep = []

        dim = n_vocab
        if use_dict:
            dim = len(use_dict)

        if encoded is not None:
            if isinstance(encoded[0], np.integer):
                encoded = [encoded]
        else:
            return []

        for song in encoded:
            one_hot = []

            for note in song:
                temp = np.zeros(dim)

                ind = int(note)
                if use_dict:
                    ind = use_dict[note]

                temp[ind] = 1
                one_hot.append(temp)

            one_hot_rep.append(np.asarray(one_hot))

        return one_hot_rep

    def get_dictionary_of_notes(self, encoded=None, zero_pad=False):
        """Returns a dictionary of all notes that appear in the dataset"""

        if encoded is not None:
            if isinstance(encoded[0], np.integer):
                encoded = [encoded]
        else:
            return []

        set_notes = set()

        for song in encoded:
            set_notes = set_notes.union(set(song))

        if zero_pad:
            temp = zip(set_notes, range(1, len(sorted(set_notes)) + 1))
        else:
            temp = zip(set_notes, range(len(sorted(set_notes))))

        return dict(temp)

    def extract_representation(self, path, transpose=True, divide_parts=False, expand_repeats=True, index=0):
        """Extract Representation"""
        try:
            if isinstance(path, str):
                stream = music21.converter.parse(path)
            else:
                stream = path

            if transpose:
                stream = transpose_notes(stream, self.transposition)
            else:
                self.transposition = None

            if expand_repeats:
                stream = stream.expandRepeats()

            if divide_parts:
                notes = {}
                for part in stream.getElementsByClass('Part'):
                    notes[part.id] = sorted(
                        part.flat.notes, key=lambda note: note.offset)
                return self.save_dict({p: self.extract_representation_method(nts) for (p, nts) in notes.items()})

            notes = sorted(stream.flat.notes, key=lambda note: note.offset)
            return self.save_list(self.extract_representation_method(notes))

        except Exception as exc:
            print(exc)
            self.bad_files.append(path)

    def decode(self, encoded):
        """Decode Representation"""
        if not isinstance(encoded, dict):
            encoded = {'p1': encoded}

        stream = music21.stream.Stream()  # type: ignore
        for _, enc in encoded.items():
            part = self.decode_method(enc)
            part.makeNotation(inPlace=True)
            stream.insert(0.0, part)
        return stream

    def sample_file(self, file, file_id=0, seq_len=12):
        """
        sample a file by seq_len
        """
        if file.shape[0] <= seq_len:
            return None
        return (f'Song:{file_id}', int(file.shape[0] - seq_len))

    @abc.abstractmethod
    def decode_method(self, encoded):
        """Extract Representation"""
        raise NotImplementedError

    @abc.abstractmethod
    def extract_representation_method(self, notes):
        """Extract Representation Method"""
        raise NotImplementedError

    @abc.abstractmethod
    def augment_song(self, encoded, augmentation='FD'):
        """Extract Representation"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_vocab_size_and_embedding(self):
        """Get Vocab Size and Embedding Necessity"""
        raise NotImplementedError
