#!/usr/bin/env python3

import argparse
import datetime
import logging
import os
import shutil
import subprocess
import sys
import tempfile

"""
Last update: Dom Heinzeller (dom.heinzeller@noaa.gov), 2019-11-22

TODO

- set debug level via command line argument
- cleanup
- add documentation
- add unit/doctests
- make default email recipient system dependent
"""

# BASEDIR is the current directory where this script is executed
BASEDIR = os.getcwd()

###############################################################################
# User config                                                                 #
###############################################################################

# Known forks
FORKS = {
    'dtc' : {
        'branches' : [ 'dtc/develop' ],
        'url'      : 'https://github.com/NCAR/ufs-weather-model',
        },
    'emc' : {
        'branches' : [ 'develop' ],
        'url'      : 'https://github.com/ufs-community/ufs-weather-model',
        },
    # For development
    'dom' : {
        'branches' : [ 'nems_machine_env_var' ],
        'url'      : 'https://github.com/climbfuji/ufs-weather-model',
        },
    }

# Systems, compilers, projects, regression test configurations
SYSTEMS = {
    'cheyenne' : {
        'compilers'        : [ 'intel', 'gnu' ],
        'default_compiler' : 'intel',
        'default_project'  : 'P48503002',
        'default_rtconfig' : {
            'intel' : 'rt.conf', # change to rt_ccpp_dtc.conf ?
            'gnu'   : 'rt_gnu.conf',
            },
        },
    'hera' : {
        'compilers'        : [ 'intel' ],
        'default_compiler' : 'intel',
        'default_project'  : 'gmtb',
        'default_rtconfig' : {
            'intel' : 'rt.conf',
            },
        },
    }

# Name of the directory to check out the code (relative)
CHECKOUT_DIR = 'ufs-weather-model'

# Directory underneath the checkout directory from which to run the tests (relative)
TEST_DIR = 'tests'

# RT_LOG is the name of the
RT_LOG = os.path.join(BASEDIR, "rt_%Y%m%dT%H%M%S.log")

# String that indicates that regression tests were successful
RT_SUCCESSFUL = 'REGRESSION TEST WAS SUCCESSFUL'

# Default email recipient
DEFAULT_EMAIL_RECIPIENT = 'heinzell@ucar.edu'

###############################################################################
# Set up the command line argument parser and other global variables          #
###############################################################################

parser = argparse.ArgumentParser()
parser.add_argument('--fork',     '-f', action='store',      help='fork to use',                required=True)
parser.add_argument('--branch',   '-b', action='store',      help='branch to test',             required=True)
parser.add_argument('--system',   '-s', action='store',      help='system/machine to use',      required=True)
parser.add_argument('--compiler', '-c', action='store',      help='compiler to use',            required=False, default=None)
parser.add_argument('--project',  '-p', action='store',      help='project to use',             required=False, default=None)
parser.add_argument('--rtconfig', '-r', action='store',      help='reg. test config to use',    required=False, default=None)
parser.add_argument('--keep',     '-k', action='store_true', help='keep temporary directory',   required=False, default=False)
parser.add_argument('--email',    '-e', action='store',      help='send email to this address', required=False, default=None)

###############################################################################
# Functions and subroutines                                                   #
###############################################################################

def execute(cmd):
    """Runs a local command in a shell. Waits for completion and
    returns status, stdout and stderr if execution of the command
    is successful, aborts otherwise."""

    # Set debug to true if logging level is debug
    debug = logging.getLogger().getEffectiveLevel() == logging.DEBUG

    logging.debug('Executing "{0}"'.format(cmd))
    p = subprocess.Popen(cmd, stdout = subprocess.PIPE,
                         stderr = subprocess.PIPE, shell = True)
    (stdout, stderr) = p.communicate()
    stdout = stdout.decode().rstrip('\n')
    stderr = stderr.decode().rstrip('\n')
    status = p.returncode
    if debug:
        message = 'Execution of "{}" returned with exit code {}\n'.format(cmd, status)
        message += '    stdout: "{}"\n'.format(stdout)
        message += '    stderr: "{}"'.format(stderr)
        logging.debug(message)
    if not status == 0:
        message = 'Execution of command {} failed, exit code {}\n'.format(cmd, status)
        message += '    stdout: "{}"\n'.format(stdout)
        message += '    stderr: "{}"'.format(stderr)
        raise Exception(message)
    return (status, stdout, stderr)

def setup_logging():
    """Sets up the logging module and logging level."""
    #level = logging.INFO
    level = logging.DEBUG
    logging.basicConfig(format='%(levelname)s: %(message)s', level=level)
    logging.info('Logging level set to {}'.format(logging.getLogger().getEffectiveLevel()))
    return

