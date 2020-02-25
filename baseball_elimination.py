'''Code file for baseball elimination lab created for Advanced Algorithms
Spring 2020 at Olin College. The code for this lab has been adapted from:
https://github.com/ananya77041/baseball-elimination/blob/master/src/BaseballElimination.java'''

import sys
import math
import picos as pic
import networkx as nx
import itertools
import cvxopt
import copy


class Division:
    '''
    The Division class represents a baseball division. This includes all the
    teams that are a part of that division, their winning and losing history,
    and their remaining games for the season.

    filename: name of a file with an input matrix that has info on teams &
    their games
    '''

    def __init__(self, filename):
        self.teams = {}
        self.G = nx.DiGraph()
        self.readDivision(filename)

    def readDivision(self, filename):
        '''Reads the information from the given file and builds up a dictionary
        of the teams that are a part of this division.

        filename: name of text file representing tournament outcomes so far
        & remaining games for each team
        '''
        f = open(filename, "r")
        lines = [line.split() for line in f.readlines()]
        f.close()

        lines = lines[1:]
        for ID, teaminfo in enumerate(lines):
            team = Team(int(ID), teaminfo[0], int(teaminfo[1]), int(teaminfo[2]), int(teaminfo[3]), list(map(int, teaminfo[4:])))
            self.teams[ID] = team

    def get_team_IDs(self):
        '''Gets the list of IDs that are associated with each of the teams
        in this division.

        return: list of IDs that are associated with each of the teams in the
        division
        '''
        return self.teams.keys()

    def is_eliminated(self, teamID, solver):
        '''Uses the given solver (either Linear Programming or Network Flows)
        to determine if the team with the given ID is mathematically
        eliminated from winning the division (aka winning more games than any
        other team) this season.

        teamID: ID of team that we want to check if it is eliminated
        solver: string representing whether to use the network flows or linear
        programming solver
        return: True if eliminated, False otherwise
        '''
        flag1 = False
        team = self.teams[teamID]

        temp = dict(self.teams)
        del temp[teamID]

        for _, other_team in temp.items():
            if team.wins + team.remaining < other_team.wins:
                flag1 = True

        saturated_edges = self.create_network(teamID)
        if not flag1:
            if solver == "Network Flows":
                flag1 = self.network_flows(saturated_edges)
            elif solver == "Linear Programming":
                flag1 = self.linear_programming(saturated_edges)

        return flag1

    def create_network(self, teamID):
        '''Builds up the network needed for solving the baseball elimination
        problem as a network flows problem & stores it in self.G. Returns a
        dictionary of saturated edges that maps team pairs to the amount of
        additional games they have against each other.

        teamID: ID of team that we want to check if it is eliminated
        return: dictionary of saturated edges that maps team pairs to
        the amount of additional games they have against each other
        '''
        self.G.clear()
        saturated_edges = {}
        self.G.add_node("S")
        self.G.add_node("T")
        versus=copy.deepcopy(self.teams)
        del versus[teamID]
        for key, value in versus.items():
            self.G.add_node(value.name)
            self.G.add_edge(value.name,"T",capacity=(self.teams[teamID].wins + self.teams[teamID].remaining - value.wins))

            for key2, value2 in versus.items():
                if (not(self.G.has_node(value2.name))):
                    self.G.add_node((value.name,value2.name))
                    self.G.add_edge("S",(value.name,value2.name),capacity=value.get_against(value2.ID))
                    self.G.add_edge((value.name,value2.name),value.name)
                    saturated_edges[("S",(value.name,value2.name))] = value.get_against(value2.ID)
                elif value.name!=value2.name:
                    self.G.add_edge((value2.name,value.name),value.name)
        #print(self.G.edges)
        return saturated_edges

    def network_flows(self, saturated_edges):
        '''Uses network flows to determine if the team with given team ID
        has been eliminated. You can feel free to use the built in networkx
        maximum flow function or the maximum flow function you implemented as
        part of the in class implementation activity.

        saturated_edges: dictionary of saturated edges that maps team pairs to
        the amount of additional games they have against each other
        return: True if team is eliminated, False otherwise
        '''

        #TODO: implement this
        max_flow, flows = nx.maximum_flow(self.G,'S','T')
        for key,value in flows['S'].items():
            if value != saturated_edges[('S',key)]:
                #print(value)
                #print(flows)
                self.G.clear()
                return True
        self.G.clear()
        return False

    def linear_programming(self, saturated_edges):
        '''Uses linear programming to determine if the team with given team ID
        has been eliminated. We recommend using a picos solver to solve the
        linear programming problem once you have it set up.
        Do not use the flow_constraint method that Picos provides (it does all of the work for you)
        We want you to set up the constraint equations using picos (hint: add_constraint is the method you want)

        saturated_edges: dictionary of saturated edges that maps team pairs to
        the amount of additional games they have against each other
        returns True if team is eliminated, False otherwise
        '''

        maxflow=pic.Problem()
        y=[]
        i=0
        #F=maxflow.add_variable('F',1)
        for node in self.G.neighbors("S"):
            y.append(maxflow.add_variable('y[{0}]'.format(i),1))
            maxflow.add_constraint(y[i]<self.G.edges['S',node]['capacity'])
            i+=1
        j=0
        maxflow.set_objective('max',sum(y))
        for node in self.G.neighbors("S"):
            maxflow.add_constraint(y[j]>0)
            j+=1
            capacitance=[]
            for node2 in self.G.neighbors(node):
                capacitance.append(i)
                y.append(maxflow.add_variable('y[{0}]'.format(i),1))
                maxflow.add_constraint(y[i]>0)
                i+=1
            maxflow.add_constraint(y[j]==sum(y[capacitance[0]:capacitance[-1]+1]))

        for node in self.G.predecessors("T"):
            y.append(maxflow.add_variable('y[{0}]'.format(i),1))
            maxflow.add_constraint(y[i]<self.G.edges[node,'T']['capacity'])
            maxflow.add_constraint(y[i]>0)
            maxflow.add_constraint(y[i]==sum(y[i-(2*j):i-(2*j)+2]))
            i+=1
        #maxflow.add_list_of_constraints(
        #  [pic.sum([y[p,i] for p in self.G.predecessors(i)],'p','pred(i)')
        #    == pic.sum([y[i,j] for j in self.G.successors(i)],'j','succ(i)')
        #    for i in self.G.nodes() if i not in ("S","T")],
        #  'i','nodes-(s,t)')
        maxflow.solve(verbose=0,solver='glpk')
        total_flow=0
        for key, value in saturated_edges.items():
            total_flow+=value
        #print(maxflow)
        #print(y[10])
        #print(total_flow)
        #print(maxflow.obj_value())
        if(total_flow!=maxflow.obj_value()):
            return True
        #TODO: implement this
        return False


    def checkTeam(self, team):
        '''Checks that the team actually exists in this division.
        '''
        if team.ID not in self.get_team_IDs():
            raise ValueError("Team does not exist in given input.")

    def __str__(self):
        '''Returns pretty string representation of a division object.
        '''
        temp = ''
        for key in self.teams:
            temp = temp + f'{key}: {str(self.teams[key])} \n'
        return temp

