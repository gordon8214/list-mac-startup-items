#!/usr/bin/env python

import os
import stat
import sys
import glob
import subprocess
import platform
import argparse
import pwd

# Help
parser = argparse.ArgumentParser(description='Returns a detailed list of all third-party startup items in OS.'
                                             'Takes no arguments.')
args = parser.parse_args()

# Get current OS X version. Format: 10.x (int).
min_os_subversion = 7
os_ver = platform.mac_ver()[0]
os_ver = int('.'.join(os_ver.split('.')[1:2]))
devnull = open(os.devnull, 'w')

if os_ver < min_os_subversion:
    print "ERROR: This script requires OS %s or later." % str(min_os_subversion)
    print "Your OS Version: %s." % str(os_ver)
    sys.exit(1)

# Get the username of the currently logged-in user.
current_username = os.getlogin()
current_uid = str(pwd.getpwnam(current_username).pw_uid)


class ColoredText:
    """Colored text for prettier console output."""
    def __init__(self):
        self.HEADER = '\033[95m'
        self.OKBLUE = '\033[94m'
        self.OKGREEN = '\033[92m'
        self.WARNING = '\033[93m'
        self.FAIL = '\033[91m'
        self.ENDC = '\033[0m'
        self.BOLD = '\033[1m'
        self.UNDERLINE = '\033[4m'

    def print_header(self, msg_type, text):
        """
        Print a header line in colored text.

        :param msg_type: str
        :param text: str
        """

        print '\n' + msg_type + text + self.ENDC + '\n'


class StartupServices:
    """Get and store the various startup services."""
    def __init__(self, apps_to_check):
        self.warnings = list()
        self.apps = apps_to_check
        self.services = self.__get_loginitem_services()
        self.shared_file_list = self.__get_login_items().split(',')
        self.launchagents_allusers = (self.__check_launchd_dirs('/Library/LaunchAgents/'))
        self.launchdaemons = (self.__check_launchd_dirs('/Library/LaunchDaemons/'))
        self.launchagents_user = (self.__check_launchd_dirs('/Users/' + current_username + '/Library/LaunchAgents/'))

    @staticmethod
    def __get_login_items():
        return subprocess.check_output(['osascript', '-e',
                                        'tell application "System Events" to get the path of every login item'])

    def __get_loginitem_services(self):
        services_list = list()
        for app in self.apps:
            if os.path.isdir(app + '/Contents/Library/LoginItems'):
                helper = os.listdir(app + '/Contents/Library/LoginItems/')[0]
                helperpath = app + '/Contents/Library/LoginItems/' + helper
                helper_bundle_id = subprocess.check_output([
                    '/usr/libexec/PlistBuddy', '-c', 'Print CFBundleIdentifier', helperpath + '/Contents/Info.plist'])
                # If this script is run as root, we need to run launchctl as the current user instead of root
                # to get the proper results.
                if os.getuid() == 0:
                    launchd_job_exists = subprocess.call([
                        'sudo', '-u', current_username, 'launchctl', 'list',
                        helper_bundle_id.rstrip()], stdout=devnull, stderr=devnull)
                else:
                    launchd_job_exists = subprocess.call([
                        'launchctl', 'list', helper_bundle_id.rstrip()], stdout=devnull, stderr=devnull)
                if launchd_job_exists == 0:
                    startup_app = (app, helper)
                    services_list.append(startup_app)
        return services_list

    def __check_launchd_dirs(self, l_dir):
        result = []
        arguments = None
        if l_dir.startswith('/Library'):
            domain = 'allusers'
        else:
            domain = 'user'

        # OS 10.11 introduces a new location for the overrides/disabled file.
        if os_ver >= 10.11:
            overrides_file_allusers = '/private/var/db/com.apple.xpc.launchd/disabled.plist'
            overrides_file_user = '/private/var/db/com.apple.xpc.launchd/disabled.' + current_uid + '.plist'
        else:
            overrides_file_allusers = '/private/var/db/launchd.db/overrides.plist'
            overrides_file_user = 'overrides/private/var/db/launchd.db/com.apple.launchd.peruser.'\
                                  + current_uid + '/overrides.plist'

        for plist in glob.glob(l_dir + '*'):
            skip = False

            try:
                job_label = (subprocess.check_output(['/usr/libexec/PlistBuddy',
                                                      '-c', 'Print Label', plist], stderr=devnull)).rstrip()
            except subprocess.CalledProcessError:
                # Try to figure out why we can't read a plist's label attribute.
                job_label = ''
                if os.path.islink(plist):
                    if not os.path.exists(os.readlink(plist)):
                        self.warnings.append("- Job '%s' is a symbolic link to a nonexistent file.\n "
                                             "It should be safe to delete." % plist)
                    else:
                        pass

                elif not os.access(plist, os.R_OK):
                    self.warnings.append("- Job '%s' requires root privileges to read. This is unusual.\n"
                                         "Run this script again using 'sudo' in order to read this job." % plist)
                else:
                    self.warnings.append("- Job '%s' could not be read. It may be corrupt." % plist)

            # Check if job is disabled by either default value or override.
            # The keys in the 'disabled' files override the Disabled key in the launchd job file.
            if domain == 'allusers':
                overrides_file = overrides_file_allusers
            elif domain == 'user':
                overrides_file = overrides_file_user
            if plist_key_exists(job_label, overrides_file):
                if plist_val_true(job_label, overrides_file):
                    skip = True
            elif plist_val_true('Disabled', plist):
                skip = True

            if not plist_val_true('RunAtLoad', plist):
                skip = True

            if not skip:
                if plist_key_exists('Program', plist):
                    startup_agent = (subprocess.check_output(['/usr/libexec/PlistBuddy',
                                                              '-c', 'Print Program', plist])).rstrip()
                    if plist_key_exists('ProgramArguments', plist):
                        arguments = (subprocess.check_output([
                            '/usr/libexec/PlistBuddy', '-c', 'Print ProgramArguments', plist], stderr=devnull)).rstrip()
                        arguments = arguments.split('\n')
                        # Remove array formatters.
                        del arguments[0]
                        del arguments[-1]
                        arguments = map(lambda x: x.lstrip(), arguments)
                        if arguments[0] == startup_agent:
                            del arguments[0]
                else:
                    arguments = (subprocess.check_output([
                        '/usr/libexec/PlistBuddy', '-c', 'Print ProgramArguments', plist], stderr=devnull)).rstrip()
                    arguments = arguments.split('\n')
                    # Remove array formatters.
                    del arguments[0]
                    del arguments[-1]
                    startup_agent = arguments[0].lstrip()
                    if len(arguments) > 1:
                        arguments = map(lambda x: x.lstrip(), arguments[1:])
                    else:
                        arguments = None

                if arguments:
                    result.append((startup_agent, arguments))
                else:
                    result.append((startup_agent, ''))
        return result


