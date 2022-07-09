import sys

import git_blame_project


def welcome_message():
    message = (
        f"Welcome to {git_blame_project.__appname__}!\n"
        f"{git_blame_project.__copyright__}\n"
        "All Rights Reserved\n\n"
    )
    sys.stdout.write(message)


def run():
    print("Running")


if __name__ == "__main__":
    welcome_message()
    run()
