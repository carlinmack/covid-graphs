import argparse
import os

import requests
from tqdm import tqdm

from datetime import timedelta, date


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
            '"newPeopleReceivingFirstDose":"newPeopleReceivingFirstDose","newPeopleReceivingSecondDose":"newPeopleReceivingSecondDose"',
        ]
        urlSuffix = "%7D&format=csv"
        names = [
            "testing.reported",
            "cases",
            "cases.reported",
            "deaths",
            "deaths.reported",
            "hospitalisations",
            "vaccinations",
        ]

        nations = ["Scotland", "England", "Northern Ireland", "Wales"]

        t = tqdm(
            total=35, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} {elapsed_s:.0f}s"
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

        if "newPeopleReceivingFirstDose" in titles:
            data = insertZeros(data, intervalType="weeks")
        else:
            data = insertZeros(data)

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


def insertZeros(data, intervalType="days"):
    """Converts ["2020-07-02,1508", "2020-07-06,1067"]
       to ["2020-07-02,1508", "2020-07-03,0", "2020-07-04,0", "2020-07-05,0", 
           "2020-07-06,1067"]"""

    start_date = date(2020, 1, 3)
    end_date = date.today() + timedelta(days=1)

    i = 0
    for curDate in daterange(start_date, end_date):
        if intervalType != "days":
            if curDate.weekday() != 6:
                continue
        # print('sunday', curDate, curDate.weekday())
        curDate = curDate.strftime("%Y-%m-%d")
        if i < len(data):
            dataDate = data[i].split(",")[0]
            if dataDate == curDate:
                i += 1
            else:
                data.insert(i, curDate + ",0")
                i += 1
        else:
            data.insert(i, curDate + ",0")
            i += 1

    return data


def parseInt(str):
    str = str.strip()
    return int(str) if str else 0


def updateProgressBar(figname, t):
    t.update()
    t.set_description(figname)


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


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
