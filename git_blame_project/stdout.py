import copy
import click

from git_blame_project.utils import ensure_iterable, humanize_list, empty


class Terminal:
    BOLD = '\033[1m'
    END = '\033[0m'
    BLUE = '\033[34m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[33m'
    RED = '\033[31m'

    LEVEL_COLOR_MAP = {
        'warning': YELLOW,
        'error': RED,
        'success': GREEN,
        'info': BLUE
    }

    BOLD_STYLE = "bold"
    STYLES = [BOLD_STYLE]
    STYLE_METHOD_MAP = {
        'bold': 'bold'
    }

    @classmethod
    def reset(cls, text, reset=True):
        if reset:
            return text + cls.END
        return text

    @classmethod
    def conditionally_join(cls, strings):
        filtered = [value for value in strings if value is not None]
        return " ".join(filtered)

    @classmethod
    def get_styles(cls, style=None, bold=empty):
        style = style or []
        styles = ensure_iterable(style)

        if bold is True and cls.BOLD_STYLE not in styles:
            styles += [cls.BOLD_STYLE]
        elif bold is False and cls.BOLD_STYLE in styles:
            styles = [s for s in styles if s != cls.BOLD_STYLE]

        invalid_styles = []
        for s in styles:
            if s not in cls.STYLES:
                invalid_styles.append(s)
        if invalid_styles:
            if len(invalid_styles) == 1:
                raise ValueError(
                    f"The provided style {styles[0]} is invalid.")
            humanized = humanize_list(invalid_styles)
            raise ValueError(f"The provided styles {humanized} are invalid.")
        return styles

    @classmethod
    def apply_style(cls, text, style, reset=False):
        # This should be prevented before we get to this method.
        assert style in cls.STYLES, f"The style {style} is invalid."
        return cls.STYLE_METHOD_MAP[style](text, reset=reset)

    @classmethod
    def apply_styles(cls, text, style=None, bold=empty, reset=False):
        styles = cls.get_styles(style=style, bold=bold)
        for s in styles:
            text = cls.apply_style(text, s, reset=False)
        return cls.reset(text, reset=reset)

    @classmethod
    def get_color(cls, color=None, level=None):
        if color is not None:
            if not color.startswith("\\"):
                if not hasattr(cls, color.upper()):
                    raise LookupError(f"Invalid color {color} provided.")
                color = getattr(cls, color.upper())
            return color
        elif level is not None:
            if level.lower() not in cls.LEVEL_COLOR_MAP:
                raise LookupError(f"Invalid level provided: {level}.")
            return cls.LEVEL_COLOR_MAP[level.lower()]
        return None

    @classmethod
    def get_prefix(cls, prefix=None, color=None, level=None):
        if prefix is not None:
            if not prefix.endswith(":"):
                prefix = f"{prefix}:"
            prefix = cls.bold(prefix, color=color, level=level, reset=True)
            return prefix
        return None

    @classmethod
    def get_indent_prefix(cls, indent=None):
        if indent is not None:
            return "-" * 2 * indent + ">"
        return None

    @classmethod
    def color(cls, text, color=None, level=None, reset=False):
        color = cls.get_color(color=color, level=level)
        if color is not None:
            text = color + text
            # Reset is only applicable if the color was applied.
            return cls.reset(text, reset=reset)
        return text

    @classmethod
    def bold(cls, text, color=None, level=None, reset=False):
        text = cls.color(text, color=color, level=level, reset=True)
        return cls.reset(cls.BOLD + text, reset=reset)

    @classmethod
    def style(cls, text, color=None, level=None, style=None, bold=True,
            reset=True):
        text = cls.color(text, color=color, level=level, reset=False)
        text = cls.apply_styles(text, style=style, reset=False, bold=bold)
        return cls.reset(text, reset=reset)

    @classmethod
    def message(cls, text, prefix=None, color=None, level=None, indent=None,
            style=None, bold=empty):
        return cls.conditionally_join([
            cls.get_indent_prefix(indent=indent),
            cls.get_prefix(prefix=prefix, color=color, level=level),
            cls.style(text, color=color, level=level, style=style, bold=bold,
                reset=True)
        ])


class MessageFn:
    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def __call__(self, *args, **kwargs):
        display = kwargs.pop('display', True)

        # The original configuration that was used to create the MessageFn
        # is overridden by any configuration values provided dynamically.
        base_kwargs = copy.deepcopy(self._kwargs)
        base_kwargs.update(**kwargs)
        if args:
            # If arguments are provided, the first argument must be the string
            # message.  If this is the case, then we are calling the MessageFn
            # in an attempt to output the provided string message to the
            # terminal.
            if len(args) != 1 or not isinstance(args[0], str):
                raise TypeError(f"Inproper call of {self.__class__}.")
            data = Terminal.message(args[0], **base_kwargs)
            if display is True:
                click.echo(data)
            return data
        else:
            # If no arguments are provided, this means that we are creating a
            # new instance of the MessageFn class with new keyword arguments.
            return self.__class__(**base_kwargs)

    def display(self, message, **kwargs):
        if 'display' in kwargs:
            raise TypeError(
                "The `display` parameter is redundant for this method.")
        return self(message, display=True, **kwargs)

    def format(self, message, **kwargs):
        if 'display' in kwargs:
            raise TypeError(
                "The `display` parameter is redundant for this method.")
        return self(message, display=False, **kwargs)


class stdout:
    bold = MessageFn(style=["bold"])
    info = MessageFn(level="info")
    not_supported = info(prefix="Not Supported")
    warning = MessageFn(level="warning", prefix="Warning")
    error = MessageFn(level="error", prefix="Error")
    # TODO: We need to implement a logging system.
    log = warning
