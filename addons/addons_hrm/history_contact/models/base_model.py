import collections
import contextlib
import functools
import warnings
from collections import defaultdict
from operator import itemgetter

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from odoo.exceptions import MissingError

from odoo import models

# Suppress specific warning
warnings.filterwarnings("ignore", category=UserWarning,
                        message="You provided Unicode markup but also provided a value for from_encoding.")


def cleanhtml(raw_html):
    # Check if the input looks like a file path
    if "\n" not in raw_html and raw_html.endswith(".html"):
        # Assuming raw_html is a file path, open the file and read its content
        with open(raw_html, 'r', encoding='utf-8') as file:
            html_content = file.read()
    else:
        # If raw_html doesn't look like a file path, use it as HTML content
        html_content = raw_html

    # Use BeautifulSoup to parse HTML
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", MarkupResemblesLocatorWarning)
        soup = BeautifulSoup(html_content, 'html.parser', from_encoding='utf-8')
    cleantext = soup.get_text(separator='\n')
    return cleantext


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _read_format(self, fnames, load='_classic_read'):
        data = [(record, {'id': record._ids[0]}) for record in self]
        use_name_get = (load == '_classic_read')
        for name in fnames:
            convert = self._fields[name].convert_to_read
            for record, vals in data:
                if not vals:
                    continue
                try:
                    if self._context.get('update_partner'):
                        if convert(record[name], record, use_name_get):
                            vals[name] = convert(record[name], record, use_name_get)
                    else:
                        vals[name] = convert(record[name], record, use_name_get)
                except MissingError:
                    vals.clear()
        result = [vals for record, vals in data if vals]

        return result

    def _export_rows(self, fields, *, _is_toplevel_call=True):
        """ Export fields of the records in ``self``.

        :param list fields: list of lists of fields to traverse
        :param bool _is_toplevel_call:
            used when recursing, avoid using when calling from outside
        :return: list of lists of corresponding values
        """
        import_compatible = self.env.context.get('import_compat', True)
        lines = []
        if self._name == 'project.task' and ['display_name'] not in fields:
            fields += [['base_url']]
        def splittor(rs):
            """ Splits the self recordset in batches of 1000 (to avoid
            entire-recordset-prefetch-effects) & removes the previous batch
            from the cache after it's been iterated in full
            """
            for idx in range(0, len(rs), 1000):
                sub = rs[idx:idx + 1000]
                for rec in sub:
                    yield rec
                sub.invalidate_recordset()

        if not _is_toplevel_call:
            splittor = lambda rs: rs

        # memory stable but ends up prefetching 275 fields (???)
        for record in splittor(self):
            # main line of record, initially empty
            current = [''] * len(fields)
            lines.append(current)

            # list of primary fields followed by secondary field(s)
            primary_done = []

            # process column by column
            for i, path in enumerate(fields):
                if not path:
                    continue

                name = path[0]
                if name in primary_done:
                    continue

                if name == '.id':
                    current[i] = str(record.id)
                elif name == 'id':
                    current[i] = (record._name, record.id)
                else:
                    field = record._fields[name]
                    value = record[name]
                    if type(value) == str:
                        value = cleanhtml(record[name])

                    # this part could be simpler, but it has to be done this way
                    # in order to reproduce the former behavior
                    if not isinstance(value, BaseModel):
                        current[i] = field.convert_to_export(value, record)
                    else:
                        primary_done.append(name)
                        # recursively export the fields that follow name; use
                        # 'display_name' where no subfield is exported
                        fields2 = [(p[1:] or ['display_name'] if p and p[0] == name else [])
                                   for p in fields]

                        # in import_compat mode, m2m should always be exported as
                        # a comma-separated list of xids or names in a single cell
                        if import_compatible and field.type == 'many2many':
                            index = None
                            # find out which subfield the user wants & its
                            # location as we might not get it as the first
                            # column we encounter
                            for name in ['id', 'name', 'display_name']:
                                with contextlib.suppress(ValueError):
                                    index = fields2.index([name])
                                    break
                            if index is None:
                                # not found anything, assume we just want the
                                # name_get in the first column
                                name = None
                                index = i

                            if name == 'id':
                                xml_ids = [xid for _, xid in value.__ensure_xml_id()]
                                current[index] = ','.join(xml_ids)
                            else:
                                current[index] = field.convert_to_export(value, record)
                            continue

                        lines2 = value._export_rows(fields2, _is_toplevel_call=False)
                        if lines2:
                            # merge first line with record's main line
                            for j, val in enumerate(lines2[0]):
                                if val or isinstance(val, (int, float)):
                                    current[j] = val
                            # append the other lines at the end
                            lines += lines2[1:]
                        else:
                            current[i] = ''

        # if any xid should be exported, only do so at toplevel
        if _is_toplevel_call and any(f[-1] == 'id' for f in fields):
            bymodels = collections.defaultdict(set)
            xidmap = collections.defaultdict(list)
            # collect all the tuples in "lines" (along with their coordinates)
            for i, line in enumerate(lines):
                for j, cell in enumerate(line):
                    if type(cell) is tuple:
                        bymodels[cell[0]].add(cell[1])
                        xidmap[cell].append((i, j))
            # for each model, xid-export everything and inject in matrix
            for model, ids in bymodels.items():
                for record, xid in self.env[model].browse(ids).__ensure_xml_id():
                    for i, j in xidmap.pop((record._name, record.id)):
                        lines[i][j] = xid
            assert not xidmap, "failed to export xids for %s" % ', '.join('{}:{}' % it for it in xidmap.items())

        return lines

    # def grouped(self, key):
    #     """Eagerly groups the records of ``self`` by the ``key``, returning a
    #     dict from the ``key``'s result to recordsets. All the resulting
    #     recordsets are guaranteed to be part of the same prefetch-set.
    #
    #     Provides a convenience method to partition existing recordsets without
    #     the overhead of a :meth:`~.read_group`, but performs no aggregation.
    #
    #     .. note:: unlike :func:`itertools.groupby`, does not care about input
    #               ordering, however the tradeoff is that it can not be lazy
    #
    #     :param key: either a callable from a :class:`Model` to a (hashable)
    #                 value, or a field name. In the latter case, it is equivalent
    #                 to ``itemgetter(key)`` (aka the named field's value)
    #     :type key: callable | str
    #     :rtype: dict
    #     """
    #     if isinstance(key, str):
    #         key = itemgetter(key)
    #
    #     collator = defaultdict(list)
    #     for record in self:
    #         collator[key(record)].extend(record._ids)
    #
    #     browse = functools.partial(type(self), self.env, prefetch_ids=self._prefetch_ids)
    #     return {key: browse(tuple(ids)) for key, ids in collator.items()}
