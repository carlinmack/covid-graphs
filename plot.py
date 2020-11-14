import argparse
import csv
import math
import os
from datetime import datetime as dt
from operator import add

import matplotlib
import matplotlib.font_manager as font_manager
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import matplotlib.ticker as tkr
import numpy as np
import pandas as pd
import requests
from matplotlib.dates import DateFormatter as df
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

        for i, name in enumerate(names):
            suffix = urls[i] + urlSuffix
            for nation in nations:
                prefix = urlPrefix.format("nation;areaName={}").format(nation)
                getCSV(prefix + suffix, nation + "." + name)

            prefix = urlPrefix.format("overview")
            getCSV(prefix + suffix, "UK." + name)

        with open(dataDir + "Last-Modified.txt", "w") as file:
            file.write(lastModified)

        print("Done!")
        return True
    else:
        return False


def mainPlot(t, dataDir="data/", plotsDir="plots/", avg=True):
    """avg indicates seven day average of new cases should be used"""

    def readFile(name, dictionary=False, raw=False):
        with open(name, "r") as file:
            reader = csv.reader(file, delimiter=",")
            data = [[line[0], int(line[1])] for line in reader]
        # convert to np array and separate dates from case counts
        casesData = np.array(data)
        casesRawDates = casesData[:, 0]
        casesDates = [dt.strptime(x, "%Y-%m-%d") for x in casesRawDates]
        cases = casesData[:, 1].astype(np.float)
        mortCases = n_day_sum(cases, 28)
        # compute seven day average of cases if enabled
        if avg:
            cases = n_day_avg(cases, 7)

        if dictionary:
            casesDict = dict(zip(casesRawDates, cases))
            mortCasesDict = dict(zip(casesRawDates, mortCases))
            return cases, casesDates, casesDict, mortCasesDict

        if raw:
            return cases, casesDates, casesRawDates

        return cases, casesDates

    def percentOf28daysCases(deaths, deathDates, mortCasesDict):
        mortality = [0] * len(deaths)
        for j, date in enumerate(deathDates):
            casesDate = date.strftime("%Y-%m-%d")

            if (
                deaths[j]
                and casesDate in mortCasesDict
                and mortCasesDict[casesDate] > 0
            ):
                mortality[j] = min(deaths[j] / mortCasesDict[casesDate] * 100, 100)
            else:
                mortality[j] = 0
        return mortality

    def getData(name):
        casesFileName = dataDir + name + ".cases.csv"
        testsFileName = dataDir + name + ".testing.csv"
        deathsFileName = dataDir + name + ".deaths.csv"
        hospitalisationsFileName = dataDir + name + ".hospitalisations.csv"

        nationData = {}

        cases, casesDates, casesDict, mortCasesDict = readFile(
            casesFileName, dictionary=True
        )

        testsOriginal, testDates, testRawDates = readFile(testsFileName, raw=True)

        tests = np.copy(testsOriginal)

        for j, date in enumerate(testRawDates):
            if date in casesDict:
                tests[j] = min(casesDict[date] / tests[j] * 100, 100)
            else:
                tests[j] = 0

        deaths, deathDates = readFile(deathsFileName)

        mortality = percentOf28daysCases(deaths, deathDates, mortCasesDict)

        hospitalisations, hospitalisationDates = readFile(hospitalisationsFileName)

        hospitalisations = percentOf28daysCases(
            hospitalisations, hospitalisationDates, mortCasesDict
        )

        # remove the most recent three dates as they won't be accurate yet
        skip = 3
        nationData["cases"] = cases[:-skip]
        nationData["casesDates"] = casesDates[:-skip]
        nationData["tests"] = tests[:-skip]
        nationData["testDates"] = testDates[:-skip]
        nationData["testsOriginal"] = testsOriginal[:-skip]
        nationData["mortality"] = mortality[:-skip]
        nationData["deathDates"] = deathDates[:-skip]
        nationData["hospitalisations"] = hospitalisations[:-skip]
        nationData["hospitalisationDates"] = hospitalisationDates[:-skip]

        return nationData

    def lockdownVlines(ax, outerI):
        nationLockdownDates = [
            [
                [
                    dt.strptime("2020-03-23", "%Y-%m-%d"),
                    dt.strptime("2020-11-05", "%Y-%m-%d"),
                ]
            ],
        ]
        nationLockdownEasing = [
            [dt.strptime("2020-07-04", "%Y-%m-%d")],
        ]

        ymin, ymax = ax.get_ylim()
        for date in nationLockdownDates[outerI]:
            ax.vlines(
                x=date,
                ymin=ymin,
                ymax=ymax,
                color="#FF41367F",
                label="Start of lockdown",
            )

        ax.vlines(
            x=nationLockdownEasing[outerI],
            ymin=ymin,
            ymax=ymax,
            color="#3D99707F",
            label="End of lockdown",
        )

    nationList = [["UK"], ["Scotland", "England", "Northern Ireland", "Wales"]]
    colorsList = [["#2271d3"], ["#003078", "#5694CA", "#FFDD00", "#D4351C"]]
    fignames = ["", "-Nation"]
    titles = ["", " nation"]

    leftLim = dt.strptime("2020-03-01", "%Y-%m-%d")
    rightLim = dt.today()

    for outerI, nations in enumerate(nationList):
        data = {}
        for nation in nations:
            data[nation] = getData(nation)

        plt.figure()
        fig, ax = plt.subplots()

        figname = plotsDir + "PercentPositive" + fignames[outerI]
        title = (
            "UK%s COVID-19 cases compared to percentage of positive tests"
            % titles[outerI]
        )
        if avg:
            figname += "-Avg"
            title = "Average " + title
        updateProgressBar(figname, t)

        ax.set_title(title, fontweight="bold")

        if outerI == 0:
            ax.bar(data["UK"]["casesDates"], data["UK"]["cases"], color="#2271d3")
            
            yLabel = "Daily COVID-19 Cases in the UK"
            if avg:
                yLabel += " (seven day average)"
            ax.set_ylabel(yLabel, color="#2271d3")

            ax2 = ax.twinx()

            ax2.plot_date(
                data["UK"]["testDates"], data["UK"]["tests"], "white", linewidth=3
            )
            ax2.plot_date(
                data["UK"]["testDates"], data["UK"]["tests"], "orangered", linewidth=2
            )

            yLabel = "Percent positive tests per day"
            if avg:
                yLabel += " (seven day average)"

            ax2.set_ylabel(
                yLabel, color="orangered", rotation=270, ha="center", va="bottom"
            )

            ax.spines["top"].set_visible(False)
            ax2.spines["top"].set_visible(False)
            ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))

            percentAxis(ax2)
            ax2.hlines(
                y=5,
                xmin=leftLim,
                xmax=rightLim,
                linestyles="dotted",
                color="black",
                label="WHO 5% reopening threshold",
            )

            lockdownVlines(ax2, outerI)
        elif outerI == 1:
            for i, nation in enumerate(data):
                nationTests = data[nation]["tests"]
                ax.plot_date(
                    data[nation]["testDates"],
                    nationTests,
                    colorsList[outerI][i],
                    linewidth=2,
                    label=nations[i],
                )

            ax.hlines(
                y=5,
                xmin=leftLim,
                xmax=rightLim,
                linestyles="dotted",
                color="black",
                label="WHO 5% reopening threshold",
            )

            yLabel = "Percent positive tests per day"
            if avg:
                yLabel += " (seven day average)"

            ax.set_ylabel(yLabel)
            percentAxis(ax)

        ax.set_xlabel(
            """
        Note: Positive rates should be at or below 5 percent for at least 14 days before
        a country can safely reopen, according to the World Health Organization.""",
            color="#666",
        )

        dateAxis(ax)

        plt.legend()
        removeSpines(ax)

        savePlot(figname, fig)

        # Double bar chart -------------------------------------------------------------
        figname = plotsDir + "DoubleBarChart" + fignames[outerI]
        title = "Number of tests vs positive tests"
        if avg:
            figname += "-Avg"
            title += " (averaged)"
        updateProgressBar(figname, t)
        plt.figure()

        if outerI == 0:
            fig, ax = plt.subplots()

            ax.set_title(title, fontweight="bold")

            fivePercent = [x * 0.05 for x in data["UK"]["testsOriginal"]]

            ax.bar(
                data["UK"]["testDates"],
                data["UK"]["testsOriginal"],
                color="#2271d3",
                label="Total tests",
            )
            ax.bar(
                data["UK"]["testDates"],
                fivePercent,
                color="black",
                label="WHO 5% reopening threshold",
            )
            ax.bar(
                data["UK"]["casesDates"],
                data["UK"]["cases"],
                color="orangered",
                label="Positive tests",
            )

            lockdownVlines(ax, outerI)

            dateAxis(ax)

            ax.set_xlabel(
                """
                Note: Positive rates should be at or below 5 percent for at least 14 days before
                a country can safely reopen, according to the World Health Organization.""",
                color="#666",
            )

            yLabel = "Number of tests per day"
            if avg:
                yLabel += " (seven day average)"
            ax.set_ylabel(yLabel)
            ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))

            removeSpines(ax)
            showGrid(ax, "y")

            ax.legend()
        else:
            fig, axs = plt.subplots(2, 2, sharex=True)
            axs = axs.flatten()
            fig.suptitle(title, fontweight="bold")

            for j, nation in enumerate(data):
                ax = axs[j]
                tests = data[nation]["testsOriginal"]

                fivePercent = [x * 0.05 for x in tests]

                ax.bar(
                    data[nation]["testDates"],
                    tests,
                    color="#2271d3",
                    label="Total tests",
                )
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

                dateAxis(ax)
                reduceXlabels(ax)

                yLabel = "Number of tests per day"
                if avg:
                    yLabel += " (seven day average)"
                ax.set_ylabel(yLabel)
                ax.set_title(nations[j])
                ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))

                removeSpines(ax)
                showGrid(ax, "y")

        savePlot(figname, fig)

        # Testing ----------------------------------------------------------------------
        figname = plotsDir + "Testing" + fignames[outerI]
        title = "Positive test rate of COVID-19 in the UK"
        if avg:
            figname += "-Avg"
            title = "Average positive test rate of COVID-19 in the UK"
        updateProgressBar(figname, t)
        plt.figure()

        if outerI == 0:
            fig, ax = plt.subplots()

            ax.set_title(title, fontweight="bold")

            tests = data["UK"]["tests"]

            ax.plot(data["UK"]["testDates"], tests, color="#333")

            ymin, ymax = ax.get_ylim()
            maxArray = [x >= 5 for x in tests]
            minArray = [x <= 5 for x in tests]
            ax.fill_between(
                data["UK"]["testDates"],
                5,
                tests,
                where=maxArray,
                facecolor="#FF41367F",
                interpolate=True,
            )
            ax.fill_between(
                data["UK"]["testDates"],
                5,
                tests,
                where=minArray,
                facecolor="#3D99707F",
                interpolate=True,
            )

            dateAxis(ax)

            ax.set_xlabel(
                """
                Note: Target positive testing rate is 5% according to the World Health Organization.""",
                color="#666",
            )

            yLabel = "Percent positive tests per day"
            if avg:
                yLabel += " (seven day average)"
            ax.set_ylabel(yLabel)
            percentAxis(ax)

            removeSpines(ax)
            showGrid(ax, "y")
        else:
            fig, axs = plt.subplots(2, 2, sharex=True)
            axs = axs.flatten()
            fig.suptitle(title, fontweight="bold")

            for j, nation in enumerate(data):
                ax = axs[j]
                tests = data[nation]["tests"]

                ax.plot(data[nation]["testDates"], tests, color="#333")

                ymin, ymax = ax.get_ylim()
                maxArray = [x >= 5 for x in tests]
                minArray = [x <= 5 for x in tests]
                ax.fill_between(
                    data[nation]["testDates"],
                    5,
                    tests,
                    where=maxArray,
                    facecolor="#FF41367F",
                    interpolate=True,
                )
                ax.fill_between(
                    data[nation]["testDates"],
                    5,
                    tests,
                    where=minArray,
                    facecolor="#3D99707F",
                    interpolate=True,
                )

                dateAxis(ax)
                reduceXlabels(ax)

                yLabel = "% positive tests per day"
                if avg:
                    yLabel += " (seven day average)"
                ax.set_ylabel(yLabel)
                ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))
                showGrid(ax, "y")
                percentAxis(ax)

                ax.set_title(nations[j])
                removeSpines(ax)

        savePlot(figname, fig)

        # Mortality/Hospitalisation plot -----------------------------------------------
        innerFignames = ["Mortality", "Hospitalisation"]
        innerTitles = ["Mortality", "Hospitalisation rate"]
        innerYs = ["deathDates", "hospitalisationDates"]
        innerXs = ["mortality", "hospitalisations"]
        innerYlables = innerXs
        innerNotes = [
            "Mortality is calculated as deaths",
            "Hospitalisation rate is caluated as hospitalisations",
        ]

        for innerI in range(len(innerFignames)):
            figname = plotsDir + innerFignames[innerI] + fignames[outerI]
            if avg:
                figname += "-Avg"
            updateProgressBar(figname, t)
            plt.figure()
            fig, ax = plt.subplots()

            if outerI == 0:
                title = "%s of COVID-19 in the UK" % innerTitles[innerI]

                ax.bar(data["UK"]["casesDates"], data["UK"]["cases"], color="#2271d3")
                yLabel = "Daily COVID-19 Cases in the UK"
                if avg:
                    yLabel += " (seven day average)"

                ax.set_ylabel(yLabel, color="#2271d3")

                ax2 = ax.twinx()

                ax2.plot_date(
                    data["UK"][innerYs[innerI]],
                    data["UK"][innerXs[innerI]],
                    "white",
                    linewidth=3,
                )
                ax2.plot_date(
                    data["UK"][innerYs[innerI]],
                    data["UK"][innerXs[innerI]],
                    "orangered",
                    linewidth=2,
                )

                yLabel = "Percent %s per day" % innerYlables[innerI]
                if avg:
                    yLabel += " (seven day average)"

                ax2.set_ylabel(
                    yLabel, color="orangered", rotation=270, ha="center", va="bottom"
                )

                ax.spines["top"].set_visible(False)
                ax2.spines["top"].set_visible(False)

                ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))
                percentAxis(ax2)
            elif outerI == 1:
                title = "%s of COVID-19 in UK nations" % innerTitles[innerI]

                for i, nation in enumerate(data):
                    nationDeaths = data[nation][innerXs[innerI]]
                    ax.plot_date(
                        data[nation][innerYs[innerI]],
                        nationDeaths,
                        colorsList[outerI][i],
                        linewidth=2,
                        label=nations[i],
                    )

                yLabel = "Percent %s per day" % innerYlables[innerI]
                if avg:
                    yLabel += " (seven day average)"

                ax.set_ylabel(yLabel)
                percentAxis(ax)

                plt.legend()

            if avg:
                title += " (averaged)"
            ax.set_title(title, fontweight="bold")

            ax.set_xlabel(
                """
            Note: %s per day divided by the sum of cases in the prior 28 days"""
                % innerNotes[innerI],
                color="#666",
            )

            dateAxis(ax)

            removeSpines(ax)

            savePlot(figname, fig)


