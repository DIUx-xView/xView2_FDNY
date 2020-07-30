import fnmatch
import glob
import os
import re

import inference
# TODO: Clean up directory structure
# TODO: gather input and output files from folders --> create pre and post mosaic --> create intersection --> get chips from intersection for pre/post --> extract geotransform per chip --> convert to PNG/JPG --> hand off to inference --> georef outputs

PRE_DIR = 'test_dir/input/pre'
POST_DIR = 'test_dir/input/post'
OUTPUT_DIR = 'test_dir/output'


class Files(object):

    def __init__(self, pre, post):
        self.pre = os.path.abspath(os.path.join(PRE_DIR, pre))
        self.post = os.path.abspath(os.path.join(POST_DIR, post))
        self.base_num = self.check_extent()
        self.output_loc = os.path.abspath(os.path.join(OUTPUT_DIR, 'loc', f'{self.base_num}_loc.png'))
        self.output_dmg = os.path.abspath(os.path.join(OUTPUT_DIR, 'dmg', f'{self.base_num}_dmg.png'))
        self.opts = inference.Options(self.pre, self.post, self.output_loc, self.output_dmg)

    def check_extent(self):
        """
        Check that our pre and post are the same extent
        Note:
        Currently only checks that the number sequence matches for both the pre and post images.
        :return: True if numbers match
        """
        pre_base = ''.join([digit for digit in self.pre if digit.isdigit()])
        post_base = ''.join([digit for digit in self.post if digit.isdigit()])
        if pre_base == post_base:
            return pre_base

    def infer(self):
        """
        Passes object to inference.
        :return: True if successful
        """

        try:
            # TODO: Not sure why opts seems to be a list.
            inference.main(self.opts[0])
        except Exception as e:
            print(f'File: {self.pre}. Error: {e}')
            return False

        return True

    def georef(self):
        pass


def main():

    pre_files = sorted(get_files(PRE_DIR))
    post_files = sorted(get_files(POST_DIR))
    string_len_check(pre_files, post_files)
    file_objs = []
    for pre, post in zip(pre_files, post_files):
        file_objs.append(Files(pre, post))

    for obj in file_objs:
        obj.infer()


def make_output_structure(path):
    pass


def get_files(dirname, extensions=['.png', '.tif'], recursive=True):
    files = glob.glob(f'{dirname}/**', recursive=recursive)
    match = [file for file in files if os.path.splitext(file)[1].lower() in extensions]
    return match


def string_len_check(pre, post):

    if len(pre) != len(post):
        # TODO: Add some helpful info on why this failed
        return False

    return True


if __name__ == '__main__':
    main()
