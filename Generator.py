#!/usr/bin/python

import logging
import random
import sys
import numpy as np

from Parser import Parser
from Lexer import Lexer
from YapyGraph.Vertex import Vertex

import functools
import graphviz as gv

graph = functools.partial(gv.Graph, format='jpg', engine='neato')

class Generator(object):
    """

    Transformation engine for graphs. Given a set of Productions of the form
    lhs ==> rhs, and using a starting graph G, uses graph isomorphic searching
    to find instances of a lhs in G and replaces the lhs vertices with the rhs.
    The engine continues to apply these transformations until G contains a
    given number of vertices. This assumes that the productions generally
    increase the number of vertices.

    Usage: Either use the all-inclusive main() method which checks the 
    command-line arguments, or call applyProductions() yourself which
    takes a starting graph, list of productions, and a dictionary of
    configuration options.
    """

    #--------------------------------------------------------------------------
    def applyProductions(self, startGraph, productions, config):
        """
        Randomly applies a Production from the given list of Productions to the
        specified starting graph until the graph contains at least the number
        of vertices specified by the config option "min_vertices". This assumes
        that the productions generally increase the number of vertices.
        Inputs: 
            * startGraph - Graph to begin applying transformations
            * productions - list of Production objects
            * config - dictionary of options
        Outputs: None
        """
        def add_nodes(graph, nodes):
            for n in nodes:
                if isinstance(n, tuple):
                    graph.node(n[0], **n[1])
                else:
                    graph.node(n)
            return graph

        def add_edges(graph, edges):
            for e in edges:
                if isinstance(e[0], tuple):
                    graph.edge(*e[0], **e[1])
                else:
                    graph.edge(*e)
            return graph
        print 'Starting Graph: ', startGraph
        iteration = 0
        edges = [(v1.name[0] + v1.id[1:], v2.name[0] + v2.id[1:]) for (v1, v2) in startGraph.edges]
        vertices = [v.name[0] + v.id[1:] for v in startGraph.vertices]
        graph_name = NAME + '_' + str(iteration)
        add_edges(add_nodes(graph(), vertices),edges).render('img/' + graph_name)
        # logging.debug('In applyProductions')
        #while startGraph.numVertices < int(config['min_vertices']):
        while startGraph.numVertices < int(NUM_VERTICES):
            # matchingProductions is a list of (Production, mapping) 
            # pairs where mapping is {vid->vid} dictionary of where 
            # the production's lhs vertices can be found in startGraph.
            #matchingProductions = self._findMatchingProductions(startGraph, productions)
            matchingProductions = self._findWeightedMatchingProductions(startGraph, productions)
            
            if len(matchingProductions) == 0:
                raise RuntimeError('No productions match the given graph.')

            (prod, mapping) = random.choice(matchingProductions)
            # print "Prod: ", prod.lhs, " => ", prod.rhs
            # (prod, mapping) = np.random.choice(matchingProductions, None, True, [80,20])

            self._applyProduction(startGraph, prod, mapping)

            iteration += 1
            edges = [(v1.name[0] + v1.id[1:], v2.name[0] + v2.id[1:]) for (v1, v2) in startGraph.edges]
            vertices = [v.name[0] + v.id[1:] for v in startGraph.vertices]
            graph_name = NAME + '_' + str(iteration)
            add_edges(add_nodes(graph(), vertices),edges).render('img/' + graph_name)

        self._showCounts(productions)
        print 'Final Graph: ', startGraph, '\n'

        vertices = [v.name[0] + v.id[1:] for v in startGraph.vertices]
        #print vertices
        edges = [(v1.name[0] + v1.id[1:], v2.name[0] + v2.id[1:]) for (v1, v2) in startGraph.edges]

        
        for e in edges:
            (v1, v2) = e
            print v1, '->', v2

        graph_name = NAME + '_' + NUM_VERTICES        
        add_edges(add_nodes(graph(), vertices),edges).render('img/' + graph_name) 

    def outputReverseFile(self, filename, f):
        text_filename = filename + ".txt"
        
        grammarFile = open(GRAMMAR, "r")
        rules = []
        for line in grammarFile:
            if "==>" in line:
                idx = line.index("==>")
                lhs = line[:idx].strip()
                rhs = line[idx+3:-2].strip()
                rule = rhs + " ==> " + lhs
                rules.append(rule)

        text_file = open(text_filename, "w")

        edges = [(v1.name[0]+v1.id[1:], v2.name[0]+v2.id[1:]) for (v1,v2) in f.startGraph.edges]
        start_graph = ""
        for (v1,v2) in edges:
            start_graph += v1 + "->" + v2 +", "
        start_graph = start_graph[:-2] + ";"
        output = "productions {\n"
        output += "# Start graph\n"
        output += start_graph
        output += "\n\n# Rules\n"
        for rule in rules:
            output += rule + ";\n"
        output += "}"
        text_file.write(output)
        text_file.close()
        

    #--------------------------------------------------------------------------
    def generateFromFile(self, filename):
        """
        Opens the given grammar file, parses it, then applies its productions
        to its start graph.
        Inputs: filename is the name of a graph grammar file
        Outputs: resulting graph
        """
        grammarFile = open(filename, 'r')
        f = self._parseGrammarFile(grammarFile.read())
        grammarFile.close()

        NUM_RULES = len(f.productions)
        if len(WEIGHTS) != NUM_RULES:
            raise RuntimeError('Number of rule weights not equal to number of rules.')

        if sum(WEIGHTS) != 1.0:
            raise RuntimeError("Weights don't sum to 1, you dingus!")

        self.applyProductions(f.startGraph, f.productions, f.config)
        graph_name = NAME + '_' + NUM_VERTICES + '_rev'
        self.outputReverseFile(graph_name, f)
        return f.startGraph


    #--------------------------------------------------------------------------
    # PRIVATE METHODS - These aren't the methods you're looking for.
    #--------------------------------------------------------------------------
    def _addNewEdges(self, graph, production, rhsMapping):
        """
        Adds edges to graph that appear in production.rhs but not in 
        production.lhs. Assumes that all the new vertices in the production.rhs
        have been added to graph, and rhsMapping has been updated accordingly.
        Inputs:
            * graph - Graph to which to apply the production
            * production - Production to apply
            * rhsMapping - {vid->vid} mapping between production.rhs
              and graph
        Outputs: None
        """	
        # logging.debug('>>> _addNewEdges <<<')
        for rhsEdge in production.rhs.edges: # [startVertex,endVertex]
            graphStartVID = rhsMapping[rhsEdge[0].id]
            graphEndVID = rhsMapping[rhsEdge[1].id]
            if not graph.hasEdgeBetweenVertices(graphStartVID, graphEndVID):
                graph.addEdge(graphStartVID, graphEndVID)
        logging.debug('graph is now %s' % graph)

    #--------------------------------------------------------------------------
    def _addNewVertices(self, graph, production, rhsMapping):
        """
        Adds vertices to graph that appear in production.rhs but not in 
        production.lhs. New vertices are given a vid of the form 'vN' where
        N is the number of vertices currently in the graph. New graph vertices
        are also added to rhsMapping.
        Inputs:
            * graph - Graph to which to apply the production
            * production - Production to apply
            * rhshMapping - {vid->vid} mapping from production.rhs to graph.
              This is typically created by _mapRHSToGraph().
        Outputs: nothing
        """
        # logging.debug('>>> _addNewVertices <<<')
        for rhsVertex in production.rhs.vertices:
            if rhsVertex.name not in production.lhs.names:
                # logging.debug('name %s in rhs but not lhs' % rhsVertex.label)
                newVertexID = 'v%s' % graph.numVertices
                newVertex = graph.addVertex(Vertex(newVertexID, rhsVertex.label, rhsVertex.number))
                # logging.debug('added vertex %s' % newVertex)
                rhsMapping[rhsVertex.id] = newVertexID
        # logging.debug('graph is now %s' % graph)

    #--------------------------------------------------------------------------
    def _applyProduction(self, graph, production, lhsMapping):
        """
        Applies the given production to the given graph. The general idea is to
        transform the portion of the graph identified by mapping (which 
        corresponds to the production's LHS) to look like the RHS of the
        production, by adding and/or removing vertices and edges.
        Inputs:
            graph - Graph to which to apply the production
            production - Production to apply
            lhsMapping - {vid->vid} mapping from production.lhs
                to graph
        Outputs: None
        """
        rhsMapping = self._mapRHSToGraph(graph, production, lhsMapping)
        self._deleteMissingVertices(graph, production, lhsMapping)
        self._deleteMissingEdges(graph, production, lhsMapping, rhsMapping)
        self._addNewVertices(graph, production, rhsMapping)
        self._addNewEdges(graph, production, rhsMapping)

    #--------------------------------------------------------------------------
    def _deleteMissingEdges(self, graph, production, lhsMapping, rhsMapping):
        """
        Deletes edges from graph that appear in production.lhs but not in 
        production.rhs. Assumes new vertices on rhs have been added to
        graph.
        Inputs: 
            * graph - Graph to which to apply the production
            * production - Production to apply
            * lhsMapping - {vid->vid} mapping from production.lhs
              to graph
            * rhsMapping - {vid->vid} mapping from production.rhs
              to graph
        Outputs: None
        """
        # logging.debug('>>> _deleteMissingEdges <<<')
        for lhsEdge in production.lhs.edges:    # [startVertex,endVertex]

            # Find the starting and ending vertices of the corresponding edge in graph.
            graphStartVID = lhsMapping[lhsEdge[0].id]
            graphEndVID = lhsMapping[lhsEdge[1].id]
            
            # Try to find the corresponding starting vertex in the rhs (if it
            # it exists at all). If it doesn't even exist, then the edge
            # doesn't exist either, so delete it from graph.
            rhsStart = [rhsID for rhsID,graphID in rhsMapping.items() if graphID == graphStartVID]
            if len(rhsStart) == 0:
                # logging.debug('edge start from %s to %s does not appear in rhs' % (lhsEdge[0], lhsEdge[1]))
                graph.deleteEdge(graphStartVID, graphEndVID)
                continue

            # Try to find the corresponding ending vertex in the rhs (if it
            # it exists at all). If it doesn't even exist, then the edge
            # doesn't exist either, so delete it from graph.
            rhsEnd = [rhsID for rhsID,graphID in rhsMapping.items() if graphID == graphEndVID]
            if len(rhsEnd) == 0:
                # logging.debug('edge end from %s to %s does not appear in rhs' % (lhsEdge[0], lhsEdge[1]))
                graph.deleteEdge(graphStartVID, graphEndVID)
                continue

            # We found both rhs vertices, but are they connected with an
            # edge? If not, the delete the edge from graph.
            if not production.rhs.hasEdgeBetweenVertices(rhsStart[0], rhsEnd[0]):
                # logging.debug('edge from %s to %s does not appear in rhs' % (lhsEdge[0], lhsEdge[1]))
                # logging.debug('deleting edge from %s to %s' % (graphStartVID, graphEndVID))
                graph.deleteEdge(graphStartVID, graphEndVID)

        # logging.debug('graph is now %s' % graph)

    #--------------------------------------------------------------------------
    def _deleteMissingVertices(self, graph, production, lhsMapping):
        """
        Deletes vertices from graph that appear in production.lhs but not in 
        production.rhs. It also deletes all edges to lead to or from the
        deleted vertex.
        Inputs:
            * graph - Graph to which to apply the production
            * production - Production to apply
            * lhsMapping - {vid->vid} mapping between production.lhs
                    and graph
        Outputs: None
        """
        # logging.debug('>>> _deleteMissingVertices <<<')
        for lhsVertex in production.lhs.vertices:
            if not production.rhs.findVertex(lhsVertex.name):
                graphVertexID = lhsMapping[lhsVertex.id]
                # logging.debug('deleting vertex %s' % graphVertexID)
                graph.deleteVertex(graphVertexID)

    #--------------------------------------------------------------------------
    def _findMatchingProductions(self, graph, productions):
        """
        Finds all the productions whose LHS graph can be found in graph. A
        production LHS matches if the text-only labels (e.g., "A") and the
        edges match (i.e., searching doesn't use the vertex number).
        Inputs: 
            * graph - Graph to search
            * productions - list of Production objects to search
        Outputs: list of (Production, mapping) tuples where Production
            is a Production whose LHS can be found in graph, and mapping is
            a {vid->vid} dictionary (LHS->graph) of where the LHS can be found.
        """
        # logging.debug('In _findMatchingProductions')
        solutions = []
        for prod in productions:
            # logging.debug('Checking production LHS %s ' % prod.lhs)
            print "Prod: ", prod.lhs, ' ', prod.rhs
            # Find all places where prod.lhs can be found in graph.
            listOfMatches = graph.search(prod.lhs)
            if len(listOfMatches) > 0:
                for match in listOfMatches:
                    solutions.append( (prod, match) )
                    # logging.debug('Production %s matches' % prod.lhs)
            else:
                    # logging.debug('Production %s does not match' % prod.lhs)
                    pass
                    
        # logging.debug('Out _findMatchingProductions')

        return solutions

    #--------------------------------------------------------------------------
    def _findWeightedMatchingProductions(self, graph, productions):

        # logging.debug('In _findMatchingProductions')
        solutions = []
        weights = WEIGHTS
        #weights = [1.0]
        # prod = np.random.choice(productions, p=weights)

        while True:
            cs = np.cumsum(weights) #An array of the weights, cumulatively summed.
            idx = sum(cs < np.random.rand())  #Find the index of the first weight over a random value.
            #productions[idx].incr_count()
            prod = productions[idx]
            # logging.debug('Checking production LHS %s ' % prod.lhs)

            # Find all places where prod.lhs can be found in graph.
            listOfMatches = graph.search(prod.lhs)
            if len(listOfMatches) > 0:
                break
            
        productions[idx].incr_count()
        print "Selected Production:\n", prod.lhs, " ==> ", prod.rhs, "Count: ", prod.count;
        if len(listOfMatches) > 0:
            for match in listOfMatches:
                solutions.append( (prod, match) )
                # logging.debug('Production %s matches' % prod.lhs)
        else:
                # logging.debug('Production %s does not match' % prod.lhs)
                pass
                
        # logging.debug('Out _findMatchingProductions')
        return solutions

    #--------------------------------------------------------------------------
    def _mapRHSToGraph(self, graph, production, lhsMapping):
        """
        Maps to production's rhs vertices to graph. For rhs vertices that
        appear in the lhs, we use the lhsMapping to determine which graph
        vertex the rhs vertex maps to. For rhs vertices that are new (i.e.,
        don't exist in the lhs), we ignore them for now and update the
        rhs mapping when we add the new vertices to graph. LHS and RHS 
        vertices are considered the same if both their label and their
        number match.
        Inputs:
            * graph - Graph to which to apply the production
            * production - Production to apply
            * lhs2GraphMapping - {vid->vid} mapping from production.lhs
              vertices to graph
        Outputs: {vid->vid} mapping from production.rhs vertices to graph
        """
        rhsMapping = {}

        for rhsVertex in production.rhs.vertices:
            if rhsVertex.name in production.lhs.names:
                lhsVertex = production.lhs.findVertex(rhsVertex.name)
                rhsMapping[rhsVertex.id] = lhsMapping[lhsVertex.id] 
        return rhsMapping

    #--------------------------------------------------------------------------
    def _parseGrammarFile(self, grammarFile):
        """
        Parses the given grammar file contents, returning the parser.
        Inputs: grammarFile - string contents of a graph grammar file
        Outputs: Parser after it has parsed the given input
        """
        #print grammarFile
        p = Parser(Lexer(grammarFile))
        p.parse()
        return p

    def _showCounts(self, productions):

        print "Number of applications: "
        for prod in productions:
            print prod.lhs, " ==> ", prod.rhs, "\nCount: ", prod.count 

# debug, info, warning, error and critical
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
if __name__ == '__main__':
    num_args = len(sys.argv)
    if num_args < 2:
        print >> sys.stderr, "Usage: %s GRAMMAR_FILE" % sys.argv[0]
        sys.exit(1)
    e = Generator()
    GRAMMAR = sys.argv[1]
    NAME = sys.argv[2]
    NUM_VERTICES = sys.argv[3]
    
    WEIGHTS = []
    for i in range(4,num_args):
        WEIGHTS.append(float(sys.argv[i]))
    e.generateFromFile(GRAMMAR)

# vim:nowrap