def parse_arguments():
    """Parse command line arguments."""
    args = parser.parse_args()
    # GitHub fork
    fork = args.fork
    if not fork in FORKS.keys():
        raise Exception("Invalid fork {}".format(fork))
    # GitHub branch
    branch = args.branch
    if not branch in FORKS[fork]['branches']:
        raise Exception("Invalid branch {} of fork".format(branch, fork))
    logging.info('Using branch {} of fork {}'.format(branch, fork))
    # System
    system = args.system
    if not system in SYSTEMS.keys():
        raise Exception("Invalid system {}".format(system))
    # Compiler
    if args.compiler:
        compiler = args.compiler
    else:
        compiler = SYSTEMS[system]['default_compiler']
    if not compiler in SYSTEMS[system]['compilers']:
        raise Exception("Invalid compiler {} for system {}".format(compiler, system))
    # Project
    if args.project:
        project = args.project
    else:
        project = SYSTEMS[system]['default_project']
    #if not project in SYSTEMS[system]['projects']:
    #    raise Exception("Invalid project {} for system {}".format(project, system))
    #
    # Regression test configuration
    if args.rtconfig:
        rtconfig = args.rtconfig
    else:
        rtconfig = SYSTEMS[system]['default_rtconfig'][compiler]
    #if not rtconfig in SYSTEMS[system]['rtconfigs'][compiler]:
    #    raise Exception("Invalid reg. test config {} for system {} and compiler".format(project, system, compiler))
    #
    logging.info('Running on {} with compiler {} and project {} using {} regression test config'.format(system, compiler, project, rtconfig))
    keep = args.keep
    if keep:
        logging.info('Keep run directory after successful test')
    else:
        logging.info('Delete run directory after successful test (keep if not successful)')
    # Email
    if args.email:
        email = args.email
    else:
        email = DEFAULT_EMAIL_RECIPIENT
    #
    return (fork, branch, system, compiler, project, rtconfig, keep, email)

def get_workdir(now, fork, branch, compiler):
    tmpdir = tempfile.mkdtemp(prefix='regtest_ufs_weather_model_{}_{}_{}_{}_'.format(
             fork, branch.replace('/','-'), compiler, now.strftime('%Y%m%dT%H%M%S')))
    logging.info('Setting up temporary directory {}'.format(tmpdir))
    return tmpdir

def checkout_code(fork, branch, tmpdir):
    url = FORKS[fork]['url']
    #
    logging.info('Cloning branch {} from url {}'.format(branch, url))
    os.chdir(tmpdir)
    cmd = 'git clone -v -b {} {} {}'.format(branch, url, CHECKOUT_DIR)
    (status, stdout, stderr) = execute(cmd)
    #
    logging.info('Checking out submodules')
    os.chdir(CHECKOUT_DIR)
    cmd = 'git submodule sync'
    (status, stdout, stderr) = execute(cmd)
    cmd = 'git submodule update --init --recursive'
    (status, stdout, stderr) = execute(cmd)
    #
    os.chdir(BASEDIR)
    return

def run_tests(now, system, compiler, project, rtconfig, keep, tmpdir):
    os.chdir(os.path.join(tmpdir, CHECKOUT_DIR, TEST_DIR))
    if keep:
        keep_flag = '-k'
    else:
        keep_flag = ''
    #
    rtlog = now.strftime(RT_LOG)
    logging.info('Launching regression test, logging to {} ... '.format(rtlog))
    cmd = 'NEMS_MACHINE={} NEMS_COMPILER={} ACCNR={} ./rt.sh -l {} {} > {} 2>&1'.format(
                                  system, compiler, project, rtconfig, keep_flag, rtlog)
    (status, stdout, stderr) = execute(cmd)
    #
    os.chdir(BASEDIR)
    return rtlog

def check_logs(system, compiler, tmpdir, rtlog, keep, email):
    # Check for the string indicating success in the regression test log
    with open(rtlog) as f:
        if RT_SUCCESSFUL in f.read():
            success = True
        else:
            success = False
    # Delete temporary run directory unless requested to keep it
    if success and keep:
        subject = '{}/{}: regression tests passed'.format(system, compiler)
        message = 'Regression tests passed, see regression test log {} and run directory {}.'.format(rtlog, tmpdir)
        logging.info(message)
    elif success and not keep:
        subject = '{}/{}: regression tests passed'.format(system, compiler)
        message = 'Regression tests passed, see regression test log {}.'.format(rtlog)
        logging.info(message)
    else:
        subject = '{}/{}: regression tests did NOT PASS'.format(system, compiler)
        message = 'Regression tests did NOT PASS, check latest regression test log {} and run directory {}'.format(rtlog, tmpdir)
        logging.error(message)
    # Send out email
    cmd = 'echo "{}" | mail -a "{}" -s "{}" {}'.format(message, rtlog, subject, email)
    (status, stdout, stderr) = execute(cmd)
    return success

def cleanup(success, keep, tmpdir):
    if success and not keep:
        logging.debug('Deleting temporary directory {}'.format(tmpdir))
        shutil.rmtree(tmpdir)

def main():
    now = datetime.datetime.now()
    setup_logging()
    logging.info('Starting automatic regression test')
    (fork, branch, system, compiler, project, rtconfig, keep, email) = parse_arguments()
    tmpdir = get_workdir(now, fork, branch, compiler)
    checkout_code(fork, branch, tmpdir)
    rtlog = run_tests(now, system, compiler, project, rtconfig, keep, tmpdir)
    success = check_logs(system, compiler, tmpdir, rtlog, keep, email)
    cleanup(success, keep, tmpdir)
    logging.info('Finished automatic regression test')

if __name__ == '__main__':
    main()
