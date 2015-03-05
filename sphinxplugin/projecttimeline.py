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

    env.timeline_chunks = dict(
        [(key, chunk) for (key, chunk) in env.timeline_chunks.iteritems()
         if chunk.docname != docname])
    env.timeline_groups = dict(
        [(key, group) for (key, group) in env.timeline_chunks.iteritems()
         if group.docname != docname])


def task_group_role(name, rawtext, text, lineno, inliner,
                    options={}, content=[]):

    env = inliner.document.settings.env

    if not hasattr(env, 'timeline_groups'):
        env.timeline_groups = {}

    env.timeline_groups[text] = {
        'parent': inliner.parent,
        'docname': inliner.docname
    }

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
