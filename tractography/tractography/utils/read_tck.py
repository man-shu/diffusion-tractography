import numpy as np
import struct
import os


def read_tck_file(tck_file):
    """Read streamlines from MRTrix3 TCK file format.

    TCK format consists of a text header followed by binary track data.
    Tracks are separated by NaN triplets and file ends with Inf triplet.

    Parameters
    ----------
    tck_file : str
        Path to .tck file

    Returns
    -------
    streamlines_list : list of ndarray
        List of streamlines, each as an Nx3 array of coordinates
    """

    streamlines_list = []

    with open(tck_file, "rb") as f:
        # Read header
        header_lines = []
        offset = None
        datatype = "Float32LE"  # Default

        while True:
            line = f.readline().decode("utf-8").strip()
            header_lines.append(line)

            if line.startswith("file:"):
                # Extract file offset
                parts = line.split()
                offset = int(parts[-1])

            if line.startswith("datatype:"):
                datatype = line.split()[-1]

            if line == "END":
                break

        if offset is None:
            raise ValueError("No 'file:' offset found in TCK header")

        # Determine float format
        if "Float32" in datatype:
            fmt = "f"  # 32-bit float
            float_size = 4
        elif "Float64" in datatype:
            fmt = "d"  # 64-bit float
            float_size = 8
        else:
            raise ValueError(f"Unsupported datatype: {datatype}")

        # Determine byte order
        if "BE" in datatype:
            byte_order = ">"  # Big endian
        else:
            byte_order = "<"  # Little endian (default)

        # Move to binary data
        f.seek(offset)

        # Read binary track data
        current_streamline = []

        while True:
            # Read triplet of floats
            data = f.read(3 * float_size)
            if len(data) < 3 * float_size:
                break  # End of file

            # Unpack triplet
            fmt_str = byte_order + "3" + fmt
            triplet = struct.unpack(fmt_str, data)

            # Check for end of file marker (all Inf)
            if all(np.isinf(v) for v in triplet):
                if current_streamline:
                    streamlines_list.append(np.array(current_streamline))
                    current_streamline = []
                break

            # Check for track separator (all NaN)
            if all(np.isnan(v) for v in triplet):
                if current_streamline:
                    streamlines_list.append(np.array(current_streamline))
                    current_streamline = []
            else:
                current_streamline.append(triplet)

    return streamlines_list
