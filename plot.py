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
import mpld3
import numpy as np
import pandas as pd
from matplotlib.dates import DateFormatter as df
from tqdm import tqdm

from getData import getData
from readData import readData

def mainPlot(t, dataDir="data/", plotsDir="plots/", avg=True):
    """avg indicates seven day average of new cases should be used"""

    def readFile(name, dictionary=False, raw=False):
        data = readData(name)
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

        hospitalisationRate = percentOf28daysCases(
            hospitalisations, hospitalisationDates, mortCasesDict
        )

        # remove the most recent three dates as they won't be accurate yet
        skip = 4
        nationData["casesDates"] = casesDates[:-skip]
        nationData["cases"] = cases[:-skip]
        nationData["testDates"] = testDates[:-skip]
        nationData["posTests"] = tests[:-skip]
        nationData["tests"] = testsOriginal[:-skip]
        nationData["deathDates"] = deathDates[:-skip]
        nationData["deaths"] = deaths[:-skip]
        nationData["mortality"] = mortality[:-skip]
        nationData["hospitalisationDates"] = hospitalisationDates[:-skip]
        nationData["hospitalisations"] = hospitalisations[:-skip]
        nationData["hospitalisationRate"] = hospitalisationRate[:-skip]

        return nationData

    nationList = [["UK"], ["Scotland", "England", "Northern Ireland", "Wales"]]
    colorsList = [["#2271d3"], ["#003078", "#5694CA", "#FFDD00", "#D4351C"]]
    fignames = ["", "-Nation"]
    titles = ["", " nation"]

    for outerI, nations in enumerate(nationList):
        data = {}
        for nation in nations:
            data[nation] = getData(nation)

        fig, ax = plt.subplots()

        figname = "PercentPositive" + fignames[outerI]
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
            ax.bar(data["UK"]["casesDates"], data["UK"]["cases"], color="orangered")

            setYLabel(ax, "Daily COVID-19 Cases in the UK", avg, color="orangered")

            ax2 = ax.twinx()

            ax2.plot_date(
                data["UK"]["testDates"], data["UK"]["posTests"], "white", linewidth=3
            )
            ax2.plot_date(
                data["UK"]["testDates"],
                data["UK"]["posTests"],
                "#333",
                linewidth=2,
            )

            yLabel = "Percent positive tests per day"
            if avg:
                yLabel += " (seven day average)"

            ax2.set_ylabel(
                yLabel, rotation=270, ha="center", va="bottom"
            )

            ax.spines["top"].set_visible(False)
            ax2.spines["top"].set_visible(False)
            threeFigureAxis(ax)

            percentAxis(ax2)
            ax2.axline(
                (0, 5),
                slope=0,
                ls="dotted",
                color="black",
                label="WHO 5% reopening threshold",
            )

            lockdownVlines(ax2, outerI)
        elif outerI == 1:
            for i, nation in enumerate(data):
                nationTests = data[nation]["posTests"]
                ax.plot_date(
                    data[nation]["testDates"],
                    nationTests,
                    colorsList[outerI][i],
                    linewidth=2,
                    label=nations[i],
                )

            ax.axline(
                (0, 5),
                slope=0,
                ls="dotted",
                color="black",
                label="WHO 5% reopening threshold",
            )

            setYLabel(ax, "Percent positive tests per day", avg)
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

        savePlot(plotsDir, figname, fig)

        # Double bar chart -------------------------------------------------------------
        figname = "DoubleBarChart" + fignames[outerI]
        title = "Number of tests vs positive tests"
        if avg:
            figname += "-Avg"
            title += " (averaged)"
        updateProgressBar(figname, t)

        if outerI == 0:
            fig, ax = plt.subplots()

            ax.set_title(title, fontweight="bold")

            fivePercent = [x * 0.05 for x in data["UK"]["tests"]]

            ax.bar(
                data["UK"]["testDates"],
                data["UK"]["tests"],
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

            setYLabel(ax, "Number of tests per day", avg)
            threeFigureAxis(ax)

            removeSpines(ax)
            showGrid(ax)

            ax.legend()
        else:
            fig, axs = plt.subplots(2, 2, sharex=True)
            axs = axs.flatten()
            fig.suptitle(title, fontweight="bold")

            for j, nation in enumerate(data):
                ax = axs[j]
                tests = data[nation]["tests"]

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

                setYLabel(ax, "Number of tests per day", avg)

                ax.set_title(nations[j])
                threeFigureAxis(ax)

                removeSpines(ax)
                showGrid(ax)

        savePlot(plotsDir, figname, fig)

        # Testing ----------------------------------------------------------------------
        figname = "Testing" + fignames[outerI]
        title = "Positive test rate of COVID-19 in the UK"
        if avg:
            figname += "-Avg"
            title = "Average positive test rate of COVID-19 in the UK"
        updateProgressBar(figname, t)

        if outerI == 0:
            fig, ax = plt.subplots()

            ax.set_title(title, fontweight="bold")

            ax.plot(data["UK"]["testDates"], data["UK"]["posTests"], color="#333")

            maxArray = [x >= 5 for x in data["UK"]["posTests"]]
            minArray = [x <= 5 for x in data["UK"]["posTests"]]
            ax.fill_between(
                data["UK"]["testDates"],
                5,
                data["UK"]["posTests"],
                where=maxArray,
                facecolor="#FF41367F",
                interpolate=True,
            )
            ax.fill_between(
                data["UK"]["testDates"],
                5,
                data["UK"]["posTests"],
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

            setYLabel(ax, "Percent positive tests per day", avg)
            percentAxis(ax)

            removeSpines(ax)
            showGrid(ax)
        else:
            fig, axs = plt.subplots(2, 2, sharex=True)
            axs = axs.flatten()
            fig.suptitle(title, fontweight="bold")

            for j, nation in enumerate(data):
                ax = axs[j]

                ax.plot(
                    data[nation]["testDates"], data[nation]["posTests"], color="#333"
                )

                maxArray = [x >= 5 for x in data[nation]["posTests"]]
                minArray = [x <= 5 for x in data[nation]["posTests"]]
                ax.fill_between(
                    data[nation]["testDates"],
                    5,
                    data[nation]["posTests"],
                    where=maxArray,
                    facecolor="#FF41367F",
                    interpolate=True,
                )
                ax.fill_between(
                    data[nation]["testDates"],
                    5,
                    data[nation]["posTests"],
                    where=minArray,
                    facecolor="#3D99707F",
                    interpolate=True,
                )

                dateAxis(ax)
                reduceXlabels(ax)

                setYLabel(ax, "% positive tests per day", avg)
                showGrid(ax)
                percentAxis(ax)

                ax.set_title(nations[j])
                removeSpines(ax)

        savePlot(plotsDir, figname, fig)

        # Mortality/Hospitalisation plot -----------------------------------------------
        innerFignames = ["Mortality", "Hospitalisation"]
        innerTitles = ["Mortality", "Hospitalisation rate"]
        innerYs = ["deathDates", "hospitalisationDates"]
        innerXs = ["mortality", "hospitalisationRate"]
        innerYlables = innerXs
        innerNotes = [
            "Mortality is calculated as deaths",
            "Hospitalisation rate is calculated as hospitalisations",
        ]

        for innerI in range(len(innerFignames)):
            figname = innerFignames[innerI] + fignames[outerI]
            if avg:
                figname += "-Avg"
            updateProgressBar(figname, t)
            fig, ax = plt.subplots()

            if outerI == 0:
                title = "%s of COVID-19 in the UK" % innerTitles[innerI]

                ax.bar(data["UK"]["casesDates"], data["UK"]["cases"], color="#2271d3")
                setYLabel(ax, "Daily COVID-19 Cases in the UK", avg, color="#2271d3")

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

                threeFigureAxis(ax)
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

                setYLabel(ax, "Percent %s per day" % innerYlables[innerI], avg)
                percentAxis(ax)

                plt.legend()

            if avg:
                title += " (averaged)"
            ax.set_title(title, fontweight="bold")

            xLabel = (
                "\nNote: %s per day divided by the sum of cases in the prior 28 days"
                % innerNotes[innerI]
            )
            if innerI == 1 and outerI == 1:
                xLabel += "\nWales includes suspected COVID-19 patients in hospitalisation figures while the other nations include only confirmed cases."
            ax.set_xlabel(xLabel, color="#666")

            dateAxis(ax)

            removeSpines(ax)

            savePlot(plotsDir, figname, fig)

        if outerI == 0:
            ComparisonUK(plotsDir, avg, t, data)
        else:
            ComparisonNation(plotsDir, avg, t, data, nations)


def ComparisonUK(plotsDir, avg, t, data):
    figname = "Comparison"
    title = "Comparing daily COVID-19 cases, hospitalisation and deaths in the UK"
    if avg:
        figname += "-Avg"
    updateProgressBar(figname, t)
    fig, ax = plt.subplots()

    fig.subplots_adjust(right=0.75)

    ax2 = ax.twinx()
    ax3 = ax.twinx()
    axes = [ax, ax2, ax3]

    # Offset the right spine of par2.
    ax3.spines["right"].set_position(("axes", 1.15))
    # Second, show the right spine.
    ax3.spines["right"].set_visible(True)

    (p1,) = ax.plot(
        data["UK"]["casesDates"],
        data["UK"]["cases"],
        "orangered",
        ls="-",
        label="Cases",
    )
    (p2,) = ax2.plot(
        data["UK"]["hospitalisationDates"],
        data["UK"]["hospitalisations"],
        "#851bc2",
        ls="-",
        label="Hospitalisations",
    )
    (p3,) = ax3.plot(
        data["UK"]["deathDates"], data["UK"]["deaths"], "#333", ls="-", label="Deaths",
    )

    setYLabel(ax, "Cases", avg)
    setYLabel(ax2, "Hospitalisations", avg)
    setYLabel(ax3, "Deaths", avg)

    ax.yaxis.label.set_color(p1.get_color())
    ax2.yaxis.label.set_color(p2.get_color())

    if avg:
        title += " (averaged)"
    ax.set_title(title, fontweight="bold")

    dateAxis(ax)
    for axis in axes:
        threeFigureAxis(axis)

    lines = [p1, p2, p3]

    ax.legend(lines, [l.get_label() for l in lines], loc="upper center")

    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    removeSpines(ax3, all=True)
    ax3.spines["right"].set_visible(True)

    for axis in axes:
        axis.set_ylim(bottom=0)

    savePlot(plotsDir, figname, fig)


def ComparisonNation(plotsDir, avg, t, data, nations):
    populations = [5463300, 56286961, 1893667, 3152879]

    fignameSuffix = ["", "-Per-Capita"]
    titleSuffix = ["", ", per capita"]
    perCapita = [0, 1]

    for i in range(2):
        figname = "Comparison-Nation" + fignameSuffix[i]
        title = (
            "Comparing daily COVID-19 cases, hospitalisation and deaths in the UK nations"
            + titleSuffix[i]
        )
        if avg:
            figname += "-Avg"
        updateProgressBar(figname, t)

        fig, axs = plt.subplots(2, 2, sharex=True)
        fig.subplots_adjust(right=0.75, wspace=0.4)

        if avg:
            title += " (averaged)"
        fig.suptitle(title, fontweight="bold")

        axs = axs.flatten()
        primary_ax = []
        secondary_ax = []
        tertiary_ax = []
        axMax = [0, 0, 0]

        for j, nation in enumerate(data):
            ax = axs[j]
            ax2 = ax.twinx()
            ax3 = ax.twinx()
            axes = [ax, ax2, ax3]

            # Offset the right spine of par2.
            ax3.spines["right"].set_position(("axes", 1.15))
            # Second, show the right spine.
            ax3.spines["right"].set_visible(True)

            cases = data[nation]["cases"]
            hospitalisations = data[nation]["hospitalisations"]
            deaths = data[nation]["deaths"]

            if perCapita[i]:
                cases = [x / populations[j] * 100 for x in cases]
                hospitalisations = [x / populations[j] * 100 for x in hospitalisations]
                deaths = [x / populations[j] * 100 for x in deaths]

            (p1,) = ax.plot(data[nation]["casesDates"], cases, "orangered", ls="-")
            (p2,) = ax2.plot(
                data[nation]["hospitalisationDates"],
                hospitalisations,
                "#851bc2",
                ls="-",
            )
            ax3.plot(data[nation]["deathDates"], deaths, "#333", ls="-")

            setYLabel(ax, "Cases", avg)
            setYLabel(ax2, "Hospitalisations", avg)
            setYLabel(ax3, "Deaths", avg)

            ax.yaxis.label.set_color(p1.get_color())
            ax2.yaxis.label.set_color(p2.get_color())

            ax.set_title(title, fontweight="bold")

            dateAxis(ax)
            for axis in axes:
                if perCapita[i]:
                    percentAxis(axis)
                else:
                    threeFigureAxis(axis)

            ax.spines["top"].set_visible(False)
            ax2.spines["top"].set_visible(False)
            removeSpines(ax3, all=True)
            ax3.spines["right"].set_visible(True)

            if perCapita[i]:
                primary_ax.append(ax)
                secondary_ax.append(ax2)
                tertiary_ax.append(ax3)

                if j > 0:
                    ax.tick_params(labelleft=False)
                    ax2.tick_params(labelright=False)
                    ax3.tick_params(labelright=False)

            for k, axis in enumerate(axes):
                _, ymax = axis.get_ylim()
                if ymax > axMax[k]:
                    axMax[k] = ymax

            ax.set_title(nations[j])
            removeSpines(ax)

        if perCapita[i]:
            for axis in primary_ax:
                axis.set_ylim(bottom=0, top=axMax[0])

            for axis in secondary_ax:
                axis.set_ylim(bottom=0, top=axMax[1])

            for axis in tertiary_ax:
                axis.set_ylim(bottom=0, top=axMax[2])

        plt.annotate(
            "Note: Wales includes suspected COVID-19 patients in hospitalisation figures while the other nations include only confirmed cases.",
            xy=(0.25, 0.025),
            xycoords="figure fraction",
            color="#666",
        )

        savePlot(plotsDir, figname, fig, size=(24, 12))

def lockdownVlines(ax, outerI=0):
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
                color="#FF4136AF",
                ls="dashed",
                label="Start of lockdown",
            )

        ax.vlines(
            x=nationLockdownEasing[outerI],
            ymin=ymin,
            ymax=ymax,
            color="#3D9970AF",
            ls="dashed",
            label="End of lockdown",
        )


def nationReportedPlot(t, dataDir="data/", plotsDir="plots/", avg=True):
    data = [
        {"name": "England", "color": "#5694CA", "population": 56286961},
        {"name": "Northern Ireland", "color": "#FFDD00", "population": 1893667},
        {"name": "Scotland", "color": "#003078", "population": 5463300},
        {"name": "Wales", "color": "#D4351C", "population": 3152879},
    ]
    totalPopulation = sum([x["population"] for x in data])

    fileNameTypes = [".cases.reported", ".deaths.reported"]
    fignameTypes = ["Nation-Reported-Cases", "Nation-Reported-Deaths"]
    titleTypesUpper = ["Cases", "Deaths"]
    titleTypesLower = ["cases", "deaths"]
    yLabelTypes = ["tested positive", "who have died within 28 days of a positive test"]

    for type in range(2):
        for i, nation in enumerate(data):
            reportedFileName = dataDir + nation["name"] + fileNameTypes[type] + ".csv"
            reportedData = readData(reportedFileName)
            reportedData = np.array(reportedData)

            testDates = reportedData[:, 0]
            testDates = [dt.strptime(x, "%Y-%m-%d") for x in testDates]
            reportedData = reportedData[:, 1].astype(np.float)
            if avg:
                reportedData = n_day_avg(reportedData, 7)

            data[i]["reported"] = reportedData
            data[i]["dates"] = testDates

        fignameSuffix = ["", "-Per-Capita"]
        titleSuffix = ["", ", per capita"]
        perCapita = [0, 1]

        for i in range(2):
            figname = fignameTypes[type] + fignameSuffix[i]
            title = " by date reported" + titleSuffix[i]
            if avg:
                figname += "-Avg"
                title = "Average " + titleTypesLower[type] + title
            else:
                title = titleTypesUpper[type] + title
            updateProgressBar(figname, t)
            fig, ax = plt.subplots()
            ax.set_title(title, fontweight="bold")

            bottom = [0] * len(data[0]["reported"])

            for j, nation in enumerate(data):
                reportedData = data[j]["reported"]

                if perCapita[i]:
                    reportedData = [
                        x / nation["population"] * 100 for x in reportedData
                    ]
                    ax.plot(
                        data[j]["dates"],
                        reportedData,
                        color=nation["color"],
                        label=nation["name"],
                        linewidth=2,
                    )
                else:
                    ax.bar(
                        data[j]["dates"],
                        reportedData,
                        color=nation["color"],
                        label=nation["name"],
                        bottom=bottom,
                    )

                    bottom = list(map(add, reportedData, bottom))

            if not perCapita[i]:
                lockdownVlines(ax)

            dateAxis(ax)
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(reversed(handles), reversed(labels))

            if perCapita[i]:
                yLabel = "Percent of nation " + yLabelTypes[type]
            else:
                yLabel = "Reported " + titleTypesLower[type]

            setYLabel(ax, yLabel, avg)

            if perCapita[i]:
                percentAxis(ax)
            else:
                threeFigureAxis(ax)

            removeSpines(ax)
            showGrid(ax)

            savePlot(plotsDir, figname, fig)

        # Cumulative
        yLabels = ["UK population", "nation"]

        if not avg:
            for i in range(2):
                figname = fignameTypes[type] + "-Cumulative" + fignameSuffix[i]
                updateProgressBar(figname, t)
                fig, ax = plt.subplots()
                ax.set_title(
                    "Cumulative %s by date reported%s"
                    % (titleTypesLower[type], titleSuffix[i]),
                    fontweight="bold",
                )

                bottom = [0] * len(data[0]["reported"])

                for j, nation in enumerate(data):
                    reportedData = data[j]["reported"]
                    if perCapita[i]:
                        reportedData = [
                            x / nation["population"] * 100 for x in reportedData
                        ]
                    else:
                        reportedData = [x / totalPopulation * 100 for x in reportedData]
                    reportedData = np.cumsum(reportedData)

                    if perCapita[i]:
                        ax.plot(
                            data[j]["dates"],
                            reportedData,
                            color=nation["color"],
                            label=nation["name"],
                            linewidth=2,
                        )
                    else:
                        ax.bar(
                            data[j]["dates"],
                            reportedData,
                            color=nation["color"],
                            label=nation["name"],
                            bottom=bottom,
                        )

                        bottom = list(map(add, reportedData, bottom))

                dateAxis(ax)
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(reversed(handles), reversed(labels))

                percentAxis(ax)
                setYLabel(ax, "Percent of " + yLabels[i] + " " + yLabelTypes[type], avg)

                removeSpines(ax)
                showGrid(ax)

                savePlot(plotsDir, figname, fig)


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

        for fileName in fileNames:
            data.append(readData(fileName))

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

        figname = fignames[i] + "HeatMap"
        updateProgressBar(figname, t)
        fig, axs = plt.subplots(len(dataFrames), 1, sharex=True)

        for j, ax in enumerate(axs):
            plt.xticks(ticks=list(range(7)), labels=days)

            plotHeatmap(ax, names[i][j], dataFrames[j])

        fig.suptitle("Heatmap of number of %s per day" % titles[i], fontweight="bold")

        savePlot(plotsDir, figname, fig, (10, 5))

        # Nations
        nations = ["Scotland", "England", "Northern Ireland", "Wales"]
        colors = ["#003078", "#5694CA", "#FFDD00", "#D4351C"]
        nationsDf = []

        for nation in nations:
            nationDataFrame = getDataframes(nation, casesBoolean[i])

            nationsDf.append(nationDataFrame)

        figname = fignames[i] + "HeatMap-Nation"
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

        savePlot(plotsDir, figname, fig, (20, 10))


# Helpers ------------------------------------------------------------------------------
def updateProgressBar(figname, t):
    t.update()
    t.set_description(figname)


def savePlot(plotsDir, figname, fig, size=()):
    if size:
        plt.gcf().set_size_inches(*size)
    else:
        plt.gcf().set_size_inches(12, 8)
    plt.savefig(plotsDir + figname, bbox_inches="tight", pad_inches=0.25, dpi=200)
    # mpld3.save_json(fig, "d3/" + figname + ".json")
    plt.close(fig)


def removeSpines(ax, all=False):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if all:
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)


