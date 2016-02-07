# List Mac Startup Items

OS X has a bunch of different ways for processes to run at startup:

- Shared file list (e.g., Users & Groups > Login Items)
- Services Management Framework (API call + special helper in app bundle)
- User-specific LaunchAgents
- System-level LaunchAgents
- LaunchDaemons

This script finds third-party processes in any of these locations and determines whether they are set to execute on startup/login.

## Usage

The script takes no arguments, so to execute:

``` shell
./find_all_startup_items.py
```

You'll get a list of every startup item, arranged by type.

You should not normally need to run this script as root, but occasionally LaunchAgents and LaunchDaemons may only be readable by root. In this case, you'll get a warning message when you run the script, and can run it again as root to read this items.

### Example output

``` 
Startup items in shared file list (System Preferences > Users & Groups > Login Items):

/Applications/iTunes.app/Contents/MacOS/iTunesHelper.app
/Applications/Dropbox.app 


Startup items loaded by the Services Management Framework:

/Applications/Fantastical 2.app
    Helper app: Fantastical Launcher.app

/Applications/HardwareGrowler.app
    Helper app: HardwareGrowlerLauncher.app


LaunchAgents (run at login for all users)
/Library/LaunchAgents

/Library/Application Support/Adobe/OOBE/PDApp/UWA/UpdaterStartupUtility
    Arguments: -mode=logon

/Library/Application Support/Paragon Updater/Paragon Updater.app/Contents/MacOS/Paragon Updater
    Arguments: --check --delay=30


LaunchDaemons (run at system start with root privileges)
/Library/LaunchDaemons

/Library/Application Support/Adobe/AdobeGCClient/AGSService

/sbin/kextload
    Arguments: /Library/Extensions/ufsd_NTFS.kext


User LaunchAgents (run at login for the current user)
~/Library/LaunchAgents

/Applications/Adobe Acrobat XI Pro/Adobe Acrobat Pro.app/Contents/MacOS/Updater/Adobe Acrobat Updater Helper.app/Contents/MacOS/Adobe Acrobat Updater Helper
    Arguments: semi-auto
```

## System Requirements

- Tested on 10.7-10.11.
- Does not run on 10.6 and earlier.