import argparse
import os
import sys

from   pathlib import Path

# Path to the directory containg the script file
root_path = (Path(__file__) / "..").resolve()

# Add current script directory to windows path (on windows :p) to find third party DLLs
if sys.platform == "win32":
    os.environ["PATH"] = str(root_path) + os.pathsep + os.environ["PATH"]

from pathlib import Path
from instr.tds2024b import TDS2024B_Interface

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
