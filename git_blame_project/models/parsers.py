from git_blame_project import exceptions, utils


def parse_param(cls, param, *args, **kwargs):
    """
    Parses a parameter from either the arguments or the keyword arguments
    allowing for a more flexible function signature.  Validates the presence
    of the parameter and type of the parameter based on the optionally provided
    `required` parameter and the optionally provided `valid_types` parameter.
    """
    required = kwargs.pop('required', True)
    valid_types = kwargs.pop('valid_types', None)

    if len(args) == 1:
        value = args[0]
    elif param in kwargs:
        value = kwargs[param]
    elif required:
        raise exceptions.ImproperInitializationError(
            cls=cls,
            message=f"The parameter {param} is required."
        )
    else:
        return None

    if valid_types and not isinstance(value, valid_types):
        if len(valid_types) == 1:
            raise exceptions.ImproperInitializationError(
                cls=cls,
                message=(
                    f"Expected type {valid_types[0]} for {param}, but "
                    f"received {type(value)}."
                )
            )
        humanized = utils.humanize_list(valid_types, conjunction="or")
        raise exceptions.ImproperInitializationError(
            cls=cls,
            message=(
                f"Expected type {humanized} for {param}, but received "
                f"{type(value)}."
            )
        )
    return value
