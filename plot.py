
import csv
from datetime import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.ticker as tkr

def plot():
    with open("cases.csv", "r") as file:
        reader = csv.reader(file, delimiter=",")
        casesData = [(line[3], int(line[4])) for line in reader]
        casesDict = dict(casesData)
        casesDates = [dt.strptime(x[0], "%Y-%m-%d") for x in casesData]
        cases = [x[1] for x in casesData]

    with open("tests.csv", "r") as file:
        reader = csv.reader(file, delimiter=",")
        testsData = [(line[3], int(line[8])) for line in reader]
        testRawDates = [x[0] for x in testsData]
        testDates = [dt.strptime(x[0], "%Y-%m-%d") for x in testsData]
        tests = [x[1] for x in testsData]

    for j, date in enumerate(testRawDates):
        if date in casesDict:
            tests[j] = casesDict[date] / tests[j] * 100
        else:
            tests[j] = 0

    figname = "COVID"
    plt.figure()
    _, ax = plt.subplots()

    ax.set_title("UK COVID-19 cases compared to percentage of positive tests")

    ax.bar(casesDates, cases)
    ax.set_ylabel("Daily COVID-19 Cases in the UK", color="C0")

    ax2 = ax.twinx()
    ax2.plot_date(testDates, tests, "white", linewidth=3)
    ax2.plot_date(testDates, tests, "orangered", linewidth=2)
    ax2.set_ylabel(
        "Daily COVID-19 Tests in the UK",
        color="orangered",
        rotation=270,
        ha="center",
        va="bottom",
    )

    ax.xaxis_date()
    ax.set_xlim(
        left=dt.strptime("2020-03-01", "%Y-%m-%d"),
        right=dt.strptime("2020-10-22", "%Y-%m-%d"),
    )
    ax.yaxis.set_major_formatter(tkr.FuncFormatter(threeFigureFormatter))

    ax2.yaxis.set_major_formatter(tkr.PercentFormatter(decimals=0))
    ax2.hlines(
        y=5,
        xmin=dt.strptime("2020-01-30", "%Y-%m-%d"),
        xmax=dt.strptime("2020-11-01", "%Y-%m-%d"),
        linestyles="dotted",
        color="black",
    )

    plt.gcf().set_size_inches(12, 7.5)
    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)

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
    plot()