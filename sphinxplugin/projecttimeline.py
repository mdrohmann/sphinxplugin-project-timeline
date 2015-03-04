import re
import roman
import dateutil.parser
import docutils
import sphinxcontrib.blockdiag
from sphinx.util.nodes import nested_parse_with_titles


submodule_split_re = re.compile(
    r'(?P<name>[^(]+)\(?(?P<submodule>[IVX, ]*)?\)?', re.IGNORECASE)
submodules_split_re = re.compile(r'[^IVX]*', re.IGNORECASE)


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


def identify_time_chunk_name(name, aliases, allow_groups=False,
                             submodule_ids=False):
    parts = split_name_and_submodule(name)
    possible_alias = aliases[parts[0]]
    if len(possible_alias) > 1:
        # TODO: add a parser warning
        raise ValueError(
            "TimelineChunk with non-unique identifier {name} requested!"
            .format(name=name))
    name = possible_alias[0][0]
#    nsms = possible_alias[0][1]

    submodules = None
    if len(parts) == 2:
        submodules = parts[1:]
    else:
        if allow_groups:
            submodules = range(possible_alias[0][1])
        else:
            submodules = [0]

    ret = [(name, sm) for sm in submodules]
    if submodule_ids:
        ret = [id_from_name_and_submodule(x[0], x[1]) for x in ret]
    return ret  # , nsms


def parse_list_items(enumeration):
    items = []
    for item in enumeration.traverse(docutils.nodes.list_item):
        item_paragraph = item.traverse(docutils.nodes.paragraph)

        if len(item_paragraph) == 0:
            # TODO: raise warning in parser
            raise ValueError('empty enumeration item encountered')

        items.append(' '.join(list(item.traverse(docutils.nodes.Text))))

    return items


class SubmoduleNode(object):

    def __init__(self, tcs, fullid):
        parts = split_name_and_submodule(fullid)
        self.name = parts[0]
        self.timechunk = tcs[parts[0]]
        if len(parts) > 1:
            self.submodule = parts[1]
        else:
            self.submodule = 0
        self.children = []
        self.important = False
        self.group = None

    def set_important(self):
        self.important = True
        for child in self.children:
            child.set_important()

    def get_full_id(self, nowhitespace=False):
        ret = id_from_name_and_submodule(self.name, self.submodule)
        if nowhitespace:
            ret = re.sub(r'[()]', r'', ret)
            ret = re.sub(r'\W+', r'-', ret)
        return ret

    def visit_dependency_resolution(self, timechunks, aliases, parents):
        tc = self.timechunk
        for dep in tc.get_dependencies(self.submodule):
            depname = identify_time_chunk_name(dep, aliases, True, True)
            for sn in depname:
                if sn in parents:
                    # TODO: make this a parser error
                    raise ValueError(
                        "Cyclic dependency in graph!  {} depends on istself."
                        .format(sn))
                self.children.append(SubmoduleNode(timechunks, sn))
        tc.submodules[self.submodule] = self
        for child in self.children:
            child.visit_dependency_resolution(
                timechunks, aliases, parents + [self.get_full_id()])

    def traverse_edge_lines(self, lines):
        fi = self.get_full_id(True)
        for child in self.children:
            lines.append(
                self.blockdiag_edge_format(fi, child.get_full_id(True)))
            child.traverse_edge_lines(lines)

    def blockdiag_edge_format(self, fi, ci):
        ret = '{} -> {}'.format(ci, fi)
        options = []
        if self.important:
            options.append('color = "red"')
        if len(options) > 0:
            ret += ' [{}]'.format(', '.join(options))
        return ret

    def blockdiag_node_format(self):
        ret = self.get_full_id(True)
        pref = self.timechunk.parent.attributes['ids'][-1]
        options = []
        if self.group:
            options.append('group = "{}"'.format(self.group))
        if self.important:
            options.append('linecolor = "red"')
        options.append('label = "{}"'.format(self.get_full_id()))
        options.append('href = ":ref:`{}`"'.format(pref))
        if len(options) > 0:
            ret += ' [{}]'.format(', '.join(options))
        return ret

    def get_blockdiag_nodes(self, nodes):
        nodes.add(self.blockdiag_node_format())
        for child in self.children:
            child.get_blockdiag_nodes(nodes)


