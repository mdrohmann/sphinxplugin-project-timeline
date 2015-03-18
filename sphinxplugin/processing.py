import docutils
import sphinxcontrib.blockdiag

from .nodes import TimelineNode, TaskTableSummaryNode
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
    tcs.update_aliases()

    tn.resolve_all_dependencies(tcs)

    lines, meta = tn.resolve_milestones(tcs)
    lines2, meta2 = tn.resolve_deadlines(tcs)
    lines += lines2
    meta += meta2

    tnsns = doctree.traverse(TaskTableSummaryNode)
    for tnsn in tnsns:
        tnsn.add_stat_table(tcs)

    nodes = set()
    for rc in tn.root_chunks:
        rc.traverse_edge_lines(lines)
        rc.get_blockdiag_nodes(nodes)

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
    descriptions1 = utils.make_descriptions_from_meta(meta, 'Milestone')

    table1 = utils.description_table(descriptions1, widths, headers)

    lines = ['orientation = portrait', ''] + list(nodes) + lines

    paragraph = docutils.nodes.paragraph()
    tn.blockdiag = sphinxcontrib.blockdiag.blockdiag_node()
    paragraph += tn.blockdiag
    paragraph += table1
    tn.blockdiag.code = (
        'blockdiag {{\n\t{}\n}}\n'.format('\n\t'.join(lines)))
    tn.blockdiag['code'] = tn.blockdiag.code
    tn.blockdiag['options'] = {}
    tn.blockdiag['ids'] = tn['ids']

    tn.replace_self(paragraph)

    # The following line, explicitly resolve the now created blockdiag node.
    # NB: It might also resolve other blockdiag nodes, but this should be safe.
    sphinxcontrib.blockdiag.on_doctree_resolved(app, doctree, fromdocname)
