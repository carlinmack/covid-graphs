import csv
import os
import requests
from datetime import datetime as dt
from datetime import timedelta

import matplotlib.pyplot as plt
import matplotlib.ticker as tkr
import numpy as np
import pandas as pd


def getData(dataDir):
    nations = ["Scotland", "England", "Northern Ireland", "Wales"]
    testingURL = """https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=nation;areaName={nation}&structure=%7B"date":"date","newPillarOneTestsByPublishDate":"newPillarOneTestsByPublishDate","newPillarTwoTestsByPublishDate":"newPillarTwoTestsByPublishDate","newPillarFourTestsByPublishDate":"newPillarFourTestsByPublishDate"%7D&format=csv"""

    casesURL = """https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=nation;areaName={nation}&structure=%7B"date":"date","newCasesBySpecimenDate":"newCasesBySpecimenDate"%7D&format=csv"""

    reportedURL = """https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=nation;areaName={nation}&structure=%7B""date":"date","newCasesByPublishDate":"newCasesByPublishDate"%7D&format=csv"""

    dataURLs = [testingURL, casesURL, reportedURL]
    names = ["testing", "cases", "cases.reported"]

    today = dt.today()
    yesterday = today - timedelta(days=1)

    for i, url in enumerate(dataURLs):
        for nation in nations:
            r = requests.get(url.format(nation=nation))
            text = r.text
            filePrefix = dataDir + nation + "." + names[i] + "."

            yesterdaysFileName = filePrefix + yesterday.strftime("%Y-%m-%d") + ".csv"
            if os.path.exists(yesterdaysFileName):
                os.remove(yesterdaysFileName)

            fileName = filePrefix + today.strftime("%Y-%m-%d") + ".csv"
            with open(fileName, "w") as file:
                file.writelines(text)

    ukTestingURL = """https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=overview&structure=%7B"date":"date","newPillarOneTestsByPublishDate":"newPillarOneTestsByPublishDate","newPillarTwoTestsByPublishDate":"newPillarTwoTestsByPublishDate","newPillarFourTestsByPublishDate":"newPillarFourTestsByPublishDate"%7D&format=csv"""
    ukCasesURL = """https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=overview&structure=%7B"date":"date","newCasesBySpecimenDate":"newCasesBySpecimenDate"%7D&format=csv"""

    ukReportedURL = """https://api.coronavirus.data.gov.uk/v1/data?filters=areaName=United%2520Kingdom;areaType=overview&structure=%7B"date":"date","newCasesByPublishDate":"newCasesByPublishDate"%7D&format=csv"""

    URLs = [ukTestingURL, ukCasesURL, ukReportedURL]

    for j, url in enumerate(URLs):
        r = requests.get(url)
        text = r.text
        filePrefix = dataDir + "UK." + names[j] + "."

        yesterdaysFileName = filePrefix + yesterday.strftime("%Y-%m-%d") + ".csv"
        if os.path.exists(yesterdaysFileName):
            os.remove(yesterdaysFileName)

        fileName = filePrefix + today.strftime("%Y-%m-%d") + ".csv"
        with open(fileName, "w") as file:
            file.writelines(text)


