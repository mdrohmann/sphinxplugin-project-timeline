import re
from datetime import datetime
import dateutil.parser
import roman
from . import utils


class TimelineChunk(object):

    def __init__(self, parent,
                 title='unknown', name='unknown', docname='unknown'):
        self.parent = parent
        self.title = title
        self.name = name
        self.time_deltas = []
        self.dependencies = {}
        self.docname = docname
        self.submodules = {}
        self.worked_minutes = {}
        self.start_times = {}
        self.completeness = {}

    def get_dependencies(self, num):
        if num in self.dependencies:
            return self.dependencies[num]
        else:
            return []

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

    def get_worked_time(self, num):
        st = self.get_start_time(num)
        now = datetime.now()
        return utils.dt_to_float_days(now - st)

    def get_completeness(self, num):
        if num in self.completeness:
            return self.get_completeness[num]
        else:
            return 0

    def num_submodules(self):
#        assert len(self.time_deltas) > max(self.dependencies.keys())
        return len(self.time_deltas)

    def get_submodule(self, num):
        if num in self.submodules:
            return self.submodules[num]
        else:
            raise ValueError(
                'Submodule {} in {} does not exist.'
                'Do you have cyclic dependencies?'
                .format(num, self.name))

    def _parse_worked_on_line(self, line, submodule):
        res = {'date': None, 'minutes': 0, 'done': 0}
        parts = re.split(r' +', line, 2)
        lindex = 0
        try:
            time = dateutil.parser.parse(parts[0])
            self.start_times[submodule] = time
            lindex = 1
        except:
            pass

        nline = ' '.join(parts[lindex:])
        res = re.search(r'([\d\.]+) *%', nline)
        if res:
            nline = nline[0:res.start()]
            self.completeness[submodule] = float(res.group())
        self.worked_minutes[submodule] = utils.parse_time_delta(nline)

    def _parse_worked_strings(self, worked_strings, submodule):
        for ws in worked_strings:
            self._parse_worked_on_line(ws, submodule)

    def parse_worked_on(self, text_or_node, submodule):

        if len(submodule) == 0:
            submodule = 0
        else:
            submodule = roman.fromRoman(submodule[0]) - 1

        worked_strings = []
        if isinstance(text_or_node, basestring):
            worked_strings = [text_or_node]
        else:
            enumerations = text_or_node.traverse(utils.is_list_or_enumeration)
            for enumeration in enumerations:
                worked_strings += utils.parse_list_items(text_or_node)

        self._parse_worked_strings(worked_strings, submodule)

    def parse_dependencies(self, text_or_node, submodule):

        if len(submodule) == 0:
            submodule = 0
        else:
            submodule = roman.fromRoman(submodule[0]) - 1

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
        arg = (self.name, self.num_submodules())
        for cid in [self.title] + self.parent.attributes['ids']:
            if cid in aliases.keys():
                aliases[cid.lower()].add(arg)
            else:
                aliases[cid.lower()] = set([arg])

        for gk, gv in groups.iteritems():
            if self.parent.parent == gv:
                if gk in aliases.keys():
                    aliases[gk.lower()].add(arg)
                else:
                    aliases[gk.lower()] = set([arg])
        return aliases
