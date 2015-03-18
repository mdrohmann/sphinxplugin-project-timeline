# -*- coding: utf-8 -*-

import pytest
import re
import math
from docutils import nodes
from datetime import datetime, timedelta
from sphinx_testing import with_app
from sphinxplugin.timeline_chunk import (
    TimelineChunk, TimelineChunksContainer)
from sphinxplugin.nodes import TimelineNode
from sphinxplugin.submodule_node import SubmoduleNode
from sphinxplugin.utils import (
    parse_list_items, add_stats, make_descriptions_from_meta,
    split_name_and_submodule,
    parse_time_delta)


from collections import namedtuple
MockParent = namedtuple('parent', ['attributes'])

with_svg_app = with_app(
    srcdir='tests/docs/complete',
    buildername='html',
    #    write_docstring=True,
    confoverrides={
        'blockdiag_html_image_format': 'SVG'
    })


@with_svg_app
def test_build_html(app, status, warning):
    app.builder.build_all()
    source = (app.outdir / 'index.html').read_text(encoding='utf-8')
    import pudb
    pudb.set_trace()
    # assert re.match('<div><img .*? src=".*?.png" .*?/></div>', source)


def test_split_names():
    res = split_name_and_submodule('test 1 (I)')
    assert res == ['test 1', 0]
    res = split_name_and_submodule('test 1')
    assert res == ['test 1']


@pytest.fixture(params=[nodes.enumerated_list, nodes.bullet_list])
def get_list(request):
    p = nodes.paragraph()
    el = request.param()
    return p, el


@pytest.fixture()
def tc_worked_on():
    return TimelineChunk(MockParent({'ids': ['test1']}))


def test_parse_worked_on_1(tc_worked_on):
    tc = tc_worked_on
    line = '2015-01-01:  2hrs 90%'
    tc._parse_worked_on_line(line, 0)
    assert tc.completeness[0] == 0.9
    assert tc.start_times[0] == datetime(2015, 1, 1)
    assert tc.worked_minutes[0] == 120


def test_parse_worked_on_2(tc_worked_on):
    tc = tc_worked_on
    line = '15/01/01: 2hrs 30min 90%'
    tc._parse_worked_on_line(line, 0)
    assert tc.completeness[0] == 0.9
    assert tc.start_times[0] == datetime(2001, 1, 15)
    assert tc.worked_minutes[0] == 150

    line = '05/01/01: 30min 90%'
    tc._parse_worked_on_line(line, 0)
    assert tc.completeness[0] == 0.9
    assert tc.start_times[0] == datetime(2001, 1, 15)
    assert tc.worked_minutes[0] == 180


def test_parse_worked_on_3(tc_worked_on):
    tc = tc_worked_on
    line = 'May 2nd, 2015:30min 90%'
    tc._parse_worked_on_line(line, 0)
    assert tc.completeness[0] == 0.9
    assert tc.start_times[0] == datetime(2015, 5, 2)
    assert tc.worked_minutes[0] == 30


def test_parse_worked_on_4(tc_worked_on):
    tc = tc_worked_on
    line = '30min 90%'
    tc._parse_worked_on_line(line, 0)
    assert tc.completeness[0] == 0.9
    assert abs(tc.get_start_time(0) - datetime.now()).days == 0
    assert tc.worked_minutes[0] == 30


def test_parse_worked_on_5(tc_worked_on):
    tc = tc_worked_on
    line = '1/1/01: 90%'
    tc._parse_worked_on_line(line, 0)
    assert tc.completeness[0] == 0.9
    assert tc.get_start_time(0) == datetime(2001, 1, 1)
    assert tc.get_worked_minutes(0) == 0


def test_parse_worked_on_6(tc_worked_on):
    tc = tc_worked_on
    line = '1/1/01: 1.5hrs'
    tc._parse_worked_on_line(line, 0)
    assert tc.get_completeness(0) == 0.
    assert tc.get_start_time(0) == datetime(2001, 1, 1)
    assert tc.get_worked_minutes(0) == 90


def test_parse_worked_on_7(tc_worked_on):
    tc = tc_worked_on
    line = '1/1/01'
    tc._parse_worked_on_line(line, 0)
    assert tc.get_completeness(0) == 0.
    assert tc.get_start_time(0) == datetime(2001, 1, 1)
    assert tc.get_worked_minutes(0) == 0


def test_parse_list_items(get_list):
    p, el = get_list
    assert parse_list_items(p) == []
    p.append(el)
    item1 = nodes.list_item()
    paragraph1 = nodes.paragraph()
    el.append(item1)
    with pytest.raises(ValueError):
        parse_list_items(p)

    item1.append(paragraph1)
    text1 = nodes.Text('test')
    paragraph1.append(text1)
    assert parse_list_items(p) == ['test']

    item2 = nodes.list_item()
    paragraph2 = nodes.paragraph()
    text21 = nodes.Text('test2')
    text22 = nodes.Text('test3')
    el.append(item2)
    item2.append(paragraph2)
    paragraph2.append(text21)
    paragraph2.append(text22)

    assert parse_list_items(p) == ['test', 'test2 test3']