class TimelineChunk(object):

    tdelta_hours_re = re.compile(
        r'(?P<hours>[\d\.]+)\W*(?!\d*\W*m)(h|hr|hrs)?')
    tdelta_minutes_re = re.compile(
        r'(?P<minutes>[\d]+)\W*(m|min|mins)')

    def __init__(self, parent, name='unknown', docname='unknown'):
        self.parent = parent
        self.name = name
        self.time_deltas = []
        self.dependencies = {}
        self.docname = docname
        self.submodules = {}

    def get_dependencies(self, num):
        if num in self.dependencies:
            return self.dependencies[num]
        else:
            return []

    def num_submodules(self):
#        assert len(self.time_deltas) > max(self.dependencies.keys())
        return len(self.time_deltas)

    def get_submodule(self, num):
        if num in self.submodules:
            return self.submodules[num]
        else:
            raise ValueError(
                'Submodule does not exist.  Do you have cyclic dependencies?')

    def parse_time_delta(self, string):
        hours = self.tdelta_hours_re.search(string)
        minutes = self.tdelta_minutes_re.search(string)
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

    def parse_dependencies(self, text_or_node, submodule):

        if len(submodule) == 0:
            submodule = 0
        else:
            submodule = roman.fromRoman(submodule[0]) - 1

        dep_strings = []
        if isinstance(text_or_node, basestring):
            dep_strings = [text_or_node]
        else:
            enumerations = text_or_node.traverse(is_list_or_enumeration)
            for enumeration in enumerations:
                dep_strings += parse_list_items(text_or_node)

        if submodule not in self.dependencies:
            self.dependencies[submodule] = []
        self.dependencies[submodule] += dep_strings

    def parse_requested_time(self, text_or_node):
        time_strings = []
        if isinstance(text_or_node, basestring):
            time_strings = [text_or_node]
        else:
            enumerations = text_or_node.traverse(is_list_or_enumeration)
            for enumeration in enumerations:
                time_strings += parse_list_items(text_or_node)

        self.time_deltas = [
            self.parse_time_delta(time_string) for time_string in time_strings]

    def update_aliases_with_backreference(self, aliases):
        arg = (self.name, self.num_submodules())
        for cid in self.parent.attributes['ids']:
            if cid in aliases.keys():
                aliases[cid].append(arg)
            else:
                aliases[cid] = [arg]
        return aliases


class TimelineBlockdiagNode(sphinxcontrib.blockdiag.blockdiag_node):
    name = 'TimelineBlockdiagNode'
    """
    overwrites the blockdiag node from the sphinxcontrib package.

    This node will be replaced by the actual sphinxcontrib.blockdiag nodes in a
    later step.
    """
    pass


