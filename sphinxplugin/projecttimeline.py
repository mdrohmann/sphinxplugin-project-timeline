import re
import dateutil
import docutils
import sphinxcontrib.blockdiag
from sphinx.util.nodes import nested_parse_with_titles


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

    def _parse_list_items(self, enumeration):
        re_submodules = re.compile(r'\(([IVX, ]*)\)', re.IGNORECASE)
        re_submodules_split = re.compile(r'[^IVX]*', re.IGNORECASE)
        items = []
        for item in enumeration.traverse(docutils.nodes.list_item):
            item_paragraph = item.traverse(docutils.nodes.paragraph)[0]
            parts = item_paragraph.astext().split(' ')
            res = {'time': None, 'xref': None, 'submodules': []}
            index = 0
            if len(parts) == 0:
                # TODO: change this into a parser warning
                raise ValueError(
                    'Invalid format for milestone / deadline item.')
            elif len(parts) > 1:
                try:
                    res['time'] = dateutil.parser.parse(parts[0])
                except:
                    index = 1
            res['xref'] = parts[index]
            index += 1
            if len(parts) >= index + 1:
                submodules_string = re_submodules.sub(r'\1', parts[index])
                if submodules_string != parts[index]:
                    submodules = re_submodules_split.match(submodules_string)
                    res['submodules'] = submodules

            items.append(res)

        return items

    def add_milestones_from_section(self, milestones_section):
        res = []
        for enumeration in milestones_section.traverse(
                docutils.nodes.enumerated_list):
            res += self._parse_list_items(enumeration)
        self.milestones = res

    def add_deadlines_from_section(self, deadline_section):
        res = []
        for enumeration in deadline_section.traverse(
                docutils.nodes.enumerated_list):
            res += self._parse_list_items(enumeration)
        self.deadlines = res


def node_is_section_with_title(node, title):
    return (
        isinstance(node, docutils.nodes.section)
        and len(node.children) >= 1
        and isinstance(node[0], docutils.nodes.title)
        and node[0][0].lower() == title.lower())


class TimelineDependencyDirective(docutils.parsers.rst.Directive):

    def run(self):

        return []


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

        import pudb
        pudb.set_trace()

        return results


def requested_time_role(
        name, rawtext, text, lineno, inliner,
        options={}, content=[]):
    """
    When this role is found, we need to update information to the
    env.timeline_chunks variable, concerning the requested time for this chunk.
    """
    import pudb
    pudb.set_trace()
    pass


def purge_timelines(app, env, docname):
    """
    purge all environment variables created from the document `docname`.
    """
    pass


def process_timelines(app, doctree, fromdocname):
    """
    replace TimelineNode with their children, replace TimelineBlockdiag with
    sphinxcontrib.blockdiag and call its handler function...
    """
    import pudb
    pudb.set_trace()


def setup(app):

    app.add_node(TimelineBlockdiagNode)
    app.add_node(TimelineNode)
    app.add_role('requested-time', requested_time_role)
    app.add_directive('dependent-tasks', TimelineDependencyDirective)
    app.add_directive('timeline', TimelineDirective)
    app.add_directive('env-purge-doc', purge_timelines)
    app.connect('doctree-resolved', process_timelines)

    # TODO:
    # - [ ] add javascript source code in order to manipulate the progress
    #       interactively

    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
