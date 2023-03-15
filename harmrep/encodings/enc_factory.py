"""This module implements a serializer for the encodings"""

import importlib

class EncoderFactory():
    """
    Class for Factory Encoder

    Attributes
    ----------
    ENCODINGS : dict
        Dictionary with the available encodings

    Methods
    -------
    get_encoder(encoding, **kwargs)
        Factory for Getting Specified Encoder from string
    class_encoding(encoding)
        Return Class Encoding
    """

    ENCODINGS = {
        'abc': 'ABCEncoder',
        'dft12': 'DFT12Encoder',
        'dft128': 'DFT128Encoder',
        'polymidi': 'PolyMidiEncoder',
        'pianoroll': 'PianoRollEncoder',
        'tonnetz': 'TonnetzEncoder',
    }

    @classmethod
    def get_encoder(cls, encoding, **kwargs) -> None:
        """Factory for Getting Specified Encoder from string"""
        if encoding in cls.ENCODINGS:
            module = importlib.import_module(f'.enc_{encoding.lower()}', 'harmrep.encodings')
            class_ = getattr(module, cls.ENCODINGS[encoding])
            return class_(kwargs['data_path'], kwargs['data_name'], transposition=kwargs['transposition'])

        print(f'Encoder {encoding} not implemented!')
        return None

    @classmethod
    def class_encoding(cls, encoding):
        """Return Class Encoding"""
        if encoding in cls.ENCODINGS:
            return cls.ENCODINGS[encoding]
        return None
