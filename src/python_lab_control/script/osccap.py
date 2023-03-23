"""
┌────────────────────────────────────────────────────────────────────┐
│ Quick and dirty script to take captures from TDS2024B oscilloscope │
└────────────────────────────────────────────────────────────────────┘

 Florian Dupeyron
 January 2022
"""

import argparse
import os
import sys

from   pathlib import Path

# Path to the directory containg the script file
root_path = (Path(__file__) / "..").resolve()

if sys.platform == "win32":
    import libusb

    # Uncomment this line if you get a "No backend availble" error
    # This line adds the found DLL_PATH to the PATH env. variable, so that
    # the libusb dll can be found by the current executable.
    #os.environ["PATH"] = str((Path(libusb._platform.DLL_PATH) / "..").resolve()) + os.pathsep + os.environ["PATH"]

from pathlib import Path
from ..instr.tds2024b import TDS2024B_Interface

def dir_file(path):
    p = Path(path)
    if p.is_dir():
        raise argparse.ArgumentTypeError(f"{str(path)} is a folder")
    return p

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture from TDS2024B")
    parser.add_argument("output_file", help="output file path")

    args = parser.parse_args()

    osc = TDS2024B_Interface()
    img = osc.capture()

    img.save(str(args.output_file))