def nationReportedPlot(t, dataDir="data/", plotsDir="plots/", avg=True):
    nations = ["England", "Northern Ireland", "Scotland", "Wales"]
    colors = ["#5694CA", "#FFDD00", "#003078", "#D4351C"]
    populations = [56286961, 1893667, 5463300, 3152879]
    totalPopulation = sum(populations)

    leftLim = dt.strptime("2020-03-01", "%Y-%m-%d")
    rightLim = dt.today()

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
            if avg:
                reportedData = n_day_avg(reportedData, 7)

            nationsReported.append(reportedData)
            nationDates.append(testDates)

        fignameSuffix = ["", "-Per-Capita"]
        titleSuffix = ["", ", per capita"]
        perCapita = [0, 1]

        for i in range(2):
            figname = plotsDir + fignameTypes[type] + fignameSuffix[i]
            title = " by date reported" + titleSuffix[i]
            if avg:
                figname += "-Avg"
                title = "Average " + titleTypesLower[type] + title
            else:
                title = titleTypesUpper[type] + title
            updateProgressBar(figname, t)
            plt.figure()
            fig, ax = plt.subplots()
            ax.set_title(title, fontweight="bold")

            bottom = [0] * len(nationsReported[0])

            for j, nation in enumerate(nations):
                reportedData = nationsReported[j]
                dates = nationDates[j]

                if perCapita[i]:
                    reportedData = [x / populations[j] * 100 for x in reportedData]
                    ax.plot(
                        dates, reportedData, color=colors[j], label=nation, linewidth=2
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

            dateAxis(ax)
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(reversed(handles), reversed(labels))

            if perCapita[i]:
                yLabel = "Percent of nation " + yLabelTypes[type]
            else:
                yLabel = "Reported " + titleTypesLower[type]

            if avg:
                yLabel += " (seven day average)"
            ax.set_ylabel(yLabel)

            if perCapita[i]:
                percentAxis(ax)
            else:
                ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))

            removeSpines(ax)
            showGrid(ax, "y")

            savePlot(figname, fig)

        # Cumulative
        yLabels = ["UK population", "nation"]

        if not avg:
            for i in range(2):
                figname = (
                    plotsDir + fignameTypes[type] + "-Cumulative" + fignameSuffix[i]
                )
                updateProgressBar(figname, t)
                plt.figure()
                fig, ax = plt.subplots()
                ax.set_title(
                    "Cumulative %s by date reported%s"
                    % (titleTypesLower[type], titleSuffix[i]),
                    fontweight="bold",
                )

                bottom = [0] * len(nationsReported[0])

                for j, nation in enumerate(nations):
                    reportedData = nationsReported[j]
                    if perCapita[i]:
                        reportedData = [x / populations[j] * 100 for x in reportedData]
                    else:
                        reportedData = [x / totalPopulation * 100 for x in reportedData]
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

                dateAxis(ax)
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(reversed(handles), reversed(labels))

                percentAxis(ax)
                yLabel = "Percent of " + yLabels[i] + " " + yLabelTypes[type]
                if avg:
                    yLabel += " (seven day average)"
                ax.set_ylabel(yLabel)

                removeSpines(ax)
                showGrid(ax, "y")

                savePlot(figname, fig)