class TimelineNode(docutils.nodes.General, docutils.nodes.Element):
    """
    This node simply is a wrapper creating a TimelineBlockdiag element with a
    paragraph for meta information.

    It will be replaced by its children in a later step. (doctree-resolved)
    """

    def _parse_list_items(self, item_strings):
        items = []
        for item_string in item_strings:
            name_submodule = split_name_and_submodule(item_string)
            parts = name_submodule[0].split(' ', 2)
            res = {'time': None, 'xref': None, 'submodules': []}
            index = 0
            if len(parts) == 0:
                # TODO: change this into a parser warning
                raise ValueError(
                    'Invalid format for milestone / deadline item.')
            elif len(parts) > 1:
                try:
                    res['time'] = dateutil.parser.parse(parts[0])
                    index = 1
                except:
                    pass
            res['xref'] = ' '.join(parts[index:])
            res['submodules'] = name_submodule[1:]

            items.append(res)

        return items

    def _get_available_submodules(self, timechunks):
        available_submodules = set()
        for tk in timechunks.keys():
            for i in [id_from_name_and_submodule(tk, y)
                      for y in range(timechunks[tk].num_submodules())]:
                available_submodules.add(i)
        return available_submodules

    def resolve_all_dependencies(self, timechunks, aliases):
        # gather all root elements (nodes without parents)
        submodules_with_parents = set()
        for tc in timechunks.itervalues():
            alldeps = reduce(
                lambda x, y: x + y, tc.dependencies.itervalues(), [])
            for dep in alldeps:
                depnames = identify_time_chunk_name(
                    dep, aliases, True, True)
                for dn in depnames:
                    submodules_with_parents.add(dn)
        available_submodules = self._get_available_submodules(timechunks)

        root_elements = available_submodules - submodules_with_parents
        if len(root_elements) == 0:
            # TODO: make this a parser error
            raise ValueError(
                "All timeline chunks are a dependant of another chunk."
                "Cyclic dependencies?")
        self.root_chunks = [
            SubmoduleNode(timechunks, el) for el in root_elements]

        for rc in self.root_chunks:
            rc.visit_dependency_resolution(timechunks, aliases, [])

    def _resolve_milestone(self, milestone, timechunks, aliases):
        mn = milestone[0]
        ms = milestone[1]
        ms_key = identify_time_chunk_name(ms['xref'], aliases)
        ms_chunk = timechunks[ms_key[0][0]]
        submodules = ms['submodules'] or range(ms_chunk.num_submodules())
        for sm in submodules:
            submodule = ms_chunk.get_submodule(sm)
            submodule.set_important()
            submodule.group = 'Milestone{}'.format(mn)

    def resolve_milestones(self, timechunks, aliases):
        grouplines = []
        for milestone in enumerate(self.milestones):
            self._resolve_milestone(milestone, timechunks, aliases)
            grouplines += [
                'group Milestone{}'.format(milestone[0]) + ' {',
                '  label = "Milestone {}"'.format(milestone[0]),
                '  color = "#aaaaaa"',
                '}']
        return grouplines

    def _resolve_deadline(self, deadline, timechunks, aliases):
        dn = deadline[0]
        dl = deadline[1]
        dl_key = identify_time_chunk_name(dl['xref'], aliases)
        dl_chunk = timechunks[dl_key[0][0]]
        submodules = dl['submodules'] or range(dl_chunk.num_submodules())
        for sm in submodules:
            submodule = dl_chunk.get_submodule(sm)
            submodule.group = 'Deadline{}'.format(dn)

    def resolve_deadlines(self, timechunks, aliases):
        grouplines = []
        for deadline in enumerate(self.deadlines):
            self._resolve_deadline(deadline, timechunks, aliases)
            grouplines += [
                'group Deadline{}'.format(deadline[0]) + ' {',
                '  label = "Deadline {}"'.format(deadline[1]['time']),
                '  color = "#bbbbbb"',
                '}']
        return grouplines

    def _parse_list_items_from_doctree(self, enumeration):
        strings = parse_list_items(enumeration)
        return self._parse_list_items(strings)

    def _get_list_items_from_list(self, section):

        res = []
        for enumeration in section.traverse(is_list_or_enumeration):
            res += self._parse_list_items_from_doctree(enumeration)
        return res

    def add_milestones_from_section(self, milestones_section):
        self.milestones = self._get_list_items_from_list(milestones_section)

    def add_deadlines_from_section(self, deadlines_section):
        self.deadlines = self._get_list_items_from_list(deadlines_section)


def node_is_section_with_title(node, title):
    return (
        isinstance(node, docutils.nodes.section)
        and len(node.children) >= 1
        and isinstance(node[0], docutils.nodes.title)
        and node[0][0].lower() == title.lower())


