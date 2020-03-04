import random
import numpy as np
import networkx as nx
from ortools.linear_solver import pywraplp

def main():
    ## BUILD SIMPLE GRAPH FOR TESTING
    num_nodes = 4
    # Assumes graph always has edge in both directions even though `directed`
    graph = nx.Graph().to_directed()
    edge_weight = 10
    graph.add_edge(0, 1, weight=edge_weight)
    graph.add_edge(1, 0, weight=edge_weight)
    graph.add_edge(1, 2, weight=edge_weight)
    graph.add_edge(2, 1, weight=edge_weight)
    graph.add_edge(2, 3, weight=edge_weight)
    graph.add_edge(3, 2, weight=edge_weight)
    graph.add_edge(3, 0, weight=edge_weight)
    graph.add_edge(0, 3, weight=edge_weight)
    demands = np.ones(shape=(num_nodes, num_nodes), dtype=float)


    ## ACTUAL CODE START
    edges = list(graph.edges())
    edge_index_dict = {edge : i for i, edge in enumerate(edges)}
    
    # create commodities from demands (make sure to ignore demand to self)
    commodities = [(i, j, demands[i, j]) for i in range(num_nodes)
                                         for j in range(num_nodes) if i != j]

    # Create the linear solver with the GLOP backend.
    solver = pywraplp.Solver('multicommodity_flow_lp',
                                pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)

    ## VARIABLES
    # Flow variables, the splitting ratios for each edge
    # Stored as a list of lists (flow_variables[ith_flow][jth_edge])
    flow_variables = []
    print(list(graph.edges()))
    for i in range(len(commodities)):
        flow_variable_edges = []
        for j in range(graph.number_of_edges()):
            flow_variable_edges.append(
                solver.NumVar(0, 1, '({},{})'.format(i, j)))
        flow_variables.append(flow_variable_edges)

    print('Number of variables =', solver.NumVariables())

    ## CONSTRAINTS
    # Capacity constraint
    capacity_constraints = []
    for i, edge in enumerate(graph.edges()):
        # Constraint between 0 and edge capacity
        constraint_i = solver.Constraint(
            0, graph.get_edge_data(*edge)['weight'],'(1,{},{})'.format(*edge))
        for j, commodity in enumerate(commodities):
            # Coefficient for jth flow over ith edge is scaled by flow width
            constraint_i.SetCoefficient(flow_variables[j][i],
                                        commodity[2])
        capacity_constraints.append(constraint_i)

    # Conservation on transit nodes
    conservation_transit_constraints = []
    for i, commodity in enumerate(commodities):
        constraints_flow_i = []
        for j in range(graph.number_of_nodes()):
            if j != commodity[0] and j != commodity[1]:
                # Constraint must sum to zero
                constraint_j = solver.Constraint(0, 0, '(2,{},{})'.format(i, j))
                for k in list(graph.adj[j].keys()):
                    # Ingress edges
                    constraint_j.SetCoefficient(
                        flow_variables[i][edge_index_dict[(k, j)]], 1)
                    # Egress edges
                    constraint_j.SetCoefficient(
                        flow_variables[i][edge_index_dict[(j, k)]], -1)
                constraints_flow_i.append(constraint_j)
        conservation_transit_constraints.append(constraints_flow_i)

    # Conservation  of flow at source node
    conservation_source_constraints = []
    for i, commodity in enumerate(commodities):
        # Constraint must sum to one (assuming all the demand can be met)
        constraint_i = solver.Constraint(1, 1, '(3,{})'.format(i))
        for edge_dest in list(graph.adj[commodity[0]].keys()):
            constraint_i.SetCoefficient(
                flow_variables[i][edge_index_dict[(commodity[0], edge_dest)]],
                1)
            constraint_i.SetCoefficient(
                flow_variables[i][edge_index_dict[(edge_dest, commodity[0])]],
                -1)
        conservation_source_constraints.append(constraint_i)

    # Conservation of flow at destination node
    conservation_dest_constraints = []
    for i, commodity in enumerate(commodities):
        # Constraint must sum to one (assuming all the demand can be met)
        constraint_i = solver.Constraint(1, 1, '(4,{})'.format(i))
        for edge_dest in list(graph.adj[commodity[1]].keys()):
            constraint_i.SetCoefficient(
                flow_variables[i][edge_index_dict[(edge_dest, commodity[1])]], 1)
            constraint_i.SetCoefficient(
                flow_variables[i][edge_index_dict[(commodity[1], edge_dest)]], -1)
        conservation_dest_constraints.append(constraint_i)

    print('Number of constraints =', solver.NumConstraints())

    ## OBJECTIVES
    # Implementation of the load-balancing example from wikipedia
    # First we add more constraints so that we are minimising the maximum
    max_utilisation_variable = solver.NumVar(0, solver.Infinity(),
                                             'max_link_utilisation')
    min_of_max_constraints = []
    for i, edge in enumerate(graph.edges()):
        # Constraint that '-inf < f_0 + f_1 +... - max < 0'
        # i.e 'f_0 + f_1 + ... < max'
        constraint_i = solver.Constraint(-solver.Infinity(), 0,
                                         '(5,{})'.format(i))
        constraint_i.SetCoefficient(max_utilisation_variable, -1)
        for j, flow_variable in enumerate(flow_variables):
            constraint_i.SetCoefficient(flow_variable[i],
                                        commodities[j][2] /
                                        graph.get_edge_data(*edge)['weight'])
        min_of_max_constraints.append(constraint_i)

    # Objective now is to minimise the maximum link utilisation
    objective = solver.Objective()
    objective.SetCoefficient(max_utilisation_variable, 1)
    objective.SetMinimization()
    solver.Solve()

    print('Solution:')
    print('Objective value =', objective.Value())

    for i, flow_var in enumerate(flow_variables):
        print("Flow: {}".format(i))
        for edge in flow_var:
            print(edge.solution_value())

if __name__ == '__main__':
    main()
