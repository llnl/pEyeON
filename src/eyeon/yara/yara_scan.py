import sys
import argparse
from pathlib import Path
import yara # using yara-python


def compile_yara_rules(rule_path: Path) -> yara.Rules:
    """
    Compile YARA rules from a .yar or directory.
    """
    if not rule_path.exists():
        raise FileNotFoundError(f"Rule file not found: {rule_path}")
    return yara.compile(filepath=str(rule_path))


def scan_file_with_rules(rules: yara.Rules, target_path: Path):
    """
    Scan a file with compiled YARA rules and return matches.
    """
    if not target_path.exists():
        raise FileNotFoundError(f"Target file not found: {target_path}")
    matches = rules.match(filepath=str(target_path), timeout=60)
    return matches


def print_matches(matches):
    """
    Pretty print YARA match results.
    """
    if not matches:
        print("No YARA matches found.")
        return

    for match in matches:
        print(f"Matched rule: {match.rule}")
        if match.namespace:
            print(f"  Namespace: {match.namespace}")

        if match.meta:
            print("  Meta:")
            for k, v in match.meta.items():
                print(f"    {k}: {v}")

        if match.strings:
            print("  Strings:")
            for (offset, identifier, data) in match.strings:
                preview = data[:32]
                try:
                    preview_str = preview.decode(errors="replace")
                except Exception:
                    preview_str = repr(preview)
                print(f"    {identifier} at offset {offset}, preview: {preview_str!r}")

        print("-" * 60)

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Scan a binary with YARA rules."
    )
    parser.add_argument(
        "-r",
        "--rules",
        required=True,
        help="Path to YARA rules file (.yar)"
    )
    parser.add_argument(
        "target",
        help="Path to target binary file to scan"
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    

    rule_file = Path(args.rules)
    target_file = Path(args.target)

    try:
        rules = compile_yara_rules(rule_file)
        matches = scan_file_with_rules(rules, target_file)
        print_matches(matches)
    except yara.TimeoutError:
        print("YARA scan timed out.")
        sys.exit(2)
    except yara.Error as e:
        print(f"YARA error: {e}")
        sys.exit(3)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(4)


if __name__ == "__main__":
    main()