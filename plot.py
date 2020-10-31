import argparse
import csv
import json
import os
from datetime import datetime as dt
from datetime import timedelta
from operator import add

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import matplotlib.ticker as tkr
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm


def getData(dataDir, force=False):
    def getCSV(url, name):
        r = requests.get(url)
        text = r.text
        fileName = dataDir + name + ".csv"

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
                    "%s,%s"
                    % (arr[0], parseInt(arr[1]) + parseInt(arr[2]) + parseInt(arr[3]))
                )
            data = newData

        data = "\n".join(data)

        with open(fileName, "w") as file:
            file.writelines(data)

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
        ]
        urlSuffix = "%7D&format=csv"
        names = ["testing", "cases", "cases.reported", "deaths", "deaths.reported"]

        nations = ["Scotland", "England", "Northern Ireland", "Wales"]

        for i, name in enumerate(names):
            for nation in nations:
                prefix = urlPrefix.format("nation;areaName={}").format(nation)
                url = prefix + urls[i] + urlSuffix

                getCSV(url, nation + "." + name)

            prefix = urlPrefix.format("overview")
            url = prefix + urls[i] + urlSuffix
            getCSV(url, "UK." + name)

        with open(dataDir + "Last-Modified.txt", "w") as file:
            file.write(lastModified)

        print("Done!")


def ukPlot(dataDir="data/", plotsDir="plots/", avg=True):
    """avg indicates seven day average of new cases should be used"""
    today = dt.today()

    casesFileName = dataDir + "UK.cases.csv"
    testsFileName = dataDir + "UK.testing.csv"

    with open(casesFileName, "r") as file:
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
        reader = csv.reader(file, delimiter=",")
        testsData = [(line[0], int(line[1])) for line in reader]
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
    skip = 3
    cases = cases[:-skip]
    casesDates = casesDates[:-skip]
    tests = tests[:-skip]
    testTotal = testTotal[:-skip]
    testDates = testDates[:-skip]

    plt.figure()
    fig, ax = plt.subplots()

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

    savePlot(figname, fig)

    # Double bar chart
    figname = plotsDir + "DoubleBarChart"
    if avg:
        figname += "-Avg"
    plt.figure()
    fig, ax = plt.subplots()

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

    savePlot(figname, fig)


