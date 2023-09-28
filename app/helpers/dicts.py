"""Helper functions for working with dicts."""

import re


class QueryDict(dict):
    """Helper class to query and update a dict more conveniently."""

    def __getitem__(self, key):
        """Dunder method to get value at by ["..."] syntax."""
        return self.get(key)

    def get(self, path, default=None, separator="/", escape_sequence="''"):
        """
        Return the value at the given path.

        If the path cannot be found, the default value is returned.

        Keys in the path can be surrounded by the given escape sequence to treat separators as
        regular chars instead of separators. For instance, "abc/''def/ghi''" will return the value
        at abc -> def/ghi instead of abc -> def -> ghi (assuming default values for parameters
        'separator' and 'escape_sequence' are used).

        Optionally, a path can start with a separator ("/" by default). If path is only the
        separator, the entire dict is returned.
        """
        if not path:
            return default

        if path == separator:
            return dict(self)

        keys_from_path = QueryDict._get_keys_from_path(path, separator, escape_sequence)

        path_length = len(keys_from_path)
        for i, key_from_path in enumerate(keys_from_path):
            if i == 0:
                parent_element = dict.get(self, key_from_path, default)
                continue
            if i > 0 and i < path_length:
                try:
                    parent_element = parent_element[key_from_path]
                    continue
                except:
                    return default
        return parent_element

    def set(self, path, value, separator="/", escape_sequence="''"):
        """
        Set the given value at the given path.

        Path items which do not exist yet, will be added.

        Keys in the path can be surrounded by the given escape sequence to treat separators as
        regular chars instead of separators. For instance, "abc/''def/ghi''" will set the value at
        abc -> def/ghi instead of abc -> def -> ghi (assuming default values for parameters
        'separator' and 'escape_sequence' are used).

        Optionally, a path can start with a separator ("/" by default). If path is only the
        separator, the entire dict
        is set.
        """
        keys_from_path = QueryDict._get_keys_from_path(path, separator, escape_sequence)
        parent_element = self
        is_last_element_in_path = False
        for i, key_from_path in enumerate(keys_from_path):
            is_last_element_in_path = i == len(keys_from_path) - 1
            if not key_from_path in parent_element:
                parent_element[key_from_path] = {}
            if not is_last_element_in_path and not isinstance(parent_element[key_from_path], dict):
                raise ValueError(
                    (
                        "Cannot set value. All items on the way to the last element must be of "
                        "type dict to avoid that data is unintentionally overwritten."
                    )
                )
            if not is_last_element_in_path:
                parent_element = parent_element[key_from_path]
            else:
                parent_element[key_from_path] = value

    @staticmethod
    def get_last_item_from_path(path, separator="/", escape_sequence="''"):
        """Return the last item from the given path."""
        return QueryDict._get_keys_from_path(path, separator, escape_sequence)[-1]

    @staticmethod
    def _get_keys_from_path(path, separator, escape_sequence):
        """Get the different keys from the given path."""
        if path.startswith("/"):
            path = path[1:]

        escaped_escape_sequence = re.escape(escape_sequence)
        keys_from_path = [
            re.sub(
                rf"^{escaped_escape_sequence}|{escaped_escape_sequence}$",
                "",
                element.replace(chr(0), separator),
            )
            for element in re.sub(
                rf"{escaped_escape_sequence}.*?{escaped_escape_sequence}",
                lambda match: match.group().replace(separator, chr(0)),
                path,
            ).split(separator)
        ]
        return keys_from_path
