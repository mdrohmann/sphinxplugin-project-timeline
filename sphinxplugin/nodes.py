import sphinxcontrib.blockdiag
import docutils
import dateutil

from .submodule_node import SubmoduleNode
from . import utils


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
            name_submodule = utils.split_name_and_submodule(item_string)
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
            for i in [utils.id_from_name_and_submodule(tk, y)
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
                try:
                    depnames = utils.identify_time_chunk_name(
                        dep, aliases, True, True)
                    for dn in depnames:
                        submodules_with_parents.add(dn)
                except KeyError:
                    print "could not resolve dependency {}".format(dep)

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

    def _resolve_milestone(self, milestone, timechunks, aliases, stats):
        mn = milestone[0]
        ms = milestone[1]
        ms_key = utils.identify_time_chunk_name(ms['xref'], aliases)
        ms_chunk = timechunks[ms_key[0][0]]
        submodules = ms['submodules'] or range(ms_chunk.num_submodules())
        for sm in submodules:
            submodule = ms_chunk.get_submodule(sm)
            stats = submodule.compute_work_stats(stats)
            submodule.set_important()
            submodule.group = 'Milestone{}'.format(mn)

    def resolve_milestones(self, timechunks, aliases):
        grouplines = []
        stats = []
        for milestone in enumerate(self.milestones):
            mstats = {}
            self._resolve_milestone(milestone, timechunks, aliases, mstats)
            stats.append(utils.add_stats(mstats))
            grouplines += [
                'group Milestone{}'.format(milestone[0]) + ' {',
                '  label = "Milestone {}"'.format(milestone[0]),
                '  color = "#aaaaaa"',
                '}']
        return grouplines, stats

    def _resolve_deadline(self, deadline, timechunks, aliases):
        dn = deadline[0]
        dl = deadline[1]
        dl_key = utils.identify_time_chunk_name(dl['xref'], aliases)
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
        strings = utils.parse_list_items(enumeration)
        return self._parse_list_items(strings)

    def _get_list_items_from_list(self, section):

        res = []
        for enumeration in section.traverse(utils.is_list_or_enumeration):
            res += self._parse_list_items_from_doctree(enumeration)
        return res

    def add_milestones_from_section(self, milestones_section):
        self.milestones = self._get_list_items_from_list(milestones_section)

    def add_deadlines_from_section(self, deadlines_section):
        self.deadlines = self._get_list_items_from_list(deadlines_section)