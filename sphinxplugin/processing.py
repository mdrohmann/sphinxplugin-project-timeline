import docutils
import sphinxcontrib.blockdiag

from .nodes import TimelineNode
from . import utils


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
    if not hasattr(env, 'timeline_groups'):
        tgs = {}
    else:
        tgs = env.timeline_groups

    aliases = {}
    for tc in tcs.values():
        tc.update_aliases_with_backreference(aliases, tgs)

#    import pudb
#    pudb.set_trace()
#
    tn.resolve_all_dependencies(tcs, aliases)
    lines, meta = tn.resolve_milestones(tcs, aliases)
    lines += tn.resolve_deadlines(tcs, aliases)
    nodes = set()
    for rc in tn.root_chunks:
        rc.traverse_edge_lines(lines)
        rc.get_blockdiag_nodes(nodes)

    headers = [
        '              ',
        'Requested time',
        'Spent work hrs',
        'Hours left I  ',
        'Hours left II ',
        'Spent days    ',
        'Work factor   ',
        'Advance / week',
        'ETA           ',
    ]
    widths = [16] * len(headers)
    descriptions = utils.make_descriptions_from_meta(meta, 'Milestone')

    table = utils.description_table(descriptions, widths, headers)

    lines = list(nodes) + lines

    paragraph = docutils.nodes.paragraph()
    tn.blockdiag = sphinxcontrib.blockdiag.blockdiag_node()
    paragraph += tn.blockdiag
    paragraph += table
    tn.blockdiag.code = (
        'blockdiag {{\n\t{}\n}}\n'.format('\n\t'.join(lines)))
    tn.blockdiag['code'] = tn.blockdiag.code
    tn.blockdiag['options'] = {}
    tn.blockdiag['ids'] = tn['ids']

    tn.replace_self(paragraph)

    # The following line, explicitly resolve the now created blockdiag node.
    # NB: It might also resolve other blockdiag nodes, but this should be safe.
    sphinxcontrib.blockdiag.on_doctree_resolved(app, doctree, fromdocname)