class Team:
    '''
    The Team class represents one team within a baseball division for use in
    solving the baseball elimination problem. This class includes information
    on how many games the team has won and lost so far this season as well as
    information on what games they have left for the season.

    ID: ID to keep track of the given team
    teamname: human readable name associated with the team
    wins: number of games they have won so far
    losses: number of games they have lost so far
    remaining: number of games they have left this season
    against: dictionary that can tell us how many games they have left against
    each of the other teams
    '''

    def __init__(self, ID, teamname, wins, losses, remaining, against):
        self.ID = ID
        self.name = teamname
        self.wins = wins
        self.losses = losses
        self.remaining = remaining
        self.against = against

    def get_against(self, other_team=None):
        '''Returns number of games this team has against this other team.
        Raises an error if these teams don't play each other.
        '''
        try:
            num_games = self.against[other_team]
        except:
            raise ValueError("Team does not exist in given input.")

        return num_games

    def __str__(self):
        '''Returns pretty string representation of a team object.
        '''
        return f'{self.name} \t {self.wins} wins \t {self.losses} losses \t {self.remaining} remaining'

if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        division = Division(filename)
    #    p=division.create_network(0)
    #    print(division.linear_programming(p))

        for (ID, team) in division.teams.items():
            print(f'{team.name}: Eliminated? {division.is_eliminated(team.ID, "Network Flows")}')
    else:
        print("To run this code, please specify an input file name. Example: python baseball_elimination.py teams2.txt.")
