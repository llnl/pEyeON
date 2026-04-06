from box import box_auth, box_config
from boxsdk import Client

import pandas as pd
import os
import zipfile
import tarfile
import shutil


def get_box_client() -> Client:
    """
    authenticate with the box service
    """
    settings = box_config.get_box_settings()
    client = box_auth.authenticate_oauth(settings)
    return client


def list_box_items():
    settings = box_config.get_box_settings()
    client = get_box_client()

    data = pd.DataFrame(columns=["Filename", "ID", "Size", "Created", "Modified", "Uploaded by"])

    for item in client.folder(settings.FOLDER).get_items(limit=1000):
        # Get extra fields beyond the minimal.
        user = client.file(item.id).get(fields=["created_by", "size", "created_at", "modified_at"])
        if item.type == "file":
            new_data = {
                "Filename": item.name,
                "ID": item.id,
                "Size": user.size,
                "Created": user.created_at,
                "Modified": user.modified_at,
                "Uploaded by": user.created_by.name,
            }
            data = pd.concat([data, pd.DataFrame([new_data])], ignore_index=True)

        elif item.type == "folder":
            new_data = {
                "Filename": item.name,
                "ID": item.id,
                "Size": user.size,
                "Created": user.created_at,
                "Modified": user.modified_at,
                "Uploaded by": user.created_by.name,
            }
            data = pd.concat([data, pd.DataFrame([new_data])], ignore_index=True)
    print(data)
    return data


def delete_file(file: str):
    """
    delete target file by name or ID
    """
    settings = box_config.get_box_settings()
    client = get_box_client()

    if file.isdigit():
        # if the file is all digit assume they are trying to delete based on item id
        file_id = int(file)
        try:
            box_file = client.file(file_id).get()
            print(f"Deleting file '{box_file.name}' (ID: {file_id})")
            box_file.delete()
        except Exception as e:
            print(f"File with ID {file_id} not found or could not be deleted: {e}")
        return

    elif not file.isdigit():
        folder = client.folder(settings.FOLDER)
        file_name = file.split("/")[-1]  # need to split as file is path with path
        # Delete existing file with same name
        found = False
        for item in folder.get_items(limit=1000):
            if item.type == "file" and item.name == file_name:
                print(f"Deleting file '{file_name}' (ID: {item.id})")
                item.delete()
                found = True
                break
        if not found:
            print(f"File named '{file_name}' not found in folder.")
        return

    else:
        print("Invalid input type. Must be file name or ID")
        return


def compress_file(file: str, compression: str):
    #currently creates the archive in the directory the tool is ran from 
    # normalize path to remove trailing slashes for renaming/extensions
    file = os.path.normpath(file)
    # get just the directory or file name (not the full path or extension)
    base_name = os.path.basename(file).split(".")[0]

    if compression == "zip":
        output_path = base_name + ".zip"
        if os.path.isdir(file):
            shutil.make_archive(base_name, "zip", file)
        else:
            with zipfile.ZipFile(base_name + ".zip", "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file, arcname=os.path.basename(file))

    elif compression == "tar":
        output_path = base_name + ".tar"
        with tarfile.open(output_path, "w") as tarf:
            tarf.add(file, arcname=os.path.basename(file))

    elif compression == "tar.gz":
        output_path = base_name + ".tar.gz"
        with tarfile.open(output_path, "w:gz") as targzf:
            targzf.add(file, arcname=os.path.basename(file))
    else:
        print("Unsupported compression format. Use zip, tar, or tar.gz")
        return None
    
    return output_path


def upload(file: str, compression: str = None):
    """
    upload target file
    """
    allowed_ext = [".zip", ".tar", ".gz"]

    _, ext = os.path.splitext(file)

    # If file is not compressed and compression is specified, compress it.
    if ext.lower() not in allowed_ext:
        if compression:
            file = compress_file(file, compression)
            _, new_ext = os.path.splitext(file)
        else:
            print(
                "Please compress into one of the following formats: "
                f"{allowed_ext} or specify -z {allowed_ext} option."
            )
            return

    settings = box_config.get_box_settings()
    client = get_box_client()

    new_file = client.folder(settings.FOLDER).upload(file)
    print(f"Uploaded {file!r} as file ID {new_file.id}")
