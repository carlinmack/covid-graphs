import csv
import os
import requests
from datetime import datetime as dt
from datetime import timedelta

import matplotlib.pyplot as plt
import matplotlib.ticker as tkr
import numpy as np


def getData(dataDir):
    nations = ["Scotland", "England", "Northern%2520Ireland", "Wales"]
    testingURL = "https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=nation;areaName={nation}&structure=%7B%22date%22:%22date%22,%22newPillarOneTestsByPublishDate%22:%22newPillarOneTestsByPublishDate%22,%22newPillarTwoTestsByPublishDate%22:%22newPillarTwoTestsByPublishDate%22,%22newPillarFourTestsByPublishDate%22:%22newPillarFourTestsByPublishDate%22%7D&format=csv"

    casesURL = "https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=nation;areaName={nation}&structure=%7B%22date%22:%22date%22,%22newCasesBySpecimenDate%22:%22newCasesBySpecimenDate%22%7D&format=csv"

    dataURLs = [testingURL, casesURL]
    names = ["testing", "cases"]

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


def n_day_avg(xs, n=7):
    """compute n day average of time series, using maximum possible number of days at
    start of series"""
    return [np.mean(xs[max(0, i + 1 - n) : i + 1]) for i in range(xs.shape[0])]


def ukPlot(dataDir="data/", avg=True):
    """avg indicates seven day average of new cases should be used"""
    today = dt.today()

    with open(dataDir + "cases.csv", "r") as file:
        reader = csv.reader(file, delimiter=",")
        casesData = [[line[3], int(line[4])] for line in reader]
        casesDict = dict(casesData)
        # convert to np array and separate dates from case counts
        casesData = np.array(casesData)
        casesDates = casesData[:, 0]
        cases = casesData[:, 1].astype(np.float)
        casesDates = [dt.strptime(x, "%Y-%m-%d") for x in casesDates]
        # compute seven day average of cases if enabled
        if avg:
            cases = n_day_avg(cases, 7)

    with open(dataDir + "tests.csv", "r") as file:
        reader = csv.reader(file, delimiter=",")
        testsData = [(line[3], int(line[8])) for line in reader]
        testsData = np.array(testsData)
        testRawDates = testsData[:, 0]
        testDates = [dt.strptime(x, "%Y-%m-%d") for x in testRawDates]
        tests = testsData[:, 1].astype(np.float)
        # if avg:
        #     tests = n_day_avg(tests,7)

    testTotal = np.copy(tests)
    for j, date in enumerate(testRawDates):
        if date in casesDict:
            tests[j] = casesDict[date] / tests[j] * 100
        else:
            tests[j] = 0

    if avg:
        tests = n_day_avg(tests, 7)

    plt.figure()
    _, ax = plt.subplots()

    figname = "PercentPositive"
    if avg:
        figname += "Avg"

    ax.set_title("UK COVID-19 cases compared to percentage of positive tests")

    ax.bar(casesDates, cases)
    if avg:
        ax.set_ylabel("Daily COVID-19 Cases in the UK (seven day average)", color="C0")
    else:
        ax.set_ylabel("Daily COVID-19 Cases in the UK", color="C0")

    ax2 = ax.twinx()
    ax2.plot_date(testDates, tests, "white", linewidth=3)
    ax2.plot_date(testDates, tests, "orangered", linewidth=2)
    if avg:
        ax2.set_ylabel(
            "Percent positive tests per day (seven day average)",
            color="orangered",
            rotation=270,
            ha="center",
            va="bottom",
        )
    else:
        ax2.set_ylabel(
            "Percent positive tests per day",
            color="orangered",
            rotation=270,
            ha="center",
            va="bottom",
        )

    ax2.set_ylim(bottom=0)

    ax.xaxis_date()
    ax.set_xlim(
        left=dt.strptime("2020-03-01", "%Y-%m-%d"),
        right=today,
    )
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
    figname = "DoubleBarChart"
    if avg:
        figname += "Avg"
    plt.figure()
    _, ax = plt.subplots()

    ax.set_title("Number of tests vs positive tests")

    if avg:
        testTotal = n_day_avg(testTotal, 7)
    ax.bar(testDates, testTotal, color="C0", label="Total tests")
    ax.bar(casesDates, cases, color="orangered", label="Positive tests")
    
    ax.xaxis_date()
    ax.set_xlim(
        left=dt.strptime("2020-03-01", "%Y-%m-%d"),
        right=today,
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


def nationPlot(dataDir="data/", avg=True):
    """avg indicates seven day average of new cases should be used"""
    casesData = []
    testsData = []

    nations = ["Scotland", "England", "Northern%2520Ireland", "Wales"]
    colors = ["#003078", "#5694CA", "#FFDD00", "#D4351C"]
            
    today = dt.today()

    for nation in nations:
        filePrefix = dataDir + nation 
        testsFileName = filePrefix + ".testing." + today.strftime("%Y-%m-%d") + ".csv"
        casesFileName = filePrefix + ".cases." + today.strftime("%Y-%m-%d") + ".csv"

        with open(dataDir + casesFileName, "r") as file:
            reader = csv.reader(file, delimiter=",")
            casesData = [[line[3], int(line[4])] for line in reader]
            casesDict = dict(casesData)
            # convert to np array and separate dates from case counts
            casesData = np.array(casesData)
            casesDates = casesData[:, 0]
            cases = casesData[:, 1].astype(np.float)
            casesDates = [dt.strptime(x, "%Y-%m-%d") for x in casesDates]
            # compute seven day average of cases if enabled
            if avg:
                cases = n_day_avg(cases, 7)

        with open(dataDir + testsFileName, "r") as file:
            reader = csv.reader(file, delimiter=",")
            testsData = [(line[3], int(line[8])) for line in reader]
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

    plt.figure()
    _, ax = plt.subplots()

    figname = "NationPercentPositive"
    if avg:
        figname += "Avg"

    ax.set_title("UK COVID-19 cases compared to percentage of positive tests")

    for i, nation in enumerate(testsData):
        ax.plot_date(testDates, nation, colors[i], linewidth=2)
    if avg:
        ax.set_ylabel(
            "Percent positive tests per day (seven day average)",
            color="orangered",
            rotation=270,
            ha="center",
            va="bottom",
        )
    else:
        ax.set_ylabel(
            "Percent positive tests per day",
            color="orangered",
            rotation=270,
            ha="center",
            va="bottom",
        )

    ax.set_ylim(bottom=0)

    ax.xaxis_date()
    ax.set_xlim(
        left=dt.strptime("2020-03-01", "%Y-%m-%d"),
        right=dt.strptime("2020-10-22", "%Y-%m-%d"),
    )

    ax.yaxis.set_major_formatter(tkr.PercentFormatter(decimals=0))
    ax.hlines(
        y=5,
        xmin=dt.strptime("2020-01-30", "%Y-%m-%d"),
        xmax=dt.strptime("2020-11-01", "%Y-%m-%d"),
        linestyles="dotted",
        color="black",
        label="WHO 5% reopening threshold",
    )

    plt.legend()

    plt.gcf().set_size_inches(12, 7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    savePlot(figname)

    # Double bar chart
    figname = "NationDoubleBarChart"
    if avg:
        figname += "Avg"
    plt.figure()
    fig, axs = plt.subplots(2,2,sharey=True)

    fig.suptitle("Number of tests vs positive tests")

    if avg:
        testTotal = n_day_avg(testTotal, 7)
    ax.bar(testDates, testTotal, color="C0", label="Total tests")
    ax.bar(casesDates, cases, color="orangered", label="Positive tests")

    ax.xaxis_date()
    ax.set_xlim(
        left=dt.strptime("2020-03-01", "%Y-%m-%d"),
        right=dt.strptime("2020-10-22", "%Y-%m-%d"),
    )

    yLabel = "Number of tests per day"
    if avg:
        yLabel += " (seven day average)"
    ax.set_ylabel(yLabel)
    ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))

    plt.gcf().set_size_inches(12, 7.5)
    ax.spines["top"].set_visible(False)

    ax.legend()

    savePlot(figname)


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


if __name__ == "__main__":
    dataDir = "data/"

    if not os.path.exists(dataDir):
        os.mkdir(dataDir)

    # getData(dataDir)

    ukPlot(dataDir, avg=False)
    ukPlot(dataDir,)

    # nationPlot(dataDir, avg=False)
    # nationPlot(dataDir,)
