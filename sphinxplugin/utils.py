import re
import math
from docutils import nodes
from datetime import datetime, timedelta
import docutils
import roman


submodule_split_re = re.compile(
    r'(?P<name>[^(]+)\(?(?P<submodule>[IVX, ]*)?\)?', re.IGNORECASE)
submodules_split_re = re.compile(r'[^IVX]*', re.IGNORECASE)
tdelta_hours_re = re.compile(
    r'(?P<hours>[\d\.]+)\W*(?!\d*\W*m)(h|hr|hrs)?')
tdelta_minutes_re = re.compile(
    r'(?P<minutes>[\d]+)\W*(m|min|mins)')


def node_is_section_with_title(node, title):
    return (
        isinstance(node, docutils.nodes.section)
        and len(node.children) >= 1
        and isinstance(node[0], docutils.nodes.title)
        and node[0][0].lower() == title.lower())


def make_descriptions_from_meta(meta, name):
    rows = []
    for i, mrow in enumerate(meta):
        nam = '{} {}'.format(name, i + 1)
        r_req_time = float(mrow['time_req']) / 60.
        r_worked = float(mrow['minutes_worked']) / 60.
        r_done = float(mrow['done'])
        r_days = float(mrow['time_worked'])

        if r_done == 0:
            r_factor = 0
        else:
            r_factor = (r_worked / (r_req_time * r_done))

        # at least 5 minutes of recorded work
        if math.floor(r_days * 288) == 0:
            advancement_week = 0
            r_ETA = float('inf')
        else:
            advancement_week = (r_done / (r_days / 7.))
            r_ETA = (1. - r_done) * (r_days / (r_done))  # in days

        req_time = '{:0.2f} h'.format(r_req_time)
        hrs_spent = '{:0.2f} h'.format(r_worked)
        prc_done = '{:2.1f} %'.format(r_done * 100)
        hrs_left1 = '{:0.2f} h'.format(max(r_req_time - r_worked, 0))
        hrs_left2 = '{:0.2f} h'.format(
            max(r_req_time * r_factor - r_worked, 0))
        days_spent = '{:0.2f} d'.format(int(r_days))
        work_factor = '{:0.2f}'.format(r_factor)
        advancement_week = '{:0.0f} %'.format(advancement_week * 100)
        if r_ETA == float('inf'):
            ETA = 'undefined'
            ETA2 = 'undefined'
        else:
            try:
                r_ETA1 = datetime.now() + timedelta(int(r_ETA))
                ETA = '{}'.format(r_ETA1.strftime('%Y-%m-%d'))
            except:
                ETA = 'undefined'
            try:
                r_ETA2 = datetime.now() + timedelta(int(r_ETA/r_factor))
                ETA2 = '{}'.format(r_ETA2.strftime('%Y-%m-%d'))
            except:
                ETA2 = 'undefined'
        rows.append([
            nam, req_time, prc_done, hrs_spent, hrs_left1, hrs_left2,
            days_spent, work_factor, advancement_week, ETA, ETA2
        ])

    return rows


def description_table(descriptions, widths, headers):
    # generate table-root
    tgroup = nodes.tgroup(cols=len(widths))
    for width in widths:
        tgroup += nodes.colspec(colwidth=width)
    table = nodes.table()
    table += tgroup

    # generate table-header
    thead = nodes.thead()
    row = nodes.row()
    for header in headers:
        entry = nodes.entry()
        entry += nodes.paragraph(text=header)
        row += entry
    thead += row
    tgroup += thead

    # generate table-body
    tbody = nodes.tbody()
    for desc in descriptions:
        row = nodes.row()
        for col in desc:
            entry = nodes.entry()
            if not isinstance(col, basestring):
                col = str(col)
            paragraph = nodes.paragraph()
            paragraph += nodes.Text(col)
            entry += paragraph
            row += entry
        tbody += row
    tgroup += tbody

    return table


def dt_to_float_days(dt):
    return float(dt.days + dt.seconds / 3600.)


def parse_time_delta(string):
    hours = tdelta_hours_re.search(string)
    minutes = tdelta_minutes_re.search(string)
    res = hours.groupdict() if hours is not None else {'hours': 0}
    res.update(
        minutes.groupdict() if minutes is not None else {'minutes': 0})

    res = dict(
        [(key, float(value)) for (key, value) in res.iteritems()])

    total_minutes = int(res['hours'] * 60. + res['minutes'])
    if total_minutes == 0:
        # TODO: make this a parser error
        raise ValueError('Could not parse the requested time string')

    return total_minutes


def add_stats(stats):
    res = {}
    for key in ['time_req', 'minutes_worked']:
        res[key] = sum(stats[key].itervalues())
    res['time_worked'] = dt_to_float_days(
        datetime.now() - stats['start_time'])
    res['done'] = 1. / res['time_req'] * sum(
        [float(stats['done'][key] * stats['time_req'][key])
         for key in stats['done'].keys()])
    return res


def is_list_or_enumeration(node):
    return (isinstance(node, docutils.nodes.bullet_list)
            or isinstance(node, docutils.nodes.enumerated_list))


def id_from_name_and_submodule(name, submodule):
    return '{} ({})'.format(name, roman.toRoman(submodule + 1))


def split_name_and_submodule(name):
    res = submodule_split_re.match(name)
    parts = list(res.groups())
    parts[0] = parts[0].strip()
    if len(parts[1]) == 0:
        parts = [parts[0]]
    else:
        submodules = submodules_split_re.split(
            parts[1])
        parts = [parts[0]] + [
            roman.fromRoman(submodule.upper()) - 1
            for submodule in submodules]
    return parts


def slugify(name):
    return re.sub(r'[\W_]+', r'-', name.lower())


def parse_list_items(enumeration):
    items = []
    for item in enumeration.traverse(docutils.nodes.list_item):
        item_paragraph = item.traverse(docutils.nodes.paragraph)

        if len(item_paragraph) == 0:
            # TODO: raise warning in parser
            raise ValueError('empty enumeration item encountered')

        items.append(' '.join(list(item.traverse(docutils.nodes.Text))))

    return items
