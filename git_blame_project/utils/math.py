def count_by_nested_attributes(data, *attrs, **kwargs):
    """
    Counts the number of objects present in the data based on values associated
    with the provided attributes.  The final returned data can optionally
    include formatted values.

    Parameters:
    ----------
    data: :obj:`list` or :obj:`tuple` or :obj:`lambda`
        Either an iterable of object instances or a function that returns an
        iterable of object instances.  For the provided attributes, the number
        of times each attribute value is seen over the instances defined by
        this parameter will be counted.

    *attrs: :obj:`str`
        The string attributes that will be counted on the provided object
        instances.  If multiple attributes are provided, the counts will be
        nested.

        For example, if the attributes are ('size', 'color'), the values of
        'size' on all of the provided instances will be counted, and for each
        distinct value, the number of times a given 'color' appears will be
        counted.  The resulting :obj:`dict` instance may look like the
        following:

        >>> {
        >>>     "large": {
        >>>         "count": 10,
        >>>         "formatted": "10%",
        >>>         "children": {
        >>>             "blue": {
        >>>                 "count": 4,
        >>>                 "formatted": "20%"
        >>>             },
        >>>             "red": {
        >>>                 "count": 6,
        >>>                 "formatted": "30%"
        >>>             }
        >>>         }
        >>>     },
        >>>     "small": {...}
        >>> }

    formatter: :obj:`lambda` or :obj:`dict` (optional)
        A formatting function that should be applied to the count values of
        each nested attribute.  If the formatter differs for each attribute,
        it can be provided as an :obj:`dict` instance indexed by the attribute
        it applies to.

        Default: None

    attr_formatter: :obj:`lambda` or :obj:`dict` (optional)
        A formatting function that should be applied to the attribute name
        for each nested attribute.  If the formatter differs for each
        attribute, it can be provided as a :obj:`dict` instance indexed by the
        attribute it applies to.

        Default: None
    """
    from git_blame_project import exceptions

    def get_attr_formatter(attr):
        # The attribute formatter may be a dictionary indexed by the
        # attribute name.
        attr_formatter = kwargs.get('attr_formatter', None)
        if attr_formatter is not None and isinstance(attr_formatter, dict):
            return attr_formatter.get(attr, None)
        return attr_formatter

    def get_value_formatter(attr):
        # The value formatter may be a dictionary indexed by the
        # attribute name.
        formatter = kwargs.get('formatter', None)
        if formatter is not None and isinstance(formatter, dict):
            return formatter.get(attr, None)
        return formatter

    def fmt(formatter, v):
        if formatter is not None:
            return formatter(v)
        return v

    def get_instance_value(obj, attr):
        return fmt(get_attr_formatter(attr), getattr(obj, attr))

    def format_count(attr, value):
        return fmt(get_value_formatter(attr), value)

    if len(attrs) == 0:
        raise exceptions.ImproperUsageError(
            message=f"Expected at least one attribute to be provided, "
            "but received 0."
        )

    non_string_attrs = [a for a in attrs if not isinstance(a, str)]
    if non_string_attrs:
        raise exceptions.InvalidParamError(
            param='attrs',
            value=non_string_attrs,
            valid_types=(str,)
        )

    def perform_count(current, line, *attributes):
        if len(attributes) == 0:
            return current
        attr_value = get_instance_value(line, attributes[0])
        current.setdefault(attr_value, {'count': 0, 'children': {}})
        current[attr_value]['count'] += 1
        perform_count(current[attr_value]['children'], line, *attributes[1:])

    def format_final_data(count):
        final_data = {}
        for k, v in count.items():
            final_data[k] = {
                'formatted': format_count(k, v['count']),
                'count': v['count'],
                'children': []
            }
            if len(v['children']) != 0:
                final_data[k]['children'] = format_final_data(v['children'])
        return final_data

    count = {}

    def gen():
        if hasattr(data, '__call__'):
            for datum in data():
                yield datum
        else:
            for datum in data:
                yield datum

    for line in gen():
        perform_count(count, line, *attrs)

    return {'data': format_final_data(count), 'num_levels': len(attrs)}