def nationPlot(dataDir="data/", plotsDir="plots/", avg=True):
    """avg indicates seven day average of new cases should be used"""

    def getData(name):
        casesFileName = dataDir + nation + ".cases.csv"
        testsFileName = dataDir + nation + ".testing.csv"

        nationData = {}

        with open(casesFileName, "r") as file:
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
            reader = csv.reader(file, delimiter=",")
            nationTestData = [(line[0], int(line[1])) for line in reader]
            nationTestData = np.array(nationTestData)
            testRawDates = nationTestData[:, 0]
            testDates = [dt.strptime(x, "%Y-%m-%d") for x in testRawDates]
            tests = nationTestData[:, 1].astype(np.float)

        testsOriginal = np.copy(tests)
        for j, date in enumerate(testRawDates):
            if date in casesDict:
                tests[j] = min(casesDict[date] / tests[j] * 100, 100)
            else:
                tests[j] = 0

        # remove the most recent two dates as they won't be accurate yet
        skip = 3
        nationData["cases"] = cases[:-skip]
        nationData["casesDates"] = casesDates[:-skip]
        nationData["tests"] = tests[:-skip]
        nationData["testDates"] = testDates[:-skip]
        nationData["testsOriginal"] = testsOriginal[:-skip]

        return nationData

    nations = ["Scotland", "England", "Northern Ireland", "Wales"]
    colors = ["#003078", "#5694CA", "#FFDD00", "#D4351C"]

    today = dt.today()
    data = {}

    for nation in nations:
        data[nation] = getData(nation)

    plt.figure()
    fig, ax = plt.subplots()

    figname = plotsDir + "PercentPositive-Nation"
    if avg:
        figname += "-Avg"

    ax.set_title("UK COVID-19 cases compared to percentage of positive tests")

    for i, nation in enumerate(data):
        nationTests = data[nation]["tests"]
        if avg:
            nationTests = n_day_avg(nationTests, 7)
        ax.plot_date(
            data[nation]["testDates"],
            nationTests,
            colors[i],
            linewidth=2,
            label=nations[i],
        )

    yLabel = "Percent positive tests per day"
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

    plt.legend()

    plt.gcf().set_size_inches(12, 7.5)
    removeSpines(ax)

    savePlot(figname, fig)

    # Double bar chart
    figname = plotsDir + "DoubleBarChart-Nation"
    if avg:
        figname += "-Avg"
    plt.figure()
    fig, axs = plt.subplots(2, 2, sharex=True)
    axs = axs.flatten()
    fig.suptitle("Number of tests vs positive tests")

    for j, nation in enumerate(data):
        ax = axs[j]
        tests = data[nation]["testsOriginal"]

        if avg:
            tests = n_day_avg(tests, 7)

        fivePercent = [x * 0.05 for x in tests]

        ax.bar(data[nation]["testDates"], tests, color="C0", label="Total tests")
        ax.bar(
            data[nation]["testDates"],
            fivePercent,
            color="black",
            label="WHO 5% reopening threshold",
        )
        ax.bar(
            data[nation]["casesDates"],
            data[nation]["cases"],
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

        removeSpines(ax)

    plt.gcf().set_size_inches(15, 9)

    savePlot(figname, fig)


def nationReportedPlot(dataDir="data/", plotsDir="plots/", avg=True):
    nations = ["England", "Northern Ireland", "Scotland", "Wales"]
    colors = ["#5694CA", "#FFDD00", "#003078", "#D4351C"]
    populations = [56286961, 1893667, 5463300, 3152879]
    totalPopulation = sum(populations)

    today = dt.today()

    fileNameTypes = [".cases.reported", ".deaths.reported"]
    fignameTypes = ["Nation-Reported-Cases", "Nation-Reported-Deaths"]
    titleTypesUpper = ["Cases", "Deaths"]
    titleTypesLower = ["cases", "deaths"]
    yLabelTypes = ["tested positive", "who have died within 28 days of a positive test"]

    for type in range(2):
        nationsReported = []
        nationDates = []

        for nation in nations:
            reportedFileName = dataDir + nation + fileNameTypes[type] + ".csv"
            with open(reportedFileName, "r") as file:
                reader = csv.reader(file, delimiter=",")
                reportedData = [[line[0], int(line[1])] for line in reader]

            reportedData = np.array(reportedData)
            testDates = reportedData[:, 0]
            testDates = [dt.strptime(x, "%Y-%m-%d") for x in testDates]
            reportedData = reportedData[:, 1].astype(np.float)

            nationsReported.append(reportedData)
            nationDates.append(testDates)

        fignameSuffix = ["", "-Per-Capita"]
        titleSuffix = ["", ", per capita"]
        perCapita = [0, 1]

        for i in range(2):
            figname = plotsDir + fignameTypes[type] + fignameSuffix[i]
            if avg:
                figname += "-Avg"
            plt.figure()
            fig, ax = plt.subplots()
            ax.set_title(titleTypesUpper[type] + " by date reported" + titleSuffix[i])

            if avg:
                bottom = [0] * len(nationsReported[0][3:])
            else:
                bottom = [0] * len(nationsReported[0])

            for j, nation in enumerate(nations):
                reportedData = nationsReported[j]
                dates = nationDates[j]

                if avg:
                    reportedData = n_day_avg(reportedData, 7)
                    # remove the most recent 3 days as they won't be accurate yet
                    reportedData = reportedData[3:]
                    dates = dates[3:]

                if perCapita[i]:
                    reportedData = [x / populations[j] * 100 for x in reportedData]

                if perCapita[i]:
                    ax.plot(
                        dates, reportedData, color=colors[j], label=nation, linewidth=2,
                    )
                else:
                    ax.bar(
                        dates,
                        reportedData,
                        color=colors[j],
                        label=nation,
                        bottom=bottom,
                    )

                bottom = list(map(add, reportedData, bottom))

            ax.xaxis_date()
            ax.set_xlim(
                left=dt.strptime("2020-03-01", "%Y-%m-%d"), right=today,
            )
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(reversed(handles), reversed(labels))

            if perCapita[i]:
                yLabel = "Percent of nation " + yLabelTypes[type]
            else:
                yLabel = "Reported " + titleTypesLower[type]

            if avg:
                yLabel += " (seven day average)"
            ax.set_ylabel(yLabel)
            ax.set_ylim(bottom=0)

            if perCapita[i]:
                ax.yaxis.set_major_formatter(tkr.PercentFormatter(decimals=2))
            else:
                ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))

            removeSpines(ax)

            plt.gcf().set_size_inches(15, 9)

            savePlot(figname, fig)

        # Cumulative
        yLabels = ["UK population", "nation"]

        if not avg:
            for i in range(2):
                figname = (
                    plotsDir + fignameTypes[type] + "-Cumulative" + fignameSuffix[i]
                )
                plt.figure()
                fig, ax = plt.subplots()
                ax.set_title(
                    "Cumulative %s by date reported%s"
                    % (titleTypesLower[type], titleSuffix[i])
                )

                bottom = [0] * len(nationsReported[0])

                for j, nation in enumerate(nations):
                    reportedData = nationsReported[j]
                    if perCapita[i]:
                        reportedData = [x / populations[j] * 100 for x in reportedData]
                    else:
                        reportedData = [x / totalPopulation * 100 for x in reportedData]
                    # reversed cumulative sum
                    reportedData = np.cumsum(reportedData)

                    if perCapita[i]:
                        ax.plot(
                            nationDates[j],
                            reportedData,
                            color=colors[j],
                            label=nation,
                            linewidth=2,
                        )
                    else:
                        ax.bar(
                            nationDates[j],
                            reportedData,
                            color=colors[j],
                            label=nation,
                            bottom=bottom,
                        )

                    bottom = list(map(add, reportedData, bottom))

                ax.xaxis_date()
                ax.set_xlim(
                    left=dt.strptime("2020-03-01", "%Y-%m-%d"), right=today,
                )
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(reversed(handles), reversed(labels))

                ax.yaxis.set_major_formatter(tkr.PercentFormatter(decimals=2))
                yLabel = "Percent of " + yLabels[i] + " " + yLabelTypes[type]
                if avg:
                    yLabel += " (seven day average)"
                ax.set_ylabel(yLabel)
                ax.set_ylim(bottom=0)

                removeSpines(ax)
                showGrid(ax, "y")

                plt.gcf().set_size_inches(15, 9)

                savePlot(figname, fig)