def ukPlot(dataDir="data/", plotsDir="plots/", avg=True):
    """avg indicates seven day average of new cases should be used"""
    today = dt.today()

    filePrefix = dataDir + "UK"
    casesFileName = filePrefix + ".cases." + today.strftime("%Y-%m-%d") + ".csv"
    testsFileName = filePrefix + ".testing." + today.strftime("%Y-%m-%d") + ".csv"

    with open(casesFileName, "r") as file:
        next(file)
        reader = csv.reader(file, delimiter=",")
        casesData = [[line[0], int(line[1])] for line in reader]
        casesDict = dict(casesData)
        # convert to np array and separate dates from case counts
        casesData = np.array(casesData)
        casesDates = casesData[:, 0]
        cases = casesData[:, 1].astype(np.float)
        casesDates = [dt.strptime(x, "%Y-%m-%d") for x in casesDates]
        # compute seven day average of cases if enabled
        if avg:
            cases = n_day_avg(cases, 7)

    with open(testsFileName, "r") as file:
        next(file)
        reader = csv.reader(file, delimiter=",")
        testsData = [
            (line[0], parseInt(line[1]) + parseInt(line[2]) + parseInt(line[3]))
            for line in reader
        ]
        testsData = np.array(testsData)
        testRawDates = testsData[:, 0]
        testDates = [dt.strptime(x, "%Y-%m-%d") for x in testRawDates]
        tests = testsData[:, 1].astype(np.float)

    testTotal = np.copy(tests)
    for j, date in enumerate(testRawDates):
        if date in casesDict:
            tests[j] = casesDict[date] / tests[j] * 100
        else:
            tests[j] = 0

    if avg:
        tests = n_day_avg(tests, 7)

    # remove the most recent two dates as they won't be accurate yet
    skip = 2
    cases = cases[skip:]
    casesDates = casesDates[skip:]
    tests = tests[skip:]
    testTotal = testTotal[skip:]
    testDates = testDates[skip:]

    plt.figure()
    _, ax = plt.subplots()

    figname = plotsDir + "PercentPositive"
    if avg:
        figname += "-Avg"

    ax.set_title("UK COVID-19 cases compared to percentage of positive tests")

    ax.bar(casesDates, cases)
    if avg:
        ax.set_ylabel("Daily COVID-19 Cases in the UK (seven day average)", color="C0")
    else:
        ax.set_ylabel("Daily COVID-19 Cases in the UK", color="C0")

    ax2 = ax.twinx()

    ax2.plot_date(testDates, tests, "white", linewidth=3)
    ax2.plot_date(testDates, tests, "orangered", linewidth=2)

    yLabel = "Percent positive tests per day"
    if avg:
        yLabel += " (seven day average)"

    ax2.set_ylabel(
        yLabel, color="orangered", rotation=270, ha="center", va="bottom",
    )

    ax2.set_ylim(bottom=0)

    ax.xaxis_date()
    ax.set_xlim(left=dt.strptime("2020-03-01", "%Y-%m-%d"), right=today)
    ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))

    ax2.yaxis.set_major_formatter(tkr.PercentFormatter(decimals=0))
    ax2.hlines(
        y=5,
        xmin=dt.strptime("2020-01-30", "%Y-%m-%d"),
        xmax=today,
        linestyles="dotted",
        color="black",
        label="WHO 5% reopening threshold",
    )

    plt.legend()

    plt.gcf().set_size_inches(12, 7.5)
    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)

    savePlot(figname)

    # Double bar chart
    figname = plotsDir + "DoubleBarChart"
    if avg:
        figname += "-Avg"
    plt.figure()
    _, ax = plt.subplots()

    ax.set_title("Number of tests vs positive tests")

    if avg:
        testTotal = n_day_avg(testTotal, 7)

    fivePercent = [x * 0.05 for x in testTotal]

    ax.bar(testDates, testTotal, color="C0", label="Total tests")
    ax.bar(testDates, fivePercent, color="black", label="WHO 5% reopening threshold")
    ax.bar(casesDates, cases, color="orangered", label="Positive tests")

    ax.xaxis_date()
    ax.set_xlim(
        left=dt.strptime("2020-03-01", "%Y-%m-%d"), right=today,
    )

    yLabel = "Number of tests per day"
    if avg:
        yLabel += " (seven day average)"
    ax.set_ylabel(yLabel)
    ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))

    plt.gcf().set_size_inches(12, 7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend()

    savePlot(figname)


def nationPlot(dataDir="data/", plotsDir="plots/", avg=True):
    """avg indicates seven day average of new cases should be used"""
    nationsCases = []
    nationCasesDates = []
    testsData = []
    testTotalData = []
    nationTestDates = []

    nations = ["Scotland", "England", "Northern Ireland", "Wales"]
    colors = ["#003078", "#5694CA", "#FFDD00", "#D4351C"]

    today = dt.today()

    for nation in nations:
        filePrefix = dataDir + nation
        testsFileName = filePrefix + ".testing." + today.strftime("%Y-%m-%d") + ".csv"
        casesFileName = filePrefix + ".cases." + today.strftime("%Y-%m-%d") + ".csv"

        with open(casesFileName, "r") as file:
            next(file)  # skip first line
            reader = csv.reader(file, delimiter=",")
            casesData = [[line[0], int(line[1])] for line in reader]
            casesDict = dict(casesData)
            # convert to np array and separate dates from case counts
            casesData = np.array(casesData)
            casesDates = casesData[:, 0]
            cases = casesData[:, 1].astype(np.float)
            casesDates = [dt.strptime(x, "%Y-%m-%d") for x in casesDates]
            # compute seven day average of cases if enabled
            if avg:
                cases = n_day_avg(cases, 7)

        with open(testsFileName, "r") as file:
            next(file)  # skip first line
            reader = csv.reader(file, delimiter=",")
            nationTestData = [
                (line[0], parseInt(line[1]) + parseInt(line[2]) + parseInt(line[3]))
                for line in reader
            ]
            nationTestData = np.array(nationTestData)
            testRawDates = nationTestData[:, 0]
            testDates = [dt.strptime(x, "%Y-%m-%d") for x in testRawDates]
            tests = nationTestData[:, 1].astype(np.float)

        testTotal = np.copy(tests)
        for j, date in enumerate(testRawDates):
            if date in casesDict:
                tests[j] = min(casesDict[date] / tests[j] * 100, 100)
            else:
                tests[j] = 0

        # remove the most recent two dates as they won't be accurate yet
        skip = 2
        nationsCases.append(cases[skip:])
        nationCasesDates.append(casesDates[skip:])

        testsData.append(tests[skip:])
        testTotalData.append(testTotal[skip:])
        nationTestDates.append(testDates[skip:])

    plt.figure()
    _, ax = plt.subplots()

    figname = plotsDir + "PercentPositive-Nation"
    if avg:
        figname += "-Avg"

    ax.set_title("UK COVID-19 cases compared to percentage of positive tests")

    for i, nation in enumerate(testsData):
        if avg:
            nation = n_day_avg(nation, 7)
        ax.plot_date(
            nationTestDates[i], nation, colors[i], linewidth=2, label=nations[i]
        )

    yLabel = plotsDir + "Percent positive tests per day"
    if avg:
        yLabel += " (seven day average)"

    ax.set_ylabel(yLabel)

    ax.set_ylim(bottom=0)

    ax.xaxis_date()
    ax.set_xlim(left=dt.strptime("2020-03-01", "%Y-%m-%d"), right=today)

    ax.yaxis.set_major_formatter(tkr.PercentFormatter(decimals=0))
    ax.hlines(
        y=5,
        xmin=dt.strptime("2020-01-30", "%Y-%m-%d"),
        xmax=dt.strptime("2020-11-01", "%Y-%m-%d"),
        linestyles="dotted",
        color="black",
        label="WHO 5% reopening threshold",
    )

    # ax.vlines(x=dt.strptime("2020-04-21", "%Y-%m-%d"), ymin=0, ymax=3000)

    plt.legend()

    plt.gcf().set_size_inches(12, 7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    savePlot(figname)

    # Double bar chart
    figname = plotsDir + "DoubleBarChart-Nation"
    if avg:
        figname += "-Avg"
    plt.figure()
    fig, axs = plt.subplots(2, 2, sharex=True)
    axs = axs.flatten()
    fig.suptitle("Number of tests vs positive tests")

    for j, ax in enumerate(axs):
        testTotal = testTotalData[j]

        if avg:
            testTotal = n_day_avg(testTotal, 7)

        fivePercent = [x * 0.05 for x in testTotal]

        ax.bar(nationTestDates[j], testTotal, color="C0", label="Total tests")
        ax.bar(
            nationTestDates[j],
            fivePercent,
            color="black",
            label="WHO 5% reopening threshold",
        )
        ax.bar(
            nationCasesDates[j],
            nationsCases[j],
            color="orangered",
            label="Positive tests",
        )

        ax.xaxis_date()
        ax.set_xlim(
            left=dt.strptime("2020-03-01", "%Y-%m-%d"), right=today,
        )

        yLabel = "Number of tests per day"
        if avg:
            yLabel += " (seven day average)"
        ax.set_ylabel(yLabel)
        ax.set_title(nations[j])
        ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    plt.gcf().set_size_inches(15, 9)

    savePlot(figname)


def heatMapPlot(dataDir="data/", plotsDir="plots/"):
    today = dt.today()

    filePrefix = dataDir + "UK"
    casesFileName = filePrefix + ".cases." + today.strftime("%Y-%m-%d") + ".csv"
    reportedFileName = filePrefix + ".cases.reported." + today.strftime("%Y-%m-%d") + ".csv"
    testsFileName = filePrefix + ".testing." + today.strftime("%Y-%m-%d") + ".csv"

    with open(casesFileName, "r") as file:
        next(file)
        reader = csv.reader(file, delimiter=",")
        casesData = [[line[0], int(line[1])] for line in reader]

    with open(reportedFileName, "r") as file:
        next(file)
        reader = csv.reader(file, delimiter=",")
        reportedData = [[line[0], int(line[1])] for line in reader]

    with open(testsFileName, "r") as file:
        next(file)
        reader = csv.reader(file, delimiter=",")
        testsData = [
            (line[0], parseInt(line[1]) + parseInt(line[2]) + parseInt(line[3]))
            for line in reader
        ]

    casesDf = pd.DataFrame(casesData, columns=["Date", "Cases"])
    reportedDf = pd.DataFrame(reportedData, columns=["Date", "Cases"])
    testsDf = pd.DataFrame(testsData, columns=["Date", "Tests"])

    casesDf["Date"] = pd.to_datetime(casesDf["Date"])
    reportedDf["Date"] = pd.to_datetime(reportedDf["Date"])
    testsDf["Date"] = pd.to_datetime(testsDf["Date"])

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    casesWeekDf = casesDf.groupby(casesDf["Date"].dt.day_name()).mean().reindex(days)
    reportedWeekDf = reportedDf.groupby(reportedDf["Date"].dt.day_name()).mean().reindex(days)
    testsWeekDf = testsDf.groupby(testsDf["Date"].dt.day_name()).mean().reindex(days)

    dataFrames = [testsWeekDf, reportedWeekDf, casesWeekDf]
    names = ["Tests", "Cases (reported date)", "Cases (specimen date)"]

    figname = plotsDir + "testsCasesHeatMap"
    plt.figure()
    fig, axs = plt.subplots(3, 1, sharex=True)

    for j, ax in enumerate(axs):
        ax.set_ylabel(names[j], rotation=0, ha="right", va="center")
        ax.tick_params(axis="y", which="both", left=False, labelleft=False)
        plt.xticks(ticks=list(range(7)), labels=days)

        hm = ax.imshow(
            [dataFrames[j]], cmap="plasma", interpolation="none", aspect="auto"
        )
        plt.colorbar(hm, ax=ax, format=threeFigureFormatter, aspect=10)

        removeSpines(ax)

    fig.suptitle("Heatmap of number of tests or cases per day")
    plt.gcf().set_size_inches(10, 5)

    savePlot(figname)


# Helpers ------------------------------------------------------------------------------


def savePlot(figname):
    plt.savefig(figname, bbox_inches="tight", pad_inches=0.25, dpi=200)
    plt.cla()
    plt.close()


def threeFigureFormatter(x, pos):
    s = "%d" % x
    if abs(x) >= 1:
        groups = []
        while s and s[-1].isdigit():
            groups.append(s[-3:])
            s = s[:-3]
        return s + ",".join(reversed(groups))
    else:
        return s


def removeSpines(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def n_day_avg(xs, n=7):
    """compute n day average of time series, using maximum possible number of days at
    start of series"""
    return [np.mean(xs[max(0, i + 1 - n) : i + 1]) for i in range(xs.shape[0])]


def parseInt(str):
    str = str.strip()
    return int(str) if str else 0


if __name__ == "__main__":
    dataDir = "data/"
    plotsDir = "plots/"

    if not os.path.exists(dataDir):
        os.mkdir(dataDir)

    if not os.path.exists(plotsDir):
        os.mkdir(plotsDir)

    getData(dataDir)

    # ukPlot(dataDir, plotsDir, avg=False)
    # ukPlot(dataDir, plotsDir)

    # nationPlot(dataDir, plotsDir, avg=False)
    # nationPlot(dataDir, plotsDir)

    # heatMapPlot(dataDir, plotsDir)

