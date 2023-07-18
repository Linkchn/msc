#
# Copyright 2016 Chris Cummins <chrisc.101@gmail.com>.
#
# This file is part of CLgen.
#
# CLgen is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CLgen is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CLgen.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Exploratory analysis of OpenCL dataset
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import locale
import os
import sqlite3

from multiprocessing import Pool

from labm8 import fs

from clgen import dbutil
from clgen import log


IMG_DIR = 'img'


def decode(string):
    """
    Decode Unicode string.

    Arguments:
        string (str): Unicode encoded string.

    Returns:
        str: Decoded string, or empty string if decode fails.
    """
    try:
        return string.decode('utf-8')
    except UnicodeDecodeError:
        return ''


def div(x, y):
    """
    Zero-safe division.

    Arguments:
        x (Number): Numerator
        y (Number): Denominator

    Returns:
        Number: x / y
    """
    try:
        return x / y
    except ZeroDivisionError:
        return 0


def median(sorted_arr):
    """
    Return the median of a sorted sequence.

    Arugments:
        sorted_arr (Number[]): Sequence.

    Returns:
        Number: Median value.
    """
    n = len(sorted_arr)
    if not n:
        return 0

    midpoint = int(n / 2)
    if n % 2 == 1:
        return sorted_arr[midpoint]
    else:
        return (sorted_arr[midpoint - 1] + sorted_arr[midpoint]) / 2.0


def bigint(n):
    """
    Return comma seperated big numbers.

    Arugments:
        n (Number): Value.

    Returns:
        str: Comma separated value.
    """
    return locale.format('%d', round(n), grouping=True)


def seq_stats(sorted_arr):
    """
    Return stats on a sequence.

    Arguments:
        sorted_arr (Number[]): Sequence.

    Returns:
        str: Sequnece stats.
    """
    sorted_arr = sorted_arr or [0]
    avg = sum(sorted_arr) / len(sorted_arr)
    midpoint = int(len(sorted_arr) / 2)
    if len(sorted_arr) % 2 == 1:
        median = sorted_arr[midpoint]
    else:
        median = (sorted_arr[midpoint - 1] + sorted_arr[midpoint]) / 2.0
    return (
        'min: {}, med: {}, avg: {}, max: {}'.format(
            bigint(sorted_arr[0]), bigint(median), bigint(avg),
            bigint(sorted_arr[len(sorted_arr) - 1])))


def stats_worker(db_path):
    """
    Generate dataset stats.
    """
    log.debug("stats worker ...")
    db = dbutil.connect(db_path)
    c = db.cursor()
    stats = []

    c.execute("SELECT Count(*) from ContentFiles")
    nb_ocl_files = c.fetchone()[0]
    stats.append(('Number of content files', bigint(nb_ocl_files)))
    stats.append(('', ''))

    # ContentFiles
    c.execute("SELECT Count(DISTINCT id) from ContentFiles")
    nb_uniq_ocl_files = c.fetchone()[0]
    ratio_uniq_ocl_files = div(nb_uniq_ocl_files, nb_ocl_files)
    stats.append(('Number of unique content files',
                  bigint(nb_uniq_ocl_files) +
                  ' ({:.0f}%)'.format(ratio_uniq_ocl_files * 100)))

    c.execute("SELECT contents FROM ContentFiles")
    code = c.fetchall()
    code_lcs = [len(x[0].split('\n')) for x in code]
    code_lcs.sort()
    code_lc = sum(code_lcs)
    stats.append(('Total content line count', bigint(code_lc)))

    stats.append(('Content file line counts', seq_stats(code_lcs)))
    stats.append(('', ''))

    # Preprocessed
    c.execute("SELECT Count(*) FROM PreprocessedFiles WHERE status=0")
    nb_pp_files = c.fetchone()[0]
    ratio_pp_files = div(nb_pp_files, nb_ocl_files)
    stats.append(('Number of good preprocessed files',
                  bigint(nb_pp_files) +
                  ' ({:.0f}%)'.format(ratio_pp_files * 100)))

    c.execute('SELECT contents FROM PreprocessedFiles WHERE status=0')
    bc = c.fetchall()
    pp_lcs = [len(x[0].split('\n')) for x in bc]
    pp_lcs.sort()
    pp_lc = sum(pp_lcs)
    ratio_pp_lcs = div(pp_lc, code_lc)
    stats.append(('Lines of good preprocessed code',
                  bigint(pp_lc) +
                  ' ({:.0f}%)'.format(ratio_pp_lcs * 100)))

    stats.append(('Good preprocessed line counts',
                  seq_stats(pp_lcs)))
    stats.append(('', ''))

    return stats


