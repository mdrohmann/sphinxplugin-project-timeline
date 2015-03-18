import re
from datetime import datetime
from . import utils


class SubmoduleNode(object):

    def __init__(self, tcs, fullid):
        parts = utils.split_name_and_submodule(fullid)
        self.name = parts[0]
        self.timechunk = tcs.chunks[parts[0]]
        if len(parts) > 1:
            self.submodule = parts[1]
        else:
            self.submodule = 0
        self.timechunk.submodules[self.submodule] = self
        self.children = []
        self.important = False
        self.group = None
        self.stats = None

    def set_important(self):
        self.important = True
        for child in self.children:
            if not child.important:
                child.set_important()

    def get_full_id(self, nowhitespace=False):
        ret = utils.id_from_name_and_submodule(self.name, self.submodule)
        if nowhitespace:
            ret = re.sub(r'[()]', r'', ret)
            ret = re.sub(r'\W+', r'-', ret)
        return ret

    def compute_work_stats(self, stats):
        if self.stats is None:
            tc = self.timechunk
            sn = self.submodule
            time_req = tc.get_requested_time(sn)
            minutes_worked = tc.get_worked_minutes(sn)
            time_worked = tc.get_worked_time(sn)  # in days
            complete = tc.get_completeness(sn)
            self.stats = {
                'time_req': time_req,
                'minutes_worked': minutes_worked,
                'time_worked': time_worked,
                'done': complete,
            }

            self.timechunk.add_stats(self.submodule, self.stats)

            total_stats = {
                'start_time': datetime.now(), 'time_req': {},
                'minutes_worked': {}, 'done': {}
            }
            for child in self.children:
                child.compute_work_stats(total_stats)

            fi = self.get_full_id()
            start_time = tc.get_start_time(sn)
            if 'start_time' in total_stats:
                total_stats['start_time'] = min(
                    start_time, total_stats['start_time'])
            else:
                total_stats['start_time'] = start_time
            total_stats['time_req'][fi] = time_req
            total_stats['minutes_worked'][fi] = minutes_worked
            total_stats['done'][fi] = complete

            self.total_stats = total_stats
        self.merge_stats(stats)

    def merge_stats(self, stats, other_stats=None):
        if other_stats is None:
            ts = self.total_stats
        else:
            ts = other_stats
        if len(stats) == 0:
            stats.update(ts)
        else:
            stats['start_time'] = min(ts['start_time'], stats['start_time'])
            for key in ['time_req', 'minutes_worked', 'done']:
                stats[key].update(ts[key])

    def get_title_with_submodule(self):
        return utils.id_from_name_and_submodule(
            self.timechunk.title, self.submodule)

    def visit_dependency_resolution(self, timechunks, parents):
        tc = self.timechunk
        for dep in tc.get_dependencies(self.submodule):
            try:
                depname = timechunks.get_chunk_id(dep, True, True)
                for sn in depname:
                    if sn in parents:
                        # TODO: make this a parser error
                        raise ValueError(
                            "Cyclic dependency in graph!"
                            "  {} depends on istself. {} -> {}"
                            .format(sn, sn, ' -> '.join(parents)))
                    self.children.append(SubmoduleNode(timechunks, sn))
            except KeyError:
                print "Could not resolve dependency {}".format(dep)
        #        tc.submodules[self.submodule] = self
        for child in self.children:
            child.visit_dependency_resolution(
                timechunks, parents + [self.get_full_id()])

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
        options.append('label = "{}"'.format(self.get_title_with_submodule()))
        options.append('href = ":ref:`{}`"'.format(pref))
        if len(options) > 0:
            ret += ' [{}]'.format(', '.join(options))
        return ret

    def get_blockdiag_nodes(self, nodes):
        nodes.add(self.blockdiag_node_format())
        for child in self.children:
            child.get_blockdiag_nodes(nodes)
