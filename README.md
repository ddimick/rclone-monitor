## Rclone Monitor

### What
Recursively monitors a directory for new files and moves them to cloud storage via Rclone.

### Why
Accessing cloud storage is very slow compared to local storage. Automation tools like Sonarr do not deal well with slow storage while importing and can be rendered unusable until the import completes. A better method is to stage the files locally and move them to cloud storage using an external tool. This is that external tool.

### Requirements
A working Rclone installation and Python 3+ with the watchdog module installed.

### Installation
Download or clone this repo.
Make `rclone-monitor.py` accessible somewhere in your `PATH`, like `/usr/local/bin/rclone-monitor.py`.
Run `pip install -r requirements.txt`

If you use SystemD, there is an example unit file included. Edit `rclone-monitor.service` to suite your needs, then copy to `/etc/systemd/system/rclone-monitor.service`. Run `systemctl daemon-reload` and `systemctl start rclone-monitor.service`. You can monitor output by running `journalctl -f -u rclone-monitor.service`. Once you are satisfied it's working, run `systemctl enable rclone-monitor.service` so that it starts upon bootup.

#### Usage
```
usage: rclone-monitor.py [-h] [-e EXECUTABLE] [-f RCLONE_FLAG] [-l LOGLEVEL] [-p POLLING] [-s] [--debug] src dst

Monitor staging directory and move files to rclone backend

positional arguments:
  src                   Source directory to monitor for new files (i.e. /mnt/staging)
  dst                   Rclone target location (i.e. gdrive:/)

optional arguments:
  -h, --help            show this help message and exit
  -e EXECUTABLE, --executable EXECUTABLE
                        Rclone executable (default: "rclone" in PATH)
  -f RCLONE_FLAG, --rclone-flag RCLONE_FLAG
                        Append global flag to Rclone command (see
                        https://rclone.org/flags/) (list of flags always set:
                        ['progress', 'stats=10s', 'no-traverse', 'user-
                        agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)
                        AppleWebKit/537.36 (KHTML, like Gecko)
                        Chrome/74.0.3729.131 Safari/537.36"'])
  -l LOGLEVEL, --loglevel LOGLEVEL
                        Logging output level (valid options are "DEBUG",
                        "INFO", "WARNING", "ERROR", and "CRITICAL") (default:
                        INFO)
  -p POLLING, --polling POLLING
                        Seconds to wait for more data to be written to file
                        before proceeding with Rclone move (default: 60)
  -s, --scan-existing   Scan for existing files upon startup
  --debug               Show debugging output
```

### Example
```
$ rclone-monitor.py --loglevel=info -s -f=bwlimit=2M /mnt/tank0/test gdrive:/test
INFO:root:Connected to backend "gdrive:/test"
INFO:root:Scanning "/mnt/tank0/test" for existing files
INFO:root:Scan of "/mnt/tank0/test" completed
INFO:root:Started monitoring "/mnt/tank0/test"
INFO:root:File check polling timer: 10 seconds
INFO:root:Detected:   "/mnt/tank0/test/testdir/testfile"
INFO:root:Monitoring: "/mnt/tank0/test/testdir/testfile"
INFO:root:Moving:     "/mnt/tank0/test/testdir/testfile" to "gdrive:/test/testdir/"
INFO:root:Status:     15.684M / 100 MBytes completed (16%) at 1.646 MBytes/s ETA 51s
INFO:root:Status:     22.027M / 100 MBytes completed (22%) at 1.516 MBytes/s ETA 51s
INFO:root:Status:     29.184M / 100 MBytes completed (29%) at 1.495 MBytes/s ETA 47s
INFO:root:Status:     36.309M / 100 MBytes completed (36%) at 1.480 MBytes/s ETA 43s
INFO:root:Status:     42.496M / 100 MBytes completed (42%) at 1.439 MBytes/s ETA 39s
INFO:root:Status:     50.496M / 100 MBytes completed (50%) at 1.463 MBytes/s ETA 33s
INFO:root:Status:     58.496M / 100 MBytes completed (58%) at 1.480 MBytes/s ETA 28s
INFO:root:Status:     66.496M / 100 MBytes completed (66%) at 1.493 MBytes/s ETA 22s
INFO:root:Status:     74.496M / 100 MBytes completed (74%) at 1.504 MBytes/s ETA 16s
INFO:root:Status:     82.496M / 100 MBytes completed (82%) at 1.513 MBytes/s ETA 11s
INFO:root:Status:     88M / 100 MBytes completed (88%) at 1.478 MBytes/s ETA 8s
INFO:root:Status:     96M / 100 MBytes completed (96%) at 1.488 MBytes/s ETA 2s
INFO:root:Status:     100M / 100 MBytes completed (100%) at 1.438 MBytes/s ETA 0s
INFO:root:Status:     100M / 100 MBytes completed (100%) at 1.435 MBytes/s ETA 0s
INFO:root:Finished:   "/mnt/tank0/test/testdir/testfile" moved to "gdrive:/test/testdir/" in 0 hours, 1 minutes, and 12 seconds (11.51mbps)
INFO:root:Cleaning up empty directories in "/mnt/tank0/test"
INFO:root:Cleaning up empty directories in "/mnt/tank0/test/testdir"
INFO:root:Removing directory "/mnt/tank0/test/testdir"
```