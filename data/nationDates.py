import datetime as dt

nation1kDates = [
    [dt.strptime("2020-03-11", "%Y-%m-%d")],
    [
        dt.strptime("2020-03-25", "%Y-%m-%d"),
        dt.strptime("2020-03-11", "%Y-%m-%d"),
        dt.strptime("2020-04-03", "%Y-%m-%d"),
        dt.strptime("2020-03-26", "%Y-%m-%d"),
    ],
]
nationLockdownDates = [
    [
        [
            dt.strptime("2020-03-23", "%Y-%m-%d"),
            dt.strptime("2020-11-05", "%Y-%m-%d"),
        ]
    ],
    [
        [
            dt.strptime("2020-03-23", "%Y-%m-%d"),
            dt.strptime("2020-10-07", "%Y-%m-%d"),
        ],
        [
            dt.strptime("2020-03-23", "%Y-%m-%d"),
            dt.strptime("2020-10-23", "%Y-%m-%d"),
        ],
        [
            dt.strptime("2020-03-23", "%Y-%m-%d"),
            dt.strptime("2020-11-05", "%Y-%m-%d"),
        ],
        [
            dt.strptime("2020-03-23", "%Y-%m-%d"),
            dt.strptime("2020-10-16", "%Y-%m-%d"),
        ],
    ],
]
nationLockdownEasing = [
    [dt.strptime("2020-07-04", "%Y-%m-%d")],
    [
        dt.strptime("2020-07-15", "%Y-%m-%d"),
        dt.strptime("2020-08-03", "%Y-%m-%d"),
        dt.strptime("2020-07-04", "%Y-%m-%d"),
        dt.strptime("2020-09-23", "%Y-%m-%d"),
    ],
]