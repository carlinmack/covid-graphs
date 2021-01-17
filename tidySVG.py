import re

def tidySVG(filename):
    with open(filename, "r") as r:
        contents = r.readlines()

    for i, line in enumerate(contents):
        if re.match(r"^<svg", line):
            withoutH = re.sub(r"^(<svg.*?)height=.*? (.*$)", r"\1\2", line)
            withoutW = re.sub(r"^(<svg.*?)width=.*? (.*$)", r"\1\2", withoutH)
            contents[i] = withoutW
            break

    
    with open(filename, "w") as w:
        w.writelines(contents)
            