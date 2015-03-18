import re
import docutils
from datetime import datetime
import dateutil.parser
import roman
from . import utils
from .submodule_node import SubmoduleNode


class TimelineChunksContainer(object):

    def __init__(self):

        self.chunks = {}
        self.aliases = {}
        self.groups = {}

    def purge(self, docname):
        self.chunks = dict(
            [(key, chunk) for (key, chunk) in self.chunks.iteritems()
             if chunk.docname != docname])
        self.groups = dict(
            [(key, group) for (key, group) in self.groups.iteritems()
             if group.docname != docname])

        self.aliases = {}
        self.update_aliases()

    def get_chunk_id(self, name, allow_groups=False, submodule_ids=False):
        parts = utils.split_name_and_submodule(name)
        # TODO: use pending_xrefs to resolve the links
        try:
            possible_alias = list(self.aliases[parts[0].lower()])
        except KeyError:
            possible_alias = list(self.aliases[utils.slugify(parts[0])])

        if not allow_groups and len(possible_alias) > 1:
            # TODO: add a parser warning
            raise ValueError(
                "TimelineChunk with non-unique identifier {name} requested!"
                .format(name=name))

        ret = []
        for pa in possible_alias:
            name = pa[0]
        #    nsms = possible_alias[0][1]

            submodules = None
            if len(parts) == 2:
                submodules = parts[1:]
            else:
                if allow_groups:
                    submodules = range(pa[1])
                else:
                    submodules = [0]

            ret_t = [(name, sm) for sm in submodules]
            if submodule_ids:
                ret_t = [
                    utils.id_from_name_and_submodule(x[0], x[1])
                    for x in ret_t]
            ret += ret_t
        return ret  # , nsms

    def add_chunk(self, parent, docname):
        parent_name = parent.attributes['ids']
        if not isinstance(parent, docutils.nodes.section):
            # TODO: make this an error in the parser
            raise ValueError('parent of timeline chunk is not a section!')
        if len(parent_name) == 0:
            # TODO: make this a warning or error in the parser
            raise ValueError('no id name for timeline chunk.')
        elif len(parent_name) > 1:
            # TODO: add a warning that the timeline chunk is not unique
            raise ValueError('timeline chunk is not unique.')

        parent_name = parent_name[0]

        title = (
            ' '.join([t.astext() for t in (parent
                     .traverse(docutils.nodes.title)[0]
                     .traverse(docutils.nodes.Text))]))

        if utils.slugify(title) not in self.chunks:
            self.chunks[utils.slugify(title)] = TimelineChunk(
                parent, title, parent_name, docname, self)

        return self.chunks[utils.slugify(title)]

    def add_group(self, name, parent, docname):
        self.groups[name] = {
            'parent': parent,
            'docname': docname
        }

    def update_aliases(self):
        for tc in self.chunks.values():
            tc.update_aliases_with_backreference(self.aliases, self.groups)

    def add_stat_tables(self):
        for tc in self.chunks.values():
            tc.add_stat_tables()


class TimelineChunk(object):

    def __init__(self, parent,
                 title='unknown', name='unknown', docname='unknown',
                 container=None):
        self.container = container
        self.parent = parent
        self.title = title
        self.name = name
        self.time_deltas = []
        self.dependencies = {}
        self.docname = docname
        self.submodules = {}
        self.worked_minutes = {}
        self.start_times = {}
        self.end_times = {}
        self.completeness = {}
        self.stats = {}

    def add_stat_tables(self, ttsn):

        headers = [
            '              ',
            'Requested time',
            'Percent done  ',
            'Spent work hrs',
            'Hours left I  ',
            'Hours left II ',
            'Spent days    ',
            'Work factor   ',
            'Advance / week',
            'ETA           ',
            'ETA 2         ',
            ]
        widths = [16] * len(headers)
        meta = [self.stats[key] for key in sorted(self.stats.keys())]
        descriptions1 = utils.make_descriptions_from_meta(meta, 'Task')

        paragraph = docutils.nodes.paragraph()
        table = utils.description_table(descriptions1, widths, headers)
        paragraph += table
        ttsn.replace_self(paragraph)

    def get_dependencies(self, num):
        if num in self.dependencies:
            return self.dependencies[num]
        else:
            return []

    def add_stats(self, submodule, stats):
        self.stats[submodule] = stats

    def get_requested_time(self, num):
        return self.time_deltas[num]

    def get_worked_minutes(self, num):
        if num in self.worked_minutes:
            return self.worked_minutes[num]
        else:
            return 0

    def get_start_time(self, num):
        if num in self.start_times:
            return self.start_times[num]
        else:
            return datetime.now()

    def set_start_time(self, num, time):
        if num in self.start_times:
            self.start_times[num] = min(self.start_times[num], time)
        else:
            self.start_times[num] = time

    def get_end_time(self, num):
        if num in self.end_times:
            return self.end_times[num]
        else:
            return datetime.now()

    def get_worked_time(self, num):
        st = self.get_start_time(num)

        end = self.get_end_time(num)
        return utils.dt_to_float_days(end - st)

    def get_completeness(self, num):
        if num in self.completeness:
            return self.completeness[num]
        else:
            return 0

    def set_completeness(self, num, prc_done, time):
        self.completeness[num] = prc_done
        if prc_done == 1:
            if time is None:
                self.end_times[num] = datetime.now()
            else:
                self.end_times[num] = time

    def num_submodules(self):