def heatMapPlot(t, dataDir="data/", plotsDir="plots/"):
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
        updateProgressBar(figname, t)
        plt.figure()
        fig, axs = plt.subplots(len(dataFrames), 1, sharex=True)

        for j, ax in enumerate(axs):
            plt.xticks(ticks=list(range(7)), labels=days)

            plotHeatmap(ax, names[i][j], dataFrames[j])

        fig.suptitle("Heatmap of number of %s per day" % titles[i], fontweight="bold")

        savePlot(figname, fig, (10, 5))

        # Nations
        nations = ["Scotland", "England", "Northern Ireland", "Wales"]
        colors = ["#003078", "#5694CA", "#FFDD00", "#D4351C"]
        nationsDf = []

        for nation in nations:
            nationDataFrame = getDataframes(nation, casesBoolean[i])

            nationsDf.append(nationDataFrame)

        figname = plotsDir + fignames[i] + "HeatMap-Nation"
        updateProgressBar(figname, t)

        fig = plt.figure(figsize=(20, 10))
        outerAxs = gridspec.GridSpec(2, 2, hspace=0.3)

        fig.suptitle("Heatmap of number of %s per day" % titles[i], fontweight="bold")

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

        savePlot(figname, fig, (20, 10))


# Helpers ------------------------------------------------------------------------------


