#!/usr/bin/env python3

import argparse
import hashlib
import os
import re
import sys
import shutil
import zipfile

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Tuple, Any

# All files in the defined directories and all subdirectories will be cleaned.
# Setting this to '.' or '/' will cause the tool to clean all existing files in the zip.
LOGDIRS = [
    '.',
]

TMPDIR = TemporaryDirectory()
SUPPORT_CLEANER_PATH = Path(__file__).parent.absolute()

if sys.version_info < (3, 5):
    raise Exception('Python in version 3.5 or higher is required to run this tool.')


#  1 HELPER FUNCTIONS

def add_unit_prefix(num: float, unit='B') -> str:
    """
    source: https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    """
    for prefix in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, prefix, unit)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', unit)


def remove_unit_prefix(numstr: str) -> Tuple[float, str]:
    num, prefix, unit = re.match(pattern=r'(\d+\.?\d*)\s?([KMGTPEZY]i)?(.*)', string=numstr).groups()
    num = float(num)

    if prefix is None:
        return num, unit

    for i in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi']:
        if prefix == i:
            return num, unit
        else:
            num *= 1024


def get_free_disk_space(path: str) -> int:
    _, _, free = shutil.disk_usage(path)
    return free


def print_files(files: List[Tuple[str, Any]], intro: str):
    print(intro)
    for path, value in files:
        path = Path(path).relative_to(TMPDIR.name)
        print('{path}: {value}'.format(path=path, value=value))


def delete_files(files: List[Tuple[str, Any]], message: str):
    while True:
        delete = input('\nDo you want to delete them? (y/n)')
        if delete == 'y':
            print(message)
            for file, _ in files:
                os.remove(file)
            break
        elif delete == 'n':
            break


