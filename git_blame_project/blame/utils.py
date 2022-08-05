import collections


TabularData = collections.namedtuple('TabularData', ['header', 'rows'])

NestedAttributeData = collections.namedtuple(
    'NestedAttributeData',
    ['attributes', 'data']
)


def count_by_nested_attributes(data, *attrs):
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
    """
    def perform_count(line, current, *attributes):
        attr_value = getattr(line, attributes[0].name)
        current.setdefault(attr_value, {'count': 0, 'children': {}})
        current[attr_value]['count'] += 1
        if len(attributes) > 1:
            perform_count(
                line,
                current[attr_value]['children'],
                *attributes[1:],
            )

    def format_final_data(count):
        final_data = {}
        for k, v in count.items():
            final_data[k] = {
                'count': v['count'],
                'children': []
            }
            if len(v['children']) != 0:
                final_data[k]['children'] = format_final_data(v['children'])
        return final_data

    count = {}
    if hasattr(data, '__call__'):
        for datum in data():
            perform_count(datum, count, *attrs)
    else:
        for datum in data:
            perform_count(datum, count, *attrs)

    return NestedAttributeData(
        data=format_final_data(count),
        attributes=list(attrs)
    )


def tabulate_nested_attribute_data(data, *attrs, formatter=None,
        formatted_title="Formatted"):
    attribute_data = count_by_nested_attributes(data, *attrs)

    def get_row(value, attribute_count, level_number=0):
        row = []
        assert level_number <= len(attribute_data.attributes), \
            f"The current level number {level_number} should always be less " \
            f"than the number of attributes, {len(attribute_data.attributes)}."
        # Add the cells at the beginning of the row that display the attribute
        # at the current nested level.
        for i in range(len(attribute_data.attributes)):
            if level_number == i:
                row.append(value)
            else:
                row.append("")
        if formatter is not None:
            return row + [
                attribute_count['count'],
                formatter(attribute_count['count'])
            ]
        return row + [attribute_count['count']]

    def get_rows(data, level_number=0):
        rows = []
        for k, v in data.items():
            rows.append(get_row(k, v, level_number=level_number))
            if len(v['children']) != 0:
                rows += get_rows(v['children'], level_number=level_number + 1)
        return rows

    header = [attr.title for attr in attrs] + ["Num Lines"]
    if formatter is not None:
        header += [formatted_title]

    print(attribute_data.data)
    rows = get_rows(data=attribute_data.data)
    print(rows)
    return TabularData(
        header=header,
        rows=rows
    )
