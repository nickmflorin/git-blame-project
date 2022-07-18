def standardize_extension(ext, include_prefix=True):
    ext = ext.lower()
    if not ext.startswith('.') and include_prefix:
        ext = f".{ext}"
    elif ext.startswith('.') and not include_prefix:
        return ext.split('.')[1]
    return ext


def standardize_extensions(exts, include_prefix=True):
    return [
        standardize_extension(ext, include_prefix=include_prefix)
        for ext in exts
    ]


def extensions_equal(ext1, ext2):
    return standardize_extension(ext1) == standardize_extension(ext2)