def gh_stats_worker(db_path):
    """
    Generate github dataset stats.
    """
    print("stats worker ...")
    db = dbutil.connect(db_path)
    c = db.cursor()
    stats = []

    # Repositories
    c.execute("SELECT Count(*) from Repositories")
    nb_repos = c.fetchone()[0]
    stats.append(('Number of repositories visited', bigint(nb_repos)))
    stats.append(('', ''))

    c.execute("SELECT Count(DISTINCT repo_url) from ContentMeta")
    nb_ocl_repos = c.fetchone()[0]
    stats.append(('Number of content file repositories', bigint(nb_ocl_repos)))

    c.execute('SELECT Count(*) FROM Repositories WHERE fork=1 AND url IN '
              '(SELECT repo_url FROM ContentMeta)')
    nb_forks = c.fetchone()[0]
    ratio_forks = div(nb_forks, nb_ocl_repos)
    stats.append(('Number of forked repositories',
                  bigint(nb_forks) +
                  ' ({:.0f}%)'.format(ratio_forks * 100)))

    c.execute("SELECT Count(*) from ContentFiles")
    nb_ocl_files = c.fetchone()[0]
    stats.append(('Number of content files', bigint(nb_ocl_files)))
    stats.append(('', ''))

    # ContentFiles
    c.execute("SELECT Count(DISTINCT id) from ContentFiles")
    nb_uniq_ocl_files = c.fetchone()[0]
    ratio_uniq_ocl_files = div(nb_uniq_ocl_files, nb_ocl_files)
    stats.append(('Number of unique content files',
                  bigint(nb_uniq_ocl_files) +
                  ' ({:.0f}%)'.format(ratio_uniq_ocl_files * 100)))

    avg_nb_ocl_files_per_repo = div(nb_ocl_files, nb_ocl_repos)
    stats.append(('Content files per repository',
                  'avg: {:.2f}'.format(avg_nb_ocl_files_per_repo)))

    c.execute("SELECT contents FROM ContentFiles")
    code = c.fetchall()
    code_lcs = [len(x[0].split('\n')) for x in code]
    code_lcs.sort()
    code_lc = sum(code_lcs)
    stats.append(('Total content line count', bigint(code_lc)))

    stats.append(('Content file line counts', seq_stats(code_lcs)))
    stats.append(('', ''))

    # Preprocessed
    c.execute("SELECT Count(*) FROM PreprocessedFiles WHERE status=0")
    nb_pp_files = c.fetchone()[0]
    ratio_pp_files = div(nb_pp_files, nb_ocl_files)
    stats.append(('Number of good preprocessed files',
                  bigint(nb_pp_files) +
                  ' ({:.0f}%)'.format(ratio_pp_files * 100)))

    c.execute('SELECT contents FROM PreprocessedFiles WHERE status=0')
    bc = c.fetchall()
    pp_lcs = [len(x[0].split('\n')) for x in bc]
    pp_lcs.sort()
    pp_lc = sum(pp_lcs)
    ratio_pp_lcs = div(pp_lc, code_lc)
    stats.append(('Lines of good preprocessed code',
                  bigint(pp_lc) +
                  ' ({:.0f}%)'.format(ratio_pp_lcs * 100)))

    stats.append(('Good preprocessed line counts',
                  seq_stats(pp_lcs)))
    stats.append(('', ''))

    return stats


