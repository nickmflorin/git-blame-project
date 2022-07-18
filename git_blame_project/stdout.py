import click


class Terminal:
    BOLD = '\033[1m'
    END = '\033[0m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[33m'
    RED = '\033[31m'

    @classmethod
    def color(cls, text, color=None, reset=False):
        if color:
            if not color.startswith("\\"):
                if not hasattr(cls, color.upper()):
                    raise LookupError(f"Invalid color {color} provided.")
                color = getattr(cls, color.upper())
            text = color + text
        if reset:
            return text + cls.END
        return text

    @classmethod
    def bold(cls, text, color=None, reset=False):
        if color is not None:
            text = cls.color(text, color, reset=True)
        if reset:
            return cls.BOLD + text + cls.END
        return cls.BOLD + text

    @classmethod
    def color_with_prefix(cls, text, prefix, color=None):
        if not prefix.endswith(":"):
            prefix = f"{prefix}:"
        prefix = cls.bold(prefix, color=color, reset=True)
        text = cls.color(text, color=color, reset=True)
        return f"{prefix} {text}"

    @classmethod
    def message(cls, text, prefix=None, color=None):
        if prefix is not None:
            return cls.color_with_prefix(text, prefix, color=color)
        return cls.color(text, color=color, reset=True)


def info(message, prefix=None):
    msg = Terminal.message(message, prefix=prefix, color="blue")
    click.echo(msg)


def not_supported(message):
    return info(message, prefix="Not Supported")


def warning(message):
    msg = Terminal.message(message, prefix="Warning", color="yellow")
    click.echo(msg)


def error(message):
    msg = Terminal.message(message, prefix="Error", color="red")
    click.echo(msg)


def log(message):
    # TODO: We need to implement a logging system.
    warning(message)