#        assert len(self.time_deltas) > max(self.dependencies.keys())
        return len(self.time_deltas)

    def get_submodule(self, num):
        if num in self.submodules:
            return self.submodules[num]
        else:
            sm = SubmoduleNode(
                self.container,
                utils.id_from_name_and_submodule(
                    utils.slugify(self.title), num))
            sm.visit_dependency_resolution(self.container, [])
            return sm

    def _parse_worked_on_line(self, line, submodule):
        parts = re.split(r':', line, 2)
        lindex = 0
        time = None
        try:
            time = dateutil.parser.parse(parts[0])
            self.set_start_time(submodule, time)
            lindex = 1
        except:
            pass

        nline = ':'.join(parts[lindex:])
        res = re.search(r'([\d\.]+) *%', nline)
        if res:
            nline = nline[0:res.start()]
            self.set_completeness(submodule, float(res.groups()[0])/100., time)
        try:
            time_delta = utils.parse_time_delta(nline)
            if submodule in self.worked_minutes:
                self.worked_minutes[submodule] += time_delta
            else:
                self.worked_minutes[submodule] = time_delta
        except ValueError:
            pass

    def _parse_worked_strings(self, worked_strings, submodule):
        for ws in worked_strings:
            self._parse_worked_on_line(ws, submodule)

    def parse_worked_on(self, text_or_node, submodule):

        submodule = roman.fromRoman(submodule) - 1

        worked_strings = []
        if isinstance(text_or_node, basestring):
            worked_strings = [text_or_node]
        else:
            enumerations = text_or_node.traverse(utils.is_list_or_enumeration)
            for enumeration in enumerations:
                worked_strings += utils.parse_list_items(text_or_node)

        self._parse_worked_strings(worked_strings, submodule)

    def parse_dependencies(self, text_or_node, submodule):

        submodule = roman.fromRoman(submodule) - 1

        dep_strings = []
        if isinstance(text_or_node, basestring):
            dep_strings = [text_or_node]
        else:
            enumerations = text_or_node.traverse(utils.is_list_or_enumeration)
            for enumeration in enumerations:
                dep_strings += utils.parse_list_items(text_or_node)

        if submodule not in self.dependencies:
            self.dependencies[submodule] = []
        self.dependencies[submodule] += dep_strings

    def parse_requested_time(self, text_or_node):
        time_strings = []
        if isinstance(text_or_node, basestring):
            time_strings = [text_or_node]
        else:
            enumerations = text_or_node.traverse(utils.is_list_or_enumeration)
            for enumeration in enumerations:
                time_strings += utils.parse_list_items(text_or_node)

        self.time_deltas = [
            utils.parse_time_delta(time_string)
            for time_string in time_strings]

    def update_aliases_with_backreference(self, aliases, groups):
        arg = (utils.slugify(self.title), self.num_submodules())
        for cid in [utils.slugify(self.title)] + self.parent.attributes['ids']:
            if cid in aliases.keys():
                aliases[cid.lower()].add(arg)
            else:
                aliases[cid.lower()] = set([arg])

        for gk, gv in groups.iteritems():
            if self.parent.parent == gv['parent']:
                if gk in aliases.keys():
                    aliases[gk.lower()].add(arg)
                else:
                    aliases[gk.lower()] = set([arg])
        return aliases
