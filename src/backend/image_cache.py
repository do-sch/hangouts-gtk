# This file is part of Hangouts GTK
# Copyright © 2019-2020 Dominik Schütz <do.sch.dev@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import requests
import _thread
import threading
import os
import datetime

from gi.repository import Gio, GLib
from gi.repository.GdkPixbuf import Pixbuf, InterpType

PROFILE_PHOTO = (46, 46)
PROFILE_PHOTO_SMALL = (32, 32)
SENT_IMAGE_PREVIEW = (200, 200)


class ImageCache:

    __REFETCH_TIME = 5 * 60 * 60  # refetch after 5 hours

    def __init__(self):
        self.__raw_image_dict = dict()
        self.__scaled_image_dict = dict()

        self.__sem = _thread.allocate_lock()
        self.__fetch_sem = _thread.allocate_lock()
        self.__sems = dict()
        self.__image_dict = dict()

        self.__image_cache_dir_path = GLib.get_user_cache_dir()

        # create cache directory if not exists
        _thread.start_new_thread(
            GLib.mkdir_with_parents,
            (self.__image_cache_dir_path, 0o644)
        )

    # looks into cache and fetches images
    def __get_image_thread(self, url: str, callback, cache, userdata=None):

        # standardize all URLs
        if not url.startswith("https:"):
            url = "https:" + url

        # look into ram cache
        cached = self.__image_dict.get(url, None)
        if cached:
            timeval, pixbuf = cached

            # give cached image to client
            _thread.start_new_thread(
                callback, (cached, userdata)
            )

            # if image is cached and not too old
            time_diff = datetime.datetime.now() - mod_time
            if time_diff.total_secounds() < self.__REFETCH_TIME:
                return

        # look in cache dir
        else:
            filename = url.split("/")[-1]
            filepath = os.path.join(self.__image_cache_dir_path, filename)
            if GLib.file_test(filepath, GLib.FileTest.EXISTS):
                pixbuf = Pixbuf.new_from_file(filepath)

                mod_time = os.stat(filepath).st_mtime
                mod_time = datetime.datetime.fromtimestamp(mod_time)
                # store to ram cache
                self.__image_dict[url] = (mod_time, pixbuf)

                # give cached image to client
                _thread.start_new_thread(
                    callback, (pixbuf, userdata)
                )

                # if image is cached and not too old return
                time_diff = datetime.datetime.now() - mod_time
                if time_diff.total_seconds() < self.__REFETCH_TIME:
                    return

        # create a lock for this url
        self.__sem.acquire()
        my_lock = self.__sems.get(url, _thread.allocate_lock())
        self.__sem.release()

        my_lock.acquire()

        # search again in ram cache
        cached = self.__image_dict.get(url, None)
        if cached:
            timeval, pixbuf = cached

            # give cached image to client
            _thread.start_new_thread(
                callback, (cached, userdata)
            )

            time_diff = datetime.datetime.now() - mod_time
            if time_diff.total_seconds() < self.__REFETCH_TIME:
                my_lock.release()
                return

        # request and cache image to file image
        self.__fetch_sem.acquire()
        response = requests.get(url)
        filename = url.split("/")[-1]
        filepath = os.path.join(self.__image_cache_dir_path, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)
        response.close()
        pixbuf = Pixbuf.new_from_file(filepath)
        input_stream.close()
        self.__fetch_sem.release()

        # return new image to caller
        _thread.start_new_thread(
            callback,
            (pixbuf, userdata)
        )

        # cache image in ram
        self.__image_dict[url] = (datetime.datetime.now(), pixbuf)

        # release lock for this url
        my_lock.release()


    def get_image(self, url: str, callback, size=PROFILE_PHOTO, cache=False):

        def got_image(image, userdata):
            callback, size = userdata
            resize(image, size, callback)

        _thread.start_new_thread(
            self.__get_image_thread,
            (url, got_image, cache, (callback, size))
        )

def resize(pixbuf, size, callback):

    if size is None:
        GLib.idle_add(callback, pixbuf)
        return

    width, height = size
    if width <= 0 and height <= 0:
        return pixbuf
    dim = pixbuf.props.width / pixbuf.props.height
    if dim > 1:
        height = width / dim
    else:
        width = height * dim

    scaled_image = pixbuf.scale_simple(width, height, InterpType.BILINEAR)

    GLib.idle_add(callback, scaled_image)