#  2 PREPARATION & EXTRACTION

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
    parser.add_argument(
        '--filterfile',
        help='read filters from textfile',
        default='{support_cleaner_path}/filters.txt'.format(support_cleaner_path=SUPPORT_CLEANER_PATH)
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


def _get_uncompressed_size(zipf: zipfile.ZIP_DEFLATED) -> int:
    size = 0
    for file in zipf.infolist():
        size += file.file_size
    return size


#  3 DELETE UNWANTED LOGS

#  3.1 OLD FILES

def _remove_old_files(supportzip: str):
    limit = _set_age_limit()
    if not limit:
        return

    delete_timedelta = timedelta(days=limit)

    old_files = _collect_old_files(supportzip, delete_timedelta)
    print_files(files=old_files, intro='The following files are older than {} days:\n'.format(delete_timedelta.days))
    delete_files(files=old_files, message='Deleting old files\n')


def _collect_old_files(supportzip: str, delete_timedelta: timedelta) -> List[Tuple[str, datetime]]:
    old_files = []
    with zipfile.ZipFile(supportzip, 'r') as zipf:
        for file in zipf.infolist():
            name = '{tmpdir}/{rel_path}'.format(tmpdir=TMPDIR.name, rel_path=file.filename)
            (year, month, day, hours, minutes, seconds) = file.date_time
            date_time = datetime(year=year, month=month, day=day, hour=hours, minute=minutes, second=seconds)
            if datetime.now() - date_time > delete_timedelta:
                old_files.append((name, date_time))
    return old_files


def _set_age_limit() -> int:
    if os.getenv('DELETE_AFTER_DAYS'):
        return int(os.getenv('DELETE_AFTER_DAYS'))
    while True:
        limit = input('\nChoose a limit in days to delete old files (leave empty to skip)\n')
        if limit:
            try:
                return int(limit)
            except ValueError:
                print('Your input needs to be an integer.')
        else:
            break


#  3.2 BIG FILES

def _remove_large_files():
    large_files = _collect_largest_files()
    print_files(files=large_files, intro='Largest {}%:'.format(LARGEST_PERCENT))
    delete_files(files=large_files, message='Deleting largest files\n')


def _collect_largest_files() -> List[Tuple[str, str]]:
    logfiles = _list_files_in_dir(TMPDIR.name)
    file_sizes = []
    for file in logfiles:
        file_sizes.append((file, os.stat(file).st_size))
    # sort files by size
    file_sizes.sort(key=lambda x: x[1])
    # select files which are in the LARGEST_PERCENT of files
    n_small_files = int(len(file_sizes) * (1 - LARGEST_PERCENT / 100))
    large_files = file_sizes[n_small_files:]
    return [(path, add_unit_prefix(size)) for (path, size) in large_files]


#  3.3 MAIL LOGS

def _remove_maillogs():
    file_list = _list_files_in_dir(TMPDIR.name, pattern=r'.*(incoming|outgoing)-mail\.log')
    mail_log_files = [(file, '') for file in file_list]
    print_files(files=mail_log_files, intro='\nFound following mail log files:')
    delete_files(files=mail_log_files, message='Deleting mail log files\n')


#  4 CHECK LOGLEVEL

def _check_loglevel():
    # This regex matches the beginning of the standard atlassian logging format
    # e.g. 2020-01-22 09:03:08,633 http-nio-8080-exec-55 INFO
    regex_loglevel = r'^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}(,|.)\d{1,3})\s.*?\s(INFO|DEBUG)'
    for logdir in LOGDIRS:
        logfiles = _list_files_in_dir('{tmpdir}/{logdir}'.format(tmpdir=TMPDIR.name, logdir=logdir))
        for logfile in logfiles:
            with open(logfile, 'r') as file:
                logcontent = file.read()
                if re.search(regex_loglevel, logcontent) is not None:
                    input(
                        '{boundary}'
                        'Logmessages with level INFO or DEBUG have been detected!\n'
                        'Please consider using a stricter loglevel to avoid exposing too much sensitive information.\n'
                        'If this is not possible, take extra care to remove any sensitive information from the logs.\n'
                        '{boundary}'
                        'Press Enter to proceed.\n'.format(boundary=90 * '#' + '\n')
                    )
                    return


#  5 CLEAN LOGS

def _clean_logs(baseurl: str, filters: List[str]):
    for logdir in LOGDIRS:
        logfiles = _list_files_in_dir('{tmpdir}/{logdir}'.format(tmpdir=TMPDIR.name, logdir=logdir))
        for potential_filter in filters:
            try:
                pattern, replacement = potential_filter.split('||')
                if '{baseurl}' in pattern:
                    pattern = pattern.replace('{baseurl}', baseurl)
            except ValueError:
                print('"{}" is no valid filter string'.format(potential_filter))
                continue
            _replace_pattern_in_logs(
                pattern=pattern,
                replacement=replacement,
                logfiles=logfiles,
            )


def _get_filters(filterfile: str) -> List[str]:
    with open(filterfile) as file:
        return [line.strip() for line in file.readlines() if not line.startswith('#')]


def _generate_hash(string: str) -> str:
    return 'SHA256:' + hashlib.sha256(bytes(string, encoding='utf-8')).hexdigest()[:10]


def _hash_replacement(match: re.Match) -> str:
    replacement = '{hash}_CLEANED'
    substitute = match.group(0)
    groups = match.groupdict()
    if 'internal_mail' in groups:
        replacement = 'INTERNAL_EMAIL_{hash}_CLEANED'
        substitute = groups['internal_mail']
    elif 'external_mail' in groups:
        replacement = 'EXTERNAL_EMAIL_{hash}_CLEANED'
        substitute = groups['external_mail']
    elif 'user' in groups:
        replacement = 'USERNAME_{hash}_CLEANED'
        substitute = groups['user']
    replacement_hash = _generate_hash(substitute)
    return replacement.format(hash=replacement_hash)


def _replace_pattern_in_logs(pattern: str, replacement: str, logfiles: List[str]):
    print('-- pattern: "{}" --'.format(pattern))
    for logfile in logfiles:
        with open(logfile, 'r') as file:
            logcontent = file.read()
            if '{hash}' in replacement:
                # use _hash_replacement function in repl to determine the replacement string
                logcontent, nr = re.subn(pattern=re.compile(pattern), repl=_hash_replacement, string=logcontent)
            else:
                logcontent, nr = re.subn(pattern=re.compile(pattern), repl=replacement, string=logcontent)
            if nr:
                print('{nr} replacements ({replacement}) in {logfile}'.format(
                    nr=nr,
                    replacement=replacement,
                    logfile=Path(logfile).relative_to(TMPDIR.name),
                ))
        with open(logfile, 'w+') as file:
            file.write(logcontent)


def _clean_manual():
    input(
        '\nAutomatic cleaning finished. The extracted files are available at {tmpdir}. \n'
        '\n################################################################################\n'
        'These filters won\'t have cleaned everything perfectly from the logs!\n'
        'Especially usernames and names of people or businesses may still be present.\n'
        '##################################################################################\n'
        '\nYou can cleanup additional things manually or check how the files look like.\n'
        'Press Enter to proceed.\n'
        ''.format(tmpdir=TMPDIR.name)
    )


#  6 CREATE CLEANED ZIP AND CLEANUP

def _create_cleaned_zip():
    with zipfile.ZipFile('cleaned.zip', 'w', zipfile.ZIP_DEFLATED) as cleanedzip:
        _zip_dir(cleanedzip)


def _zip_dir(ziph: zipfile.ZipFile):
    for file in _list_files_in_dir(TMPDIR.name):
        ziph.write(filename=file, arcname=str(Path(file).relative_to(TMPDIR.name)))


def _list_files_in_dir(path: str, pattern='.*') -> List[str]:
    filelist = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if re.match(pattern=pattern, string=file):
                filelist.append(os.path.join(root, file))
    return filelist


def _cleanup():
    TMPDIR.cleanup()


# -- MAIN PROGRAM -- #

MAX_TMP_DIR_SIZE, _ = remove_unit_prefix(os.getenv('MAX_TMP_DIR_SIZE', '200MiB'))

# files that are in the LARGEST_PERCENTage are flagged for automatic deletion
LARGEST_PERCENT = 10

if __name__ == '__main__':
    args = _arguments()

    print('---')
    print('CLI tool to clean Atlassian support.zip from various data')
    print('---')

    try:
        _prepare()

        print('\nExtract support zip')
        _extract_zip(supportzip=args.supportzip)

        print('\nRemove old files')
        _remove_old_files(supportzip=args.supportzip)

        print('\nRemove largest files')
        _remove_large_files()

        print('\nRemove mail logs')
        _remove_maillogs()

        print('\nCheck Loglevel')
        _check_loglevel()

        print('\nClean unwanted information:')
        _clean_logs(baseurl=args.baseurl, filters=_get_filters(args.filterfile))

        _clean_manual()

        print('\nCreate cleaned.zip')
        _create_cleaned_zip()
    finally:
        _cleanup()
