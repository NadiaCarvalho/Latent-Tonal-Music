"""Utils for outputing results"""

#import os

import numpy as np

def export_to_file(info, path):
    """Export to File"""
    with open(path, 'w', encoding='utf-8') as file:
        if isinstance(info, np.ndarray):
            if isinstance(info[0], int):
                np.savetxt(file, info, fmt='%d')
            if isinstance(info[0], float):
                np.savetxt(file, info, fmt='%.4e')
            elif isinstance(info[0][0], np.int16):  # type: ignore
                np.savetxt(file, info, fmt='%d')
            else:
                np.savetxt(file, info, fmt='%.4e')
        else:
            file.write(str(info))
        file.close()
