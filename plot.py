import argparse
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
from matplotlib.dates import MonthLocator
from tqdm import tqdm

from getData import getData
from readData import readData
from processData import processData


def mainPlot(t, dataDir="data/", plotsDir="plots/", avg=True):
    """avg indicates seven day average of new cases should be used"""
    nationList = [["UK"], ["Scotland", "England", "Northern Ireland", "Wales"]]
    colorsList = [["#2271d3"], ["#003078", "#5694CA", "#FFDD00", "#D4351C"]]
    fignames = ["", "-Nation"]

    for outerI, nations in enumerate(nationList):
        data = {}
        for nation in nations:
            if avg:
                data[nation] = pd.read_csv(
                    dataDir + nation + ".avg.csv", index_col=0, parse_dates=True
                )
            else:
                data[nation] = pd.read_csv(
                    dataDir + nation + ".csv", index_col=0, parse_dates=True
                )

        testingPlot(fignames, outerI, avg, t, data, nations, plotsDir)

        percentPositivePlot(
            t, plotsDir, avg, colorsList, fignames, outerI, nations, data
        )

        doubleBarChartPlot(t, plotsDir, avg, fignames, outerI, nations, data)

        mortalityHospitalisationPlot(
            fignames, outerI, avg, t, data, colorsList, nations, plotsDir
        )

        if outerI == 0:
            ComparisonUK(plotsDir, avg, t, data)
        else:
            ComparisonNation(plotsDir, avg, t, data, nations)


def readFile(name, avg):
    data = readData(name)
    # convert to np array and separate dates from case counts
    casesData = np.array(data)
    casesRawDates = casesData[:, 0]
    casesDates = [dt.strptime(x, "%Y-%m-%d") for x in casesRawDates]
    cases = casesData[:, 1].astype(np.float)

    # compute seven day average of cases if enabled
    if avg:
        cases = n_day_avg(cases, 7)

    return cases, casesDates


