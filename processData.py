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
    ]

    names = [
        "reportedTests",
        "reportedCases",
        "specimenCases",
        "reportedDeaths",
        "specimenDeaths",
        "hospitalisations",
    ]

    nationList = ["UK", "Scotland", "England", "Northern Ireland", "Wales"]

    for nation in nationList:
        nationSeries = []
        for i, fileName in enumerate(fileNames):
            fileName = dataDir + nation + fileName
            if i == 0 or i == 1 or i == 3:
                data = readData(fileName, type="dict")
            else:
                data = readData(fileName, type="dict", skip=5)
            series = pd.Series(data, name=names[i])
            nationSeries.append(series)

        nationData = pd.concat(nationSeries, axis=1)

        nationData["posTests"] = nationData.apply(
            lambda row: min(row["reportedCases"] / row["reportedTests"] * 100, 100), axis=1
        )

        nationData["mortCases"] = nationData["reportedCases"].rolling(28).sum()

        nationData["mortality"] = nationData.apply(
            lambda row: min(row["specimenDeaths"] / row["mortCases"] * 100, 100), axis=1
        )
        nationData["hospitalisationRate"] = nationData.apply(
            lambda row: min(row["hospitalisations"] / row["mortCases"] * 100, 100), axis=1,
        )

        nationData.to_csv(dataDir + nation + ".csv")
        
        for column in names:
            nationData[column] = pd.Series(n_day_avg(nationData[column]), index=nationData.index)

        nationData["posTests"] = nationData.apply(
            lambda row: min(row["reportedCases"] / row["reportedTests"] * 100, 100), axis=1
        )

        nationData["mortCases"] = nationData["reportedCases"].rolling(28).sum()

        nationData["mortality"] = nationData.apply(
            lambda row: min(row["specimenDeaths"] / row["mortCases"] * 100, 100), axis=1
        )

        nationData.to_csv(dataDir + nation + ".avg.csv")
    

def n_day_avg(xs, n=7):
    """compute n day average of time series, using maximum possible number of days at
    start of series"""
    return [np.mean(xs[max(0, i + 1 - n) : i + 1]) for i in range(xs.shape[0])]

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