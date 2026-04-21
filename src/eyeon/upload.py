from box import box_auth, box_config
from boxsdk import Client

import os
import shutil
import tarfile
import zipfile


BOX_LIST_HEADERS = ["Type", "Filename", "ID", "Size", "Created", "Modified", "Uploaded by"]
ALLOWED_ARCHIVE_EXTENSIONS = (".zip", ".tar", ".gz")


def get_box_client() -> Client:
    """
    authenticate with the box service
    """
    settings = box_config.get_box_settings()
    client = box_auth.authenticate_oauth(settings)
    return client


def _get_box_folder():
    settings = box_config.get_box_settings()
    client = get_box_client()
    return client, client.folder(settings.FOLDER)


def _get_item_details(client: Client, item):
    get_item = client.file if item.type == "file" else client.folder
    return get_item(item.id).get(fields=["created_by", "size", "created_at", "modified_at"])


def _print_box_rows(rows) -> None:
    widths = {header: len(header) for header in BOX_LIST_HEADERS}
    for row in rows:
        for header in BOX_LIST_HEADERS:
            widths[header] = max(widths[header], len(str(row[header])))

    header_line = "  ".join(
        f"{header:<{widths[header]}}" for header in BOX_LIST_HEADERS
    )
    separator_line = "  ".join("-" * widths[header] for header in BOX_LIST_HEADERS)
    print(header_line)
    print(separator_line)
    for row in rows:
        print(
            "  ".join(
                f"{str(row[header]):<{widths[header]}}" for header in BOX_LIST_HEADERS
            )
        )


def list_box_items():
    client, folder = _get_box_folder()

    rows = []
    for item in folder.get_items(limit=1000):
        details = _get_item_details(client, item)
        rows.append(
            {
                "Type": item.type,
                "Filename": item.name,
                "ID": item.id,
                "Size": details.size,
                "Created": details.created_at,
                "Modified": details.modified_at,
                "Uploaded by": details.created_by.name,
            }
        )

    if not rows:
        print("No items found in the configured Box folder.")
        return rows

    _print_box_rows(rows)
    return rows


def delete_file(file: str):
    """
    delete target file by name or ID
    """
    client, folder = _get_box_folder()

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

    file_name = os.path.basename(file)
    for item in folder.get_items(limit=1000):
        if item.type == "file" and item.name == file_name:
            print(f"Deleting file '{file_name}' (ID: {item.id})")
            item.delete()
            return

    print(f"File named '{file_name}' not found in folder.")


def compress_file(file: str, compression: str):
    # currently creates the archive in the directory the tool is run from
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
    _, ext = os.path.splitext(file)

    # If file is not compressed and compression is specified, compress it.
    if ext.lower() not in ALLOWED_ARCHIVE_EXTENSIONS:
        if compression:
            file = compress_file(file, compression)
            if file is None:
                return
        else:
            print(
                "Please compress into one of the following formats: "
                f"{list(ALLOWED_ARCHIVE_EXTENSIONS)} or specify -z <format>."
            )
            return

    _, folder = _get_box_folder()
    new_file = folder.upload(file)
    print(f"Uploaded {file!r} as file ID {new_file.id}")
