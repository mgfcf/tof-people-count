from datetime import datetime
import json
from typing import Dict
from xmlrpc.client import Boolean

import matplotlib.pyplot as plt

# Config
FILE_PATH = "log.txt"


# Read file
content = None
with open(FILE_PATH, "r") as file:
    content = file.readlines()


def parse_log_entry(entry: Dict) -> Dict:
    # Only keep last record of a sequence
    if not is_last_in_sequence(entry):
        return False

    entry["dateTime"] = datetime.strptime(
        str(entry["dateTime"])[:19], "%Y-%m-%d %H:%M:%S")
    if entry["dateTime"] < datetime(2022, 1, 1):
        return False

    return entry


def is_last_in_sequence(entry: Dict) -> Boolean:
    indoor = entry["directionState"]["indoor"]
    outdoor = entry["directionState"]["outdoor"]
    
    if len(indoor) <= 0 or len(outdoor) <= 0:
        return False
    
    end_key = "end_distance"
    # Check version
    if end_key not in indoor[-1]:
        end_key = "end"
    
    if indoor[-1][end_key] is None or outdoor[-1][end_key] is None:
        return False

    return True


# Collect
log = [json.loads(line.strip("\x00")) for line in content]
print("Number of total entries:", len(log))

# Parse & Filter
log = [parse_log_entry(entry) for entry in log if parse_log_entry(entry)]
print("Number of filtered entries:", len(log))

# Render
fig, ax = plt.subplots()  # Create a figure containing a single axes.
times: list[datetime] = [entry["dateTime"] for entry in log]
counts: list[int] = [entry["previousPeopleCount"] for entry in log]
ax.step(times, counts, where="pre")
plt.show()
print("-"*20)


# Print stats
walk_ins = [entry for entry in log if entry["countChange"] > 0]
walk_outs = [entry for entry in log if entry["countChange"] < 0]
walk_unders = [entry for entry in log if entry["countChange"] == 0]
print("Number of walk-ins:", len(walk_ins))
print("Number of walk-outs:", len(walk_outs))
print("Number of walk-unders:", len(walk_unders))
print("-"*20)

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
print("Percentage of faults:", fault_count / len(log) * 100, "%")

print("-"*20)
faulty_off = [entry for entry in log if entry["faulty"]
              and entry["faultyCount"] == 0]
faulty_on = [entry for entry in log if entry["faulty"]
             and entry["faultyCount"] != 0]
print("Number of false-0:", len(faulty_off))
print("Number of false-1:", len(faulty_on))
print("Percentage of false-0:", len(faulty_off) / fault_count * 100, "%")
print("Percentage of false-1:", len(faulty_on) / fault_count * 100, "%")
