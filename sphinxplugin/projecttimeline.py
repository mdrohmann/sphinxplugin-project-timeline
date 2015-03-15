from .timeline_chunk import TimelineChunksContainer
from .nodes import (TimelineBlockdiagNode, TimelineNode)
from .directives import (
    TimelineWorkedOnDirective, TimelineRequestedDirective,
    TimelineDependencyDirective, TimelineDirective)
from .processing import process_timelines


def purge_timelines(app, env, docname):
    """
    purge all environment variables created from the document `docname`.
    """
    if not hasattr(env, 'timeline_chunks'):
        return

    env.timeline_chunks.purge(docname)


def task_group_role(name, rawtext, text, lineno, inliner,
                    options={}, content=[]):

    env = inliner.document.settings.env

    if not hasattr(env, 'timeline_chunks'):
        env.timeline_chunks = TimelineChunksContainer()

    env.timeline_chunks.add_group(text, inliner.parent, inliner.docname)

    return [], []


def on_builder_inited(self):
    pass
#    config = self.builder.config
#    blockdiag_loaded = 'sphinxcontrib.blockdiag' in config.extensions


def setup(app):

    app.add_node(TimelineBlockdiagNode)
    app.add_node(TimelineNode)
    app.add_role('task-group', task_group_role)
    app.add_role(
        'worked-on',
        lambda *args: TimelineWorkedOnDirective.role(*args))
    app.add_directive('worked-on', TimelineWorkedOnDirective)
    app.add_role(
        'requested-time',
        lambda *args: TimelineRequestedDirective.role(*args))
    app.add_directive('requested-time', TimelineRequestedDirective)
    app.add_role(
        'dependent-tasks',
        lambda *args: TimelineDependencyDirective.role(*args))
    app.add_directive('dependent-tasks', TimelineDependencyDirective)
    app.add_directive('timeline', TimelineDirective)
    app.connect('doctree-resolved', process_timelines)
    app.connect('builder-inited', on_builder_inited)
    app.connect('env-purge-doc', purge_timelines)

    # TODO:
    # - [ ] add javascript source code in order to manipulate the progress
    #       interactively

    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
