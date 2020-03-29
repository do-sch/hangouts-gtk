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
import threading
from gi.repository import Gio, GLib
from gi.repository.GdkPixbuf import Pixbuf, InterpType

PROFILE_PHOTO = (46, 46)
PROFILE_PHOTO_SMALL = (32, 32)
SENT_IMAGE_PREVIEW = (200, 200)


class ImageCache:

    __scaled_image_dict: dict = NotImplemented  # contains cache of scaled images
    __raw_image_dict: dict = NotImplemented     # contains cache of raw images
    __request_threads_lock = threading.Lock()
    __request_threads = set()

    # create ImageCache TODO: load cache from .cache directory
    def __init__(self):
        self.__raw_image_dict = dict()
        self.__scaled_image_dict = dict()

    def get_image(self, url: str, callback, size=PROFILE_PHOTO):

        if not url.startswith("https"):
            url = "https:" + url

        key = (url, size)

        image = self.__scaled_image_dict.get(key, None)

        # if image is cached return instantly
        if image:
            callback(image)
            return

        work = dict()
        work[key] = [callback]

        # Thread for requesting and resizing images
        class RequestAndResizeThread(threading.Thread):

            __lock = threading.Lock()
            __work = dict()

            def __init__(self, not_cached: dict, raw_image_dict, scaled_image_dict, threads_set: set, lock: threading.Lock):
                super().__init__(name="RequestAndResize-Thread")

                self.__not_cached = not_cached
                self.__raw_image_dict = raw_image_dict
                self.__scaled_image_dict = scaled_image_dict
                self.__threads_set = threads_set
                self.__outer_lock = lock

            # add work to dict extend callbacks
            def add_work(self, work):
                self.__lock.acquire()
                for key in work:
                    old_callbacks = self.__work.get(key, [])
                    new_callbacks = work.get(key, [])

                    self.__work[key] = old_callbacks + new_callbacks

                self.__lock.release()

            # get one key-value-pair from dict
            def __get_key_callback(self):
                self.__lock.acquire()
                try:
                    key = next(iter(self.__work.keys()))
                    value = self.__work[key]
                    del self.__work[key]
                except StopIteration:
                    key, value = None, None
                self.__lock.release()
                return key, value

            def __scale_image(self, pixbuf, size):
                width, height = size
                if width <= 0 and height <= 0:
                    return pixbuf
                dim = pixbuf.props.width / pixbuf.props.height
                if dim > 1:
                    height = width / dim
                else:
                    width = height * dim

                return pixbuf.scale_simple(width, height, InterpType.BILINEAR)

            # do work
            def run(self):

                self.add_work(self.__not_cached)
                key, callbacks = self.__get_key_callback()
                while key:
                    # is already cached
                    scaled_image = self.__scaled_image_dict.get(key, None)
                    if scaled_image:
                        for callback in callbacks:
                            GLib.idle_add(callback, scaled_image)

                    # size not cached
                    else:
                        url, size = key
                        raw_image = self.__raw_image_dict.get(url, None)

                        # raw image is cached
                        if raw_image:
                            scaled = self.__scale_image(raw_image, size)
                            self.__scaled_image_dict[key] = scaled
                            for callback in callbacks:
                                GLib.idle_add(callback, scaled)

                        # raw image not cached
                        else:
                            response = requests.get(url)
                            input_stream = Gio.MemoryInputStream.new_from_data(response.content, None)
                            pixbuf = Pixbuf.new_from_stream(input_stream, None)
                            self.__raw_image_dict[url] = pixbuf
                            scaled = self.__scale_image(pixbuf, size)
                            self.__scaled_image_dict[key] = scaled
                            for callback in callbacks:
                                GLib.idle_add(callback, scaled)

                    # get next key
                    key, callbacks = self.__get_key_callback()

                self.__outer_lock.acquire()
                # start new thread, if new work was added before lock.acquire was called
                if self.__work:
                    req_thread = RequestAndResizeThread(self.__work, self.__raw_image_dict, self.__scaled_image_dict, self.__threads_set, self.__lock)
                    self.__threads_set.add(req_thread)
                    req_thread.start()

                self.__threads_set.remove(self)
                self.__outer_lock.release()

        self.__request_threads_lock.acquire()

        # if thread is running give your work to that thread
        if len(self.__request_threads):
            next(iter(self.__request_threads)).add_work(work)

        # if no thread is running, start new thread for getting image
        else:
            req_thread = RequestAndResizeThread(
                work,
                self.__raw_image_dict,
                self.__scaled_image_dict,
                self.__request_threads,
                self.__request_threads_lock
            )
            self.__request_threads.add(req_thread)
            req_thread.start()
        self.__request_threads_lock.release()

    def _debug(self):
        import sys
        print("scaled_image_dict size", len(self.__scaled_image_dict))
        print("mem: ", sys.getsizeof(self.__scaled_image_dict))
        print("__raw_image_dict size", len(self.__raw_image_dict))
        print("mem 2: ", sys.getsizeof(self.__raw_image_dict))
