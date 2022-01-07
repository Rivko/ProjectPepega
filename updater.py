import urllib.error
from urllib.request import urlopen

from config import __VERSION__


def get_latest():
    data = urlopen(
        "https://raw.githubusercontent.com/Rivko/ProjectPepega/main/.version"
    )
    for line in data:
        latest = line.decode()
        break
    return latest.rstrip("\n").rstrip("\r")


def check_for_updates(version):
    try:
        latest = float(get_latest())
        if latest > version:
            return latest
        return False
    except urllib.error.HTTPError as e:
        return False


if __name__ == "__main__":
    github_updated = check_for_updates(__VERSION__)
    if github_updated:
        print(f"There is a new update {github_updated}")
    else:
        print("Version is up to date")