class TimelineChunksDirective(docutils.parsers.rst.Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    option_spec = {}

    @classmethod
    def get_chunk_for_node(cls, document, node):

        env = document.settings.env

        if not hasattr(env, 'timeline_chunks'):
            env.timeline_chunks = {}

        parent = node.parent
        parent_name = parent.attributes['ids']
        if not isinstance(parent, docutils.nodes.section):
            # TODO: make this an error in the parser
            raise ValueError('parent of timeline chunk is not a section!')
        if len(parent_name) == 0:
            # TODO: make this a warning or error in the parser
            raise ValueError('no id found name for timeline chunk.')
        elif len(parent_name) > 1:
            # TODO: add a warning that the timeline chunk is not unique
            raise ValueError('timeline chunk is not unique.')

        parent_name = parent_name[0]

        if parent_name not in env.timeline_chunks:
            env.timeline_chunks[parent_name] = TimelineChunk(
                parent, parent_name, env.docname)
        chunk = env.timeline_chunks[parent_name]

        return chunk


class TimelineRequestedDirective(TimelineChunksDirective):

    def run(self):
        chunk = self.get_chunk_for_node(self.state.document, self.state)

        nested_node = docutils.nodes.paragraph()
        nested_parse_with_titles(self.state, self.content, nested_node)

        chunk.parse_requested_time(nested_node)

        return []

    @classmethod
    def role(cls, name, rawtext, text, lineno, inliner,
             options={}, content=[]):
        chunk = cls.get_chunk_for_node(inliner.document, inliner)

        chunk.parse_requested_time(text)
        return [], []


class TimelineDependencyDirective(TimelineChunksDirective):

    optional_arguments = 1

    def run(self):
        chunk = self.get_chunk_for_node(self.state.document, self.state)

        nested_node = docutils.nodes.paragraph()
        nested_parse_with_titles(self.state, self.content, nested_node)

        chunk.parse_dependencies(nested_node, self.arguments)
        return []

    @classmethod
    def role(cls, name, rawtext, text, lineno, inliner,
             options={}, content=[]):
        chunk = cls.get_chunk_for_node(inliner.document, inliner)

        chunk.parse_dependencies(text, ['I'])
        return [], []


class TimelineDirective(docutils.parsers.rst.Directive):
    """
    Initializes a customized blockdiag node (TimelineBlockdiag) and maybe a
    paragraph node, that has some meta information about the progress.

    It writes the requested timeline paths in env.timeline_paths.
    """
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    option_spec = {}

    def run(self):

        docutils.parsers.rst.roles.set_classes({"class": "timeline"})

        nested_node = docutils.nodes.paragraph()
        nested_parse_with_titles(self.state, self.content, nested_node)

        # find milestones section
        milestones_sections = list(
            nested_node.traverse(
                lambda(node): node_is_section_with_title(node, 'milestones')))
        # find deadlines section
        deadlines_sections = list(
            nested_node.traverse(
                lambda(node): node_is_section_with_title(node, 'deadlines')))

        # create a timeline node
        timeline = TimelineNode()
        results = [timeline]

        for milestones_section in milestones_sections:
            timeline.add_milestones_from_section(milestones_section)

        for deadline_section in deadlines_sections:
            timeline.add_deadlines_from_section(deadline_section)

        return results


def purge_timelines(app, env, docname):
    """
    purge all environment variables created from the document `docname`.
    """
    if not hasattr(env, 'timeline_chunks'):
        return

    env.timeline_chunks = dict(
        [(key, chunk) for (key, chunk) in env.timeline_chunks.iteritems()
         if chunk.docname != docname])


def process_timelines(app, doctree, fromdocname):
    """
    replace TimelineNode with their children, replace TimelineBlockdiag with
    sphinxcontrib.blockdiag and call its handler function...
    """

    tn = doctree.traverse(TimelineNode)
    if len(tn) == 0:
        return
    if len(tn) > 1:
        # TODO: make this a parser error!
        raise ValueError("Only one timeline per file allowed!")
    tn = tn[0]

    env = app.env
    if not hasattr(env, 'timeline_chunks'):
        # TODO: make this a parser error!
        tn.replace_self([])
        raise ValueError("no timeline chunks for the timeline found!")

    tcs = env.timeline_chunks
    aliases = {}
    for tc in tcs.values():
        tc.update_aliases_with_backreference(aliases)

    tn.resolve_all_dependencies(tcs, aliases)
    lines = tn.resolve_milestones(tcs, aliases)
    lines += tn.resolve_deadlines(tcs, aliases)
    nodes = set()
    for rc in tn.root_chunks:
        rc.traverse_edge_lines(lines)
        rc.get_blockdiag_nodes(nodes)

    lines = list(nodes) + lines

    tn.blockdiag = sphinxcontrib.blockdiag.blockdiag_node()
    tn.blockdiag.code = (
        'blockdiag {{\n\t{}\n}}\n'.format('\n\t'.join(lines)))
    tn.blockdiag['code'] = tn.blockdiag.code
    tn.blockdiag['options'] = {}
    tn.blockdiag['ids'] = tn['ids']

    tn.replace_self(tn.blockdiag)

    # The following line, explicitly resolve the now created blockdiag node.
    # NB: It might also resolve other blockdiag nodes, but this should be safe.
    sphinxcontrib.blockdiag.on_doctree_resolved(app, doctree, fromdocname)


def on_builder_inited(self):
    pass
#    config = self.builder.config
#    blockdiag_loaded = 'sphinxcontrib.blockdiag' in config.extensions


def setup(app):

    app.add_node(TimelineBlockdiagNode)
    app.add_node(TimelineNode)
    app.add_role(
        'requested-time',
        lambda *args: TimelineRequestedDirective.role(*args))
    app.add_directive('requested-time', TimelineRequestedDirective)
    app.add_role(
        'dependent-tasks',
        lambda *args: TimelineDependencyDirective.role(*args))
    app.add_directive('dependent-tasks', TimelineDependencyDirective)
    app.add_directive('timeline', TimelineDirective)
    app.add_directive('env-purge-doc', purge_timelines)
    app.connect('doctree-resolved', process_timelines)
    app.connect('builder-inited', on_builder_inited)

    # TODO:
    # - [ ] add javascript source code in order to manipulate the progress
    #       interactively

    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
