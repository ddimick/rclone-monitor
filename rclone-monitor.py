#!/usr/bin/env python3

import os
import sys
import time
import argparse
import logging
import datetime
from glob import glob
from subprocess import Popen, PIPE
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler


def now():
  return datetime.datetime.fromtimestamp(time.time())


def scan_existing(path):
  logging.info('Scanning "%s" for existing files' % path)

  # Returns a recursive list of files.
  files = [y for x in os.walk(path) for y in glob(os.path.join(x[0], '*'))]

  for f in files:
    if os.path.isfile(f):
      logging.info('Detected:   "%s"' % f)

      if(monitor_file(f)):
        move_file(f)

  logging.info('Scan of "%s" completed' % path)

  return None


def rclone(cmd):
  flags = []
  for f in args.rclone_flag:
    flags.append('--' + f)

  cmd = [args.executable] + cmd + flags
  logging.debug(cmd)

  try:
    with Popen(cmd, stdout=PIPE, stderr=PIPE, bufsize=1, universal_newlines=True) as process:

      # It's ugly, but it works. Easily broken if Rclone changes their progress output.
      for line in process.stdout:
        if line.strip().startswith('*'):
          line = line.split(':')
          line = line[2].split(',')
          logging.info('Status:     "%s": %s completed (%s) at %s %s' % (cmd[2], line[0].strip(), line[1].strip(), line[2].strip(), line[3].strip()))

      for line in process.stderr:
        logging.error(line)

  except OSError as e:
    sys.exit(logging.error(e))

  return process


def on_created(event):
  if os.path.isfile(event.src_path):
    logging.info('Detected:   "%s"' % event.src_path)

    if monitor_file(event.src_path):
      move_file(event.src_path)
  
  return None


def on_deleted(event):
  logging.debug('Deleted:    "%s"' % event.src_path)
  return None


def on_modified(event):
  logging.debug('Modified:   "%s"' % event.src_path)
  return None


def on_moved(event):
  logging.debug('Moved:      "%s" => "%s"' % (event.src_path, event.dest_path))
  return None


def monitor_file(file):
  logging.info('Monitoring: "%s"' % file)

  # Wait until source file appears complete and is no longer being written to.
  while True:
    filestat1 = get_filestat(file)
    time.sleep(args.polling)
    filestat2 = get_filestat(file)

    if not filestat1 or not filestat2:
      logging.warning('Unable to stat "%s"' % file)
      return False

    if (filestat1 == filestat2):
      logging.debug('File "%s" unchanged during polling window, assuming it is in a steady state' % file)
      return True

  return None


def get_filestat(file):
  try:
    filestat = os.stat(file)
    logging.debug('File stat for "%s": %s' % (file, filestat))
  except FileNotFoundError:
    filestat = False
    logging.warning('Vanished!:  "%s"' % file)
  except OSError as e:
    filestat = False
    logging.warning('Could not get size for "%s": %s' % (file, e))
  
  return filestat


def move_file(src):
  dst = os.path.dirname(src).replace(args.src, args.dst) + '/'
  logging.info('Moving:     "%s" to "%s"' % (src, dst))
  filesize = os.path.getsize(src)
  time_srt = now()
  res = rclone(['move', src, dst])
  time_end = now()
  time_dur = time_end - time_srt

  if res.returncode == 0:
    seconds = time_dur.total_seconds()
    rate_mbits = format(((filesize * 8) / 1000000) / seconds, '.2f')
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)

    logging.info('Finished:   "%s" moved to "%s" in %s hours, %s minutes, and %s seconds (%smbps)' % (src, dst, hours, minutes, seconds, rate_mbits))

    cleanup(args.src)

  return None


def cleanup(path):
  logging.info('Cleaning up empty directories in "%s"' % path)
  files = os.listdir(path)
  if len(files):
    for f in files:
      fullpath = os.path.join(path, f)
      if os.path.isdir(fullpath):
        cleanup(fullpath)
  
  files = os.listdir(path)
  if len(files) == 0 and path is not args.src:
    logging.info('Removing directory "%s"' % path)
    os.rmdir(path)

  return None


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Monitor staging directory and move files to rclone backend')
  
  parser.add_argument(
    'src',
    help='Source directory to monitor for new files (i.e. /mnt/staging)'
  )
  
  parser.add_argument(
    'dst',
    help='Rclone target location (i.e. gdrive:/)'
  )
  
  parser.add_argument(
    '-e',
    '--executable',
    default='rclone',
    help='Rclone executable (default: "%(default)s" in PATH)'
  )

  parser.add_argument(
    '-f',
    '--rclone-flag',
    action='append',
    default=[
      'progress',
      'stats=10s',
      'no-traverse',
      'user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"'
    ],
    help='Append global flag to Rclone command (see https://rclone.org/flags/) (list of flags always set: %(default)s)'
  )

  parser.add_argument(
    '-l',
    '--loglevel',
    default='INFO',
    help='Logging output level (valid options are "DEBUG", "INFO", "WARNING", "ERROR", and "CRITICAL") (default: %(default)s)'
  )

  parser.add_argument(
    '-p',
    '--polling',
    type=int,
    default=60,
    help='Seconds to wait for more data to be written to file before proceeding with Rclone move (default: %(default)s)'
  )
  
  parser.add_argument(
    '-s',
    '--scan-existing',
    action='store_true',
    help='Scan for existing files upon startup'
  )

  parser.add_argument(
    '--debug',
    action='store_true',
    help='Show debugging output'
  )

  args = parser.parse_args()

  logging.basicConfig(level=getattr(logging, args.loglevel.upper(), None))

  # Create Watchdog event handler.
  handler = LoggingEventHandler()
  handler.on_created = on_created
  handler.on_deleted = on_deleted
  handler.on_modified = on_modified
  handler.on_moved = on_moved

  # Create Watchdog observer.
  observer = Observer()
  observer.schedule(handler, args.src, recursive=True)

  try:
    if rclone(['about', args.dst]).returncode == 0:
      logging.info('Connected to backend "%s"' % args.dst)
    else:
      sys.exit()

    # Process any existing files.
    if args.scan_existing:
      scan_existing(args.src)

    observer.start()

    logging.info('Started monitoring "%s"' % args.src)
    logging.info('File check polling timer: %s seconds' % args.polling)

  except OSError as e:
    sys.exit(logging.error(e))

  try:
    while observer.isAlive():
      observer.join(1)
  except KeyboardInterrupt:
    observer.stop()

  observer.join()
