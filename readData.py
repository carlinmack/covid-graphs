import csv
import argparse


def readData(fileName):
    with open(fileName, "r") as file:
        reader = csv.reader(file, delimiter=",")
        fileData = [[line[0], int(line[1])] for line in reader]

    return fileData


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