def heatMapPlot(dataDir="data/", plotsDir="plots/"):
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    def getDataframes(name, cases):
        if cases:
            fileNames = [
                dataDir + name + ".testing.csv",
                dataDir + name + ".cases.reported.csv",
                dataDir + name + ".cases.csv",
            ]
        else:
            fileNames = [
                dataDir + name + ".deaths.csv",
                dataDir + name + ".deaths.reported.csv",
            ]

        data = []
        dataFrames = []

        for i, fileName in enumerate(fileNames):
            with open(fileName, "r") as file:
                reader = csv.reader(file, delimiter=",")
                if i == 0 and cases:
                    fileData = [(line[0], int(line[1]),) for line in reader]
                else:
                    fileData = [[line[0], int(line[1])] for line in reader]

            data.append(fileData)

        for dataSet in data:
            dataFrame = pd.DataFrame(dataSet, columns=["Date", "Number"])
            dataFrame["Date"] = pd.to_datetime(dataFrame["Date"])
            dataFrame = (
                dataFrame.groupby(dataFrame["Date"].dt.day_name()).mean().reindex(days)
            )
            dataFrames.append(dataFrame)

        return dataFrames

    def plotHeatmap(ax, name, dataFrames):
        ax.set_ylabel(name, rotation=0, ha="right", va="center")
        ax.tick_params(axis="y", which="both", left=False, labelleft=False)
        hm = ax.imshow([dataFrames], cmap="plasma", interpolation="none", aspect="auto")
        plt.colorbar(hm, ax=ax, format=threeFigureFormatter, aspect=10)
        # ax.bar(range(7), dataFrames["Number"])

        removeSpines(ax)

    casesBoolean = [1, 0]
    fignames = ["TestsCases", "Deaths"]
    titles = ["tests/cases", "deaths"]

    names = [
        ["Tests", "Cases (reported date)", "Cases (specimen date)"],
        ["Deaths", "Reported Deaths"],
    ]

    for i in range(2):
        # UK
        dataFrames = getDataframes("UK", casesBoolean[i])

        figname = plotsDir + fignames[i] + "HeatMap"
        plt.figure()
        fig, axs = plt.subplots(len(dataFrames), 1, sharex=True)

        for j, ax in enumerate(axs):
            plt.xticks(ticks=list(range(7)), labels=days)

            plotHeatmap(ax, names[i][j], dataFrames[j])

        fig.suptitle("Heatmap of number of %s per day" % titles[i])
        plt.gcf().set_size_inches(10, 5)

        savePlot(figname, fig)

        # Nations
        nations = ["Scotland", "England", "Northern Ireland", "Wales"]
        colors = ["#003078", "#5694CA", "#FFDD00", "#D4351C"]
        nationsDf = []

        for nation in nations:
            nationDataFrame = getDataframes(nation, casesBoolean[i])

            nationsDf.append(nationDataFrame)

        figname = plotsDir + fignames[i] + "HeatMap-Nation"

        fig = plt.figure(figsize=(20, 10))
        outerAxs = gridspec.GridSpec(2, 2, hspace=0.3)

        fig.suptitle("Heatmap of number of %s per day" % titles[i])

        for k in range(4):
            inner = outerAxs[k].subgridspec(len(nationsDf[0]), 1, hspace=0.3)

            for j in range(len(nationsDf[0])):
                ax = fig.add_subplot(inner[j])
                if j == 0:
                    ax.set_title(nations[k])
                    ax.tick_params(
                        axis="x", which="both", bottom=False, labelbottom=False
                    )
                elif j == 1:
                    ax.tick_params(
                        axis="x", which="both", bottom=False, labelbottom=False
                    )
                elif j == 2:
                    plt.xticks(ticks=list(range(7)), labels=days)

                plotHeatmap(ax, names[i][j], nationsDf[k][j])
                fig.add_subplot(ax)

        savePlot(figname, fig)


