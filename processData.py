import argparse
from readData import readData
import pandas as pd
import numpy as np


def processData(dataDir="data/"):
    fileNames = [
        ".testing.reported.csv",
        ".cases.reported.csv",
        ".cases.csv",
        ".deaths.reported.csv",
        ".deaths.csv",
        ".hospitalisations.csv",
        ".inHospital.csv"
    ]

    names = [
        "reportedTests",
        "reportedCases",
        "specimenCases",
        "reportedDeaths",
        "specimenDeaths",
        "hospitalisations",
        "inHospital",
    ]

    nationList = ["UK", "Scotland", "England", "Northern Ireland", "Wales"]

    for nation in nationList:
        nationSeries = []
        for i, fileName in enumerate(fileNames):
            fileName = dataDir + nation + fileName
            if i in [2, 4]:
                data = readData(fileName, type="dict", skip=5)
            else:
                data = readData(fileName, type="dict")
            series = pd.Series(data, name=names[i])
            nationSeries.append(series)

        nationData = pd.concat(nationSeries, axis=1)

        calculateFeatures(nationData)

        nationData.to_csv(dataDir + nation + ".csv")

        for column in names:
            nationData[column].loc[
                nationData[column].first_valid_index() : nationData[column].last_valid_index()
            ].fillna(0, inplace=True)
            nationData[column] = nationData[column].rolling(7).mean()

        calculateFeatures(nationData)

        nationData.to_csv(dataDir + nation + ".avg.csv")


def calculateFeatures(nationData):
    nationData["posTests"] = nationData.apply(
        lambda row: min(row["reportedCases"] / row["reportedTests"] * 100, 100), axis=1,
    )

    nationData["mortCases"] = nationData["reportedCases"].rolling(28).sum()

    nationData["mortality"] = nationData.apply(
        lambda row: min(row["specimenDeaths"] / row["mortCases"] * 100, 100), axis=1
    )
    nationData["hospitalisationRate"] = nationData.apply(
        lambda row: min(row["hospitalisations"] / row["mortCases"] * 100, 100), axis=1,
    )


def defineArgParser():
    """Creates parser for command line arguments"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
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

    processData(clArgs.dataDir)
