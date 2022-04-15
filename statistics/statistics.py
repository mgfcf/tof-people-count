from datetime import datetime
import json
from typing import Dict

import matplotlib.pyplot as plt

# Config
FILE_PATH = "log.txt"


# Read file
content = None
with open(FILE_PATH, "r") as file:
    content = file.readlines()


def parse_log_entry(entry: Dict) -> Dict:
    if entry["countChange"] == 0:
        return False

    entry["dateTime"] = datetime.strptime(
        str(entry["dateTime"])[:19], "%Y-%m-%d %H:%M:%S")
    if entry["dateTime"] < datetime(2022, 1, 1):
        return False

    return entry


# Collect
log = [json.loads(line.strip("\x00")) for line in content]
print("Number of entries:", len(log))

# Parse & Filter
log = [parse_log_entry(entry) for entry in log if parse_log_entry(entry)]
print("Number of counts:", len(log))

# Render
fig, ax = plt.subplots()  # Create a figure containing a single axes.
times: list[datetime] = [entry["dateTime"] for entry in log]
counts: list[int] = [entry["previousPeopleCount"] for entry in log]
ax.step(times, counts, where="pre")
plt.show()

# Calculate faults
for c, n in zip(list(range(len(log))), list(range(len(log)))[1:]):
    estimated_count: int = log[c]["previousPeopleCount"] + \
        log[c]["countChange"]
    faulty: bool = estimated_count != log[n]["previousPeopleCount"]
    log[c]["faulty"] = faulty
    log[c]["faultyCount"] = log[c]["previousPeopleCount"] if faulty else None

log = log[:-1]
fault_count = sum(1 for entry in log if entry["faulty"])
print("Number of faults:", fault_count)
print("Percentage of faults:", fault_count / len(log) * 100)

print("-"*20)
faulty_off = [entry for entry in log if entry["faulty"]
              and entry["faultyCount"] == 0]
faulty_on = [entry for entry in log if entry["faulty"]
             and entry["faultyCount"] != 0]
print("Number of false-0:", len(faulty_off))
print("Number of false-1:", len(faulty_on))
print("Percentage of false-0:", len(faulty_off) / fault_count * 100)
print("Percentage of false-1:", len(faulty_on) / fault_count * 100)
