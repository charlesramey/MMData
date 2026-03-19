import glob
from datetime import datetime, timezone, timedelta

edt = timezone(timedelta(hours=-4))
csvs = sorted(glob.glob("720sync/*Aframe*/*_cleaned.csv"))

for path in csvs:
    folder = path.split("/")[1]
    with open(path) as f:
        lines = f.readlines()
    first_ts = float(lines[1].split(",")[0])
    last_line = lines[-1].strip() if lines[-1].strip() else lines[-2].strip()
    last_ts = float(last_line.split(",")[0])
    dt = datetime.fromtimestamp(first_ts, tz=edt)
    dur = last_ts - first_ts
    print("{:25s} {:.6f}  {}  {:.2f}s".format(folder, first_ts, dt.strftime('%Y-%m-%d %H:%M:%S.%f'), dur))
