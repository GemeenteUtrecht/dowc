import glob
import os

from doc.core.exceptions import FilesNotFoundInFolder


def find_document(path):
    # In case filename has changed
    dir_path = os.path.dirname(path)

    # Get files
    _fpath, file_extension = os.path.splitext(path)
    files_path = os.path.join(dir_path, f"*{file_extension}")
    filenames = glob.glob(files_path)

    # Get last modified file
    lmt_old = 0
    if filenames:
        for fn in filenames:
            lmt_new = os.path.getmtime(fn)
            if lmt_new > lmt_old:
                last_modified_file = fn

        return last_modified_file

    raise FilesNotFoundInFolder(f"No files were found in {dir_path}")