def graph_ocl_lc(db_path):
    """
    Plot distribution of OpenCL file line counts.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    sns.set(color_codes=True)

    out_path = fs.path(IMG_DIR, '/ocl_lcs.png')
    print('graph', out_path, '...')
    db = dbutil.connect(db_path)
    c = db.cursor()

    c.execute("SELECT contents FROM ContentFiles")
    ocl = c.fetchall()
    ocl_lcs = [len(x[0].split('\n')) for x in ocl]

    # Filter range
    data = [x for x in ocl_lcs if x < 500]

    sns.distplot(data, bins=20, kde=False)
    plt.xlabel('Line count')
    plt.ylabel('Number of OpenCL files')
    plt.title('Distribution of source code lengths')
    plt.savefig(out_path)


def graph_bc_lc(db_path):
    """
    Plot distribution of bytecode line counts.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    sns.set(color_codes=True)

    out_path = fs.path(IMG_DIR, 'bc_lcs.png')
    print('graph', out_path, '...')
    db = dbutil.connect(db_path)
    c = db.cursor()

    c.execute("SELECT contents FROM Bytecodes")
    ocl = c.fetchall()
    ocl_lcs = [len(decode(x[0]).split('\n')) for x in ocl]

    # Filter range
    data = [x for x in ocl_lcs if x < 500]

    sns.distplot(data, bins=20, kde=False)
    plt.xlabel('Line count')
    plt.ylabel('Number of Bytecode files')
    plt.title('Distribution of Bytecode lengths')
    plt.savefig(out_path)


def graph_ocl_stars(db_path):
    """
    Plot distribution of stargazers per file.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    sns.set(color_codes=True)

    out_path = fs.path(IMG_DIR, '/ocl_stars.png')
    print('graph', out_path, '...')
    db = dbutil.connect(db_path)
    c = db.cursor()

    c.execute('SELECT stars FROM ContentMeta LEFT JOIN Repositories '
              'ON ContentMeta.repo_url=Repositories.url')
    stars = [x[0] for x in c.fetchall()]

    # Filter range
    data = [x for x in stars if x < 50]

    sns.distplot(data, bins=20, kde=False)
    plt.xlabel('GitHub Stargazer count')
    plt.ylabel('Number of files')
    plt.title('Stargazers per file')
    plt.savefig(out_path)


def explore(db_path, graph=False):
    """
    Run exploratory analysis on dataset.

    Arguments:
        db_path (str): Path to dataset.
        graph (bool, optional): Render graphs.
    """
    locale.setlocale(locale.LC_ALL, 'en_GB.utf-8')

    db = dbutil.connect(db_path)

    if dbutil.is_github(db):
        db.close()
        explore_gh(db_path)
        return

    if graph and not os.path.exists(IMG_DIR):
        os.makedirs(IMG_DIR)

    # Worker process pool
    pool, jobs = Pool(processes=4), []
    if graph:
        jobs.append(pool.apply_async(graph_ocl_lc, (db_path,)))
        # TODO: If GH dataset:
        # jobs.append(pool.apply_async(graph_ocl_stars, (db_path,)))
    future_stats = pool.apply_async(stats_worker, (db_path,))

    # Wait for jobs to finish
    [job.wait() for job in jobs]

    # Print stats
    print()
    stats = future_stats.get()
    maxlen = max([len(x[0]) for x in stats])
    for stat in stats:
        k, v = stat
        if k:
            print(k, ':', ' ' * (maxlen - len(k) + 2), v, sep='')
        elif v == '':
            print(k)
        else:
            print()


def explore_gh(db_path, graph=False):
    """
    Run exploratory analysis on GitHub dataset.

    Arguments:
        db_path (str): Path to dataset.
        graph (bool, optional): Render graphs.
    """
    locale.setlocale(locale.LC_ALL, 'en_GB.utf-8')

    db = dbutil.connect(db_path)

    if graph and not os.path.exists(IMG_DIR):
        os.makedirs(IMG_DIR)

    # Worker process pool
    pool, jobs = Pool(processes=4), []
    if graph:
        jobs.append(pool.apply_async(graph_ocl_lc, (db_path,)))
        jobs.append(pool.apply_async(graph_ocl_stars, (db_path,)))

    future_stats = pool.apply_async(gh_stats_worker, (db_path,))

    # Wait for jobs to finish
    [job.wait() for job in jobs]

    # Print stats
    print()
    stats = future_stats.get()
    maxlen = max([len(x[0]) for x in stats])
    for stat in stats:
        k, v = stat
        if k:
            print(k, ':', ' ' * (maxlen - len(k) + 2), v, sep='')
        elif v == '':
            print(k)
        else:
            print()
