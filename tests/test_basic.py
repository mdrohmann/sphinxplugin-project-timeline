# -*- coding: utf-8 -*-

import pytest
import re
from docutils import nodes
from datetime import datetime
from sphinx_testing import with_app
from sphinxplugin.projecttimeline import (
    TimelineChunk, TimelineNode, parse_list_items,
    split_name_and_submodule, identify_time_chunk_name)


with_svg_app = with_app(
    srcdir='tests/docs/basic',
    buildername='html',
    #    write_docstring=True,
    confoverrides={
        'blockdiag_html_image_format': 'SVG'
    })


@with_svg_app
def test_build_html(app, status, warning):
    app.builder.build_all()
    source = (app.outdir / 'index.html').read_text(encoding='utf-8')
    # assert re.match('<div><img .*? src=".*?.png" .*?/></div>', source)


def test_split_names():
    res = split_name_and_submodule('test 1 (I)')
    assert res == ['test 1', 0]
    res = split_name_and_submodule('test 1')
    assert res == ['test 1']


def test_parse_list_items():
    p = nodes.paragraph()
    assert parse_list_items(p) == []
    el = nodes.enumerated_list()
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
    assert identify_time_chunk_name('test (I)', aliases) == [('test', 0)]
    assert identify_time_chunk_name(
        'test (I)', aliases, False, True) == [('test (I)')]
    assert identify_time_chunk_name('test (II)', aliases) == [('test', 1)]
    assert identify_time_chunk_name('test', aliases) == [('test', 0)]
    assert (
        identify_time_chunk_name('test', aliases, True)
        == [('test', 0), ('test', 1)])
    with pytest.raises(ValueError):
        identify_time_chunk_name('non-unique', aliases)


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

    tc = TimelineChunk(None)
    assert tc.parse_time_delta('1 hr') == 60
    assert tc.parse_time_delta('1') == 60
    assert tc.parse_time_delta('1h') == 60
    assert tc.parse_time_delta('1 hrs') == 60
    assert tc.parse_time_delta('1.5 hrs') == 90
    assert tc.parse_time_delta('1.5 hrs 20m') == 110
    assert tc.parse_time_delta('20 min') == 20
    assert tc.parse_time_delta('20 mins') == 20
    with pytest.raises(ValueError):
        tc.parse_time_delta('')


def compute_aliases(tcs):
    aliases = {}
    for tc in tcs.values():
        tc.update_aliases_with_backreference(aliases)
    return aliases


@pytest.fixture
def mock_tcs():
    from collections import namedtuple
    MockParent = namedtuple('parent', ['attributes'])
    p1 = MockParent({'ids': ['test1']})
    p2 = MockParent({'ids': ['test2']})
    tcs = {
        'test1': TimelineChunk(p1, 'test1'),
        'test2': TimelineChunk(p2, 'test2')}
    tc1 = tcs['test1']
    tc2 = tcs['test2']
    tc1.time_deltas = [1]
    tc2.time_deltas = [1]
    tc1.dependencies = {0: ['test2']}

    return tcs


def test_resolve_all_dependencies(mock_tcs):

    tcs = mock_tcs

    aliases = compute_aliases(tcs)

    tn = TimelineNode()
    tn.resolve_all_dependencies(tcs, aliases)

    root_chunks = tn.root_chunks
    assert len(root_chunks) == 1
    assert root_chunks[0].get_full_id() == 'test1 (I)'
    assert root_chunks[0].children[0].get_full_id() == 'test2 (I)'


@pytest.fixture
def test_resolve_all_dependencies_2(mock_tcs):

    tcs = mock_tcs

    tc1 = tcs['test1']
    tc1.time_deltas = [1, 1]

    aliases = compute_aliases(tcs)

    tn = TimelineNode()
    tn.resolve_all_dependencies(tcs, aliases)

    root_chunks = tn.root_chunks
    assert len(root_chunks) == 2
    assert root_chunks[0].get_full_id() == 'test1 (I)'
    assert root_chunks[1].get_full_id() == 'test1 (II)'
    assert len(root_chunks[1].children) == 0
    assert root_chunks[0].children[0].get_full_id() == 'test2 (I)'

    return tcs, tn


def test_blockdiag_edges(test_resolve_all_dependencies_2):
    tcs, tn = test_resolve_all_dependencies_2
    tc1 = tcs['test1']
    sn1 = tc1.get_submodule(0)
    lines = []
    sn1.traverse_edge_lines(lines)

    assert len(lines) == 1
    assert lines[0] == 'test2-I -> test1-I'


def test_blockdiag_edges_2(test_resolve_all_dependencies_2):
    tcs, tn = test_resolve_all_dependencies_2
    tc1 = tcs['test1']
    sn1 = tc1.get_submodule(0)
    sn1.important = True
    lines = []
    sn1.traverse_edge_lines(lines)

    assert len(lines) == 1
    assert lines[0] == 'test2-I -> test1-I [color = "red"]'


def test_blockdiag_nodes(test_resolve_all_dependencies_2):
    tcs, tn = test_resolve_all_dependencies_2
    nodes = set()
    for rc in tn.root_chunks:
        rc.get_blockdiag_nodes(nodes)

    assert len(nodes) == 3
    assert 'test1-I [label = "test1 (I)", href = ":ref:`test1`"]' in nodes
    assert 'test2-I [label = "test2 (I)", href = ":ref:`test2`"]' in nodes


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
    assert 'test2-I [label = "test2 (I)", href = ":ref:`test2`"]' in nodes


def test_resolve_all_dependencies_3(mock_tcs):

    tcs = mock_tcs
    tc2 = tcs['test2']
    tc2.time_deltas = [1, 1]

    aliases = compute_aliases(tcs)

    tn = TimelineNode()
    tn.resolve_all_dependencies(tcs, aliases)

    root_chunks = tn.root_chunks
    assert len(root_chunks) == 1
    assert root_chunks[0].get_full_id() == 'test1 (I)'
    assert root_chunks[0].children[0].get_full_id() == 'test2 (I)'
    assert root_chunks[0].children[1].get_full_id() == 'test2 (II)'


def test_resolve_all_dependencies_4(mock_tcs):

    tcs = mock_tcs
    tc2 = tcs['test2']
    tc2.dependencies = {0: ['test1']}

    aliases = compute_aliases(tcs)

    tn = TimelineNode()
    with pytest.raises(ValueError):
        tn.resolve_all_dependencies(tcs, aliases)


def test_resolve_all_dependencies_5(mock_tcs):

    tcs = mock_tcs
    tc1 = tcs['test1']
    tc1.time_deltas = [1, 1]
    tc2 = tcs['test2']
    tc2.dependencies = {0: ['test1 (I)']}

    aliases = compute_aliases(tcs)

    tn = TimelineNode()
    tn.resolve_all_dependencies(tcs, aliases)
    with pytest.raises(ValueError):
        tc1.get_submodule(0)





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
