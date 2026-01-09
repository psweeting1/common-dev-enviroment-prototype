import os

def delete_files(root_loc: str) -> None:
    """
    Deletes specific files in the given root directory if they exist.
    """
    files_to_delete = [
        '.commodities.yml',
        '.custom_provision.yml',
        '.docker-compose-file-list',
        '.db2_init.sql',
        '.postgres_init.sql'
    ]
    for filename in files_to_delete:
        file_path = os.path.join(root_loc, filename)
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass
