# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, print_function
from curdling.treestore import TreeStore, Node


def test_root_node():
    # Given I have some data
    data = {'name': 'Mr. Testingson', 'age': 234}

    # When I create a new tree, passing the above data
    tree = TreeStore(**data)

    # Then, the root is created with that data
    tree.root.data.should.equal(data)


def test_node_data():
    # Given I create a tree
    tree = TreeStore()

    # When append a couple nodes
    node1 = tree.append(tree.root, attr1='foo', attr2='bar')
    pumpkin = tree.append(tree.root, name='Joseph', lastname='Pumpkinson')

    # Then I see that the node contains the kwargs values as a
    # dictionary in its `data` attribute
    node1.data.should.equal({'attr1': 'foo', 'attr2': 'bar'})
    pumpkin.data.should.equal({'name': 'Joseph', 'lastname': 'Pumpkinson'})


def test_append():
    # Given I have a new tree store
    nav = TreeStore()

    # When I add some items to it
    item1 = nav.append(nav.root, title='Item 1')
    item2 = nav.append(nav.root, title='Item 2', foo='bar')

    # Then, I see that new nodes were added to root level of the tree
    # store with the same data I've informed before
    item1.should.be.a(Node)
    nav.parent(item1).should.equal(nav.root)
    item2.should.be.a(Node)
    nav.parent(item2).should.equal(nav.root)


def test_append_to_nodes():
    # Given I have a new tree with a root node
    nav = TreeStore(title='Root')

    # When I add sub items
    dnn = nav.append(nav.root, title='Dining & night life')
    fitness = nav.append(nav.root, title='Fitness')

    # Then I can browse these items and ensure that they were added as
    # children to the nav.root node.
    nav.children(nav.root).should.equal([dnn, fitness])
    nav.parent(dnn).should.equal(nav.root)
    nav.parent(fitness).should.equal(nav.root)


def test_append_node_to_nodes():
    "Yo dawg! I heard you like nodes, so I put a node into ya node"

    # Given I have a tree with a root node
    nav = TreeStore(title='Root')

    # When I add nodes to this root node, and nodes to the child node
    dnn = nav.append(nav.root, title='Dining & night life')
    restaurants = nav.append(dnn, title='Restaurants')
    bars = nav.append(dnn, title='Bars')

    # Then I can see that my child node also has nodes
    nav.parent(bars).should.equal(dnn)
    nav.parent(restaurants).should.equal(dnn)
    nav.parent(dnn).should.equal(nav.root)
    nav.children(dnn).should.equal([restaurants, bars])

    # Also, I can see that both bars and restaurants have common ancestors
    nav.is_ancestor(bars, dnn)
    nav.is_ancestor(bars, nav.root)
    nav.is_ancestor(restaurants, dnn)
    nav.is_ancestor(restaurants, nav.root)

    # And also, that both bars and restaurants are in the same depth in
    # our tree
    nav.depth(nav.root).should.equal(0)
    nav.depth(dnn).should.equal(1)
    nav.depth(bars).should.equal(2)
    nav.depth(restaurants).should.equal(2)


def test_node_get_path():
    # Given I have a tree with some sub nodes and some sub sub sub nodes
    tree = TreeStore()
    node1 = tree.append(tree.root, title='node1')
    node1_1 = tree.append(node1, title='node1_1')
    node1_2 = tree.append(node1, title='node1_2')
    node1_2_1 = tree.append(node1_2, title='node1_2_1')
    node1_2_2 = tree.append(node1_2, title='node1_2_2')

    # When I check the paths, Then I see that works
    tree.get_path(tree.root).should.equal([0])
    tree.get_path(node1).should.equal([0, 0])
    tree.get_path(node1_1).should.equal([0, 0, 0])
    tree.get_path(node1_2).should.equal([0, 0, 1])
    tree.get_path(node1_2_1).should.equal([0, 0, 1, 0])
    tree.get_path(node1_2_2).should.equal([0, 0, 1, 1])


def test_remove_nodes():
    # Given I have a tree with a node and subnodes
    nav = TreeStore(title='Root')
    subnode1 = nav.append(nav.root, title='Sub node 1')
    subnode2 = nav.append(nav.root, title='Sub node 2')
    nav.children(nav.root).should.equal([subnode1, subnode2])

    # When I remove a subnode
    nav.remove(subnode2)

    # Then I see the node is gone
    nav.children(nav.root).should.equal([subnode1])


def test_remove_subnodes():
    # Given I have a tree with some nodes and subnodes
    nav = TreeStore(title='Root')
    subnode1 = nav.append(nav.root, title='Sub node 1')
    ssnode1 = nav.append(subnode1, title='Sub sub node 1')
    ssnode2 = nav.append(subnode1, title='Sub sub node 2')
    subnode2 = nav.append(nav.root, title='Sub node 2')
    ssnode2_1 = nav.append(subnode2, title='Sub node 2.1')

    # When I remove a subnode with children
    nav.remove(subnode1)

    # Then I see that the node and its children were removed is not part
    # of the tree anymore, but without bothering other nodes
    nav.children(nav.root).should.equal([subnode2])
    nav.children(subnode2).should.equal([ssnode2_1])

    # Side note: The nodes are note deleted from memory. They're still
    # available and valid. You can still reattach them to the tree. But
    # they won't be available in the tree anymore
    nav.children(subnode1).should.equal([ssnode1, ssnode2])
    nav.is_ancestor(subnode1, nav.root).should.be.false


def test_insert():
    # Given I have a tree with some nodes
    tree = TreeStore()
    node1 = tree.append(tree.root, title='node 1')
    node2 = tree.append(tree.root, title='node 2')
    node3 = tree.append(tree.root, title='node 3')

    # When I insert some new nodes
    node1_1 = tree.insert(tree.root, 1, title='node 1.1')
    node2_2 = tree.insert(tree.root, 3, title='node 2.2')

    # Then I see that they were inserted in the right order
    tree.children(tree.root).should.equal(
        [node1, node1_1, node2, node2_2, node3])


def test_insert_before_tree():
    # Given I have a tree with some root nodes
    tree = TreeStore()
    node1 = tree.append(tree.root, title='node 1')
    node2 = tree.append(tree.root, title='node 2')

    # When I insert before and after
    node0 = tree.insert_before(node1, title='node 0')
    node1_2 = tree.insert_before(node2, title='node 1.2')

    # Then I see my items ordered properly in my tree
    tree.children(tree.root).should.equal([
        node0, node1, node1_2, node2])


def test_insert_before():
    # Given I have a tree with some nodes
    tree = TreeStore(title='Root')
    node1 = tree.append(tree.root, title='node 1')
    node2 = tree.append(tree.root, title='node 2')

    # When I insert before and after
    node0 = tree.insert_before(node1, title='node 0')
    node1_2 = tree.insert_before(node2, title='node 1.2')

    # Then I see my items ordered properly in my tree
    tree.children(tree.root).should.equal([
        node0, node1, node1_2, node2])


def test_insert_after():
    # Given I have a tree with some nodes
    tree = TreeStore(title='Tree.Root')
    node1 = tree.append(tree.root, title='node 1')
    node2 = tree.append(tree.root, title='node 2')

    # When I insert after
    node1_2 = tree.insert_after(node1, title='node 1.2')
    node3 = tree.insert_after(node2, title='node3')

    # Then I see my items ordered properly in my tree
    tree.children(tree.root).should.equal([
        node1, node1_2, node2, node3])


def test_insert_after_tree():
    # Given I have a tree with some nodes
    tree = TreeStore()
    node1 = tree.append(tree.root, title='node 1')
    node2 = tree.append(tree.root, title='node 2')

    # When I insert after
    node1_2 = tree.insert_after(node1, title='node 1.2')
    node3 = tree.insert_after(node2, title='node3')

    # Then I see my items ordered properly in my tree
    tree.children(tree.root).should.equal([
        node1, node1_2, node2, node3])


def test_clear_tree():
    # Given I have a tree with some nodes
    tree = TreeStore()
    tree.append(tree.root, title='node 1')
    tree.append(tree.root, title='node 2')
    tree.append(tree.root, title='node 3')

    # When I call the clear() method
    tree.clear()

    # Everything is cleaned up from the tree
    tree.children(tree.root).should.be.empty


def test_reset_tree():
    # Given I have a tree with some data in the root node
    tree = TreeStore(blah=1, bleh=2, blih='bloh')
    tree.append(tree.root, foo='bar')

    # When I reset the tree
    tree.reset()

    # Then I see that both nodes and data from the root node were
    # cleaned
    tree.root.data.should.be.empty
    tree.children(tree.root).should.be.empty


def test_tree_should_act_like_a_list():
    # Given I have a tree with some nodes
    tree = TreeStore()
    node0 = tree.append(tree.root, foo='bar')
    node1 = tree.append(tree.root, bar='baz')

    # When I try to access the above node using the square brackets or
    # to use the tree like a list. Then things don't blow up.
    tree[0].should.equal(node0)
    tree[1].should.equal(node1)
    tree.children(tree.root).should.equal([n for n in tree])