def is_readable(filepath):
    """
    Determine if we have read access to a file.

    :param filepath: str
    """

    st = os.stat(filepath)
    return bool(st.st_mode & stat.S_IRGRP)


def get_all_apps():
    """Use Spotlight to get path to all apps, excluding those in /System"""

    find_all_apps = subprocess.check_output(['mdfind', 'kMDItemKind == Application'])
    apps_to_check = []
    for app in find_all_apps.split('\n'):
        if '/System/' not in app:
            apps_to_check.append(app)
    return apps_to_check


def plist_val_true(key, plist):
    """Check if a plist boolean key exists and is True.

    :param key: str
    :param plist: str
    """

    try:
        result = subprocess.check_output(['/usr/libexec/PlistBuddy', '-c', 'Print ' + key, plist], stderr=devnull)
        if result.rstrip() == 'true':
            result = True
        else:
            result = False
    except subprocess.CalledProcessError:
        result = False
    return result


def plist_key_exists(key, plist):
    """
    Check if a given key exists.

    :param key: str
    :param plist: str
    """

    try:
        subprocess.check_output(['/usr/libexec/PlistBuddy', '-c', 'Print ' + key, plist], stderr=devnull)
    except subprocess.CalledProcessError:
        return False

    return True


# Colored text for better console output
colors = ColoredText()


def print_launchd(location, title):
    """
    Printed a formatted list of launchd jobs.

    :param title: str
    :param location: list
    """
    if location:  # Print headers only if there are actually startup items in this category.
        colors.print_header(colors.HEADER, title)

        for start_item in location:
            print start_item[0]
            if start_item[1] != '':
                print colors.BOLD + '\tArguments: ' + colors.ENDC + ' '.join(start_item[1]) + '\n'
            else:
                print ''
    else:
        pass


# New instance of our service-storage class.
services = StartupServices(get_all_apps())

if services.shared_file_list:
    colors.print_header(colors.HEADER,
                        'Startup items in shared file list (System Preferences > Users & Groups > Login Items):')
    for startup_item in services.shared_file_list:
        print startup_item

if services.services:
    colors.print_header(colors.HEADER, 'Startup items loaded by the Services Management Framework:')
    for startup_item in services.services:
        print startup_item[0]
        print '\tHelper app: ' + startup_item[1] + '\n'


print_launchd(services.launchagents_allusers, 'LaunchAgents (run at login for all users)\n'
                                              '/Library/LaunchAgents')
print_launchd(services.launchdaemons, 'LaunchDaemons (run at system start with root privileges)\n'
                                      '/Library/LaunchDaemons')
print_launchd(services.launchagents_user, 'User LaunchAgents (run at login for the current user)\n'
                                          '~/Library/LaunchAgents')

if services.warnings:
    colors.print_header(colors.WARNING, 'Warnings')
    for warning in services.warnings:
        print warning + '\n'


colors.print_header(colors.HEADER, 'Notes')

print '- To remove items from the shared file list, go to System Preferences > Users & Groups > Login Items.\n'

print '- Items cannot be removed from the Services Management Framework manually.\n' \
      '  Open the associated app and look for an option to disable automatic launch on startup.\n'

print '- LaunchAgents/LaunchDaemons aren\'t necessarily running all the time.\n' \
      '  They may run once and exit, or run on a schedule.'
