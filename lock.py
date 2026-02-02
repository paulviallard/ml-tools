# Copyright © 2025 Paul Viallard <paul.viallard@gmail.com> and Hind Atbir <atbir.p@gmail.com>
# This work is free. You can redistribute it and/or modify it under the
# terms of the Do What The Fuck You Want To Public License, Version 2,
# as published by Sam Hocevar. See http://www.wtfpl.net/ for more details.

import os
import time

###############################################################################

class Lock():

    def __init__(self, file_):
        # We save the path associated with the data
        self._path_file = os.path.abspath(file_)
        self._lock_file = self._path_file+".lock"
        # We initialize the flag to know if we got the lock
        self.__got_lock = False

    # ----------------------------------------------------------------------- #

    def do(self, function, *args, **kwargs):

        # While we do not have the lock,
        while(not self.__got_lock):
            # We get the lock
            self._get_lock()
            if self.__got_lock:
                # If we have the lock, we run the function and release the lock
                try:
                    result = function(*args, **kwargs)
                finally:
                    self._release_lock()
                return result
            else:
                # If we couldn't get the lock, we wait (a bit)
                time.sleep(0.1)

    def _get_lock(self):

        # We create the file if it does not exist
        try:
            os.makedirs(os.path.dirname(self._path_file), exist_ok=True)
            fd = os.open(self._path_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
        except FileExistsError:
            pass

        # We now assume that the file exists. We try to get the lock by
        # creating an additional hard link (named with a .lock)
        try:
            os.link(self._path_file, self._lock_file)
            if(os.stat(self._path_file).st_nlink == 2):
                self.__got_lock = True
            else:
                self.__got_lock = False
        except FileExistsError:
            self.__got_lock = False
            return

    def _release_lock(self):

        # If we got the lock, we just remove the .lock file, i.e., one link
        if self.__got_lock:
            try:
                os.unlink(self._lock_file)
            except FileNotFoundError:
                pass
            finally:
                self.__got_lock = False