def updateProgressBar(figname, t):
    t.update()
    t.set_description(figname)


def savePlot(figname, fig, size=()):
    if size:
        plt.gcf().set_size_inches(*size)
    else:
        plt.gcf().set_size_inches(12, 8)
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
    ax.grid(color="#e5e5e5", which="major", axis=axis, linestyle="solid")
    ax.set_axisbelow(True)


def dateAxis(ax):
    ax.set_xlim(left=dt.strptime("2020-03-01", "%Y-%m-%d"), right=dt.today())
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(df("%d %b"))


def percentAxis(ax):
    ax.set_ylim(bottom=0)
    ticks = ax.get_yticks()
    dataRange = max(ticks) - min(ticks)
    roundingDecimals = math.ceil(2.0 - math.log10(2.0 * dataRange))
    decimals = max(map(lambda x: decimalPlaces(x, roundingDecimals), ticks))
    ax.yaxis.set_major_formatter(tkr.PercentFormatter(decimals=decimals))


def reduceXlabels(ax, every_nth=2):
    for n, label in enumerate(ax.xaxis.get_ticklabels()):
        if n % every_nth != 0:
            label.set_visible(False)


def n_day_avg(xs, n=7):
    """compute n day average of time series, using maximum possible number of days at
    start of series"""
    return [np.mean(xs[max(0, i + 1 - n) : i + 1]) for i in range(xs.shape[0])]


