# Your own personalized radio station: mpd-myfm

The [mpd-myfm.py] [script] Python script implements a console client for [Music
Player Daemon] [mpd] that adds tracks from similar artists to your playqueue
before you reach the end of your playqueue. It's called 'mpd-myfm' because it's
supposed to work like a personalized radio station that adapts to your moods
and favorites.

Similar artists and favorite tracks are retrieved from the [Last.fm] [lastfm]
database, which means you'll need an active internet connection for the client
to work.

Unless you're running Music Player Daemon on your local machine you'll need to
provide the host name to the client using the `-H` or `--host` command-line
option. You can use `-h` or `--help` to show a list of available options.

This script uses the Python [mpd] [lib] module. On [Ubuntu] [ubuntu] you can
install this module by executing the following command:

    $ sudo apt-get install python-mpd

Otherwise just download `mpd.py` from the module's [homepage] [lib].

To disable the client without killing it you can enable random and/or repeat.
The client will start working again when you disable both random and repeat.

The client can also be used as a daemon that starts on system start trough
init.d or Upstart. To support running as a daemon the python-daemon package
needs to be installed. This package is available on most distributions.
If it is not available on the distribution of your choice you can download it
from the [pypi] page.

[lastfm]: http://last.fm/
[lib]: http://mpd.wikia.com/wiki/ClientLib:python-mpd
[mpd]: http://mpd.wikia.com/wiki/Music_Player_Daemon_Wiki
[script]: http://github.com/xolox/mpd-myfm/blob/master/mpd-myfm
[ubuntu]: http://www.ubuntu.com/
[pypi]: http://pypi.python.org/pypi/python-daemon
