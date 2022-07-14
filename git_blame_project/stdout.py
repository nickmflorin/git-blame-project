import click


class TerminalCodes:
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    @classmethod
    def underline(cls, text):
        return cls.UNDERLINE + text + cls.END

    @classmethod
    def bold(cls, text):
        return cls.BOLD + text + cls.END


def info(message, prefix=None):
    if prefix:
        prefix = TerminalCodes.bold("Not Supported:")
        click.secho(f"{prefix} {message}", fg="blue")
    else:
        click.secho(message, fg="blue")


def not_supported(message):
    prefix = TerminalCodes.bold("Not Supported:")
    click.secho(f"{prefix} {message}", fg="blue")


def warning(message):
    prefix = TerminalCodes.bold("Warning:")
    click.secho(f"{prefix} {message}", fg="yellow")


def error(message):
    prefix = TerminalCodes.bold("Error:")
    click.secho(f"{prefix} {message}", fg="red")