# Y axis
def showGrid(ax):
    ax.grid(color="#e5e5e5", which="major", axis="y", linestyle="solid")
    ax.set_axisbelow(True)


def percentAxis(ax):
    ax.set_ylim(bottom=0)
    ticks = ax.get_yticks()
    dataRange = max(ticks) - min(ticks)
    roundingDecimals = math.ceil(2.0 - math.log10(2.0 * dataRange))
    decimals = max(map(lambda x: decimalPlaces(x, roundingDecimals), ticks))
    ax.yaxis.set_major_formatter(tkr.PercentFormatter(decimals=decimals))


def threeFigureAxis(axis):
    axis.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))


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


def setYLabel(ax, label, avg, color="black"):
    if avg:
        ax.set_ylabel(label + " (seven day average)", color=color)
    else:
        ax.set_ylabel(label, color=color)


# X axis
def dateAxis(ax):
    ax.set_xlim(left=dt.strptime("2020-03-01", "%Y-%m-%d"), right=dt.today())
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(df("%d %b"))


def reduceXlabels(ax, every_nth=2):
    for n, label in enumerate(ax.xaxis.get_ticklabels()):
        if n % every_nth != 0:
            label.set_visible(False)


# Math
def n_day_avg(xs, n=7):
    """compute n day average of time series, using maximum possible number of days at
    start of series"""
    return [np.mean(xs[max(0, i + 1 - n) : i + 1]) for i in range(xs.shape[0])]


def n_day_sum(xs, n=28):
    """compute n day sum of time series, using maximum possible number of days at
    start of series"""
    return [np.sum(xs[max(0, i + 1 - n) : i + 1]) for i in range(xs.shape[0])]


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
        help="Directory where the csv files will be stored [default: data/]",
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
            total=42, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} {elapsed_s:.0f}s"
        )

        mainPlot(t, dataDir, plotsDir, avg=False)
        mainPlot(t, dataDir, plotsDir)

        nationReportedPlot(t, dataDir, plotsDir)
        nationReportedPlot(t, dataDir, plotsDir, avg=False)

        heatMapPlot(t, dataDir, plotsDir)

        t.close()
    else:
        print("No new data.")
