import dropbox

from trade_job.submodules import properties

DROPBOX_ACCESS_TOKEN = properties.dropbox_access_token


class DropboxAPI:

    def __init__(self):

        self.client = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

    def get_files_list(self, path):

        res = self.client.files_list_folder(path, recursive=True)
        self.__get_files_recursive(res)

    def __get_files_recursive(self, _res):
        for entry in _res.entries:
            print(entry.path_display)

        if _res.has_more:
            res2 = self.client.files_list_folder_continue(_res.cursor)
            self.__get_files_recursive(res2)

    def get_file_data(self, path):

        res = self.client.files_download(path)
        return res

    def download(self, from_path, to_path):

        self.client.files_download_to_file(to_path, from_path)
