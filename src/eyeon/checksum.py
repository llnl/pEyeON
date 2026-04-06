import eyeon.observe as obs


def Checksum(file: str, algorithm: str, expected_checksum: str) -> dict:
    """
    Verify the checksum for a given file, return the results of the check
    """
    # Get the hash of the file
    fileHash = obs.Observe.create_hash(file, algorithm)
    print(f"{algorithm} hash: {fileHash}")
    print(f"expected hash: {expected_checksum}")

    # compare it to the expected checksum, returns true if match
    if fileHash == expected_checksum:
        print("Checksum verification pass")
        verified = True
    else:
        print(
            "Checksum verification fail, double check the expected checksum provided. ",
            "Otherwise file may have been modified",
        )
        verified = False

    return {
        "algorithm": algorithm,
        "expected": expected_checksum,
        "actual": fileHash,
        "verified": verified,
    }
