import re
import docutils.parsers
from sphinx.util.nodes import nested_parse_with_titles
from .timeline_chunk import TimelineChunk
from .nodes import TimelineNode
from . import utils


class TimelineChunksDirective(docutils.parsers.rst.Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    option_spec = {}

    roman_re = re.compile('([IVXLCM]+)')

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
            title = (
                ' '.join([t.astext() for t in (parent
                         .traverse(docutils.nodes.title)[0]
                         .traverse(docutils.nodes.Text))]))
            env.timeline_chunks[parent_name] = TimelineChunk(
                parent, title, parent_name, env.docname)
        chunk = env.timeline_chunks[parent_name]

        return chunk

    def check_argument_is_roman(self, arguments):
        ret = []
        for arg in arguments:
            rres = self.roman_re.match(arg)
            if rres:
                ret += rres.group()
        return ret


class TimelineWorkedOnDirective(TimelineChunksDirective):

    def run(self):
        chunk = self.get_chunk_for_node(self.state.document, self.state)

        nested_node = docutils.nodes.paragraph()
        nested_parse_with_titles(self.state, self.content, nested_node)

        arguments = self.check_argument_is_roman(self.arguments)

        chunk.parse_worked_on(nested_node, arguments)

        return []

    @classmethod
    def role(cls, name, rawtext, text, lineno, inliner,
             options={}, content=[]):
        chunk = cls.get_chunk_for_node(inliner.document, inliner)

        chunk.parse_worked_on(text)
        return [], []


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

        arguments = self.check_argument_is_roman(self.arguments)

        chunk.parse_dependencies(nested_node, arguments)
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
                lambda(node):
                utils.node_is_section_with_title(node, 'milestones')))
        # find deadlines section
        deadlines_sections = list(
            nested_node.traverse(
                lambda(node):
                utils.node_is_section_with_title(node, 'deadlines')))

        # create a timeline node
        timeline = TimelineNode()
        results = [timeline]

        for milestones_section in milestones_sections:
            timeline.add_milestones_from_section(milestones_section)

        for deadline_section in deadlines_sections:
            timeline.add_deadlines_from_section(deadline_section)

        return results