# Helpers ------------------------------------------------------------------------------


def savePlot(figname, fig):
    plt.savefig(figname, bbox_inches="tight", pad_inches=0.25, dpi=200)
    plt.close(fig)


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


def removeSpines(ax, all=False):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if all:
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)


def showGrid(ax, axis):
    ax.grid(color="#ccc", which="major", axis=axis, linestyle="solid")
    ax.set_axisbelow(True)


def n_day_avg(xs, n=7):
    """compute n day average of time series, using maximum possible number of days at
    start of series"""
    return [np.mean(xs[max(0, i + 1 - n) : i + 1]) for i in range(xs.shape[0])]


def parseInt(str):
    str = str.strip()
    return int(str) if str else 0


def defineArgParser():
    """Creates parser for command line arguments"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "-d", "--dryrun", help="Don't get new data", action="store_true",
    )

    parser.add_argument(
        "-f", "--force", help="Get data even if it is not new", action="store_true",
    )

    parser.add_argument(
        "-D",
        "--dataDir",
        help="Directory where the dumps, partitions etc will be stored [default: data/]",
        default="data/",
        type=str,
    )

    parser.add_argument(
        "-P",
        "--plotsDir",
        help="Directory where the plots should be output to [default: plots/]",
        default="plots/",
        type=str,
    )

    return parser


if __name__ == "__main__":
    argParser = defineArgParser()
    clArgs = argParser.parse_args()

    dataDir = clArgs.dataDir
    plotsDir = clArgs.plotsDir

    if not os.path.exists(dataDir):
        os.mkdir(dataDir)

    if not os.path.exists(plotsDir):
        os.mkdir(plotsDir)

    if not clArgs.dryrun:
        getData(dataDir, clArgs.force)

    t = tqdm(total=4, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} {elapsed_s:.0f}s")

    t.set_description("UK Plots")
    ukPlot(dataDir, plotsDir, avg=False)
    ukPlot(dataDir, plotsDir)
    t.update()

    t.set_description("Nation Plots")
    nationPlot(dataDir, plotsDir, avg=False)
    nationPlot(dataDir, plotsDir)
    t.update()

    t.set_description("Nation Reported Cases and Reported Deaths Plots")
    nationReportedPlot(dataDir, plotsDir)
    nationReportedPlot(dataDir, plotsDir, avg=False)
    t.update()

    t.set_description("Heat Map Plots")
    heatMapPlot(dataDir, plotsDir)
    t.update()

    t.close()
