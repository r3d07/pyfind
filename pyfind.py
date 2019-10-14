#! /usr/bin/env python3

import argparse
import sys
import os
import re
import shutil


class FileObject:
    def __init__(self, abs_file_name, media_file=True):
        if not os.path.isfile(abs_file_name):
            raise FileNotFoundError('%s is not a valid file' % abs_file_name)

        self._abs_file_name = abs_file_name
        self._base_name = None
        self._extension = []
        self._size = None
        self._parse_file()

        # Media file fields
        self._abs_episode_name = None
        self._episode_name = None
        self._episode_id = None

        if media_file:
            self._parse_media_file()

    @property
    def abs_file_name(self):
        return self._abs_file_name

    @abs_file_name.setter
    def abs_file_name(self, abs_file_name, media_file=True):
        self._abs_file_name = abs_file_name
        self._parse_file()

        if media_file:
            self._parse_media_file()

    @property
    def base_name(self):
        return self._base_name

    @property
    def extension(self):
        return self._extension

    @property
    def size(self, human_readable=False):
        if human_readable:
            return self._human_size(self._size)
        return self._size

    @property
    def abs_episode_name(self):
        return self._abs_episode_name

    @property
    def episode_id(self):
        return self._episode_id

    @property
    def episode_name(self):
        return self._episode_name

    @staticmethod
    def _human_size(num, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0

        return "%.1f%s%s" % (num, 'Yi', suffix)

    def _parse_file(self):
        self._base_name = os.path.basename(self.abs_file_name)
        self._extension = os.path.splitext(self.abs_file_name)[1].strip('.')
        self._size = os.path.getsize(self.abs_file_name)

    def _parse_media_file(self):
        # Get episode specific names and information from the file name.
        self._abs_episode_name = os.path.splitext(self.abs_file_name)[0]
        self._episode_id, self._episode_name = self.base_name.rsplit(' - ')[1:3]


class DuplicateFinder:
    def __init__(self, directory='.', depth=0, valid_extensions=None):
        """

        :param directory:
        :param depth:
        :param valid_extensions:
        """
        if os.path.isdir(directory) is False:
            raise NotADirectoryError('%s is not a valid directory' % directory)

        self._directory = directory
        self._recursion_depth = depth
        self._valid_extensions = valid_extensions

        self._files = []
        self._uncategorized_episodes = []
        self._dup_episodes_diff_ext = []
        self._found_ext = set()
        self._dup_episodes_same_ext = []

        self._all_yes = False
        self._all_no = False

        self._regex = re.compile(r"^([yY]|[nN])$")

        return

    @property
    def directory(self):
        return self._directory

    @property
    def valid_extensions(self):
        return self._valid_extensions

    @staticmethod
    def _clear_screen():
        print('\n' * 100)
        os.system('cls' if os.name == 'nt' else 'clear')

        return

    def _yes_or_no(self, message):
        """

        :return:
        """
        while True:
            response = input('%s [Y/N] ' % message)

            if re.match(self._regex, response) is not None:
                break

        if response.upper() == 'Y':
            return True

        return False

    def scan_directory(self):
        """

        :return:
        """
        for root, dirs, files in os.walk(self.directory):
            if root[len(self.directory):].count(os.sep) > self._recursion_depth:
                break

            for file in files:
                if file == '.DS_Store' or file == '._.DS_Store':
                    continue

                file_object = FileObject(os.path.join(root, file))

                # Ensure we are only concerning ourselves with the file types that we care about
                if file_object.extension not in self.valid_extensions:
                    print('Valid: %s \t Actual: %s' % (self.valid_extensions, file_object.extension))
                    continue

                # Populate the list of duplicates with the same extension
                regex = re.compile(r'^.*\(copy [0-9]\)$')
                if re.match(regex, file_object.abs_episode_name) is not None:
                    self._dup_episodes_same_ext.append(file_object)
                    continue

                # Filter the unknown episodes out
                regex = re.compile(r'[sS][0-9]{2}[eE][0-9]{2}')
                if re.match(regex, file_object.episode_id) is None:
                    self._uncategorized_episodes.append(file_object)

                # Populate the list of duplicate episodes with different extensions
                for _file in self._files:
                    if file_object.abs_episode_name != _file.abs_episode_name:
                        continue

                    # Append both extensions to our set of found extensions.
                    self._found_ext.add(file_object.extension)
                    self._found_ext.add(_file.extension)
                    self._dup_episodes_diff_ext.append((file_object, _file))

                # Keep track of all files that we have processed
                self._files.append(file_object)

        return

    def del_dups_diff_ext(self):
        """

        :return:
        """
        # If the list is empty, just return
        if len(self._dup_episodes_diff_ext) == 0:
            return

        self._clear_screen()

        for duplicates in self._dup_episodes_diff_ext:
            for episode in duplicates:
                print('%s' % episode.abs_file_name)

        print('Found %d files with the same name, but different extension.' % len(self._dup_episodes_diff_ext))

        while True:
            response = input('Which extensions would you like deleted %s? ' % self._found_ext)
            exts_to_delete = response.split(',')
            exts_to_delete = [ext.strip() for ext in exts_to_delete]

            if any(ext in exts_to_delete for ext in self._found_ext):
                break

        self._clear_screen()
        deletion_list = []
        for duplicates in self._dup_episodes_diff_ext:
            for episode in duplicates:
                if episode.extension in exts_to_delete:
                    deletion_list.append(episode)
                    print(episode.abs_file_name)

        response = self._yes_or_no('Do you want to delete these files? ')

        if response is True:
            for episode in deletion_list:
                os.remove(episode.abs_file_name)

        return

    def del_dups_same_ext(self):
        """

        :return:
        """
        # If the list is empty, just return
        if len(self._dup_episodes_same_ext) == 0:
            return

        self._clear_screen()

        for episode in self._dup_episodes_same_ext:
            print(episode.abs_file_name)

        print('Found %d duplicate files' % len(self._dup_episodes_same_ext))
        response = self._yes_or_no('Do you want to delete these files? ')

        if response is True:
            for episode in self._dup_episodes_same_ext:
                os.remove(episode.abs_file_name)

        return

    def mv_uncategorized(self, dest_dir):
        """

        :return:
        """
        # If the list is empty, just return
        if len(self._uncategorized_episodes) == 0:
            return

        self._clear_screen()

        for episode in self._uncategorized_episodes:
            print(episode.abs_file_name)

        print('Found %d uncategorized episodes' % len(self._uncategorized_episodes))
        response = self._yes_or_no('Do you want to move these files? ')

        if response is True:
            for episode in self._uncategorized_episodes:
                shutil.move(episode.abs_file_name, dest_dir)

        return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('base_directory', default='.', nargs='?',
                        help='The directory from which the search should start')
    parser.add_argument('-f', '--filter-extensions', nargs='+', default='mkv,ts',
                        help='Specify the valid extensions in a comma separated list. Prefix the first extension '
                             'with a + to append to the existing defaults')
    parser.add_argument('-r', '--recursion-depth', default=0, type=int,
                        help='Specifies how many sub-folders to recurse into. -1 is infinite.')
    parser.add_argument('--del-dups-diff-ext', action='store_true', dest='dup_diff',
                        help='Delete duplicate episodes that have different extensions. Specify a comma-separated '
                             'list of extensions of files to delete')
    parser.add_argument('--del-dups-same-ext', action='store_true', dest='dup_same',
                        help='Delete duplicate episodes that have the same extension')
    parser.add_argument('--move-uncategorized', nargs='+', dest='mv_uncat',
                        help='Move all uncategorized episodes to this directory')
    args = parser.parse_args()

    mv_uncat = args.mv_uncat[0]
    base_directory = args.base_directory
    recursion_depth = args.recursion_depth
    filter_extensions = args.filter_extensions

    # Make the output directory if needed
    if mv_uncat is not None:
        os.makedirs(mv_uncat, exist_ok=True)

    try:
        df = DuplicateFinder(base_directory, recursion_depth, filter_extensions)
        df.scan_directory()

        if args.dup_diff:
            df.del_dups_diff_ext()

        if args.dup_same:
            df.del_dups_same_ext()

        if args.mv_uncat is not None:
            df.mv_uncategorized(mv_uncat)

    except KeyboardInterrupt:
        print('\nExiting...')

    sys.exit(0)
