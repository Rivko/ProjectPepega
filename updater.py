from urllib.request import urlopen


def get_latest():
    data = urlopen(
        "https://raw.githubusercontent.com/Rivko/ProjectPepega/main/.version"
    )
    for line in data:
        latest = line.decode()
        break
    return latest.rstrip("\n").rstrip("\r")


def check_for_updates(version):
    latest = get_latest()
    if latest > version:
        return latest
    return False


if __name__ == "__main__":
    check_for_updates(0.0)
