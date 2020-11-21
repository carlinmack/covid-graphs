import argparse
import os

import requests
from tqdm import tqdm


def getData(dataDir, force=False):
    # check for if there is new data
    if os.path.isfile(dataDir + "Last-Modified.txt"):
        with open(dataDir + "Last-Modified.txt") as file:
            prevLastModified = file.read()
    else:
        prevLastModified = ""

    url = "https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=overview&structure=%7B%7D"

    r = requests.get(url)
    lastModified = r.headers["Last-Modified"]

    if prevLastModified != lastModified or force:
        print("Getting new data...")

        urlPrefix = 'https://api.coronavirus.data.gov.uk/v1/data?filters=areaType={}&structure=%7B"date":"date",'
        urls = [
            '"newPillarOneTestsByPublishDate":"newPillarOneTestsByPublishDate","newPillarTwoTestsByPublishDate":"newPillarTwoTestsByPublishDate","newPillarFourTestsByPublishDate":"newPillarFourTestsByPublishDate"',
            '"newCasesBySpecimenDate":"newCasesBySpecimenDate"',
            '"newCasesByPublishDate":"newCasesByPublishDate"',
            '"newDeaths28DaysByDeathDate":"newDeaths28DaysByDeathDate"',
            '"newDeaths28DaysByPublishDate":"newDeaths28DaysByPublishDate"',
            '"newAdmissions":"newAdmissions"',
        ]
        urlSuffix = "%7D&format=csv"
        names = [
            "testing",
            "cases",
            "cases.reported",
            "deaths",
            "deaths.reported",
            "hospitalisations",
        ]

        nations = ["Scotland", "England", "Northern Ireland", "Wales"]

        t = tqdm(
            total=30, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} {elapsed_s:.0f}s"
        )

        for i, name in enumerate(names):
            suffix = urls[i] + urlSuffix
            for nation in nations:
                prefix = urlPrefix.format("nation;areaName={}").format(nation)
                fileName = nation + "." + name
                updateProgressBar(fileName, t)
                getCSV(prefix + suffix, dataDir, fileName)

            prefix = urlPrefix.format("overview")
            fileName = "UK." + name
            updateProgressBar(fileName, t)
            getCSV(prefix + suffix, dataDir, fileName)

        with open(dataDir + "Last-Modified.txt", "w") as file:
            file.write(lastModified)

        print("Done!")
        return True
    else:
        return False


def getCSV(url, dataDir, name):
    r = requests.get(url)
    text = r.text
    fileName = dataDir + name + ".csv"
    if r.status_code == 200:
        titles, data = text.split("\n", 1)

        data = data.split("\n")
        data = data[:-1]  # remove last blank line
        data = list(reversed(data))

        titles = titles.split(",")
        if "newPillarOneTestsByPublishDate" in titles:
            newData = []
            for line in data:
                arr = line.split(",")
                newData.append(
                    str(arr[0])
                    + ","
                    + str(parseInt(arr[1]) + parseInt(arr[2]) + parseInt(arr[3]))
                )
            data = newData

        data = "\n".join(data)

        with open(fileName, "w") as file:
            file.writelines(data)
    elif r.status_code == 204:
        print("Error: No data returned")
        exit()
    else:
        print("Error " + r.status_code)
        print(r.headers)
        exit()


def parseInt(str):
    str = str.strip()
    return int(str) if str else 0


def updateProgressBar(figname, t):
    t.update()
    t.set_description(figname)


def defineArgParser():
    """Creates parser for command line arguments"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "-f", "--force", help="Get data even if it is not new", action="store_true"
    )

    parser.add_argument(
        "-D",
        "--dataDir",
        help="Directory where the csv files will be stored [default: data/]",
        default="data/",
        type=str,
    )

    return parser


if __name__ == "__main__":
    argParser = defineArgParser()
    clArgs = argParser.parse_args()

    dataDir = clArgs.dataDir

    if not os.path.exists(dataDir):
        os.mkdir(dataDir)

    newData = getData(dataDir, clArgs.force)

    if not newData:
        print("No new data.")
