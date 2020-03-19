#!/usr/bin/env python3

import argparse
import os
import re
import sys
import shutil
import zipfile

from pathlib import Path
from tempfile import TemporaryDirectory

# All files in the defined directories and all subdirectories will be cleaned.
# Setting this to '.' or '/' will cause the tool to clean all existing files in the zip.
LOGDIRS = [
    '.',
]

TMPDIR = TemporaryDirectory()

if sys.version_info < (3, 5):
    raise Exception('Python in version 3.5 or higher is required to run this tool.')


def add_unit_prefix(num: float, unit='B') -> str:
    """
    source: https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    """
    for prefix in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, prefix, unit)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', unit)


def remove_unit_prefix(numstr: str) -> (float, str):
    num, prefix, unit = re.match(pattern=r'(\d+\.?\d*)\s?([KMGTPEZY]i)?(.*)', string=numstr).groups()
    num = float(num)

    if prefix is None:
        return num, unit

    for i in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi']:
        if prefix == i:
            return num, unit
        else:
            num *= 1024


def get_free_disk_space(path: str):
    total, used, free = shutil.disk_usage(path)
    return free


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='CLI tool to clean Atlassian support.zip from various data',
    )
    parser.add_argument(
        'supportzip',
        help='Path to support zip file to be cleaned',
    )
    parser.add_argument(
        'baseurl',
        help='Base-URL of the corresponding system',
    )
    return parser.parse_args()


def _prepare():
    try:
        os.remove('cleaned.zip')
        print('Removed existing cleaned.zip')
    except FileNotFoundError:
        pass


def _extract_zip(supportzip: str):
    global MAX_TMP_DIR_SIZE
    with zipfile.ZipFile(supportzip, 'r') as zipf:
        uncompressed_size = _get_uncompressed_size(zipf)
        while uncompressed_size > MAX_TMP_DIR_SIZE:
            print('\nWARNING: Decompressed size of {uncomp} exceeds allowed MAX_TMP_DIR_SIZE of {max_size}.'.format(
                uncomp=add_unit_prefix(uncompressed_size),
                max_size=add_unit_prefix(MAX_TMP_DIR_SIZE),
            ))
            answer = input(
                'Free disk space: {free_space}\n\n'
                'Change MAX_TMP_DIR_SIZE to:\n'
                '(Enter value in bytes, prefixes are allowed (KiB, MiB, GiB, ...); a to abort)\n'
                ''.format(free_space=add_unit_prefix(get_free_disk_space(TMPDIR.name)))
            )

            if answer == 'a':
                print('Aborted by user.')
                exit()

            try:
                MAX_TMP_DIR_SIZE, _ = remove_unit_prefix(answer)
                print('Changed MAX_TMP_DIR_SIZE to {}\n'.format(answer))
            except AttributeError:
                print('Input leads to an error: Please enter something like "30MiB"')

        zipf.extractall(TMPDIR.name)


def _get_uncompressed_size(zipf: zipfile.ZIP_DEFLATED):
    size = 0
    for file in zipf.infolist():
        size += file.file_size
    return size


def _clean_logs(baseurl: str):
    for logdir in LOGDIRS:
        logfiles = _list_files_in_dir('{tmpdir}/{logdir}'.format(tmpdir=TMPDIR.name, logdir=logdir))
        _replace_pattern_in_logs(  # Clean URL
            pattern=re.escape(baseurl),
            replacement='URL_CLEANED',
            logfiles=logfiles,
        )
        _replace_pattern_in_logs(  # Clean user names
            pattern='userName: \\S+',
            replacement='userName: USERNAME_CLEANED',
            logfiles=logfiles,
        )
    _clean_maillogs()
    _clean_manual()


def _replace_pattern_in_logs(pattern: str, replacement: str, logfiles: [str]):
    for logfile in logfiles:
        with open(logfile, 'r') as file:
            logcontent = file.read()
            logcontent, nr = re.subn(pattern=re.compile(pattern), repl=replacement, string=logcontent)
            if nr:
                print('{nr} replacements ({replacement}) in {logfile}'.format(
                    nr=nr,
                    replacement=replacement,
                    logfile=Path(logfile).relative_to(TMPDIR.name),
                ))
        with open(logfile, 'w+') as file:
            file.write(logcontent)


def _clean_maillogs():
    maillogfiles = _list_files_in_dir(TMPDIR.name, pattern=r'.*(incoming|outgoing)-mail\.log')
    print('\nFound following mail log files:')
    for file in maillogfiles:
        print(Path(file).relative_to(TMPDIR.name))
    while True:
        answer = input('\nDelete mail log files? (y/n)')
        if answer == 'y':
            for file in maillogfiles:
                os.remove(file)
            break
        if answer == 'n':
            break


def _clean_manual():
    input(
        '\nAutomatic cleaning finished. The extracted files are available at {tmpdir}. '
        'If you like, you can cleanup additional things manually or check how the files look like.\n'
        'Press Enter to proceed.\n'
        ''.format(tmpdir=TMPDIR.name)
    )


def _create_cleaned_zip():
    with zipfile.ZipFile('cleaned.zip', 'w', zipfile.ZIP_DEFLATED) as cleanedzip:
        _zip_dir(cleanedzip)


def _zip_dir(ziph: zipfile.ZipFile):
    for file in _list_files_in_dir(TMPDIR.name):
        ziph.write(filename=file, arcname=str(Path(file).relative_to(TMPDIR.name)))


def _list_files_in_dir(path: str, pattern='.*') -> [str]:
    filelist = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if re.match(pattern=pattern, string=file):
                filelist.append(os.path.join(root, file))
    return filelist


def _cleanup():
    TMPDIR.cleanup()


MAX_TMP_DIR_SIZE, _ = remove_unit_prefix(os.getenv('MAX_TMP_DIR_SIZE', '200MiB'))

if __name__ == '__main__':
    args = _arguments()

    print('---')
    print('CLI tool to clean Atlassian support.zip from various data')
    print('---')

    try:
        _prepare()

        print('Extract support zip')
        _extract_zip(supportzip=args.supportzip)

        print('Clean unwanted information:')
        _clean_logs(baseurl=args.baseurl)

        print('Create cleaned.zip')
        _create_cleaned_zip()
    finally:
        _cleanup()