def testingPlot(fignames, outerI, avg, t, data, nations, plotsDir):
    figname = "Testing" + fignames[outerI]
    title = "Positive test rate of COVID-19 in the UK"
    if avg:
        figname += "-Avg"
        title = "Average positive test rate of COVID-19 in the UK"
    updateProgressBar(figname, t)

    if outerI == 0:
        fig, ax = plt.subplots()

        ax.set_title(title, fontweight="bold")

        ax.plot(data["UK"].index, data["UK"]["posTests"], color="#333")

        maxArray = [x >= 5 for x in data["UK"]["posTests"]]
        minArray = [x <= 5 for x in data["UK"]["posTests"]]

        ax.fill_between(
            data["UK"].index,
            5,
            data["UK"]["posTests"].fillna(0),
            where=maxArray,
            facecolor="#FF41367F",
            interpolate=True,
        )
        ax.fill_between(
            data["UK"].index,
            5,
            data["UK"]["posTests"].fillna(0),
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

            ax.plot(data[nation].index, data[nation]["posTests"], color="#333")

            maxArray = [x >= 5 for x in data[nation]["posTests"]]
            minArray = [x <= 5 for x in data[nation]["posTests"]]
            ax.fill_between(
                data[nation].index,
                5,
                data[nation]["posTests"].fillna(0),
                where=maxArray,
                facecolor="#FF41367F",
                interpolate=True,
            )
            ax.fill_between(
                data[nation].index,
                5,
                data[nation]["posTests"].fillna(0),
                where=minArray,
                facecolor="#3D99707F",
                interpolate=True,
            )

            dateAxis(ax)
            reduceXlabels(ax)
            reduceYlabels(ax)

            setYLabel(ax, "% positive tests per day", avg)
            showGrid(ax)
            percentAxis(ax)

            ax.set_title(nations[j])
            removeSpines(ax)

    savePlot(plotsDir, figname, fig)


def percentPositivePlot(t, plotsDir, avg, colorsList, fignames, outerI, nations, data):
    fig, ax = plt.subplots()
    figname = "PercentPositive" + fignames[outerI]
    if outerI == 0:
        title = "UK COVID-19 cases compared to percentage of tests which are positive"
        if avg:
            title = "Average " + title
    elif outerI == 1 and avg:
        title = (
            "Average percentage of tests which are positive for COVID-19 in UK nations"
        )
    else:
        title = "Percentage of tests which are positive for COVID-19 in UK nations"
    if avg:
        figname += "-Avg"
    updateProgressBar(figname, t)
    ax.set_title(title, fontweight="bold")
    if outerI == 0:
        ax.bar(data["UK"].index, data["UK"]["reportedCases"], color="orangered")
        setYLabel(ax, "Daily COVID-19 Cases in the UK", avg, color="orangered")
        ax2 = ax.twinx()
        ax2.plot_date(data["UK"].index, data["UK"]["posTests"], "white", linewidth=3)
        ax2.plot_date(
            data["UK"].index, data["UK"]["posTests"], "#333", linewidth=2,
        )
        setYLabel(ax2, "Percent positive tests per day", avg, ax2=True)
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
                data[nation].index,
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
        showGrid(ax)
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


def doubleBarChartPlot(t, plotsDir, avg, fignames, outerI, nations, data):
    figname = "DoubleBarChart" + fignames[outerI]
    title = "Number of tests vs positive tests"
    if avg:
        figname += "-Avg"
        title += " (averaged)"
    updateProgressBar(figname, t)
    if outerI == 0:
        fig, ax = plt.subplots()
        ax.set_title(title, fontweight="bold")
        fivePercent = [x * 0.05 for x in data["UK"]["reportedTests"]]
        ax.bar(
            data["UK"].index,
            data["UK"]["reportedTests"],
            color="#2271d3",
            label="Total tests",
        )
        ax.bar(
            data["UK"].index,
            fivePercent,
            color="black",
            label="WHO 5% reopening threshold",
        )
        ax.bar(
            data["UK"].index,
            data["UK"]["reportedCases"],
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
            tests = data[nation]["reportedTests"]
            fivePercent = [x * 0.05 for x in tests]
            ax.bar(
                data[nation].index, tests, color="#2271d3", label="Total tests",
            )
            ax.bar(
                data[nation].index,
                fivePercent,
                color="black",
                label="WHO 5% reopening threshold",
            )
            ax.bar(
                data[nation].index,
                data[nation]["reportedCases"],
                color="orangered",
                label="Positive tests",
            )
            dateAxis(ax)
            reduceXlabels(ax)
            reduceYlabels(ax)
            setYLabel(ax, "Number of tests per day", avg)
            ax.set_title(nations[j])
            threeFigureAxis(ax)
            removeSpines(ax)
            showGrid(ax)
    savePlot(plotsDir, figname, fig)


def mortalityHospitalisationPlot(
    fignames, outerI, avg, t, data, colorsList, nations, plotsDir
):
    innerFignames = ["Mortality", "Hospitalisation"]
    innerTitles = ["Mortality", "Hospitalisation rate"]
    innerYs = ["deathDates", "hospitalisationDates"]
    innerXs = ["mortality", "hospitalisationRate"]
    innerYlables = ["mortality", "hospitalisation rate"]
    innerNotes = [
        "Mortality is calculated as deaths",
        "Hospitalisation rate is calculated as hospitalisations",
    ]
    innerColors = ["black", "#851bc2"]

    for innerI in range(len(innerFignames)):
        figname = innerFignames[innerI] + fignames[outerI]
        if avg:
            figname += "-Avg"
        updateProgressBar(figname, t)
        fig, ax = plt.subplots()

        if outerI == 0:
            title = "%s of COVID-19 in the UK" % innerTitles[innerI]

            ax.bar(data["UK"].index, data["UK"]["reportedCases"], color="orangered")
            setYLabel(ax, "Daily COVID-19 Cases in the UK", avg, color="orangered")

            ax2 = ax.twinx()

            ax2.plot_date(
                data["UK"].index, data["UK"][innerXs[innerI]], "white", linewidth=3,
            )
            ax2.plot_date(
                data["UK"].index,
                data["UK"][innerXs[innerI]],
                innerColors[innerI],
                linewidth=2,
            )

            yLabel = "Percent %s per day" % innerYlables[innerI]
            setYLabel(ax2, yLabel, avg, color=innerColors[innerI], ax2=True)

            ax.spines["top"].set_visible(False)
            ax2.spines["top"].set_visible(False)

            threeFigureAxis(ax)
            percentAxis(ax2)
        elif outerI == 1:
            title = "%s of COVID-19 in UK nations" % innerTitles[innerI]

            for i, nation in enumerate(data):
                nationDeaths = data[nation][innerXs[innerI]]
                ax.plot_date(
                    data[nation].index,
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
        data["UK"].index,
        data["UK"]["reportedCases"],
        "orangered",
        ls="-",
        label="Cases",
    )
    (p2,) = ax2.plot(
        data["UK"].index,
        data["UK"]["hospitalisations"],
        "#851bc2",
        ls="-",
        label="Hospitalisations",
    )
    (p3,) = ax3.plot(
        data["UK"].index, data["UK"]["specimenDeaths"], "#333", ls="-", label="Deaths",
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

            cases = data[nation]["reportedCases"]
            hospitalisations = data[nation]["hospitalisations"]
            deaths = data[nation]["specimenDeaths"]

            if perCapita[i]:
                cases = [x / populations[j] * 100 for x in cases]
                hospitalisations = [x / populations[j] * 100 for x in hospitalisations]
                deaths = [x / populations[j] * 100 for x in deaths]

            (p1,) = ax.plot(data[nation].index, cases, "orangered", ls="-")
            (p2,) = ax2.plot(data[nation].index, hospitalisations, "#851bc2", ls="-",)
            ax3.plot(data[nation].index, deaths, "#333", ls="-")

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
                axis.yaxis.set_major_locator(plt.MaxNLocator(3))

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
                axis.set_ylim(top=axMax[0])

            for axis in secondary_ax:
                axis.set_ylim(top=axMax[1])

            for axis in tertiary_ax:
                axis.set_ylim(top=axMax[2])

        plt.annotate(
            "Note: Wales includes suspected COVID-19 patients in hospitalisation figures while the other nations include only confirmed cases.",
            xy=(0.25, 0.025),
            xycoords="figure fraction",
            color="#666",
        )

        savePlot(plotsDir, figname, fig, size=(24, 12))


def lockdownVlines(ax, outerI=0):
    nationLockdownDates = [
        [dt(2020, 3, 23), dt(2020, 11, 5), dt(2020, 12, 20)],
    ]
    nationLockdownEasing = [
        [dt(2020, 7, 4), dt(2020, 12, 2)],
    ]

    ymin, ymax = ax.get_ylim()
    ax.vlines(
        x=nationLockdownEasing[outerI],
        ymin=ymin,
        ymax=ymax,
        color="#3D9970AF",
        ls="dashed",
        label="End of lockdown",
    )

    ax.vlines(
        x=nationLockdownDates[outerI],
        ymin=ymin,
        ymax=ymax,
        color="#FF4136AF",
        ls="dashed",
        label="Start of lockdown",
    )

    ax.vlines(
        x=dt(2020, 3, 11),
        ymin=ymin,
        ymax=ymax,
        color="#333",
        ls="dashed",
        label="WHO declares pandemic",
    )


def nationPlot(t, dataDir="data/", plotsDir="plots/", avg=True):
    data = [
        {"name": "England", "color": "#5694CA", "population": 56286961},
        {"name": "Northern Ireland", "color": "#FFDD00", "population": 1893667},
        {"name": "Scotland", "color": "#003078", "population": 5463300},
        {"name": "Wales", "color": "#D4351C", "population": 3152879},
    ]

    totalPopulation = sum([x["population"] for x in data])

    types = [
        {
            "fileName": ".cases.reported",
            "figname": "Nation-Cases-Reported",
            "title": "COVID-19 cases by date reported",
            "yLabel": "tested positive",
        },
        {
            "fileName": ".deaths.reported",
            "figname": "Nation-Deaths-Reported",
            "title": "Deaths within 4 weeks of a positive COVID-19 test by date reported",
            "yLabel": "who have died within 28 days of a positive test",
        },
        {
            "fileName": ".cases",
            "figname": "Nation-Cases",
            "title": "COVID-19 cases in UK Nations",
            "yLabel": "tested positive",
        },
        {
            "fileName": ".deaths",
            "figname": "Nation-Deaths",
            "title": "Deaths within 4 weeks of a positive COVID-19 test",
            "yLabel": "who have died within 28 days of a positive test",
        },
        {
            "fileName": ".inVentilationBeds",
            "figname": "Nation-Ventilation",
            "title": "COVID-19 patients in mechanical ventilation beds by nation",
            "yLabel": "who are in mechanical ventilation beds",
        },
        {
            "fileName": ".vaccinations",
            "figname": "Nation-Vaccinations",
            "title": "COVID-19 vaccinations by nation",
            "yLabel": "who have received vaccinations",
        },
    ]

    iterations = len(types)
    if avg:
        iterations = len(types) - 1

    for figType in range(iterations):
        series = []
        for i, nation in enumerate(data):
            fileName = dataDir + nation["name"] + types[figType]["fileName"] + ".csv"

            if figType == 2 or figType == 3:
                nationData = readData(fileName, type="dict", skip=5)
            else:
                nationData = readData(fileName, type="dict")

            nationSeries = pd.Series(nationData, name=nation["name"])

            if avg:
                nationAvgSeries = pd.Series(
                    n_day_avg(nationSeries),
                    index=nationSeries.index,
                    name=nation["name"],
                )
                series.append(nationAvgSeries)
            else:
                series.append(nationSeries)

        df = pd.concat(series, axis=1)
        dates = df.index

        fignameSuffix = ["", "-Per-Capita"]
        titleSuffix = ["", ", per capita"]
        perCapita = [0, 1]

        barWidth = 1
        alignment = "center"
        if figType == len(types) - 1:
            barWidth = -5.6
            alignment = "edge"

        for i in range(len(fignameSuffix)):
            figname = types[figType]["figname"] + fignameSuffix[i]
            if avg:
                figname += "-Avg"
                title = "Average " + types[figType]["title"] + titleSuffix[i]
            else:
                title = types[figType]["title"] + titleSuffix[i]
            updateProgressBar(figname, t)
            fig, ax = plt.subplots()
            ax.set_title(title, fontweight="bold")

            bottom = [0] * len(df.index)

            for nation in data:
                plotData = df[nation["name"]]

                if perCapita[i]:
                    plotData = [x / nation["population"] * 100 for x in plotData]
                    ax.plot(
                        dates,
                        plotData,
                        color=nation["color"],
                        label=nation["name"],
                        linewidth=2,
                    )
                else:
                    ax.bar(
                        dates,
                        plotData,
                        color=nation["color"],
                        label=nation["name"],
                        bottom=bottom,
                        width=barWidth,
                        align=alignment,
                    )
                    bottom = list(map(add, plotData.fillna(0), bottom))

            if not perCapita[i]:
                lockdownVlines(ax)

            dateAxis(ax)
            if figType == len(types) - 1:
                dateAxis(ax, left=dt(2020, 12, 1), right=dt(2021, 1, 1))
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(reversed(handles), reversed(labels))

            if perCapita[i]:
                yLabel = "Percent of nation " + types[figType]["yLabel"]
            else:
                yLabel = types[figType]["title"]

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
            for i in range(len(yLabels)):
                figname = types[figType]["figname"] + "-Cumulative" + fignameSuffix[i]
                updateProgressBar(figname, t)
                fig, ax = plt.subplots()
                ax.set_title(
                    "Cumulative %s%s" % (types[figType]["title"], titleSuffix[i]),
                    fontweight="bold",
                )

                bottom = [0] * len(df.index)

                for nation in data:
                    reportedData = df[nation["name"]].fillna(0)
                    if perCapita[i]:
                        reportedData = [
                            x / nation["population"] * 100 for x in reportedData
                        ]
                    else:
                        reportedData = [x / totalPopulation * 100 for x in reportedData]
                    reportedData = np.cumsum(reportedData)

                    if perCapita[i]:
                        ax.plot(
                            dates,
                            reportedData,
                            color=nation["color"],
                            label=nation["name"],
                            linewidth=2,
                        )
                    else:
                        ax.bar(
                            dates,
                            reportedData,
                            color=nation["color"],
                            label=nation["name"],
                            bottom=bottom,
                            width=barWidth,
                            align=alignment,
                        )

                        bottom = list(map(add, reportedData, bottom))

                dateAxis(ax)
                if figType == len(types) - 1:
                    dateAxis(ax, left=dt(2020, 12, 1), right=dt(2021, 1, 1))
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(reversed(handles), reversed(labels))

                percentAxis(ax)
                setYLabel(
                    ax, "Percent of " + yLabels[i] + " " + types[figType]["yLabel"], avg
                )

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
                dataDir + name + ".testing.reported.csv",
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

    def plotHeatmap(ax, name, dataFrames, color, hide=0):
        if hide == 0:
            ax.set_ylabel(name, rotation=0, ha="right", va="center")

        ax.bar(range(7), dataFrames["Number"], color=color)
        ax.yaxis.set_major_locator(plt.MaxNLocator(2))
        threeFigureAxis(ax)

        removeSpines(ax, all=True)
        showGrid(ax, color="#bbb")

    casesBoolean = [1, 0]
    fignames = ["Tests-Cases", "Deaths"]
    titles = ["tests and cases", "deaths"]

    names = [
        ["Tests", "Cases (reported date)", "Cases (specimen date)"],
        ["Deaths", "Reported Deaths"],
    ]

    colors = [["#2271d3", "orangered", "orangered"], ["#333", "#333", "#333"]]

    for i in range(2):
        title = "Comparison of average number of %s per day" % titles[i]

        # UK
        dataFrames = getDataframes("UK", casesBoolean[i])

        figname = "HeatMap-" + fignames[i]
        updateProgressBar(figname, t)
        fig, axs = plt.subplots(len(dataFrames), 1, sharex=True)

        for j, ax in enumerate(axs):
            plt.xticks(ticks=list(range(7)), labels=days)

            plotHeatmap(ax, names[i][j], dataFrames[j], colors[i][j])

        fig.suptitle(title, fontweight="bold")

        savePlot(plotsDir, figname, fig)

        # Nations
        figname = "HeatMap-" + fignames[i] + "-Nation"
        updateProgressBar(figname, t)

        nations = ["Scotland", "England", "Northern Ireland", "Wales"]
        nationsDf = []

        for nation in nations:
            nationDataFrame = getDataframes(nation, casesBoolean[i])

            nationsDf.append(nationDataFrame)

        fig = plt.figure()
        outerAxs = gridspec.GridSpec(2, 2, hspace=0.3)

        fig.suptitle(title + ", per nation", fontweight="bold")

        for k in range(len(nationsDf)):
            inner = outerAxs[k].subgridspec(len(nationsDf[0]), 1, hspace=0.3)

            axsRows = len(nationsDf[0])

            for j in range(axsRows):
                ax = fig.add_subplot(inner[j])
                if j == 0:
                    ax.set_title(nations[k])
                    ax.tick_params(
                        axis="x", which="both", bottom=False, labelbottom=False
                    )
                elif j == axsRows - 1 and k > 1:
                    plt.xticks(ticks=list(range(7)), labels=days)
                else:
                    ax.tick_params(
                        axis="x", which="both", bottom=False, labelbottom=False
                    )

                plotHeatmap(ax, names[i][j], nationsDf[k][j], colors[i][j], hide=k % 2)
                fig.add_subplot(ax)

        savePlot(plotsDir, figname, fig, (17.5, 10))


def timelinePlot(t, dataDir="data/", plotsDir="plots/"):
    """mask mandate
    NI [dt(2020, 9, 22), ?],"""
    data = [
        {
            "name": "Scotland",
            "color": "#003078",
            "Cases": [[None],],
            "Deaths": [[None],],
            "Lockdown": [
                [dt(2020, 3, 23), dt(2020, 6, 29),],
                [dt(2020, 12, 26), dt(2021, 1, 16)],
            ],
            "Tiered system": [[dt(2020, 11, 2), None],],
            "Closed pubs": [
                [dt(2020, 3, 20), dt(2020, 7, 15),],
                [dt(2020, 10, 9), None],
            ],
        },
        {
            "name": "England",
            "color": "#5694CA",
            "Cases": [[None],],
            "Deaths": [[None],],
            "Lockdown": [
                [dt(2020, 3, 23), dt(2020, 7, 4),],
                [dt(2020, 11, 5), dt(2020, 12, 2),],
                [dt(2020, 12, 26), None,],
            ],
            "Tiered system": [[dt(2020, 10, 14), None],],
            "Closed pubs": [
                [dt(2020, 3, 23), dt(2020, 7, 4),],
                [dt(2020, 11, 5), dt(2020, 12, 2),],
                [dt(2020, 12, 26), None,],
            ],
        },
        {
            "name": "Northern Ireland",
            "color": "#FFDD00",
            "Cases": [[None],],
            "Deaths": [[None],],
            "Lockdown": [
                [dt(2020, 3, 23), dt(2020, 7, 3),],
                [dt(2020, 11, 27), dt(2020, 12, 11),],
                [dt(2020, 12, 26), dt(2021, 2, 6),],
            ],
            "Tiered system": [[None],],
            "Closed pubs": [
                [dt(2020, 3, 15), dt(2020, 9, 23),],
                [dt(2020, 10, 16), None],
            ],
        },
        {
            "name": "Wales",
            "color": "#D4351C",
            "Cases": [[None],],
            "Deaths": [[None],],
            "Lockdown": [
                [dt(2020, 3, 23), dt(2020, 7, 13),],
                [dt(2020, 10, 23), dt(2020, 11, 9)],
                [dt(2020, 12, 20), None],
            ],
            "Tiered system": [[None],],
            "Closed pubs": [
                [dt(2020, 3, 23), dt(2020, 8, 3)],
                [dt(2020, 10, 23), dt(2020, 11, 9)],
                [dt(2020, 12, 4), None],
            ],
        },
    ]

    title = "Timeline of COVID-19 restrictions in the UK"

    figname = "Timeline"
    updateProgressBar(figname, t)
    fig, axs = plt.subplots(len(data), 1, constrained_layout=True)

    for j, ax in enumerate(axs):
        ax.set_title(data[j]["name"])
        ax.set_yticks([0])
        keys = ["Closed pubs", "Tiered system", "Lockdown", "Deaths", "Cases"]

        for i, key in enumerate(keys):
            for dates in data[j][key]:
                if dates[0] == None:
                    ax.barh(
                        y=i,
                        width=dt(2022, 1, 2) - dt(2022, 1, 1),
                        left=dt(2018, 1, 1),
                        alpha=0,
                    )
                elif dates[1] == None:
                    ax.barh(
                        y=i,
                        width=dt(2022, 1, 1) - dates[0],
                        left=dates[0],
                        color=data[j]["color"],
                        hatch="//",
                        alpha=0.75,
                    )
                else:
                    ax.barh(
                        y=i,
                        width=dates[1] - dates[0],
                        left=dates[0],
                        color=data[j]["color"],
                    )
        ax.set_yticks(range(len(keys)))
        ax.set_yticklabels(keys)

        cases, casesDates = readFile(dataDir + data[j]["name"] + ".cases.csv", True)
        ax2 = ax.twinx()
        ax2.plot_date(casesDates[:-5], cases[:-5], "orangered")
        ymin, ymax = ax2.get_ylim()
        yRange = ymax - ymin
        ymin = ymin - (5 * yRange)
        ymax = ymax + (0.25 * yRange)
        ax2.set_ylim(bottom=ymin, top=ymax)
        ax2.axes.yaxis.set_visible(False)

        deaths, deathDates = readFile(dataDir + data[j]["name"] + ".deaths.csv", True)
        ax3 = ax.twinx()
        ax3.plot_date(deathDates[:-5], deaths[:-5], "#333")
        ymin, ymax = ax3.get_ylim()
        yRange = ymax - ymin
        ymin = ymin - (3.75 * yRange)
        ymax = ymax + (1.5 * yRange)
        ax3.set_ylim(bottom=ymin, top=ymax)
        ax3.axes.yaxis.set_visible(False)

        dateAxis(ax, year=True)

        removeSpines(ax)
        removeSpines(ax2)
        removeSpines(ax3)

        if j == 3:
            ax.set_xlabel(
                """
                Note: Hatching displays when there is no end date specified""",
                color="#666",
            )

    fig.suptitle(title, fontweight="bold")

    savePlot(plotsDir, figname, fig, size=(10, 16))


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
def showGrid(ax, color="#e5e5e5"):
    ax.grid(color=color, which="major", axis="y", linestyle="solid")
    ax.spines["left"].set_visible(False)
    ax.set_axisbelow(True)


def percentAxis(ax):
    ax.set_ylim(bottom=0)
    ticks = ax.get_yticks()
    dataRange = max(ticks) - min(ticks)
    roundingDecimals = math.ceil(2.0 - math.log10(2.0 * dataRange))
    decimals = max(map(lambda x: decimalPlaces(x, roundingDecimals), ticks))
    ax.yaxis.set_major_formatter(tkr.PercentFormatter(decimals=decimals))


def threeFigureAxis(ax):
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))


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


def setYLabel(ax, label, avg, color="black", ax2=False):
    if avg:
        label += " (seven day average)"

    if ax2:
        ax.set_ylabel(label, rotation=270, ha="center", va="bottom", color=color)
    else:
        ax.set_ylabel(label, color=color)


# X axis
def dateAxis(ax, year=False, left=dt(2020, 3, 1), right=dt.today()):
    ax.set_xlim(left=left, right=right)
    if year:
        ax.set_xlim(left=left, right=dt(2021, 3, 1))

    ax.xaxis.set_major_locator(MonthLocator())
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(df("%d %b"))


def reduceXlabels(ax, every_nth=3):
    for n, label in enumerate(ax.xaxis.get_ticklabels()):
        if n % every_nth != 0:
            label.set_visible(False)


def reduceYlabels(ax, max=6):
    ax.yaxis.set_major_locator(plt.MaxNLocator(max))


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
        processData()

        t = tqdm(
            total=65, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} {elapsed_s:.0f}s"
        )

        bools = [False, True]
        for bool in bools:
            mainPlot(t, dataDir, plotsDir, avg=bool)
            nationPlot(t, dataDir, plotsDir, avg=bool)

        heatMapPlot(t, dataDir, plotsDir)
        timelinePlot(t, dataDir, plotsDir)

        t.close()
    else:
        print("No new data.")