def test_identify_time_chunk_name():
    aliases = {
        'test': [('test', 2)],
        'non-unique': [('test', 2), ('other', 1)]
    }

    tcc = TimelineChunksContainer()
    tcc.aliases = aliases

    assert tcc.get_chunk_id('test (I)') == [('test', 0)]
    assert tcc.get_chunk_id(
        'test (I)', False, True) == [('test (I)')]
    assert tcc.get_chunk_id('test (II)') == [('test', 1)]
    assert tcc.get_chunk_id('test') == [('test', 0)]
    assert (
        tcc.get_chunk_id('test', True)
        == [('test', 0), ('test', 1)])
    with pytest.raises(ValueError):
        tcc.get_chunk_id('non-unique')


def test_TimelineNode():
    tn = TimelineNode(None)
    res = tn._parse_list_items(['link1'])
    assert res == [{'time': None, 'xref': 'link1', 'submodules': []}]
    res = tn._parse_list_items(['link1 (I, IV)'])
    assert res == [{'time': None, 'xref': 'link1', 'submodules': [0, 3]}]
    res = tn._parse_list_items(['link1 (i, IV)'])
    assert res == [{'time': None, 'xref': 'link1', 'submodules': [0, 3]}]
    res = tn._parse_list_items(['link1 (i, IV)', 'link2'])
    assert res == [{'time': None, 'xref': 'link1', 'submodules': [0, 3]},
                   {'time': None, 'xref': 'link2', 'submodules': []}]
    res = tn._parse_list_items(
        ['2015-01-01 link1 (i, IV)', '02-01-2012 link2'])
    assert res == [
        {'time': datetime(2015, 1, 1), 'xref': 'link1', 'submodules': [0, 3]},
        {'time': datetime(2012, 2, 1), 'xref': 'link2', 'submodules': []}]


def test_time_delta():

    assert parse_time_delta('1 hr') == 60
    assert parse_time_delta('1') == 60
    assert parse_time_delta('1h') == 60
    assert parse_time_delta('1 hrs') == 60
    assert parse_time_delta('1.5 hrs') == 90
    assert parse_time_delta('1.5 hrs 20m') == 110
    assert parse_time_delta('20 min') == 20
    assert parse_time_delta('20 mins') == 20
    with pytest.raises(ValueError):
        parse_time_delta('')


def compute_aliases(tcs):
    tcs.aliases = {}
    tcs.update_aliases()


@pytest.fixture
def mock_tcs():
    p1 = MockParent({'ids': ['test1']})
    p2 = MockParent({'ids': ['test2']})
    tcs = TimelineChunksContainer()
    tcs.chunks = {
        'test1': TimelineChunk(p1, 'test1', 'test1'),
        'test-2': TimelineChunk(p2, 'Test 2', 'test2')}
    tc1 = tcs.chunks['test1']
    tc2 = tcs.chunks['test-2']
    tc1.time_deltas = [60]
    tc2.time_deltas = [60]
    tc1.dependencies = {0: ['test-2']}

    tc1.worked_minutes = {0: 30}
    tc2.worked_minutes = {0: 60}
    tc1.completeness = {0: 0.5}
    tc2.completeness = {0: 0.5}
    tc1.start_times = {
        0: datetime.now() - timedelta(7, 0, 0)}

    return tcs


def test_work_stats(mock_tcs):
    tcs = mock_tcs
    sn1 = SubmoduleNode(tcs, 'test1 (I)')
    sn1.children.append(SubmoduleNode(tcs, 'test-2 (I)'))
    stats = {}
    sn1.compute_work_stats(stats)
    res = add_stats(stats)
    assert res['time_req'] == 120
    assert res['minutes_worked'] == 90
    assert res['done'] == 0.5
    assert math.floor(res['time_worked']) == 7

    rows = make_descriptions_from_meta([res], 'Milestone')
    fmt = '%Y-%m-%d'
    eta1 = (datetime.now() + timedelta(7)).strftime(fmt)
    eta2 = (datetime.now() + timedelta(int(7/1.5))).strftime(fmt)
    assert rows == [
        ['Milestone 1', '2.00 h', '50.0 %',
         '1.50 h', '0.50 h', '1.50 h', '7.00 d', '1.50',
         '50 %', eta1, eta2
         ]]


def test_resolve_all_dependencies(mock_tcs):

    tcs = mock_tcs

    compute_aliases(tcs)

    tn = TimelineNode()
    tn.resolve_all_dependencies(tcs)

    root_chunks = tn.root_chunks
    assert len(root_chunks) == 1
    assert root_chunks[0].get_full_id() == 'test1 (I)'
    assert root_chunks[0].children[0].get_full_id() == 'test-2 (I)'


