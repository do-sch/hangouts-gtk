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
from gi.repository import Gio, GLib
from gi.repository.GdkPixbuf import Pixbuf, InterpType

PROFILE_PHOTO = (46, 46)
PROFILE_PHOTO_SMALL = (32, 32)
SENT_IMAGE_PREVIEW = (200, 200)


class ImageCache:

    #__scaled_image_dict: dict = NotImplemented  # contains cache of scaled images
    #__raw_image_dict: dict = NotImplemented     # contains cache of raw images
    #__request_threads_lock = threading.Lock()
    #__request_threads = set()

    __sem = NotImplemented
    __image_dict = NotImplemented

    # create ImageCache TODO: load cache from .cache directory
    def __init__(self):
        self.__raw_image_dict = dict()
        self.__scaled_image_dict = dict()

        self.__sem = _thread.allocate_lock()
        self.__image_dict = dict()
        self.__fetching_dict = dict()


    def __get_image_thread(self, url: str, callback, cache, userdata=None):

        # standardize all URLs
        if not url.startswith("https:"):
            url = "https:" + url

        # look into cache
        cached = self.__image_dict.get(url, None)
        if cached:
            _thread.start_new_thread(
                callback, (cached, userdata)
            )
            return

        # no one is allowed to look inside fetching_dict
        self.__sem.acquire()

        # look into cache again
        cached = self.__image_dict.get(url, None)
        if cached:
            callback(cached, userdata)
            return

        # see if someone else is working
        do_the_work = len(self.__fetching_dict) == 0

        work = (callback, userdata, cache)
        url_list = self.__fetching_dict.get(url, list())
        url_list.append(work)
        self.__fetching_dict[url] = url_list

        self.__sem.release()

        # return if someone else needs to do the work
        if not do_the_work:
            return

        # iterate through all urls
        while len(self.__fetching_dict):
            # get first key
            url = next(iter(self.__fetching_dict))

            # request image
            response = requests.get(url)
            input_stream = Gio.MemoryInputStream.new_from_data(response.content, None)
            pixbuf = Pixbuf.new_from_stream(input_stream, None)

            self.__sem.acquire()
            # pass image to every callback
            for (callback, userdata, cache) in self.__fetching_dict.get(url):
                if cache:
                    self.__image_dict[url] = pixbuf
                _thread.start_new_thread(
                    callback,
                    (pixbuf, userdata)
                )
            del self.__fetching_dict[url]
            self.__sem.release()


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
