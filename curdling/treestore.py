# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, print_function

"""Generic Tree Store

This file holds a generic tree store implementation that is intended to
be used as a base class for more sophisticated UI components, like menus
or treeviews.
"""


class Node(object):
    """Node object that holds data for each item in the treeview

    This class is an opaque structure that holds info about which data
    each item in the tree view holds.

    Also, this structure is aware of its parent and child nodes.
    """
    def __init__(self, parent, data):
        self.parent = parent
        self.data = data
        self.nodes = []


class TreeStore(object):
    """A tree-like data structure to store nodes and subnodes

    Quick usage example:

        >>> tree = TreeStore()
        >>> item1 = tree.append(tree.root, title="Main Menu")
        >>> subitem1 = tree.append(item1, title="Sub Item 1")
        >>> subitem2 = tree.append(item1, title="Sub Item 2")
        >>> len(tree.children(tree.root)) == 1
        True
        >>> len(tree.children(item1)) == 2
        True

    """

    def __init__(self, **data):
        self.root = Node(None, data)

    def append(self, parent, **data):
        node = Node(parent, data)
        (parent or self.root).nodes.append(node)
        return node

    def append_node(self, parent, node):
        node = node
        parent = parent or node.parent or self.root
        (parent).nodes.append(node)
        return node

    def insert(self, parent, position, **data):
        node = Node(parent, data)
        (parent or self.root).nodes.insert(position, node)
        return node

    def insert_before(self, node, **data):
        parent = node and node.parent or self.root
        position = max(parent.nodes.index(node), 0)
        return self.insert(parent, position, **data)

    def insert_after(self, node, **data):
        parent = node and node.parent or self.root
        position = parent.nodes.index(node) + 1
        return self.insert(parent, position, **data)

    def parent(self, node):
        return node.parent

    def children(self, node):
        return (node or self.root).nodes

    def is_ancestor(self, node, descendant):
        return node.parent == descendant

    def depth(self, node):
        count = 0
        parent = node.parent
        while parent:
            count += 1
            parent = parent.parent
        return count

    def get_path(self, node):
        path = []
        current = node
        parent = node.parent

        while parent:
            path.append(parent.nodes.index(current))
            current = parent
            parent = parent.parent

        path.reverse()          # Left to right
        path.insert(0, 0)       # Root node
        return path

    def remove(self, node):
        node.parent.nodes.remove(node)
        node.parent = None

    def clear(self):
        self.root.nodes = []

    def reset(self):
        self.clear()
        self.root.data = {}

    def __getitem__(self, item):
        """List interface"""
        return self.root.nodes[item]
