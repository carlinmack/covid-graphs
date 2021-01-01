import csv
import argparse
from datetime import datetime as dt


def readData(fileName, type="arr", skip=0):
    if type == "arr":
        with open(fileName, "r") as file:
            reader = csv.reader(file, delimiter=",")
            fileData = [[line[0], int(line[1])] for line in reader]
        if skip:
            return fileData[:-skip]
        return fileData
    elif type == "dict":
        with open(fileName, "r") as file:
            reader = csv.reader(file, delimiter=",")
            fileData = [[dt.fromisoformat(line[0]), int(line[1])] for line in reader]
        if skip:
            return dict(fileData[:-skip])
        return dict(fileData)
    
    return None


def defineArgParser():
    """Creates parser for command line arguments"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "fileName", help="Name of the file that should be read", type=str,
    )

    return parser


if __name__ == "__main__":
    argParser = defineArgParser()
    clArgs = argParser.parse_args()

    print(readData(clArgs.fileName))