@pytest.fixture
def test_resolve_all_dependencies_2(mock_tcs):

    tcs = mock_tcs

    tc1 = tcs.chunks['test1']
    tc1.time_deltas = [1, 1]

    compute_aliases(tcs)

    tn = TimelineNode()
    tn.resolve_all_dependencies(tcs)

    root_chunks = tn.root_chunks
    assert len(root_chunks) == 2
    assert root_chunks[0].get_full_id() == 'test1 (I)'
    assert root_chunks[1].get_full_id() == 'test1 (II)'
    assert len(root_chunks[1].children) == 0
    assert root_chunks[0].children[0].get_full_id() == 'test-2 (I)'

    return tcs, tn


def test_blockdiag_edges(test_resolve_all_dependencies_2):
    tcs, tn = test_resolve_all_dependencies_2
    tc1 = tcs.chunks['test1']
    sn1 = tc1.get_submodule(0)
    lines = []
    sn1.traverse_edge_lines(lines)

    assert len(lines) == 1
    assert lines[0] == 'test-2-I -> test1-I'


def test_blockdiag_edges_2(test_resolve_all_dependencies_2):
    tcs, tn = test_resolve_all_dependencies_2
    tc1 = tcs.chunks['test1']
    sn1 = tc1.get_submodule(0)
    sn1.important = True
    lines = []
    sn1.traverse_edge_lines(lines)

    assert len(lines) == 1
    assert lines[0] == 'test-2-I -> test1-I [color = "red"]'


def test_blockdiag_nodes(test_resolve_all_dependencies_2):
    tcs, tn = test_resolve_all_dependencies_2
    nodes = set()
    for rc in tn.root_chunks:
        rc.get_blockdiag_nodes(nodes)

    assert len(nodes) == 3
    assert 'test1-I [label = "test1 (I)", href = ":ref:`test1`"]' in nodes
    assert 'test-2-I [label = "Test 2 (I)", href = ":ref:`test2`"]' in nodes


def test_blockdiag_nodes_2(test_resolve_all_dependencies_2):
    tcs, tn = test_resolve_all_dependencies_2
    nodes = set()
    rc1 = tn.root_chunks[0]
    rc1.important = True
    rc1.group = 'Milestone1'
    for rc in tn.root_chunks:
        rc.get_blockdiag_nodes(nodes)

    assert len(nodes) == 3
    assert (
        'test1-I '
        '[group = "Milestone1", linecolor = "red", label = "test1 (I)",'
        ' href = ":ref:`test1`"]'
        in nodes)
    assert 'test-2-I [label = "Test 2 (I)", href = ":ref:`test2`"]' in nodes


def test_resolve_all_dependencies_3(mock_tcs):

    tcs = mock_tcs
    tc2 = tcs.chunks['test-2']
    tc2.time_deltas = [1, 1]

    compute_aliases(tcs)

    tn = TimelineNode()
    tn.resolve_all_dependencies(tcs)

    root_chunks = tn.root_chunks
    assert len(root_chunks) == 1
    assert root_chunks[0].get_full_id() == 'test1 (I)'
    assert root_chunks[0].children[0].get_full_id() == 'test-2 (I)'
    assert root_chunks[0].children[1].get_full_id() == 'test-2 (II)'


def test_resolve_all_dependencies_4(mock_tcs):

    tcs = mock_tcs
    tc2 = tcs.chunks['test-2']
    tc2.dependencies = {0: ['test1']}

    compute_aliases(tcs)

    tn = TimelineNode()
    with pytest.raises(ValueError):
        tn.resolve_all_dependencies(tcs)


def test_resolve_all_dependencies_5(mock_tcs):

    tcs = mock_tcs
    tc1 = tcs.chunks['test1']
    tc1.time_deltas = [1, 1]
    tc2 = tcs.chunks['test-2']
    tc2.dependencies = {0: ['test1 (I)']}

    compute_aliases(tcs)

    tn = TimelineNode()
    tn.resolve_all_dependencies(tcs)
    with pytest.raises(ValueError):
        tc1.container = tcs
        tc2.container = tcs
        tc1.get_submodule(0)


def test_stat_tables(mock_tcs):
    pass



# class TestTimelineNode(unittest.TestCase):
#
#     def get_doctree(self, app, doctree, fromdocname):
#         self.dt = doctree
#         import pudb
#         pudb.set_trace()
#
#     @with_svg_app
#     def test_milestones(self, app, status, warning):
#         """
#         .. timeline::
#
#             Milestones
#             ----------
#
#             A. subject
#         ..
#         """
#
#         app.connect('doctree-resolved', self.get_doctree)
#         app.builder.build_all()
#
#         import pudb
#         pudb.set_trace()

# @with_app(buildername='latex', srcdir='tests/docs/basic/')
# def test_build_latex(app, status, warning):
#     app.builder.build_all()
# 
# 
# @with_app(buildername='epub', srcdir='tests/docs/basic/')
# def test_build_epub(app, status, warning):
#     app.builder.build_all()
# 
# 
# @with_app(buildername='json', srcdir='tests/docs/basic/')
# def test_build_json(app, status, warning):
#     app.builder.build_all()
