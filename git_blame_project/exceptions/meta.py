from git_blame_project import utils


class ExceptionMetaClass(type):
    """
    Meta class for :obj:`AbstractException` that uses the information defined
    in the `attributes` property to construct the exception class.

    Attributes defined on the base class will be merged with attributes defined
    on the current class, and these attributes are used to attach @property(s)
    to the current exception class that properly access the correct value
    associated with each attribute and return the formatted value.
    """
    def __new__(cls, name, bases, dct):
        attributes = [
            getattr(b, 'attributes', []) for b in bases
        ] + [dct.get('attributes', [])]
        dct['attributes'] = utils.merge_without_duplicates(
            *attributes,
            attr='name'
        )
        klass = super(ExceptionMetaClass, cls).__new__(cls, name, bases, dct)

        def establish_property(attr, original=utils.empty):
            """
            Establishes an @property on the :obj:`AbstractException` class
            that is responsible for accessing the value associated with the
            attribute and returning the formatted value.

            In the case that the attribute name is not already defined
            statically on the class (i.e. `original` is None) the @property
            is being added to the class for the first time.

            In the case that the attribute name is already defined
            statically on the class (i.e. `original` is not None) the @property
            is wrapping an existing @property or an existing static attribute.

            The value is accessed based on the following order of precedence:

            (1) The value is provided on initialization of the instance.
            (2) The value is already defined statically on the class.
            (3) The class defines a `default_<attribute>` attribute.
            (4) The :obj:`ExceptionAttribute` instance itself defaults a
                `default` value.

            Once the value is accessed based on the precedence defined above,
            it is formatted based on the configuration of the associated
            :obj:`ExceptionAttribute` instance and returned.
            """
            def attribute_property(instance):
                # Access the value associated with the attribute that was
                # provided on initialization.
                value = getattr(instance, f'_{attr.name}')
                # If the value was not provided on initialization, check if it
                # already exists on the class statically.
                if value is None and original is not utils.empty:
                    value = original
                    if isinstance(original, property):
                        value = original.fget(instance)
                # If the value is still None, use the default value associated
                # with the :obj:`ExceptionAttribute` instance.
                value = value or attr.default
                # If the value is still None, look for a default value defined
                # statically on the class.
                if value is None:
                    value = getattr(instance, f'default_{attr.name}', None)
                # Return the formatted value.
                return attr.format(value, instance)
            return attribute_property

        for attr in dct['attributes']:
            existing = getattr(klass, attr.name, utils.empty)
            if existing is utils.empty:
                setattr(klass, attr.name, property(establish_property(attr)))
            else:
                setattr(klass, attr.name,
                    property(establish_property(attr, original=existing)))
        return klass
