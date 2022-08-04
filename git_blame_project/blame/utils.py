def tabulate_nested_attribute_data(attribute_data, formatter=None):

    def get_row(value, attribute_count, level_number=0, num_levels=0):
        row = []

        assert level_number <= num_levels
        for i in range(num_levels):
            if level_number == i:
                row.append(value)
            else:
                row.append("")

        if formatter is not None:
            return (
                row + [
                    attribute_count['count'],
                    formatter(attribute_count['count'])
                ],
                True
            )
        elif attribute_count['formatted'] is not None:
            return (
                row + [
                    attribute_count['count'],
                    attribute_count['formatted']
                ],
                True
            )
        return (row + [value, attribute_count['count']], False)

    formatting_included = False

    def get_rows(data_at_level, level_number=0, num_levels=0):
        rows = []
        for k, v in data_at_level.items():
            row, was_formatted = get_row(k, v, level_number=level_number, num_levels=num_levels)
            # if was_formatted is True and formatting_included is False:
            #     formatting_included = True
            rows.append(row)
            if len(v['children']) != 0:
                rows += get_rows(v['children'], level_number=level_number + 1, num_levels=num_levels)
        return rows

    data = attribute_data['data']
    num_levels = attribute_data['num_levels']
    return get_rows(data, num_levels=num_levels)

