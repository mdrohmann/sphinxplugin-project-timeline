import re
import docutils.parsers
from sphinx.util.nodes import nested_parse_with_titles
from .timeline_chunk import TimelineChunksContainer
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
            env.timeline_chunks = TimelineChunksContainer()

        chunk = env.timeline_chunks.add_chunk(node.parent, env.docname)

        return chunk

    def check_argument_is_roman(self, arguments):
        if len(arguments) == 0:
            return ['I']
        ret = []
        for arg in arguments:
            rres = self.roman_re.match(arg)
            if rres:
                ret.append(rres.group())
        return ret


class TimelineWorkedOnDirective(TimelineChunksDirective):

    optional_arguments = 1

    def run(self):
        chunk = self.get_chunk_for_node(self.state.document, self.state)

        nested_node = docutils.nodes.paragraph()
        nested_parse_with_titles(self.state, self.content, nested_node)

        arguments = self.check_argument_is_roman(self.arguments)

        for argument in arguments:
            chunk.parse_worked_on(nested_node, argument)

        return []

    @classmethod
    def role(cls, name, rawtext, text, lineno, inliner,
             options={}, content=[]):
        chunk = cls.get_chunk_for_node(inliner.document, inliner)

        chunk.parse_worked_on(text, 'I')
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

        for argument in arguments:
            chunk.parse_dependencies(nested_node, argument)

        return []

    @classmethod
    def role(cls, name, rawtext, text, lineno, inliner,
             options={}, content=[]):
        chunk = cls.get_chunk_for_node(inliner.document, inliner)

        chunk.parse_dependencies(text, 'I')
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