def n_day_sum(xs, n=28):
    """compute n day sum of time series, using maximum possible number of days at
    start of series"""
    return [np.sum(xs[max(0, i + 1 - n) : i + 1]) for i in range(xs.shape[0])]


def parseInt(str):
    str = str.strip()
    return int(str) if str else 0


def decimalPlaces(number, digits):
    s = str(round(number, digits))
    s = s.strip("0")

    if not "." in s:
        return 0
    return len(s) - s.index(".") - 1


def defineArgParser():
    """Creates parser for command line arguments"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "-d", "--dryrun", help="Don't get new data", action="store_true"
    )

    parser.add_argument(
        "-f", "--force", help="Get data even if it is not new", action="store_true"
    )

    parser.add_argument(
        "-t", "--test", help="Plot even if there is no new data", action="store_true"
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

    fontFiles = font_manager.findSystemFonts(fontpaths=["font"])
    for fontFile in fontFiles:
        font_manager.fontManager.addfont(fontFile)

    if "Inter" in [f.name for f in font_manager.fontManager.ttflist]:
        matplotlib.rcParams["font.family"] = "Inter"

    newData = False
    if not clArgs.dryrun:
        newData = getData(dataDir, clArgs.force)

    if newData or clArgs.test or clArgs.dryrun:
        t = tqdm(
            total=36, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} {elapsed_s:.0f}s"
        )

        mainPlot(t, dataDir, plotsDir, avg=False)
        mainPlot(t, dataDir, plotsDir)

        nationReportedPlot(t, dataDir, plotsDir)
        nationReportedPlot(t, dataDir, plotsDir, avg=False)

        heatMapPlot(t, dataDir, plotsDir)

        t.close()
    else:
        print("No new data.")
