#!/usr/bin/python

import logging
import random
import sys

from PGC.Parser import Parser
from PGC.Lexer import Lexer
from PGC.Graph.Vertex import Vertex

class Generator(object):
    """
    Transformation engine for graphs. Given a set of productions of the
    form lhs ==> rhs, and using a starting graph G, uses graph 
    isomorphic searching to find instances of a lhs in G and replaces the lhs 
    vertices with the rhs. The engine continues to apply these transformations 
    until G contains a given number of vertices. This assumes that the productions
    generally increase the number of vertices.

    Usage: Either use the all-inclusive main() method which checks the 
    command-line arguments, or call applyProductions() yourself which
    takes a starting graph, list of productions, and a dictionary of
    configuration options.
    """

    #--------------------------------------------------------------------------
    def applyProductions(self, startGraph, productions, config):
        """
        Randomly applies a production from the given list of productions to the
        specified starting graph until the graph contains at least the number
        of vertices specified by the config option "min_vertices". This assumes
        that the productions generally increase the number of vertices.
        Inputs: 
                * startGraph - Graph to begin applying transformations
                * productions - list of Production objects
                * config - dictionary of key/value pairs of configuration options. Only
                    one is mandatory: min_vertices, which indicates when to stop
                    applying productions.
        Outputs: None
        """ 
        while startGraph.numVertices < config['min_vertices']:

            # matchingProductions is a list of (Production, mapping) 
            # pairs where mapping is {vid->vid} dictionary of where 
            # the production's lhs vertices can be found in startGraph.
            matchingProductions = self._findMatchingProductions(startGraph, productions)
            
            if len(matchingProductions) == 0:
                raise RuntimeError('No productions match the given graph.')

            (prod, mapping) = random.choice(matchingProductions)
            logging.debug('Going to apply %s using mapping %s.' % (prod, mapping))

            self._applyProduction(startGraph, prod, mapping)

    #--------------------------------------------------------------------------
    def main(self):
        """
        To be called from the command line. Checks the command line arguments 
        for a filename, opens the file, and sends it to the parser.
        Inputs: None
        Outputs: None
        """
        if len(sys.argv) < 2:
            raise RuntimeError("Usage: %s FILENAME" % sys.argv[0])
        
        prodFile = open(sys.argv[1], 'r')
        p = self._parseGrammarFile(prodFile.read())
        prodFile.close()

        self.applyProductions(p.startGraph, p.productions, p.config)

    #--------------------------------------------------------------------------
    def _addNewEdges(self, graph, production, rhsMapping):
        """
        Adds edges to graph that appear in production.rhs but not in 
        production.lhs. Assumes that all the new vertices in the production.rhs
        have been added to graph.
        Inputs:
                * graph - Graph to which to apply the production
                * production - Production to apply
                * rhsMapping - {vid->vid} mapping between production.rhs
                        and graph
        Outputs: None
        """	
        for rhsEdge in production.rhs.edges: # [Vertex,Vertex]
            logging.debug('checking for edge between %s and %s in graph' % (rhsEdge[0].label, rhsEdge[1].label))
            graphStartVID = rhsMapping[rhsEdge[0].id]
            graphEndVID = rhsMapping[rhsEdge[1].id]
            #if (graphStartVID not in graph._edges) or (graphEndVID not in graph._edges[graphStartVID]):
            if not graph.hasEdgeBetween(graphStartVID, graphEndVID):
                logging.debug("edge doesn't exist. creating it")
                logging.debug('adding edge between %s and %s' % (graphStartVID, graphEndVID))
                graph.addEdge(graphStartVID, graphEndVID)

    #--------------------------------------------------------------------------
    def _addNewVertices(self, graph, production, lhsMapping, rhsMapping):
        """
        Adds vertices to graph that appear in production.rhs but not in 
        production.lhs.
        Inputs:
            * graph - Graph to which to apply the production
            * production - Production to apply
            * lhs2GraphMapping - {vid->vid} mapping between production.lhs
                    and graph
        Outputs: nothing
        """
        for rhsVertex in production.rhs.vertices.itervalues():
            if rhsVertex.label not in production.lhs.labels:
                logging.debug("found rhs rhsVertex %s not in lhs" % rhsVertex)
                newVertexID = 'v%s' % graph.numVertices
                logging.debug("adding vertex to graph with id %s and label %s" % (newVertexID, rhsVertex.label))
                logging.debug("graph as %d vertices" % graph.numVertices)
                newVertex = graph.addVertex(Vertex(newVertexID, rhsVertex.label))
                logging.debug("graph now has %d vertices" % graph.numVertices)
                rhsMapping[rhsVertex.id] = newVertexID

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
            lhsMapping - {vid->vid} mapping between production.lhs
                    and graph
        Outputs: None
        """
        rhsMapping = self._mapRHSToGraph(graph, production, lhsMapping)
        self._addNewVertices(graph, production, lhsMapping, rhsMapping)
        self._addNewEdges(graph, production, rhsMapping)
        self._deleteMissingEdges(graph, production, lhsMapping, rhsMapping)
        self._deleteMissingVertices(graph, production, lhsMapping)

    #--------------------------------------------------------------------------
    def _deleteMissingEdges(self, graph, production, lhsMapping, rhsMapping):
        """
        Deletes edges from graph that appear in production.lhs but not in 
        production.rhs. Assumes the vertices between lhs and rhs have been
        added/removed.
        Inputs:
            * graph - Graph to which to apply the production
            * production - Production to apply
            * lhsMapping - {vid->vid} mapping between production.lhs
                    and graph
            * rhsMapping - {vid->vid} mapping between production.rhs
                    and graph
        Outputs: None
        """
        for lhsEdge in production.lhs.edges:    # [Vertex,Vertex]
            logging.debug('checking for edge between %s and %s in rhs' % (lhsEdge[0].label, lhsEdge[1].label))
            graphStartVID = lhsMapping[lhsEdge[0].id]
            graphEndVID = lhsMapping[lhsEdge[1].id]
            
            # Probably should move this to a method to make it more readable.
            rhsStartVID = [rhsID for rhsID,graphID in rhsMapping.items() if graphID == graphStartVID][0]
            rhsEndVID = [rhsID for rhsID,graphID in rhsMapping.items() if graphID == graphEndVID][0]

            if not production.rhs.hasEdgeBetween(rhsStartVID, rhsEndVID):
                logging.debug('no edge found in rhs, removing from graph')
                graph.deleteEdge(graphStartVID, graphEndVID)

    #--------------------------------------------------------------------------
    def _deleteMissingVertices(self, graph, production, lhsMapping):
        """
        Deletes vertices from graph that appear in production.lhs but not in 
        production.rhs.
        Inputs:
                * graph - Graph to which to apply the production
                * production - Production to apply
                * lhsMapping - {vid->vid} mapping between production.lhs
                        and graph
        Outputs: None
        """
        for lhsVertex in production.lhs.vertices.itervalues():
            if lhsVertex.label not in production.rhs.labels:
                logging.debug("found lhs lhsVertex %s not in rhs" % lhsVertex)
                graphVertexID = lhsMapping[lhsVertex.id]
                logging.debug("deleting vertex from graph with id %s" % graphVertexID)
                newVertex = graph.deleteVertex(graphVertexID)
                logging.debug("graph now has %d vertices" % graph.numVertices)

    #--------------------------------------------------------------------------
    def _findMatchingProductions(self, graph, productions):
        """
        Finds all the productions whose LHS can be found in graph.
        Inputs: 
                * graph - Graph to search
                * productions - list of Production objects to search
        Outputs: list of (Production, mapping) tuples where Production
            is a Production that can be found in graph, and mapping is
            a {vid->vid} dictionary of where the lhs can be found.
        """
        solutions = []
        for prod in productions:
            logging.debug('Checking production %s ' % prod.lhs)
            matches = graph.search(prod.lhs)
            if len(matches) > 0:
                for match in matches:
                    solutions.append( (prod, match) )
                    logging.debug('Production %s matches' % prod.lhs)
            else:
                    logging.debug('Production %s does not match' % prod.lhs)
        return solutions

    #--------------------------------------------------------------------------
    def _mapRHSToGraph(self, graph, production, lhsMapping):
        """
        Maps to production's rhs vertices to graph. For rhs vertices that
        appear in the lhs, we use the lhsMapping to determine which graph
        vertex to rhs vertex maps to. For rhs vertices that are new (i.e.,
        don't exist in the lhs), we ignore them.
        Inputs:
            * graph - Graph to which to apply the production
            * production - Production to apply
            * lhs2GraphMapping - {vid->vid} mapping between production.lhs
              vertices and graph
        Outputs: {vid->vid} mapping between production.rhs vertices and graph
        """

        rhsMapping = {}

        for rhsVertex in production.rhs.vertices.itervalues():
            if rhsVertex.label in production.lhs.labels:
                rhsMapping[rhsVertex.id] = lhsMapping[production.lhs.findVertexWithLabel(rhsVertex.label).id] 
        return rhsMapping

    #--------------------------------------------------------------------------
    def _parseGrammarFile(self, grammarFile):
        """
        Parses the given grammar file contents, returning the parser.
        Inputs: grammarFile - string contents of a graph grammar file
        Outputs: Parser after it has parsed the given input
        """

        p = Parser(Lexer(grammarFile))
        p.parse()
        return p

# debug, info, warning, error and critical
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
if __name__ == '__main__':
    e = Generator()
    e.main()